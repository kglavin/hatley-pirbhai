---
name: hp-ingest
description: Brownfield ingest — orchestrates the full pipeline (Stage 0 scanner → Stages 1–5 LLM agents → merge → review → emit dictionary.yaml) to turn an existing codebase into an HP project. Pure-Python prep scripts do the bulk of the work; LLM agents handle the architectural-judgment calls.
---

# hp-ingest

## When to use

To take an existing codebase (your own brownfield project, an open-source target, etc.) and produce an HP `dictionary.yaml` that the rest of the toolkit (validate, render, status, portal, PDF, all the `hp-propose-*` modernization skills) can consume.

Two modes:

- **Greenfield ingest** — no existing `dictionary.yaml` in the output project. Default.
- **Incremental update** — re-ingest a codebase that was previously ingested. Only re-runs the agents whose inputs touched (see *Incremental* below). Triggered with `--incremental`.

Per Q4 in [INGEST_DESIGN.md](../INGEST_DESIGN.md), v1 does **not** support merging a hand-authored `dictionary.yaml` with an ingested one — `--incremental` is for code-change reconciliation on an already-ingested baseline.

## What it does

Runs a 7-phase pipeline:

| Phase | Step | Mechanism | Output |
|---|---|---|---|
| 0 | Scan codebase | Pure Python (`scan_codebase`) | `intermediate/scan.json` — per-file role hint + significance |
| 1 | Boundary candidate prep + LLM | Script + [`hp-ingest-boundary`](hp-ingest-boundary.md) | `intermediate/boundary.json` |
| 2 | Process candidate prep + LLM | Script + [`hp-ingest-processes`](hp-ingest-processes.md) | `intermediate/processes.json` |
| 3+4 | State-machine detect + parallel LLM per leaf | Script + N×[`hp-ingest-leaf`](hp-ingest-leaf.md) (3–5 concurrent) | `intermediate/leaf-<proc>.json` per process |
| Merge 1 | Deterministic merge | Pure Python (`merge_graph.py`) | `intermediate/hp-graph.json` + merge report |
| 5 | Architecture candidate prep + LLM | Script + [`hp-ingest-architect`](hp-ingest-architect.md) | `intermediate/architecture.json` |
| Merge 2 | Final merge with allocations | Pure Python | Updated `hp-graph.json` |
| Review | Repair + validate | [`hp-ingest-review`](hp-ingest-review.md) | Validation pass + `ingest-report.md` (+ optional `ingest-conflicts.md` for incremental) |
| Emit | IR → YAML | Pure Python (`emit_dictionary.py`) | `dictionary.yaml` |
| Render | Diagrams + portal + PDF | Existing toolkit (`render_project.py`) | All generated artifacts |

Token cost (per [INGEST_DESIGN.md](../INGEST_DESIGN.md) > *Token economics*):
- ~50–100k tokens for fishing-rig-scale projects (~$0.50)
- ~300–800k tokens for cloudctlplane-scale (~$1–5)
- Leaf analyzer dominates because it reads raw source code. Significance filter is the highest-leverage cost lever.

## Behavior

When invoked, conversationally:

### Phase 0 — Scan

Run the Python scanner:

```bash
cd toolkit
uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --scan-only
```

This writes `<project-dir>/intermediate/scan.json` with the per-file role hints. **Inspect it before proceeding** — if the significance filter dropped too much (or too little), tune `SignificanceConfig` and re-run. The cost of getting Phase 0 right is zero tokens.

### Phase 1 — Boundary

Run the boundary candidate-prep script:

```bash
uv run python -m hp_toolkit.ingest.boundary_candidates \
    --scan <project-dir>/intermediate/scan.json \
    --codebase <codebase-path> \
    --output <project-dir>/intermediate/boundary-candidates.json
```

Then dispatch the `hp-ingest-boundary` subagent (Task tool). Pass:
- Path to `scan.json` (for project meta + framework hints)
- Path to `boundary-candidates.json` (per-file kind hints + routes/topics)
- Required output: `<project-dir>/intermediate/boundary.json` (IR-shaped nodes + edges)

### Phase 2 — Processes

```bash
uv run python -m hp_toolkit.ingest.process_candidates \
    --scan <project-dir>/intermediate/scan.json \
    --output <project-dir>/intermediate/process-candidates.json
```

Dispatch `hp-ingest-processes` subagent. Pass:
- `scan.json`, `boundary.json`, `process-candidates.json`
- Required output: `<project-dir>/intermediate/processes.json`

### Phases 3 + 4 — Per-process leaf analysis (parallel)

Detect state-machine candidates first (deterministic):

```bash
uv run python -m hp_toolkit.ingest.state_machine_detector \
    --scan <project-dir>/intermediate/scan.json \
    --codebase <codebase-path> \
    --output <project-dir>/intermediate/state-machine-candidates.json
```

