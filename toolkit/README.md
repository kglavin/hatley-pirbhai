# HP Toolkit

An AI-augmented toolkit around the **Hatley-Pirbhai methodology** for systems requirements and architecture specification. Brings the rigor of HP (1988 + 2000 books) into modern AI-assisted development.

## Status

Early. This is the *distribution-side* of an in-flight project. For project state, decisions, and the design log, see [`../PLAN.md`](../PLAN.md) in the repo root (workshop side).

## What this toolkit is for

Modern AI-assisted development has a coherence problem: proposals get to 85%, features rathole into subsystems, interfaces get lost in implementation, and there's no single northstar across a growing pile of `.md` files. HP was invented in 1988 for exactly this — keeping large, long-lived, multi-author systems coherent on FAA-certified avionics. This toolkit makes HP's rigor affordable in 2026 by automating its bookkeeping with AI, while preserving the discipline that made it work.

It's for senior engineers and architects who've watched UML, Agile, and "just-enough docs" fail to scale, and want a rigorous method that doesn't require expensive enterprise tooling.

## Install

```bash
bash toolkit/bootstrap.sh
```

User-space only (`~/.local/bin/`); no sudo required; idempotent.

Installs:

- **`uv`** — Python project/env manager (Astral). Powers the toolkit's Python side.
- **`d2`** — declarative diagrams renderer. For one of the visualization modes.
- **`mmdc`** — Mermaid CLI. For rendering Mermaid views to SVG/PNG without VSCode.

After install: add `~/.local/bin` to your `$PATH` if you haven't already.

## Layout

```
toolkit/
├── README.md              # this file
├── bootstrap.sh           # environment setup (idempotent)
├── reference/
│   └── HP_QUICK_REF.md    # HP method vocabulary card
├── pyproject.toml         # (planned) Python project — model core, validators, renderers
├── hp_toolkit/            # (planned) Python package
└── skills/                # (planned) Claude Code skill files, one per workflow stage
```

## Get started

Right now: read [`reference/HP_QUICK_REF.md`](reference/HP_QUICK_REF.md) for the HP vocabulary card.

The methodology workflow (Context Diagram → leveled DFDs → CSPECs/PSPECs → Architecture model → Mechanisms → validation) and the skills that drive it are coming. See [`../PLAN.md`](../PLAN.md) for current status and the strawman workflow.

## License

TBD.
