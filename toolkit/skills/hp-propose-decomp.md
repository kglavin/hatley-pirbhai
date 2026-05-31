---
name: hp-propose-decomp
description: Stage 2 — draft a form-based Level-N+1 DFD decomposition proposal. Reads the locked parent diagram (Context or higher-level DFD), proposes internal bubbles + data stores + internal flows, writes a reviewable proposal.md with Claude's recommended defaults pre-checked.
---

# hp-propose-decomp

## When to use

Decomposing a process bubble into its level-N+1 internals — typically `sys_root` → Level-1 DFD after Stage 1 locks, or any internal process that needs further breakdown.

Specifically:

- A parent diagram is locked (Status: Locked on its proposal, dictionary entries materialized, naming review resolved).
- The bubble being decomposed needs more than ~3 internal processes to express its behavior — i.e., it's worth a separate page.
- The decomposition has multiple plausible shapes; the user needs to pick deliberately rather than have Claude commit silently.

This is the **Propose + Surface Ambiguity** AI move applied to a single-level decomposition.

## What it does

Drafts `<level-dir>/proposal.md` as a form-based batch-review document — same shape as [`examples/solar/01-level1/proposal.md`](../../examples/solar/01-level1/proposal.md) and [`examples/fishing-rig/01-level1/proposal.md`](../../examples/fishing-rig/01-level1/proposal.md).

Standard decision set (7–8 decisions; project-shape varies the exact list):

| # | Decision | What it pins down |
|---|---|---|
| 1 | Decomposition coarseness | How many internal processes (e.g., "5 + optional 6th") |
| 2 | Data store presence | Explicit `store_*` for shared state vs implicit / pass-through |
| 3 | Internal flow style | Event-driven, periodic-tick, or hybrid |
| 4 | State-rich behavior owner | Which bubble carries the CSPEC at Stage 3 (`needs_cspec: true`) |
| 5 | Cross-cutting concerns | Where do fault handling / alerts / overrides live |
| 6 | Boundary flow refinement | Each level-N flow's level-N+1 endpoint (which internal consumes/produces) |
| 7 | Naming convention | Keep `proc_*` / `store_*` / `event_*` / `data_*` / `cmd_*` prefixes? |
| 8 | Anything else | Free-form escape hatch |

Each decision lists alternatives with Claude's recommended default **pre-checked** and provenance noted ("matches solar's pattern"; "minimum bubbles consistent with single-responsibility"; "AI inference from your description"). The user toggles overrides in MPE, saves once, pings back.

On lock, the skill writes the `## ✅ Status: Locked YYYY-MM-DD` header, populates `dictionary.yaml` with internal processes + data stores + internal flows + `refined_source`/`refined_target` on boundary flows, then hands off to [`hp-confirm-naming`](hp-confirm-naming.md).

## Behavior

When invoked, conversationally:

1. **Read the parent.** Load `dictionary.yaml`; pick out the entity being decomposed (defaults to `sys_root` for Stage 2). Find the locked parent diagram's SVG to embed in the context recap.
2. **Draft a proposal DFD inline.** Hand-author a Mermaid + D2 of the proposed decomposition (`proposal-dfd.{mmd,d2}` + rendered `proposal-dfd.svg`). This is a *proposal-specific* diagram, separate from the eventual `dfd.generated.*` — those come from the dictionary, which doesn't yet contain the internals.
3. **Identify which bubble owns the CSPEC.** Mark exactly one (or rarely two) bubble as state-rich. This becomes `needs_cspec: true` in the dictionary and unlocks Stage 3.
4. **Refine every boundary flow.** For each level-N flow crossing the parent's boundary, name its level-N+1 endpoint (`refined_source` / `refined_target` on the Flow). Boundary flows must balance — every level-N flow must appear at level-N+1.
5. **Write `proposal.md`** with: stage header → form-based-review instructions → context recap (level-N SVG embedded) → proposed decomposition (proposal-dfd.svg embedded) → "Bubble roles at a glance" table → numbered decisions with alternatives + pre-checked recommendation + provenance.
6. **Tell the user**: "Open `<level-dir>/proposal.md` in MPE, override any defaults, save, ping me when done."
7. **On user ping**: parse decisions, write Status: Locked block + resolution table, populate dictionary, run [`hp-validate`](hp-validate.md) (catches refinement gaps; boundary-flow balance check), then [`hp-confirm-naming`](hp-confirm-naming.md), then [`hp-render`](hp-render.md).

