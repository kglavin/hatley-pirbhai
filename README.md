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

Given a project's `dictionary.yaml` — the canonical declaration of every entity, flow, transition, architecture module, ADR, budget, SLO, bounded context, and more — the toolkit:

1. **Validates** the model (reference integrity, hierarchy consistency, coverage metrics, orphan detection, PSPEC balancing, Stage 5 allocation, modernization cross-references: STRIDE on cross-trust-zone interconnects, TPM vs budget direction, SLO→TPM resolution, ACL routing on cross-context flows, MITRE/CWE/compliance ID format)
2. **Renders** the model in three notations:
   - **Mermaid** — `.mmd` + `.svg`
   - **D2** — `.d2` + `.svg`
   - **Cytoscape interactive HTML** — clickable, drag-to-rearrange, double-click drill-down navigation between levels
3. **Catches drift** — the renderer round-trip (dictionary → diagram → diff against hand-written) surfaces inconsistencies the human eye misses

Rendered artifacts span the five HP stages plus a modernization layer:

| Artifact | Source | What it shows |
|---|---|---|
| **Context Diagram** (level 0) | from `dictionary.yaml` | The system + its external terminators + boundary flows |
| **Level-1 DFD** | from `dictionary.yaml` | Internal processes + data stores + refined boundary flows |
| **CSPEC** (state machine) | from `dictionary.yaml` (`transitions:` section) | Control sequence for any process flagged `needs_cspec: true` |
| **PSPECs** (Stage 4) | per leaf process | INPUTS / OUTPUTS / TRANSFORMATION + optional V&V + Observability sections |
| **AFD / AID + AMS / AIS sidecars** (Stage 5) | per architecture module + interconnect | Allocation + design rationale + constraints + Verification + Budgets + TPMs + Observability + SLOs + STRIDE + LINDDUN + Catalog refs |
| **ADR sidecars** *(modernization #10)* | per `adrs:` entry | Nygard-style record with MITRE/CWE refs |
| **Context Map** *(modernization #5)* | from `bounded_contexts:` + ACLs | Per-context boundaries with ACL translations |
| **SLOs summary** *(modernization #32)* | from `service_level_objectives:` | Project-level SLO table |
| **Project portal index** *(landing page)* | from the full project tree | `project_index.generated.html` — front-door page with collapsible sidebar; every other rendered HTML page carries the same sidebar |
| **Project PDF** *(shareable review pack)* | from the full project tree | `project.generated.pdf` — cover + TOC + per-stage covers + all diagrams + all markdown sidecars + HP Quick Reference appendix |
| **Brownfield ingest** *(bootstrap path)* | from an existing codebase | `hp-ingest <codebase>` runs a 6-agent pipeline (scan → boundary → processes → leaf×N parallel → architect → review) that produces a draft `dictionary.yaml` — Python does ~80% of the structural work, LLM agents make the architectural judgment |

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

End-to-end rendering pipeline live for both dogfood projects. Both have **all 5 HP stages locked + the modernization layer applied** (ADRs, design-time budgets + runtime TPMs, SLOs anchored to TPMs, per-leaf observability + V&V, STRIDE on cross-trust-zone interconnects + MITRE/CWE/compliance refs; solar additionally declares 2 bounded contexts + an Anti-Corruption Layer). All generated from each project's `dictionary.yaml` via the same generic script. Both projects also produce a **living portal** (`project_index.generated.html` + collapsible sidebar on every page) and a **shareable PDF** (`project.generated.pdf`, ~70–80 pages of cover + TOC + diagrams + sidecars + HP reference). **Toolkit transferability has been validated** across two genuinely different domains (solar energy orchestration; automated fishing rig). **Brownfield ingest pipeline shipped** — `hp-ingest <codebase>` orchestrates 6 LLM subagents over a deterministic Python prep layer to produce a draft `dictionary.yaml` from an existing codebase; first dogfood target is cloudctlplane.

Deferred work tracked in [`PLAN.md`](PLAN.md) > Open Questions: per-level label abbreviation, edge refinement schema, hp-ingest dogfood on cloudctlplane (next branch), per-context filtered renderer view (`hp-render-context`), third-project transferability (doorbell), merge-mode for incremental ingest (Q4-deferred v2 feature).
