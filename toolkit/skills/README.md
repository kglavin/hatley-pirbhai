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
| [`hp-propose-architecture`](hp-propose-architecture.md) | ✅ drafted | Stage 5: form-based Architecture Model proposal (AFD + AID + AMS + AIS + allocation) |
| [`hp-capture-adr`](hp-capture-adr.md) | ✅ drafted | Cross-cutting — mid-decision ADR capture (Modernization #10) |
| [`hp-propose-budgets-and-tpms`](hp-propose-budgets-and-tpms.md) | ✅ drafted | Post-Stage-5: NASA design-time budgets + tracked-over-time TPMs (Modernization #21 + #22) |
| [`hp-propose-observability`](hp-propose-observability.md) | ✅ drafted | Per leaf process / module — runtime metrics + alerts + runbooks (Modernization #1 + #33) |
| [`hp-propose-slos`](hp-propose-slos.md) | ✅ drafted | After observability — SLI/SLO/SLA commitments (Modernization #32) |
| [`hp-propose-threat-model`](hp-propose-threat-model.md) | ✅ drafted | Per cross-trust-zone interconnect — STRIDE + MITRE catalog refs (Modernization #8.2 + #8.3) |
| [`hp-propose-bounded-contexts`](hp-propose-bounded-contexts.md) | ✅ drafted | When team/vocabulary boundaries become visible — DDD contexts + ACLs (Modernization #5) |
| [`hp-ingest`](hp-ingest.md) | ✅ drafted + code live | Brownfield ingest — codebase → draft dictionary.yaml via the multi-stage pipeline (master orchestrator) |
| [`hp-ingest-scan`](hp-ingest-scan.md) | ✅ drafted + code live | Stage 0 — file walk + 6-category role-hint classifier (no LLM) |
| [`hp-ingest-glossary`](hp-ingest-glossary.md) | ✅ drafted + code live | Stage 0c-curate (optional) — LLM curator reduces ~10k deterministic glossary candidates to ~30–60 canonical entries (H.4.b) |
| [`hp-ingest-boundary`](hp-ingest-boundary.md) | ✅ drafted | Stage 1 — boundary candidates → Stage-1 terminators + boundary flows (reads glossary + user-docs + testbeds) |
| [`hp-ingest-processes`](hp-ingest-processes.md) | ✅ drafted | Stage 2 — process candidates → internal processes + data stores + internal flows (reads glossary + testbeds + external-context) |
| [`hp-ingest-leaf`](hp-ingest-leaf.md) | ✅ drafted | Stages 3+4 — per-process CSPEC or PSPEC; parallel 3–5 concurrent (reads glossary + testbeds + external-context) |
| [`hp-ingest-architect`](hp-ingest-architect.md) | ✅ drafted | Stage 5 — architecture candidates → modules + interconnects + allocation; reads typed `CandidateEdge`s, per-candidate rationale evidence, recipes, testbeds |
| [`hp-ingest-review`](hp-ingest-review.md) | ✅ drafted | Final reviewer — repair + validate + emit dictionary.yaml |

## Provenance

These skills are the codified form of the methodology tactics in [`../../PLAN.md`](../../PLAN.md) > *Methodology Tactics*. Each skill file references the tactics it embodies and the lived examples that informed it.

## Working with skills

The skills are markdown files designed to be read by Claude Code (or referenced manually). They describe **when** to use a pattern, **what** it does, **how** it behaves on invocation, and the **discipline** rules that prevent regression. They don't yet include direct executable wiring — that's a future addition once we settle the patterns enough to automate them.

Two example projects exercise the patterns these skills describe: [`../../examples/solar/`](../../examples/solar/) and [`../../examples/fishing-rig/`](../../examples/fishing-rig/).
