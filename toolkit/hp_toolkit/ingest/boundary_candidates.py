# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Stage 1 candidate extractor — surfaces Stage-1 boundary candidates from
the Stage-0 scan output.

Pure Python, no LLM. Reads `intermediate/scan.json`, filters to files with
`hp_role_hint == boundary`, and for each one detects what *kind* of boundary
(HTTP server, CLI entry, message-bus consumer, etc.) from a small set of
content patterns. Emits `intermediate/boundary-candidates.json` — the input
to the `hp-ingest-boundary` LLM agent.

The LLM agent then decides which candidates correspond to real Stage-1
terminators, names them, and draws boundary flows.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .schema import HpRoleHint, ProjectScan


# Per-kind detection: each entry yields a tuple (kind_label, regex) that
# detects a particular boundary subtype. Order matters — more specific
# kinds before more general.

_BOUNDARY_KIND_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("http_server",        re.compile(r"\b(FastAPI|fastapi|flask\.Flask|express\s*\(\)|Axum|axum::Router|axum::serve|actix_web|rocket|gin\.(New|Default)|http\.ListenAndServe)\b")),
    ("grpc_server",        re.compile(r"\b(grpc\.NewServer|tonic::transport::Server)\b")),
    ("websocket_server",   re.compile(r"\b(WebSocketServer|ws\.Server|tokio_tungstenite::accept_async)\b")),
    ("cli_entry",          re.compile(r"\b(clap::Parser|argparse\.ArgumentParser|click\.command|cobra\.(Command|Execute))\b")),
    ("kafka_consumer",     re.compile(r"\b(KafkaConsumer|AIOKafkaConsumer|kafka_consumer)\b")),
    ("sqs_consumer",       re.compile(r"\b(SQS|sqs)\.receive_message|@sqs_listener\b")),
    ("nats_consumer",      re.compile(r"\b(nats|NATS)\.subscribe\b")),
    ("cron_scheduler",     re.compile(r"\b(cron|schedule|APScheduler)\.|@cron|@scheduled\b")),
    ("file_watcher",       re.compile(r"\b(inotify\.|fs\.watch|fsnotify\.NewWatcher)\b")),
    # ── Embedded / firmware kinds (per EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding B) ──
    # Ordered most-specific first so the right kind wins per file.
    ("hw_peripheral_pwm",      re.compile(r"\bHAL_TIM_PWM_(Start|Init)(_IT|_DMA)?\b")),
    ("hw_peripheral_gpio",     re.compile(r"\bHAL_GPIO_(EXTI_Callback|EXTI_IRQHandler|WritePin|ReadPin)\b")),
    ("hw_peripheral_timer",    re.compile(r"\bHAL_TIM_(Base_Init|Base_Start|IRQHandler|OC_Start)(_IT|_DMA)?\b")),
    ("hw_peripheral_uart",     re.compile(r"\bHAL_(UART|USART)_(Init|Receive_IT|Transmit_IT|Receive_DMA|Transmit_DMA)\b")),
    ("hw_peripheral_i2c",      re.compile(r"\bHAL_I2C_(Init|Master_Receive|Master_Transmit|Mem_Read|Mem_Write)(_IT|_DMA)?\b")),
    ("hw_peripheral_spi",      re.compile(r"\bHAL_SPI_(Init|TransmitReceive|Receive|Transmit)(_IT|_DMA)?\b")),
    ("hw_peripheral_can",      re.compile(r"\bHAL_CAN_(Start|AddTxMessage|GetRxMessage|Init)\b")),
    ("hw_peripheral_adc",      re.compile(r"\bHAL_ADC_(Init|Start|GetValue|Start_IT|Start_DMA)\b")),
    ("hw_peripheral_zephyr",   re.compile(r"\b(device_get_binding\s*\(|DEVICE_DT_GET\s*\()")),
    ("hw_peripheral_nuttx",    re.compile(r"\b(px4_arch_[a-z_]+|board_app_initialize)\b")),
    ("mavlink_endpoint",       re.compile(r"\bmavlink_msg_[a-z0-9_]+_(pack|encode|decode)\b")),
    ("dds_endpoint",           re.compile(r"\bdds_create_(writer|reader|topic|participant)\b")),
    ("ros2_publisher",         re.compile(r"\b(rclcpp::create_publisher|rcl_publisher_init\w*|rclc_publisher_init\w*)\b")),
    ("ros2_subscriber",        re.compile(r"\b(rclcpp::create_subscription|rcl_subscription_init\w*|rclc_subscription_init\w*)\b")),
    ("ros2_service",           re.compile(r"\b(rclcpp::create_service|rclcpp::create_client|rcl_service_init\w*|rclc_service_init\w*|rcl_client_init\w*)\b")),
    ("uorb_publisher",         re.compile(r"\borb_advertise\b")),
    ("uorb_subscriber",        re.compile(r"\borb_subscribe\b")),
    ("nsh_command",            re.compile(r"\b(NSH_DECLARE_BUILTIN|nsh_builtin)\b")),
]


