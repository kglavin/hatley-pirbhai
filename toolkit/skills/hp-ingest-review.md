---
name: hp-ingest-review
description: Final stage of brownfield ingest — read the merge-report.txt produced by the deterministic IR merger, repair flagged issues, run the toolkit's existing hp-validate on the projected dictionary, repair any validator errors, then approve emission to `dictionary.yaml`. The only agent permitted to mutate the IR after Stage 5.
---

# hp-ingest-review

## When to use

After all 5 ingest stages have run + the deterministic merger has assembled the IR + identified anything it couldn't normalize. The reviewer is the last guard before `dictionary.yaml` is written.

Two trigger conditions:

1. **Initial ingest:** runs once after Stage 5 + merge.
2. **Incremental re-ingest:** runs after the merger has reconciled new findings against existing `dictionary.yaml`. The reviewer's job here is to surface conflicts via `ingest-conflicts.md` for manual review before the YAML is overwritten.

## What it does

Given:
- `intermediate/hp-graph.json` (the merged IR from `merge_graph.py`)
- `intermediate/merge-report.txt` (stderr-style report of normalizations, duplicates, dropped edges, unrecoverable issues)
- (Incremental only) the existing `dictionary.yaml` for reconciliation

Produce:

1. **Repair unrecoverable issues** logged in the merge report. These are typically nodes/edges the LLM agents emitted in a shape the merger's alias tables couldn't normalize (e.g., a brand-new IRNodeKind value the LLM invented). Fix them by editing `hp-graph.json` directly: either map to a canonical kind or delete with rationale.
2. **Project dictionary.yaml + run hp-validate** against the projected output. The emitter (`emit_dictionary.py`) translates IR → YAML; `hp-validate` then runs the toolkit's existing 60+ validator rules. Any error → repair the IR until validate is clean.
3. **(Incremental only) Conflict surface.** For each IR node whose `id` matches an existing dictionary entry but whose key fields (kind, label, parent, needs_cspec, allocated_*) differ, write a row to `ingest-conflicts.md`. Default behavior is *no auto-overwrite* — the user reviews + approves each conflict.
4. **Compose `ingest-report.md`** for the user. Sections:
   - Summary stats (nodes, edges, validation status, token usage estimate).
   - Confidence histogram (how many nodes at each confidence band — surfaces what to spot-check).
   - Filter audit (what files got dropped + why — from scan.json `is_significant: false`).
   - Orphans (Stage 1–4 entities that aren't allocated to any Stage 5 module — should be zero after architect).
   - Open questions (lowest-confidence entities, conflicts requiring user attention).
5. **Approve emission.** When all the above pass, the orchestrator runs `emit_dictionary.py` → `dictionary.yaml`.

## Behavior

**Progress log:** at entry, append a START line; after composing `ingest-report.md` + approving emission, append a DONE line. Per `hp-ingest.md` orchestrator convention:
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START    stage=review agent=hp-ingest-review" >> <intermediate-dir>/progress.log`
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DONE     stage=review agent=hp-ingest-review repairs=$R conflicts=$C validate_errors=$E" >> <intermediate-dir>/progress.log`

When invoked, conversationally:

1. **Read merge-report.txt.** If non-empty:
   - **Normalizations / duplicates / dropped edges** — already auto-resolved by the merger. Surface them in `ingest-report.md` for transparency but no action needed.
   - **Unrecoverable** — required to repair. Walk each one, edit `hp-graph.json` in place to fix. Common patterns: invented enum value → map to canonical; missing required field → fill with a sensible default + `confidence: 0.4` + `provenance.rationale: "repaired by hp-ingest-review"`.
2. **Run the projection.** Invoke `emit_dictionary.py` (via Bash) to produce a candidate `dictionary.yaml` at a temp path.
3. **Run hp-validate** against the candidate YAML. The validator emits structured errors.
4. **Repair each validator error** in `hp-graph.json` and re-project. Common errors:
   - "Process X not allocated to any architecture module" → add an `allocates_to` edge.
   - "Boundary flow F1 has no refined_target at level 1" → set the refinement on the flow edge.
   - "CSPEC X has no initial state" → identify the most-likely-initial state node and set `is_initial: true`.
   - "Entity X references non-existent parent" → either create the parent or fix the reference.

5. **Repair recoverable warnings from `merge-report.txt`** (the new `warnings` section). These don't fail validation but indicate Stage-1/2/5 agent gaps. Common patterns:
   - **Boundary-flow refinement missing on N edges** (H.1.2 warning): Stage-2 agent skipped refining boundary flows. Cross-reference `intermediate/processes.json` against `intermediate/boundary.json`: for each boundary flow `term_X → sys_root` (inbound) or `sys_root → term_X` (outbound), identify the Stage-2 process whose `implemented_by[]` cluster contains the endpoint handler. Edit `hp-graph.json` to set `refined_target=<proc_id>` (inbound) or `refined_source=<proc_id>` (outbound) on that edge. Re-emit and re-validate. Without this repair, the level-1 DFD renders with boundary arrows dangling at `sys_root`.
   - **Architecture flow not in any interconnect's carries:** Stage-5 architect drew the flow but didn't add it to a `carries:` list. Cross-reference flow endpoints with interconnect endpoint lists; add to the matching interconnect.
   - **Low-confidence module / process / terminator (< 0.6):** not a repair — surface in `ingest-report.md`'s "spot-check these first" section. Low-confidence is a signal, not a bug (G.4).
6. **Compose ingest-report.md** (see above).
7. **For incremental:** before final emission, check every existing-dictionary entity. If hp-graph.json has a contradictory value (different kind, label, parent, allocation), write the diff to `ingest-conflicts.md` and **halt** (default is conservative — don't auto-overwrite). User reviews + re-runs with `--auto-accept` to commit.
8. **Approve emission.** Tell the orchestrator the pipeline can write the final YAML.

## Discipline

- **The reviewer is the only agent that mutates the IR after merge.** Stage-1–5 agents are write-only; merger is auto-normalize-only; reviewer is the targeted-repair agent.
- **Every repair leaves a trail.** When you edit a node, update its `provenance.rationale` to record the repair (`"repaired by hp-ingest-review: invented kind 'external_system' → canonical 'terminator'"`). The IR is the audit log.
- **Modernization fields are off-limits.** On incremental, `adrs:` / `budgets:` / `tpms:` / `service_level_objectives:` / `bounded_contexts:` / PSPEC `verification:` / PSPEC `observability:` / interconnect `stride_mitigations:` / catalog refs — all preserved verbatim. The reviewer **never** touches them (see Q4 lock + the "Reconciliation rules" in INGEST_DESIGN.md).
- **Halt on conflict by default.** `ingest-conflicts.md` exists for the user to review; the YAML doesn't get overwritten until they explicitly accept. `--auto-accept` is opt-in.
- **The validator's word is final.** `hp-validate` clean = ready to emit. If you can't get validation clean after a reasonable number of repair iterations (say, 5), halt and write the unrecovered errors to `ingest-report.md` for the user to resolve manually. Don't paper over validator errors by editing the validator.
- **Low confidence is a signal, not a bug (G.4).** When a node carries `confidence < 0.6`, that's the architect-spot-check signal working as designed — the agent flagged its own uncertainty so the architect knows what to look at first. Don't "repair" low-confidence entities just because they're low-confidence; only repair when there's a concrete validator error or a missing-required-field gap. Instead, group low-confidence entities into a dedicated **"Spot-check first"** section in `ingest-report.md` (sorted ascending by confidence) — give the architect a focused queue of what to review, not a flat list. This converts confidence from a noisy field into an actionable triage tool.

## Implementation status

**Skill description: ✅ drafted.** Backing scripts: ✅ `hp_toolkit/ingest/merge_graph.py` (Commit 2) + `emit_dictionary.py` (Commit 3) + existing `hp-validate` CLI. Orchestrator dispatch via `/hp-ingest` skill (Commit 3).

## See also

- Design doc: [`toolkit/INGEST_DESIGN.md`](../INGEST_DESIGN.md) — full pipeline, especially the "Reconciliation rules" section in *Incremental updates*.
- Predecessors: all the Stage 1–5 agents.
- Companion (existing): [`hp-validate`](hp-validate.md) — the validator the reviewer runs.
- Schema: [`hp_toolkit/ingest/schema.py`](../hp_toolkit/ingest/schema.py).
