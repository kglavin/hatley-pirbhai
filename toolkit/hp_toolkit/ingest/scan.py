# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Stage 0 — codebase scanner. Pure Python, no LLM.

Walks the codebase, classifies each file with an HP role hint (see
`role_classifier.py`), applies the significance filter (see `significance.py`),
detects languages + frameworks, and emits `intermediate/scan.json`.

This is the input to every downstream agent. The cost is O(files) + a few
content reads per file — fast enough to run on acme-cp-scale repos
in seconds.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from .role_classifier import classify_file, detect_language
from .schema import FileEntry, HpRoleHint, ProjectMeta, ProjectScan
from .significance import SignificanceConfig, filter_significance, is_path_always_skipped, content_marks_generated


# Max bytes read per file when sniffing for role-classifier content patterns.
# Bigger files are sampled; tiny role-classifier patterns rarely live past the
# top of the file (imports, server setup, enum declarations).
_MAX_CONTENT_BYTES = 16 * 1024


# ─────────────────────────────────────────────────────────────────────
# Framework detection — heuristic, runs on aggregated content
# ─────────────────────────────────────────────────────────────────────

_FRAMEWORK_MARKERS = [
    # Python web/api frameworks
    ("FastAPI",     re.compile(r"\bfrom fastapi import|FastAPI\(")),
    ("Flask",       re.compile(r"\bfrom flask import|Flask\(")),
    ("Django",      re.compile(r"\bdjango\.")),
    ("Starlette",   re.compile(r"\bfrom starlette import")),
    # Rust web/runtime
    ("Axum",        re.compile(r"\baxum::")),
    ("Actix",       re.compile(r"\bactix_web::")),
    ("Tonic",       re.compile(r"\btonic::")),
    ("Tokio",       re.compile(r"\btokio::")),
    # Go web frameworks
    ("Gin",         re.compile(r"\"github\.com/gin-gonic/gin\"")),
    ("Echo",        re.compile(r"\"github\.com/labstack/echo")),
    ("Chi",         re.compile(r"\"github\.com/go-chi/chi")),
    ("Cobra",       re.compile(r"\bcobra\.Command\b")),
    # TS/JS frontend / backend
    ("React",       re.compile(r"\bfrom ['\"]react['\"]")),
    ("Next.js",     re.compile(r"\bfrom ['\"]next/")),
    ("Vue",         re.compile(r"\bfrom ['\"]vue['\"]")),
    ("Express",     re.compile(r"\brequire\(['\"]express['\"]\)|from ['\"]express['\"]")),
    ("Nest",        re.compile(r"\bfrom ['\"]@nestjs/")),
    # Data stores
    ("PostgreSQL",  re.compile(r"\b(psycopg2|asyncpg|sqlx::PgPool|pg\.Pool)\b")),
    ("Redis",       re.compile(r"\b(redis|aioredis|go-redis)\b")),
    ("ClickHouse",  re.compile(r"\bclickhouse\b", re.IGNORECASE)),
    ("Dgraph",      re.compile(r"\bdgraph\b", re.IGNORECASE)),
    ("VictoriaMetrics", re.compile(r"\bvictoriametrics|VictoriaMetrics")),
    ("MongoDB",     re.compile(r"\bMongoClient|aiomongo|mongodb\b", re.IGNORECASE)),
    # Observability
    ("OpenTelemetry", re.compile(r"\bopentelemetry\b", re.IGNORECASE)),
    ("Prometheus",  re.compile(r"\bprometheus_client|prom-client\b")),
    # Build / infra
    ("Docker",      re.compile(r"^FROM\s+", re.MULTILINE)),
    ("Kubernetes",  re.compile(r"^apiVersion:\s*(apps|core|networking|batch)/", re.MULTILINE)),
    ("Terraform",   re.compile(r"^resource\s+\"", re.MULTILINE)),

    # ── Embedded RTOSes (per EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding A) ──
    ("FreeRTOS",    re.compile(r"\b(xTaskCreate|osThreadDef|osThreadNew|vTaskDelay|vTaskStartScheduler)\b")),
    ("NuttX",       re.compile(r"\b(px4_arch_|board_app_initialize|nsh_main)\b|^#include\s+<nuttx/")),
    ("Zephyr",      re.compile(r"\bk_thread_create\b|^#include\s+<zephyr/|^CONFIG_ZEPHYR")),
    ("ChibiOS",     re.compile(r"\b(chThdCreate|chThdSleep|evtRegister|chSysInit)\b")),
    ("Mbed",        re.compile(r"^#include\s+\"mbed\.h\"|\bmbed::Thread|\bEventQueue\s*\(")),
    ("ESP-IDF",     re.compile(r"\besp_event_loop\b|\besp_wifi_\w+\b|^#include\s+\"esp_", re.MULTILINE)),

    # ── STM32 ecosystem ──
    ("STM32 HAL",   re.compile(r"\bHAL_[A-Z][A-Za-z0-9_]*_Init\b|^#include\s+\"stm32[a-z0-9]+_hal\.h\"")),
    ("STM32CubeMX", re.compile(r"\bMX_[A-Z][A-Za-z0-9_]*_Init\b|^Mcu\.Family=STM32", re.MULTILINE)),
    ("STM32 LL",    re.compile(r"\bLL_[A-Z][A-Z0-9_]*_(?:Init|Enable|Disable)\b|^#include\s+\"stm32[a-z0-9]+_ll_")),

    # ── Arduino + AUTOSAR ──
    ("Arduino",     re.compile(r"^void\s+setup\s*\(\s*\)|^void\s+loop\s*\(\s*\)|^#include\s+(<|\")Arduino\.h", re.MULTILINE)),
    ("AUTOSAR",     re.compile(r"\b(Rte_[A-Z][\w]+|BswM_[A-Z][\w]+|Com_[A-Z][\w]+|Os_[A-Z][\w]+|EcuM_[A-Z][\w]+)\b")),

    # ── ROS 2 family + Micro-ROS ──
    ("ROS 2",       re.compile(r"\brclcpp::|\brclpy\.|^#include\s+\"rclcpp/")),
    ("Micro-ROS",   re.compile(r"\b(rclc_[a-z_]+|rmw_microros_|rcl_publisher_init|rcl_subscription_init)\b")),
    ("MAVLink",     re.compile(r"\bmavlink_msg_[a-z0-9_]+_(pack|decode|encode)\b|^#include\s+\"mavlink/")),
    ("uORB",        re.compile(r"\b(orb_advertise|orb_subscribe|ORB_ID\(|ORB_DECLARE)\b")),

    # ── DDS impls ──
    ("Fast-DDS",    re.compile(r"\beprosima::fastdds::|^#include\s+(<|\")fastdds/")),
    ("Cyclone DDS", re.compile(r"\bdds_create_(writer|reader|topic|participant)\b|^#include\s+(<|\")dds/")),
    ("Connext DDS", re.compile(r"\bRTI_Connext|^#include\s+(<|\")ndds/")),
]


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def scan_codebase(
    root: Path,
    project_name: Optional[str] = None,
    significance_config: Optional[SignificanceConfig] = None,
) -> ProjectScan:
    """Walk `root`, classify each file, return a `ProjectScan`.

    `project_name` defaults to the basename of `root`. The git commit hash is
    captured if `root` is a git repository; otherwise omitted.
    """
    root = root.resolve()
    name = project_name or root.name

    file_paths = list(_enumerate_files(root))
    files: list[FileEntry] = []
    framework_hits: Counter[str] = Counter()

    for abs_path in file_paths:
        rel = abs_path.relative_to(root).as_posix()
        if is_path_always_skipped(rel):
            # Don't even open the file
            files.append(FileEntry(
                path=rel,
                language=detect_language(abs_path),
                size_lines=0,
                hp_role_hint=None,
                is_significant=False,
                notes="filtered: skipped path (pre-walk filter)",
            ))
            continue

        content, line_count = _read_file_sample(abs_path)

        if content is not None and content_marks_generated(content):
            files.append(FileEntry(
                path=rel,
                language=detect_language(abs_path),
                size_lines=line_count,
                hp_role_hint=None,
                is_significant=False,
                notes="filtered: file marks itself AUTO-GENERATED",
            ))
            continue

        hint = classify_file(abs_path, content)
        files.append(FileEntry(
            path=rel,
            language=detect_language(abs_path),
            size_lines=line_count,
            hp_role_hint=hint,
            is_significant=True,                 # provisional; finalized by filter pass
            notes=None,
        ))

        if content is not None:
            for fw_name, fw_pat in _FRAMEWORK_MARKERS:
                if fw_pat.search(content):
                    framework_hits[fw_name] += 1

    # Apply significance filter (annotates is_significant + notes)
    files = filter_significance(files, significance_config)

    # Language histogram across significant files
    lang_hits: Counter[str] = Counter(
        f.language for f in files if f.is_significant and f.language
    )

    project = ProjectMeta(
        name=name,
        languages=[lang for lang, _ in lang_hits.most_common()],
        frameworks=[fw for fw, _ in framework_hits.most_common()],
        git_commit_hash=_git_commit_hash(root),
        analyzed_at=datetime.now(),
    )

    return ProjectScan(project=project, files=files, import_map={})


