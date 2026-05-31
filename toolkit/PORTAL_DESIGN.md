# Project Portal + PDF — design

## ✅ Status: Locked 2026-05-23

Open questions resolved with the defaults I leaned toward — Kevin signed off ("okay go ahead") without overrides.

**Status:** locked.
**Branch:** `kg/project-portal-and-pdf`.
**Spawning conversation:** Kevin reported navigation links pointing to pre-`.generated.` filenames (bug fix landed as `d4efd14`); follow-up asks were "I should land in the project rather than a random directory" + a tree-of-everything sidebar + a generated PDF of the project tree.

## Goal

Two outputs from one source:

1. **Living portal** — an HTML view of the project usable during work. Every generated page gets a collapsible left-sidebar showing the full project tree, with "you-are-here" highlighting. A new root `project_index.generated.html` is the front door.
2. **Shareable PDF** — `project.generated.pdf` at the project root: cover, clickable TOC, per-stage section covers, and every artifact in document order. The thing you email to a reviewer or archive.

The **single source** is a `ProjectTree` data structure built from the `Project` model. Both renderers consume it.

## What "browse the project" looks like

The tree mirrors the actual artifact layout, organized by stage + the modernization sections. For fishing-rig, the rendered tree is:

```
AutoFishingRig
  Home                            project_index.generated.html
  Validation status               (inline on Home)

  Stage 1 — Context Diagram       ✅ locked
    Context Diagram               00-context/context.generated.html

  Stage 2 — Level-1 DFD           ✅ locked
    Level-1 DFD                   01-level1/dfd.generated.html

  Stage 3 — CSPECs                ✅ 1/1
    Bite Detector                 01-level1/cspecs/bite-detector/cspec.generated.html

  Stage 4 — PSPECs                ✅ 4/4
    Acquire Tension               01-level1/pspecs/acquire-tension.md
    Reel Controller               01-level1/pspecs/reel-controller.md
    Serve UI                      01-level1/pspecs/serve-ui.md
    Cloud Forward                 01-level1/pspecs/cloud-forward.md

  Stage 5 — Architecture          ✅ locked
    AFD                           architecture/afd.generated.html
    AID                           architecture/aid.generated.html
    Modules
      Main Controller Board       architecture/specs/controller.md
      Angler Mobile App           architecture/specs/angler-app.md
    Interconnects
      BLE Link                    architecture/specs/interconnects/ble.md

  Modernization
    ADRs (1)
      001: BLE transport          adrs/001-ble-transport.md
    SLOs Summary                  architecture/slos.md
    Bounded Contexts              — none declared
    Runbooks (2)
      tension-sensor-stuck        runbooks/tension-sensor-stuck.md
      slo-bite-to-set-burn        runbooks/slo-bite-to-set-burn.md

  Reference
    Dictionary                    dictionary.yaml
    HP Quick Reference            ../../toolkit/reference/HP_QUICK_REF.md
```

For solar, the tree additionally has a **Bounded Contexts** subtree under Modernization (2 contexts + 1 ACL) and a **Context Map** node.

## Data model

```python
# toolkit/hp_toolkit/render/tree.py

from dataclasses import dataclass, field
from typing import Literal

NodeKind = Literal[
    "root", "section", "subsection", "artifact", "external", "note",
]

@dataclass
class TreeNode:
    label: str
    kind: NodeKind = "section"
    href: str | None = None             # path relative to project root
    badge: str | None = None            # e.g. "✅ locked", "🟡 in flight"
    children: list["TreeNode"] = field(default_factory=list)
    # PDF only: when present, this node is a stage cover with a sectioned body.
    pdf_section_intro: str | None = None


def build_project_tree(project: Project, project_dir: Path) -> TreeNode:
    """Build the full project tree from the loaded Project model."""
    ...
```

`build_project_tree` walks the same model used by status, validate, and render today. Stage badges come from the existing `status._check_stage_N` functions (reused, not duplicated). Modernization counts come from `_modernization_summary`.

## HTML output

### `project_index.generated.html` (new)

The "Home" page. Layout:

```
┌───────────────────────────────────────────────────────────────────┐
│  AutoFishingRig                                                    │
│  Motorized rig that auto-detects bites and reels in fish.          │
│  Last rendered 2026-05-23 · Validation: ✅ no errors               │
├──────────────────┬────────────────────────────────────────────────┤
│ [sidebar: tree]  │  Stages                                         │
│                  │    ✅ Stage 1 — Context Diagram                 │
│                  │    ✅ Stage 2 — Level-1 DFD                     │
│                  │    ...                                           │
│                  │                                                 │
│                  │  Modernization                                  │
│                  │    ADRs: 1 · Budgets/TPMs: 2+2 · SLOs: 1 · ...  │
│                  │                                                 │
│                  │  Quick links                                    │
│                  │    Dictionary · HP Quick Reference · Tutorial   │
└──────────────────┴────────────────────────────────────────────────┘
```

