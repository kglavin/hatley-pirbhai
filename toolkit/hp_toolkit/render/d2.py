"""D2 renderer — emit D2 declarative source from a Project model.

Currently supports: level-0 Context Diagram.
"""

from __future__ import annotations

from ..model import Project, Entity, Flow, Edge, Transition, EntityKind


def _esc(text: str) -> str:
    """Quote a D2 string — escape internal quotes."""
    return text.replace('"', '\\"').replace("\n", "\\n")


def _node_decl(e: Entity) -> list[str]:
    """D2 declaration for an entity. Returns multiple lines (D2 blocks)."""
    label = _esc(e.label)
    if e.kind == EntityKind.SYSTEM:
        return [
            f'{e.id}: "{label}" {{',
            "  shape: oval",
            '  style.fill: "#4a90e2"',
            "  style.font-color: white",
            "  style.bold: true",
            "  style.font-size: 18",
            "}",
        ]
    if e.kind == EntityKind.TERMINATOR:
        block = [
            f'{e.id}: "{label}" {{',
            "  shape: rectangle",
        ]
        if "grid" in e.id:
            block.extend([
                '  style.fill: "#fef0ef"',
                '  style.stroke: "#e74c3c"',
            ])
        if e.optional:
            block.extend([
                "  style.stroke-dash: 5",
                "  style.opacity: 0.55",
                '  style.font-color: "#666"',
            ])
        block.append("}")
        return block
    if e.kind == EntityKind.DATA_STORE:
        return [
            f'{e.id}: "{label}" {{',
            "  shape: cylinder",
            '  style.fill: "#fff5cc"',
            "}",
        ]
    return [f'{e.id}: "{label}"']


def _flow_edge(f: Flow) -> str:
    label = _esc(f.label)
    if f.optional:
        return (
            f'{f.source} -> {f.target}: "{label}" {{\n'
            '  style.stroke-dash: 5\n'
            '  style.opacity: 0.6\n'
            '}'
        )
    return f'{f.source} -> {f.target}: "{label}"'


def _edge_decl(ed: Edge) -> str:
    """D2 declaration for a non-data edge, styled by EdgeKind."""
    label = _esc(ed.label) if ed.label else ""
    from ..model import EdgeKind as _EK
    if ed.kind == _EK.PHYSICAL_AC_POWER:
        stroke, width, opacity, dash = "#e74c3c", 3, 0.7, None
        if not label:
            label = "AC power"
    elif ed.kind == _EK.PHYSICAL_DC_POWER:
        stroke, width, opacity, dash = "#2a70c2", 3, 0.7, None
        if not label:
            label = "DC power"
    elif ed.kind == _EK.PHYSICAL_INTERACTION:
        stroke, width, opacity, dash = "#888", 2, 0.6, 4
        if not label:
            label = ""
    else:
        stroke, width, opacity, dash = "#888", 2, 0.7, None

    decl = [f'{ed.source} -- {ed.target}: "{label}" {{',
            f'  style.stroke: "{stroke}"',
            f'  style.stroke-width: {width}',
            f'  style.opacity: {opacity}']
    if dash is not None:
        decl.append(f'  style.stroke-dash: {dash}')
    decl.append("}")
    return "\n".join(decl)


def render_context_diagram(project: Project) -> str:
    """Render the level-0 Context Diagram as a D2 source string."""
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

    lines: list[str] = ["direction: right", ""]
    lines.append("# --- System under design ---")
    lines.extend(_node_decl(system))
    lines.append("")
    lines.append("# --- Terminators ---")
    for t in terminators:
        lines.extend(_node_decl(t))
    lines.append("")
    lines.append("# --- Flows ---")
    for f in flows:
        lines.append(_flow_edge(f))
    if edges:
        lines.append("")
        lines.append("# --- Physical AC power ---")
        for ed in edges:
            lines.append(_edge_decl(ed))

    return "\n".join(lines) + "\n"


def _process_decl(p: Entity) -> list[str]:
    """D2 block for a process — styled by needs_cspec / optional."""
    label = _esc(p.label)
    block = [f'{p.id}: "{label}" {{', "  shape: oval"]
    if p.needs_cspec:
        block.append('  style.fill: "#7fbff5"')
        block.append("  style.bold: true")
    elif p.optional:
        block.append('  style.fill: "#e6f0ff"')
        block.append("  style.stroke-dash: 3")
        block.append("  style.opacity: 0.7")
    else:
        block.append('  style.fill: "#cfe5ff"')
    block.append("}")
    return block