# Route / endpoint extractors per HTTP framework. These produce hints about
# what external clients will touch the boundary — useful for terminator naming.
_HTTP_ROUTE_PATTERNS = [
    # FastAPI: @app.get("/path"), @app.post(...)
    re.compile(r"@\w+\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]"),
    # Flask: @app.route("/path", methods=["GET"])
    re.compile(r"@\w+\.route\(['\"]([^'\"]+)['\"]"),
    # Express: app.get("/path", ...)
    re.compile(r"\b\w+\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]"),
    # Gin / Echo / Chi: r.GET("/path", ...)
    re.compile(r"\b\w+\.(GET|POST|PUT|DELETE|PATCH)\(['\"]([^'\"]+)['\"]"),
    # Axum: .route("/path", ...)
    re.compile(r"\.route\(['\"]([^'\"]+)['\"]"),
]


# Topic / queue name extractors
_TOPIC_PATTERNS = [
    re.compile(r"\.subscribe\(['\"]([^'\"]+)['\"]"),
    re.compile(r"topic\s*=\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"QueueName\s*=\s*['\"]([^'\"]+)['\"]"),
    # ── Embedded topic / endpoint extractors (per EMBEDDED_FIRMWARE_TUNING_DESIGN.md B) ──
    # ROS 2: `create_publisher<Type>("/topic_name", ...)`
    re.compile(r"\.create_(?:publisher|subscription)\s*<[^>]+>\s*\(\s*['\"]([^'\"]+)['\"]"),
    # Micro-ROS: `rclc_publisher_init_default(&pub, &node, type_support, "topic_name")`
    # The args wrap across newlines + the type-support arg uses macros
    # that contain their own commas (ROSIDL_GET_MSG_TYPE_SUPPORT(...)).
    # Capture by lazy-matching up to the first quoted string after the
    # `(` — the topic-name literal is typically the only string in the call.
    re.compile(r"\brcl[c]?_(?:publisher|subscription)_init\w*\s*\([^\"]*?['\"]([^'\"]+)['\"]", re.DOTALL),
    # uORB: `orb_advertise(ORB_ID(<topic>), ...)` — topic is an ORB_ID(...) macro
    re.compile(r"\b(?:orb_advertise|orb_subscribe)\s*\(\s*ORB_ID\s*\(\s*(\w+)\s*\)"),
    # MAVLink: `mavlink_msg_<MSGNAME>_pack(...)` — the message name IS the surface
    re.compile(r"\bmavlink_msg_([a-z0-9_]+)_(?:pack|encode|decode)\b"),
    # DDS: `dds_create_topic(participant, &TYPE_desc, "topic_name", ...)`
    re.compile(r"\bdds_create_topic\s*\([^,]+,[^,]+,\s*['\"]([^'\"]+)['\"]"),
]


# ─────────────────────────────────────────────────────────────────────
# Candidate schema
# ─────────────────────────────────────────────────────────────────────

class BoundaryCandidate(BaseModel):
    """One boundary file with the kind hint + extracted evidence the LLM will
    use to decide whether it's a real Stage-1 terminator."""

    path: str
    kind_hint: Optional[str] = None
    routes: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class BoundaryCandidates(BaseModel):
    """`intermediate/boundary-candidates.json` shape."""

    boundary_files: list[BoundaryCandidate] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Extraction
# ─────────────────────────────────────────────────────────────────────

def extract_candidates(scan: ProjectScan, codebase_root: Path) -> BoundaryCandidates:
    """Walk the scan output, build per-boundary-file candidates with kind
    hints, routes / topics, and one-line evidence.

    Per EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding B: firmware files often
    mix concerns — a single `app.cpp` may contain the state machine AND
    the Micro-ROS pub/sub surface. The role classifier returns ONE hint
    per file (state-machine wins over boundary), so a strict
    boundary-only loop would miss the comm surface. We also scan
    state-machine + pure-logic files for embedded boundary patterns +
    surface them as candidates when a match fires."""
    out: list[BoundaryCandidate] = []
    seen_paths: set[str] = set()
    for f in scan.files:
        if not f.is_significant:
            continue
        if f.hp_role_hint == HpRoleHint.BOUNDARY:
            scan_for_embedded = False
        elif f.hp_role_hint in (HpRoleHint.STATE_MACHINE, HpRoleHint.PURE_LOGIC):
            # Embedded-mixed-concern path: only surface if the file
            # contains an embedded boundary kind we recognize.
            scan_for_embedded = True
        else:
            continue
        abs_path = codebase_root / f.path
        content = _read_head(abs_path)
        if scan_for_embedded:
            if content is None:
                continue
            embedded_kind = _detect_kind(content)
            if embedded_kind is None or not embedded_kind.startswith(("hw_peripheral_", "ros2_", "uorb_", "mavlink_", "dds_", "nsh_")):
                # No embedded boundary signal in this state-machine /
                # pure-logic file — leave it for Stage 2 to handle.
                continue
        cand = BoundaryCandidate(path=f.path)
        if content:
            cand.kind_hint = _detect_kind(content)
            cand.routes = _extract_routes(content)
            cand.topics = _extract_topics(content)
            cand.evidence = _gather_evidence(content)
        if f.path in seen_paths:
            continue
        seen_paths.add(f.path)
        out.append(cand)
    return BoundaryCandidates(boundary_files=out)


def write_candidates(c: BoundaryCandidates, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(c.model_dump_json(indent=2))


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

_MAX_HEAD = 16 * 1024


def _read_head(path: Path) -> Optional[str]:
    try:
        with path.open("rb") as fh:
            head = fh.read(_MAX_HEAD)
        if b"\x00" in head:
            return None
        return head.decode("utf-8", errors="replace")
    except (OSError, PermissionError):
        return None


def _detect_kind(content: str) -> Optional[str]:
    for label, pat in _BOUNDARY_KIND_PATTERNS:
        if pat.search(content):
            return label
    return None


def _extract_routes(content: str) -> list[str]:
    found: list[str] = []
    for pat in _HTTP_ROUTE_PATTERNS:
        for m in pat.finditer(content):
            # The path is whichever group is non-empty (route patterns vary)
            for group in m.groups():
                if group and group.startswith("/"):
                    found.append(group)
                    break
    # De-dupe preserving order
    seen: set[str] = set()
    return [x for x in found if not (x in seen or seen.add(x))][:30]


def _extract_topics(content: str) -> list[str]:
    found: list[str] = []
    for pat in _TOPIC_PATTERNS:
        for m in pat.finditer(content):
            for group in m.groups():
                if group:
                    found.append(group)
                    break
    seen: set[str] = set()
    return [x for x in found if not (x in seen or seen.add(x))][:30]


def _gather_evidence(content: str) -> list[str]:
    """Return up to 5 distinct lines from the file head that contain the
    matched patterns — useful for the LLM agent to verify the classifier."""
    matched_lines: list[str] = []
    for label, pat in _BOUNDARY_KIND_PATTERNS:
        for m in pat.finditer(content):
            # Find the line containing the match
            start = content.rfind("\n", 0, m.start()) + 1
            end = content.find("\n", m.end())
            if end < 0:
                end = len(content)
            line = content[start:end].strip()
            if line and line not in matched_lines:
                matched_lines.append(line)
            if len(matched_lines) >= 5:
                return matched_lines
    return matched_lines


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def _main(argv: Optional[list[str]] = None) -> int:
    import argparse
    from .progress_log import log_done, log_start
    parser = argparse.ArgumentParser(
        prog="hp_boundary_candidates",
        description="Extract Stage-1 boundary candidates from scan.json.",
    )
    parser.add_argument("--scan",   required=True, help="Path to intermediate/scan.json")
    parser.add_argument("--codebase", required=True, help="Codebase root (for re-reading file content)")
    parser.add_argument("--output", required=True, help="Output path for boundary-candidates.json")
    args = parser.parse_args(argv)

    intermediate = Path(args.output).parent
    log_start(intermediate, stage="1-prep", agent="boundary_candidates")

    scan_data = json.loads(Path(args.scan).read_text())
    scan = ProjectScan.model_validate(scan_data)
    candidates = extract_candidates(scan, Path(args.codebase))
    write_candidates(candidates, Path(args.output))
    print(f"wrote {args.output} ({len(candidates.boundary_files)} boundary candidates)")

    log_done(intermediate, stage="1-prep", agent="boundary_candidates",
             count=len(candidates.boundary_files))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
