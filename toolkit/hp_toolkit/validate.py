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

from pathlib import Path

from .model import (
    Project, Entity, EntityKind, Flow, PSpec, ADR, ADRStatus,
    AuthRequired, Encryption, Budget, TPM, TPMDirection,
    Observability, Alert, SLO, STRIDEMitigations,
    ArchInterconnect, ArchModuleSpec, ArchInterconnectSpec,
)


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


# ─────────────────────────────────────────────────────────────────────
# Architecture Model validation (rules from toolkit/ARCH_DESIGN.md §6)
#
# Sources: Hatley, Hruschka & Pirbhai 2000 ch. 4, §4.2 (Architecture Model).
# Specific rule sources cited per-rule below.
# ─────────────────────────────────────────────────────────────────────


def _is_leaf_requirements_process(project: Project, e: Entity) -> bool:
    """A leaf requirements process — eligible for architecture allocation."""
    if e.kind != EntityKind.PROCESS:
        return False
    for other in project.all_entities():
        if other.parent == e.id and other.kind == EntityKind.PROCESS:
            return False
    return True


def architecture_validation(project: Project) -> ValidationReport:
    """Validate the Architecture Model per the 15 rules from ARCH_DESIGN.md §6."""
    report = ValidationReport()
    entity_ids = set(project.entities.keys())
    am_ids = set(project.architecture_modules.keys())
    af_ids = set(project.architecture_flows.keys())
    ai_ids = set(project.architecture_interconnects.keys())

    # Short-circuit: if no architecture surface defined, nothing to check
    if not project.architecture_modules:
        return report

    # ─── Reference integrity (rules 5–10, 13, 14) ───

    # Rule 5: ArchModule.parent references a real module
    for m in project.all_architecture_modules():
        if m.parent and m.parent not in am_ids:
            report.issues.append(ValidationIssue(
                "error", "architecture", m.id,
                f"parent {m.parent!r} not in architecture_modules"
            ))
        # Rule 13: allocated_* reference real requirements entities of the correct kind
        for proc_id in m.allocated_processes:
            target = project.entities.get(proc_id)
            if target is None:
                report.issues.append(ValidationIssue(
                    "error", "architecture", m.id,
                    f"allocated_process {proc_id!r} not in entities"))
            elif target.kind != EntityKind.PROCESS:
                report.issues.append(ValidationIssue(
                    "error", "architecture", m.id,
                    f"allocated_process {proc_id!r} is kind {target.kind.value!r}, expected 'process'"))
        for proc_id in m.allocated_cspecs:
            target = project.entities.get(proc_id)
            if target is None:
                report.issues.append(ValidationIssue(
                    "error", "architecture", m.id,
                    f"allocated_cspec {proc_id!r} not in entities"))
            elif target.kind != EntityKind.PROCESS or not target.needs_cspec:
                report.issues.append(ValidationIssue(
                    "error", "architecture", m.id,
                    f"allocated_cspec {proc_id!r} is not a process with needs_cspec=true"))
        for store_id in m.allocated_stores:
            target = project.entities.get(store_id)
            if target is None:
                report.issues.append(ValidationIssue(
                    "error", "architecture", m.id,
                    f"allocated_store {store_id!r} not in entities"))
            elif target.kind != EntityKind.DATA_STORE:
                report.issues.append(ValidationIssue(
                    "error", "architecture", m.id,
                    f"allocated_store {store_id!r} is kind {target.kind.value!r}, expected 'data_store'"))

    # Rule 6: ArchFlow.{source,target} reference real modules
    for f in project.all_architecture_flows():
        if f.source not in am_ids:
            report.issues.append(ValidationIssue(
                "error", "architecture", f.id,
                f"source {f.source!r} not in architecture_modules"))
        if f.target not in am_ids:
            report.issues.append(ValidationIssue(
                "error", "architecture", f.id,
                f"target {f.target!r} not in architecture_modules"))
        # Rule 14: allocated_flows references real requirements flows
        for fid in f.allocated_flows:
            if fid not in project.flows:
                report.issues.append(ValidationIssue(
                    "error", "architecture", f.id,
                    f"allocated_flow {fid!r} not in requirements flows"))

    # Rule 7: ArchInterconnect.endpoints reference real modules; ≥ 2 endpoints
    for ic in project.all_architecture_interconnects():
        if len(ic.endpoints) < 2:
            report.issues.append(ValidationIssue(
                "error", "architecture", ic.id,
                f"interconnect has {len(ic.endpoints)} endpoint(s); ≥ 2 required"))
        for ep in ic.endpoints:
            if ep not in am_ids:
                report.issues.append(ValidationIssue(
                    "error", "architecture", ic.id,
                    f"endpoint {ep!r} not in architecture_modules"))
        # Rule 8: carries references real architecture flows
        for fid in ic.carries:
            if fid not in af_ids:
                report.issues.append(ValidationIssue(
                    "error", "architecture", ic.id,
                    f"carries {fid!r} not in architecture_flows"))

    # Rule 9: AMS.parent_module references a real module
    for s in project.all_architecture_module_specs():
        if s.parent_module not in am_ids:
            report.issues.append(ValidationIssue(
                "error", "architecture", s.id,
                f"parent_module {s.parent_module!r} not in architecture_modules"))

    # Rule 10: AIS.parent_interconnect references a real interconnect
    for s in project.all_architecture_interconnect_specs():
        if s.parent_interconnect not in ai_ids:
            report.issues.append(ValidationIssue(
                "error", "architecture", s.id,
                f"parent_interconnect {s.parent_interconnect!r} not in architecture_interconnects"))

    # ─── Allocation coverage (rules 1, 2, 3) ───

    # Collect allocations across all modules
    allocated_proc_set: set[str] = set()
    allocated_cspec_set: set[str] = set()
    allocated_store_set: set[str] = set()
    for m in project.all_architecture_modules():
        allocated_proc_set.update(m.allocated_processes)
        allocated_cspec_set.update(m.allocated_cspecs)
        allocated_store_set.update(m.allocated_stores)

    # Rule 1: every leaf requirements process is allocated to ≥ 1 module.
    # State-rich processes (needs_cspec=true) satisfy this via allocated_cspecs;
    # non-state-rich leaves satisfy it via allocated_processes.
    leaf_procs = [e for e in project.all_entities() if _is_leaf_requirements_process(project, e)]
    for proc in leaf_procs:
        if proc.needs_cspec:
            if proc.id not in allocated_cspec_set:
                report.issues.append(ValidationIssue(
                    "error", "architecture", proc.id,
                    "state-rich leaf process not listed in any module's allocated_cspecs (2000 §4.2.5.4)"))
        else:
            if proc.id not in allocated_proc_set:
                report.issues.append(ValidationIssue(
                    "error", "architecture", proc.id,
                    "leaf requirements process not allocated to any architecture module (2000 §4.2.5.4)"))

    # Rule 2: every CSPEC's parent process is in allocated_cspecs of at least one module
    cspec_owners = {e.id for e in project.all_entities()
                    if e.kind == EntityKind.PROCESS and e.needs_cspec}
    for cid in cspec_owners:
        if cid not in allocated_cspec_set:
            report.issues.append(ValidationIssue(
                "error", "architecture", cid,
                "process with needs_cspec=true not listed in any module's allocated_cspecs"))

    # Rule 3: every requirements data store is allocated
    stores = [e for e in project.all_entities() if e.kind == EntityKind.DATA_STORE]
    for s in stores:
        if s.id not in allocated_store_set:
            report.issues.append(ValidationIssue(
                "error", "architecture", s.id,
                "data store not allocated to any architecture module"))

    # Rule 4: every requirements flow at level ≥ 1 is allocated to an architecture flow,
    # OR is internal to one module's allocations
    allocated_flow_set: set[str] = set()
    for f in project.all_architecture_flows():
        allocated_flow_set.update(f.allocated_flows)

    def _flow_internal_to_one_module(rf: Flow) -> bool:
        """Both endpoints of this flow live in the same architecture module's allocations."""
        src, tgt = rf.refined_source or rf.source, rf.refined_target or rf.target
        for m in project.all_architecture_modules():
            owned = (set(m.allocated_processes)
                     | set(m.allocated_cspecs)
                     | set(m.allocated_stores))
            if src in owned and tgt in owned:
                return True
        return False

    for rf in project.all_flows():
        if rf.level == 0:
            continue
        if rf.id in allocated_flow_set:
            continue
        if _flow_internal_to_one_module(rf):
            continue
        report.issues.append(ValidationIssue(
            "warning", "architecture", rf.id,
            f"requirements flow not carried by any architecture flow and not internal to a single module"))

    # ─── Spec coverage (rules 11, 12) ───

    ams_modules: set[str] = {s.parent_module for s in project.all_architecture_module_specs()}
    for m in project.all_architecture_modules():
        if m.id not in ams_modules:
            report.issues.append(ValidationIssue(
                "error", "architecture", m.id,
                "architecture module has no AMS (2000 §4.2.5.4: every module must have an AMS)"))

    ais_interconnects: set[str] = {s.parent_interconnect for s in project.all_architecture_interconnect_specs()}
    for ic in project.all_architecture_interconnects():
        if ic.id not in ais_interconnects:
            report.issues.append(ValidationIssue(
                "warning", "architecture", ic.id,
                "architecture interconnect has no AIS"))

    # Rule 15: module_number uniqueness
    seen_numbers: dict[str, str] = {}
    for m in project.all_architecture_modules():
        if not m.module_number:
            continue
        if m.module_number in seen_numbers:
            report.issues.append(ValidationIssue(
                "warning", "architecture", m.id,
                f"module_number {m.module_number!r} also used by {seen_numbers[m.module_number]!r}"))
        else:
            seen_numbers[m.module_number] = m.id

    # ─── Coverage metrics ───
    if leaf_procs:
        n_allocated = sum(
            1 for p in leaf_procs
            if (p.needs_cspec and p.id in allocated_cspec_set)
            or (not p.needs_cspec and p.id in allocated_proc_set)
        )
        report.metrics["architecture_module_coverage_pct"] = round(100 * n_allocated / len(leaf_procs), 1)

    l1plus_flows = [f for f in project.all_flows() if f.level != 0]
    if l1plus_flows:
        n_carried = sum(1 for f in l1plus_flows
                        if f.id in allocated_flow_set or _flow_internal_to_one_module(f))
        report.metrics["architecture_flow_coverage_pct"] = round(100 * n_carried / len(l1plus_flows), 1)

    if project.architecture_modules:
        n_ams = sum(1 for m in project.all_architecture_modules() if m.id in ams_modules)
        report.metrics["ams_coverage_pct"] = round(100 * n_ams / len(project.architecture_modules), 1)
        report.counts["architecture_modules"] = len(project.architecture_modules)
        report.counts["architecture_flows"] = len(project.architecture_flows)
        report.counts["architecture_interconnects"] = len(project.architecture_interconnects)

    if project.architecture_interconnects:
        n_ais = sum(1 for ic in project.all_architecture_interconnects() if ic.id in ais_interconnects)
        report.metrics["ais_coverage_pct"] = round(100 * n_ais / len(project.architecture_interconnects), 1)

    return report


