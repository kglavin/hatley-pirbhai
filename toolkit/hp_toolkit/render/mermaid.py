"""Mermaid renderer — emit Mermaid `graph LR` source from a Project model.

Currently supports: level-0 Context Diagram. Level-N DFD rendering will
follow once the dictionary models boundary-flow refinement.
"""

from __future__ import annotations

from ..model import (
    Project, Entity, Flow, Edge, Transition, EntityKind, FlowKind,
    ArchModule, ArchFlow, ArchInterconnect, ArchModuleKind,
)


def _esc(text: str) -> str:
    """Quote a Mermaid edge label — strip newlines and any quotes."""
    return text.replace('"', "'").replace("\n", " ")


def _node_decl(e: Entity) -> str:
    """Mermaid node declaration for an entity, choosing shape by kind."""
    label = _esc(e.label)
    if e.kind == EntityKind.SYSTEM:
        # double-circle for the system (in level-0 it IS the system)
        return f'    {e.id}(("{label}"))'
    if e.kind == EntityKind.TERMINATOR:
        if e.optional:
            # stadium/lozenge shape + italic "optional"
            return f'    {e.id}(["{label}<br/><i>optional</i>"])'
        return f'    {e.id}["{label}"]'
    if e.kind == EntityKind.DATA_STORE:
        return f'    {e.id}[("{label}")]'
    if e.kind == EntityKind.PROCESS:
        return f'    {e.id}(("{label}"))'
    # default: rectangle
    return f'    {e.id}["{label}"]'


def _flow_edge(f: Flow) -> str:
    """Mermaid edge declaration for a flow."""
    label = _esc(f.label)
    if f.optional:
        # dashed arrow
        return f'    {f.source} -. "{label}" .-> {f.target}'
    return f'    {f.source} -- "{label}" --> {f.target}'


def _edge_decl(ed: Edge) -> str:
    """Mermaid edge declaration for a non-data edge (e.g., physical AC).

    Uses an undirected `---` so the visualization shows context without
    implying a data-flow direction.
    """
    return f'    {ed.source} --- {ed.target}'


def render_context_diagram(project: Project) -> str:
    """Render the level-0 Context Diagram as a Mermaid source string.

    Includes:
      - system bubble (the level-0 system entity)
      - terminator rectangles (kind=terminator at level 0)
      - boundary flows (level 0 flows touching the system)
      - non-data edges at level 0 (e.g., physical AC power)
      - classDef styling matching the hand-written context.md

    Output is deterministic — entities and flows are emitted in
    dictionary order.
    """
    # ─── Collect ───
    system = next(
        (e for e in project.all_entities()
         if e.kind == EntityKind.SYSTEM and e.level == 0),
        None,
    )
    if system is None:
        raise ValueError("Project has no level-0 system entity")

    terminators = [
        e for e in project.all_entities()
        if e.kind == EntityKind.TERMINATOR and e.level == 0
    ]
    flows = project.flows_at_level(0)
    edges = [ed for ed in project.all_edges() if ed.level == 0]

    # ─── Emit ───
    lines: list[str] = ["graph LR"]

    # Terminator nodes first (visually they ring the system in LR layout)
    for t in terminators:
        lines.append(_node_decl(t))

    lines.append("")  # blank for readability

    # System bubble last (in case Mermaid renders nodes in source order)
    lines.append(_node_decl(system))

    lines.append("")

    # Flows
    for f in flows:
        lines.append(_flow_edge(f))

    if edges:
        lines.append("")
        for ed in edges:
            lines.append(_edge_decl(ed))

    # Styling — kind-based classDefs, mirrors hand-written conventions
    lines.append("")
    lines.append("    classDef system fill:#4a90e2,stroke:#2a70c2,color:#fff,font-weight:bold;")
    lines.append("    classDef terminator fill:#fafafa,stroke:#444;")
    lines.append("    classDef optional fill:#fafafa,stroke:#888,stroke-dasharray:5 5,color:#666;")
    lines.append("    classDef grid fill:#fef0ef,stroke:#e74c3c;")
    lines.append(f"    class {system.id} system;")

    normal_terms = [t.id for t in terminators if not t.optional and "grid" not in t.id]
    grid_terms = [t.id for t in terminators if "grid" in t.id]
    optional_terms = [t.id for t in terminators if t.optional]

    if normal_terms:
        lines.append(f"    class {','.join(normal_terms)} terminator;")
    if grid_terms:
        lines.append(f"    class {','.join(grid_terms)} grid;")
    if optional_terms:
        lines.append(f"    class {','.join(optional_terms)} optional;")

    return "\n".join(lines) + "\n"


