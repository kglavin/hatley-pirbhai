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
    hints, routes / topics, and one-line evidence."""
    out: list[BoundaryCandidate] = []
    for f in scan.files:
        if not f.is_significant or f.hp_role_hint != HpRoleHint.BOUNDARY:
            continue
        abs_path = codebase_root / f.path
        content = _read_head(abs_path)
        cand = BoundaryCandidate(path=f.path)
        if content:
            cand.kind_hint = _detect_kind(content)
            cand.routes = _extract_routes(content)
            cand.topics = _extract_topics(content)
            cand.evidence = _gather_evidence(content)
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
    parser = argparse.ArgumentParser(
        prog="hp_boundary_candidates",
        description="Extract Stage-1 boundary candidates from scan.json.",
    )
    parser.add_argument("--scan",   required=True, help="Path to intermediate/scan.json")
    parser.add_argument("--codebase", required=True, help="Codebase root (for re-reading file content)")
    parser.add_argument("--output", required=True, help="Output path for boundary-candidates.json")
    args = parser.parse_args(argv)

    scan_data = json.loads(Path(args.scan).read_text())
    scan = ProjectScan.model_validate(scan_data)
    candidates = extract_candidates(scan, Path(args.codebase))
    write_candidates(candidates, Path(args.output))
    print(f"wrote {args.output} ({len(candidates.boundary_files)} boundary candidates)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
