"""Append-only progress log — `intermediate/progress.log`.

Every ingest agent (Python scripts + LLM subagents) appends timestamped
START / DONE lines. An external observer can `tail -f intermediate/progress.log`
to watch the run live. The `--resume` flag (in scripts/hp_ingest.py) reads
this log to determine which stages have already completed.

Per locked tuning Q3: augment stderr; don't replace it. Scripts continue to
print human-readable output to stderr/stdout; progress.log is the
machine-readable structured tail.

Format: one event per line, key=value separated by spaces.

    2026-05-24T19:32:14Z START   stage=0 agent=hp-ingest-scan
    2026-05-24T19:33:42Z DONE    stage=0 agent=hp-ingest-scan files=4012 significant=1551
    2026-05-24T19:34:01Z START   stage=1-prep agent=boundary_candidates
    2026-05-24T19:34:03Z DONE    stage=1-prep agent=boundary_candidates count=50

Conventions:
- `stage` matches the design doc taxonomy: 0 / 1-prep / 1 / 2-prep / 2 /
  3-prep / 3-4 / 5-prep / 5 / merge / review / emit.
- `agent` is the Python module or LLM skill name.
- Free-form key=value pairs after that — counts, durations, paths.
- Use ISO-8601 UTC timestamps with seconds precision.

Concurrency: each call opens-appends-closes. Safe across parallel agent
dispatch (each parallel hp-ingest-leaf invocation writes its own line).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def log_event(intermediate_dir: Path, event: str, *, stage: str, agent: str, **fields: Any) -> None:
    """Append a single event line to `<intermediate_dir>/progress.log`.

    `event` is conventionally `START`, `DONE`, `SKIP`, `WARN`, `HINT_LOADED`,
    or `PAUSED`. `stage` + `agent` are required; everything else is free-form
    key=value pairs."""
    intermediate_dir = Path(intermediate_dir)
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    log_path = intermediate_dir / "progress.log"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [ts, f"{event:8s}", f"stage={stage}", f"agent={agent}"]
    for k, v in fields.items():
        parts.append(f"{k}={_format_value(v)}")
    line = " ".join(parts) + "\n"

    # Open-append-close per call so parallel writers don't trample each other.
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def log_start(intermediate_dir: Path, *, stage: str, agent: str, **fields: Any) -> None:
    log_event(intermediate_dir, "START", stage=stage, agent=agent, **fields)


def log_done(intermediate_dir: Path, *, stage: str, agent: str, **fields: Any) -> None:
    log_event(intermediate_dir, "DONE", stage=stage, agent=agent, **fields)


def log_skip(intermediate_dir: Path, *, stage: str, agent: str, reason: str, **fields: Any) -> None:
    """Emitted by --resume when a stage's output already exists on disk."""
    log_event(intermediate_dir, "SKIP", stage=stage, agent=agent, reason=reason, **fields)


def read_completed_stages(intermediate_dir: Path) -> set[str]:
    """Return the set of (stage, agent) tuples represented as 'stage:agent' that
    have a DONE event in progress.log.

    Used as one input to `--resume` skip logic (the other is checking that
    each stage's output JSON actually exists + parses)."""
    log_path = Path(intermediate_dir) / "progress.log"
    if not log_path.exists():
        return set()
    completed: set[str] = set()
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if " DONE " not in line:
            continue
        # Parse trailing key=value pairs
        stage = agent = None
        for tok in line.split():
            if tok.startswith("stage="):
                stage = tok[len("stage="):]
            elif tok.startswith("agent="):
                agent = tok[len("agent="):]
        if stage and agent:
            completed.add(f"{stage}:{agent}")
    return completed


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

def _format_value(v: Any) -> str:
    """Render a value for the log. Avoid spaces inside values so the line
    parses unambiguously as space-separated key=value pairs."""
    s = str(v)
    if " " in s:
        return s.replace(" ", "_")
    return s