def render_dfd(project: Project, parent_id: str = "sys_root") -> str:
    """Render a level-N+1 DFD (decomposition of `parent_id`) as Mermaid.

    Shows:
      - Internal entities (children of parent_id at level 1+): processes
        and data stores
      - Terminators that the boundary flows reach
      - Boundary flows (level-0) refined to internal endpoints via
        `refined_source` / `refined_target`
      - Internal flows (level 1) between internal entities
      - Physical edges at level 0

    Internal processes get kind-based classDef styling:
      - brain   (process with needs_cspec=True)
      - optional (process with optional=True)
      - proc    (default)
    """
    parent = project.entities.get(parent_id)
    if parent is None:
        raise ValueError(f"Parent {parent_id!r} not in project")

    # Per HIERARCHICAL_INGEST_DESIGN.md: child_level / boundary_level
    # derive from the parent's level. sys_root sits at level 0; its
    # children at level 1; their children at level 2; etc. This is the
    # only change needed to generalize from "level-1 DFD only" to
    # "level-N DFD for any non-leaf parent".
    child_level = parent.level + 1
    boundary_level = parent.level

    # Internal entities — direct children of parent at child_level
    internal = [e for e in project.all_entities()
                if e.parent == parent_id and e.level == child_level]
    processes = [e for e in internal if e.kind == EntityKind.PROCESS]
    stores    = [e for e in internal if e.kind == EntityKind.DATA_STORE]

    # Boundary flows (at the parent's level) touching this parent
    boundary_flows = [f for f in project.flows_at_level(boundary_level)
                      if f.source == parent_id or f.target == parent_id]

    # Terminators that participate in boundary flows
    term_ids: set[str] = set()
    for f in boundary_flows:
        if f.source != parent_id:
            term_ids.add(f.source)
        if f.target != parent_id:
            term_ids.add(f.target)
    # Also any terminator that the parent edges to (e.g., physical AC) —
    # only meaningful at level 0; level-2+ DFDs don't have edges-to-terminators
    edges_level0 = [ed for ed in project.all_edges() if ed.level == boundary_level]
    for ed in edges_level0:
        if project.entities.get(ed.source, None) and project.entities[ed.source].kind == EntityKind.TERMINATOR:
            term_ids.add(ed.source)
        if project.entities.get(ed.target, None) and project.entities[ed.target].kind == EntityKind.TERMINATOR:
            term_ids.add(ed.target)
    terminators = [project.entity(tid) for tid in term_ids
                   if project.entity(tid).kind == EntityKind.TERMINATOR]

    # Internal flows at child_level
    internal_flows = [f for f in project.flows_at_level(child_level)]

    # ─── Emit ───
    lines: list[str] = ["graph LR"]

    # Terminators
    lines.append("    %% Terminators")
    for t in terminators:
        lines.append(_node_decl(t))
    lines.append("")

    # Internal processes
    lines.append("    %% Internal processes")
    for p in processes:
        lines.append(_node_decl(p))
    lines.append("")

    # Data stores
    if stores:
        lines.append("    %% Data store")
        for s in stores:
            lines.append(_node_decl(s))
        lines.append("")

    # Boundary flows refined to internal endpoints
    lines.append("    %% Boundary flows (refined)")
    for f in boundary_flows:
        src = f.refined_source if f.source == parent_id and f.refined_source else f.source
        tgt = f.refined_target if f.target == parent_id and f.refined_target else f.target
        label = _esc(f.label)
        arrow = '-. "{}" .->' if f.optional else '-- "{}" -->'
        lines.append(f"    {src} {arrow.format(label)} {tgt}")
    lines.append("")

    # Physical edges
    if edges_level0:
        lines.append("    %% Physical AC")
        for ed in edges_level0:
            lines.append(_edge_decl(ed))
        lines.append("")

    # Internal flows
    lines.append("    %% Internal flows")
    for f in internal_flows:
        lines.append(_flow_edge(f))

    # Styling
    lines.append("")
    lines.append("    classDef proc fill:#cfe5ff,stroke:#2a70c2,color:#000;")
    lines.append("    classDef brain fill:#7fbff5,stroke:#1f5a99,color:#000,font-weight:bold;")
    lines.append("    classDef optional fill:#e6f0ff,stroke:#888,stroke-dasharray:3 3;")
    lines.append("    classDef terminator fill:#fafafa,stroke:#444;")
    lines.append("    classDef store fill:#fff5cc,stroke:#b89800;")
    lines.append("    classDef grid fill:#fef0ef,stroke:#e74c3c;")
    lines.append("    classDef termopt fill:#fafafa,stroke:#888,stroke-dasharray:5 5,color:#666;")

    procs_normal   = [p.id for p in processes if not p.needs_cspec and not p.optional]
    procs_brain    = [p.id for p in processes if p.needs_cspec]
    procs_optional = [p.id for p in processes if p.optional]
    store_ids      = [s.id for s in stores]
    terms_normal   = [t.id for t in terminators if not t.optional and "grid" not in t.id]
    terms_grid     = [t.id for t in terminators if "grid" in t.id]
    terms_optional = [t.id for t in terminators if t.optional]

    if procs_normal:   lines.append(f"    class {','.join(procs_normal)} proc;")
    if procs_brain:    lines.append(f"    class {','.join(procs_brain)} brain;")
    if procs_optional: lines.append(f"    class {','.join(procs_optional)} optional;")
    if store_ids:      lines.append(f"    class {','.join(store_ids)} store;")
    if terms_normal:   lines.append(f"    class {','.join(terms_normal)} terminator;")
    if terms_grid:     lines.append(f"    class {','.join(terms_grid)} grid;")
    if terms_optional: lines.append(f"    class {','.join(terms_optional)} termopt;")

    return "\n".join(lines) + "\n"


