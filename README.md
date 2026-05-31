# Hatley-Pirbhai Toolkit Project

An AI-augmented systems-engineering methodology, built around the **Hatley-Pirbhai (HP)** structured-analysis framework from 1988/2000 and the modern AI capabilities of the 2020s. Bringing rigorous systems specification — long the domain of FAA-certified avionics — into reach for any AI-assisted development project.

## Two parts

This repository has two distinct halves:

```
hatley-pirbhai/
├── PLAN.md                     ← document of record (decisions, tactics, design log)
├── examples/                   ← workshop: dogfood projects developed using the toolkit
│   ├── solar/                  ← Solar Local Stack (Hoymiles + Victron orchestration)
│   └── fishing-rig/            ← AutoFishingRig (automated bite-detection)
├── reference-docs/             ← workshop reading aids (the two HP source PDFs, gitignored)
├── graphify-out/               ← workshop methodology analysis (gitignored)
│
└── toolkit/                    ← THE DELIVERABLE — what ships to practitioners
    ├── README.md
    ├── bootstrap.sh            ← user-space install of uv, d2, mmdc
    ├── pyproject.toml          ← Python project (uv-managed)
    ├── hp_toolkit/             ← model / load / validate / render code
    ├── scripts/                ← render_project.py, check_dictionary.py
    ├── skills/                 ← Claude Code skill files
    └── reference/HP_QUICK_REF.md   ← HP method vocabulary card
```

- **The workshop** (everything at the repo root) — design log, dogfood projects, methodology development. This is where the toolkit is built and exercised.
- **The toolkit** ([`toolkit/`](toolkit/)) — the deliverable that ships to practitioners. Python package, scaffolding scripts, skill definitions, reference card.

## What the toolkit does

Given a project's `dictionary.yaml` — the canonical declaration of every entity, flow, and transition — the toolkit:

1. **Validates** the model (reference integrity, hierarchy consistency, coverage metrics, orphan detection)
2. **Renders** the model in three notations:
   - **Mermaid** — `.mmd` + `.svg`
   - **D2** — `.d2` + `.svg`
   - **Cytoscape interactive HTML** — clickable, drag-to-rearrange, double-click drill-down navigation between levels
3. **Catches drift** — the renderer round-trip (dictionary → diagram → diff against hand-written) surfaces inconsistencies the human eye misses

Three artifact kinds are rendered across all three notations:

| Artifact | Source | What it shows |
|---|---|---|
| **Context Diagram** (level 0) | from `dictionary.yaml` | The system + its external terminators + boundary flows |
| **Level-1 DFD** | from `dictionary.yaml` | Internal processes + data stores + refined boundary flows |
| **CSPEC** (state machine) | from `dictionary.yaml` (`transitions:` section) | The fishing/control sequence for any process flagged `needs_cspec: true` |

## Quick start

```bash
# 1. Install (user-space; no sudo)
bash toolkit/bootstrap.sh

# 2. Validate an example project
cd toolkit
uv run python -m hp_toolkit.validate ../examples/solar/dictionary.yaml

# 3. Render an example end-to-end (Context + DFD + CSPEC)
uv run python scripts/render_project.py ../examples/solar
uv run python scripts/render_project.py ../examples/fishing-rig
```

Then open any of the `.generated.html` files under `examples/*/` in a browser to see the interactive workspaces.

## Where to go next

- **For methodology refresh** — [`toolkit/reference/HP_QUICK_REF.md`](toolkit/reference/HP_QUICK_REF.md) (60+ HP terms with modern analogs)
- **For toolkit usage** — [`toolkit/README.md`](toolkit/README.md)
- **For example projects** — [`examples/solar/`](examples/solar/) (mature reference) or [`examples/fishing-rig/`](examples/fishing-rig/) (transferability test)
- **For design rationale and lived methodology tactics** — [`PLAN.md`](PLAN.md)

## Status

End-to-end rendering pipeline live for both dogfood projects. Both have locked Context + level-1 DFD + at least one CSPEC, all generated from their respective `dictionary.yaml` files via the same generic script. **Toolkit transferability has been validated** across two genuinely different domains (solar energy orchestration; automated fishing rig).

Deferred work tracked in [`PLAN.md`](PLAN.md) > Open Questions: per-level label abbreviation, edge refinement schema, brownfield ingest, more skills (`hp-init`, `hp-propose-context`, etc.).
