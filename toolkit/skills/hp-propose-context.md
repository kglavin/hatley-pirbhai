---
name: hp-propose-context
description: Stage 1 — draft a form-based Context Diagram proposal for a new HP project. Reads the user's description + current dictionary, proposes terminators / scope / flows, writes a reviewable proposal.md with Claude's recommended defaults pre-checked.
---

# hp-propose-context

## When to use

Starting Stage 1 (Context Diagram) on a project — typically right after `hp-init` has scaffolded the directory + empty dictionary. Also valid for **re-doing** Stage 1 on a project that already has terminators if the boundary needs to shift (system scope widening, new external actor identified, terminator merge/split).

Specifically:

- Project scaffolded but `00-context/proposal.md` is the unfilled stub from `hp-init`, OR
- An existing locked Stage 1 needs revisiting because the boundary changed.

This is the **Propose + Surface Ambiguity** AI move applied to Stage 1.

## What it does

Drafts (or redrafts) `00-context/proposal.md` as a form-based batch-review document — same structure as the lived examples in [`examples/solar/00-context/`](../../examples/solar/00-context/) (ad-hoc) and [`examples/fishing-rig/00-context/proposal.md`](../../examples/fishing-rig/00-context/proposal.md) (form-based from the start).

Standard decision set (7 + 1 modernization, may vary slightly by project shape):

| # | Decision | What it pins down |
|---|---|---|
| 1 | System name | Final label for `sys_root` |
| 2 | System scope | Narrow / medium / wide — what's *inside* the boundary |
| 3 | Terminator inventory | Each external actor that exchanges a flow with the system |
| 4 | Optional terminators | Cloud / monitoring / future-load — modeled as dashed/optional? |
| 5 | Power modeling | Physical edge (no data flow) vs data-modeled |
| 6 | Flow naming convention | `F1-Fn` numbered? prefixed? domain words? |
| 7 | Anything else | Free-form escape hatch for project-specific surprises |
| 8 | Bounded contexts at this stage *(modernization #5)* | Multi-team / multi-language? Declare `bounded_contexts:` now (Stage 1 is cheapest) or defer. If declared, every terminator + sys_root gains a `context:` tag and Stage 2 will inherit. |

Each decision lists alternatives as `- [ ]` checkboxes, with Claude's recommended default **pre-checked** (`- [x]`) and provenance noted ("extracted from your description"; "matches solar's pattern"; "AI inference"). The user toggles overrides via Markdown Preview Enhanced, saves once, pings back.

On lock-in, the skill writes the `## ✅ Status: Locked YYYY-MM-DD` header, populates `dictionary.yaml` with the resulting terminators + boundary flows + physical edges, and hands off to [`hp-confirm-naming`](hp-confirm-naming.md) for the naming review pass.

## Behavior

When invoked, conversationally:

1. **Read the current state.** Load `dictionary.yaml`; inspect existing entities. Read the project's `README.md` and any user-provided description to ground the proposal.
2. **Identify candidate terminators.** Apply Propose with provenance: extract named external actors from the description ("the angler triggers reels" → `Angler` terminator), and surface AI-inferred ones ("you mentioned power — likely a `Power Source` physical edge"). Flag inferred items explicitly so the user can reject them.
3. **Draft `proposal.md`** in the standard form structure:
   - Stage header + status placeholder
   - Form-based-review instructions ("open in MPE → toggle `[ ]` → `[x]` → save once → ping")
   - Proposed Context Diagram (inline Mermaid block) — uses working names; gets re-rendered after dictionary lock
   - 7 numbered decisions with alternatives + pre-checked recommendation + provenance
4. **Tell the user**: "Open `00-context/proposal.md` in MPE, override any defaults, save, ping me when done."
5. **On user ping**: parse the saved file, write the `Status: Locked` block + resolution table, populate `dictionary.yaml`, then invoke [`hp-confirm-naming`](hp-confirm-naming.md) for the naming pass on the new entities. Finally invoke [`hp-render`](hp-render.md) to regenerate the Context Diagram views.

## Discipline

- **Defaults must be pre-checked and provenance-labeled.** A bare list of alternatives forces re-litigation of every choice; pre-checking the recommendation is how the form-based pattern delivers leverage. Provenance ("extracted from your paragraph 2"; "AI inference") is how the user knows what to trust.
- **The proposal is the locked record, not chat.** Once the user saves the file with their overrides and pings back, the proposal becomes the canonical Stage 1 artifact. Resist the urge to negotiate decisions in chat afterward — that loses the audit trail.
- **Don't pre-populate the dictionary with proposed entities.** The dictionary stays at `sys_root` only until the proposal locks. This prevents drift if the user rejects a proposed terminator.
- **Working names are throwaway.** Names assigned in this proposal are explicitly working — the immediately-following `hp-confirm-naming` pass is where they get reviewed against `accept / rename / alias` semantics. Don't get attached.
- **Diagram before prose.** The proposal embeds a rendered Mermaid block of the proposed Context Diagram up top, then the decisions. Visual first, text second — matches the *Recap with diagrams, not text walls* tactic.
- **Bounded contexts are cheapest to declare early** *(modernization #5)*. If the project is obviously multi-team or multi-language, declare contexts at Stage 1 — every subsequent stage inherits the discipline. If unsure, defer (the synthetic `default` context applies); contexts can be retrofitted later via `hp-propose-bounded-contexts`. Discipline rule: once bounded_contexts is declared, every new entity *must* carry a `context:` tag (Commit 5's validator enforces this).

## Lived examples

- [`examples/fishing-rig/00-context/proposal.md`](../../examples/fishing-rig/00-context/proposal.md) — Stage 1 form-based proposal locked 2026-05-22; all 7 defaults accepted; 5 terminators + 2 physical edges materialized into the dictionary.
- [`examples/solar/00-context/`](../../examples/solar/00-context/) — Stage 1 done **ad-hoc** before the form-based pattern existed; preserved as the pre-pattern counter-example. The Status block sits in `naming-review.md` instead of `proposal.md`.

## Implementation status

**Skill description: ✅ drafted.** Code wiring planned — would extend `toolkit/scripts/hp_init.py`'s pre-population step or live as a sibling `hp_toolkit/proposals/context.py` module. Until wired, invoke conversationally: the user pastes their description, Claude drafts `proposal.md` following the template + decision list above.

The decision set is intentionally not hard-coded — projects with unusual shape (e.g., no power source; >2 cloud-side terminators) may add or omit decisions. The 7 above are the **canonical baseline** drawn from solar + fishing-rig.

## See also

- Tactic source: [`PLAN.md` > Methodology Tactics > A > Propose + Surface Ambiguity](../../PLAN.md), [`PLAN.md` > Methodology Tactics > B > Form-based batch review](../../PLAN.md)
- Lived counterpart: [`hp-init`](hp-init.md) scaffolds the project; this skill fills its proposal.
- Sequel: [`hp-confirm-naming`](hp-confirm-naming.md) runs immediately after lock to review the working names.
- Renderer: [`hp-render`](hp-render.md) regenerates the Context Diagram once the dictionary is populated.
- Stage 2: [`hp-propose-decomp`](hp-propose-decomp.md) *(planned)* follows once Stage 1 is locked.
- HP reference: [`HP_QUICK_REF.md` > Context Diagram](../reference/HP_QUICK_REF.md)
