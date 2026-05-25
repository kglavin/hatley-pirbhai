"""Makefile + Justfile recipe parser (Kevin's T8 follow-up question).

Per the tuning discussion at T8: Makefile / Justfile recipes carry
several kinds of architectural signal the deep-deployment-parser arc
(T8 H.5) missed:

- **`deploy` / `up` / `migrate` / `seed` targets** = deployment recipes
  (Stage 5 signal — alongside compose/k8s)
- **`run-<service>` / `start-<service>` targets** = boundary CLI entry
  points (Stage 1 signal)
- **`# comment above target`** = architect-facing rationale prose
- **Recipe bodies** = the project's canonical operational commands

Both Make + Just use the same target/recipe structure (target name,
optional prereqs/args, body commands), so one parser handles both via
a `kind:` field. Detection is filename-based: `Makefile` /
`*.makefile` / `*.mk` → make; `justfile` / `Justfile` / `*.just` →
just.

Output: `intermediate/recipes.json` — read by `hp-ingest-architect`
(deployment recipes), `hp-ingest-boundary` (run-target CLI entries),
and surfaced in `ingest-report.md`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .scan import _enumerate_files


# Maximum lines to keep in `body_preview` per recipe — enough to surface
# the canonical commands without dumping a 100-line release script.
_MAX_BODY_LINES = 5

# Cap the recipe-source-comment block at ~400 chars; longer narrative
# belongs in a README, not adjacent to a target.
_MAX_COMMENT_BYTES = 400


# Categorization by target-name keyword. First match wins; order matters
# (deploy > publish > release for the same category, but they're
# independent here so any-order is fine for this set).
_TARGET_CATEGORIES: list[tuple[str, re.Pattern[str]]] = [
    ("deploy",   re.compile(r"^(deploy|publish|ship|release|rollout|promote)\b", re.IGNORECASE)),
    ("up",       re.compile(r"^(up|start|launch|dev|serve|run(?:-\w+)?)\b", re.IGNORECASE)),
    ("build",    re.compile(r"^(build|compile|package|bundle|dist)\b", re.IGNORECASE)),
    ("test",     re.compile(r"^(test|check|lint|verify|validate|coverage)\b", re.IGNORECASE)),
    ("migrate",  re.compile(r"^(migrate|migration|db[-_]?(?:up|migrate|seed))\b", re.IGNORECASE)),
    ("setup",    re.compile(r"^(setup|install|bootstrap|init|configure|prep)\b", re.IGNORECASE)),
    ("clean",    re.compile(r"^(clean|wipe|clear|reset|teardown|down|stop)\b", re.IGNORECASE)),
    ("docs",     re.compile(r"^(docs?|generate[-_]docs|render)\b", re.IGNORECASE)),
]


# ─────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────

class Recipe(BaseModel):
    """One target / recipe extracted from a Make or Just file."""

    source_file: str
    kind: Literal["make", "just"]
    target: str
    category: str = "other"                   # deploy / up / build / test / migrate / setup / clean / docs / other
    prereqs: list[str] = Field(default_factory=list)
    comment: Optional[str] = None             # `# ...` block immediately above the target line
    body_preview: list[str] = Field(default_factory=list)


class RecipeHarvest(BaseModel):
    """`intermediate/recipes.json` shape."""

    recipes: list[Recipe] = Field(default_factory=list)

    def by_category(self, category: str) -> list[Recipe]:
        return [r for r in self.recipes if r.category == category]


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def gather(codebase_root: Path) -> RecipeHarvest:
    """Walk the codebase + parse every Makefile / Justfile found."""
    root = codebase_root.resolve()
    out = RecipeHarvest()
    for f in _enumerate_files(root):
        try:
            rel = f.relative_to(root)
        except ValueError:
            continue
        rel_path = rel.as_posix()
        kind = _detect_kind(rel_path)
        if kind is None:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parsed = _parse(rel_path, kind, content)
        out.recipes.extend(parsed)
    return out


def write_harvest(harvest: RecipeHarvest, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(harvest.model_dump_json(indent=2))


def load_harvest(path: Path) -> RecipeHarvest:
    return RecipeHarvest.model_validate_json(Path(path).read_text())


# ─────────────────────────────────────────────────────────────────────
# Internals — file-type detection
# ─────────────────────────────────────────────────────────────────────

def _detect_kind(rel_path: str) -> Optional[Literal["make", "just"]]:
    """Return 'make' / 'just' / None for the given file path."""
    name = Path(rel_path).name.lower()
    if name in {"makefile", "gnumakefile"} or name.endswith((".mk", ".makefile")):
        return "make"
    if name in {"justfile"} or name.endswith(".just"):
        return "just"
    return None


# ─────────────────────────────────────────────────────────────────────
# Internals — target extraction
# ─────────────────────────────────────────────────────────────────────

# Make target line: `target: prereqs` at column 0. Excludes lines starting
# with whitespace (those are recipe body) and lines containing `=` before
# the colon (those are variable assignments, not targets).
_MAKE_TARGET = re.compile(
    r"^([\w./-]+)\s*:(?!=)\s*(.*)$",
    re.MULTILINE,
)
# Variable-assignment patterns we exclude
_MAKE_VAR_ASSIGN = re.compile(r"^[\w./-]+\s*[:?]?=")

# Justfile target: `target arg1 arg2:` at column 0 (no tabs/spaces).
# Just uses 4-space indent for body, not tabs.
_JUST_TARGET = re.compile(
    r"^([\w-]+)(?:\s+(?:[\w-]+(?:\s+[\w-]+)*))?\s*:\s*$",
    re.MULTILINE,
)


def _parse(rel_path: str, kind: Literal["make", "just"], content: str) -> list[Recipe]:
    if kind == "make":
        return _parse_make(rel_path, content)
    return _parse_just(rel_path, content)


def _parse_make(rel_path: str, content: str) -> list[Recipe]:
    out: list[Recipe] = []
    lines = content.splitlines()
    seen_targets: set[str] = set()
    for i, line in enumerate(lines):
        m = _MAKE_TARGET.match(line)
        if not m:
            continue
        if _MAKE_VAR_ASSIGN.match(line):
            continue
        target = m.group(1)
        # Skip phony targets that are too generic (`PHONY:`, `.SUFFIXES:`)
        # and special variable-prefixed targets
        if target.startswith(".") and not target.startswith("./"):
            continue
        if target in seen_targets:
            continue
        seen_targets.add(target)

        prereqs_raw = m.group(2).strip()
        prereqs = [p for p in prereqs_raw.split() if p] if prereqs_raw else []
        comment = _comment_above(lines, i)
        body_preview = _body_below(lines, i, kind="make")
        out.append(Recipe(
            source_file=rel_path,
            kind="make",
            target=target,
            category=_categorize(target),
            prereqs=prereqs,
            comment=comment,
            body_preview=body_preview,
        ))
    return out


def _parse_just(rel_path: str, content: str) -> list[Recipe]:
    out: list[Recipe] = []
    lines = content.splitlines()
    seen_targets: set[str] = set()
    for i, line in enumerate(lines):
        m = _JUST_TARGET.match(line)
        if not m:
            continue
        # Skip lines that are actually variable assignments
        # (just supports `name := value` syntax which the regex above
        # won't match, but bare `key: value` could be either)
        if " := " in line or " = " in line:
            continue
        target = m.group(1)
        # Skip generic targets that aren't useful
        if target in {"default", "_default"}:
            continue
        if target in seen_targets:
            continue
        seen_targets.add(target)

        comment = _comment_above(lines, i)
        body_preview = _body_below(lines, i, kind="just")
        out.append(Recipe(
            source_file=rel_path,
            kind="just",
            target=target,
            category=_categorize(target),
            comment=comment,
            body_preview=body_preview,
        ))
    return out


def _comment_above(lines: list[str], idx: int) -> Optional[str]:
    """Collect the contiguous block of `# comment` lines immediately
    above `idx`. Stops at blank lines or non-comment lines."""
    out: list[str] = []
    j = idx - 1
    while j >= 0:
        stripped = lines[j].lstrip()
        if not stripped:
            break
        if not stripped.startswith("#"):
            break
        text = stripped.lstrip("#").lstrip()
        out.insert(0, text)
        j -= 1
    if not out:
        return None
    joined = "\n".join(out).strip()
    if len(joined) > _MAX_COMMENT_BYTES:
        joined = joined[:_MAX_COMMENT_BYTES] + "…"
    return joined or None


def _body_below(lines: list[str], idx: int, *, kind: str) -> list[str]:
    """Capture the first N non-comment recipe body lines after `idx`.

    Make recipes use TAB-prefixed lines for body; Just uses indented
    spaces (typically 4)."""
    out: list[str] = []
    for line in lines[idx + 1:]:
        if not line:
            continue
        if kind == "make":
            if not line.startswith("\t"):
                break
            text = line.lstrip("\t").strip()
        else:                   # just
            if not (line.startswith("    ") or line.startswith("\t")):
                break
            text = line.strip()
        if not text or text.startswith("#"):
            continue
        # Strip leading prefix decorators: `@` (silent), `-` (ignore err)
        text = text.lstrip("@-").strip()
        out.append(text)
        if len(out) >= _MAX_BODY_LINES:
            break
    return out


def _categorize(target: str) -> str:
    for cat, pat in _TARGET_CATEGORIES:
        if pat.search(target):
            return cat
    return "other"


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def _main() -> None:
    import argparse
    from collections import Counter

    from .progress_log import log_done, log_start

    parser = argparse.ArgumentParser(description="Parse Makefile + Justfile recipes (T9.c).")
    parser.add_argument("--codebase", required=True, help="Codebase root")
    parser.add_argument("--output", "-o", required=True, help="Where to write recipes.json")
    args = parser.parse_args()

    out_path = Path(args.output)
    intermediate_dir = out_path.parent
    log_start(intermediate_dir, stage="0-recipes", agent="recipe_parser")

    harvest = gather(Path(args.codebase))
    write_harvest(harvest, out_path)

    by_cat = Counter(r.category for r in harvest.recipes)
    log_done(intermediate_dir, stage="0-recipes", agent="recipe_parser",
             recipes=len(harvest.recipes),
             **{k: v for k, v in by_cat.items() if v})
    print(json.dumps({
        "recipes": len(harvest.recipes),
        "by_category": dict(by_cat),
    }, indent=2))


if __name__ == "__main__":
    _main()
