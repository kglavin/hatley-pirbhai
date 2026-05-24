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
      "provenance": { "agent": "hp-ingest-processes",
                      "rationale": "Directory cluster `src/orders/` with 3 pure-logic files, one inbound import path from api/handlers.rs" } },
    { "id": "store_orders_db", "kind": "data_store", "label": "Orders DB",
      "stage": 2, "confidence": 0.9,
      "implemented_by": ["src/db/orders_repo.rs"],
      "summary": "Persistent storage for orders + line items." },
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

1. **Read inputs.** `scan.json`, `boundary.json`, `process-candidates.json`. Skim the file lists in each cluster to understand what's inside (the role-hint mix gives a strong starting point).
2. **Cluster-by-cluster decision:** for each candidate, decide promote / merge with sibling / drop.
3. **Look at the import edges between clusters** to inform the flow graph. If cluster A's files frequently import from cluster B, A consumes data from B → draw a flow B → A.
4. **Cross-reference with boundary terminators.** Each terminator has a boundary flow; identify which Stage-2 process handles it. Add the refinement (`refined_target` for inbound flows, `refined_source` for outbound).
5. **Cap process count.** Aim for 5–10 internal processes at Stage 2 for a cloudctlplane-scale project. More is fine but means decomposition is happening at too low a level. Use process subdirectories to surface fewer top-level processes.
6. **Skip clusters that are infrastructure-only** (e.g., a `src/utils/` cluster with only helpers). Note in a `notes` field for architect audit.
7. **Set confidence + provenance** on every emitted node/edge.
8. **Write `intermediate/processes.json`.**

## Discipline

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
