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
| Level-0 Context Diagram (Mermaid) | ✅ live | `render.mermaid.render_context_diagram(project)` |
| Level-0 Context Diagram (D2) | ✅ live | `render.d2.render_context_diagram(project)` |
| Level-1 DFD (Mermaid / D2) | ✅ live | `render.mermaid.render_dfd(project, parent_id)` · `render.d2.render_dfd(project, parent_id)` — requires `refined_source` / `refined_target` populated on boundary flows |
| State machine (Mermaid `stateDiagram-v2` / D2 containers) | ✅ live | `render.mermaid.render_state_machine(project, parent_machine_id)` · `render.d2.render_state_machine(project, parent_machine_id)` — requires `transitions:` populated, plus `is_initial: true` on the CSPEC entry state and each composite's initial sub-state |
| Cytoscape (Context HTML) | ✅ live | `render.cytoscape.render_context_elements(project)` + `wrap_context_html(project)` produces full HTML — Cytoscape script, side panel, navigation, legend, tap/dbltap event handlers |
| Cytoscape (DFD HTML + CSPEC HTML) | planned | reuse the wrapper pattern with view-specific element generators, style arrays, and legends |
| SVG orchestration | ✅ live | `render.svg.render_d2_to_svg(src, out)` invokes `d2`; `render.svg.render_mermaid_to_svg(src, out)` invokes `mmdc` (with `.puppeteer-config.json` for Ubuntu sandbox). Both raise `FileNotFoundError` if the binary isn't installed (point user at `bash toolkit/bootstrap.sh`). `mmdc` `-1` suffix is handled transparently. |

Output is **deterministic** — same dictionary always produces byte-identical sources. Iteration order is YAML insertion order.

## Behavior

**CLI** (regenerate everything in the dogfood):

```bash
cd toolkit && uv run python scripts/render_dogfood.py
```

Writes `*.generated.{mmd,d2}` sidecars next to the hand-written originals and diffs them so drift is visible without overwriting.

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
