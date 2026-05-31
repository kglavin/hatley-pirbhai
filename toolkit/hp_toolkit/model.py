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
    # Future: PHYSICAL_DC_POWER, MECHANICAL_LINK, etc.


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


class Flow(BaseModel):
    """A data or control flow between entities."""
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    source: str   # entity id
    target: str   # entity id
    kind: FlowKind
    level: LevelType
    medium: Optional[str] = None    # how the flow is carried (RF, Modbus, MQTT, etc.)
    notes: Optional[str] = None
    optional: bool = False


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

    # ─── Convenience accessors ───

    def all_entities(self) -> list[Entity]:
        return list(self.entities.values())

    def all_flows(self) -> list[Flow]:
        return list(self.flows.values())

    def all_edges(self) -> list[Edge]:
        return list(self.edges.values())

    def entity(self, id: str) -> Entity:
        return self.entities[id]

    def flow(self, id: str) -> Flow:
        return self.flows[id]

    def edge(self, id: str) -> Edge:
        return self.edges[id]

    def entities_at_level(self, level: LevelType) -> list[Entity]:
        return [e for e in self.entities.values() if e.level == level]

    def flows_at_level(self, level: LevelType) -> list[Flow]:
        return [f for f in self.flows.values() if f.level == level]

    def children_of(self, parent_id: str) -> list[Entity]:
        """Entities whose `parent` or `parent_state` is the given id."""
        return [
            e for e in self.entities.values()
            if e.parent == parent_id or e.parent_state == parent_id
        ]
