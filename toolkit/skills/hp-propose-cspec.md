---
name: hp-propose-cspec
description: Stage 3 — draft a form-based CSPEC (Control Specification) proposal for one process bubble. Reads the locked parent DFD, proposes a hierarchical state machine (modes + sub-states + transitions + timing model), writes a reviewable proposal.md with Claude's recommended defaults pre-checked.
---

# hp-propose-cspec

## When to use

Specifying the control behavior of a state-rich process bubble — one that was flagged `needs_cspec: true` during its parent DFD decomposition.

Specifically:

- A bubble's parent DFD is locked (`proposal.md` has Status: Locked; the bubble exists in `dictionary.yaml` with `needs_cspec: true`).
- The bubble has clearly-named events coming in and actions going out, but its *internal state structure* is unsettled — multiple modes? hierarchical sub-states? hybrid timing?
- Without a CSPEC, the bubble's behavior would have to be re-derived from prose every time someone reads its level-N+1 inputs/outputs.

This is the **Propose + Surface Ambiguity** AI move applied to a hierarchical state machine.

## What it does

Drafts `<cspec-dir>/proposal.md` as a form-based batch-review document — same shape as [`examples/solar/01-level1/cspecs/compute-balance/proposal.md`](../../examples/solar/01-level1/cspecs/compute-balance/proposal.md) and [`examples/fishing-rig/01-level1/cspecs/bite-detector/proposal.md`](../../examples/fishing-rig/01-level1/cspecs/bite-detector/proposal.md).

Standard decision set (7–8 decisions; project-shape varies):

