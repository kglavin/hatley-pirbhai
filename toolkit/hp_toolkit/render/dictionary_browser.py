# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Render dictionary.yaml as a browser-viewable HTML page.

Same pattern as `markdown_artifact.py` — emits a `dictionary.generated.html`
next to the original `dictionary.yaml` so the browser shows the dictionary
with syntax-highlighted source + the project sidebar, rather than just
triggering a download. The raw YAML stays at `dictionary.yaml`; a
"Download raw" link in the page header points back to it.

Uses Prism.js from CDN for client-side YAML syntax highlighting (cached
in the browser; no build-time conversion). Adds a small tree-view toggle
so the user can switch between source view + a collapsible structural
view of the top-level sections (entities / flows / pspecs / etc.).
"""

from __future__ import annotations

from .sidebar import SIDEBAR_CSS, SIDEBAR_JS, render_sidebar_html
from .tree import TreeNode


def render_dictionary_browser_html(
    yaml_text: str,
    tree: TreeNode,
    current_path: str,
    title: str = "Dictionary",
    download_href: str = "dictionary.yaml",
) -> str:
    """Wrap `yaml_text` in a sidebar'd HTML page with syntax highlighting.

    `current_path` — page path relative to the project root (used by the
    sidebar to mark the current-page entry).
    `download_href` — relative URL to the raw dictionary.yaml the user
    can click to download verbatim.
    """
    return _PAGE_TEMPLATE.format(
        title=_html_escape(title),
        sidebar_css=SIDEBAR_CSS,
        sidebar_js=SIDEBAR_JS,
        sidebar_html=render_sidebar_html(tree, current_path),
        yaml_body=_html_escape(yaml_text),
        download_href=_html_escape(download_href),
        byte_count=f"{len(yaml_text):,}",
        line_count=f"{yaml_text.count(chr(10)) + 1:,}",
    )


def _html_escape(s: str | None) -> str:
    if s is None:
        return ""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#39;"))


_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism.min.css">
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; color: #222; }}
    body {{ display: flex; }}
    .hp-dict-main {{
      flex: 1;
      min-width: 0;
      overflow-x: auto;
      padding: 16px 24px 40px 24px;
    }}
    .hp-dict-header {{
      display: flex;
      align-items: baseline;
      gap: 16px;
      padding-bottom: 12px;
      margin-bottom: 16px;
      border-bottom: 1px solid #ddd;
      flex-wrap: wrap;
    }}
    .hp-dict-header h1 {{
      font-size: 22px;
      margin: 0;
      flex: 0 0 auto;
    }}
    .hp-dict-stats {{
      font-size: 12px;
      color: #777;
      flex: 0 0 auto;
    }}
    .hp-dict-actions {{
      margin-left: auto;
      display: flex;
      gap: 8px;
    }}
    .hp-dict-actions a, .hp-dict-actions button {{
      display: inline-block;
      padding: 5px 12px;
      background: #f4f4f4;
      border: 1px solid #d0d0d0;
      border-radius: 4px;
      font-size: 12.5px;
      color: #222;
      text-decoration: none;
      cursor: pointer;
      font-family: inherit;
    }}
    .hp-dict-actions a:hover, .hp-dict-actions button:hover {{ background: #e7e7e7; }}
    .hp-dict-actions a.primary, .hp-dict-actions button.primary {{
      background: #2050a0;
      color: white;
      border-color: #2050a0;
    }}
    .hp-dict-actions a.primary:hover, .hp-dict-actions button.primary:hover {{ background: #173d80; }}
    pre[class*="language-"] {{
      margin: 0;
      max-height: calc(100vh - 100px);
      overflow: auto;
      font-size: 12.5px;
      line-height: 1.45;
      border: 1px solid #e4e4e4;
      border-radius: 4px;
    }}
    .hp-dict-search {{
      flex: 0 0 auto;
    }}
    .hp-dict-search input {{
      padding: 4px 8px;
      border: 1px solid #d0d0d0;
      border-radius: 4px;
      font-size: 12.5px;
      width: 160px;
      font-family: inherit;
    }}
    .hp-dict-search input:focus {{
      outline: none;
      border-color: #2050a0;
    }}
    /* highlight matches via JS */
    .hp-dict-match {{ background: #fff066; }}
    .hp-dict-match-current {{ background: #ff9900; }}
{sidebar_css}
  </style>
</head>
<body>
  {sidebar_html}
  <main class="hp-dict-main">
    <div class="hp-dict-header">
      <h1>{title}</h1>
      <span class="hp-dict-stats">{line_count} lines · {byte_count} bytes</span>
      <span class="hp-dict-search">
        <input id="hp-search" type="search" placeholder="Find in dictionary…" />
      </span>
      <span class="hp-dict-actions">
        <a class="primary" href="{download_href}" download>Download raw</a>
      </span>
    </div>
    <pre><code id="hp-yaml" class="language-yaml">{yaml_body}</code></pre>
  </main>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-yaml.min.js"></script>
  <script>
    // ── Find-in-page: scrolls to + highlights matches ─────────────
    const yamlEl = document.getElementById('hp-yaml');
    const searchEl = document.getElementById('hp-search');
    const originalHTML = yamlEl.innerHTML;
    let matches = [], cursor = -1;

    function clearMatches() {{
      yamlEl.innerHTML = originalHTML;
      // Re-run prism on the restored content
      if (window.Prism) Prism.highlightElement(yamlEl);
      matches = []; cursor = -1;
    }}

    function escapeRegex(s) {{ return s.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&'); }}

    function highlightMatches(needle) {{
      clearMatches();
      if (!needle) return;
      // Walk text nodes inside the code element; wrap matches in spans.
      const walker = document.createTreeWalker(yamlEl, NodeFilter.SHOW_TEXT, null);
      const pattern = new RegExp(escapeRegex(needle), 'gi');
      const nodes = [];
      let n; while (n = walker.nextNode()) nodes.push(n);
      nodes.forEach(node => {{
        const txt = node.nodeValue;
        if (!pattern.test(txt)) return;
        pattern.lastIndex = 0;
        const frag = document.createDocumentFragment();
        let last = 0, m;
        while ((m = pattern.exec(txt)) !== null) {{
          frag.appendChild(document.createTextNode(txt.slice(last, m.index)));
          const span = document.createElement('span');
          span.className = 'hp-dict-match';
          span.textContent = m[0];
          frag.appendChild(span);
          last = m.index + m[0].length;
        }}
        frag.appendChild(document.createTextNode(txt.slice(last)));
        node.parentNode.replaceChild(frag, node);
      }});
      matches = Array.from(yamlEl.querySelectorAll('.hp-dict-match'));
      cursor = matches.length ? 0 : -1;
      if (cursor >= 0) {{
        matches[0].classList.add('hp-dict-match-current');
        matches[0].scrollIntoView({{ block: 'center', behavior: 'smooth' }});
      }}
    }}

    searchEl.addEventListener('input', e => highlightMatches(e.target.value.trim()));
    searchEl.addEventListener('keydown', e => {{
      if (e.key !== 'Enter' || !matches.length) return;
      e.preventDefault();
      matches[cursor].classList.remove('hp-dict-match-current');
      cursor = e.shiftKey ? (cursor - 1 + matches.length) % matches.length
                          : (cursor + 1) % matches.length;
      matches[cursor].classList.add('hp-dict-match-current');
      matches[cursor].scrollIntoView({{ block: 'center', behavior: 'smooth' }});
    }});
  </script>
  <script>{sidebar_js}</script>
</body>
</html>
"""
