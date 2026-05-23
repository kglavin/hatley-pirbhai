"""Render the project tree as a collapsible HTML left-sidebar.

Used by every wrap_*_html function in cytoscape.py + by render/index.py +
by render/markdown_artifact.py. The same tree is built once by
render.tree.build_project_tree and passed to every page renderer.

Collapse state persists across pages via localStorage. Per-section
collapse state uses native <details>/<summary> and is preserved by
HTML's default behavior.

This module is the entirety of the portal's navigation chrome. The PDF
renderer (Commit 3) will consume the same tree to produce a TOC.
"""

from __future__ import annotations

from .tree import TreeNode


def render_sidebar_html(tree: TreeNode, current_path: str | None = None) -> str:
    """Render the project tree as a left-sidebar <aside> element.

    `current_path` is the href of the page hosting this sidebar, relative to
    the project root. Tree hrefs are also project-root-relative; this function
    prefixes them with the right number of `../` segments so they resolve from
    the host page's directory. The matching <a> gets a `.current` class;
    ancestor <details> sections are emitted `open`. Top-level sections are
    also open by default so first-time visitors see the structure."""
    prefix = _path_prefix_for(current_path)
    body = "".join(_render_node(c, current_path, prefix, depth=0)
                   for c in tree.children)
    return (
        '<aside class="hp-sidebar" id="hp-sidebar">\n'
        '  <button class="hp-sidebar-toggle" id="hp-sidebar-toggle" '
        'aria-label="Toggle sidebar" title="Toggle sidebar">◀</button>\n'
        '  <div class="hp-sidebar-header">\n'
        f'    <strong>{_html_escape(tree.label)}</strong>\n'
        '  </div>\n'
        '  <nav class="hp-tree">\n'
        f'{body}'
        '  </nav>\n'
        '</aside>\n'
    )


def _render_node(node: TreeNode, current: str | None, prefix: str, depth: int) -> str:
    if not node.children:
        return _render_leaf(
            node, prefix,
            is_current=(node.href is not None and node.href == current),
        )

    is_top = (depth == 0)
    contains_current = _contains_path(node, current) if current else False
    open_attr = ' open' if (is_top or contains_current) else ''
    badge = (f' <span class="hp-badge">{_html_escape(node.badge)}</span>'
             if node.badge else '')
    children = "".join(_render_node(c, current, prefix, depth + 1) for c in node.children)

    return (
        f'    <details class="hp-tree-section depth-{depth}"{open_attr}>\n'
        f'      <summary>{_html_escape(node.label)}{badge}</summary>\n'
        f'      <ul>{children}</ul>\n'
        f'    </details>\n'
    )


def _render_leaf(node: TreeNode, prefix: str, is_current: bool) -> str:
    badge = (f' <span class="hp-badge">{_html_escape(node.badge)}</span>'
             if node.badge else '')
    if node.href:
        current_attr = ' class="current"' if is_current else ''
        marker = ' <span class="hp-ext">↗</span>' if node.kind == 'external' else ''
        # External hrefs already escape outward (../..); leave them alone.
        href = node.href if node.kind == 'external' else _resolve_href(prefix, node.href)
        return (
            f'<li><a href="{_html_escape(href)}"{current_attr}>'
            f'{_html_escape(node.label)}{marker}{badge}</a></li>\n'
        )
    return f'<li class="hp-tree-note"><span>{_html_escape(node.label)}</span>{badge}</li>\n'


def _path_prefix_for(current_path: str | None) -> str:
    """Compute the `../` prefix that walks from `current_path`'s directory back
    to the project root. `current_path` is project-root-relative."""
    if not current_path or "/" not in current_path:
        return ""
    depth = current_path.count("/")
    return "../" * depth


def _resolve_href(prefix: str, href: str) -> str:
    """Convert a project-root-relative href into one relative to the host page."""
    return prefix + href


def _contains_path(node: TreeNode, path: str | None) -> bool:
    if path is None:
        return False
    for n in node.walk():
        if n.href == path:
            return True
    return False


def _html_escape(s: str | None) -> str:
    if s is None:
        return ""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#39;"))