def render_dfd(project: Project, parent_id: str = "sys_root") -> str:
    """Render a level-N+1 DFD (decomposition of `parent_id`) as D2.

    Same content as `mermaid.render_dfd` — internal processes + stores,
    boundary flows refined, internal flows, physical edges.
    """
    parent = project.entities.get(parent_id)
    if parent is None:
        raise ValueError(f"Parent {parent_id!r} not in project")

    internal = [e for e in project.all_entities()
                if e.parent == parent_id and e.level == 1]
    processes = [e for e in internal if e.kind == EntityKind.PROCESS]
    stores    = [e for e in internal if e.kind == EntityKind.DATA_STORE]

    boundary_flows = [f for f in project.flows_at_level(0)
                      if f.source == parent_id or f.target == parent_id]

    term_ids: set[str] = set()
    for f in boundary_flows:
        if f.source != parent_id:
            term_ids.add(f.source)
        if f.target != parent_id:
            term_ids.add(f.target)
    edges_level0 = [ed for ed in project.all_edges() if ed.level == 0]
    for ed in edges_level0:
        if project.entities.get(ed.source) and project.entities[ed.source].kind == EntityKind.TERMINATOR:
            term_ids.add(ed.source)
        if project.entities.get(ed.target) and project.entities[ed.target].kind == EntityKind.TERMINATOR:
            term_ids.add(ed.target)
    terminators = [project.entity(tid) for tid in term_ids
                   if project.entity(tid).kind == EntityKind.TERMINATOR]

    internal_flows = list(project.flows_at_level(1))

    lines: list[str] = ["direction: right", ""]

    lines.append("# --- Terminators ---")
    for t in terminators:
        lines.extend(_node_decl(t))
    lines.append("")

    lines.append("# --- Internal processes ---")
    for p in processes:
        lines.extend(_process_decl(p))
    lines.append("")

    if stores:
        lines.append("# --- Data store ---")
        for s in stores:
            lines.extend(_node_decl(s))
        lines.append("")

    lines.append("# --- Boundary flows (refined) ---")
    for f in boundary_flows:
        src = f.refined_source if f.source == parent_id and f.refined_source else f.source
        tgt = f.refined_target if f.target == parent_id and f.refined_target else f.target
        label = _esc(f.label)
        if f.optional:
            lines.append(f'{src} -> {tgt}: "{label}" {{')
            lines.append("  style.stroke-dash: 5")
            lines.append("  style.opacity: 0.6")
            lines.append("}")
        else:
            lines.append(f'{src} -> {tgt}: "{label}"')
    lines.append("")

    if edges_level0:
        lines.append("# --- Physical AC ---")
        for ed in edges_level0:
            lines.append(_edge_decl(ed))
        lines.append("")

    lines.append("# --- Internal flows ---")
    for f in internal_flows:
        lines.append(_flow_edge(f))

    return "\n".join(lines) + "\n"


def _tx_label(t: Transition) -> str:
    return _esc(t.label or t.event)


def render_state_machine(project: Project, parent_machine_id: str) -> str:
    """Render a CSPEC state machine as D2 with container blocks for
    composite states. References to sub-states from outside their
    composite use dot notation (e.g., `Fault.TelemetryFault`)."""
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
    atomic_top_states = [s for s in top_level_states if s.kind == EntityKind.STATE]

    transitions = project.transitions_for(parent_machine_id)

    # Partition transitions
    composite_txns: dict[str, list[Transition]] = {c.id: [] for c in composite_states}
    cross_txns: list[Transition] = []
    for t in transitions:
        src = project.entities.get(t.source_state)
        tgt = project.entities.get(t.target_state)
        if src and tgt and src.parent_state and src.parent_state == tgt.parent_state:
            composite_txns[src.parent_state].append(t)
        else:
            cross_txns.append(t)

    initial_top = next((s for s in top_level_states if s.is_initial), None)

    lines: list[str] = ["direction: right", ""]

    # Start pseudo-state
    lines.extend([
        'start: "●" {',
        '  shape: circle',
        '  style.fill: "#222"',
        '  width: 30',
        '  height: 30',
        "}",
        "",
    ])

    # Top-level atomic states (e.g., Initializing)
    for s in atomic_top_states:
        lines.append(f'{s.label}: {{ shape: oval; style.fill: "#e8e8e8" }}')
    lines.append("")

    # Composite state containers
    for comp in composite_states:
        # Choose styling per composite by name (heuristic)
        if comp.id == "state_grid_tie":
            fill, stroke = "#e6f3ff", "#2a70c2"
        elif comp.id == "state_island":
            fill, stroke = "#fff3e6", "#d68910"
        elif comp.id == "state_fault":
            fill, stroke = "#fee6e6", "#c0392b"
        else:
            fill, stroke = "#f0f0f0", "#888"

        lines.append(f'{comp.label}: {{')
        lines.append(f'  label: "{comp.label}"')
        lines.append(f'  style.fill: "{fill}"')
        lines.append(f'  style.stroke: "{stroke}"')
        lines.append("")

        substates = [s for s in all_states if s.parent_state == comp.id]
        for s in substates:
            lines.append(f'  {s.label}: {{ shape: oval; style.fill: "#fff" }}')

        # Inner transitions
        if composite_txns[comp.id]:
            lines.append("")
            for t in composite_txns[comp.id]:
                src_label = project.entities[t.source_state].label
                tgt_label = project.entities[t.target_state].label
                lines.append(f'  {src_label} -> {tgt_label}: "{_tx_label(t)}"')

        lines.append("}")
        lines.append("")

    # Cross-state transitions (use dot notation for substate targets if needed)
    def _ref(state_id: str) -> str:
        """D2 reference — dotted if the state is inside a composite."""
        s = project.entities[state_id]
        if s.parent_state:
            parent_label = project.entities[s.parent_state].label
            return f"{parent_label}.{s.label}"
        return s.label

    lines.append("# --- Cross-state transitions ---")
    if initial_top:
        lines.append(f"start -> {_ref(initial_top.id)}")
    for t in cross_txns:
        lines.append(f'{_ref(t.source_state)} -> {_ref(t.target_state)}: "{_tx_label(t)}"')

    return "\n".join(lines) + "\n"