# ─────────────────────────────────────────────────────────────────────
# Modernization validators (Commit 1 — items #2, #8.1, #10, #25)
#
# Sources cited per-rule below. All rules treat the modernization fields
# as optional — projects without modernization data still validate.
# ─────────────────────────────────────────────────────────────────────


def modernization_validation(project: Project, project_dir: Path | None = None) -> ValidationReport:
    """Validate the Commit-1 modernization additions.

    - #2:   Flow / ArchFlow synchronicity — warn if unset on ArchFlow
    - #8.1: Trust boundaries + interconnect security — warn on cross-
            trust-zone interconnects without auth/encryption
    - #10:  ADRs — reference integrity on `affects` and `supersedes`
    - #25:  V&V plans — warn if `test_suite` path doesn't exist
    """
    report = ValidationReport()
    entity_ids = set(project.entities.keys())
    am_ids = set(project.architecture_modules.keys())
    af_ids = set(project.architecture_flows.keys())
    ai_ids = set(project.architecture_interconnects.keys())

    # ─── #2: synchronicity coverage on architecture flows ───
    arch_flows = project.all_architecture_flows()
    if arch_flows:
        n_with_sync = sum(1 for f in arch_flows if f.synchronicity is not None)
        report.metrics["synchronicity_coverage_pct"] = round(100 * n_with_sync / len(arch_flows), 1)
        for f in arch_flows:
            if f.synchronicity is None:
                report.issues.append(ValidationIssue(
                    "info", "modernization", f.id,
                    "architecture flow has no synchronicity declared (modernization #2)"))

    # ─── #8.1: cross-trust-zone interconnects need auth + encryption ───
    for ic in project.all_architecture_interconnects():
        # Find trust zones of endpoints
        ep_zones = set()
        for ep_id in ic.endpoints:
            m = project.architecture_modules.get(ep_id)
            if m is not None and m.trust_zone is not None:
                ep_zones.add(m.trust_zone)

        if len(ep_zones) > 1:
            # Crosses trust zones
            if ic.auth_required is None or ic.auth_required == AuthRequired.NONE:
                report.issues.append(ValidationIssue(
                    "warning", "modernization", ic.id,
                    f"interconnect crosses trust zones {sorted(z.value for z in ep_zones)!r} "
                    f"but has no auth_required (modernization #8.1)"))
            if ic.encryption is None or ic.encryption == Encryption.NONE:
                report.issues.append(ValidationIssue(
                    "warning", "modernization", ic.id,
                    f"interconnect crosses trust zones {sorted(z.value for z in ep_zones)!r} "
                    f"but has no encryption (modernization #8.1)"))

    # ─── #10: ADR reference integrity ───
    adr_ids = set(project.adrs.keys())
    for adr in project.all_adrs():
        # supersedes references a real ADR
        if adr.supersedes is not None and adr.supersedes not in adr_ids:
            report.issues.append(ValidationIssue(
                "error", "modernization", adr.id,
                f"ADR supersedes {adr.supersedes!r} but that ADR is not in the dictionary"))
        # `affects` references resolve. Targets can be entities, flows, edges,
        # transitions, architecture modules / flows / interconnects.
        all_refable = (entity_ids | set(project.flows.keys())
                       | set(project.edges.keys()) | set(project.transitions.keys())
                       | am_ids | af_ids | ai_ids)
        for kind, ids in adr.affects.items():
            for ref_id in ids:
                if ref_id not in all_refable:
                    report.issues.append(ValidationIssue(
                        "error", "modernization", adr.id,
                        f"ADR.affects[{kind!r}] references {ref_id!r} which is not in the dictionary"))

    if project.adrs:
        n_accepted = sum(1 for a in project.all_adrs() if a.status == ADRStatus.ACCEPTED)
        report.counts["adrs_total"] = len(project.adrs)
        report.counts["adrs_accepted"] = n_accepted

    # ─── #21: Budget allocation hard rule + reference integrity ───
    am_ids_set = set(project.architecture_modules.keys())
    for b in project.all_budgets():
        # Allocations reference real architecture modules
        for mod_id in b.allocations.keys():
            if mod_id not in am_ids_set:
                report.issues.append(ValidationIssue(
                    "error", "modernization", b.id,
                    f"budget allocation references unknown module {mod_id!r}"))
        # Hard rule: sum(allocations) + reserve ≤ system_target
        allocated_total = sum(b.allocations.values())
        if allocated_total + b.system_reserve > b.system_target + 1e-9:
            report.issues.append(ValidationIssue(
                "error", "modernization", b.id,
                f"budget over-allocated: allocations ({allocated_total} {b.unit}) "
                f"+ reserve ({b.system_reserve} {b.unit}) > "
                f"system_target ({b.system_target} {b.unit}) "
                f"(NASA SE Handbook §6.7)"))

    if project.budgets:
        # Coverage metric: how close to fully allocated (avg across budgets)
        completeness_values = []
        for b in project.all_budgets():
            if b.system_target == 0:
                continue
            completeness_values.append(
                100 * (sum(b.allocations.values()) + b.system_reserve) / b.system_target
            )
        if completeness_values:
            report.metrics["budget_allocation_completeness_pct"] = round(
                sum(completeness_values) / len(completeness_values), 1)
        report.counts["budgets_total"] = len(project.budgets)

    # ─── #22: TPM threshold rule + cross-references ───
    # Threshold semantics depend on direction:
    #   less_is_better — threshold is a ceiling; current + growth must stay ≤ threshold
    #   more_is_better — threshold is a floor;   current - growth must stay ≥ threshold
    def _tpm_within_threshold(t: TPM) -> bool:
        if t.direction == TPMDirection.MORE_IS_BETTER:
            return t.current_estimate >= t.threshold
        return t.current_estimate <= t.threshold

    def _tpm_growth_safe(t: TPM) -> bool:
        if t.direction == TPMDirection.MORE_IS_BETTER:
            return t.current_estimate - t.growth_allowance >= t.threshold
        return t.current_estimate + t.growth_allowance <= t.threshold

    budget_ids = set(project.budgets.keys())
    for t in project.all_tpms():
        if not _tpm_growth_safe(t):
            direction_phrase = (
                "current_estimate − growth_allowance dropped below threshold"
                if t.direction == TPMDirection.MORE_IS_BETTER
                else "current_estimate + growth_allowance exceeded threshold"
            )
            report.issues.append(ValidationIssue(
                "error", "modernization", t.id,
                f"TPM headroom exhausted ({t.direction.value}): {direction_phrase} — "
                f"current={t.current_estimate} {t.unit}, growth={t.growth_allowance}, "
                f"threshold={t.threshold}"))
        if not _tpm_within_threshold(t):
            direction_phrase = (
                f"below floor of {t.threshold}"
                if t.direction == TPMDirection.MORE_IS_BETTER
                else f"above ceiling of {t.threshold}"
            )
            report.issues.append(ValidationIssue(
                "warning", "modernization", t.id,
                f"TPM current_estimate ({t.current_estimate} {t.unit}) is {direction_phrase}"))
        if t.derived_from_budget is not None and t.derived_from_budget not in budget_ids:
            report.issues.append(ValidationIssue(
                "error", "modernization", t.id,
                f"TPM derived_from_budget {t.derived_from_budget!r} not in dictionary"))

    if project.tpms:
        n_within = sum(1 for t in project.all_tpms() if _tpm_within_threshold(t))
        n_safe   = sum(1 for t in project.all_tpms() if _tpm_growth_safe(t))
        report.metrics["tpm_within_threshold_pct"] = round(100 * n_within / len(project.tpms), 1)
        report.metrics["tpm_growth_safety_pct"]    = round(100 * n_safe   / len(project.tpms), 1)
        report.counts["tpms_total"] = len(project.tpms)

    # ─── #25: V&V — verification block coverage + test_suite path check ───
    n_specs_total = len(project.pspecs) + len(project.architecture_module_specs)
    if n_specs_total > 0:
        n_with_verif = (
            sum(1 for p in project.all_pspecs() if p.verification is not None)
            + sum(1 for a in project.all_architecture_module_specs() if a.verification is not None)
        )
        report.metrics["verification_coverage_pct"] = round(100 * n_with_verif / n_specs_total, 1)

        # Path-existence check (only if project_dir is provided)
        if project_dir is not None:
            def _check_paths(spec_id: str, spec_verif):
                if spec_verif is None or spec_verif.test_suite is None:
                    return
                test_path = spec_verif.test_suite
                # Reject absolute paths and parent-directory escape
                if test_path.startswith("/") or ".." in Path(test_path).parts:
                    report.issues.append(ValidationIssue(
                        "error", "modernization", spec_id,
                        f"V&V test_suite path {test_path!r} must be relative and within project"))
                    return
                full_path = project_dir / test_path
                if not full_path.exists():
                    report.issues.append(ValidationIssue(
                        "warning", "modernization", spec_id,
                        f"V&V test_suite {test_path!r} does not exist at expected location"))

            for p in project.all_pspecs():
                _check_paths(p.id, p.verification)
            for a in project.all_architecture_module_specs():
                _check_paths(a.id, a.verification)

    # ─── #1: observability coverage + alert path checks ───
    am_ids_set = set(project.architecture_modules.keys())

    def _validate_observability(holder_id: str, obs) -> None:
        if obs is None:
            return
        seen_alert_names: set[str] = set()
        for alert in obs.alerts:
            if alert.name in seen_alert_names:
                report.issues.append(ValidationIssue(
                    "error", "modernization", holder_id,
                    f"duplicate alert name {alert.name!r} within this observability block"))
            seen_alert_names.add(alert.name)
            # #33 — runbook path validation
            if alert.runbook is not None and project_dir is not None:
                if alert.runbook.startswith("/") or ".." in Path(alert.runbook).parts:
                    report.issues.append(ValidationIssue(
                        "error", "modernization", holder_id,
                        f"alert {alert.name!r} runbook path {alert.runbook!r} "
                        f"must be relative and within project"))
                elif not (project_dir / alert.runbook).exists():
                    report.issues.append(ValidationIssue(
                        "warning", "modernization", holder_id,
                        f"alert {alert.name!r} runbook {alert.runbook!r} does not exist"))

    for ps in project.all_pspecs():
        _validate_observability(ps.id, ps.observability)
    for am in project.all_architecture_modules():
        _validate_observability(am.id, am.observability)

    obs_holders_total = len(project.pspecs) + len(project.architecture_modules)
    if obs_holders_total > 0:
        obs_with = (
            sum(1 for ps in project.all_pspecs() if ps.observability is not None)
            + sum(1 for am in project.all_architecture_modules() if am.observability is not None)
        )
        report.metrics["observability_coverage_pct"] = round(100 * obs_with / obs_holders_total, 1)

    # Coverage metric: alerts with runbook (#33)
    all_alerts: list = []
    for ps in project.all_pspecs():
        if ps.observability:
            all_alerts.extend(ps.observability.alerts)
    for am in project.all_architecture_modules():
        if am.observability:
            all_alerts.extend(am.observability.alerts)
    if all_alerts:
        n_with_runbook = sum(1 for a in all_alerts if a.runbook is not None)
        report.metrics["alert_runbook_coverage_pct"] = round(100 * n_with_runbook / len(all_alerts), 1)
        report.counts["alerts_total"] = len(all_alerts)

    # ─── #32: SLO validator ───
    tpm_ids = set(project.tpms.keys())
    window_re = re.compile(r"^\d+(s|m|h|d|w)$")
    for slo in project.all_slos():
        if not (0 <= slo.error_budget_pct <= 100):
            report.issues.append(ValidationIssue(
                "error", "modernization", slo.id,
                f"error_budget_pct {slo.error_budget_pct} not in [0, 100]"))
        if not window_re.match(slo.window):
            report.issues.append(ValidationIssue(
                "error", "modernization", slo.id,
                f"window {slo.window!r} does not match \\d+[smhdw] (e.g. '30d', '24h')"))
        all_known: dict[str, set[str]] = {
            "modules": am_ids_set,
            "flows": set(project.flows.keys()),
            "interconnects": set(project.architecture_interconnects.keys()),
            "processes": entity_ids,
        }
        for kind, ids in slo.applies_to.items():
            known = all_known.get(kind)
            if known is None:
                continue
            for ref_id in ids:
                if ref_id not in known:
                    report.issues.append(ValidationIssue(
                        "error", "modernization", slo.id,
                        f"applies_to[{kind!r}] references {ref_id!r} which is not in the dictionary"))
        if slo.derives_from_tpm is not None and slo.derives_from_tpm not in tpm_ids:
            report.issues.append(ValidationIssue(
                "error", "modernization", slo.id,
                f"derives_from_tpm {slo.derives_from_tpm!r} not in dictionary"))
        if slo.runbook_on_burn is not None and project_dir is not None:
            rb = slo.runbook_on_burn
            if rb.startswith("/") or ".." in Path(rb).parts:
                report.issues.append(ValidationIssue(
                    "error", "modernization", slo.id,
                    f"runbook_on_burn {rb!r} must be relative and within project"))
            elif not (project_dir / rb).exists():
                report.issues.append(ValidationIssue(
                    "warning", "modernization", slo.id,
                    f"runbook_on_burn {rb!r} does not exist"))

    if project.architecture_modules:
        slo_module_ids = set()
        for slo in project.all_slos():
            slo_module_ids.update(slo.applies_to.get("modules", []))
        report.metrics["slo_coverage_pct"] = round(
            100 * len(slo_module_ids & am_ids_set) / len(am_ids_set), 1)
    if project.service_level_objectives:
        report.counts["slos_total"] = len(project.service_level_objectives)

    # ─── #8.2: STRIDE coverage on cross-trust-zone interconnects ───
    cross_zone_interconnects: list[ArchInterconnect] = []
    for ic in project.all_architecture_interconnects():
        ep_zones = set()
        for ep_id in ic.endpoints:
            m = project.architecture_modules.get(ep_id)
            if m is not None and m.trust_zone is not None:
                ep_zones.add(m.trust_zone)
        if len(ep_zones) > 1:
            cross_zone_interconnects.append(ic)
            if ic.stride_mitigations is None:
                report.issues.append(ValidationIssue(
                    "error", "modernization", ic.id,
                    f"interconnect crosses trust zones {sorted(z.value for z in ep_zones)!r} "
                    f"but has no stride_mitigations (modernization #8.2)"))

    if cross_zone_interconnects:
        n_with_stride = sum(1 for ic in cross_zone_interconnects if ic.stride_mitigations is not None)
        report.metrics["stride_coverage_pct"] = round(
            100 * n_with_stride / len(cross_zone_interconnects), 1)
        report.counts["stride_cross_zone_interconnects"] = len(cross_zone_interconnects)

    # ─── #8.3: reference-catalog ID format checks ───
    # Patterns are conservative — they catch malformed IDs without trying
    # to validate against the live external catalogs.
    mitre_attack_re = re.compile(r"^T\d{4}(\.\d{3})?$")          # T1078 or T1078.001
    cwe_re          = re.compile(r"^CWE-\d{1,5}$")               # CWE-79
    compliance_re   = re.compile(r"^[A-Z][A-Z0-9-]*-[A-Z0-9.\-]+$")  # SOC2-CC6.1, ISA-62443-SL2

    def _check_catalog_refs(holder_id: str, holder: object) -> None:
        for tid in getattr(holder, "references_mitre_attack", []) or []:
            if not mitre_attack_re.match(tid):
                report.issues.append(ValidationIssue(
                    "warning", "modernization", holder_id,
                    f"MITRE ATT&CK reference {tid!r} does not match T\\d{{4}}(\\.\\d{{3}})? format"))
        for cwe in getattr(holder, "references_cwe", []) or []:
            if not cwe_re.match(cwe):
                report.issues.append(ValidationIssue(
                    "warning", "modernization", holder_id,
                    f"CWE reference {cwe!r} does not match CWE-\\d+ format"))
        for cid in getattr(holder, "references_compliance", []) or []:
            if not compliance_re.match(cid):
                report.issues.append(ValidationIssue(
                    "warning", "modernization", holder_id,
                    f"compliance reference {cid!r} does not match expected format "
                    f"(e.g. SOC2-CC6.1, ISA-62443-SL2)"))

    for s in project.all_architecture_module_specs():
        _check_catalog_refs(s.id, s)
    for s in project.all_architecture_interconnect_specs():
        _check_catalog_refs(s.id, s)
    for adr in project.all_adrs():
        _check_catalog_refs(adr.id, adr)

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

def validate(project: Project, project_dir: Path | None = None) -> ValidationReport:
    """Run all validators and return a combined report.

    `project_dir`, when provided, lets modernization rules (#25 V&V path
    check, #33 runbook path check, etc.) verify referenced files exist.
    """
    report = ValidationReport()
    report.extend(reference_integrity(project))
    report.extend(hierarchy_consistency(project))
    report.extend(coverage_metrics(project))
    report.extend(pspec_validation(project))
    report.extend(architecture_validation(project))
    report.extend(modernization_validation(project, project_dir))
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
    report = validate(project, project_dir=path.parent)

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
