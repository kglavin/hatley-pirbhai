# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Architect-in-the-loop hints for `intermediate/hints/<stage>.md`.

Per locked tuning F.3.a: an observer watching `intermediate/progress.log`
can see a stage going off-course (e.g. Stage 2 emitting 30 over-fragmented
processes when 8 was right) and drop a hint file that subsequent stages
read before they emit.

The hint files are *guidance* (what the architect wants you to do
differently) — distinct from `external-context/` which is *evidence*
(QA plans, ADRs, requirements docs the user has). Different intent, same
file-drop ergonomics.

Stage naming convention (matches the progress-log taxonomy):

    intermediate/hints/boundary.md            → hp-ingest-boundary
    intermediate/hints/processes.md           → hp-ingest-processes
    intermediate/hints/leaf.md                → applies to every hp-ingest-leaf
    intermediate/hints/leaf-<process-id>.md   → just this one leaf
    intermediate/hints/architect.md           → hp-ingest-architect
    intermediate/hints/review.md              → hp-ingest-review

When an agent loads a hint, it should append a `HINT_LOADED` event to
progress.log so observers can confirm their guidance was picked up.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


HINTS_DIRNAME = "hints"


_KNOWN_STAGES = (
    "boundary",
    "processes",
    "leaf",
    "architect",
    "review",
)


_README_STUB = """\
# hp-ingest hints

Drop markdown files here to give the next-running agent architectural
guidance it MUST honor before emitting its output.

This is the **architect-in-the-loop** steering loop — distinct from
`../external-context/` (which is *evidence* — QA plans / ADRs / etc.
the user wants the agents to read).

## Filenames

One file per stage you want to influence. Conventions:

    boundary.md            → hp-ingest-boundary (Stage 1)
    processes.md           → hp-ingest-processes (Stage 2)
    leaf.md                → applies to every parallel hp-ingest-leaf
    leaf-<process-id>.md   → just this one leaf invocation
    architect.md           → hp-ingest-architect (Stage 5)
    review.md              → hp-ingest-review (final)

## When to drop a hint

While watching `../progress.log` (tail -f). If Stage 2 emits 30 process
candidates and you wanted 8, drop `processes.md` with guidance like:

    Cluster at services/<svc> rather than per-file; collapse
    api/handlers/* into the owning service's process. Aim for ≤10
    Stage-2 processes total.

The next stage to fire after your drop will pick it up; earlier
completed stages won't re-run automatically (use --resume after deleting
their JSON if you want to re-run them with hints applied).

## What the agent does with the hint

Each agent's skill markdown is taught to read its stage's hint file at
the start of its run, before any other inputs. The hint is treated as
binding guidance — if it conflicts with what the agent would have
inferred from code, the hint wins.

Each loaded hint produces a `HINT_LOADED` event in progress.log so you
can confirm your guidance was picked up.
"""


def hints_dir(intermediate_dir: Path) -> Path:
    return Path(intermediate_dir) / HINTS_DIRNAME


def ensure_hints_dir(intermediate_dir: Path) -> Path:
    """Create the hints directory + drop the README stub if absent.

    Idempotent — safe to call on every run. Returns the directory path."""
    d = hints_dir(intermediate_dir)
    d.mkdir(parents=True, exist_ok=True)
    readme = d / "README.md"
    if not readme.exists():
        readme.write_text(_README_STUB)
    return d


def hint_path(intermediate_dir: Path, stage: str) -> Path:
    """Return the path the agent at `stage` should look for.

    Doesn't check existence — `load_hint` does that. Stage names follow
    the progress-log taxonomy; per-leaf hints use `leaf-<process-id>`."""
    return hints_dir(intermediate_dir) / f"{stage}.md"


def load_hint(intermediate_dir: Path, stage: str) -> Optional[str]:
    """Return the hint markdown for `stage` if present, else None.

    For leaf invocations, the caller should try `leaf-<process-id>` first
    and fall back to plain `leaf` for cross-leaf guidance."""
    p = hint_path(intermediate_dir, stage)
    if not p.exists():
        return None
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return None
    return text or None


def load_leaf_hint(intermediate_dir: Path, process_id: str) -> Optional[str]:
    """Per-leaf hint with fallback to the cross-leaf hint.

    Looks for `intermediate/hints/leaf-<process_id>.md`, then for the
    generic `leaf.md`. Returns the first found, or None."""
    specific = load_hint(intermediate_dir, f"leaf-{process_id}")
    if specific is not None:
        return specific
    return load_hint(intermediate_dir, "leaf")


def list_dropped_hints(intermediate_dir: Path) -> dict[str, Path]:
    """Map stage-name → path for every present hint file (excluding README).

    Used by orchestrators / reporting to tell the user what guidance is
    in flight. Stage name is the filename without `.md` extension."""
    d = hints_dir(intermediate_dir)
    if not d.exists():
        return {}
    out: dict[str, Path] = {}
    for p in sorted(d.glob("*.md")):
        if p.name == "README.md":
            continue
        out[p.stem] = p
    return out


def known_stages() -> tuple[str, ...]:
    return _KNOWN_STAGES
