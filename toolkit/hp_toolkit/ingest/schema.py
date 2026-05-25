"""Pydantic schemas for the brownfield-ingest intermediate representation (IR).

The IR is `intermediate/hp-graph.json`, accreted across the 6 ingest agents
(see INGEST_DESIGN.md). Every IR node carries confidence + provenance so the
architect can review and override.

The IR uses HP entity vocabulary (terminator / process / data_store / state /
pspec / architecture_module / architecture_flow / architecture_interconnect)
— *not* implementation primitives. The final emission step transforms IR into
the existing `dictionary.yaml` schema.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────
# HP role hint — the per-file classifier output (no LLM; Stage 0)
# ─────────────────────────────────────────────────────────────────────

class HpRoleHint(str, Enum):
    """Per-file architectural role hint, produced by the role classifier.

    The single most decision-shaping signal hp-ingest gives to downstream
    agents. Computed deterministically from file path, extension, and a few
    content regexes — never via LLM."""

    BOUNDARY      = "boundary"       # HTTP handlers, CLI entry points, message-bus subscribers
    PURE_LOGIC    = "pure-logic"     # Domain types + functions, no I/O
    STATE_MACHINE = "state-machine"  # State-enum + transition-table patterns
    DATA_STORE    = "data-store"     # DB / cache / queue clients, ORM models
    INFRA         = "infra"          # Dockerfile / k8s / terraform / CI manifests
    CONFIG        = "config"         # TOML / YAML / JSON config files


# ─────────────────────────────────────────────────────────────────────
# IR node kinds — mirror of HP entity vocabulary
# ─────────────────────────────────────────────────────────────────────

class IRNodeKind(str, Enum):
    """The HP entity kinds an IR node can represent.

    Mirrors the dictionary.yaml `entities`/`flows`/`architecture_*` vocabulary
    so emission is a near-1:1 mapping with provenance stripped."""

    TERMINATOR              = "terminator"
    PROCESS                 = "process"
    DATA_STORE              = "data_store"
    STATE                   = "state"
    STATE_COMPOSITE         = "state_composite"
    PSPEC                   = "pspec"
    ARCHITECTURE_MODULE     = "architecture_module"
    ARCHITECTURE_INTERCONNECT = "architecture_interconnect"


class IREdgeKind(str, Enum):
    """The HP edge / flow kinds an IR edge can represent."""

    DATA_FLOW       = "data_flow"          # Stage 1 / 2 / 5
    CONTROL_FLOW    = "control_flow"
    PHYSICAL_EDGE   = "physical_edge"      # non-data physical interaction
    ALLOCATES_TO    = "allocates_to"       # Stage 5: process → architecture module
    TRIGGERS        = "triggers"           # CSPEC transition
    REFINES         = "refines"            # higher-level entity → lower-level child
    CARRIES         = "carries"            # architecture flow → requirements flow


# ─────────────────────────────────────────────────────────────────────
# Provenance — required on every IR node
# ─────────────────────────────────────────────────────────────────────

class Provenance(BaseModel):
    """Where this IR node came from + why.

    `agent` distinguishes hp-ingest-authored fields (replaceable on
    incremental re-ingest) from user-authored fields (preserved verbatim).
    `rationale` is the LLM's one-line reason for the classification —
    surfaces in `ingest-report.md` for architect review.
    `external_context_used` records which `external-context/<category>/`
    files contributed to this node, for the H.8 audit trail."""

    agent: str                       # e.g., "hp-boundary-finder"
    rationale: Optional[str] = None  # one-line LLM justification
    external_context_used: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# IR node + edge
# ─────────────────────────────────────────────────────────────────────

class IRNode(BaseModel):
    """One entity in the ingest IR.

    Translation to dictionary.yaml: each IRNode emits one entry in the
    corresponding section (entities/pspecs/architecture_modules/…) with
    `confidence` / `provenance` / `implemented_by` stripped. Those three
    fields stay in `intermediate/hp-graph.json` for re-ingest reconciliation."""

    model_config = ConfigDict(extra="allow")

    id: str
    kind: IRNodeKind
    label: str
    stage: int                       # 0–5; which agent produced this
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: Provenance

    # Provenance-of-implementation: which files in the codebase compose this
    # entity. Empty for external terminators.
    implemented_by: list[str] = Field(default_factory=list)

    summary: Optional[str] = None
    description: Optional[str] = None

    # HP-specific fields carried through to dictionary.yaml. Only populated
    # for the relevant kind; extras allowed for incremental schema growth.
    needs_cspec: Optional[bool] = None       # processes only
    is_initial: Optional[bool] = None        # states only
    optional: Optional[bool] = None
    parent: Optional[str] = None             # for hierarchy
    parent_machine: Optional[str] = None     # for state entities


class IREdge(BaseModel):
    """One edge in the ingest IR — flow / transition / allocation / etc."""

    model_config = ConfigDict(extra="allow")

    source: str
    target: str
    kind: IREdgeKind
    stage: int                       # 0–5; which agent produced this
    label: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance: Optional[Provenance] = None


# ─────────────────────────────────────────────────────────────────────
# Stage 0 scan output — `intermediate/scan.json`
# ─────────────────────────────────────────────────────────────────────

class FileEntry(BaseModel):
    """One file in the scanned codebase, with its HP role hint."""

    path: str                            # repo-relative
    language: Optional[str] = None       # py | ts | tsx | js | rs | go | …
    size_lines: int = 0
    hp_role_hint: Optional[HpRoleHint] = None  # None = not yet classified or filtered out
    is_significant: bool = True          # passed the significance filter
    notes: Optional[str] = None          # filter reason, classifier hint, etc.


class ProjectMeta(BaseModel):
    """Project-level metadata captured at ingest time."""

    name: str
    description: Optional[str] = None    # one-paragraph LLM output (Stage 0)
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    git_commit_hash: Optional[str] = None
    analyzed_at: datetime = Field(default_factory=datetime.now)


class ProjectScan(BaseModel):
    """The Stage 0 scanner's output — `intermediate/scan.json`."""

    project: ProjectMeta
    files: list[FileEntry] = Field(default_factory=list)
    import_map: dict[str, list[str]] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────
# IR graph — `intermediate/hp-graph.json`
# ─────────────────────────────────────────────────────────────────────

class IRGraph(BaseModel):
    """The full ingest IR. Accreted across agents; emitted as dictionary.yaml
    at the end by the assembler-reviewer."""

    version: str = "0.1"
    project: ProjectMeta
    nodes: list[IRNode] = Field(default_factory=list)
    edges: list[IREdge] = Field(default_factory=list)

    # Stage-0 scan output is carried in the graph so downstream agents
    # never need to re-read scan.json from disk separately.
    scan: Optional[ProjectScan] = None

    # Reviewer-emitted artifacts (filled by the assembler-reviewer pass)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    orphans: list[str] = Field(default_factory=list)
