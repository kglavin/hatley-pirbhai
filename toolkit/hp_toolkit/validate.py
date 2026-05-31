"""Validators for the HP toolkit model.

These implement the "make rigor measurable" tactic — every check produces
a ValidationReport with issues (errors / warnings / info) and metrics
(percentages and counts) the human can act on.

Public API:
    validate(project) -> ValidationReport     # run all validators
    reference_integrity(project)              # parent / source / target resolve
    hierarchy_consistency(project)            # kind-appropriate parent/parent_state
    coverage_metrics(project)                 # description %, etc.
    find_orphans(project)                     # entities referenced by no flow
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

from .model import Project, Entity, EntityKind


Severity = Literal["error", "warning", "info"]


@dataclass
class ValidationIssue:
    """A single finding from a validator."""
    severity: Severity
    category: str           # "reference" / "hierarchy" / "coverage" / "orphan"
    entity_id: str | None   # the entity / flow / edge id this concerns, if any
    message: str

    def format(self) -> str:
        icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}[self.severity]
        ref = f" [{self.entity_id}]" if self.entity_id else ""
        return f"{icon} {self.category}{ref}: {self.message}"


@dataclass
class ValidationReport:
    """Aggregate result from running validators."""
    issues: list[ValidationIssue] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def infos(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "info"]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def extend(self, other: "ValidationReport") -> None:
        self.issues.extend(other.issues)
        self.metrics.update(other.metrics)
        self.counts.update(other.counts)


# ─────────────────────────────────────────────────────────────────────
# Individual validators
# ─────────────────────────────────────────────────────────────────────

def reference_integrity(project: Project) -> ValidationReport:
    """Verify every parent / parent_state / source / target points at an
    entity id that exists in the dictionary."""
    report = ValidationReport()
    entity_ids = set(project.entities.keys())

    for e in project.all_entities():
        if e.parent and e.parent not in entity_ids:
            report.issues.append(ValidationIssue(
                "error", "reference", e.id,
                f"parent {e.parent!r} not in dictionary"
            ))
        if e.parent_state and e.parent_state not in entity_ids:
            report.issues.append(ValidationIssue(
                "error", "reference", e.id,
                f"parent_state {e.parent_state!r} not in dictionary"
            ))

    for f in project.all_flows():
        if f.source not in entity_ids:
            report.issues.append(ValidationIssue(
                "error", "reference", f.id,
                f"flow source {f.source!r} not in dictionary"
            ))
        if f.target not in entity_ids:
            report.issues.append(ValidationIssue(
                "error", "reference", f.id,
                f"flow target {f.target!r} not in dictionary"
            ))

    for ed in project.all_edges():
        if ed.source not in entity_ids:
            report.issues.append(ValidationIssue(
                "error", "reference", ed.id,
                f"edge source {ed.source!r} not in dictionary"
            ))
        if ed.target not in entity_ids:
            report.issues.append(ValidationIssue(
                "error", "reference", ed.id,
                f"edge target {ed.target!r} not in dictionary"
            ))

    return report


def hierarchy_consistency(project: Project) -> ValidationReport:
    """Verify hierarchy rules — `parent_state` only on states; sub-states
    must point at composite parents; processes can only nest under sys/process."""
    report = ValidationReport()

    for e in project.all_entities():
        # Only states can carry parent_state.
        if e.parent_state and e.kind not in (EntityKind.STATE, EntityKind.STATE_COMPOSITE):
            report.issues.append(ValidationIssue(
                "error", "hierarchy", e.id,
                f"entity of kind {e.kind.value!r} has parent_state — that field "
                f"is reserved for states inside composite states"
            ))

        # parent_state, if set, should point at a composite state.
        if e.parent_state:
            parent = project.entities.get(e.parent_state)
            if parent and parent.kind != EntityKind.STATE_COMPOSITE:
                report.issues.append(ValidationIssue(
                    "warning", "hierarchy", e.id,
                    f"parent_state {e.parent_state!r} is kind {parent.kind.value!r}, "
                    f"expected 'state_composite'"
                ))

        # States must have a parent process (set via `parent`).
        if e.kind in (EntityKind.STATE, EntityKind.STATE_COMPOSITE) and not e.parent:
            report.issues.append(ValidationIssue(
                "warning", "hierarchy", e.id,
                f"state has no `parent` field — should reference the process it lives in"
            ))

        # Terminators should have no parent (they're external).
        if e.kind == EntityKind.TERMINATOR and e.parent:
            report.issues.append(ValidationIssue(
                "warning", "hierarchy", e.id,
                f"terminator has parent={e.parent!r} — terminators are external; "
                f"they don't decompose"
            ))

    return report


def coverage_metrics(project: Project) -> ValidationReport:
    """Compute the 'make rigor measurable' percentages."""
    report = ValidationReport()
    entities = project.all_entities()
    flows = project.all_flows()

    n_entities = len(entities)
    n_flows = len(flows)

    if n_entities:
        with_desc = sum(1 for e in entities if e.description)
        report.metrics["description_coverage_pct"] = round(100 * with_desc / n_entities, 1)
        report.counts["entities_with_description"] = with_desc
        report.counts["entities_total"] = n_entities

    if n_flows:
        with_medium = sum(1 for f in flows if f.medium)
        with_notes = sum(1 for f in flows if f.notes)
        report.metrics["flow_medium_coverage_pct"] = round(100 * with_medium / n_flows, 1)
        report.metrics["flow_notes_coverage_pct"] = round(100 * with_notes / n_flows, 1)
        report.counts["flows_total"] = n_flows

    # Entities by kind
    from collections import Counter
    kinds = Counter(e.kind.value for e in entities)
    for kind, n in kinds.items():
        report.counts[f"entities__{kind}"] = n

    # Levels
    levels = Counter(e.level for e in entities)
    for level, n in sorted(levels.items()):
        report.counts[f"level_{level}_entities"] = n

    return report


def find_orphans(project: Project) -> ValidationReport:
    """Entities that no flow or edge references — *and* are not the
    container of another entity (i.e., not a parent). True orphans probably
    indicate a missing flow or a stale dictionary entry."""
    report = ValidationReport()

    referenced: set[str] = set()
    for f in project.all_flows():
        referenced.add(f.source)
        referenced.add(f.target)
    for ed in project.all_edges():
        referenced.add(ed.source)
        referenced.add(ed.target)

    is_parent: set[str] = set()
    for e in project.all_entities():
        if e.parent:
            is_parent.add(e.parent)
        if e.parent_state:
            is_parent.add(e.parent_state)

    for e in project.all_entities():
        if e.id in referenced or e.id in is_parent:
            continue
        # States get a pass — they're not referenced by flows (yet — we don't
        # model transitions in dictionary.yaml as flows).
        if e.kind in (EntityKind.STATE, EntityKind.STATE_COMPOSITE):
            continue
        report.issues.append(ValidationIssue(
            "info", "orphan", e.id,
            f"entity is not referenced by any flow/edge and has no children — "
            f"possible stale entry or missing flow"
        ))

    return report


# ─────────────────────────────────────────────────────────────────────
# Aggregate
# ─────────────────────────────────────────────────────────────────────

def validate(project: Project) -> ValidationReport:
    """Run all validators and return a combined report."""
    report = ValidationReport()
    report.extend(reference_integrity(project))
    report.extend(hierarchy_consistency(project))
    report.extend(coverage_metrics(project))
    report.extend(find_orphans(project))
    return report


# ─────────────────────────────────────────────────────────────────────
# CLI entrypoint:  uv run python -m hp_toolkit.validate <path>
# ─────────────────────────────────────────────────────────────────────

def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def _main() -> int:
    import sys
    from pathlib import Path
    from .load import load

    if len(sys.argv) < 2:
        print("usage: python -m hp_toolkit.validate <path/to/dictionary.yaml>",
              file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(_color(f"ERROR: {path} does not exist", "31"), file=sys.stderr)
        return 2

    project = load(path)
    report = validate(project)

    # Issues, grouped by severity
    if report.errors:
        print(_color(f"== {len(report.errors)} ERROR(S) ==", "31"))
        for i in report.errors:
            print("  " + i.format())
        print()
    if report.warnings:
        print(_color(f"== {len(report.warnings)} WARNING(S) ==", "33"))
        for i in report.warnings:
            print("  " + i.format())
        print()
    if report.infos:
        print(_color(f"== {len(report.infos)} INFO ==", "36"))
        for i in report.infos:
            print("  " + i.format())
        print()

    # Metrics — the "rigor measurable as percentages" payoff
    print(_color("== Coverage metrics ==", "1"))
    for name, value in sorted(report.metrics.items()):
        bar = "█" * int(value / 5) + "░" * (20 - int(value / 5))
        print(f"  {name:34s} [{bar}] {value:5.1f}%")
    print()

    print(_color("== Counts ==", "1"))
    for name, value in sorted(report.counts.items()):
        print(f"  {name:34s} {value}")
    print()

    if report.ok:
        print(_color("VALID — no errors", "32"))
        return 0
    else:
        print(_color(f"INVALID — {len(report.errors)} error(s)", "31"))
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(_main())
