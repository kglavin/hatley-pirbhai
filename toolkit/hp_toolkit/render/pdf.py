"""Render a project as a single shareable PDF.

Composes one HTML document and rasterises it via WeasyPrint:

- Cover page (project name + description + version + validation status)
- Clickable Table of Contents (WeasyPrint fills page numbers via
  target-counter())
- Per-stage section: a one-page cover, then each artifact in order
- Diagrams embed as SVG `<img>` on landscape-oriented pages
- Markdown sidecars (PSPECs, AMS, AIS, ADRs, SLOs summary, runbooks)
  convert to HTML inline
- Appendix: HP Quick Reference

Per PORTAL_DESIGN.md decisions:
- Q1: only example-project PDFs are tracked (.gitignore handles user
  projects).
- Q2: mixed portrait/landscape — wide diagrams use a named landscape
  page; prose stays portrait.
- Q3: Python-Markdown with tables / fenced_code / attr_list / sane_lists
  / toc extensions.
- Q4: HP_QUICK_REF.md included as appendix.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import subprocess

import cairosvg
import markdown
import weasyprint

from ..model import Project
from ..status import modernization_summary
from ..validate import validate
from .svg import _find_binary
from .tree import TreeNode, build_project_tree


# Width of cairosvg-rendered PNGs from SVGs (pixels). Only used as a fallback
# when the d2/mmdc binaries aren't available — the binaries render at their
# native viewBox dimensions via Chromium, which produces a much higher-
# fidelity result.
_PNG_WIDTH_PX = 2400


_MD_EXTENSIONS = ["tables", "fenced_code", "attr_list", "sane_lists", "toc"]


def render_project_pdf(
    project: Project,
    project_dir: Path,
    out_path: Path | None = None,
) -> Path:
    """Render the project to a single PDF (default: `project.generated.pdf`
    at the project root). Returns the output path."""
    if out_path is None:
        out_path = project_dir / "project.generated.pdf"

    html_doc = _compose_pdf_html(project, project_dir)
    weasyprint.HTML(string=html_doc, base_url=str(project_dir)).write_pdf(out_path)
    return out_path


# ─────────────────────────────────────────────────────────────────────
# Composition
# ─────────────────────────────────────────────────────────────────────

def _compose_pdf_html(project: Project, project_dir: Path) -> str:
    """Build the full HTML document that WeasyPrint will rasterise."""
    tree = build_project_tree(project, project_dir)
    anchors: dict[int, str] = {}   # id(node) → anchor id

    cover_html = _render_cover(project)
    toc_html = _render_toc(tree, anchors)
    body_html = _render_body(tree, anchors, project_dir)
    appendix_html = _render_appendix(project_dir)

    return _DOCUMENT_TEMPLATE.format(
        title=_html_escape(project.project),
        css=_PDF_CSS,
        cover=cover_html,
        toc=toc_html,
        body=body_html,
        appendix=appendix_html,
    )


def _render_cover(project: Project) -> str:
    sys_root = project.entities.get("sys_root")
    description = (sys_root.description or "").strip() if sys_root else ""
    report = validate(project)
    modern = modernization_summary(project)

    validation = "✅ valid" if report.ok else f"✗ {len(report.errors)} error(s)"
    n_adrs = sum(modern.adrs_by_status.values())
    modern_line = (
        f"ADRs: {n_adrs} · Budgets/TPMs: {modern.budgets}/{modern.tpms} · "
        f"SLOs: {modern.slos} · "
        f"Bounded contexts: {modern.bounded_contexts}"
    )

    return (
        '<section class="cover-page">\n'
        f'  <h1 class="cover-title">{_html_escape(project.project)}</h1>\n'
        f'  <p class="cover-description">{_html_escape(description) or "—"}</p>\n'
        '  <div class="cover-meta">\n'
        f'    <p>Version <strong>{_html_escape(project.version)}</strong></p>\n'
        f'    <p>Dictionary last updated <strong>{_html_escape(str(project.last_updated))}</strong></p>\n'
        f'    <p>Generated <strong>{datetime.now().strftime("%Y-%m-%d")}</strong></p>\n'
        f'    <p>Validation: <strong>{validation}</strong></p>\n'
        f'    <p>Modernization: <strong>{_html_escape(modern_line)}</strong></p>\n'
        '  </div>\n'
        '</section>\n'
    )


def _render_toc(tree: TreeNode, anchors: dict[int, str]) -> str:
    """Render the TOC and stash a unique anchor id for each non-Home node so
    the body anchors can match."""
    counter = [0]
    rows: list[str] = []

    def visit(node: TreeNode, depth: int) -> None:
        for child in node.children:
            if child.label == "Home":
                continue
            if depth == 0 and child.label == "Reference":
                # Reference becomes the appendix — handled separately.
                continue
            if depth == 0 and not child.children:
                # Skip empty top-level stages (no content)
                continue
            counter[0] += 1
            anchor = f"sec-{counter[0]}"
            anchors[id(child)] = anchor
            rows.append(
                f'    <p class="toc-row toc-depth-{depth}">'
                f'<a href="#{anchor}">{_html_escape(child.label)}'
                f'<span class="toc-leader"></span>'
                f'<span class="toc-pageno" data-target="#{anchor}"></span></a></p>\n'
            )
            visit(child, depth + 1)

    visit(tree, 0)

    return (
        '<section class="toc-page">\n'
        '  <h1 class="toc-title">Contents</h1>\n'
        '  <nav class="toc">\n'
        f'{"".join(rows)}'
        '  </nav>\n'
        '</section>\n'
    )


def _render_body(tree: TreeNode, anchors: dict[int, str], project_dir: Path) -> str:
    """Render every stage section + its artifacts in document order."""
    parts: list[str] = []
    for stage in tree.children:
        if stage.label == "Home" or stage.label == "Reference":
            continue
        if not stage.children:
            continue
        parts.append(_render_stage_section(stage, anchors, project_dir))
    return "\n".join(parts)


def _render_stage_section(stage: TreeNode, anchors: dict[int, str], project_dir: Path) -> str:
    """One top-level stage cover + its artifact bodies."""
    anchor = anchors.get(id(stage), "")
    badge_html = (f'<p class="stage-cover-badge">{_html_escape(stage.badge)}</p>'
                  if stage.badge else "")
    cover = (
        f'<section class="stage-cover" id="{anchor}">\n'
        f'  <h1 class="stage-cover-title">{_html_escape(stage.label)}</h1>\n'
        f'  {badge_html}\n'
        '</section>\n'
    )
    body_parts = [_render_artifact(child, anchors, project_dir)
                  for child in stage.children]
    return cover + "\n".join(p for p in body_parts if p)


def _render_artifact(node: TreeNode, anchors: dict[int, str], project_dir: Path) -> str:
    """Render one artifact node — leaf or subsection."""
    if node.children:
        anchor = anchors.get(id(node), "")
        sub_parts = [
            f'<section class="subsection-header" id="{anchor}">\n'
            f'  <h2>{_html_escape(node.label)}</h2>\n'
            '</section>\n'
        ]
        for child in node.children:
            sub_parts.append(_render_artifact(child, anchors, project_dir))
        return "\n".join(p for p in sub_parts if p)

    if not node.href:
        return ""

    anchor = anchors.get(id(node), "")
    href = node.href

    if href.endswith(".generated.html"):
        # Cytoscape diagram pages have a generated SVG sibling — check first
        # because legacy projects may have a hand-written `.md` next to a
        # diagram (e.g., solar's `context.md`), which would incorrectly shadow
        # the SVG embed if we checked markdown first.
        #
        # Prefer D2 over Mermaid for PDF rendering: Mermaid SVGs put node text
        # inside <foreignObject> with HTML, which WeasyPrint can't render —
        # shapes appear but text labels go missing. D2 uses native SVG <text>,
        # which WeasyPrint handles correctly when the SVG is *inlined* (not
        # loaded via <img>, which loses the SVG's internal <style> classes).
        for suffix in ["-d2.svg", "-mermaid.svg"]:
            svg_path = project_dir / href.replace(".html", suffix)
            if svg_path.exists():
                return _embed_diagram(svg_path, node.label, anchor)
        # Otherwise this is a markdown sidecar wrapper — embed the .md source
        md_path = project_dir / href.replace(".generated.html", ".md")
        if md_path.exists():
            return _embed_markdown(md_path, node.label, anchor)
        return ""

    if href.endswith(".svg"):
        svg_path = project_dir / href
        if svg_path.exists():
            return _embed_diagram(svg_path, node.label, anchor)
        return ""

    if href.endswith(".md"):
        md_path = project_dir / href
        if md_path.exists():
            return _embed_markdown(md_path, node.label, anchor)
        return ""

    # Unknown artifact kind — quietly skip
    return ""


def _embed_markdown(md_path: Path, label: str, anchor: str) -> str:
    body_html = markdown.markdown(md_path.read_text(), extensions=_MD_EXTENSIONS)
    anchor_attr = f' id="{anchor}"' if anchor else ""
    return (
        f'<section class="prose-section"{anchor_attr}>\n'
        f'{body_html}\n'
        '</section>\n'
    )


def _embed_diagram(svg_path: Path, label: str, anchor: str) -> str:
    """Render the diagram source to PNG and embed the PNG on a landscape
    page (per Q2).

    Why PNG instead of inline SVG or <img src=...svg>:
    WeasyPrint's PDF output of SVG (whether via <img> or inline) doesn't
    reliably reproduce D2's class-based fills/strokes or Mermaid's
    foreignObject text. The result across viewers (Chrome's pdf.js, VS
    Code pdf extension, etc.) is missing shapes plus 'redacted' (black
    bar) text glyphs.

    Why two PNG render paths:
    - Primary: invoke the `d2` or `mmdc` binary on the original source file
      (`.d2` / `.mmd`). Both use headless Chromium internally — the same
      pipeline that produces the in-browser preview. Fonts and styling
      render identically to what you'd see in a browser.
    - Fallback: cairosvg on the SVG. Lower fidelity (cairo loses D2's
      class-based styling) but works when binaries aren't installed.

    PNG is cached next to the SVG (`*.png`) so subsequent `--pdf-only`
    builds skip the regen unless the source has changed.
    """
    png_path = svg_path.with_suffix(".png")
    fresh = (png_path.exists()
             and png_path.stat().st_mtime >= svg_path.stat().st_mtime)
    if not fresh:
        rendered = _render_png_from_source(svg_path, png_path)
        if not rendered:
            # Fallback: cairosvg on the SVG itself.
            cairosvg.svg2png(
                url=svg_path.as_uri(),
                write_to=str(png_path),
                output_width=_PNG_WIDTH_PX,
            )

    anchor_attr = f' id="{anchor}"' if anchor else ""
    src = png_path.as_uri()
    return (
        f'<section class="diagram-page"{anchor_attr}>\n'
        f'  <h2 class="diagram-title">{_html_escape(label)}</h2>\n'
        f'  <img class="diagram" src="{src}" alt="{_html_escape(label)}" />\n'
        '</section>\n'
    )


def _render_png_from_source(svg_path: Path, png_path: Path) -> bool:
    """Render a high-fidelity PNG by invoking the same binary that produced
    the SVG (`d2` for `*-d2.svg`, `mmdc` for `*-mermaid.svg`) on the
    original source file. Both binaries use headless Chromium internally.

    Returns True if a PNG was successfully written, False otherwise."""
    name = svg_path.name
    if name.endswith("-d2.svg"):
        source = svg_path.with_name(name[:-len("-d2.svg")] + ".d2")
        binary = _find_binary("d2")
        if binary is None or not source.exists():
            return False
        result = subprocess.run(
            [binary, str(source.resolve()), str(png_path.resolve())],
            capture_output=True, text=True,
        )
        return result.returncode == 0 and png_path.exists()

    if name.endswith("-mermaid.svg"):
        source = svg_path.with_name(name[:-len("-mermaid.svg")] + ".mmd")
        binary = _find_binary("mmdc")
        if binary is None or not source.exists():
            return False
        cmd = [binary, "-i", str(source.resolve()), "-o", str(png_path.resolve())]
        # Auto-locate puppeteer config (Ubuntu 23.10+ sandbox quirk)
        pkg_dir = Path(__file__).resolve().parent.parent.parent
        ppt = pkg_dir / ".puppeteer-config.json"
        if ppt.exists():
            cmd.extend(["-p", str(ppt)])
        result = subprocess.run(cmd, capture_output=True, text=True)
        # mmdc sometimes appends `-1` to the output name; handle that.
        suffix_output = png_path.with_name(png_path.stem + "-1" + png_path.suffix)
        if suffix_output.exists() and not png_path.exists():
            suffix_output.rename(png_path)
        return result.returncode == 0 and png_path.exists()

    return False


def _render_appendix(project_dir: Path) -> str:
    """Include HP Quick Reference as an appendix (per Q4)."""
    quickref = _find_quick_ref(project_dir)
    if quickref is None or not quickref.exists():
        return ""
    body_html = markdown.markdown(quickref.read_text(), extensions=_MD_EXTENSIONS)
    return (
        '<section class="stage-cover" id="sec-appendix">\n'
        '  <h1 class="stage-cover-title">Appendix — HP Quick Reference</h1>\n'
        '</section>\n'
        '<section class="prose-section">\n'
        f'{body_html}\n'
        '</section>\n'
    )


def _find_quick_ref(project_dir: Path) -> Path | None:
    """Walk up the project_dir to find toolkit/reference/HP_QUICK_REF.md.

    Standard layout: examples/<project>/ — toolkit is at ../../toolkit/.
    """
    candidates = [
        project_dir.parent.parent / "toolkit" / "reference" / "HP_QUICK_REF.md",
        project_dir.parent / "toolkit" / "reference" / "HP_QUICK_REF.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _html_escape(s: str | None) -> str:
    if s is None:
        return ""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#39;"))


# ─────────────────────────────────────────────────────────────────────
# CSS — print + paged-media rules
# ─────────────────────────────────────────────────────────────────────

_PDF_CSS = """
@page {
  size: A4 portrait;
  margin: 2cm 2.2cm 2cm 2.2cm;
  @bottom-right { content: counter(page); font-size: 9pt; color: #888; }
  @top-left { content: string(running-title); font-size: 9pt; color: #888; }
}

@page diagram {
  size: A4 landscape;
  margin: 1.5cm;
  @bottom-right { content: counter(page); font-size: 9pt; color: #888; }
}

@page cover-page {
  margin: 4cm 3cm;
  @bottom-right { content: ""; }
  @top-left { content: ""; }
}

@page toc-page {
  @top-left { content: ""; }
}

html { font-family: "Helvetica", "Arial", sans-serif; font-size: 11pt; color: #222; line-height: 1.45; }
body { margin: 0; padding: 0; }

/* Cover */
.cover-page {
  page: cover-page;
  page-break-after: always;
  height: 24cm;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.cover-title { font-size: 30pt; margin: 0 0 0.4cm 0; color: #1a1a1a; }
.cover-description { font-size: 13pt; color: #555; margin: 0 0 1.6cm 0; font-style: italic; }
.cover-meta p { margin: 0.18cm 0; font-size: 11pt; color: #444; }

/* TOC */
.toc-page { page: toc-page; page-break-after: always; }
.toc-title { font-size: 22pt; margin: 0 0 0.8cm 0; color: #1a1a1a; }
.toc { display: block; }
.toc-row { margin: 0.18cm 0; padding: 0; }
.toc-row a { color: #222; text-decoration: none; display: flex; align-items: baseline; }
.toc-leader { flex: 1; border-bottom: 1px dotted #aaa; margin: 0 0.3em; transform: translateY(-2pt); }
.toc-row a > .toc-pageno { font-variant-numeric: tabular-nums; }
.toc-row a > .toc-pageno::after { content: target-counter(attr(data-target), page); }
.toc-depth-0 { font-weight: 600; font-size: 11pt; margin-top: 0.32cm; }
.toc-depth-1 { font-size: 10pt; padding-left: 1cm; }
.toc-depth-2 { font-size: 9.5pt; padding-left: 2cm; color: #555; }

/* Stage covers — one-page section dividers */
.stage-cover {
  page-break-before: always;
  page-break-after: always;
  height: 24cm;
  display: flex;
  flex-direction: column;
  justify-content: center;
  string-set: running-title content();
}
.stage-cover-title { font-size: 26pt; margin: 0; color: #1a1a1a; }
.stage-cover-badge { font-size: 12pt; color: #666; margin-top: 0.4cm; }

/* Subsection header */
.subsection-header {
  page-break-before: always;
  string-set: running-title content();
}
.subsection-header h2 { font-size: 18pt; margin: 0 0 0.6cm 0; color: #333; padding-bottom: 0.2cm; border-bottom: 1px solid #ccc; }

/* Diagram pages (landscape) */
.diagram-page {
  page: diagram;
  page-break-before: always;
  text-align: center;
}
.diagram-title { font-size: 14pt; margin: 0 0 0.4cm 0; color: #333; }
.diagram {
  display: block;
  width: 100%;
  height: auto;
  max-height: 17cm;
  margin: 0 auto;
  object-fit: contain;
}

/* Prose / markdown sections */
.prose-section {
  page-break-before: always;
}
.prose-section h1 { font-size: 17pt; margin: 0 0 0.4cm 0; color: #1a1a1a; padding-bottom: 0.2cm; border-bottom: 1px solid #ccc; }
.prose-section h2 { font-size: 13pt; margin: 0.5cm 0 0.2cm 0; color: #333; }
.prose-section h3 { font-size: 11.5pt; margin: 0.35cm 0 0.15cm 0; color: #444; }
.prose-section p { margin: 0.2cm 0; }
.prose-section ul, .prose-section ol { padding-left: 1.2em; }
.prose-section li { margin: 0.06cm 0; }
.prose-section code {
  background: #f4f4f4;
  padding: 1px 4px;
  border-radius: 2px;
  font-family: "Courier New", monospace;
  font-size: 9.5pt;
}
.prose-section pre {
  background: #f7f7f8;
  border: 1px solid #e0e0e0;
  border-radius: 3px;
  padding: 0.3cm;
  overflow-x: auto;
  font-size: 9pt;
  line-height: 1.4;
}
.prose-section pre code { background: transparent; padding: 0; }
.prose-section table {
  border-collapse: collapse;
  margin: 0.3cm 0;
  font-size: 10pt;
  width: 100%;
}
.prose-section th, .prose-section td {
  border: 1px solid #ccc;
  padding: 4px 8px;
  text-align: left;
  vertical-align: top;
}
.prose-section th { background: #f4f4f4; font-weight: 600; }
.prose-section blockquote {
  border-left: 3px solid #ccc;
  margin: 0.3cm 0;
  padding: 0.1cm 0.4cm;
  color: #555;
  font-style: italic;
}
"""

_DOCUMENT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>{css}</style>
</head>
<body>
  {cover}
  {toc}
  {body}
  {appendix}
</body>
</html>
"""