# ─────────────────────────────────────────────────────────────────────
# Sidebar CSS — injected into every page's <head>
# ─────────────────────────────────────────────────────────────────────

SIDEBAR_CSS = """
/* Project Portal — sidebar */
.hp-sidebar {
  width: 260px;
  flex: 0 0 260px;
  background: #f7f7f8;
  border-right: 1px solid #ddd;
  font: 13px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  color: #333;
  overflow-y: auto;
  position: sticky;
  top: 0;
  height: 100vh;
  transition: width 0.15s ease, flex-basis 0.15s ease;
}
body[data-sidebar-collapsed="true"] .hp-sidebar {
  width: 28px;
  flex: 0 0 28px;
}
body[data-sidebar-collapsed="true"] .hp-sidebar > *:not(.hp-sidebar-toggle) {
  display: none;
}
.hp-sidebar-toggle {
  position: absolute;
  top: 6px;
  right: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  color: #666;
  padding: 4px 6px;
  z-index: 10;
  line-height: 1;
}
.hp-sidebar-toggle:hover { color: #000; }
body[data-sidebar-collapsed="true"] .hp-sidebar-toggle {
  right: auto;
  left: 4px;
  transform: rotate(180deg);
}
.hp-sidebar-header {
  padding: 12px 12px 8px 12px;
  border-bottom: 1px solid #ddd;
  font-size: 13px;
  margin-right: 26px;       /* leave room for toggle */
}
.hp-sidebar-header strong {
  display: block;
  font-size: 13px;
  color: #222;
}
.hp-tree {
  padding: 8px 4px 24px 4px;
}
.hp-tree-section {
  padding: 4px 0 4px 8px;
}
.hp-tree-section > summary {
  cursor: pointer;
  list-style: none;
  font-weight: 600;
  font-size: 12.5px;
  padding: 3px 4px 3px 0;
  color: #333;
  user-select: none;
}
.hp-tree-section > summary::-webkit-details-marker { display: none; }
.hp-tree-section > summary::before {
  content: "▸";
  display: inline-block;
  width: 12px;
  font-size: 9px;
  color: #999;
  transition: transform 0.12s;
}
.hp-tree-section[open] > summary::before { transform: rotate(90deg); }
.hp-tree-section.depth-1 > summary {
  font-weight: 500;
  font-size: 12px;
  color: #555;
}
.hp-tree ul {
  list-style: none;
  margin: 2px 0 2px 12px;
  padding: 0;
}
.hp-tree li { margin: 1px 0; }
.hp-tree a {
  display: block;
  padding: 2px 6px;
  border-radius: 3px;
  color: #2050a0;
  text-decoration: none;
  font-size: 12.5px;
}
.hp-tree a:hover { background: #e7eef9; }
.hp-tree a.current {
  background: #e2eaf6;
  color: #112e60;
  font-weight: 600;
}
.hp-ext { color: #888; font-size: 10px; }
.hp-tree-note span {
  display: block;
  padding: 2px 6px;
  color: #888;
  font-style: italic;
  font-size: 12px;
}
.hp-badge {
  display: inline-block;
  margin-left: 4px;
  font-size: 10.5px;
  color: #777;
  font-weight: normal;
}
""".strip()


# ─────────────────────────────────────────────────────────────────────
# JS — sidebar collapse persistence
# ─────────────────────────────────────────────────────────────────────

SIDEBAR_JS = """
(function() {
  var toggle = document.getElementById('hp-sidebar-toggle');
  if (!toggle) return;
  var KEY = 'hp-portal-sidebar-collapsed';
  if (localStorage.getItem(KEY) === 'true') {
    document.body.setAttribute('data-sidebar-collapsed', 'true');
  }
  toggle.addEventListener('click', function() {
    var collapsed = document.body.getAttribute('data-sidebar-collapsed') === 'true';
    if (collapsed) {
      document.body.removeAttribute('data-sidebar-collapsed');
      localStorage.setItem(KEY, 'false');
    } else {
      document.body.setAttribute('data-sidebar-collapsed', 'true');
      localStorage.setItem(KEY, 'true');
    }
  });
})();
""".strip()
