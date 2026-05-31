"""Cytoscape renderer — generate the elements JSON and a self-contained
HTML workspace from the Project model.

The Cytoscape output has two parts:
    1. Elements list   — list of {data: {...}} dicts; one per node/edge.
                         JSON-serializable; this is the model-driven part.
    2. HTML wrapper    — page scaffold (styles, side panel, navigation,
                         JavaScript for tap/dbltap handlers, legend).
                         Mostly static; differs per view in legend +
                         style array + navigation links.

Functions:
    render_context_elements(project)            -> list[dict]
    wrap_context_html(project, elements)        -> str (full HTML)
"""

from __future__ import annotations

import json
from typing import Any

from ..model import (
    Project,
    Entity,
    Flow,
    Edge,
    EntityKind,
    FlowKind,
    EdgeKind,
    ArchModule,
    ArchFlow,
    ArchInterconnect,
    ArchModuleKind,
)
from .sidebar import SIDEBAR_CSS, SIDEBAR_JS, _path_prefix_for, render_sidebar_html
from .tree import TreeNode


def _hp_ref_base(current_path: str | None) -> str:
    """Compute the host-page-relative path to toolkit/reference/HP_QUICK_REF.md.

    Project layout is `<repo>/examples/<project>/<current_path>`, so we need
    `_path_prefix_for(current_path)` (to reach project root) plus `../../` (to
    cross examples/<project> to repo root) plus `toolkit/reference/...`."""
    prefix = _path_prefix_for(current_path or "")
    return prefix + "../../toolkit/reference/HP_QUICK_REF.md"


def _sidebar_fields(tree: TreeNode | None, current_path: str | None) -> dict[str, str]:
    """Build the placeholder values for the HTML template.

    Returns empty strings for sidebar fields when `tree` is None — preserves
    back-compat for direct callers that don't yet pass a tree. `hp_ref_base`
    is always computed since the JS reference link uses it."""
    base = {"hp_ref_base": _hp_ref_base(current_path)}
    if tree is None:
        return {**base, "sidebar_html": "", "sidebar_css": "", "sidebar_js": ""}
    return {
        **base,
        "sidebar_html": render_sidebar_html(tree, current_path),
        "sidebar_css": SIDEBAR_CSS,
        "sidebar_js": SIDEBAR_JS,
    }


# ─────────────────────────────────────────────────────────────────────
# Kind mapping — translate model kinds + qualifiers to Cytoscape kind
# tags (which the HTML wrapper's style array selects on).
# ─────────────────────────────────────────────────────────────────────

def _node_kind(e: Entity) -> str:
    if e.kind == EntityKind.SYSTEM:
        return "system"
    if e.kind == EntityKind.TERMINATOR:
        if e.optional:
            return "terminator-optional"
        if "grid" in e.id:
            return "terminator-grid"
        return "terminator"
    if e.kind == EntityKind.PROCESS:
        if e.needs_cspec:
            return "process-brain"
        if e.optional:
            return "process-optional"
        return "process"
    if e.kind == EntityKind.DATA_STORE:
        return "datastore"
    if e.kind == EntityKind.STATE:
        if e.is_initial and not e.parent_state:
            return "state-init"
        return "state"
    if e.kind == EntityKind.STATE_COMPOSITE:
        return f"mode-{e.id.replace('state_', '').replace('_', '-')}"
    return e.kind.value


def _flow_kind(f: Flow) -> str:
    if f.kind == FlowKind.DATA_AND_CONTROL:
        return "data" if not f.optional else "data-optional"
    if f.optional:
        return f"{f.kind.value}-optional"
    return f.kind.value


# ─────────────────────────────────────────────────────────────────────
# Context Diagram — elements list
# ─────────────────────────────────────────────────────────────────────

def render_context_elements(
    project: Project,
    drill_target: str | None = "../01-level1/dfd.generated.html",
) -> list[dict[str, Any]]:
    """Produce the Cytoscape elements list for the level-0 Context Diagram.

    `drill_target` is the URL the system bubble's double-click navigates to.
    Set to None if no level-1 DFD exists yet (the system bubble then renders
    without the decomposable double-border).
    """
    elements: list[dict[str, Any]] = []

    system = next(
        (e for e in project.all_entities()
         if e.kind == EntityKind.SYSTEM and e.level == 0),
        None,
    )
    if system is None:
        raise ValueError("Project has no level-0 system entity")

    sys_data: dict[str, Any] = {
        "id": system.id,
        "label": system.label,
        "kind": _node_kind(system),
        "description": system.description or "",
    }
    if drill_target:
        sys_data["decomposable"] = True
        sys_data["decomposes_to"] = drill_target
        sys_data["decomposes_label"] = "Level-1 DFD (internal processes)"
    elements.append({"data": sys_data})

    # Terminators
    for t in [e for e in project.all_entities()
              if e.kind == EntityKind.TERMINATOR and e.level == 0]:
        label = t.label + ("\n(optional)" if t.optional else "")
        elements.append({
            "data": {
                "id": t.id,
                "label": label,
                "kind": _node_kind(t),
                "description": t.description or "",
            }
        })

    # Boundary flows (F1–F8)
    for f in project.flows_at_level(0):
        node: dict[str, Any] = {
            "data": {
                "id": f.id,
                "source": f.source,
                "target": f.target,
                "label": f.label,
                "kind": _flow_kind(f),
            }
        }
        if f.medium:
            node["data"]["medium"] = f.medium
        if f.notes:
            node["data"]["notes"] = f.notes
        elements.append(node)

    # Physical AC edges
    for ed in [e for e in project.all_edges() if e.level == 0]:
        elements.append({
            "data": {
                "id": ed.id,
                "source": ed.source,
                "target": ed.target,
                "label": ed.label or "AC power",
                "kind": "power",
            }
        })

    return elements


# ─────────────────────────────────────────────────────────────────────
# HTML wrapper for the Context view
# ─────────────────────────────────────────────────────────────────────

