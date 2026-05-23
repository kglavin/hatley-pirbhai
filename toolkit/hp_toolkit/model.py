"""Pydantic schemas for the HP toolkit dictionary model.

The dictionary.yaml file is the canonical source of truth for an HP
project — every entity, flow, and edge has a stable_id (the dict key)
plus a human-readable label, kind, level, and optional metadata.

These models mirror the structure used by examples/solar/dictionary.yaml
and serve as the foundation everything else (validators, renderers,
skills) operates on.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────

class EntityKind(str, Enum):
    """Kinds of entity an HP model can contain.

    Level-0: system, terminator(s).
    Level-N (N≥1): process, data_store.
    CSPEC-level (typically level-2 inside a process): state, state_composite.
    """
    SYSTEM = "system"
    TERMINATOR = "terminator"
    PROCESS = "process"
    DATA_STORE = "data_store"
    STATE = "state"
    STATE_COMPOSITE = "state_composite"


class FlowKind(str, Enum):
    """Kinds of flow between entities."""
    DATA = "data"
    CONTROL = "control"
    DATA_AND_CONTROL = "data+control"


class EdgeKind(str, Enum):
    """Kinds of non-data edge (shown for context but not modeled as data flow)."""
    PHYSICAL_AC_POWER = "physical_ac_power"
    PHYSICAL_DC_POWER = "physical_dc_power"
    PHYSICAL_INTERACTION = "physical_interaction"  # e.g., fish acts on line


class PSpecStyle(str, Enum):
    """Canonical body styles for a PSPEC transformation.

    Source: Hatley & Pirbhai 1988 §13.2 ("PSPECs come in several different
    flavors: text, equations, tables, or diagrams, or any combination");
    Hatley, Hruschka & Pirbhai 2000 §4.3.3.9 Fig 4.47.
    """
    TEXTUAL = "textual"      # structured English; 1988 §13.4
    EQUATION = "equation"
    TABLE = "table"          # decision tables, condition→output matrices (NOT PATs)
    DIAGRAM = "diagram"      # body references a sidecar image
    MIXED = "mixed"


# ─────────────────────────────────────────────────────────────────────
# Core entities
# ─────────────────────────────────────────────────────────────────────

# Level can be int (e.g., 0, 1, 2) or float (e.g., 2.1 for nested sub-states
# at some future point). Accept both.
LevelType = Union[int, float]


class Entity(BaseModel):
    """An entity in the HP model — system, terminator, process, store, or state.

    Stable identity is the dict key in dictionary.yaml (populated as `id`
    by the loader). The `label` is the human-readable display name and can
    be changed without affecting references elsewhere.
    """
    model_config = ConfigDict(extra="allow")  # forward-compat for added fields

    id: str
    kind: EntityKind
    label: str
    level: LevelType
    parent: Optional[str] = None         # parent entity (e.g., parent process)
    parent_state: Optional[str] = None   # for nested states inside composite states
    description: Optional[str] = None
    optional: bool = False
    needs_cspec: bool = False            # process bubbles flagged for CSPEC
    is_initial: bool = False             # for states: this is the initial state of its parent composite (or of the whole CSPEC if no parent_state)


class Flow(BaseModel):
    """A data or control flow between entities.

    Level-0 boundary flows additionally carry refinement endpoints —
    `refined_source` and/or `refined_target` — which name the internal
    entity at level N+1 that the flow connects to once the parent is
    decomposed. This lets one boundary flow be rendered at multiple
    levels of decomposition without duplicating the entry.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    source: str   # entity id at this flow's level
    target: str   # entity id at this flow's level
    kind: FlowKind
    level: LevelType
    medium: Optional[str] = None    # how the flow is carried (RF, Modbus, MQTT, etc.)
    notes: Optional[str] = None
    optional: bool = False

    # ─── Refinement (for boundary flows at level N) ───
    # When rendering at level N+1, replace `source` (if it equals the
    # parent being decomposed) with `refined_source`; same for target.
    refined_source: Optional[str] = None
    refined_target: Optional[str] = None


class Edge(BaseModel):
    """A non-data physical/implicit connection — shown in diagrams for context."""
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    source: str
    target: str
    kind: EdgeKind
    level: LevelType
    notes: Optional[str] = None


class ComputationalConstraints(BaseModel):
    """Optional PSPEC computational constraints.

    Source: Hatley, Hruschka & Pirbhai 2000 §4.3.3.9 — "PSPECs may contain
    computational constraints, such as accuracy of computations, timing
    constraints on algorithms, and frequency of performance."
    """
    model_config = ConfigDict(extra="allow")

    frequency: Optional[str] = None
    accuracy: Optional[str] = None
    timing: Optional[str] = None


class Transformation(BaseModel):
    """The TRANSFORMATION section of a PSPEC — the spec body.

    Source: 2000 Fig 4.46 (generic PSPEC format: INPUTS / OUTPUTS / TRANSFORMATION).
    """
    model_config = ConfigDict(extra="allow")

    style: PSpecStyle
    body: str   # required; non-empty


class PSpec(BaseModel):
    """A Process Specification — the leaf-level functional contract for a process.

    INPUTS and OUTPUTS are NOT declared here; they are derived from
    dictionary.flows at validate time. The validator enforces the
    balancing rule (1988 §13.1): every input is used in the body; every
    output is generated by the body; no body reference to flows absent
    from the bubble's inputs/outputs.

    Source: Hatley & Pirbhai 1988 ch. 13; 2000 §4.3.3.9, A.2.12.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    parent_process: str                  # references a process entity (needs_cspec=false, leaf)
    transformation: Transformation
    computational_constraints: Optional[ComputationalConstraints] = None
    comments: Optional[str] = None       # rationale; 1988 §13.5 — NOT part of formal spec


class Transition(BaseModel):
    """A state-machine transition inside a CSPEC.

    `parent_machine` is the process whose CSPEC contains this transition
    (e.g., proc_compute_balance for the Energy Manager state machine).
    `source_state` / `target_state` reference state entities (which may be
    atomic states or composite states — for composite, semantics are
    "any sub-state" on the source side / "initial sub-state" on the target).
    """
    model_config = ConfigDict(extra="allow")

    id: str
    source_state: str            # entity id of source state (atomic or composite)
    target_state: str            # entity id of target state (atomic or composite)
    parent_machine: str          # entity id of the process this CSPEC lives in
    event: str                   # what triggers the transition (free text for now)
    label: Optional[str] = None  # short label for diagrams (defaults to event if omitted)
    action: Optional[str] = None # side effect that runs on transition
    guard: Optional[str] = None  # optional precondition on the event


# ─────────────────────────────────────────────────────────────────────
# Project root
# ─────────────────────────────────────────────────────────────────────

class Project(BaseModel):
    """The root of a dictionary.yaml — project metadata + collections."""
    # coerce_numbers_to_str lets `version: 0.1` (parsed as float by PyYAML)
    # validate against `version: str` without forcing every author to quote.
    model_config = ConfigDict(extra="allow", coerce_numbers_to_str=True)

    project: str
    version: str
    last_updated: Union[date, str]    # PyYAML parses YYYY-MM-DD as date

    entities: dict[str, Entity] = Field(default_factory=dict)
    flows: dict[str, Flow] = Field(default_factory=dict)
    edges: dict[str, Edge] = Field(default_factory=dict)
    transitions: dict[str, Transition] = Field(default_factory=dict)
    pspecs: dict[str, PSpec] = Field(default_factory=dict)

    # ─── Convenience accessors ───

    def all_entities(self) -> list[Entity]:
        return list(self.entities.values())

    def all_flows(self) -> list[Flow]:
        return list(self.flows.values())

    def all_edges(self) -> list[Edge]:
        return list(self.edges.values())

    def all_transitions(self) -> list[Transition]:
        return list(self.transitions.values())

    def all_pspecs(self) -> list[PSpec]:
        return list(self.pspecs.values())

    def entity(self, id: str) -> Entity:
        return self.entities[id]

    def flow(self, id: str) -> Flow:
        return self.flows[id]

    def edge(self, id: str) -> Edge:
        return self.edges[id]

    def transition(self, id: str) -> Transition:
        return self.transitions[id]

    def pspec(self, id: str) -> PSpec:
        return self.pspecs[id]

    def pspec_for_process(self, process_id: str) -> Optional[PSpec]:
        """Return the PSPEC for a process, or None if it doesn't have one."""
        for p in self.pspecs.values():
            if p.parent_process == process_id:
                return p
        return None

    def entities_at_level(self, level: LevelType) -> list[Entity]:
        return [e for e in self.entities.values() if e.level == level]

    def flows_at_level(self, level: LevelType) -> list[Flow]:
        return [f for f in self.flows.values() if f.level == level]

    def transitions_for(self, parent_machine_id: str) -> list[Transition]:
        """Transitions belonging to the CSPEC of `parent_machine_id`."""
        return [t for t in self.transitions.values()
                if t.parent_machine == parent_machine_id]

    def children_of(self, parent_id: str) -> list[Entity]:
        """Entities whose `parent` or `parent_state` is the given id."""
        return [
            e for e in self.entities.values()
            if e.parent == parent_id or e.parent_state == parent_id
        ]
