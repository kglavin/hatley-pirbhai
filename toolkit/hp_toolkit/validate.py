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

import re

from .model import Project, Entity, EntityKind, Flow, PSpec


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
        if f.refined_source and f.refined_source not in entity_ids:
            report.issues.append(ValidationIssue(
                "error", "reference", f.id,
                f"flow refined_source {f.refined_source!r} not in dictionary"
            ))
        if f.refined_target and f.refined_target not in entity_ids:
            report.issues.append(ValidationIssue(
                "error", "reference", f.id,
                f"flow refined_target {f.refined_target!r} not in dictionary"
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

    for t in project.all_transitions():
        if t.source_state not in entity_ids:
            report.issues.append(ValidationIssue(
                "error", "reference", t.id,
                f"transition source_state {t.source_state!r} not in dictionary"
            ))
        if t.target_state not in entity_ids:
            report.issues.append(ValidationIssue(
                "error", "reference", t.id,
                f"transition target_state {t.target_state!r} not in dictionary"
            ))
        if t.parent_machine not in entity_ids:
            report.issues.append(ValidationIssue(
                "error", "reference", t.id,
                f"transition parent_machine {t.parent_machine!r} not in dictionary"
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


# ─────────────────────────────────────────────────────────────────────
# PSPEC validation (rules from toolkit/PSPEC_DESIGN.md §5)
#
# Sources:
#   Hatley & Pirbhai 1988 ch. 13 (esp. §13.1 balancing; §13.2 styles + PAT
#   exclusion + no-code rule; §13.3 "issue" keyword; §13.4 capitalized
#   flow names; §13.5 comments)
#   Hatley, Hruschka & Pirbhai 2000 §4.3.3.9 + A.2.12 (one PSPEC per leaf;
#   computational constraints; "what not how")
# ─────────────────────────────────────────────────────────────────────


def _is_leaf_process(project: Project, e: Entity) -> bool:
    """A leaf process is a process with no children in the entities table
    AND not flagged needs_cspec=True. Such a process needs a PSPEC."""
    if e.kind != EntityKind.PROCESS:
        return False
    if e.needs_cspec:
        return False
    # If any other entity has this as parent, it's decomposed → not a leaf.
    for other in project.all_entities():
        if other.parent == e.id and other.kind == EntityKind.PROCESS:
            return False
    return True


def _process_inputs(project: Project, process_id: str) -> list[Flow]:
    """Flows whose effective level-N+1 target is this process.

    Includes both internal flows (target=process directly) and refined
    boundary flows (refined_target=process — the level-N flow whose
    level-N+1 endpoint is this process).
    """
    result: list[Flow] = []
    for f in project.all_flows():
        if f.refined_target == process_id:
            result.append(f)
        elif f.target == process_id and not f.refined_target:
            result.append(f)
    return result


def _process_outputs(project: Project, process_id: str) -> list[Flow]:
    """Flows whose effective level-N+1 source is this process."""
    result: list[Flow] = []
    for f in project.all_flows():
        if f.refined_source == process_id:
            result.append(f)
        elif f.source == process_id and not f.refined_source:
            result.append(f)
    return result


def _flow_reference_tokens(f: Flow) -> list[str]:
    """Plausible uppercase tokens by which a PSPEC body might reference a flow.

    The 1988 book §13.4 requires textual PSPECs to capitalize flow names
    matching the dictionary entries exactly. We accept several common
    forms because the dictionary stores both an id (e.g., flow_f3_tension)
    and a label (e.g., "F3: tension feedback") — either uppercased should
    count as a valid reference.
    """
    tokens: list[str] = []
    # ID variants
    raw_id = f.id
    if raw_id.startswith("flow_"):
        raw_id = raw_id[len("flow_"):]
    tokens.append(raw_id.upper())
    tokens.append(raw_id.replace("_", " ").upper())
    # Label variants
    label_clean = re.sub(r"[^A-Za-z0-9 ]+", " ", f.label).strip()
    label_clean = re.sub(r"\s+", " ", label_clean)
    tokens.append(label_clean.upper())
    # Drop dupes preserving order
    seen, out = set(), []
    for t in tokens:
        if t and t not in seen:
            seen.add(t); out.append(t)
    return out


def _body_references_flow(body: str, f: Flow) -> bool:
    """Heuristic: does the body reference this flow by any plausible name?"""
    body_upper = body.upper()
    return any(tok in body_upper for tok in _flow_reference_tokens(f))


# Patterns suggesting code or pseudocode — flagged as warnings (1988 §13.2).
_CODE_PATTERNS = [
    re.compile(r":="),                              # Pascal-style assignment
    re.compile(r"\bfor\s*\("),                      # C-style for-loop
    re.compile(r"\bwhile\s*\("),                    # C-style while
    re.compile(r"\bdef\s+\w+\s*\("),                # Python def
    re.compile(r"\bfunction\s+\w+\s*\("),           # JS function
    re.compile(r"\breturn\s+"),
    re.compile(r"\+\+|--"),                         # increment/decrement
    re.compile(r"==|!="),                           # equality operators
    re.compile(r"=>"),                              # lambda/arrow
]


def _looks_like_code(body: str) -> list[str]:
    """Return the code-like patterns found in the body. Empty if clean."""
    hits: list[str] = []
    for pat in _CODE_PATTERNS:
        if pat.search(body):
            hits.append(pat.pattern)
    return hits


def pspec_validation(project: Project) -> ValidationReport:
    """Validate PSPECs per the 10 rules from PSPEC_DESIGN.md §5."""
    report = ValidationReport()
    entity_ids = set(project.entities.keys())

    leaf_processes = [e for e in project.all_entities() if _is_leaf_process(project, e)]

    # Rule 1: every leaf functional primitive has exactly one PSPEC.
    pspec_by_process: dict[str, list[PSpec]] = defaultdict(list)
    for p in project.all_pspecs():
        pspec_by_process[p.parent_process].append(p)

    for proc in leaf_processes:
        specs = pspec_by_process.get(proc.id, [])
        if len(specs) == 0:
            report.issues.append(ValidationIssue(
                "error", "pspec", proc.id,
                f"leaf process has no PSPEC (rule 1: every functional primitive needs one)"
            ))
        elif len(specs) > 1:
            ids = ", ".join(s.id for s in specs)
            report.issues.append(ValidationIssue(
                "error", "pspec", proc.id,
                f"leaf process has {len(specs)} PSPECs ({ids}); rule 1 requires exactly one"
            ))

    # Per-PSPEC rules
    for p in project.all_pspecs():
        # Rule 2: parent_process references a real process
        parent = project.entities.get(p.parent_process)
        if parent is None:
            report.issues.append(ValidationIssue(
                "error", "pspec", p.id,
                f"parent_process {p.parent_process!r} not in dictionary"
            ))
            continue
        if parent.kind != EntityKind.PROCESS:
            report.issues.append(ValidationIssue(
                "error", "pspec", p.id,
                f"parent_process {p.parent_process!r} is kind {parent.kind.value!r}, "
                f"expected 'process'"
            ))
            continue
        if parent.needs_cspec:
            report.issues.append(ValidationIssue(
                "error", "pspec", p.id,
                f"parent_process {p.parent_process!r} has needs_cspec=true; "
                f"state-rich bubbles get a CSPEC, not a PSPEC"
            ))

        body = p.transformation.body or ""

        # Rule 10: body non-empty (defensive — Pydantic should reject empty too)
        if not body.strip():
            report.issues.append(ValidationIssue(
                "error", "pspec", p.id,
                "transformation body is empty"
            ))
            continue

        # Rule 3: every input flow appears in the body
        inputs = _process_inputs(project, p.parent_process)
        for f in inputs:
            if not _body_references_flow(body, f):
                report.issues.append(ValidationIssue(
                    "error", "pspec", p.id,
                    f"input flow {f.id!r} (label {f.label!r}) not referenced in "
                    f"transformation body — balancing rule (1988 §13.1)"
                ))

        # Rule 4: every output flow is generated by the body
        outputs = _process_outputs(project, p.parent_process)
        for f in outputs:
            if not _body_references_flow(body, f):
                report.issues.append(ValidationIssue(
                    "error", "pspec", p.id,
                    f"output flow {f.id!r} (label {f.label!r}) not generated by "
                    f"transformation body — balancing rule (1988 §13.1)"
                ))

        # Rule 5: no extra flow references — heuristic placeholder.
        # Full implementation would parse the body's capitalized tokens and
        # verify each maps to an input/output. Skipped for first cut to avoid
        # false positives on natural-language usage of common words.

        # Rule 6: no Process Activation Tables (CSPEC-only construct)
        if re.search(r"\bprocess\s+activation\s+table\b|\bPAT\b", body, re.IGNORECASE):
            report.issues.append(ValidationIssue(
                "error", "pspec", p.id,
                "transformation body contains process activation table; PATs "
                "are CSPEC-only (1988 §13.2)"
            ))

        # Rule 7: no code/pseudocode (warning, heuristic)
        code_hits = _looks_like_code(body)
        if code_hits:
            report.issues.append(ValidationIssue(
                "warning", "pspec", p.id,
                f"transformation body looks code-like (matched {code_hits!r}); "
                f"PSPECs should not contain code or pseudocode (1988 §13.2)"
            ))

        # Rules 8, 9: capitalization convention and "issue" keyword — informational
        # only on first cut. Full enforcement requires a `transient:` flag on Flow
        # and stricter tokenization than we have today.

    # Coverage metric: pspec_coverage_pct
    n_leaf = len(leaf_processes)
    if n_leaf:
        n_with_pspec = sum(1 for p in leaf_processes if pspec_by_process.get(p.id))
        report.metrics["pspec_coverage_pct"] = round(100 * n_with_pspec / n_leaf, 1)
        report.counts["leaf_processes"] = n_leaf
        report.counts["pspecs_total"] = len(project.all_pspecs())

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
    report.extend(pspec_validation(project))
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