_ALL_STYLES_JSON: list[dict[str, Any]] = [
    {
        "selector": 'node[kind="system"]',
        "style": {
            "shape": "ellipse", "background-color": "#4a90e2", "color": "#fff",
            "label": "data(label)", "text-valign": "center", "text-halign": "center",
            "text-wrap": "wrap", "width": 170, "height": 170,
            "font-weight": "bold", "font-size": 13,
            "border-width": 2, "border-color": "#2a70c2",
        }
    },
    {
        "selector": 'node[kind="process"]',
        "style": {
            "shape": "ellipse", "background-color": "#cfe5ff", "color": "#000",
            "border-color": "#2a70c2", "border-width": 1,
            "label": "data(label)", "text-valign": "center", "text-halign": "center",
            "text-wrap": "wrap", "width": 110, "height": 110, "font-size": 11,
        }
    },
    {
        "selector": 'node[kind="process-brain"]',
        "style": {
            "shape": "ellipse", "background-color": "#7fbff5", "color": "#000",
            "border-color": "#1f5a99", "border-width": 2,
            "label": "data(label)", "text-valign": "center", "text-halign": "center",
            "text-wrap": "wrap", "width": 130, "height": 130,
            "font-weight": "bold", "font-size": 12,
        }
    },
    {
        "selector": 'node[kind="process-optional"]',
        "style": {
            "shape": "ellipse", "background-color": "#e6f0ff", "color": "#444",
            "border-color": "#888", "border-width": 1, "border-style": "dashed",
            "label": "data(label)", "text-valign": "center", "text-halign": "center",
            "text-wrap": "wrap", "width": 110, "height": 110,
            "font-size": 11, "opacity": 0.85,
        }
    },
    {
        "selector": 'node[kind="datastore"]',
        "style": {
            # Cytoscape doesn't have a 'cylinder' shape (Mermaid/D2 do).
            # 'barrel' is the closest visual analog for a data-store icon.
            "shape": "barrel", "background-color": "#fff5cc", "color": "#222",
            "border-color": "#b89800", "border-width": 1,
            "label": "data(label)", "text-valign": "center", "text-halign": "center",
            "text-wrap": "wrap", "width": 130, "height": 70, "font-size": 11,
        }
    },
    {
        "selector": 'node[kind="terminator"]',
        "style": {
            "shape": "rectangle", "background-color": "#fafafa", "border-color": "#444",
            "border-width": 1, "label": "data(label)", "color": "#222",
            "text-valign": "center", "text-halign": "center", "text-wrap": "wrap",
            "width": 120, "height": 60, "padding": 8, "font-size": 11,
        }
    },
    {
        "selector": 'node[kind="terminator-grid"]',
        "style": {
            "shape": "rectangle", "background-color": "#fef0ef", "border-color": "#e74c3c",
            "border-width": 1, "label": "data(label)", "color": "#c0392b",
            "text-valign": "center", "text-halign": "center", "text-wrap": "wrap",
            "width": 120, "height": 60, "padding": 8, "font-size": 11,
        }
    },
    {
        "selector": 'node[kind="terminator-optional"]',
        "style": {
            "shape": "rectangle", "background-color": "#fafafa", "border-color": "#888",
            "border-width": 1, "border-style": "dashed", "label": "data(label)",
            "color": "#666",
            "text-valign": "center", "text-halign": "center", "text-wrap": "wrap",
            "width": 120, "height": 60, "padding": 8, "font-size": 11,
        }
    },
    {
        "selector": 'node[?decomposable]',
        "style": {"border-width": 4, "border-style": "double"},
    },
    {
        "selector": 'edge[kind="data"], edge[kind="control"], edge[kind="data+control"]',
        "style": {
            "curve-style": "bezier", "target-arrow-shape": "triangle",
            "target-arrow-color": "#444", "line-color": "#444", "width": 1.5,
            "label": "data(label)", "font-size": 9, "text-rotation": "autorotate",
            "text-background-color": "#fafafa", "text-background-opacity": 0.9,
            "text-background-padding": 2, "color": "#333",
        }
    },
    {
        "selector": 'edge[kind="data-optional"], edge[kind="control-optional"], edge[kind="data+control-optional"]',
        "style": {
            "curve-style": "bezier", "target-arrow-shape": "triangle",
            "target-arrow-color": "#888", "line-color": "#888",
            "line-style": "dashed", "width": 1.5,
            "label": "data(label)", "font-size": 9, "text-rotation": "autorotate",
            "text-background-color": "#fafafa", "text-background-opacity": 0.9,
            "text-background-padding": 2, "color": "#888",
        }
    },
    {
        "selector": 'edge[kind="power"], edge[kind="physical_ac_power"]',
        "style": {
            "curve-style": "bezier", "line-color": "#e74c3c", "width": 3,
            "opacity": 0.7, "label": "data(label)", "font-size": 8,
            "text-rotation": "autorotate", "color": "#c0392b",
            "text-background-color": "#fafafa", "text-background-opacity": 0.8,
            "text-background-padding": 2,
        }
    },
    {
        "selector": 'edge[kind="physical_dc_power"]',
        "style": {
            "curve-style": "bezier", "line-color": "#2a70c2", "width": 3,
            "opacity": 0.6, "label": "data(label)", "font-size": 8,
            "text-rotation": "autorotate", "color": "#1f5a99",
            "text-background-color": "#fafafa", "text-background-opacity": 0.8,
            "text-background-padding": 2,
        }
    },
    {
        "selector": 'edge[kind="physical_interaction"]',
        "style": {
            "curve-style": "bezier", "line-color": "#888", "width": 2,
            "line-style": "dashed", "opacity": 0.6,
            "label": "data(label)", "font-size": 8,
            "text-rotation": "autorotate", "color": "#666",
            "text-background-color": "#fafafa", "text-background-opacity": 0.8,
            "text-background-padding": 2,
        }
    },
    # ─── State machine styling (CSPEC views) ───
    {
        "selector": 'node[kind="state"]',
        "style": {
            "shape": "ellipse", "background-color": "#fff", "color": "#000",
            "border-color": "#444", "border-width": 1,
            "label": "data(label)", "text-valign": "center", "text-halign": "center",
            "text-wrap": "wrap", "width": 110, "height": 70, "font-size": 11,
        }
    },
    {
        "selector": 'node[kind="state-init"]',
        "style": {
            "shape": "ellipse", "background-color": "#e8e8e8", "color": "#000",
            "border-color": "#888", "border-width": 1,
            "label": "data(label)", "text-valign": "center", "text-halign": "center",
            "text-wrap": "wrap", "width": 110, "height": 70, "font-size": 11,
        }
    },
    # Composite-state containers — per-mode coloring with fallback.
    {
        "selector": 'node[kind="mode-grid-tie"]',
        "style": {
            "shape": "round-rectangle", "background-color": "#e6f3ff",
            "background-opacity": 0.5,
            "border-color": "#2a70c2", "border-width": 2,
            "label": "data(label)", "text-valign": "top", "text-halign": "center",
            "font-size": 13, "font-weight": "bold", "color": "#1a5fa0", "padding": 15,
        }
    },
    {
        "selector": 'node[kind="mode-island"]',
        "style": {
            "shape": "round-rectangle", "background-color": "#fff3e6",
            "background-opacity": 0.5,
            "border-color": "#d68910", "border-width": 2,
            "label": "data(label)", "text-valign": "top", "text-halign": "center",
            "font-size": 13, "font-weight": "bold", "color": "#9a6707", "padding": 15,
        }
    },
    {
        "selector": 'node[kind="mode-fault"]',
        "style": {
            "shape": "round-rectangle", "background-color": "#fee6e6",
            "background-opacity": 0.5,
            "border-color": "#c0392b", "border-width": 2,
            "label": "data(label)", "text-valign": "top", "text-halign": "center",
            "font-size": 13, "font-weight": "bold", "color": "#7a1f12", "padding": 15,
        }
    },
    # Generic transition edges (state machines)
    {
        "selector": 'edge[kind="tx"]',
        "style": {
            "curve-style": "bezier", "target-arrow-shape": "triangle",
            "target-arrow-color": "#444", "line-color": "#444", "width": 1.5,
            "label": "data(label)", "font-size": 9, "text-rotation": "autorotate",
            "text-background-color": "#fafafa", "text-background-opacity": 0.9,
            "text-background-padding": 2, "color": "#333",
        }
    },
    {
        "selector": 'edge[kind="tx-mode"]',
        "style": {
            "curve-style": "bezier", "target-arrow-shape": "triangle",
            "target-arrow-color": "#9a6707", "line-color": "#9a6707", "width": 2,
            "label": "data(label)", "font-size": 9, "text-rotation": "autorotate",
            "text-background-color": "#fafafa", "text-background-opacity": 0.9,
            "text-background-padding": 2, "color": "#7a4f00",
        }
    },
    {
        "selector": 'node[?decomposable]',
        "style": {"border-width": 4, "border-style": "double"},
    },
    {
        "selector": ':selected',
        "style": {
            "border-color": "#f39c12", "border-width": 3,
            "line-color": "#f39c12", "target-arrow-color": "#f39c12",
        }
    },
]