| # | Decision | What it pins down |
|---|---|---|
| 1 | Top-level mode structure | The major states (e.g., `Initializing / GridTie / Island / Fault`) |
| 2 | Sub-states within the dominant mode | Hierarchical decomposition of the most state-rich mode |
| 3 | Fault/error granularity | Single Fault state vs per-cause Fault sub-states |
| 4 | Timing model | Event-driven, periodic-tick, or hybrid (event + N Hz tick) |
| 5 | Override / manual handling | Separate mode vs in-state behavior modifier |
| 6 | Transition guards | Trust an external authority vs debounce locally — project-specific |
| 7 | Process-controls preview | What events fire, what actions emit (Mealy/Moore boundary) |
| 8 | Anything else | Free-form escape hatch |
| 9 | **Per-mode observability** *(modernization #1)* | Should mode transitions emit traces? Should each top-level mode emit a `time_in_mode_seconds` gauge? Default: emit a `<process>_mode_transitioned_total{from, to}` counter + a `<process>_mode` gauge. Detailed metrics per leaf process come from `hp-propose-pspec`'s observability section. |

Each decision lists alternatives with Claude's recommended default **pre-checked** and provenance noted ("matches solar's pattern"; "minimum modes consistent with parent flows"; "AI inference from your domain language"). The user toggles overrides in MPE, saves once, pings back.

On lock, the skill writes the `## ✅ Status: Locked YYYY-MM-DD` header, populates `dictionary.yaml` with `State` / `StateComposite` entities and `Transition` entries (with `parent_machine`, `parent_state` for nesting), then hands off to [`hp-confirm-naming`](hp-confirm-naming.md) for state-name review.

## Behavior

When invoked, conversationally:

1. **Identify the target process.** Default: the (typically single) process with `needs_cspec: true` not yet covered by an existing CSPEC. Multiple candidates → ask the user.
2. **Read the parent DFD.** Load the locked level-N+1 DFD; find the target bubble's incoming events and outgoing actions. Those become the CSPEC's input/output boundary.
3. **Draft a hierarchical state machine.** Hand-author Mermaid (`stateDiagram-v2`) inline in the proposal + render `proposal-states.{mmd,svg}`. Choose modes that *meaningfully partition* the bubble's behavior — usually 3–4 top-level modes plus sub-states inside the dominant one. Fewer is better.
4. **Pick the timing model.** Default is hybrid (event-driven + low-Hz tick) unless the bubble is purely reactive. Justify with a sentence pointing to a specific incoming flow.
5. **Write `proposal.md`** with: stage header → form-based-review instructions → context recap (level-N+1 DFD SVG embedded; highlight the target bubble) → proposed state machine (proposal-states.svg embedded) → top-level mode descriptions + sub-state list → "Events & actions preview" table → numbered decisions with alternatives + pre-checked recommendation + provenance.
6. **Tell the user**: "Open `<cspec-dir>/proposal.md` in MPE, override any defaults, save, ping me when done."
7. **On user ping**: parse decisions, write Status: Locked block + resolution table, populate dictionary with `State` / `StateComposite` entities (level: 2, `parent_state` for nesting, `is_initial: true` on the entry state) + `Transition` entries (`parent_machine` = target process id, `source` / `target` / `event` / `action` / `guard`), run [`hp-validate`](hp-validate.md), then [`hp-confirm-naming`](hp-confirm-naming.md) on the new state names, then [`hp-render`](hp-render.md) for `cspec.generated.{mmd,d2,html,svg}`.

## Discipline

- **Hierarchical, not flat.** A 12-state flat machine is unreadable; the same 12 states partitioned into 4 modes with 3 sub-states each is approachable. If the proposal looks flat, push for a top-level partition first. Use `StateComposite` entities with `parent_state` to nest.
- **Single `is_initial: true` per machine.** Exactly one initial state across the whole CSPEC (typically an `Initializing` / `Idle` state). The `hp-validate` hierarchy check catches violations; surface this at proposal time.
- **Transitions name their event AND action.** Empty-action transitions are a smell — usually the action exists and is being skipped in the proposal. Force the question: "what changes on the wire when this transition fires?"
- **Guards reference external authorities by name.** "Trust Victron's mode" / "Wait for sensor settle" — name the authority. Don't write generic `when ready` guards.
- **Don't smuggle behavior into actions.** Actions emit a flow or set a value; they don't run multi-step procedures. If an "action" is doing real work, it's a sub-state.
- **Working names are still throwaway.** As at Stages 1 and 2, names get reviewed in the follow-up `hp-confirm-naming` pass. State names especially benefit — they're the most-referenced identifiers in the project.
- **State machines must be observable** *(modernization #1)*. The CSPEC's state is *the* most valuable runtime signal — without observability on transitions and time-in-mode, you can't tell whether the state machine is doing what the spec says. Default observability is `mode_transitioned_total` counter + `mode` gauge — opting out should be deliberate, not accidental.

## Lived examples

- [`examples/solar/01-level1/cspecs/compute-balance/proposal.md`](../../examples/solar/01-level1/cspecs/compute-balance/proposal.md) — Energy Manager CSPEC. 8 decisions; 4 top-level modes + 9 sub-states; hybrid timing (event + 1 Hz tick); 16 transitions. First CSPEC done with the form-based pattern at Stage 3.
- [`examples/fishing-rig/01-level1/cspecs/bite-detector/proposal.md`](../../examples/fishing-rig/01-level1/cspecs/bite-detector/proposal.md) — Bite Detector CSPEC. Smaller machine (9 states; 18 transitions) on a fresh project; confirmed the pattern transfers.

## Implementation status

**Skill description: ✅ drafted.** Code wiring planned — would live as `hp_toolkit/proposals/cspec.py`. The proposal-specific state diagram (`proposal-states.svg`) is hand-authored at proposal time; the dictionary's `State` / `StateComposite` / `Transition` entries are populated *after* the proposal locks.

The `Transition` schema is already live ([model.py](../hp_toolkit/model.py)); state rendering across Mermaid / D2 / Cytoscape is live ([render/](../hp_toolkit/render/)). What this skill adds is the **front-of-the-funnel design pass** that determines what gets written into the dictionary.

## See also

- Tactic source: [`PLAN.md` > Methodology Tactics > A > Propose + Surface Ambiguity](../../PLAN.md), [`PLAN.md` > Methodology Tactics > B > Form-based batch review](../../PLAN.md)
- Predecessor: [`hp-propose-decomp`](hp-propose-decomp.md) locks the parent DFD and flags the state-rich bubble.
- Sequel: [`hp-confirm-naming`](hp-confirm-naming.md) reviews state names; [`hp-validate`](hp-validate.md) checks `is_initial` uniqueness + transition reference integrity; [`hp-render`](hp-render.md) produces the three CSPEC views.
- Stage 4: `hp-propose-pspec` *(planned)* follows for each non-state-rich leaf bubble.
- HP reference: [`HP_QUICK_REF.md` > CSPEC, State, Transition](../reference/HP_QUICK_REF.md)