def write_scan(scan: ProjectScan, out_path: Path) -> None:
    """Serialize a `ProjectScan` to JSON."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(scan.model_dump_json(indent=2))


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

def _enumerate_files(root: Path) -> list[Path]:
    """Return every tracked file under `root`. Uses `git ls-files` if `root`
    is a git repo; otherwise falls back to recursive walk filtered by
    `.gitignore`-like heuristics."""
    if (root / ".git").is_dir():
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "ls-files"],
                capture_output=True, text=True, check=True,
            )
            return [root / line for line in result.stdout.splitlines() if line]
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    # Fallback: walk the tree. Filter out dot-directories at every level.
    out: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(root).parts):
            out.append(p)
    return out


def _read_file_sample(path: Path) -> tuple[Optional[str], int]:
    """Read up to `_MAX_CONTENT_BYTES` from `path`. Returns (content, total_lines).

    On any read error or binary content, returns (None, 0)."""
    try:
        with path.open("rb") as fh:
            head = fh.read(_MAX_CONTENT_BYTES)
        # Quick binary detection — null bytes in the head
        if b"\x00" in head:
            return None, 0
        try:
            text = head.decode("utf-8")
        except UnicodeDecodeError:
            text = head.decode("utf-8", errors="replace")
        # Count total lines cheaply via byte count of file
        size = path.stat().st_size
        if size <= _MAX_CONTENT_BYTES:
            total_lines = text.count("\n")
        else:
            # Estimate from sampled lines/byte ratio
            sampled_lines = text.count("\n")
            total_lines = int(sampled_lines * (size / _MAX_CONTENT_BYTES))
        return text, total_lines
    except (OSError, PermissionError):
        return None, 0


def _git_commit_hash(root: Path) -> Optional[str]:
    """Return the current git commit hash, or None if not a git repo."""
    if not (root / ".git").is_dir():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
