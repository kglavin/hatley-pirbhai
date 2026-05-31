# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

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
from .model import Project, EntityKind, ADRStatus
from .validate import validate, ValidationReport


StageState = Literal["locked", "in_progress", "not_started", "n/a"]


@dataclass
class StageStatus:
    stage: int          # 1, 2, 3, 4, 5
    name: str
    state: StageState
    detail: str = ""    # short single-line explanation


@dataclass
class ModernizationSummary:
    """Counts for the modernization layer (Commits 1–5).

    Each project may declare none, some, or all of these. Zero counts
    are reported as "none declared" — the modernization layer is
    optional and incremental."""
    adrs_by_status: dict[str, int] = field(default_factory=dict)
    budgets: int = 0
    tpms: int = 0
    budgets_tracked_by_tpm: int = 0
    slos: int = 0
    slos_tied_to_tpm: int = 0
    bounded_contexts: int = 0
    acls: int = 0
    leaf_pspecs_total: int = 0
    leaf_pspecs_with_observability: int = 0
    leaf_pspecs_with_verification: int = 0
    cross_zone_interconnects: int = 0
    cross_zone_with_stride: int = 0


@dataclass
class StatusReport:
    project_name: str
    project_dir: Path
    dictionary_exists: bool
    stages: list[StageStatus] = field(default_factory=list)
    modernization: ModernizationSummary | None = None
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

        if self.modernization is not None:
            lines.extend(_format_modernization(self.modernization))

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
# Modernization summary
# ─────────────────────────────────────────────────────────────────────

def modernization_summary(project: Project) -> ModernizationSummary:
    """Tally the modernization-layer sections declared on the project."""
    s = ModernizationSummary()

    # ADRs by status
    for adr in project.all_adrs():
        key = adr.status.value if isinstance(adr.status, ADRStatus) else str(adr.status)
        s.adrs_by_status[key] = s.adrs_by_status.get(key, 0) + 1

    # Budgets + TPMs
    s.budgets = len(project.budgets)
    s.tpms = len(project.tpms)
    tracked_budget_ids = {t.derived_from_budget for t in project.all_tpms()
                          if t.derived_from_budget}
    s.budgets_tracked_by_tpm = len(tracked_budget_ids & set(project.budgets.keys()))

    # SLOs
    s.slos = len(project.service_level_objectives)
    s.slos_tied_to_tpm = sum(1 for slo in project.all_slos()
                             if slo.derives_from_tpm and slo.derives_from_tpm in project.tpms)

    # Bounded contexts + ACLs (ACLs are entities with kind=TRANSLATION)
    s.bounded_contexts = len(project.bounded_contexts)
    s.acls = sum(1 for e in project.all_entities()
                 if e.kind == EntityKind.TRANSLATION)

    # Observability + V&V on leaf PSPECs
    leaves = _leaf_processes_needing_pspec(project)
    s.leaf_pspecs_total = len(leaves)
    for leaf in leaves:
        pspec = project.pspec_for_process(leaf.id)
        if pspec is None:
            continue
        if pspec.observability is not None:
            s.leaf_pspecs_with_observability += 1
        if pspec.verification is not None:
            s.leaf_pspecs_with_verification += 1

    # STRIDE on cross-trust-zone interconnects
    for ai in project.all_architecture_interconnects():
        zones = {project.architecture_modules[m].trust_zone
                 for m in ai.endpoints
                 if m in project.architecture_modules
                 and project.architecture_modules[m].trust_zone is not None}
        if len(zones) >= 2:
            s.cross_zone_interconnects += 1
            if ai.stride_mitigations is not None:
                s.cross_zone_with_stride += 1

    return s


def _format_modernization(s: ModernizationSummary) -> list[str]:
    """Render the modernization layer as a section of lines."""
    lines = [_color("Modernization layer", "1")]

    # ADRs
    if s.adrs_by_status:
        total = sum(s.adrs_by_status.values())
        # Order: accepted, proposed, superseded, deprecated, others alphabetical
        order = ["accepted", "proposed", "superseded", "deprecated"]
        ordered = [k for k in order if k in s.adrs_by_status] + \
                  sorted(k for k in s.adrs_by_status if k not in order)
        breakdown = " / ".join(f"{s.adrs_by_status[k]} {k}" for k in ordered)
        lines.append(f"  {'ADRs':22s} {total} ({breakdown})")
    else:
        lines.append(f"  {'ADRs':22s} {_color('none declared', '90')}")

    # Budgets / TPMs
    if s.budgets or s.tpms:
        tracked = f"{s.budgets_tracked_by_tpm}/{s.budgets} budget(s) tracked by TPM"
        lines.append(f"  {'Budgets / TPMs':22s} {s.budgets} budget(s); {s.tpms} TPM(s) [{tracked}]")
    else:
        lines.append(f"  {'Budgets / TPMs':22s} {_color('none declared', '90')}")

    # SLOs
    if s.slos:
        tied = f"{s.slos_tied_to_tpm}/{s.slos} tied to a TPM"
        lines.append(f"  {'SLOs':22s} {s.slos} SLO(s) [{tied}]")
    else:
        lines.append(f"  {'SLOs':22s} {_color('none declared', '90')}")

    # Observability + V&V coverage of leaf PSPECs
    if s.leaf_pspecs_total > 0:
        lines.append(f"  {'Observability':22s} "
                     f"{s.leaf_pspecs_with_observability}/{s.leaf_pspecs_total} leaf PSPEC(s) declare observability")
        lines.append(f"  {'V&V plans':22s} "
                     f"{s.leaf_pspecs_with_verification}/{s.leaf_pspecs_total} leaf PSPEC(s) declare verification")
    else:
        lines.append(f"  {'Observability':22s} {_color('no leaf PSPECs yet', '90')}")
        lines.append(f"  {'V&V plans':22s} {_color('no leaf PSPECs yet', '90')}")

    # STRIDE
    if s.cross_zone_interconnects > 0:
        icon = _color("✅", "32") if s.cross_zone_with_stride == s.cross_zone_interconnects else _color("⚠", "33")
        lines.append(f"  {'STRIDE':22s} {icon} "
                     f"{s.cross_zone_with_stride}/{s.cross_zone_interconnects} "
                     f"cross-trust-zone interconnect(s) have STRIDE mitigations")
    else:
        lines.append(f"  {'STRIDE':22s} {_color('no cross-trust-zone interconnects', '90')}")

    # Bounded contexts
    if s.bounded_contexts > 0:
        lines.append(f"  {'Bounded contexts':22s} {s.bounded_contexts} context(s); {s.acls} ACL(s)")
    else:
        lines.append(f"  {'Bounded contexts':22s} {_color('none declared (single-context project)', '90')}")

    lines.append("")
    return lines


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


