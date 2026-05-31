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
| 0b | Documentation corpus | Pure Python (`docs_walker.py`) | `intermediate/docs-corpus.json` — typed doc-file inventory |
| 0c | Glossary candidates (extract) | Pure Python (`glossary_extractor.py`) | `intermediate/glossary-candidates.json` — deterministic harvest |
| 0c-curate | Glossary curation (optional LLM) | [`hp-ingest-glossary`](hp-ingest-glossary.md) | `intermediate/glossary.curated.json` — canonical 30–60-term glossary |
| 0d | User-facing docs harvest (H.6) | Pure Python (`user_docs_gatherer.py`) | `intermediate/user-docs.json` — usage excerpts, actor + intent phrases, API specs |
| 0e | Testbed detect + mine (H.7) | Pure Python (`testbed_miner.py`) | `intermediate/testbeds.json` — purpose-built testbeds + their scenarios |
| 0f | Make/Justfile recipe parse | Pure Python (`recipe_parser.py`) | `intermediate/recipes.json` — deploy / up / build / test recipes |
| 0.5 | External-context solicitation (H.8.a) | Orchestrator conversation — auto-detect with fallback ask | `external-context/<category>/*` (user-managed) |
| 1 | Boundary candidate prep + LLM | Script + [`hp-ingest-boundary`](hp-ingest-boundary.md) | `intermediate/boundary.json` |
| 2 | Process candidate prep + LLM | Script + [`hp-ingest-processes`](hp-ingest-processes.md) | `intermediate/processes.json` |
| 2-recurse | Hierarchical Stage-2 recursion (H.3) | Pure Python (`recursion.py`) + recursive [`hp-ingest-processes`](hp-ingest-processes.md) dispatches | `intermediate/<parent-proc-id>/processes.json` per recursing subsystem |
| 3+4 | State-machine detect + parallel LLM per leaf | Script + N×[`hp-ingest-leaf`](hp-ingest-leaf.md) (3–5 concurrent) — leaves can be at any recursion depth | `intermediate/leaf-<proc>.json` per process |
| Merge 1 | Deterministic merge | Pure Python (`merge_graph.py`) | `intermediate/hp-graph.json` + merge report |
| 5 | Architecture candidate prep + rationale gather + LLM | Script + [`hp-ingest-architect`](hp-ingest-architect.md) | `intermediate/architecture.json` (+ `rationale-sources.json` for the architect's input) |
| Merge 2 | Final merge with allocations | Pure Python | Updated `hp-graph.json` |
| Review | Repair + validate | [`hp-ingest-review`](hp-ingest-review.md) | Validation pass + `ingest-report.md` (+ optional `ingest-conflicts.md` for incremental) |
| Emit | IR → YAML | Pure Python (`emit_dictionary.py`) | `dictionary.yaml` |
| Render | Diagrams + portal + PDF | Existing toolkit (`render_project.py`) | All generated artifacts |

Token cost (per [INGEST_DESIGN.md](../INGEST_DESIGN.md) > *Token economics*):
- ~50–100k tokens for fishing-rig-scale projects (~$0.50)
- ~300–800k tokens for acme-cp-scale (~$1–5)
- Leaf analyzer dominates because it reads raw source code. Significance filter is the highest-leverage cost lever.

## Behavior

When invoked, conversationally:

### Phase 0a — Check for resume state + progress log

Before doing anything else, check `<project-dir>/intermediate/progress.log` (if present). Each subsequent phase MUST:

- **Check for an existing valid output** for that phase. If present + parseable, **skip the phase** and announce: `[resume] skipping <phase> — <output>.json present (<summary stats>)`. Loud per locked Q2.
- **Append a START line** to `intermediate/progress.log` before dispatching the subagent: `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START    stage=<N> agent=<skill-name>" >> <intermediate>/progress.log`.
- **Append a DONE line** after the subagent's output is written, with summary stats: `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DONE     stage=<N> agent=<skill-name> <key>=<value> ..." >> <intermediate>/progress.log`.
- **Append a SKIP line** when resuming a completed phase: `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) SKIP     stage=<N> agent=<skill-name> reason=output_present <key>=<value> ..." >> <intermediate>/progress.log`.

The Python prep scripts (`scan.py`, `boundary_candidates.py`, etc.) already write their own START/DONE lines via `hp_toolkit.ingest.progress_log` when invoked from `scripts/hp_ingest.py --resume`. Subagent skills (boundary, processes, leaf, architect, review) write their own lines.

External observers can `tail -f <intermediate>/progress.log` to watch the run live.

### Phase 0b — Architect file drops (hints + external context)

Two file-drop directories are auto-created on every run (`scripts/hp_ingest.py` calls `ensure_hints_dir` + `ensure_external_context_dir` at startup; the orchestrator can lean on those, but should also tolerate either being absent):

- `<project>/intermediate/hints/<stage>.md` — *guidance* from an architect watching `progress.log`. If `processes.md` exists when Stage 2 fires, the `hp-ingest-processes` subagent reads it as binding guidance. Per locked tuning F.3.a.
- `<project>/external-context/<category>/*` — *evidence* the user pasted in before / during the run (QA test plans, ADRs, requirements, design docs, runbooks, glossary). Each subagent reads the categories relevant to its stage. Per locked tuning H.8.b.

The orchestrator's job here is **announcement**, not loading — surface what's already been dropped so the user knows what guidance/evidence is in flight, and surface where new files can be dropped at any stage boundary. The per-stage subagents do the actual loading at their respective `Phase N`.

When `hp-ingest.py` runs, it announces what it found at startup (cyan `hint` rows + magenta `ext` rows). The orchestrator can re-announce at stage boundaries to remind the user that mid-run hint drops are an option.

### Phase 0 — Scan

Run the Python scanner:

```bash
cd toolkit
uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --scan-only
```

This writes `<project-dir>/intermediate/scan.json` with the per-file role hints. **Inspect it before proceeding** — if the significance filter dropped too much (or too little), tune `SignificanceConfig` and re-run. The cost of getting Phase 0 right is zero tokens.

### Phase 0.5 — External-context solicitation (H.8.a; auto-detect with fallback ask)

Per locked tuning Q6: if the user has already populated `<project-dir>/external-context/<category>/*` (qa-test-plans / adrs / requirements / design-docs / runbooks / glossary), proceed silently — those files are already going to be fed to the relevant stages. If the directory is empty (only the bootstrap README), pause and ask the user once.

**Auto-detect logic:**

```python
# In Python terms; the orchestrator implements this via Bash + the
# external_context helper or a direct file check.
from hp_toolkit.ingest.external_context import has_any_content, summarize_presence
present = summarize_presence(project_dir)
if has_any_content(project_dir):
    # Announce what we found, proceed without prompting
    print(f"==> External context detected: {present}")
else:
    # Empty — ask once
    prompt_for_external_context()
```

**Solicitation prompt** (when external-context/ is empty):

> hp-ingest works best when it has access to the project's architectural context, not just its code. The repo scan picked up `README.md`, `docs/`, and any detected testbeds — but architectural decisions, QA test plans, and stakeholder requirements often live outside the repo (Confluence, Notion, shared drives). Are there additional context sources that would help?
>
> Common categories:
> - **QA test plans / acceptance criteria** — strongest signal for boundary intent + PSPEC outcomes
> - **Architecture decision records (ADRs)** in a wiki
> - **Design docs / proposals** in shared drives
> - **Stakeholder requirements** documents
> - **Operational runbooks**
> - **Domain glossary / vocabulary** documents
> - **Postmortems** informing architecture
>
> **If yes:** paste content (or point at a local-filesystem path) below + tell me which category each piece falls in. I'll write them under `external-context/<category>/` and feed them to the relevant stages.
>
> **If nothing applies:** reply `continue` and I'll proceed with code-only context. You can also drop files into `external-context/` at any later point and re-run the relevant stage with `--resume`.

When the user responds:
- **With pasted content** → write each piece to `external-context/<category>/<short-name>.md` (one file per piece). Re-run `has_any_content()` to confirm content is present. Append a `EXT_CONTEXT_PROVIDED` event to progress.log: `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) EXT_CONTEXT_PROVIDED stage=0.5 agent=hp-ingest categories=<comma-list>" >> intermediate/progress.log`.
- **With "continue" / "skip" / "nothing"** → proceed without external context. Append a `EXT_CONTEXT_SKIPPED` event.
- **With a local path** → copy the files into `external-context/<category>/` (the orchestrator can use Bash `cp` for this).

On subsequent runs the directory has content + the solicitation is skipped.

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

### Phase 2-recurse — Hierarchical decomposition (HIERARCHICAL_INGEST_DESIGN.md)

Per locked H.3 + Branch 3: after Stage 2 emits `processes.json`, decide which processes deserve a **recursive Stage-2 dispatch** to produce their internal level-2 sub-processes. Acme-cp-scale monorepos contain 8+ subsystems compressed into single level-1 bubbles; this phase fills out the decomposition.

```bash
uv run python -m hp_toolkit.ingest.recursion \
    --processes <project-dir>/intermediate/processes.json \
    --scan <project-dir>/intermediate/scan.json \
    --intermediate <project-dir>/intermediate \
    --current-depth 1 \
    [--threshold-files 30] \
    [--threshold-lines 3000] \
    [--max-depth 3] \
    [--no-recurse]
```

The CLI:
- Walks every process in `processes.json`.
- For each, decides `should_recurse` per the locked Q2 + Q4 thresholds (default: ≥30 files AND ≥3000 lines AND depth < 3).
- For passing processes: writes scoped `intermediate/<proc-id>/scan.json` + `intermediate/<proc-id>/process-candidates.json` containing only the subsystem's files.
- Appends `RECURSE_DECISION` + `RECURSE_INTO` events to `progress.log`.
- Emits JSON to stdout listing the subsystems queued for LLM dispatch.

**For each subsystem in the output:**

Dispatch `hp-ingest-processes` AGAIN as a recursive subagent. Pass:
- The scoped `scan.json` from the subsystem dir
- The PARENT processes.json (so the sub-agent knows which level-1 process it's decomposing — referenced via `parent_process_id`)
- The scoped `process-candidates.json` from the subsystem dir
- Required output: `<project-dir>/intermediate/<parent-proc-id>/processes.json`

Each sub-agent emits IR nodes with `parent: <parent-proc-id>` per the H.3 hierarchy.

**Then recurse again on the sub-result:**

```bash
uv run python -m hp_toolkit.ingest.recursion \
    --processes <project-dir>/intermediate/<parent-proc-id>/processes.json \
    --scan <project-dir>/intermediate/<parent-proc-id>/scan.json \
    --intermediate <project-dir>/intermediate \
    --current-depth 2 \
    --threshold-files <same> --threshold-lines <same> --max-depth <same>
```

The depth cap (default 3) bounds the tree. The orchestrator can `--no-recurse` for fast/flat runs.

### Phases 3 + 4 — Per-process leaf analysis (parallel)

Detect state-machine candidates first (deterministic):

```bash
uv run python -m hp_toolkit.ingest.state_machine_detector \
    --scan <project-dir>/intermediate/scan.json \
    --codebase <codebase-path> \
    --output <project-dir>/intermediate/state-machine-candidates.json
```

Then for **each leaf process** dispatch one `hp-ingest-leaf` subagent. **Run them in parallel — up to 5 concurrent via the Task tool's parallel-dispatch feature.** Per H.3 hierarchy: a leaf process is one with **no child processes** in the IR — recursion-tree leaves can be at any level (proc_prism_resolvers at level 2 is a leaf if it has no further sub-processes). Collect leaves by walking the full processes.json + every `<parent-proc-id>/processes.json` written by the recursion phase. Each invocation gets:
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

- **Honor the IP firewall** when ingesting IP-sensitive codebases (e.g., acme-cp, acme-sensor). Per the brownfield-ingest-patterns memory: pattern-level observations only; never quote IP-laden node descriptions, file contents, or summaries into toolkit artifacts (only into the project's own `dictionary.yaml`, which stays in the project tree).
- **Never run two LLM agents on overlapping inputs in parallel** except by design (the leaf-analyzer-per-process pattern). The agents are designed to be order-aware; running boundary + processes in parallel breaks the flow-refinement chain.
- **Conservative incremental.** On `--incremental`, the default is to write `ingest-conflicts.md` and halt before overwriting `dictionary.yaml`. The user reviews + re-runs with `--auto-accept` to commit. Modernization-layer fields (ADRs, SLOs, budgets, TPMs, observability, V&V, STRIDE, bounded contexts, catalog refs, etc.) are **never** touched by re-ingest.
- **One commit per ingest.** Recommended: after a successful ingest, commit the new `dictionary.yaml` (and `intermediate/` if you want the IR + reports tracked, though it's gitignored by default). The git commit hash gets recorded in `project.git_commit_hash` — the next `--incremental` keys off it.
- **The user's hand-edits win.** Any field in `dictionary.yaml` that hp-ingest didn't author originally (per `provenance.agent`) is preserved verbatim on re-ingest.

## Token cost

Per [INGEST_DESIGN.md > Token economics](../INGEST_DESIGN.md):

- Fishing-rig scale (~30 files, 4 leaf processes): ~50–100k tokens (~$0.50).
- acme-cp scale (~1600 files, ~30–50 leaf processes after filter): ~300–800k tokens ($1–5).
- Incremental (3–10 files changed): ~5–30k tokens.

`hp-ingest-leaf` dominates because it reads raw source. Tightening `SignificanceConfig.min_pure_logic_lines` from 50 → 200 cuts the cost 2–3× on noisy codebases.

## Implementation status

**Skill description: ✅ drafted.** Pipeline scripts: ✅ all 6 in `hp_toolkit/ingest/` (Commits 1+2+3 of `kg/brownfield-ingest`). Subagent skill definitions: ✅ all 6 in `toolkit/skills/hp-ingest-*.md`. CLI: ✅ `scripts/hp_ingest.py` with `--scan-only` and `--prep-candidates` modes; full-pipeline mode dispatches via this orchestrator skill.

## See also

- Design doc: [`toolkit/INGEST_DESIGN.md`](../INGEST_DESIGN.md) — full pipeline architecture + token economics + incremental rules.
- Subagent skills: [`hp-ingest-scan`](hp-ingest-scan.md), [`hp-ingest-boundary`](hp-ingest-boundary.md), [`hp-ingest-processes`](hp-ingest-processes.md), [`hp-ingest-leaf`](hp-ingest-leaf.md), [`hp-ingest-architect`](hp-ingest-architect.md), [`hp-ingest-review`](hp-ingest-review.md).
- Followers (post-ingest): [`hp-validate`](hp-validate.md), [`hp-render`](hp-render.md), [`hp-status`](hp-status.md). Then the modernization-layer skills: [`hp-capture-adr`](hp-capture-adr.md), [`hp-propose-budgets-and-tpms`](hp-propose-budgets-and-tpms.md), [`hp-propose-observability`](hp-propose-observability.md), [`hp-propose-slos`](hp-propose-slos.md), [`hp-propose-threat-model`](hp-propose-threat-model.md), [`hp-propose-bounded-contexts`](hp-propose-bounded-contexts.md), [`hp-propose-architecture`](hp-propose-architecture.md) — these refine the ingested baseline with form-based reviews.
- Pattern source: review of [Understand-Anything](https://github.com/Lum1104/Understand-Anything) (TypeScript Claude Code plugin doing similar work) — see *Provenance* in INGEST_DESIGN.md.
