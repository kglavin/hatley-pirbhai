"""hp-status — report what stages an HP project has reached, plus
validation, artifact freshness, and open questions.

Programmatic:
    from hp_toolkit.status import status_report
    report = status_report(Path("examples/solar"))
    print(report.format())

CLI:
    cd toolkit
    uv run python -m hp_toolkit.status <project-dir>
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .load import load
from .model import Project, EntityKind
from .validate import validate, ValidationReport


StageState = Literal["locked", "in_progress", "not_started", "n/a"]


@dataclass
class StageStatus:
    stage: int          # 1, 2, 3, 4, 5
    name: str
    state: StageState
    detail: str = ""    # short single-line explanation


@dataclass
class StatusReport:
    project_name: str
    project_dir: Path
    dictionary_exists: bool
    stages: list[StageStatus] = field(default_factory=list)
    validation: ValidationReport | None = None
    stale_artifacts: list[Path] = field(default_factory=list)   # generated files older than dictionary
    open_questions: dict[Path, int] = field(default_factory=dict)  # file → count of unchecked [ ]

    @property
    def ok(self) -> bool:
        return self.dictionary_exists and (self.validation is not None and self.validation.ok)

    def format(self) -> str:
        lines: list[str] = []
        lines.append(_color(f"=== {self.project_name} — Project Status ===", "1"))
        lines.append("")

        if not self.dictionary_exists:
            lines.append(_color(f"  ✗ No dictionary.yaml found in {self.project_dir}", "31"))
            lines.append(f"  Run: cd toolkit && uv run python scripts/hp_init.py <name>")
            return "\n".join(lines)

        lines.append(_color("Stages", "1"))
        for s in self.stages:
            icon = {
                "locked": _color("✅", "32"),
                "in_progress": _color("🟡", "33"),
                "not_started": "⬜",
                "n/a": "—",
            }[s.state]
            lines.append(f"  {icon} Stage {s.stage} — {s.name:30s} {s.detail}")
        lines.append("")

        if self.validation is not None:
            lines.append(_color("Validation", "1"))
            ok_str = _color("✅ no errors", "32") if self.validation.ok \
                else _color(f"✗ {len(self.validation.errors)} error(s)", "31")
            lines.append(f"  {ok_str}")
            for name, value in sorted(self.validation.metrics.items()):
                bar = "█" * int(value / 5) + "░" * (20 - int(value / 5))
                lines.append(f"  {name:34s} [{bar}] {value:5.1f}%")
            lines.append("")

        lines.append(_color("Artifact freshness", "1"))
        if self.stale_artifacts:
            lines.append(_color(f"  ⚠ {len(self.stale_artifacts)} artifact(s) older than dictionary.yaml:", "33"))
            for p in self.stale_artifacts:
                lines.append(f"    {p.relative_to(self.project_dir)}")
            lines.append(_color(f"  Run: cd toolkit && uv run python scripts/render_project.py {self.project_dir}", "36"))
        else:
            lines.append(_color("  ✅ all generated artifacts are fresh (or no generated artifacts exist yet)", "32"))
        lines.append("")

        lines.append(_color("Open questions (unchecked [ ] items in proposal/naming-review files)", "1"))
        if self.open_questions:
            for path, count in self.open_questions.items():
                lines.append(f"  {count:3d} in {path.relative_to(self.project_dir)}")
        else:
            lines.append(_color("  ✅ none — all reviewable decisions resolved", "32"))
        lines.append("")

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# Discovery logic
# ─────────────────────────────────────────────────────────────────────

_STATUS_LOCKED_RE = re.compile(r"^##\s*✅?\s*Status:\s*(Locked|Resolved)", re.MULTILINE | re.IGNORECASE)


def _is_locked(md_path: Path) -> bool:
    """A proposal / naming-review file is 'locked' if it has a top-level
    `## Status: Locked` (or `## Status: Resolved`) heading near the top."""
    if not md_path.exists():
        return False
    text = md_path.read_text()[:2000]  # first ~2KB is enough
    return bool(_STATUS_LOCKED_RE.search(text))


def _has_terminator(project: Project) -> bool:
    return any(e.kind == EntityKind.TERMINATOR for e in project.all_entities())


def _has_internal_processes(project: Project) -> bool:
    return any(
        e.kind == EntityKind.PROCESS and e.parent == "sys_root" and e.level == 1
        for e in project.all_entities()
    )


def _cspec_processes(project: Project) -> list:
    return [e for e in project.all_entities()
            if e.kind == EntityKind.PROCESS and e.needs_cspec]


def _check_stage_1(project: Project, project_dir: Path) -> StageStatus:
    proposal = project_dir / "00-context" / "proposal.md"
    naming_review = project_dir / "00-context" / "naming-review.md"
    context_md = project_dir / "00-context" / "context.md"
    has_terms = _has_terminator(project)
    n_terms = sum(1 for e in project.all_entities() if e.kind == EntityKind.TERMINATOR)

    if _is_locked(proposal) and has_terms:
        return StageStatus(1, "Context Diagram", "locked", f"{n_terms} terminator(s); proposal locked")
    # Pre-form-pattern fallback: solar-era projects did Stage 1 ad-hoc, before
    # form-based proposals existed. Terminators in the dictionary + either a
    # locked naming-review or a hand-written context.md count as locked.
    if has_terms and (_is_locked(naming_review) or context_md.exists()):
        return StageStatus(1, "Context Diagram", "locked", f"pre-form pattern; {n_terms} terminator(s)")
    if proposal.exists():
        return StageStatus(1, "Context Diagram", "in_progress", "proposal exists but no Status: Locked block yet")
    if project.entities.get("sys_root"):
        return StageStatus(1, "Context Diagram", "in_progress", "sys_root exists; no proposal.md yet")
    return StageStatus(1, "Context Diagram", "not_started", "")


def _check_stage_2(project: Project, project_dir: Path) -> StageStatus:
    proposal = project_dir / "01-level1" / "proposal.md"
    locked = _is_locked(proposal)
    has_internals = _has_internal_processes(project)
    n_procs = sum(1 for e in project.all_entities() if e.kind == EntityKind.PROCESS and e.level == 1)

    if locked and has_internals:
        return StageStatus(2, "Level-1 DFD", "locked", f"{n_procs} internal process(es); proposal locked")
    elif proposal.exists():
        return StageStatus(2, "Level-1 DFD", "in_progress", "proposal exists; not yet locked")
    elif has_internals:
        return StageStatus(2, "Level-1 DFD", "in_progress", f"{n_procs} process(es) in dictionary; no proposal.md")
    else:
        return StageStatus(2, "Level-1 DFD", "not_started", "")


def _check_stage_3(project: Project, project_dir: Path) -> StageStatus:
    procs = _cspec_processes(project)
    if not procs:
        return StageStatus(3, "CSPECs", "n/a", "no processes need_cspec=true")

    # Scan the filesystem for locked CSPEC proposals. The renderer derives
    # subdir from process id (proc_X → X-with-dashes), but tolerating any
    # subdir name keeps status robust to label-based directories.
    cspecs_dir = project_dir / "01-level1" / "cspecs"
    locked_subdirs: list[Path] = []
    if cspecs_dir.is_dir():
        for sub in sorted(cspecs_dir.iterdir()):
            if sub.is_dir() and _is_locked(sub / "proposal.md"):
                locked_subdirs.append(sub)

    procs_with_txns = [p for p in procs
                       if any(t.parent_machine == p.id for t in project.all_transitions())]

    if locked_subdirs and len(procs_with_txns) == len(procs):
        total_states = sum(
            1 for e in project.all_entities()
            if e.kind in (EntityKind.STATE, EntityKind.STATE_COMPOSITE)
        )
        return StageStatus(3, "CSPECs", "locked",
                           f"{len(locked_subdirs)} locked CSPEC(s); "
                           f"{total_states} states + {len(project.all_transitions())} transitions")
    if locked_subdirs:
        return StageStatus(3, "CSPECs", "in_progress",
                           f"{len(locked_subdirs)} locked CSPEC(s); "
                           f"{len(procs_with_txns)}/{len(procs)} processes have transitions")
    return StageStatus(3, "CSPECs", "not_started", f"{len(procs)} process(es) flagged needs_cspec")


def _scan_open_questions(project_dir: Path) -> dict[Path, int]:
    """Count unchecked `- [ ]` items in proposal.md and naming-review.md files.

    Skip files that are marked Status: Locked/Resolved — once a form-based
    proposal locks, leftover `- [ ]` items represent unselected alternatives,
    not open questions."""
    results: dict[Path, int] = {}
    pattern = re.compile(r"^- \[ \]", re.MULTILINE)
    for md in project_dir.rglob("*.md"):
        if md.name in ("proposal.md", "naming-review.md"):
            if _is_locked(md):
                continue
            n = len(pattern.findall(md.read_text()))
            if n > 0:
                results[md] = n
    return results


def _find_stale_artifacts(project_dir: Path) -> list[Path]:
    """List `.generated.*` files older than dictionary.yaml."""
    dict_path = project_dir / "dictionary.yaml"
    if not dict_path.exists():
        return []
    dict_mtime = dict_path.stat().st_mtime

    stale: list[Path] = []
    for gen in project_dir.rglob("*.generated.*"):
        if gen.stat().st_mtime < dict_mtime:
            stale.append(gen)
    return sorted(stale)


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def status_report(project_dir: Path) -> StatusReport:
    """Build a full status report for an HP project directory."""
    project_dir = Path(project_dir).resolve()
    dict_path = project_dir / "dictionary.yaml"

    if not dict_path.exists():
        return StatusReport(
            project_name=project_dir.name,
            project_dir=project_dir,
            dictionary_exists=False,
        )

    project = load(dict_path)

    return StatusReport(
        project_name=project.project,
        project_dir=project_dir,
        dictionary_exists=True,
        stages=[
            _check_stage_1(project, project_dir),
            _check_stage_2(project, project_dir),
            _check_stage_3(project, project_dir),
            StageStatus(4, "PSPECs", "n/a", "stage not yet implemented in toolkit"),
            StageStatus(5, "Architecture model", "n/a", "stage not yet implemented in toolkit"),
        ],
        validation=validate(project),
        stale_artifacts=_find_stale_artifacts(project_dir),
        open_questions=_scan_open_questions(project_dir),
    )


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def _main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m hp_toolkit.status <project-directory>", file=sys.stderr)
        return 2

    project_dir = Path(sys.argv[1])
    if not project_dir.is_dir():
        print(_color(f"ERROR: {project_dir} is not a directory", "31"), file=sys.stderr)
        return 2

    report = status_report(project_dir)
    print(report.format())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(_main())
