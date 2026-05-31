---
name: hp-frame
description: Stage-0 greenfield concept framing. Conversational interview that stress-tests a product concept against systems-thinking + capabilities-based discipline (Rebovich/Anderson/Webb, *Enterprise Systems Engineering*, 2011) and emits `concept.md` — the seed `hp-init` reads to bootstrap an HP project. Use when starting from an idea, not from existing code.
---

# hp-frame

## When to use

**Before `hp-init`, when the project is greenfield.** The user has a concept in mind but hasn't decided what the thing *is* yet — who it serves, what outcomes count as working, where the boundary sits, what's already out there.

The brownfield counterpart is [`hp-ingest`](hp-ingest.md): it derives a concept *implicit in code*. `hp-frame` does the inverse — derives a concept *from a conversation* and emits a structured framing that hp-init can seed an HP project from.

Triggering conditions:

- The user has a one-sentence pitch but no `dictionary.yaml`, no codebase, no boundary diagram.
- The user uses fuzzy language ("monitor my solar," "track inventory," "help my team coordinate") that needs sharpening before Stage 1 terminator selection makes sense.
- The user is choosing between alternatives that should stay open through framing rather than be closed by premature structure.

This skill produces synthesis — the "why does this exist and what whole does it serve" framing — that HP's analysis stages (1–5) then formalize.

## What it does

Conducts a relentless, branch-by-branch interview about a greenfield concept. Walks a tree of nine framing branches grounded in *Enterprise Systems Engineering* (Rebovich 2011, Anderson & Webb 2011) — recasting their enterprise-scale prompts in product-native language for the "I want to build a thing" case.

Emits `concept.md` at the project root: YAML frontmatter capturing the structured framing (the contract hp-init reads) + prose body narrating the conversation that produced it. Captures rejected alternatives explicitly, separates *unknowns* from *open decisions*, and surfaces tensions reframed as complementary ("and") wholes where possible.

The artifact is **deliberately implementation-agnostic**. It is not a spec, not a backlog, not a feature list. Implementation is HP's job from Stage 1 onward.

## Behavior

When invoked, conversationally:

1. **Open with one sentence.** Ask the user to state the concept in one sentence. Don't accept three. ("I want to build a thing that…")
2. **Pick a starting branch.** Usually `synthesis` (the *containing whole*) or `outcomes` (what the user gets). Synthesis goes first if the pitch is vague about purpose; outcomes goes first if the pitch is clear on purpose but vague on what "working" means.
3. **Walk one branch at a time.** Ask one question. Wait. Recommend an answer with brief rationale. Let the user accept, modify, or push back. Capture to `concept.md` frontmatter inline as each field resolves.
4. **Follow threads, not a checklist.** When a user answer raises a new ambiguity, dig into that — don't push to the next branch yet. Branch order is opportunistic, not fixed.
5. **Offer 2–3 alternatives where there's real choice.** Don't volunteer a single recommendation when the choice is genuinely open. Trade-offs explicit, user picks. Rejected alternatives go into `alternatives_considered:` with reasons, not into the prose only.
6. **Stress-test with concrete scenarios.** When a relationship or boundary feels resolved, invent a specific scenario that probes the edge. "When she's away on vacation and the inverter throws an error code at 2 AM, what should happen?" Force precision.
7. **Distinguish *unknowns* from *open questions*.** Unknowns are things the user can't currently answer (data we don't have, behavior we haven't observed). Open questions are decisions deliberately deferred. Both stay in frontmatter; the consumer treats them differently.
8. **Close when the boundary triage is stable.** When the user can answer "what do you control / influence / not control?" with confidence and the outcomes are operationally precise (effect / standard / conditions), framing is done. Resist over-framing — Stage 1 will surface things this skill can't.
9. **Emit `concept.md`.** Frontmatter follows [`hp-frame-concept-format.md`](hp-frame-concept-format.md). Body is the conversation narrative — prose elaborations of each frontmatter field, in the order they came up.

After lock, `hp-init --from-concept concept.md` (or the eventual equivalent — the consumer is separate; see *Discipline* below) seeds the HP project's `dictionary.yaml` with terminator candidates from `boundary.influenced + boundary.environment` and Stage-1 flows from the `outcomes:` list.

## Discipline

**Interview style (from grill-with-docs, [Pocock 2024](https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md)):**

- **Challenge fuzzy language.** "Fast" → fast for whom, under what load, to what threshold? "Easy" → easy compared to what? "Secure" → secure against what threat model?
- **Distinguish outcomes from features.** A *feature* is what the system does. An *outcome* is what the user gets. "Sends an email" is a feature; "Knows within 5 minutes that production stopped" is an outcome. Push toward outcomes; CBEA's `effect / standard / conditions` triple is the discipline.
- **Recommend an answer at every step.** Don't ask open-ended questions without a leaning. The skill is an interviewer with opinions, not a survey form.
- **Capture inline, lazily.** Write to `concept.md` as fields resolve. Don't batch. Don't create the file before there's something to write.

**Stage-0-specific discipline (from *Enterprise Systems Engineering*):**

