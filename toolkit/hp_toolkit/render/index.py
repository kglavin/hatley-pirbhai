"""Render `project_index.generated.html` — the project portal landing page.

The index page is the "land here" front door for a project. It pairs the same
collapsible left-sidebar that every other generated page carries (Commit 2)
with a main-content view of the project tree rendered as section cards — the
project's "executive dashboard."
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..model import Project
from ..status import ModernizationSummary, modernization_summary
from ..validate import ValidationReport, validate
from .sidebar import SIDEBAR_CSS, SIDEBAR_JS, render_sidebar_html
from .tree import TreeNode, build_project_tree


def render_project_index_html(project: Project, project_dir: Path) -> str:
    """Build the HTML body for `project_index.generated.html`."""
    tree = build_project_tree(project, project_dir)
    report = validate(project)
    modern = modernization_summary(project)

    sys_root = project.entities.get("sys_root")
    description = (sys_root.description or "").strip() if sys_root else ""

    return _PAGE_TEMPLATE.format(
        title=_html_escape(project.project),
        description=_html_escape(description) or "—",
        last_updated=_html_escape(str(project.last_updated)),
        rendered_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        validation_pill=_validation_pill(report),
        sections_html=_render_sections(tree),
        modernization_html=_render_modernization_overview(modern),
        toolkit_links=_render_toolkit_links(),
        sidebar_html=render_sidebar_html(tree, current_path="project_index.generated.html"),
        sidebar_css=SIDEBAR_CSS,
        sidebar_js=SIDEBAR_JS,
    )


# ─────────────────────────────────────────────────────────────────────
# Section + node rendering
# ─────────────────────────────────────────────────────────────────────

def _render_sections(root: TreeNode) -> str:
    """Render each top-level child (except Home) as a stage card."""
    cards = []
    for child in root.children:
        if child.label == "Home":
            continue
        cards.append(_render_section_card(child))
    return "\n".join(cards)


def _render_section_card(node: TreeNode) -> str:
    badge = f' <span class="badge">{_html_escape(node.badge)}</span>' if node.badge else ''
    if not node.children:
        return (
            f'<section class="stage-card">'
            f'<h2>{_html_escape(node.label)}{badge}</h2>'
            f'<p class="empty">— not yet started</p>'
            f'</section>'
        )
    return (
        f'<section class="stage-card">'
        f'<h2>{_html_escape(node.label)}{badge}</h2>'
        f'<ul>{_render_children(node.children)}</ul>'
        f'</section>'
    )


def _render_children(nodes: list[TreeNode]) -> str:
    items: list[str] = []
    for node in nodes:
        if node.children:
            sub_badge = f' <span class="badge">{_html_escape(node.badge)}</span>' if node.badge else ''
            items.append(
                f'<li class="subsection-li">'
                f'<span class="subsection-label">{_html_escape(node.label)}</span>{sub_badge}'
                f'<ul>{_render_children(node.children)}</ul>'
                f'</li>'
            )
        else:
            items.append(_render_artifact_li(node))
    return "".join(items)


def _render_artifact_li(node: TreeNode) -> str:
    badge = f' <span class="badge">{_html_escape(node.badge)}</span>' if node.badge else ''
    if node.href:
        marker = '↗' if node.kind == 'external' else ''
        return (
            f'<li><a href="{_html_escape(node.href)}">{_html_escape(node.label)}</a>'
            f'{(" " + marker) if marker else ""}{badge}</li>'
        )
    return f'<li>{_html_escape(node.label)}{badge}</li>'


# ─────────────────────────────────────────────────────────────────────
# Page chrome
# ─────────────────────────────────────────────────────────────────────

def _validation_pill(report: ValidationReport) -> str:
    if report.ok:
        return '<span class="pill ok">✅ valid</span>'
    return f'<span class="pill error">✗ {len(report.errors)} error(s)</span>'


def _render_modernization_overview(s: ModernizationSummary) -> str:
    n_adrs = sum(s.adrs_by_status.values())
    parts = [
        f"ADRs: {n_adrs}" if n_adrs else "ADRs: —",
        f"Budgets/TPMs: {s.budgets}/{s.tpms}" if (s.budgets or s.tpms) else "Budgets/TPMs: —",
        f"SLOs: {s.slos}" if s.slos else "SLOs: —",
        (f"STRIDE: {s.cross_zone_with_stride}/{s.cross_zone_interconnects}"
         if s.cross_zone_interconnects else "STRIDE: n/a"),
        (f"Observability: {s.leaf_pspecs_with_observability}/{s.leaf_pspecs_total}"
         if s.leaf_pspecs_total else "Observability: —"),
        f"Bounded contexts: {s.bounded_contexts}" if s.bounded_contexts else "Bounded contexts: —",
    ]
    return ' · '.join(parts)


def _render_toolkit_links() -> str:
    return (
        '<a href="../../toolkit/README.md">Toolkit README</a> · '
        '<a href="../../toolkit/TUTORIAL.md">Tutorial</a> · '
        '<a href="../../toolkit/reference/HP_QUICK_REF.md">HP Quick Reference</a>'
    )


def _html_escape(s: str | None) -> str:
    if s is None:
        return ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&#39;"))


# ─────────────────────────────────────────────────────────────────────
# HTML template
# ─────────────────────────────────────────────────────────────────────

_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      color: #222;
      display: flex;
      min-height: 100vh;
      line-height: 1.5;
    }}
    .hp-index-main {{
      flex: 1;
      min-width: 0;
      max-width: 1000px;
      padding: 24px 36px 60px 36px;
    }}
    header {{
      border-bottom: 1px solid #ddd;
      padding-bottom: 16px;
      margin-bottom: 24px;
    }}
    h1 {{ margin: 0 0 4px 0; font-size: 28px; }}
    header .description {{ color: #555; margin: 4px 0 0 0; }}
    header .meta {{ color: #777; font-size: 13px; margin-top: 10px; }}
    .pill {{
      display: inline-block;
      padding: 2px 9px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      vertical-align: 1px;
    }}
    .pill.ok {{ background: #e2f4d8; color: #2d6e10; }}
    .pill.error {{ background: #f8d8d8; color: #9c1c1c; }}
    .modernization-line {{
      font-size: 13px;
      color: #555;
      padding: 6px 0 0 0;
      margin: 0;
    }}
    .stage-card {{
      background: #fafafa;
      border: 1px solid #e4e4e4;
      border-radius: 6px;
      padding: 14px 18px;
      margin-bottom: 14px;
    }}
    .stage-card h2 {{
      margin: 0 0 8px 0;
      font-size: 16px;
      color: #333;
      font-weight: 600;
    }}
    .stage-card .badge {{
      font-size: 12px;
      color: #777;
      font-weight: 500;
    }}
    .stage-card ul {{ margin: 0; padding-left: 22px; }}
    .stage-card li {{ margin: 3px 0; }}
    .stage-card .subsection-li {{
      list-style: none;
      margin-left: -22px;
      margin-top: 6px;
    }}
    .stage-card .subsection-label {{
      font-weight: 600;
      color: #444;
      font-size: 14px;
    }}
    .stage-card .subsection-li > ul {{ margin-top: 2px; padding-left: 22px; }}
    .stage-card a {{ color: #2050a0; text-decoration: none; }}
    .stage-card a:hover {{ text-decoration: underline; }}
    .stage-card .empty {{
      color: #999;
      margin: 4px 0 0 0;
      font-style: italic;
      font-size: 13px;
    }}
    footer {{
      margin-top: 32px;
      padding-top: 16px;
      border-top: 1px solid #ddd;
      font-size: 13px;
      color: #777;
    }}
    footer a {{ color: #2050a0; text-decoration: none; }}
    footer a:hover {{ text-decoration: underline; }}
{sidebar_css}
  </style>
</head>
<body>
  {sidebar_html}
  <main class="hp-index-main">
    <header>
      <h1>{title}</h1>
      <p class="description">{description}</p>
      <p class="meta">
        Dictionary last updated <strong>{last_updated}</strong> ·
        Rendered <strong>{rendered_at}</strong> ·
        {validation_pill}
      </p>
      <p class="modernization-line">Modernization — {modernization_html}</p>
    </header>

    {sections_html}

    <footer>
      {toolkit_links}
    </footer>
  </main>
  <script>{sidebar_js}</script>
</body>
</html>
"""
