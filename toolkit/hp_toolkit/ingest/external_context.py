# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""External-context loader for `<project-dir>/external-context/<category>/*`.

Per locked tuning H.8: every non-trivial system has architectural context
that lives outside the source tree — QA test plans in Confluence, ADRs in
a wiki, stakeholder requirement docs, operational runbooks. hp-ingest's
walker can't reach those; instead the user pastes them into a structured
drop directory before (or during) the run.

This is *evidence* the user provides; distinct from `intermediate/hints/`
which is *guidance* the architect drops to steer agents. Different intent,
same file-drop ergonomics.

Layout:

    <project-dir>/external-context/
    ├── qa-test-plans/        → feeds Stage 1 (boundary) + Stage 4 (leaf-PSPEC)
    ├── adrs/                 → feeds Stage 5 (architect) + Stage 2 (processes)
    ├── requirements/         → feeds Stage 1 (boundary)
    ├── design-docs/          → feeds Stage 5 (architect)
    ├── runbooks/             → not consumed by core ingest; surfaces in ingest-report.md
    ├── glossary/             → feeds Stage 2-glossary (T7) + every naming agent
    └── README.md             → walks the user through the categories

Each agent loads its category-filtered slice via `files_for_stage(...)`.
Loaded files are recorded in IR `provenance.external_context_used` so the
architect can audit which entities derived from which external doc.

By design the directory lives under `<project-dir>/` (user-managed,
optionally gitignored), not `<project-dir>/intermediate/` (auto-managed).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Iterable


EXTERNAL_CONTEXT_DIRNAME = "external-context"


class ExternalContextCategory(str, Enum):
    """The categories the user is invited to drop content into.

    The directory name on disk is the value of the enum; the matching is
    case-sensitive and exact. Extra subdirectories under
    `external-context/` are tolerated but not consumed by any stage (the
    user can stash personal notes; the orchestrator surfaces them in
    ingest-report.md as 'uncategorized')."""

    QA_TEST_PLANS = "qa-test-plans"
    ADRS = "adrs"
    REQUIREMENTS = "requirements"
    DESIGN_DOCS = "design-docs"
    RUNBOOKS = "runbooks"
    GLOSSARY = "glossary"


_STAGE_CATEGORIES: dict[str, tuple[ExternalContextCategory, ...]] = {
    # Per H.8.c. Each stage gets a tuple of categories whose contents it
    # should read (concatenated) before producing its output.
    "boundary": (
        ExternalContextCategory.QA_TEST_PLANS,
        ExternalContextCategory.REQUIREMENTS,
    ),
    "processes": (
        ExternalContextCategory.QA_TEST_PLANS,
        ExternalContextCategory.ADRS,
    ),
    "leaf": (
        ExternalContextCategory.QA_TEST_PLANS,
    ),
    "architect": (
        ExternalContextCategory.ADRS,
        ExternalContextCategory.DESIGN_DOCS,
    ),
    "review": (),  # reviewer audits IR — doesn't re-read external context
    # Glossary extractor (T7) consumes ExternalContextCategory.GLOSSARY
    # directly; not via stage dispatch.
}


_README_STUB = """\
# External context for hp-ingest

Drop architectural context that lives outside the codebase here, organized
by category. hp-ingest will feed the relevant slice to each agent.

This is **evidence** — QA plans, ADRs, requirements docs, glossaries —
distinct from `../intermediate/hints/` which is **guidance** from a
live observer steering a stage.

## Categories

| Directory | Who reads it | What to drop |
|---|---|---|
| `qa-test-plans/` | Stage 1 boundary + Stage 4 PSPEC | Acceptance criteria, test plans (any format — paste as markdown) |
| `adrs/` | Stage 2 processes + Stage 5 architect | Architecture decision records, exported from wiki / confluence / etc. |
| `requirements/` | Stage 1 boundary | Stakeholder briefs, requirements docs |
| `design-docs/` | Stage 5 architect | Design memos, architecture proposals not committed to the repo |
| `runbooks/` | Surfaced in ingest-report.md (not consumed directly) | Operational runbooks — informs modernization-layer work post-ingest |
| `glossary/` | Glossary extractor + every naming agent | Domain vocabulary documents |

Subdirectories outside these names are tolerated but not consumed.

## Filename conventions

Anything readable as text (markdown preferred, plain text and HTML
exports are also fine). Long files are passed through verbatim — the
agent reads them, no truncation. Token cost rises with content volume,
so keep what you drop substantive + targeted.

## Auditing

Every IR entity that drew on external context records the source path
in its `provenance.external_context_used` array, so you can trace back
which entities derived from which doc.

## Should this be committed?

By default, gitignored — external-context often contains org-internal
material the user doesn't want in the repo. Override per-project if you
do want to commit (the directory itself isn't gitignored globally; the
`.gitignore` rule the orchestrator suggests is project-local).
"""


def external_context_dir(project_dir: Path) -> Path:
    return Path(project_dir) / EXTERNAL_CONTEXT_DIRNAME


def ensure_external_context_dir(project_dir: Path) -> Path:
    """Create the external-context directory tree + drop the README stub.

    Creates the top-level directory + one subdirectory per known
    category, each empty. Drops a README at the top. Idempotent — safe
    to call on every run."""
    base = external_context_dir(project_dir)
    base.mkdir(parents=True, exist_ok=True)
    for cat in ExternalContextCategory:
        (base / cat.value).mkdir(exist_ok=True)
    readme = base / "README.md"
    if not readme.exists():
        readme.write_text(_README_STUB)
    return base


def list_for_category(project_dir: Path, category: ExternalContextCategory) -> list[Path]:
    """All readable files under `external-context/<category>/`.

    Skips dot-files and the directory's own README. Returns sorted by
    path for stable output across runs."""
    cat_dir = external_context_dir(project_dir) / category.value
    if not cat_dir.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(cat_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        if p.name == "README.md" and p.parent == cat_dir:
            continue
        out.append(p)
    return out


def list_for_stage(project_dir: Path, stage: str) -> list[Path]:
    """All files an agent at `stage` should read, concatenated across the
    categories that stage consumes (per `_STAGE_CATEGORIES`)."""
    cats = _STAGE_CATEGORIES.get(stage, ())
    out: list[Path] = []
    for cat in cats:
        out.extend(list_for_category(project_dir, cat))
    return out


def categories_for_stage(stage: str) -> tuple[ExternalContextCategory, ...]:
    return _STAGE_CATEGORIES.get(stage, ())


def summarize_presence(project_dir: Path) -> dict[str, int]:
    """Map category-name → file-count. Empty/missing categories are 0.

    Used for the orchestrator's "what's been dropped?" surface."""
    out: dict[str, int] = {}
    for cat in ExternalContextCategory:
        out[cat.value] = len(list_for_category(project_dir, cat))
    return out


def has_any_content(project_dir: Path) -> bool:
    """True if at least one file (excluding READMEs) exists in any
    category. Used by the orchestrator to decide whether to mention
    external-context to the user."""
    return any(v > 0 for v in summarize_presence(project_dir).values())
