# HP Toolkit

An AI-augmented toolkit around the **Hatley-Pirbhai methodology** for systems requirements and architecture specification. Brings the rigor of HP (1988 + 2000 books) into modern AI-assisted development.

## What this toolkit is for

Modern AI-assisted development has a coherence problem: proposals get to 85% then trail off, features rathole into subsystems, interfaces get lost in implementation, and there's no single northstar across a growing pile of `.md` files. HP was invented in 1988 for exactly this — keeping large, long-lived, multi-author systems coherent on FAA-certified avionics. This toolkit makes HP's rigor affordable in 2026 by automating its bookkeeping with AI, while preserving the discipline that made it work.

It's for senior engineers and architects who've watched UML, Agile, and "just-enough docs" fail to scale, and want a rigorous method that doesn't require expensive enterprise tooling.

## Install

```bash
bash toolkit/bootstrap.sh
```

User-space only (`~/.local/bin/`); no sudo; idempotent. Installs:

- **`uv`** — Python project/env manager (Astral)
- **`d2`** — declarative diagrams renderer
- **`mmdc`** — Mermaid CLI

After install: ensure `~/.local/bin` is on your `$PATH`.

## Usage

The toolkit operates on a per-project **`dictionary.yaml`** — HP's Requirements Dictionary in YAML form, declaring every entity (system, terminator, process, data store, state), every flow, every edge, and every transition. From that one canonical source, the toolkit validates, renders, and (eventually) detects drift.

### Validate

```bash
cd toolkit
uv run python -m hp_toolkit.validate <path/to/dictionary.yaml>
```

Runs four validators (reference integrity, hierarchy consistency, coverage metrics, orphan detection) and reports issues + percentages. Errors block; warnings document; info catches drift.

### Render

```bash
cd toolkit
uv run python scripts/render_project.py <project-directory>
```

Produces (for any project with a `dictionary.yaml`):

| Artifact | Mermaid | D2 | Cytoscape HTML | Mermaid SVG | D2 SVG |
|---|:---:|:---:|:---:|:---:|:---:|
| Context Diagram (level 0) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Level-1 DFD | ✅ | ✅ | ✅ | ✅ | ✅ |
| CSPEC (state machine) | ✅ | ✅ | ✅ | ✅ | ✅ |

All three Cytoscape HTML views support the hypertext navigation chain: double-click a decomposable bubble to drill in (`context.html` → `dfd.html` → `cspec.html`), `↑ Parent` link to walk back, dictionary + HP reference links per entity.

Output files land as `*.generated.{mmd,d2,html,svg}` sidecars in each project's level directories.

### Programmatic

```python
from hp_toolkit import load, validate
from hp_toolkit.render import mermaid, d2, cytoscape, svg

project = load("examples/solar/dictionary.yaml")
report  = validate(project)

if not report.ok:
    raise SystemExit(f"{len(report.errors)} validation errors")

# Generate Mermaid source for any view
mmd_source = mermaid.render_context_diagram(project)
mmd_source = mermaid.render_dfd(project, parent_id="sys_root")
mmd_source = mermaid.render_state_machine(project, machine_id="proc_compute_balance")

# Same shape for D2 and Cytoscape (cytoscape additionally has wrap_*_html)
html = cytoscape.wrap_context_html(project)
```

## Layout

```
toolkit/
├── README.md                      ← this file
├── bootstrap.sh                   ← environment setup (idempotent)
├── .puppeteer-config.json         ← mmdc sandbox config for Ubuntu 23.10+
├── pyproject.toml                 ← uv-managed Python project
├── uv.lock                        ← pinned dependencies
│
├── hp_toolkit/                    ← Python package
│   ├── __init__.py
│   ├── model.py                   ← Pydantic schemas (Project, Entity, Flow, Edge, Transition)
│   ├── load.py                    ← dictionary.yaml → validated Project
│   ├── validate.py                ← 4 validators + ValidationReport + CLI
│   └── render/
│       ├── mermaid.py             ← Context + DFD + state machine generators
│       ├── d2.py                  ← same in D2
│       ├── cytoscape.py           ← Cytoscape elements JSON + full HTML wrappers
│       └── svg.py                 ← orchestrate d2 + mmdc binaries
│
├── scripts/
│   ├── render_project.py          ← generic: render any project end-to-end
│   ├── render_dogfood.py          ← solar-specific (legacy; use render_project.py instead)
│   └── check_dictionary.py        ← summary + hierarchy view of a project
│
├── skills/                        ← Claude Code skill files
│   ├── README.md                  ← skill catalog
│   ├── hp-confirm-naming.md       ← form-based naming review (most-validated pattern)
│   ├── hp-validate.md             ← runs hp_toolkit.validate
│   ├── hp-render.md               ← regenerates diagram sources + SVGs from dictionary
│   └── ...                        ← more planned (hp-init, hp-propose-*, hp-ingest)
│
└── reference/
    └── HP_QUICK_REF.md            ← HP method vocabulary card (60+ terms with modern analogs)
```

## Examples

Two example projects live in [`../examples/`](../examples/) and exercise the full pipeline:

- [`examples/solar/`](../examples/solar/) — Solar Local Stack (Hoymiles microinverters + Victron + grid orchestration). The original dogfood; most mature. Stages 1-3 complete; CSPEC for Energy Manager (4-mode hierarchical state machine).
- [`examples/fishing-rig/`](../examples/fishing-rig/) — AutoFishingRig. The transferability test — built from scratch on a completely different domain. Stages 1-3 complete; CSPEC for Bite Detector (9-state flat machine).

Both projects render their full Context + DFD + CSPEC pipelines through `scripts/render_project.py` with no project-specific code.

## Status

End-to-end render pipeline live and validated across two domains. The toolkit reads a `dictionary.yaml`, validates it, and produces the complete artifact set in three notations with hypertext navigation. See [`../PLAN.md`](../PLAN.md) for design rationale, methodology tactics, and a chronological log of decisions.

## License

TBD.