Same content as `hp-status` output, just rendered as HTML with click-through links.

### Sidebar injection on every generated HTML

The five existing `wrap_*_html` wrappers in `cytoscape.py` (`wrap_context_html`, `wrap_dfd_html`, `wrap_cspec_html`, `wrap_afd_html`, `wrap_aid_html`) gain two new optional parameters:

```python
def wrap_*_html(
    project: Project,
    elements: list[dict] | None = None,
    *,
    drill_target: str | None = "...",
    tree: TreeNode | None = None,          # NEW
    current_path: str | None = None,       # NEW — for "you-are-here" highlight
) -> str:
```

When `tree` is None (back-compat for direct callers), no sidebar is rendered — current behavior preserved. When `tree` is provided, a collapsible left sidebar is injected.

Sidebar HTML structure:

```html
<aside id="hp-sidebar" class="hp-sidebar" data-collapsed="false">
  <button class="hp-sidebar-toggle" aria-label="Toggle sidebar">◀</button>
  <div class="hp-sidebar-header">
    <strong>AutoFishingRig</strong>
    <span class="hp-validation-pill ok">✅ valid</span>
  </div>
  <nav class="hp-tree">
    <details open><summary>Stage 1 — Context Diagram</summary>
      <ul>
        <li><a href="../00-context/context.generated.html" class="current">Context Diagram</a></li>
      </ul>
    </details>
    ...
  </nav>
</aside>
```

- Uses native `<details>` / `<summary>` for collapse state on each section — no JS required for the basics.
- Toggle button collapses the whole sidebar to a 24px-wide strip (just the toggle), reclaiming canvas for wide diagrams.
- Collapse state (whole sidebar + per-section) persisted via `localStorage` so navigating between pages doesn't lose context.
- Current page gets a `.current` class for highlighting.

CSS lives in a new `toolkit/hp_toolkit/render/static/sidebar.css` injected into every page (or inlined — TBD; inlined keeps the artifact self-contained).

## PDF output

### Single file: `<project>/project.generated.pdf`

Structure:

```
[Cover page]
  AutoFishingRig
  Motorized rig that auto-detects bites and reels in fish.
  Generated YYYY-MM-DD
  Validation: ✅ no errors

[Table of Contents]
  Stages
    1 — Context Diagram .................... 3
    2 — Level-1 DFD ........................ 5
    ...
  Modernization
    ADRs ................................... 22
    SLOs ................................... 25
    Runbooks ............................... 27

[Stage cover: Stage 1 — Context Diagram]
  Stage 1 — Context Diagram
  ✅ Locked YYYY-MM-DD · 5 terminator(s) · proposal locked

[Stage 1 body]
  Context Diagram (embedded SVG, sized to fit)
  Description / notes

[Stage cover: Stage 2 — Level-1 DFD]
...
```

### Renderer

```python
# toolkit/hp_toolkit/render/pdf.py

def render_project_pdf(project: Project, project_dir: Path, out_path: Path) -> None:
    """Generate <project_dir>/project.generated.pdf."""
    tree = build_project_tree(project, project_dir)
    html_doc = _compose_pdf_html(project, tree, project_dir)
    weasyprint.HTML(string=html_doc, base_url=str(project_dir)).write_pdf(out_path)
```

`_compose_pdf_html` builds one large HTML document with:
- A `<style>` block of print-friendly CSS (page-break controls, page numbers via `@page` rules, font, embedded TOC styling).
- Cover page section.
- TOC section (anchors filled in; WeasyPrint resolves page numbers via `target-counter()` CSS).
- Per-section content: tree → walk depth-first → for each artifact:
  - If it's an `.svg`: `<img src="...">` (WeasyPrint embeds SVG natively).
  - If it's a generated HTML page: extract the diagram SVG (skip the sidebar/legend chrome).
  - If it's a markdown file (PSPEC / AMS / AIS / ADR / runbook): run through the `markdown` library → HTML → inline into the doc.

### Dependencies

Two new Python deps via `uv`:

- `weasyprint` — HTML+CSS → PDF.
- `markdown` — Markdown → HTML.

WeasyPrint has system deps (Pango / cairo / GDK-PixBuf). On Ubuntu these are typically already installed; `toolkit/bootstrap.sh` may need a one-line apt-install fallback hint for users on minimal images.

### CLI

```bash
# Render everything including PDF
uv run python scripts/render_project.py <dir>

# Render only the PDF (skips diagram regeneration if cached)
uv run python scripts/render_project.py <dir> --pdf-only

# Skip the PDF (faster iteration during HTML work)
uv run python scripts/render_project.py <dir> --no-pdf
```

Default: PDF is always generated. Cheap on fishing-rig/solar (sub-second on a modern dev box).

## Implementation order

Three commits on this branch:

