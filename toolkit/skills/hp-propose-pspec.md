---
name: hp-propose-pspec
description: Stage 4 — draft a form-based PSPEC (Process Specification) proposal for one leaf process bubble. Reads the locked DFD, identifies inputs/outputs from dictionary flows, proposes a TRANSFORMATION body in one of five book-canonical styles, writes a reviewable proposal.md with Claude's recommended defaults pre-checked.
---

# hp-propose-pspec

## When to use

Specifying the functional contract of a leaf process bubble — one that does *not* decompose further into a sub-DFD AND does *not* have a CSPEC (i.e., `needs_cspec: false`). Every functional primitive needs exactly one PSPEC (2000 §4.3.3.9).

Specifically:

- The bubble's parent DFD is locked (`proposal.md` has Status: Locked; the process exists in `dictionary.yaml` with `needs_cspec: false`).
- The bubble's inputs and outputs are settled (boundary flows refined, internal flows declared).
- No PSPEC for this process exists yet, OR an existing PSPEC needs revision.

This is the **Propose + Surface Ambiguity** AI move applied to a leaf-level functional contract.

## What it does

Drafts `<level-dir>/pspecs/<process-id-short>-proposal.md` as a form-based batch-review document. Once locked, the resulting PSPEC entry lands in `dictionary.yaml` under the `pspecs:` section and the rendered markdown sidecar at `<level-dir>/pspecs/<process-id-short>.md` regenerates from it.

Standard decision set (5–7 decisions; project-shape varies):

| # | Decision | What it pins down |
|---|---|---|
| 1 | Transformation style | `textual` / `equation` / `table` / `diagram` / `mixed` — 1988 §13.2 |
| 2 | Granularity | Short-and-multiple vs long-and-single (1988 §13.1: "short enough to be unambiguous, long enough to be nontrivial") |
| 3 | Computational constraints — frequency | None / sampling rate / activation cadence — optional, 2000 §4.3.3.9 |
| 4 | Computational constraints — accuracy | None / numeric tolerance — optional |
| 5 | Computational constraints — timing | None / max latency — optional |
| 6 | Transient outputs | Any output that should use the `issue` keyword (1988 §13.3); typically none |
| 7 | Anything else | Free-form escape hatch |

Each decision lists alternatives with Claude's recommended default **pre-checked** and provenance noted ("matches sibling PSPECs in this project"; "inferred from the flow's `medium` field"; "no constraints needed for this bubble"). The user toggles overrides in MPE, saves once, pings back.

On lock, the skill writes the `## ✅ Status: Locked YYYY-MM-DD` header, populates `dictionary.yaml` with a new `pspec_<short-id>:` entry, then runs [`hp-validate`](hp-validate.md) (catches balancing violations + code-like body) and [`hp-render`](hp-render.md) (emits the markdown sidecar).

## Behavior

When invoked, conversationally:

1. **Identify the target process.** Default: the (typically single) leaf process that hp-status reports as missing a PSPEC. Multiple candidates → ask the user; pick the smallest surface first.
2. **Read the inputs and outputs from the dictionary.** Query `dictionary.flows` for `target == process_id` (post-refinement) → inputs; `source == process_id` → outputs. These become the canonical INPUTS / OUTPUTS section per 2000 Fig 4.46 — the PSPEC author does *not* re-declare them.
3. **Draft a TRANSFORMATION body.** Pick a style (default to `textual` — "the most common form for PSPECs" per 2000 §4.3.3.9). For textual, write in structured English: short itemized phrases, capitalized flow names matching dictionary labels (1988 §13.4). For equation/table/diagram, follow 1988 §13.2 examples (Figs 13.1–13.4) and 2000 Fig 4.47.
4. **Identify computational constraints**, if any (2000 §4.3.3.9, A.2.12). Sampling rate, accuracy bounds, timing constraints. Most PSPECs leave these blank; only fill where the underlying flow's `medium` or the bubble's role implies a specific constraint.
5. **Write `<process-id-short>-proposal.md`** with: stage header → form-based-review instructions → INPUTS/OUTPUTS preview (derived from dictionary) → proposed TRANSFORMATION body → optional computational constraints → optional comments → numbered decisions with alternatives + pre-checked recommendation + provenance.
6. **Tell the user**: "Open `<level-dir>/pspecs/<id>-proposal.md` in MPE, override any defaults, save, ping me when done."
7. **On user ping**: parse decisions, write Status: Locked block + resolution table, populate `dictionary.yaml`'s `pspecs:` section with a new entry, run [`hp-validate`](hp-validate.md), then [`hp-render`](hp-render.md) to produce the sidecar markdown.

