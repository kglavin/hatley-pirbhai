"""D2 renderer — emit D2 declarative source from a Project model.

Currently supports: level-0 Context Diagram.
"""

from __future__ import annotations

from ..model import Project, Entity, Flow, Edge, EntityKind


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
    label = _esc(ed.label) if ed.label else "AC power"
    # Undirected (--) with red coloring for physical edges
    return (
        f'{ed.source} -- {ed.target}: "{label}" {{\n'
        '  style.stroke: "#e74c3c"\n'
        "  style.stroke-width: 3\n"
        "  style.opacity: 0.7\n"
        "}"
    )


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