1. **Commit 1 — Project tree + index page.**
   - `hp_toolkit/render/tree.py` with `build_project_tree`.
   - `hp_toolkit/render/index.py` with `render_project_index_html(project, tree)`.
   - `scripts/render_project.py` writes `project_index.generated.html` at project root.
   - Verified on fishing-rig + solar + doorbell.
   - No changes yet to existing wrappers — sidebar comes in commit 2.

2. **Commit 2 — Sidebar injection on every page.**
   - `hp_toolkit/render/sidebar.py` with `render_tree_sidebar(tree, current_path)`.
   - CSS at `hp_toolkit/render/static/sidebar.css`; inlined into every wrap_*_html output.
   - Wrappers in `cytoscape.py` accept `tree` + `current_path` kwargs.
   - `scripts/render_project.py` builds the tree once + passes it to every wrap call.
   - Collapse toggle JS (10–20 lines) inlined; uses `localStorage`.
   - Verified by clicking through fishing-rig + solar from `project_index.generated.html`.

3. **Commit 3 — PDF generation.**
   - `hp_toolkit/render/pdf.py` with `render_project_pdf`.
   - New dep entries in `pyproject.toml` (weasyprint, markdown).
   - `scripts/render_project.py` gains `--pdf-only` / `--no-pdf` flags.
   - Verified by opening generated `project.generated.pdf` for fishing-rig and solar.
   - `toolkit/README.md` updated: new dep mention, new CLI flag, new artifact in the table.

After all three, `hp-render` skill markdown gets a paragraph mentioning the new outputs (sidebar + index + PDF), and the example projects get rendered + committed (or `.generated.pdf` gets gitignored — see Open Questions).

## Backward compatibility

- All new `tree=` / `current_path=` kwargs default to `None` — direct callers of the wrappers continue to work unchanged.
- `project_index.generated.html` and `project.generated.pdf` are new artifacts at known paths; they don't overwrite anything.
- The existing per-page navigation (`↑ Parent`, drill-down) continues to work; the sidebar is additive.

## Locked decisions

### Q1. Should `project.generated.pdf` be committed?

- [ ] Yes — match the existing pattern of `*.generated.svg` (tracked).
- [ ] No — gitignore like the `*.generated.html` files already are.
- [x] **Only the example projects** — fishing-rig + solar PDFs tracked; doorbell + user projects ignored.

  *Why:* the demos are the documented reference; reviewers browsing the repo on GitHub benefit from a viewable PDF on the example projects. User projects shouldn't be polluted by toolkit-generated binaries.

### Q2. PDF page orientation for wide diagrams?

- [ ] Portrait throughout, diagrams scaled to fit.
- [x] **Landscape pages just for wide diagrams** — `@page :diagram { size: A4 landscape; }` named-page rule applied to a wrapper div.
- [ ] Landscape throughout.

  *Why:* portrait would shrink 4090px-wide D2 SVGs to ~14% scale (unreadable). Landscape-throughout makes prose worse for no benefit on prose pages. Mixed orientation is the WeasyPrint sweet spot — well-supported by `@page` named pages.

### Q3. Markdown rendering library?

- [x] **`markdown`** (Python-Markdown) with `tables`, `fenced_code`, `attr_list`, `toc`, `sane_lists` extensions.
- [ ] `mistune`
- [ ] `markdown-it-py`

  *Why:* mature and covers everything our sidecars use (GFM-style tables, fenced code blocks, attr-list for IDs/classes). Spot-check confirms PSPEC/AMS/AIS/ADR markdown stays within these features.

### Q4. Reference-card location in PDF?

- [x] **Include `HP_QUICK_REF.md` as an appendix.**
- [ ] Link only (external).

  *Why:* the PDF is meant to be self-contained for sharing. The reference card is small + universally relevant for HP readers.

### Q5. Sidebar on non-HTML rendered artifacts (markdown sidecars)?

- [ ] Leave them as markdown.
- [x] **Also wrap them in HTML.** A new `render_markdown_artifact_html(md_path, tree, current_path)` step converts each `.md` sidecar to a sidebar'd `.generated.html` (markdown content + the same sidebar). Original `.md` source preserved alongside.

  *Why:* uniform navigation is the point of this feature. The cost (doubling rendered-artifact count) is modest and the navigation gain is large.

## Notes

- Once Commit 1 is in, the index page itself is a nice incremental improvement even before the sidebar lands.
- WeasyPrint's `@page` CSS is the reason we can do clickable TOC + page numbers without a heavier toolchain.
- The sidebar tree is also a natural place to surface validation errors per stage in a future iteration — out of scope here.

---

*Drafted 2026-05-23 on `kg/project-portal-and-pdf`. Pattern matches the prior design docs: `MODERNIZATION_DESIGN.md`, `BOUNDED_CONTEXTS_DESIGN.md`, `ARCH_DESIGN.md`, `PSPEC_DESIGN.md`.*
