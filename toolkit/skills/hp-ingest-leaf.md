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
5. **Write architect-facing `comments` (H.2.c).** 2–4 sentences capturing the *why* of this PSPEC — the rationale beyond the functional body. What's the design constraint that drove this contract? What alternatives were rejected? What's the operational consequence of getting it wrong? Pull from the source's module docstrings, file-header comments, and (if available) external-context QA test plans. This is the field that distinguishes a "structural extraction" PSPEC from one an architect would actually want to review.
6. **Set confidence**: 0.8+ when the source clearly shows what the process does; lower when it's distributed across many helpers.

Output shape (PSPEC):

```json
{
  "nodes": [
    { "id": "pspec_validate_order", "kind": "pspec", "label": "Validate Order — PSPEC",
      "stage": 4, "confidence": 0.82,
      "implemented_by": ["src/orders/validate.rs", "src/orders/rules.rs"],
      "parent": "proc_validate_order",
      "summary": "Apply business rules to inbound order events.",
      "transformation": {
        "style": "textual",
        "body": "FOR EACH INCOMING_ORDER:\n  APPLY business rules from RULE_TABLE\n  IF all rules pass: EMIT VALIDATED_ORDER\n  ELSE: EMIT VALIDATION_FAILURE with rule violations"
      },
      "comments": "Validation is centralized here rather than in the API gateway so that order events from any source (HTTP API, message bus, batch import) get the same rule treatment. Rules are versioned in RULE_TABLE — never inline. Performance constraint: validation must complete in <50ms per order (the API path's hard latency budget).",
      "provenance": { "agent": "hp-ingest-leaf",
                      "rationale": "validate.rs::validate(order: Order) -> Result<Validated, RuleError>; rules read from RULE_TABLE constant in rules.rs:14." } }
  ],
  "edges": []
}
```

The full PSPEC body (transformation text + constraints + comments) lives in `extra` fields on the node that the emitter consumes when writing `dictionary.yaml`. Schema is permissive (`model_config = ConfigDict(extra="allow")`) so the LLM can attach `transformation: { style: "textual", body: "..." }` + `comments: "..."` + computational-constraint fields directly.

## Behavior

**Progress log:** at entry, append a START line scoped to *this* leaf invocation (parallel runs each write their own line); after writing `leaf-<process-id>.json`, append a DONE line. Per `hp-ingest.md` orchestrator convention:
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START    stage=3-4 agent=hp-ingest-leaf process=<proc-id>" >> <intermediate-dir>/progress.log`
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DONE     stage=3-4 agent=hp-ingest-leaf process=<proc-id> kind=<cspec|pspec> confidence=<0.0-1.0>" >> <intermediate-dir>/progress.log`

When invoked, conversationally:

1. **Read the project glossary (H.4.c).** Load `intermediate/glossary.curated.json` (if present). State names + transition labels (CSPEC mode) and flow names + PSPEC body terminology (PSPEC mode) all draw on the project's domain vocabulary. Prefer glossary terms — especially categories `state`, `event`, and `process` — over generic English.
2. **Read pre-stage file drops (architect guidance + external evidence).**
   - **Hints:** check `intermediate/hints/leaf-<process-id>.md` first (process-specific guidance); fall back to `intermediate/hints/leaf.md` (cross-leaf guidance). If present, treat as binding. Append a `HINT_LOADED` line: `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) HINT_LOADED stage=3-4 agent=hp-ingest-leaf process=<proc-id> path=<hint-path>" >> <intermediate-dir>/progress.log`.
   - **External context:** read `external-context/qa-test-plans/` — relevant plans describe expected behavior for the process (PSPEC outcome expectations / CSPEC state transitions). Record source paths in `provenance.external_context_used` on the IR nodes that drew on them.
3. **Read the process input** (id, label, implemented_by, needs_cspec).
4. **Read every file in `implemented_by[]`.** This is the only agent that reads raw source.
5. **If `needs_cspec`:** consult `state-machine-candidates.json` for this process's files. Use Mode A above.
6. **Else:** use Mode B (PSPEC).
7. **Set confidence + provenance** on every node/edge.
8. **Write `intermediate/leaf-<process-id>.json`.**

## Discipline

- **CSPEC and PSPEC are mutually exclusive.** Per HP convention, a state-rich process gets a CSPEC and *does not* get a separate PSPEC (the CSPEC IS the spec). If `needs_cspec` was set by Stage 2, never emit a PSPEC for this process.
- **PSPEC bodies use HP structured-English**, not code. Re-read existing examples (`examples/fishing-rig/01-level1/pspecs/acquire-tension.md`) for tone.
- **Capitalized flow names in PSPEC bodies** match the flow labels exactly (`F3 TENSION`, not `tension`). The validator's balancing rule (1988 §13.1) depends on this.
- **State labels are noun phrases**, not verbs ("Initializing", "Armed", "Bite Detected" — not "Initialize", "Arm", "Detect Bite").
- **State nodes MUST set `parent_machine: <proc_id>` (G.2).** Every CSPEC-mode state node has `parent_machine: proc_<owning-process-id>` pointing at the process that owns the CSPEC. Same for `parent: proc_<owning-process-id>` (the level-2 hierarchy parent). Without these, the validator flags "state without parent_machine" and the renderer can't draw the state inside the right CSPEC bubble. **Required, not optional.** Mirrors the `parent` convention for terminators (G.1) and processes (H.1.1).
- **Exactly one state per CSPEC has `is_initial: true`.** Pick the variant the constructor sets, or the one with no inbound transitions. If you can't identify the initial state from source evidence, emit your best guess with confidence < 0.7 + a `provenance.rationale` noting the ambiguity — the reviewer will spot-check.
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