# Back-compat alias for existing references (some scripts still import it)
_CONTEXT_STYLES_JSON = _ALL_STYLES_JSON


_CONTEXT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <script src="https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js"></script>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; }}
    body {{ display: flex; }}
    #cy {{ flex: 1; background: #fafafa; min-width: 0; }}
    #panel {{ width: 340px; padding: 18px; background: #fff; border-left: 1px solid #ddd; overflow-y: auto; font-size: 13px; line-height: 1.5; }}
    #panel h1 {{ font-size: 15px; margin: 0 0 6px; color: #222; }}
    #panel .sub {{ color: #888; font-size: 11px; margin-bottom: 16px; }}
    #panel h2 {{ font-size: 13px; margin: 18px 0 6px; color: #333; border-bottom: 1px solid #eee; padding-bottom: 4px; }}
    #panel p {{ margin: 6px 0; }}
    #panel .label {{ font-weight: 600; color: #444; }}
    #info {{ min-height: 80px; }}
    #info .placeholder {{ color: #999; font-style: italic; }}
    .legend-item {{ display: flex; align-items: center; margin: 6px 0; font-size: 12px; }}
    .legend-swatch {{ width: 28px; height: 16px; margin-right: 10px; border-radius: 2px; flex-shrink: 0; }}
    .controls button {{ padding: 4px 10px; margin: 2px 4px 2px 0; font-size: 11px; border: 1px solid #ccc; background: #f6f6f6; border-radius: 3px; cursor: pointer; }}
{sidebar_css}
  </style>
</head>
<body>
  {sidebar_html}
  <div id="cy"></div>
  <div id="panel">
    <h1>{title}</h1>
    <div class="sub">{subtitle}</div>

    <h2>Navigation</h2>
    {nav_html}

    <h2>Selected</h2>
    <div id="info"><div class="placeholder">Click a node or edge to see details. Drag nodes to rearrange.</div></div>

    <h2>Legend</h2>
    {legend_html}

    <h2>Controls</h2>
    <div class="controls">
      <button onclick="cy.fit(undefined, 30); cy.center();">Fit</button>
      <button onclick="cy.layout({{name:'cose', nodeRepulsion: 8000, idealEdgeLength: 130, padding: 40, animate: true}}).run();">Re-layout</button>
    </div>
  </div>

  <script>
    var elements = {elements_json};
    var styles   = {styles_json};

    var cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: elements,
      style: styles,
      layout: {{ name: 'cose', nodeRepulsion: 8000, idealEdgeLength: 130, padding: 40 }}
    }});

    var hpRefMap = {{
      'system': '#process-bubble',
      'terminator': '#terminator',
      'terminator-grid': '#terminator',
      'terminator-optional': '#terminator',
    }};
    var hpRefBase = '{hp_ref_base}';

    function render(html) {{ document.getElementById('info').innerHTML = html; }}

    var lastTapTime = 0, lastTapId = null;
    var DOUBLE_TAP_MS = 350;

    cy.on('tap', 'node', function(evt) {{
      var d = evt.target.data();
      var now = Date.now();
      var isDouble = (lastTapId === d.id) && (now - lastTapTime < DOUBLE_TAP_MS);
      lastTapTime = now; lastTapId = d.id;
      if (isDouble && d.decomposes_to) {{ window.location.href = d.decomposes_to; return; }}
      var html = '<p><span class="label">Node:</span> ' + d.label.replace(/\\n/g, ' ') + '</p>';
      html += '<p><span class="label">Kind:</span> ' + d.kind + '</p>';
      if (d.description) html += '<p>' + d.description + '</p>';
      if (d.decomposes_to) {{
        html += '<p><span class="label">▼ Drills into:</span> <a href="' + d.decomposes_to + '">' + (d.decomposes_label || 'next level') + '</a> <em style="font-size:11px;color:#888;">(or double-click bubble)</em></p>';
      }}
      if (d.pspec_link) {{
        html += '<p><span class="label">► PSPEC:</span> <a href="' + d.pspec_link + '">' + (d.pspec_label || 'process specification') + '</a></p>';
      }}
      var ref = hpRefMap[d.kind];
      if (ref) {{
        html += '<p style="font-size:11px;color:#888;margin-top:10px;"><a href="' + hpRefBase + ref + '">[?] What is a ' + d.kind.replace('-optional','').replace('-grid','') + '?</a> &middot; <a href="../dictionary.generated.html">dictionary entry</a></p>';
      }}
      render(html);
    }});

    cy.on('tap', 'edge', function(evt) {{
      var d = evt.target.data();
      var src = cy.getElementById(d.source).data('label').replace(/\\n/g, ' ');
      var tgt = cy.getElementById(d.target).data('label').replace(/\\n/g, ' ');
      var html = '<p><span class="label">Flow:</span> ' + d.label + '</p>';
      html += '<p><span class="label">From:</span> ' + src + '</p>';
      html += '<p><span class="label">To:</span> ' + tgt + '</p>';
      html += '<p><span class="label">Kind:</span> ' + d.kind + '</p>';
      if (d.medium) html += '<p><span class="label">Medium:</span> ' + d.medium + '</p>';
      if (d.notes) html += '<p>' + d.notes + '</p>';
      render(html);
    }});

    cy.on('tap', function(evt) {{
      if (evt.target === cy) {{
        render('<div class="placeholder">Click a node or edge to see details. Drag nodes to rearrange.</div>');
      }}
    }});
  </script>
  <script>{sidebar_js}</script>
