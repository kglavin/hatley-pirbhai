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

**Skill catalog (current and planned):**

| Skill | Status | Stage |
|---|---|---|
| `hp-confirm-naming` | ✅ drafted | Cross-cutting — after any AI move that introduces named entities |
| `hp-validate` | ✅ drafted + code live | Run validators (reference integrity, hierarchy, coverage metrics, orphans) |
| `hp-render` | ✅ drafted + code live (level-0 Context, Mermaid + D2) | Regenerate diagram sources from the dictionary |
| `hp-propose-context` | planned | Stage 1: establish system context |
| `hp-propose-decomp` | planned | Stage 2: propose level-N+1 DFD decomposition |
| `hp-propose-cspec` | planned | Stage 3: propose CSPEC state machine |
| `hp-propose-pspec` | planned | Stage 4: propose PSPECs for leaf bubbles |
| `hp-propose-arch` | planned | Stage 5: propose Architecture Model |
| `hp-init` | planned | Initialize a new HP project (scaffolds dictionary, directories) |
| `hp-ingest` | planned (phase 5) | Brownfield ingest — read existing proposals/code and propose an HP model |

**Provenance:** these skills are the codified form of the methodology tactics in [`../../PLAN.md`](../../PLAN.md) > *Methodology Tactics*. Each skill file references the tactics it embodies.
