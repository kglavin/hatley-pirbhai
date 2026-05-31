# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Render a markdown sidecar (PSPEC / AMS / AIS / ADR / runbook / SLOs
summary) as a standalone sidebar'd HTML page.

The original .md file is preserved; we emit a sibling .generated.html that
sources the same markdown via the `markdown` library and wraps it in the
shared sidebar chrome from render.sidebar.

Per Q5 in PORTAL_DESIGN.md — wrapping markdown sidecars in HTML gives
uniform left-sidebar navigation across every project artifact.
"""

from __future__ import annotations

from pathlib import Path

import markdown

from .sidebar import SIDEBAR_CSS, SIDEBAR_JS, render_sidebar_html
from .tree import TreeNode


_MD_EXTENSIONS = [
    "tables",
    "fenced_code",
    "attr_list",
    "sane_lists",
    "toc",
]


def render_markdown_artifact_html(
    md_text: str,
    tree: TreeNode,
    current_path: str,
    title: str,
) -> str:
    """Convert markdown text to a standalone HTML page with the project sidebar.

    `current_path` is the new HTML page's path relative to the project root.
    `title` populates <title> + the H1 banner at the top of the content area.
    """
    body_html = markdown.markdown(md_text, extensions=_MD_EXTENSIONS)
    return _PAGE_TEMPLATE.format(
        title=_html_escape(title),
        sidebar_css=SIDEBAR_CSS,
        sidebar_js=SIDEBAR_JS,
        sidebar_html=render_sidebar_html(tree, current_path),
        body_html=body_html,
    )


def html_path_for_md(md_path: Path) -> Path:
    """`pspecs/acquire-tension.md` → `pspecs/acquire-tension.generated.html`."""
    return md_path.with_suffix(".generated.html")


def html_path_for_md_relative(md_rel: str) -> str:
    """As `html_path_for_md` but on a string (relative URL)."""
    if md_rel.endswith(".md"):
        return md_rel[:-3] + ".generated.html"
    return md_rel


def _html_escape(s: str | None) -> str:
    if s is None:
        return ""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#39;"))


# ─────────────────────────────────────────────────────────────────────
# HTML template
# ─────────────────────────────────────────────────────────────────────

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; color: #222; }}
    body {{ display: flex; }}
    .hp-md-main {{
      flex: 1;
      min-width: 0;
      overflow-x: auto;
      padding: 24px 36px 60px 36px;
      max-width: 920px;
      line-height: 1.55;
    }}
    .hp-md-main h1 {{ font-size: 26px; margin: 0 0 16px 0; padding-bottom: 8px; border-bottom: 1px solid #ddd; }}
    .hp-md-main h2 {{ font-size: 17px; margin: 24px 0 8px 0; color: #333; }}
    .hp-md-main h3 {{ font-size: 14.5px; margin: 18px 0 6px 0; color: #444; }}
    .hp-md-main p {{ margin: 8px 0; }}
    .hp-md-main code {{
      background: #f4f4f4;
      padding: 1px 5px;
      border-radius: 3px;
      font-size: 0.92em;
      font-family: "SF Mono", Monaco, Consolas, monospace;
    }}
    .hp-md-main pre {{
      background: #f7f7f8;
      border: 1px solid #e4e4e4;
      border-radius: 4px;
      padding: 10px 12px;
      overflow-x: auto;
      font-size: 12.5px;
    }}
    .hp-md-main pre code {{ background: transparent; padding: 0; }}
    .hp-md-main table {{
      border-collapse: collapse;
      margin: 12px 0;
      font-size: 13.5px;
    }}
    .hp-md-main th, .hp-md-main td {{
      border: 1px solid #ddd;
      padding: 4px 10px;
      text-align: left;
    }}
    .hp-md-main th {{ background: #f4f4f4; font-weight: 600; }}
    .hp-md-main a {{ color: #2050a0; text-decoration: none; }}
    .hp-md-main a:hover {{ text-decoration: underline; }}
    .hp-md-main blockquote {{
      border-left: 3px solid #ccc;
      margin: 12px 0;
      padding: 4px 14px;
      color: #555;
      font-style: italic;
    }}
    .hp-md-main ul, .hp-md-main ol {{ padding-left: 26px; }}
    .hp-md-main li {{ margin: 3px 0; }}
{sidebar_css}
  </style>
</head>
<body>
  {sidebar_html}
  <main class="hp-md-main">
    {body_html}
  </main>
  <script>{sidebar_js}</script>
</body>
</html>
"""