</body>
</html>
"""


def _build_legend(project: Project) -> str:
    """Build a legend HTML based on what's actually in the project."""
    items: list[str] = []
    items.append('<div class="legend-item"><div class="legend-swatch" style="background:#4a90e2; border-radius:50%;"></div>System (what we\'re designing)</div>')
    items.append('<div class="legend-item"><div class="legend-swatch" style="background:#fafafa; border:1px solid #444;"></div>Terminator (external entity)</div>')

    if any(e.optional for e in project.all_entities() if e.kind == EntityKind.TERMINATOR):
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#fafafa; border:1px dashed #888;"></div>Optional terminator</div>')
    if any("grid" in e.id for e in project.all_entities() if e.kind == EntityKind.TERMINATOR):
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#fef0ef; border:1px solid #e74c3c;"></div>Utility grid (physical)</div>')

    edge_kinds = {ed.kind for ed in project.all_edges()}
    if EdgeKind.PHYSICAL_AC_POWER in edge_kinds:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#e74c3c; height:3px; margin-top:8px;"></div>Physical AC power</div>')
    if EdgeKind.PHYSICAL_DC_POWER in edge_kinds:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#2a70c2; height:3px; margin-top:8px;"></div>Physical DC power</div>')
    if EdgeKind.PHYSICAL_INTERACTION in edge_kinds:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#888; height:2px; margin-top:8px; border-top:1px dashed #888;"></div>Physical interaction</div>')

    return "\n    ".join(items)


def _build_nav(project: Project, drill_target: str | None) -> str:
    """Build a navigation HTML with drill, dictionary, HP reference."""
    parts = ["Level 0 (top of hierarchy)."]
    if drill_target:
        parts.append(f'<strong>↓ Drill down:</strong> <a href="{drill_target}">Level-1 DFD</a> &middot;')
    parts.append('<a href="../dictionary.generated.html">Dictionary</a> &middot;')
    parts.append('<a href="../../../toolkit/reference/HP_QUICK_REF.md">HP Reference</a>')

    nav = '<p style="margin:4px 0 4px 0;">' + " ".join(parts) + "</p>"
    if drill_target:
        nav += '\n    <p style="margin:0 0 12px 0;font-size:11px;color:#888;">Tip: <strong>double-click</strong> any double-bordered bubble to drill into its next level.</p>'
    return nav


def wrap_context_html(
    project: Project,
    elements: list[dict[str, Any]] | None = None,
    drill_target: str | None = "../01-level1/dfd.generated.html",
    *,
    tree: TreeNode | None = None,
    current_path: str | None = None,
) -> str:
    """Wrap the level-0 Context Diagram's elements list in the full HTML
    template — Cytoscape script + side panel + legend + navigation.

    `drill_target` controls whether the system bubble is decomposable
    (and where double-click navigates). Pass None for projects without
    a level-1 DFD yet.

    When `tree` is provided, a collapsible left-sidebar with the project
    portal navigation is injected.
    """
    if elements is None:
        elements = render_context_elements(project, drill_target=drill_target)

    return _CONTEXT_HTML_TEMPLATE.format(
        title=f"{project.project} — Context Diagram",
        subtitle=f"Level 0 · generated from dictionary.yaml · {project.last_updated}",
        nav_html=_build_nav(project, drill_target),
        legend_html=_build_legend(project),
        elements_json=json.dumps(elements, indent=2),
        styles_json=json.dumps(_ALL_STYLES_JSON, indent=2),
        **_sidebar_fields(tree, current_path),
    )