def _tx_label(t: Transition) -> str:
    """Pick a transition's diagram label — `label` if set, otherwise `event`."""
    return _esc(t.label or t.event)


def render_state_machine(project: Project, parent_machine_id: str) -> str:
    """Render a CSPEC state machine as Mermaid stateDiagram-v2.

    `parent_machine_id` is the process entity whose CSPEC contains the
    states and transitions. States are identified by their `label`
    (Mermaid uses label-as-identifier in stateDiagram-v2).

    Hierarchy: composite states get their own `state X { ... }` blocks
    containing their sub-states. A transition whose source and target are
    both substates of the same composite is emitted *inside* that
    composite's block; all other transitions go at the top level.

    Initial states are marked with `is_initial: true` in the dictionary
    (one for the whole machine, one per composite).
    """
    machine = project.entities.get(parent_machine_id)
    if machine is None:
        raise ValueError(f"Parent machine {parent_machine_id!r} not in project")

    all_states = [
        e for e in project.all_entities()
        if e.parent == parent_machine_id
        and e.kind in (EntityKind.STATE, EntityKind.STATE_COMPOSITE)
    ]
    top_level_states = [s for s in all_states if not s.parent_state]
    composite_states = [s for s in all_states if s.kind == EntityKind.STATE_COMPOSITE]

    transitions = project.transitions_for(parent_machine_id)

    # Partition transitions: inside-composite vs top-level
    composite_txns: dict[str, list[Transition]] = {c.id: [] for c in composite_states}
    top_txns: list[Transition] = []
    for t in transitions:
        src = project.entities.get(t.source_state)
        tgt = project.entities.get(t.target_state)
        if src and tgt and src.parent_state and src.parent_state == tgt.parent_state:
            composite_txns[src.parent_state].append(t)
        else:
            top_txns.append(t)

    # Find the machine-level initial state
    initial_top = next((s for s in top_level_states if s.is_initial), None)

    lines: list[str] = ["stateDiagram-v2", "    direction LR", ""]

    if initial_top:
        lines.append(f"    [*] --> {initial_top.label}")
        lines.append("")

    # Top-level transitions
    for t in top_txns:
        src_label = project.entities[t.source_state].label
        tgt_label = project.entities[t.target_state].label
        lines.append(f"    {src_label} --> {tgt_label} : {_tx_label(t)}")
    lines.append("")

    # Composite blocks
    for comp in composite_states:
        lines.append(f"    state {comp.label} {{")
        lines.append("        direction LR")
        substates = [s for s in all_states if s.parent_state == comp.id]
        initial_sub = next((s for s in substates if s.is_initial), None)
        if initial_sub:
            lines.append(f"        [*] --> {initial_sub.label}")
        # Substates that have no transitions to/from (e.g., siblings in Fault)
        # need to be declared explicitly so they appear in the diagram
        referenced_in_block: set[str] = set()
        if initial_sub:
            referenced_in_block.add(initial_sub.id)
        for t in composite_txns[comp.id]:
            referenced_in_block.add(t.source_state)
            referenced_in_block.add(t.target_state)
        # Declare unreferenced sub-states with bare labels
        for s in substates:
            if s.id not in referenced_in_block:
                lines.append(f"        {s.label}")
        # Inner transitions
        for t in composite_txns[comp.id]:
            src_label = project.entities[t.source_state].label
            tgt_label = project.entities[t.target_state].label
            lines.append(f"        {src_label} --> {tgt_label} : {_tx_label(t)}")
        lines.append("    }")
        lines.append("")

    return "\n".join(lines) + "\n"


