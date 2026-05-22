"""Renderers — generate diagram sources from the Project model.

Each submodule emits a different target notation:

    mermaid.render_context_diagram(project) -> str   # Mermaid `graph LR` source
    d2.render_context_diagram(project)      -> str   # D2 source

Renderers are deterministic: the same input model produces byte-identical
output. Iteration order is dictionary order (which is YAML insertion order
for our purposes).

Scope:
- ✅ Level-0 Context Diagram (Mermaid, D2)
- Planned: Level-N DFD rendering (requires schema extension for boundary-flow
  refinement at deeper levels — the dictionary needs to know which internal
  process at level N+1 consumes a level-N boundary flow)
- Planned: Cytoscape elements JSON (for HTML5 interactive workspace)
- Planned: State machine rendering (requires transitions schema)
- Planned: SVG orchestration (invoke d2 / mmdc on generated sources)
"""

from . import mermaid, d2, cytoscape, svg

__all__ = ["mermaid", "d2", "cytoscape", "svg"]