# ─────────────────────────────────────────────────────────────────────
# Level-N DFD (decomposition view) — elements + HTML wrapper
# ─────────────────────────────────────────────────────────────────────

def render_dfd_elements(
    project: Project,
    parent_id: str = "sys_root",
) -> list[dict[str, Any]]:
    """Produce the Cytoscape elements list for a level-N+1 DFD —
    decomposition of `parent_id` into internal processes + data stores
    + boundary flows refined + internal flows + physical edges.

    Processes flagged with `needs_cspec` become decomposable nodes
    that drill into their CSPEC HTML (path conventionally
    `cspecs/<id-without-proc-prefix>/cspec.html`).
    """
    parent = project.entities.get(parent_id)
    if parent is None:
        raise ValueError(f"parent {parent_id!r} not in project")

    # Per HIERARCHICAL_INGEST_DESIGN.md: child + boundary levels derive
    # from parent.level.
    child_level = parent.level + 1
    boundary_level = parent.level

    elements: list[dict[str, Any]] = []

    # Internal entities — direct children of parent at child_level
    internal = [e for e in project.all_entities()
                if e.parent == parent_id and e.level == child_level]
    processes = [e for e in internal if e.kind == EntityKind.PROCESS]
    stores    = [e for e in internal if e.kind == EntityKind.DATA_STORE]

    for p in processes:
        data: dict[str, Any] = {
            "id": p.id,
            "label": p.label,
            "kind": _node_kind(p),
            "description": p.description or "",
        }
        if p.needs_cspec:
            cspec_subdir = p.id.replace("proc_", "").replace("_", "-")
            data["decomposable"] = True
            data["decomposes_to"] = f"cspecs/{cspec_subdir}/cspec.generated.html"
            data["decomposes_label"] = f"{p.label} CSPEC"
        elif project.pspec_for_process(p.id) is not None:
            # Leaf process with a PSPEC — link to its rendered markdown.
            pspec_subdir = p.id.replace("proc_", "").replace("_", "-")
            data["pspec_link"] = f"pspecs/{pspec_subdir}.md"
            data["pspec_label"] = f"{p.label} PSPEC"
        elements.append({"data": data})

    for s in stores:
        elements.append({"data": {
            "id": s.id, "label": s.label, "kind": _node_kind(s),
            "description": s.description or "",
        }})

    # Boundary flows (touching parent_id at boundary_level)
    boundary_flows = [f for f in project.flows_at_level(boundary_level)
                      if f.source == parent_id or f.target == parent_id]

    # Terminators referenced by boundary flows + physical edges
    term_ids: set[str] = set()
    for f in boundary_flows:
        if f.source != parent_id: term_ids.add(f.source)
        if f.target != parent_id: term_ids.add(f.target)
    for ed in [e for e in project.all_edges() if e.level == boundary_level]:
        for endpoint in (ed.source, ed.target):
            entity = project.entities.get(endpoint)
            if entity and entity.kind == EntityKind.TERMINATOR:
                term_ids.add(endpoint)

    for tid in sorted(term_ids):
        t = project.entity(tid)
        label = t.label + ("\n(optional)" if t.optional else "")
        elements.append({"data": {
            "id": t.id, "label": label, "kind": _node_kind(t),
            "description": t.description or "",
        }})

    # Boundary flows — refined endpoints to internal processes
    for f in boundary_flows:
        src = (f.refined_source if f.source == parent_id and f.refined_source
               else f.source)
        tgt = (f.refined_target if f.target == parent_id and f.refined_target
               else f.target)
        data = {
            "id": f.id, "source": src, "target": tgt,
            "label": f.label, "kind": _flow_kind(f),
        }
        if f.medium: data["medium"] = f.medium
        if f.notes:  data["notes"]  = f.notes
        elements.append({"data": data})

    # Internal flows at child_level
    for f in project.flows_at_level(child_level):
        data = {
            "id": f.id, "source": f.source, "target": f.target,
            "label": f.label, "kind": _flow_kind(f),
        }
        if f.notes: data["notes"] = f.notes
        elements.append({"data": data})

    # Physical edges at level 0 — skip any that touch the parent (sys_root),
    # since the parent doesn't exist as a visible node at level-1. Edges
    # purely between terminators (e.g., fish ↔ line) survive.
    # TODO future schema extension: refined_source / refined_target on Edge
    # so that e.g. battery → controller can refine to battery → specific
    # internal process. For now, omit-touching-parent is the cleanest fix.
    for ed in [e for e in project.all_edges() if e.level == 0]:
        if ed.source == parent_id or ed.target == parent_id:
            continue  # edge references the decomposed parent; omit at level-1
        elements.append({"data": {
            "id": ed.id, "source": ed.source, "target": ed.target,
            "label": ed.label or "", "kind": ed.kind.value,
        }})

    return elements


def _build_dfd_nav(project: Project) -> str:
    return (
        '<p style="margin:4px 0 4px 0;"><strong>↑ Parent:</strong> '
        '<a href="../00-context/context.generated.html">Level-0 Context Diagram</a> '
        '&middot; <a href="../dictionary.generated.html">Dictionary</a> '
        '&middot; <a href="../../../toolkit/reference/HP_QUICK_REF.md">HP Reference</a></p>\n'
        '    <p style="margin:0 0 12px 0;font-size:11px;color:#888;">'
        'Tip: <strong>double-click</strong> any double-bordered bubble '
        '(the brain) to drill into its CSPEC.</p>'
    )


