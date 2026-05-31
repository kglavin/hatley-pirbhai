---
name: hp-ingest-leaf
description: Stages 3 + 4 of brownfield ingest, invoked once per leaf process. Decides whether the process needs a CSPEC (state machine) or a PSPEC (functional contract) based on the role-hint mix + state-machine-candidate evidence, then writes the appropriate HP artifact. Parallelizable — the orchestrator dispatches 3–5 concurrent invocations.
---

# hp-ingest-leaf

## When to use

Per leaf process discovered by `hp-ingest-processes`. The orchestrator dispatches one invocation of this skill per process (parallel, 3–5 concurrent — same pattern as Understand-Anything's parallel file-analyzers, but batched by *process*, not by file).

A "leaf" process is one that doesn't decompose into further sub-processes — it's the unit of behavior we write a CSPEC or PSPEC for. CSPEC if `needs_cspec: true`; PSPEC otherwise.

## What it does

Given:
- A single process node from `processes.json` (its `id`, `label`, `implemented_by[]`, `needs_cspec` flag)
- The `intermediate/scan.json` (for file metadata)
- The `intermediate/state-machine-candidates.json` (with extracted states + transitions for state-rich files)
- The file contents of every file in `implemented_by[]` (read fresh from disk — this is the only ingest agent that reads raw source)

Decide CSPEC vs PSPEC, write the content. Emit `intermediate/leaf-<process-id>.json` with nodes (state nodes for CSPEC; pspec node for PSPEC) + edges (transitions for CSPEC).

### Mode A — CSPEC (`needs_cspec: true`)

The state-machine detector already extracted candidate states + transitions for the files in this process. Your job:

1. **Normalize state names** to HP convention (`state_<short>`, label is a noun phrase like "Bite Detected"). Drop variants that are clearly placeholder / never-reached.
2. **Identify the initial state** — usually the variant the constructor sets, or the one with the most inbound transitions but no outbound.
3. **Decide composite states** if the state machine has nesting. Look for state-of-state patterns (a "Connected" state with sub-states "Idle" / "Streaming").
4. **Author each transition** — event name (what triggers the transition), action (what the system does as a result). Pull both from the source code; the detector only gave you the from/to pairs.
5. **Emit IR nodes** for each state + IR edges (kind=`triggers`) for each transition.

Output shape (CSPEC):

```json
{
  "nodes": [
    { "id": "state_initializing", "kind": "state", "label": "Initializing",
      "stage": 3, "confidence": 0.85, "is_initial": true,
      "parent_machine": "proc_bite_detector",
      "summary": "Startup self-test in progress.",
      "implemented_by": ["src/state.rs"],
      "provenance": { "agent": "hp-ingest-leaf",
                      "rationale": "enum variant `Initializing`; set by State::new()" } },
    ...
  ],
  "edges": [
    { "source": "state_initializing", "target": "state_armed",
      "kind": "triggers", "label": "self-test passed; ready to fish",
      "stage": 3, "confidence": 0.8,
      "provenance": { "agent": "hp-ingest-leaf",
                      "rationale": "match arm `Initializing => Armed` after self-test pass" } }
  ]
}
```

### Mode B — PSPEC (`needs_cspec: false`)

This is the per-process functional contract — INPUTS / OUTPUTS / TRANSFORMATION per 2000 Fig 4.46. Your job:

1. **Identify the process's INPUTS** by reading the source. What flows arrive at this process? (The flows are already in `boundary.json` + `processes.json`; cross-reference the IDs.)
2. **Identify the OUTPUTS** the same way.
3. **Write the TRANSFORMATION body.** In HP convention: structured English, capitalized flow names matching the flow labels. Concise — 5–15 lines. No code; no pseudocode. Describe *what* the process does, not *how*.
4. **Choose computational constraints** when relevant: `frequency`, `timing`, `accuracy`. Pull from the source if there's a `RATE_LIMIT` constant or a `sleep(0.01)` etc.
5. **Set confidence**: 0.8+ when the source clearly shows what the process does; lower when it's distributed across many helpers.

Output shape (PSPEC):

```json
{
  "nodes": [
    { "id": "pspec_validate_order", "kind": "pspec", "label": "Validate Order — PSPEC",
      "stage": 4, "confidence": 0.82,
      "implemented_by": ["src/orders/validate.rs", "src/orders/rules.rs"],
      "parent": "proc_validate_order",
      "summary": "Apply business rules to inbound order events.",
      "provenance": { "agent": "hp-ingest-leaf",
                      "rationale": "validate.rs::validate(order: Order) -> Result<Validated, RuleError>" } }
  ],
  "edges": []
}
```

The full PSPEC body (transformation text + constraints) lives in an `extra` field on the node that the emitter consumes when writing `dictionary.yaml`. Schema is permissive (`model_config = ConfigDict(extra="allow")`) so the LLM can attach `transformation: { style: "textual", body: "..." }` directly.

## Behavior

**Progress log:** at entry, append a START line scoped to *this* leaf invocation (parallel runs each write their own line); after writing `leaf-<process-id>.json`, append a DONE line. Per `hp-ingest.md` orchestrator convention:
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START    stage=3-4 agent=hp-ingest-leaf process=<proc-id>" >> <intermediate-dir>/progress.log`
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DONE     stage=3-4 agent=hp-ingest-leaf process=<proc-id> kind=<cspec|pspec> confidence=<0.0-1.0>" >> <intermediate-dir>/progress.log`

When invoked, conversationally:

1. **Read the process input** (id, label, implemented_by, needs_cspec).
2. **Read every file in `implemented_by[]`.** This is the only agent that reads raw source.
3. **If `needs_cspec`:** consult `state-machine-candidates.json` for this process's files. Use Mode A above.
4. **Else:** use Mode B (PSPEC).
5. **Set confidence + provenance** on every node/edge.
6. **Write `intermediate/leaf-<process-id>.json`.**

## Discipline

- **CSPEC and PSPEC are mutually exclusive.** Per HP convention, a state-rich process gets a CSPEC and *does not* get a separate PSPEC (the CSPEC IS the spec). If `needs_cspec` was set by Stage 2, never emit a PSPEC for this process.
- **PSPEC bodies use HP structured-English**, not code. Re-read existing examples (`examples/fishing-rig/01-level1/pspecs/acquire-tension.md`) for tone.
- **Capitalized flow names in PSPEC bodies** match the flow labels exactly (`F3 TENSION`, not `tension`). The validator's balancing rule (1988 §13.1) depends on this.
- **State labels are noun phrases**, not verbs ("Initializing", "Armed", "Bite Detected" — not "Initialize", "Arm", "Detect Bite").
- **Don't invent states.** Only emit states that have evidence in the source. If the detector found 4 states but the source clearly has 6, that's a detector gap — emit all 6 with provenance pointing at where you found them.
- **Confidence is honest.** A clear enum with an obvious match expression → 0.85+. A scattered if/else chain across multiple files → 0.5–0.7. The architect uses this to know which CSPECs to spot-check.
- **One leaf invocation, one output file.** `intermediate/leaf-<process-id>.json` — the orchestrator concatenates them via the merge script.

## Implementation status

**Skill description: ✅ drafted.** Backing scripts: ✅ `hp_toolkit/ingest/state_machine_detector.py` produces the CSPEC candidate input (Commit 2). Orchestrator dispatch (parallel Task tool calls, one per process) in Commit 3.

## See also

- Design doc: [`toolkit/INGEST_DESIGN.md`](../INGEST_DESIGN.md).
- Predecessors: [`hp-ingest-scan`](hp-ingest-scan.md), [`hp-ingest-boundary`](hp-ingest-boundary.md), [`hp-ingest-processes`](hp-ingest-processes.md).
- Existing HP equivalents (for tone/style):
  - PSPEC: [`examples/fishing-rig/01-level1/pspecs/acquire-tension.md`](../../examples/fishing-rig/01-level1/pspecs/acquire-tension.md), [`examples/solar/01-level1/pspecs/acquire-telemetry.md`](../../examples/solar/01-level1/pspecs/acquire-telemetry.md).
  - CSPEC: [`examples/fishing-rig/dictionary.yaml` → states + transitions for `proc_bite_detector`](../../examples/fishing-rig/dictionary.yaml), [`examples/solar/dictionary.yaml` → `proc_compute_balance`](../../examples/solar/dictionary.yaml).
- HP reference: [`reference/HP_QUICK_REF.md`](../reference/HP_QUICK_REF.md) — CSPEC and PSPEC sections.
