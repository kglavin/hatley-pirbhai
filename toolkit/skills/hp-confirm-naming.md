---
name: hp-confirm-naming
description: Generate a form-based naming review for HP entities at a given level. The user fills out checkboxes + custom names in MPE, saves once, and the skill applies the renames to dictionary.yaml plus regenerates dependent diagram artifacts.
---

# hp-confirm-naming

## When to use

After any AI move that introduces named entities — **before** those names propagate into permanent artifacts. Typical trigger points:

- After **Stage 1** (Context Diagram proposal) introduces the system bubble, terminators, and boundary flows.
- After **Stage 2** (level-N+1 decomposition proposal) introduces internal processes, data stores, internal flows.
- After **Stage 3** (CSPEC proposal) introduces states (and later events / actions).
- After **Stage 4** (PSPECs) introduces local data names.
- Any time the user signals "let's review names before going further."

If the user just accepted a proposal with `Status: Locked` and the names are still working names, run this next.

## What it does

Generates a `naming-review.md` file at the appropriate level directory using the **form-based batch review** pattern. The file is structured so a human can resolve many naming decisions in one editing pass and one save.

**Structure of the generated file:**

1. **Recap diagram** — embeds the relevant rendered SVG (level-N DFD / state diagram / etc.) so the user sees what they're naming. Don't replicate the model as a text table; show the picture.
2. **Bulk shortcuts** — common-cases that handle most names at once. Examples: naming style (PascalCase / snake_case / Title Case), accept-all-as-working-names, kind-specific groupings.
3. **Per-entity forms** — *only* for names where a non-obvious alternative deserves attention. Format:
   ```markdown
   ### `stable_id` — current label: **Working Name**

   - [ ] Keep current
   - [x] Claude's recommended alternative
   - [ ] Other candidate
   - [ ] Other candidate

   Custom name (overrides if non-empty):
   >

   Notes:
   >
   ```
4. **"Status: Resolved" block** is added at the top of the file once the user pings "done" — captures the final decisions as a traceable artifact in git history.

## Behavior

When invoked:

1. Determine the level / artifact being reviewed (from user's current path or explicit argument).
2. Load relevant entities from `dictionary.yaml` (or from in-flight context if not yet committed).
3. For each entity, determine:
   - Working name (current label)
   - Provenance (`extracted from user paste` / `AI inference` / `kept from prior stage` / `default from acronym`)
   - 2–4 alternative candidates with brief rationale
4. Group entities by category for bulk shortcuts; surface only the *non-obvious* candidates as per-entity forms.
5. Write `<level-dir>/naming-review.md` with the form.
6. Tell the user to open it in **Markdown Preview Enhanced**, click-toggle, save once, ping.

When the user pings "naming review done" (or similar signal):

1. Read the saved file. Parse the `[x]` selections and any `Custom:` / `Notes:` overrides.
2. Apply bulk shortcuts first, then per-entity decisions.
3. Update `dictionary.yaml` — only the `label:` field on relevant entities. Stable IDs do not change.
4. Add a "Status: Resolved" block at the top of `naming-review.md` recording the final decisions table.
5. Regenerate dependent artifacts that embed labels: Mermaid `.md` sources, HTML5 `.html` workspaces, D2 `.d2` sources, plus their rendered SVGs.
6. Report what changed (which labels were updated; which artifacts were re-rendered).

## Discipline

These rules come from lived experience on the dogfood project and are non-negotiable:

- **Don't bury chat shorthand into permanent artifacts.** Working names that include internal-conversation context (e.g., `"(b+d scope)"`) are flagged for rename, not silently accepted.
- **Provenance is always shown.** The user needs to know *why* each working name was suggested before deciding whether to keep, override, or rename.
- **Bulk shortcuts come before per-entity decisions.** Most names get accepted in bulk; per-entity scrutiny is reserved for names where a real alternative exists.
- **Diagram-first.** Always embed the rendered diagram at the top of the review file. The user reviews names against the visual, not against a text list.
- **Stable IDs never change after creation.** Renames update `label:` only. This is what makes "rename in one place, regenerate everywhere" possible.
- **The naming-review file is itself a traceable artifact.** Don't delete it after processing. The `Status: Resolved` block at the top + git history record the decisions and their rationale.

## See also

- Tactic source: [`PLAN.md` > Methodology Tactics > A > Confirm names early](../../PLAN.md)
- Tactic source: [`PLAN.md` > Methodology Tactics > B > Names are first-class artifacts; reify them in a dictionary](../../PLAN.md)
- AI Moves Catalog entry: [`PLAN.md` > AI Moves Catalog > Confirm Naming](../../PLAN.md)
- HP reference: [Requirements Dictionary](../reference/HP_QUICK_REF.md#requirements-dictionary)
- Lived examples in the dogfood:
  - `examples/solar/00-context/naming-review.md` (Status: Resolved)
  - `examples/solar/01-level1/naming-review.md` (Status: Resolved)
  - `examples/solar/01-level1/cspecs/compute-balance/naming-review.md` (Status: Resolved)
