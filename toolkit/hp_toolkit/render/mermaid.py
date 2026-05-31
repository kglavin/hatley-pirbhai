"""Mermaid renderer — emit Mermaid `graph LR` source from a Project model.

Currently supports: level-0 Context Diagram. Level-N DFD rendering will
follow once the dictionary models boundary-flow refinement.
"""

from __future__ import annotations

from ..model import Project, Entity, Flow, Edge, EntityKind, FlowKind


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