def _build_dfd_legend(project: Project, parent_id: str) -> str:
    items: list[str] = []

    internal = [e for e in project.all_entities()
                if e.parent == parent_id and e.level == 1]
    has_brain    = any(p.needs_cspec for p in internal if p.kind == EntityKind.PROCESS)
    has_optional = any(p.optional    for p in internal if p.kind == EntityKind.PROCESS)
    has_store    = any(e.kind == EntityKind.DATA_STORE for e in internal)
    has_opt_term = any(t.optional for t in project.all_entities()
                       if t.kind == EntityKind.TERMINATOR)
    has_grid_term = any("grid" in e.id for e in project.all_entities()
                        if e.kind == EntityKind.TERMINATOR)
    edge_kinds = {ed.kind for ed in project.all_edges()}

    items.append('<div class="legend-item"><div class="legend-swatch" style="background:#cfe5ff; border-radius:50%;"></div>Internal process</div>')
    if has_brain:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#7fbff5; border:2px solid #1f5a99; border-radius:50%;"></div>Brain (process with CSPEC)</div>')
    if has_optional:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#e6f0ff; border:1px dashed #888; border-radius:50%;"></div>Optional process</div>')
    if has_store:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#fff5cc; border:1px solid #b89800;"></div>Data store</div>')
    items.append('<div class="legend-item"><div class="legend-swatch" style="background:#fafafa; border:1px solid #444;"></div>Terminator</div>')
    if has_opt_term:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#fafafa; border:1px dashed #888;"></div>Optional terminator</div>')
    if has_grid_term:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#fef0ef; border:1px solid #e74c3c;"></div>Utility grid (physical)</div>')
    if EdgeKind.PHYSICAL_AC_POWER in edge_kinds:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#e74c3c; height:3px; margin-top:8px;"></div>Physical AC power</div>')
    if EdgeKind.PHYSICAL_DC_POWER in edge_kinds:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#2a70c2; height:3px; margin-top:8px;"></div>Physical DC power</div>')
    if EdgeKind.PHYSICAL_INTERACTION in edge_kinds:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#888; height:2px; margin-top:8px;"></div>Physical interaction</div>')

    return "\n    ".join(items)


def wrap_dfd_html(
    project: Project,
    parent_id: str = "sys_root",
    elements: list[dict[str, Any]] | None = None,
    *,
    tree: TreeNode | None = None,
    current_path: str | None = None,
) -> str:
    """Wrap a level-N+1 DFD's elements in the same HTML template the
    Context view uses, with DFD-specific navigation + legend.

    When `tree` is provided, a collapsible left-sidebar with the project
    portal navigation is injected."""
    if elements is None:
        elements = render_dfd_elements(project, parent_id)

    return _CONTEXT_HTML_TEMPLATE.format(
        title=f"{project.project} — Level-1 DFD",
        subtitle=f"Decomposition of {parent_id} · generated from dictionary.yaml · {project.last_updated}",
        nav_html=_build_dfd_nav(project),
        legend_html=_build_dfd_legend(project, parent_id),
        elements_json=json.dumps(elements, indent=2),
        styles_json=json.dumps(_ALL_STYLES_JSON, indent=2),
        **_sidebar_fields(tree, current_path),
    )


# ─────────────────────────────────────────────────────────────────────
# CSPEC state machine view — elements + HTML wrapper
# ─────────────────────────────────────────────────────────────────────

def render_state_machine_elements(
    project: Project,
    machine_id: str,
) -> list[dict[str, Any]]:
    """Produce Cytoscape elements for a CSPEC state machine.

    Composite states become compound parent nodes; their substates get
    `parent: <composite_id>` so Cytoscape draws them grouped inside.
    Initial states (is_initial=true at top level) are styled distinctly.
    """
    machine = project.entities.get(machine_id)
    if machine is None:
        raise ValueError(f"machine {machine_id!r} not in project")

    elements: list[dict[str, Any]] = []

    all_states = [
        e for e in project.all_entities()
        if e.parent == machine_id
        and e.kind in (EntityKind.STATE, EntityKind.STATE_COMPOSITE)
    ]

    # Composites first (parent nodes), then their substates
    composites = [s for s in all_states if s.kind == EntityKind.STATE_COMPOSITE]
    for c in composites:
        elements.append({"data": {
            "id": c.id,
            "label": c.label,
            "kind": _node_kind(c),
            "description": c.description or "",
        }})

    # Atomic states (top-level or inside a composite)
    atoms = [s for s in all_states if s.kind == EntityKind.STATE]
    for s in atoms:
        is_top_initial = s.is_initial and not s.parent_state
        data: dict[str, Any] = {
            "id": s.id,
            "label": s.label,
            "kind": "state-init" if is_top_initial else "state",
            "description": s.description or "",
        }
        if s.parent_state:
            data["parent"] = s.parent_state  # Cytoscape compound-node parent
        elements.append({"data": data})

    # Transitions — distinguish intra-composite from cross-composite
    for t in project.transitions_for(machine_id):
        src = project.entities.get(t.source_state)
        tgt = project.entities.get(t.target_state)
        same_composite = (
            src is not None and tgt is not None
            and src.parent_state and src.parent_state == tgt.parent_state
        )
        edge_data: dict[str, Any] = {
            "id": t.id,
            "source": t.source_state,
            "target": t.target_state,
            "label": t.label or t.event,
            "kind": "tx" if same_composite else "tx-mode",
            "event": t.event,
        }
        if t.action:
            edge_data["action"] = t.action
        elements.append({"data": edge_data})

    return elements


def _build_cspec_nav(project: Project, machine_id: str) -> str:
    # CSPEC pages live at 01-level1/cspecs/<id>/cspec.generated.html (depth 3),
    # so the path back to <repo>/toolkit/reference/ is five `../` segments.
    return (
        '<p style="margin:4px 0 4px 0;"><strong>↑ Parent:</strong> '
        '<a href="../../dfd.generated.html">Level-1 DFD</a> '
        '&middot; <a href="../../../dictionary.yaml">Dictionary</a> '
        '&middot; <a href="../../../../../toolkit/reference/HP_QUICK_REF.md#cspec--control-specification">CSPEC reference</a></p>\n'
        '    <p style="margin:0 0 12px 0;font-size:11px;color:#888;">'
        'Click a state to see its description; click a transition arrow '
        'for its event and action.</p>'
    )


