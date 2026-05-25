---
name: hp-ingest-processes
description: Stage 2 of brownfield ingest — given the scanner's process-candidate clusters (significant non-boundary files grouped by directory), name each cluster as a Stage-2 internal process, set `needs_cspec` on state-rich ones, identify data stores, and draw internal flows between processes + boundary terminators. Emits IR nodes for processes + data stores + edges for internal flows.
---

# hp-ingest-processes

## When to use

Stage 2 of the `/hp-ingest` orchestration. Runs after `hp-ingest-boundary`. Consumes `intermediate/scan.json` + `intermediate/boundary.json` + `intermediate/process-candidates.json`. Emits `intermediate/processes.json` with IR-shaped process + data-store nodes + internal-flow edges.

The LLM's value-add: deciding **which clusters deserve to be Stage-2 bubbles** (some are trivial, some collapse together), naming them in HP convention, and drawing the flow graph between them.

## What it does

Given the candidate clusters (directory groupings with role-hint mix + size):

1. **Promote / collapse / drop clusters.** Some clusters are clearly one process per cluster (`src/orders/` → `proc_order_management`). Some are too granular (`src/orders/types/` + `src/orders/validation/` are one process). Some are infrastructure noise that doesn't deserve a bubble. Decide which clusters become Stage-2 processes.
2. **Name each process** in HP convention: `proc_<short>` id, label is 1–3 words (verb-noun phrase like "Validate Order"), short description.
3. **Set `needs_cspec: true`** on processes whose cluster contains `state-machine`-classified files. The state-machine detector (`state_machine_detector.py`) already found enum + transitions in those files — the cluster owns a CSPEC.
4. **Identify data stores.** Clusters classified `data-store` become `data_store` nodes (not `process` nodes). HP convention: barrel shape; only stores data, doesn't transform.
5. **Draw internal flows.** For each cluster, look at its `imports_in` / `imports_out` (from the scanner's import map). An import edge from process A's cluster → process B's cluster suggests a flow B → A (B provides data to A). Be careful with bidirectional or request/response patterns.
6. **Refine boundary flows.** Each Stage-1 boundary flow has `source=term_X, target=sys_root` (or vice versa). At Stage 2, set `refined_source` / `refined_target` to the actual internal process that handles the boundary flow. The boundary flow's `source` / `target` stay pointing at the terminator + `sys_root` — only the refined endpoints get added.
7. **Set provenance + confidence** on every node/edge.

Output JSON shape:

```json
{
  "nodes": [
    { "id": "proc_order_management", "kind": "process", "label": "Order Management",
      "stage": 2, "confidence": 0.82, "needs_cspec": false,
      "implemented_by": ["src/orders/validate.rs", "src/orders/rules.rs", "src/orders/types.rs"],
      "summary": "Applies business rules to inbound order events.",
      "description": "Centralizes order-validation logic so any inbound order — HTTP API, message bus, batch import — passes through the same rule pipeline. Owns the live RULE_TABLE; emits VALIDATED_ORDER on success, VALIDATION_FAILURE with rule-violation detail otherwise. Cross-references the customer + inventory stores to bind the order to current pricing before validation runs.",
      "provenance": { "agent": "hp-ingest-processes",
                      "rationale": "Directory cluster `src/orders/` with 3 pure-logic files, one inbound import path from api/handlers.rs. Module docstring describes rule-table-driven validation." } },
    { "id": "store_orders_db", "kind": "data_store", "label": "Orders DB",
      "stage": 2, "confidence": 0.9,
      "implemented_by": ["src/db/orders_repo.rs"],
      "summary": "Persistent storage for orders + line items.",
      "description": "Authoritative store for order records across their lifecycle (placed → validated → fulfilled → completed). Schema versioned via Diesel migrations under db/migrations/." },
    ...
  ],
  "edges": [
    { "source": "proc_serve_api", "target": "proc_order_management",
      "kind": "data_flow", "label": "incoming order event",
      "stage": 2, "confidence": 0.85,
      "provenance": { "agent": "hp-ingest-processes",
                      "rationale": "Import path: src/api/handlers.rs → src/orders/validate.rs" } }
  ]
}
```

## Behavior

**Progress log:** at entry, append a START line; after writing `processes.json`, append a DONE line with summary stats. Per `hp-ingest.md` orchestrator convention:
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START    stage=2 agent=hp-ingest-processes" >> <intermediate-dir>/progress.log`
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DONE     stage=2 agent=hp-ingest-processes processes=$N stores=$M flows=$F needs_cspec=$C" >> <intermediate-dir>/progress.log`

When invoked, conversationally:

1. **Read the project glossary (H.4.c).** Load `intermediate/glossary.curated.json` (if present). When naming processes + data stores + internal flows, prefer terms from this glossary over generic English. The glossary categories `process`, `event`, and `artifact` are the most relevant here — they map directly to HP process names, flow labels, and data store names.
2. **Read pre-stage file drops (architect guidance + external evidence).**
   - **Hints:** check `intermediate/hints/processes.md`. If present, treat its contents as binding architect guidance — common cases are "cluster at directory depth N" / "collapse these clusters" / "skip these as infrastructure-only". Append a `HINT_LOADED` line: `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) HINT_LOADED stage=2 agent=hp-ingest-processes path=intermediate/hints/processes.md" >> <intermediate-dir>/progress.log`.
   - **External context:** read every file under `external-context/qa-test-plans/` (acceptance criteria — process-level evidence) and `external-context/adrs/` (architecture decisions about process boundaries). Use them to validate process names + flag possible processes the import-graph alone wouldn't surface. Record source paths in `provenance.external_context_used` on any IR node that drew on them.
3. **Read inputs.** `scan.json`, `boundary.json`, `process-candidates.json`. Skim the file lists in each cluster to understand what's inside (the role-hint mix gives a strong starting point). Also load — when present:
   - `intermediate/testbeds.json` (H.7) — scenario walk-throughs describe what processes do step-by-step. Use them to validate process boundaries: if a single scenario walks through what your candidates would split into 4 processes, that's a sign the candidate clustering is too granular. Conversely, if a scenario references operations that span multiple clusters, the cluster boundaries may be too tight.
4. **Cluster-by-cluster decision:** for each candidate, decide promote / merge with sibling / drop.
5. **Look at the import edges between clusters** to inform the flow graph. If cluster A's files frequently import from cluster B, A consumes data from B → draw a flow B → A.
6. **Cross-reference with boundary terminators.** Each terminator has a boundary flow; identify which Stage-2 process handles it. Add the refinement (`refined_target` for inbound flows, `refined_source` for outbound).
7. **Cap process count.** Aim for 5–10 internal processes at Stage 2 for a cloudctlplane-scale project. More is fine but means decomposition is happening at too low a level. Use process subdirectories to surface fewer top-level processes.
8. **Skip clusters that are infrastructure-only** (e.g., a `src/utils/` cluster with only helpers). Note in a `notes` field for architect audit.
9. **Set confidence + provenance** on every emitted node/edge.
10. **Write `intermediate/processes.json`.**

### Required checklist before emit (per cloudctlplane H.1)

Before writing `intermediate/processes.json`, verify every item:

- [ ] **Every Stage-1 boundary flow in `boundary.json` has `refined_source` or `refined_target` set on it.** Walk every entry; for each, identify the Stage-2 process that handles it (inbound boundary → `refined_target=<proc_id>`; outbound → `refined_source=<proc_id>`). Without this, the level-1 DFD renders with boundary arrows dangling at `sys_root` (which isn't a node in the level-1 view). **Required, not optional** — the merger's H.1.2 warning will flag missing refinements, and the reviewer will repair, but doing it correctly here saves a repair cycle.
- [ ] Every Stage-2 process node has `parent: sys_root` + `level: 1` set.
- [ ] Every data-store node has `parent: sys_root` + `level: 1` set + `kind: data_store`.
- [ ] Every internal flow has both endpoints in `entities` (terminator or process or data_store).
- [ ] `confidence` + `provenance.{agent, rationale}` on every emitted node and edge.

If any check fails, fix in `processes.json` before emitting.

## Discipline

- **Process `description` is 2–3 sentences (H.2.c).** Beyond the 1-line `summary`, every process node MUST carry a `description` field with 2–3 sentences capturing scope + rationale: what work the process does end-to-end, why it's a separate process from its siblings, and any constraint that anchors its boundary. Pull from module docstrings + the cluster's README. The emitter surfaces this as the process's `description:` in `dictionary.yaml` (the architect's first-pass reading material). A terse one-line `summary` is fine; a terse one-line `description` is the sidecar-feels-lifeless symptom H.2 is fixing.
- **HP processes are verb-noun.** "Validate Order" not "Validation". "Compute Balance" not "Balance Service". Match the existing examples (`proc_acquire_tension`, `proc_compute_balance`, `proc_reel_controller`).
- **Process granularity is architectural, not file-system.** Don't make every directory a process. A process is a meaningful unit of behavior — the thing an architect would draw on a whiteboard. Many directories collapse into one process.
- **Data stores are passive.** A data store stores data; it doesn't transform. If a cluster's files include both DB access AND business logic, it's a process (with `implemented_by` including the DB access files) — not a separate data store.
- **`needs_cspec` follows the role hint.** If the state-machine detector flagged any file in the cluster, `needs_cspec: true`. Don't second-guess the classifier on this — its false positives are surfaced by confidence, but the signal is strong when present.
- **Refine, don't duplicate, boundary flows.** Boundary flows are already in `boundary.json` with `source=term_X, target=sys_root`. Add `refined_target` / `refined_source` pointing at the right internal process. Don't emit a new flow.
- **Confidence on imports-based flow inference is medium.** Imports tell you "A uses B" but not always "B sends data to A." If the import is a type-only or utility import, there may be no actual data flow. Use 0.6–0.7 for import-inferred flows; 0.9+ only when there's clear runtime evidence (e.g., the cluster has explicit RPC clients).

## Implementation status

**Skill description: ✅ drafted.** Backing scripts: ✅ `hp_toolkit/ingest/process_candidates.py` (Commit 2). Orchestrator dispatch in Commit 3.

## See also

- Design doc: [`toolkit/INGEST_DESIGN.md`](../INGEST_DESIGN.md).
- Predecessors: [`hp-ingest-scan`](hp-ingest-scan.md), [`hp-ingest-boundary`](hp-ingest-boundary.md).
- Follower: [`hp-ingest-leaf`](hp-ingest-leaf.md) — Stages 3+4, runs per-process.
- IR schema: [`hp_toolkit/ingest/schema.py`](../hp_toolkit/ingest/schema.py).
- Existing HP examples: [`examples/solar/dictionary.yaml`](../../examples/solar/dictionary.yaml) (6 internal processes), [`examples/fishing-rig/dictionary.yaml`](../../examples/fishing-rig/dictionary.yaml) (5 internal processes).