## Discipline

These come straight from the books. Each cites its source.

- **PSPECs specify what, not how** (1988 §13.1; 2000 §4.3.3.9 "leave the details of how to the architecture model"). If the body describes an algorithm at a level of detail that constrains implementation, push back.
- **No code, no pseudocode** (1988 §13.2: "should not, repeat not, contain code, or even pseudocode"). Equations: yes. Decision tables: yes. `for (i := 0; ...)`: no. The validator's heuristic check flags this as a warning.
- **Each PSPEC short enough to be unambiguous, long enough to be nontrivial** (1988 §13.1). Multi-page PSPECs are usually two PSPECs that haven't been split yet.
- **Capitalize flow names in textual bodies** (1988 §13.4). Names must match `dictionary.yaml` exactly. This is the balancing check — every flow named in the body appears as an input or output, and vice versa.
- **Time is universally available** (1988 §13.3). Never model time as an input flow.
- **Large data blocks go in an appendix** (1988 §13.2; 2000 §4.3.3.9). If the transformation depends on a 100-row coefficient table, the PSPEC references the appendix rather than embedding it.
- **No Process Activation Tables in PSPECs** (1988 §13.2). PATs are CSPEC-only. The validator catches this as an error.
- **Decision tables and state transition matrices are fine** in PSPECs if their function is local, not global (1988 §13.2). Mixed-style PSPECs (textual + decision table) are valid.
- **Default outputs are time-continuous**; transient outputs use the keyword `issue` in the body (1988 §13.3). When you write `issue X = ...`, you're declaring X is momentary.

## Lived examples

- [`examples/fishing-rig/01-level1/pspecs/acquire-tension.md`](../../examples/fishing-rig/01-level1/pspecs/acquire-tension.md) *(rendered)* + the source entry `pspec_acquire_tension` in [`dictionary.yaml`](../../examples/fishing-rig/dictionary.yaml). First-locked PSPEC; textual style; computational constraints on frequency/accuracy/timing; comments field used to flag a deferred sizing question.

(More lived examples will land as the remaining 8 PSPECs across fishing-rig + solar get locked.)

## Implementation status

**Skill description: ✅ drafted.** Backing code: ✅ schema (`PSpec`, `Transformation`, `ComputationalConstraints`, `PSpecStyle`) + loader + validator rules + markdown renderer + Cytoscape side-panel link all live as of 2026-05-22. See [`toolkit/PSPEC_DESIGN.md`](../PSPEC_DESIGN.md) for the design rationale (book-cited).

What this skill adds is the **conversational front of the funnel**: identifying the target bubble, drafting the TRANSFORMATION body in a book-faithful style, surfacing the constraint decisions, and managing the form-based lock-and-populate loop.

## See also

- Design doc: [`toolkit/PSPEC_DESIGN.md`](../PSPEC_DESIGN.md)
- Predecessor: [`hp-propose-decomp`](hp-propose-decomp.md) locks the DFD that defines which bubbles need PSPECs.
- Sibling at Stage 3: [`hp-propose-cspec`](hp-propose-cspec.md) — same form-based pattern for state-rich bubbles.
- Followup: [`hp-validate`](hp-validate.md) checks balancing + code-pattern heuristics; [`hp-render`](hp-render.md) emits the sidecar markdown + DFD side-panel link.
- HP reference: [`HP_QUICK_REF.md` > PSPEC](../reference/HP_QUICK_REF.md)
- Source books: Hatley & Pirbhai (1988) ch. 13 — *Preparing Process Specifications*. Hatley, Hruschka & Pirbhai (2000) §4.3.3.9 + appendix A.2.12 — *Process Specification*.
