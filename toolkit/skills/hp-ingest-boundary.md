---
name: hp-ingest-boundary
description: Stage 1 of brownfield ingest — given the scanner's boundary-candidate list (HTTP servers, CLI entries, message-bus consumers, etc.), decide which are real Stage-1 terminators, name them, and draw boundary flows between them and `sys_root`. Emits IR nodes for terminators + edges for boundary flows.
---

# hp-ingest-boundary

## When to use

Stage 1 of the `/hp-ingest` orchestration. Runs once per ingest (or per `--incremental` re-run if any `boundary`-classified files changed). Consumes `intermediate/scan.json` + `intermediate/boundary-candidates.json` (both produced by deterministic Python scripts). Emits `intermediate/boundary.json` containing IR-shaped terminator nodes + boundary-flow edges.

The LLM's value-add here is the **judgment** call: not every HTTP listener is a Stage-1 terminator (some are internal — e.g., a health-check endpoint isn't really an external actor). The classifier provides candidates; you decide.

## What it does

For each entry in `boundary-candidates.json`:

1. **Decide if it's a real Stage-1 boundary.** A boundary candidate represents a Stage-1 terminator only if there's a meaningful *external actor* on the other side — a user, an upstream service, a hardware device, a scheduler. A health-check that only the orchestrator pings is internal; the same endpoint exposing the public API is external.
2. **Name the terminator** in HP convention: short id (`term_<short>`), human-readable label (`Browser User`, `Payment Gateway`, `Scheduled Job`), short description. Multiple candidates that all interface with the same external actor collapse to one terminator (e.g., 4 HTTP endpoints for a "User" — one terminator, multiple flows).
3. **Draw the boundary flow(s).** Each terminator has at least one flow to or from `sys_root` (the System bubble). Flow naming follows HP: short id (`flow_<short>`), label like `F1: user actions` (numbered for readability). Direction matters — `data_flow` from terminator → sys_root for inbound, sys_root → terminator for outbound. If a single endpoint has both (request/response), emit two flows.
4. **Set provenance + confidence** on every node/edge. Confidence reflects how strong the kind hint + evidence was: a clear `axum::Server::bind` with REST routes for `/users` → high confidence (0.9+). A vague match → low confidence (0.4–0.6) for the architect to spot-check.

Output JSON shape:

```json
{
  "nodes": [
    { "id": "term_browser_user", "kind": "terminator", "label": "Browser User",
      "stage": 1, "confidence": 0.9,
      "summary": "Human operator using the web UI",
      "implemented_by": [],
      "provenance": { "agent": "hp-ingest-boundary",
                      "rationale": "axum routes /login, /dashboard, /api/* with session-cookie auth" } },
    ...
  ],
  "edges": [
    { "source": "term_browser_user", "target": "sys_root",
      "kind": "data_flow", "label": "F1: user actions",
      "stage": 1, "confidence": 0.9,
      "provenance": { "agent": "hp-ingest-boundary",
                      "rationale": "inbound HTTP POST /api/* + session cookies" } },
    ...
  ]
}
```

## Behavior

**Progress log:** at entry, append a START line; after writing `boundary.json`, append a DONE line with summary stats. Per `hp-ingest.md` orchestrator convention:
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START    stage=1 agent=hp-ingest-boundary" >> <intermediate-dir>/progress.log`
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DONE     stage=1 agent=hp-ingest-boundary terminators=$N flows=$M" >> <intermediate-dir>/progress.log`

When invoked, conversationally:

1. **Read inputs.** `intermediate/scan.json` (for project meta + framework hints) and `intermediate/boundary-candidates.json` (per-file kind + routes/topics + evidence).
2. **Group candidates by external actor.** Multiple HTTP routes that all serve "users" → one terminator. A gRPC server endpoint and an HTTP endpoint that both implement the same external API → still one terminator with two flows.
3. **For each group, propose a terminator + its flows.** Emit nodes + edges as above. Be conservative on naming — generic but accurate (`Browser User` not `Chrome Desktop User`) so the architect can rename without renaming HP semantics.
4. **Skip internal boundaries.** Health-check endpoints, debug endpoints, intra-cluster service mesh interfaces. Mark them with a `notes` field saying why you skipped, so the architect can audit.
5. **Set confidence + provenance** on every emitted node/edge.
6. **Write `intermediate/boundary.json`.**

## Discipline

- **Terminators are external; never internal.** If both endpoints of a candidate flow are inside the codebase, it's a Stage-2 internal flow, not a Stage-1 boundary flow. Skip those here — Stage 2 will pick them up.
- **One terminator per external actor, not per endpoint.** "User" is one terminator regardless of how many endpoints they touch. Multiple flows are fine; many terminators with similar labels is a smell.
- **Naming follows HP convention.** `term_<short>` ids; labels are 1–3 words; descriptions one sentence; flow labels use the `F<N>: <noun-phrase>` form. Look at `examples/fishing-rig/dictionary.yaml` or `examples/solar/dictionary.yaml` for the style.
- **Confidence is honest.** Don't inflate. A guessed terminator gets 0.5; a clear-evidence one gets 0.9. The architect uses this to know what to spot-check.
- **Boundary inference is upstream of decomposition.** Don't conflate a terminator with an internal process. If candidate evidence says "this is where the system processes incoming user events" — that's a *process*, not a terminator. The terminator is the user.

## Implementation status

**Skill description: ✅ drafted.** Backing scripts: ✅ `hp_toolkit/ingest/boundary_candidates.py` (Commit 2 of `kg/brownfield-ingest`).

LLM dispatch happens via the orchestrator (`/hp-ingest` skill, Commit 3) which spawns one subagent invocation of this skill, passes the two JSON paths, and reads the resulting `boundary.json` from disk. Direct invocation: open the boundary-candidates.json in MPE, follow the behavior steps manually.

## See also

- Design doc: [`toolkit/INGEST_DESIGN.md`](../INGEST_DESIGN.md) — full pipeline.
- Predecessor: [`hp-ingest-scan`](hp-ingest-scan.md) — produces `scan.json` + the boundary-candidates this agent consumes.
- Follower: [`hp-ingest-processes`](hp-ingest-processes.md) — Stage 2, consumes `scan.json` + `boundary.json`.
- IR schema: [`hp_toolkit/ingest/schema.py`](../hp_toolkit/ingest/schema.py).
- Reference for HP terminator semantics: [`reference/HP_QUICK_REF.md`](../reference/HP_QUICK_REF.md).