- **Synthesis before analysis** *(Rebovich Ch 2 §2.4)*. Always anchor to the *containing whole* the thing serves. "What stops working if this concept doesn't exist?" is the synthesis test.
- **Controlled / Influenced / Environment** *(Rebovich Ch 2 §2.2, Fig 2.4)*. The triage is the seed of HP's Stage 1 terminator set. Force the user to assign every named entity to one of the three zones.
- **Outcomes use CBEA structure** *(Anderson & Webb Ch 4 §4.2.2.1)*. Each outcome = `effect` (the change the user experiences) + `standard` (the proficiency required to call it "working") + `conditions` (the environmental variables under which it must hold). *Tasks* are deliberately excluded — that's HP's job from Stage 1.
- **Complementarity over compromise** *(Rebovich Ch 2 §2.4.1)*. When tensions emerge as "A vs. B," look for the "A *and* B" reframing. Capture both the original tension and the reframing — the reframing isn't a deletion, it's a creative move worth preserving.
- **Slack indicators, not slack guesses** *(Rebovich Ch 2 §2.4.2)*. Ask the user: "where might optimization hit a wall the system itself causes?" Concrete slack indicators (rate limits, vendor dependencies, regulatory ceilings) are worth capturing; speculative ones aren't.
- **Variation is recorded, not just discussed** *(Rebovich Ch 2 §2.5.4)*. Every rejected alternative goes into `alternatives_considered:` with an operative reason — not a vague one. "Rejected: complexity" is too vague. "Rejected: requires homeowner to maintain a Raspberry Pi" is operative.
- **Reference portfolio is mandatory** *(Anderson & Webb Ch 4 §4.3.2.5)*. The user always has comparables. Force the listing — what's the closest thing that already exists, and why is it inadequate? Greenfield concepts that can't name their reference portfolio are usually still vapor.
- **Unknowns separated from open questions** *(CBEA principle 5)*. Bound the uncertainties. *Unknowns* are things we don't currently know (need data, need observation, need to talk to someone). *Open questions* are decisions deferred. Same field would hide a real distinction; separate fields force honesty.

**Artifact discipline (from grill, with one Stage-0-specific addition):**

- **`concept.md` is implementation-agnostic.** Not a spec. Not a roadmap. Not a feature list. If the user starts talking implementation, redirect: "that's a Stage-1+ question; let's stay at the framing layer."
- **ADRs sparingly, when all three hold:** hard to reverse, surprising without context, result of a real trade-off. Stage-0 ADRs are unusual but legitimate — e.g., a deliberate choice to scope out an entire stakeholder class.
- **Stage-0 addition: don't converge prematurely.** Grill assumes convergence is the goal. Stage 0 has more legitimately-open ends — variation has value before commitment. If the user wants to keep something open, honor that and capture it in `open_questions:`.

## Branches walked

The interview walks these nine branches, in opportunistic order based on what's still ambiguous:

| Branch | What the LLM challenges on | Frontmatter fields populated |
|---|---|---|
| **Synthesis** | "What containing whole does this serve? What stops working if this doesn't exist?" | `purpose`, `serves` |
| **Outcomes** | "Who experiences what change? Under what conditions? How fast / accurate / cheap to be 'working'?" | `outcomes[]` (each as `effect / standard / conditions`) |
| **Stakeholders** | "Who has stake in those outcomes? What do they need, what do they contribute, what do they depend on?" | `stakeholders[]` (with `interest / contributes / depends_on`) |
| **Boundary** | "Of everything you've named, what do you *control*? *Influence*? Just *live with*?" | `boundary.controlled / influenced / environment` |
| **Reference portfolio** | "What's the closest thing that already exists? Why is it inadequate? Why is it relevant?" | `reference_portfolio[]` |
| **Complementarity** | "Where are 'A vs. B' tradeoffs that might be 'A *and* B' if reframed?" | `tensions[]` (each with `statement / reframed_as_and`) |
| **Slack** | "Where might effort hit a wall the system itself causes? Where might redesign beat optimization?" | `slack_indicators[]` |
| **Variation** | "What else did you consider? Why not? What's still in scope vs. ruled out?" | `alternatives_considered[]`, `phase`, `phase_rationale` |
| **Uncertainty** | "What don't you know yet that could change the shape? What decisions are you deliberately deferring?" | `unknowns[]`, `open_questions[]` |

## Lived examples

None yet — first run will likely target a solar-monitor or comparable single-system concept. Examples land here as they accumulate.

## Implementation status

**Skill description: ✅ drafted.** Backing artifacts:

- [`hp-frame-concept-format.md`](hp-frame-concept-format.md) — schema for the `concept.md` frontmatter.
- **Consumer:** TBD. Options: a `hp-init --from-concept concept.md` flag, a separate `hp-seed-from-concept` skill, or a small Python helper. Grill's pattern says keep the consumer separate from this producer — pick one when the first lived example exists.
- **Validator:** none yet. `concept.md` frontmatter is intentionally Pydantic-free for now; promote to a typed schema only if drift becomes painful.

## See also

- Interview-pattern source: [`/grill-with-docs` by Matt Pocock](https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md). Borrowed: AI-as-challenger style, walk-the-tree mechanics, inline doc updates, sparing ADRs, one-question-at-a-time discipline.
- Content source: Rebovich, G. Jr. & White, B. E. (eds.), *Enterprise Systems Engineering: Advances in the Theory and Practice* (CRC Press, 2011). Specifically Ch 2 (Systems Thinking for the Enterprise — Rebovich) §2.2, §2.4, §2.5.4, §2.6.1; Ch 4 (Capabilities-Based Engineering Analysis — Anderson & Webb) §4.2.2.1, §4.3.1, §4.3.2.5. Reference doc lives at [`reference-docs/`](../../reference-docs/).
- Downstream consumer: [`hp-init`](hp-init.md) — the eventual `--from-concept` flag (or equivalent) reads `concept.md` and seeds Stage 1.
- Format spec: [`hp-frame-concept-format.md`](hp-frame-concept-format.md)