def _build_cspec_legend(project: Project, machine_id: str) -> str:
    all_states = [
        e for e in project.all_entities()
        if e.parent == machine_id
        and e.kind in (EntityKind.STATE, EntityKind.STATE_COMPOSITE)
    ]
    has_composite = any(s.kind == EntityKind.STATE_COMPOSITE for s in all_states)
    has_initial = any(s.is_initial and not s.parent_state for s in all_states)

    items: list[str] = []
    items.append('<div class="legend-item"><div class="legend-swatch" style="background:#fff; border:1px solid #444; border-radius:50%;"></div>State</div>')
    if has_initial:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#e8e8e8; border:1px solid #888; border-radius:50%;"></div>Initial state</div>')
    if has_composite:
        items.append('<div class="legend-item"><div class="legend-swatch" style="background:#e6f3ff; border:2px solid #2a70c2;"></div>Composite mode (with sub-states)</div>')
    items.append('<div class="legend-item"><svg width="28" height="6" style="margin-right:10px;"><line x1="0" y1="3" x2="24" y2="3" stroke="#444" stroke-width="1.5" /><polygon points="24,0 28,3 24,6" fill="#444"/></svg>Transition (event / action)</div>')
    if has_composite:
        items.append('<div class="legend-item"><svg width="28" height="6" style="margin-right:10px;"><line x1="0" y1="3" x2="24" y2="3" stroke="#9a6707" stroke-width="2" /><polygon points="24,0 28,3 24,6" fill="#9a6707"/></svg>Cross-mode transition</div>')

    return "\n    ".join(items)


def wrap_state_machine_html(
    project: Project,
    machine_id: str,
    elements: list[dict[str, Any]] | None = None,
    *,
    tree: TreeNode | None = None,
    current_path: str | None = None,
) -> str:
    """Wrap a CSPEC state machine's elements in the standard HTML template.

    Uses Cytoscape compound nodes for composite states (substates get a
    `parent` pointer back to their composite). The layout engine is the
    same `cose` we use elsewhere; for state machines this works but is
    less optimal than dedicated state-machine layout (acceptable for v1).

    When `tree` is provided, a collapsible left-sidebar with the project
    portal navigation is injected.
    """
    if elements is None:
        elements = render_state_machine_elements(project, machine_id)

    machine = project.entities[machine_id]
    return _CONTEXT_HTML_TEMPLATE.format(
        title=f"{machine.label} — CSPEC",
        subtitle=f"State machine for {machine_id} · generated from dictionary.yaml · {project.last_updated}",
        nav_html=_build_cspec_nav(project, machine_id),
        legend_html=_build_cspec_legend(project, machine_id),
        elements_json=json.dumps(elements, indent=2),
        styles_json=json.dumps(_ALL_STYLES_JSON, indent=2),
        **_sidebar_fields(tree, current_path),
    )


# ─────────────────────────────────────────────────────────────────────
# Stage 5 — Architecture Model (AFD + AID)
# ─────────────────────────────────────────────────────────────────────

_ARCH_STYLES_JSON: list[dict[str, Any]] = [
    {
        "selector": 'node[kind="am-hardware"]',
        "style": {
            "shape": "round-rectangle", "background-color": "#fff4e6",
            "border-color": "#d68910", "border-width": 2,
            "label": "data(label)", "color": "#222",
            "text-valign": "center", "text-halign": "center", "text-wrap": "wrap",
            "width": 150, "height": 80, "padding": 10, "font-size": 11,
        }
    },
    {
        "selector": 'node[kind="am-software"]',
        "style": {
            "shape": "round-rectangle", "background-color": "#e8f0fe",
            "border-color": "#4a90e2", "border-width": 2,
            "label": "data(label)", "color": "#222",
            "text-valign": "center", "text-halign": "center", "text-wrap": "wrap",
            "width": 150, "height": 80, "padding": 10, "font-size": 11,
        }
    },
    {
        "selector": 'node[kind="am-organizational"]',
        "style": {
            "shape": "round-rectangle", "background-color": "#f4f4f4",
            "border-color": "#555", "border-width": 2,
            "label": "data(label)", "color": "#222",
            "text-valign": "center", "text-halign": "center", "text-wrap": "wrap",
            "width": 150, "height": 80, "padding": 10, "font-size": 11,
        }
    },
    {
        "selector": 'edge[kind="arch-flow"]',
        "style": {
            "curve-style": "bezier", "target-arrow-shape": "triangle",
            "target-arrow-color": "#444", "line-color": "#444", "width": 1.5,
            "label": "data(label)", "font-size": 10, "text-rotation": "autorotate",
            "text-background-color": "#fafafa", "text-background-opacity": 0.9,
            "text-background-padding": 2,
        }
    },
    {
        "selector": 'edge[kind="interconnect"]',
        "style": {
            "curve-style": "bezier", "target-arrow-shape": "none",
            "source-arrow-shape": "none", "line-color": "#1f5a99", "width": 4,
            "label": "data(label)", "font-size": 11, "font-weight": "bold",
            "color": "#1f5a99",
            "text-rotation": "autorotate",
            "text-background-color": "#fafafa", "text-background-opacity": 0.95,
            "text-background-padding": 3,
        }
    },
]


def _am_node_kind(m: ArchModule) -> str:
    return f"am-{m.kind.value}"


def render_afd_elements(
    project: Project,
    parent_id: str | None = None,
) -> list[dict[str, Any]]:
    """Cytoscape elements for an Architecture Flow Diagram."""
    elements: list[dict[str, Any]] = []
    modules = [m for m in project.all_architecture_modules() if m.parent == parent_id]
    module_ids = {m.id for m in modules}

    for m in modules:
        label = m.name
        if m.module_number:
            label = f"{label}\n({m.module_number})"
        data: dict[str, Any] = {
            "id": m.id, "label": label, "kind": _am_node_kind(m),
            "description": m.description or "",
        }
        # Modernization #8.1 — trust zone surfaced in side panel
        if m.trust_zone is not None:
            data["trust_zone"] = m.trust_zone.value
        # If the module has children, mark decomposable + drill target
        if any(o.parent == m.id for o in project.all_architecture_modules()):
            data["decomposable"] = True
            data["decomposes_to"] = f"afd-{m.id}.generated.html"
            data["decomposes_label"] = f"{m.name} internals"
        # AMS link
        ams = project.ams_for_module(m.id)
        if ams is not None:
            data["pspec_link"] = f"specs/{m.id.replace('am_','').replace('_','-')}.md"
            data["pspec_label"] = f"{m.name} AMS"
        elements.append({"data": data})

    for f in project.all_architecture_flows():
        if f.source in module_ids and f.target in module_ids:
            label = f.name
            if f.kind.value != "data":
                label = f"{label} ({f.kind.value})"
            # Modernization #2 — synchronicity suffix
            if f.synchronicity is not None:
                label = f"{label} [{f.synchronicity.value}]"
            elements.append({"data": {
                "id": f.id, "source": f.source, "target": f.target,
                "label": label, "kind": "arch-flow",
            }})

    return elements


