# HP Toolkit — Skills

Per-workflow-stage skill files for the HP Toolkit. Each skill is a markdown file with YAML frontmatter; together they make up the toolkit's user-facing methodology surface.

**Format** (matches the Claude Code skill convention):

```markdown
---
name: hp-skill-name
description: One-line summary used to decide relevance.
---

# hp-skill-name

## When to use
...

## What it does
...

## Behavior
...

## Discipline
...

## See also
...
```

## Skill catalog

| Skill | Status | Stage / Purpose |
|---|---|---|
| [`hp-confirm-naming`](hp-confirm-naming.md) | ✅ drafted | Cross-cutting — form-based naming review after any AI move that introduces named entities |
| [`hp-validate`](hp-validate.md) | ✅ drafted + code live | Run validators (reference integrity, hierarchy, coverage metrics, orphan detection) |
| [`hp-render`](hp-render.md) | ✅ drafted + code live | Regenerate diagram sources + SVGs from `dictionary.yaml` |
| [`hp-init`](hp-init.md) | ✅ drafted + code live | Scaffold a new HP project (directory layout + dictionary template + Stage 1 proposal) |
| [`hp-status`](hp-status.md) | ✅ drafted | Show what stages a project has reached + coverage metrics |
| [`hp-propose-context`](hp-propose-context.md) | ✅ drafted | Stage 1: form-based context-diagram proposal for a new project |
| [`hp-propose-decomp`](hp-propose-decomp.md) | ✅ drafted | Stage 2: form-based level-N+1 DFD decomposition proposal |
| [`hp-propose-cspec`](hp-propose-cspec.md) | ✅ drafted | Stage 3: form-based CSPEC state-machine proposal |
| [`hp-propose-pspec`](hp-propose-pspec.md) | ✅ drafted | Stage 4: form-based PSPEC proposal for leaf bubbles |
| `hp-ingest` | planned (phase 5) | Brownfield ingest — read existing proposals + code, propose an HP model |

## Provenance

These skills are the codified form of the methodology tactics in [`../../PLAN.md`](../../PLAN.md) > *Methodology Tactics*. Each skill file references the tactics it embodies and the lived examples that informed it.

## Working with skills

The skills are markdown files designed to be read by Claude Code (or referenced manually). They describe **when** to use a pattern, **what** it does, **how** it behaves on invocation, and the **discipline** rules that prevent regression. They don't yet include direct executable wiring — that's a future addition once we settle the patterns enough to automate them.

Two example projects exercise the patterns these skills describe: [`../../examples/solar/`](../../examples/solar/) and [`../../examples/fishing-rig/`](../../examples/fishing-rig/).
