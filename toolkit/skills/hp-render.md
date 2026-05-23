---
name: hp-render
description: Generate diagram sources (Mermaid, D2; Cytoscape and SVG planned) from the project dictionary. The dictionary becomes the single source of truth; renderers replace hand-written diagram authoring.
---

# hp-render

## When to use

After any change to `dictionary.yaml` that affects diagram content:

- After a naming review applies renames (Mermaid/D2 sources should be regenerated to match)
- After a new entity, flow, or edge is added
- After a level's decomposition is locked
- Before committing — to ensure the hand-written diagrams haven't drifted from the dictionary

## What it does

Generates diagram sources from the Project model. Currently supports:

| View | Status | Function |
|---|---|---|
| Level-0 Context Diagram (Mermaid / D2) | ✅ live | `render.mermaid.render_context_diagram(project)` · `render.d2.render_context_diagram(project)` |
| Level-1 DFD (Mermaid / D2) | ✅ live | `render.mermaid.render_dfd(project, parent_id)` · `render.d2.render_dfd(project, parent_id)` — requires `refined_source` / `refined_target` populated on boundary flows |
| CSPEC state machine (Mermaid `stateDiagram-v2` / D2 containers) | ✅ live | `render.mermaid.render_state_machine` · `render.d2.render_state_machine` — requires `transitions:` populated, plus `is_initial: true` on the CSPEC entry state and each composite's initial sub-state |
| AFD + AID (Mermaid / D2) | ✅ live | `render.mermaid.render_afd` · `render.d2.render_afd` · `render.mermaid.render_aid` · `render.d2.render_aid` |
| Context Map (Mermaid / D2) | ✅ live | `render.mermaid.render_context_map` · `render.d2.render_context_map` — bounded contexts + ACLs |
| Cytoscape interactive HTML (Context / DFD / CSPEC / AFD / AID) | ✅ live | `render.cytoscape.wrap_*_html(project, tree=..., current_path=...)` — sidebar-aware; without the tree kwarg, back-compat sidebar-less output |
| PSPEC / AMS / AIS / ADR / SLOs / runbook markdown sidecars | ✅ live | `render.pspec.render_pspec_markdown` · `render.architecture.render_ams_markdown` / `render_ais_markdown` / `render_slos_summary` · `render.adr.render_adr_markdown` |
| Markdown sidecars → sidebar'd `.generated.html` wrappers | ✅ live | `render.markdown_artifact.render_markdown_artifact_html(md_text, tree, current_path, title)` — uniform left-sidebar navigation across every artifact |
| Project portal index | ✅ live | `render.index.render_project_index_html(project, project_dir)` → `project_index.generated.html` at project root |
| Project PDF (cover + TOC + per-stage + sidecars + HP Quick Ref appendix) | ✅ live | `render.pdf.render_project_pdf(project, project_dir)` → `project.generated.pdf` via WeasyPrint |
| SVG orchestration | ✅ live | `render.svg.render_d2_to_svg(src, out)` invokes `d2`; `render.svg.render_mermaid_to_svg(src, out)` invokes `mmdc` (with `.puppeteer-config.json` for Ubuntu sandbox). Both raise `FileNotFoundError` if the binary isn't installed (point user at `bash toolkit/bootstrap.sh`). |

Output is **deterministic** — same dictionary always produces byte-identical sources. Iteration order is YAML insertion order.

## Behavior

**CLI** (regenerate every artifact for a project):

```bash
cd toolkit
uv run python scripts/render_project.py <project-dir>                 # diagrams + sidebar'd HTML + index + PDF
uv run python scripts/render_project.py <project-dir> --pdf-only      # only the PDF (uses existing HTML/SVG)
uv run python scripts/render_project.py <project-dir> --no-pdf        # everything except the PDF (fast iteration)
```

Output:
- `*.generated.{mmd,d2,html,svg}` next to each diagram source.
- `*.md` sidecars (PSPEC / AMS / AIS / ADR / SLOs / runbook) + a sibling `*.generated.html` wrapper carrying the project sidebar.
- `project_index.generated.html` at the project root (front-door page).
- `project.generated.pdf` at the project root (single-file shareable PDF).

**Programmatic** (from another skill or script):

```python
from hp_toolkit import load
from hp_toolkit.render import mermaid, d2

project = load("examples/solar/dictionary.yaml")
mermaid_source = mermaid.render_context_diagram(project)
d2_source      = d2.render_context_diagram(project)

# Write to canonical locations
Path("examples/solar/00-context/context.d2").write_text(d2_source)
```

## Discipline

- **The dictionary is the single source of truth.** Once the renderer is reliable for an artifact kind, the hand-written sources for that kind become "old" — regeneration is canonical.
- **Renderers are deterministic.** No timestamps, no random ordering, no host-dependent paths in output. Same dictionary → same source bytes. This is what makes drift detection possible.
- **Stylistic differences are acceptable.** Generated output uses long stable_ids (e.g. `term_inverters`); hand-written used short IDs (`HM`). Visual rendering of the SVG is identical; the source-text difference is stylistic only. Future refinement could add an optional `short_id` field to the dictionary.
- **Drift is bug.** If the renderer's output disagrees with the hand-written *in label/source/target/kind*, that's drift — the hand-written has been edited without updating the dictionary (or vice versa). Fix the dictionary (or the hand-written, depending on which has the intent).

## Lived example

First run of `hp-render` against the solar dogfood **caught the F8 label drift**: the dictionary said `"F8: optional telemetry fwd"` but `context.md` said `"F8: optional telemetry forward"`. The hand-written had the right intent; the dictionary had been written hastily. Fixed in the dictionary; re-running produced matching output (modulo node-ID style).

This is the round-trip the renderer was designed to enable: **dictionary → diagrams → diff → fix → match**.

## See also

- Tactic: [`PLAN.md` > Methodology Tactics > B > Model = source of truth; views are derived](../../PLAN.md)
- Tactic: [`PLAN.md` > Methodology Tactics > B > Names are first-class artifacts; reify them in a dictionary](../../PLAN.md)
- Code: [`toolkit/hp_toolkit/render/mermaid.py`](../hp_toolkit/render/mermaid.py) · [`toolkit/hp_toolkit/render/d2.py`](../hp_toolkit/render/d2.py)
- Script: [`toolkit/scripts/render_dogfood.py`](../scripts/render_dogfood.py)
- Companion: [`hp-validate`](hp-validate.md) (typically run after `hp-render` to verify the regenerated state)