## Discipline

- **Propose graphically before prose.** The proposal embeds a rendered diagram of the proposed decomposition up front, *then* the decisions. Dense 5-bubble decomposition text is unreadable; the diagram is the artifact. (Tactic: *Recap with diagrams, not text walls*.)
- **Balance check is non-negotiable.** Every level-N boundary flow must have a `refined_source` or `refined_target` (whichever applies) pointing at a level-N+1 internal entity. `hp-validate`'s reference-integrity check catches misses; surface them at proposal time, not after lock.
- **Exactly one state-rich bubble per decomposition (typical).** Decisions 4 and 5 collude — overrides, alerts, and faults usually live with the state-rich bubble's CSPEC, not scattered across the DFD. Stage 3 is easier when the locus is unambiguous.
- **Don't write internal flows that bypass the boundary.** Every internal process either consumes or produces something visible at level-N (via refinement) or talks only to the data store. Free-floating internal-only processes that touch nothing observable from outside are usually missed responsibilities.
- **Working names are still throwaway.** As at Stage 1, names get reviewed in the follow-up `hp-confirm-naming` pass. Don't pre-litigate naming in this skill.

## Lived examples

- [`examples/solar/01-level1/proposal.md`](../../examples/solar/01-level1/proposal.md) — first form-based Stage 2 proposal (the pattern was invented here). 7 decisions; 5 internal bubbles + optional 6th; `proc_compute_balance` flagged `needs_cspec: true`. Caught 8 label drifts at render time.
- [`examples/fishing-rig/01-level1/proposal.md`](../../examples/fishing-rig/01-level1/proposal.md) — second Stage 2 proposal on a fresh project. 8 decisions; `proc_detect_bite` is the state-rich bubble. Validated transferability: same form, different domain.

## Implementation status

**Skill description: ✅ drafted.** Code wiring planned — would live as `hp_toolkit/proposals/decomp.py` or extend `render_project.py` with a `--propose` subcommand. Until wired, invoke conversationally: Claude reads the locked parent + writes `proposal.md` + drafts `proposal-dfd.{mmd,d2,svg}` following the template above.

The proposal-specific diagram (`proposal-dfd.svg`) is hand-authored at proposal time because the dictionary doesn't yet have the level-N+1 internals — the rendered `dfd.generated.svg` only becomes available *after* the proposal locks and the dictionary is populated.

## See also

- Tactic source: [`PLAN.md` > Methodology Tactics > A > Propose + Surface Ambiguity](../../PLAN.md), [`PLAN.md` > Methodology Tactics > B > Form-based batch review](../../PLAN.md), [`PLAN.md` > Methodology Tactics > B > Propose graphically before prose](../../PLAN.md)
- Predecessor: [`hp-propose-context`](hp-propose-context.md) locks Stage 1.
- Sequel: [`hp-confirm-naming`](hp-confirm-naming.md) reviews working names; [`hp-validate`](hp-validate.md) catches refinement gaps; [`hp-render`](hp-render.md) regenerates the DFD.
- Stage 3: [`hp-propose-cspec`](hp-propose-cspec.md) follows for each bubble flagged `needs_cspec: true`.
- HP reference: [`HP_QUICK_REF.md` > DFD, Data Store, Flow Refinement](../reference/HP_QUICK_REF.md)