def render_aid_elements(
    project: Project,
    parent_id: str | None = None,
) -> list[dict[str, Any]]:
    """Cytoscape elements for an Architecture Interconnect Diagram."""
    elements: list[dict[str, Any]] = []
    modules = [m for m in project.all_architecture_modules() if m.parent == parent_id]
    module_ids = {m.id for m in modules}

    for m in modules:
        label = m.name
        if m.module_number:
            label = f"{label}\n({m.module_number})"
        data: dict[str, Any] = {
            "id": m.id, "label": label, "kind": _am_node_kind(m),
            "description": m.description or "",
        }
        if m.trust_zone is not None:
            data["trust_zone"] = m.trust_zone.value
        elements.append({"data": data})

    for ic in project.all_architecture_interconnects():
        eps = [ep for ep in ic.endpoints if ep in module_ids]
        if len(eps) < 2:
            continue
        # Modernization #8.1 — auth + encryption surfaced in side panel
        sec_bits: list[str] = []
        if ic.auth_required is not None:
            sec_bits.append(f"auth={ic.auth_required.value}")
        if ic.encryption is not None:
            sec_bits.append(f"enc={ic.encryption.value}")
        sec_suffix = f" [{' '.join(sec_bits)}]" if sec_bits else ""
        for i in range(len(eps) - 1):
            elements.append({"data": {
                "id": f"{ic.id}__{i}", "source": eps[i], "target": eps[i+1],
                "label": ic.name + sec_suffix, "kind": "interconnect",
                "auth_required": ic.auth_required.value if ic.auth_required else None,
                "encryption": ic.encryption.value if ic.encryption else None,
            }})

    return elements


def _build_arch_nav(project: Project, view: str) -> str:
    return (
        f'<a href="../00-context/context.generated.html">↑ Context</a>'
        f' &middot; <a href="../01-level1/dfd.generated.html">↑ DFD</a>'
        f' &middot; <a href="../dictionary.generated.html">dictionary</a>'
        f' &middot; <span style="color:#888;">{view}</span>'
    )


def _build_arch_legend(view: str) -> str:
    rows = [
        ('<span style="display:inline-block;width:14px;height:14px;background:#fff4e6;border:2px solid #d68910;border-radius:4px;vertical-align:middle;"></span>',
         "Hardware module"),
        ('<span style="display:inline-block;width:14px;height:14px;background:#e8f0fe;border:2px solid #4a90e2;border-radius:4px;vertical-align:middle;"></span>',
         "Software module"),
        ('<span style="display:inline-block;width:14px;height:14px;background:#f4f4f4;border:2px solid #555;border-radius:4px;vertical-align:middle;"></span>',
         "Organizational module"),
    ]
    if view == "AFD":
        rows.append(('<span style="display:inline-block;width:24px;border-top:1.5px solid #444;vertical-align:middle;"></span>',
                     "Architecture flow"))
    else:
        rows.append(('<span style="display:inline-block;width:24px;border-top:4px solid #1f5a99;vertical-align:middle;"></span>',
                     "Interconnect (physical channel)"))
    return "<ul>" + "".join(
        f'<li>{icon} <span>{label}</span></li>' for icon, label in rows
    ) + "</ul>"


def wrap_afd_html(
    project: Project,
    parent_id: str | None = None,
    elements: list[dict[str, Any]] | None = None,
    *,
    tree: TreeNode | None = None,
    current_path: str | None = None,
) -> str:
    """Wrap an AFD's elements in the same HTML template the other views use.

    When `tree` is provided, a collapsible left-sidebar with the project
    portal navigation is injected."""
    if elements is None:
        elements = render_afd_elements(project, parent_id)

    title_suffix = f" — {parent_id}" if parent_id else ""
    styles = _ALL_STYLES_JSON + _ARCH_STYLES_JSON
    return _CONTEXT_HTML_TEMPLATE.format(
        title=f"{project.project} — AFD{title_suffix}",
        subtitle=f"Architecture Flow Diagram · generated from dictionary.yaml · {project.last_updated}",
        nav_html=_build_arch_nav(project, "AFD"),
        legend_html=_build_arch_legend("AFD"),
        elements_json=json.dumps(elements, indent=2),
        styles_json=json.dumps(styles, indent=2),
        **_sidebar_fields(tree, current_path),
    )


def wrap_aid_html(
    project: Project,
    parent_id: str | None = None,
    elements: list[dict[str, Any]] | None = None,
    *,
    tree: TreeNode | None = None,
    current_path: str | None = None,
) -> str:
    """Wrap an AID's elements in the same HTML template.

    When `tree` is provided, a collapsible left-sidebar with the project
    portal navigation is injected."""
    if elements is None:
        elements = render_aid_elements(project, parent_id)

    title_suffix = f" — {parent_id}" if parent_id else ""
    styles = _ALL_STYLES_JSON + _ARCH_STYLES_JSON
    return _CONTEXT_HTML_TEMPLATE.format(
        title=f"{project.project} — AID{title_suffix}",
        subtitle=f"Architecture Interconnect Diagram · generated from dictionary.yaml · {project.last_updated}",
        nav_html=_build_arch_nav(project, "AID"),
        legend_html=_build_arch_legend("AID"),
        elements_json=json.dumps(elements, indent=2),
        styles_json=json.dumps(styles, indent=2),
        **_sidebar_fields(tree, current_path),
    )