Then for **each leaf process** (every `process` node in `processes.json` that doesn't have child processes), dispatch one `hp-ingest-leaf` subagent. **Run them in parallel — up to 5 concurrent via the Task tool's parallel-dispatch feature.** Each invocation gets:
- Its one target process node (from `processes.json`)
- Path to `scan.json` (for file metadata)
- Path to `state-machine-candidates.json` (for state extraction hints)
- Required output: `<project-dir>/intermediate/leaf-<process-id>.json`

Pace: 5 at a time; wait for all 5 to finish before launching the next batch.

### Merge 1 — Assemble IR

```bash
uv run python -m hp_toolkit.ingest.merge_graph \
    --intermediate <project-dir>/intermediate \
    --output <project-dir>/intermediate/hp-graph.json \
    --report <project-dir>/intermediate/merge-report.txt
```

If the merge report is non-clean (duplicates / dropped edges / unrecoverable issues), the reviewer agent will repair. Continue regardless.

### Phase 5 — Architecture

```bash
uv run python -m hp_toolkit.ingest.architecture_candidates \
    --scan <project-dir>/intermediate/scan.json \
    --codebase <codebase-path> \
    --output <project-dir>/intermediate/architecture-candidates.json
```

Dispatch `hp-ingest-architect` subagent. Pass:
- `hp-graph.json` (for Stage 1–4 nodes the architect will allocate to modules)
- `architecture-candidates.json`
- Required output: `<project-dir>/intermediate/architecture.json`

### Merge 2 — Re-merge with architecture

Re-run `merge_graph` to fold in the architecture nodes + allocations:

```bash
uv run python -m hp_toolkit.ingest.merge_graph \
    --intermediate <project-dir>/intermediate \
    --output <project-dir>/intermediate/hp-graph.json \
    --report <project-dir>/intermediate/merge-report.txt
```

### Review — Repair + validate

Dispatch `hp-ingest-review` subagent. It:
- Repairs anything in `merge-report.txt` that needs LLM judgment
- Projects `dictionary.yaml` (via `emit_dictionary.py`) to a temp path
- Runs `hp-validate` against it
- Iterates repair → re-project → re-validate until clean (or hits 5 iterations and halts)
- Composes `ingest-report.md`

### Emit

When the reviewer approves:

```bash
uv run python -m hp_toolkit.ingest.emit_dictionary \
    --graph <project-dir>/intermediate/hp-graph.json \
    --output <project-dir>/dictionary.yaml
```

### Render

Run the existing toolkit render to produce diagrams + portal + PDF:

```bash
uv run python scripts/render_project.py <project-dir>
```

### Confirm

Run `hp-status` to show the final state of the ingested project.

## Discipline

- **Honor the IP firewall** when ingesting IP-sensitive codebases (e.g., cloudctlplane, bru). Per the brownfield-ingest-patterns memory: pattern-level observations only; never quote IP-laden node descriptions, file contents, or summaries into toolkit artifacts (only into the project's own `dictionary.yaml`, which stays in the project tree).
- **Never run two LLM agents on overlapping inputs in parallel** except by design (the leaf-analyzer-per-process pattern). The agents are designed to be order-aware; running boundary + processes in parallel breaks the flow-refinement chain.
- **Conservative incremental.** On `--incremental`, the default is to write `ingest-conflicts.md` and halt before overwriting `dictionary.yaml`. The user reviews + re-runs with `--auto-accept` to commit. Modernization-layer fields (ADRs, SLOs, budgets, TPMs, observability, V&V, STRIDE, bounded contexts, catalog refs, etc.) are **never** touched by re-ingest.
- **One commit per ingest.** Recommended: after a successful ingest, commit the new `dictionary.yaml` (and `intermediate/` if you want the IR + reports tracked, though it's gitignored by default). The git commit hash gets recorded in `project.git_commit_hash` — the next `--incremental` keys off it.
- **The user's hand-edits win.** Any field in `dictionary.yaml` that hp-ingest didn't author originally (per `provenance.agent`) is preserved verbatim on re-ingest.

## Token cost

Per [INGEST_DESIGN.md > Token economics](../INGEST_DESIGN.md):

- Fishing-rig scale (~30 files, 4 leaf processes): ~50–100k tokens (~$0.50).
- cloudctlplane scale (~1600 files, ~30–50 leaf processes after filter): ~300–800k tokens ($1–5).
- Incremental (3–10 files changed): ~5–30k tokens.

`hp-ingest-leaf` dominates because it reads raw source. Tightening `SignificanceConfig.min_pure_logic_lines` from 50 → 200 cuts the cost 2–3× on noisy codebases.

## Implementation status

**Skill description: ✅ drafted.** Pipeline scripts: ✅ all 6 in `hp_toolkit/ingest/` (Commits 1+2+3 of `kg/brownfield-ingest`). Subagent skill definitions: ✅ all 6 in `toolkit/skills/hp-ingest-*.md`. CLI: ✅ `scripts/hp_ingest.py` with `--scan-only` and `--prep-candidates` modes; full-pipeline mode dispatches via this orchestrator skill.

## See also

- Design doc: [`toolkit/INGEST_DESIGN.md`](../INGEST_DESIGN.md) — full pipeline architecture + token economics + incremental rules.
- Subagent skills: [`hp-ingest-scan`](hp-ingest-scan.md), [`hp-ingest-boundary`](hp-ingest-boundary.md), [`hp-ingest-processes`](hp-ingest-processes.md), [`hp-ingest-leaf`](hp-ingest-leaf.md), [`hp-ingest-architect`](hp-ingest-architect.md), [`hp-ingest-review`](hp-ingest-review.md).
- Followers (post-ingest): [`hp-validate`](hp-validate.md), [`hp-render`](hp-render.md), [`hp-status`](hp-status.md). Then the modernization-layer skills: [`hp-capture-adr`](hp-capture-adr.md), [`hp-propose-budgets-and-tpms`](hp-propose-budgets-and-tpms.md), [`hp-propose-observability`](hp-propose-observability.md), [`hp-propose-slos`](hp-propose-slos.md), [`hp-propose-threat-model`](hp-propose-threat-model.md), [`hp-propose-bounded-contexts`](hp-propose-bounded-contexts.md), [`hp-propose-architecture`](hp-propose-architecture.md) — these refine the ingested baseline with form-based reviews.
- Pattern source: review of [Understand-Anything](https://github.com/Lum1104/Understand-Anything) (TypeScript Claude Code plugin doing similar work) — see *Provenance* in INGEST_DESIGN.md.