# ─────────────────────────────────────────────────────────────────────
# Stage 5 — Architecture Model (AFD + AID)
#
# Modules render as Mermaid rounded rectangles (id(Name)) — distinct from
# the DFD's process circles. Architecture flows are arrows. Architecture
# interconnects (AID) use undirected edges with thicker/dashed styling
# to signal "physical channel, not flow".
# ─────────────────────────────────────────────────────────────────────


def _am_node_decl(m: ArchModule) -> str:
    """Mermaid declaration for an architecture module — rounded rectangle.

    Label includes the optional module_number on a second line.
    """
    label = _esc(m.name)
    if m.module_number:
        label = f"{label}<br/><i>{_esc(m.module_number)}</i>"
    return f'    {m.id}("{label}")'


def _af_edge(f: ArchFlow) -> str:
    """Mermaid edge declaration for an architecture flow."""
    label = _esc(f.name)
    # Differentiate flow kind in label (data/material/energy)
    if f.kind.value != "data":
        label = f"{label} <i>({f.kind.value})</i>"
    return f'    {f.source} -- "{label}" --> {f.target}'


def render_afd(project: Project, parent_id: str | None = None) -> str:
    """Render an Architecture Flow Diagram as Mermaid.

    `parent_id` selects the layer: None renders the top-level (modules
    with no parent — the root AFD); otherwise renders the decomposition
    of that module (children whose `parent` is `parent_id`).
    """
    modules = [m for m in project.all_architecture_modules() if m.parent == parent_id]
    if not modules:
        return "%% (no architecture modules at this layer)\n"

    module_ids = {m.id for m in modules}

    # Architecture flows whose endpoints are both in this layer
    flows = [f for f in project.all_architecture_flows()
             if f.source in module_ids and f.target in module_ids]

    lines: list[str] = ["graph LR"]
    lines.append("    %% Architecture modules")
    for m in modules:
        lines.append(_am_node_decl(m))
    lines.append("")

    if flows:
        lines.append("    %% Architecture flows")
        for f in flows:
            lines.append(_af_edge(f))
        lines.append("")

    # Styling by module kind
    lines.append("    classDef hardware fill:#fff4e6,stroke:#d68910,stroke-width:2px;")
    lines.append("    classDef software fill:#e8f0fe,stroke:#4a90e2,stroke-width:2px;")
    lines.append("    classDef organizational fill:#f4f4f4,stroke:#555,stroke-width:2px;")
    for m in modules:
        lines.append(f"    class {m.id} {m.kind.value};")

    return "\n".join(lines) + "\n"