def _leaf_processes_needing_pspec(project: Project) -> list:
    """A leaf process is `kind=PROCESS`, `needs_cspec=False`, with no child
    processes. Each needs a PSPEC per 2000 §4.3.3.9."""
    leaves = []
    for e in project.all_entities():
        if e.kind != EntityKind.PROCESS or e.needs_cspec:
            continue
        has_child_process = any(
            o.parent == e.id and o.kind == EntityKind.PROCESS
            for o in project.all_entities()
        )
        if not has_child_process:
            leaves.append(e)
    return leaves


def _check_stage_4(project: Project, project_dir: Path) -> StageStatus:
    leaves = _leaf_processes_needing_pspec(project)
    if not leaves:
        return StageStatus(4, "PSPECs", "n/a", "no leaf processes needing PSPECs (Stage 2 not yet locked?)")

    have_pspec = [e for e in leaves if project.pspec_for_process(e.id) is not None]
    if len(have_pspec) == len(leaves):
        return StageStatus(4, "PSPECs", "locked",
                           f"{len(have_pspec)}/{len(leaves)} leaf processes have PSPECs")
    if have_pspec:
        return StageStatus(4, "PSPECs", "in_progress",
                           f"{len(have_pspec)}/{len(leaves)} leaf processes have PSPECs")
    return StageStatus(4, "PSPECs", "not_started",
                       f"{len(leaves)} leaf process(es) need PSPECs")


def _all_leaf_processes(project: Project) -> list:
    """All leaf requirements processes (with or without needs_cspec).
    These are the processes Stage 5 must allocate."""
    leaves = []
    for e in project.all_entities():
        if e.kind != EntityKind.PROCESS:
            continue
        has_child = any(o.parent == e.id and o.kind == EntityKind.PROCESS
                        for o in project.all_entities())
        if not has_child:
            leaves.append(e)
    return leaves


def _check_stage_5(project: Project, project_dir: Path) -> StageStatus:
    """Report Stage 5 (Architecture Model) progress.

    Locked = ≥ 1 module present AND every leaf requirements process is
    allocated (via allocated_processes for non-state-rich; via
    allocated_cspecs for state-rich) AND every module has an AMS.
    """
    if not project.architecture_modules:
        return StageStatus(5, "Architecture model", "not_started",
                           "no architecture_modules defined")

    n_modules = len(project.architecture_modules)
    n_flows = len(project.architecture_flows)
    n_interconnects = len(project.architecture_interconnects)

    leaves = _all_leaf_processes(project)
    allocated_procs: set[str] = set()
    allocated_cspecs: set[str] = set()
    for m in project.all_architecture_modules():
        allocated_procs.update(m.allocated_processes)
        allocated_cspecs.update(m.allocated_cspecs)

    def _is_allocated(p) -> bool:
        return p.id in allocated_cspecs if p.needs_cspec else p.id in allocated_procs

    n_allocated = sum(1 for p in leaves if _is_allocated(p))

    ams_modules = {s.parent_module for s in project.all_architecture_module_specs()}
    n_with_ams = sum(1 for m in project.all_architecture_modules() if m.id in ams_modules)

    all_allocated = len(leaves) == n_allocated
    all_have_ams = n_modules == n_with_ams

    if all_allocated and all_have_ams:
        return StageStatus(5, "Architecture model", "locked",
                           f"{n_modules} module(s); {n_flows} flow(s); "
                           f"{n_interconnects} interconnect(s); "
                           f"{n_allocated}/{len(leaves)} leaf processes allocated; "
                           f"{n_with_ams}/{n_modules} AMS")

    return StageStatus(5, "Architecture model", "in_progress",
                       f"{n_modules} module(s); "
                       f"{n_allocated}/{len(leaves)} leaf processes allocated; "
                       f"{n_with_ams}/{n_modules} AMS")


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
            _check_stage_4(project, project_dir),
            _check_stage_5(project, project_dir),
        ],
        modernization=modernization_summary(project),
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