def render_aid(project: Project, parent_id: str | None = None) -> str:
    """Render an Architecture Interconnect Diagram as Mermaid.

    Shows modules + physical channels (interconnects) between them. Each
    interconnect connects ≥ 2 modules; rendered as labeled edges between
    every pair of endpoints (Mermaid doesn't natively support hyperedges).
    """
    modules = [m for m in project.all_architecture_modules() if m.parent == parent_id]
    if not modules:
        return "%% (no architecture modules at this layer)\n"

    module_ids = {m.id for m in modules}
    # Interconnects with ≥ 2 endpoints in this layer
    interconnects = [
        ic for ic in project.all_architecture_interconnects()
        if sum(1 for ep in ic.endpoints if ep in module_ids) >= 2
    ]

    lines: list[str] = ["graph LR"]
    lines.append("    %% Architecture modules")
    for m in modules:
        lines.append(_am_node_decl(m))
    lines.append("")

    if interconnects:
        lines.append("    %% Interconnects (physical channels)")
        for ic in interconnects:
            eps = [ep for ep in ic.endpoints if ep in module_ids]
            label = _esc(ic.name)
            # Draw as a chain of undirected thick links between endpoints
            for i in range(len(eps) - 1):
                lines.append(f'    {eps[i]} === |"{label}"| {eps[i+1]}')
        lines.append("")

    lines.append("    classDef hardware fill:#fff4e6,stroke:#d68910,stroke-width:2px;")
    lines.append("    classDef software fill:#e8f0fe,stroke:#4a90e2,stroke-width:2px;")
    lines.append("    classDef organizational fill:#f4f4f4,stroke:#555,stroke-width:2px;")
    for m in modules:
        lines.append(f"    class {m.id} {m.kind.value};")

    return "\n".join(lines) + "\n"


# ─────────────────────────────────────────────────────────────────────
# Modernization #5 — Context Map (Evans 2003 / Vernon 2013)
# ─────────────────────────────────────────────────────────────────────


def render_context_map(project: Project) -> str:
    """Render the Context Map — bounded contexts + ACL translations between them."""
    if not project.bounded_contexts:
        return "%% (no bounded_contexts declared)\n"

    lines: list[str] = ["graph LR"]
    lines.append("    %% Bounded contexts (rounded rectangles)")
    for ctx in project.all_bounded_contexts():
        label = _esc(ctx.name)
        if ctx.owner:
            label = f"{label}<br/><i>{_esc(ctx.owner)}</i>"
        lines.append(f'    {ctx.id}("{label}")')
    lines.append("")

    translations = project.all_translations()
    if translations:
        lines.append("    %% Anti-Corruption Layers (translation entities)")
        for t in translations:
            if not (t.source_context and t.target_context):
                continue
            label = _esc(t.label or t.id)
            if t.pattern:
                label = f"{label}<br/><i>{t.pattern.value.replace('_', ' ')}</i>"
            lines.append(f'    {t.source_context} -- "{label}" --> {t.target_context}')
        lines.append("")

    lines.append("    classDef bctx fill:#f0f4ff,stroke:#4a90e2,stroke-width:2px;")
    for ctx in project.all_bounded_contexts():
        lines.append(f"    class {ctx.id} bctx;")

    return "\n".join(lines) + "\n"
