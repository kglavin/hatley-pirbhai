# Hierarchical Ingest Design

## ✅ Status: Locked 2026-05-25

All five open questions resolved:
- **Q1** Decomposition mode → Option X (Hierarchical single-dictionary)
- **Q2** Recursion trigger → Auto-threshold on `implemented_by` size
- **Q3** Stage-5 architect timing → Once at top, after all recursion
- **Q4** Recursion-threshold defaults → 30 files AND 3000 lines
- **Q5** Sub-process flow refinement → Required at emit; merger validates (H.1 pattern)

---

## Goal

Make `hp-ingest` produce a **multi-level decomposition** for monorepo-scale targets (acme-cp and similar large monorepos). Today the pipeline emits a flat 2-level model (Stage-1 boundary at `level: 0`, Stage-2 internals at `level: 1`). On a monorepo containing 8+ independently-deployable subsystems, that compresses each subsystem into a single level-1 bubble — the structure is right, but every entity is one level too coarse.

HP methodology natively supports recursive decomposition: a process with sufficient internal complexity gets its own level-2 DFD; that DFD's processes can each have their own level-3 DFD; etc. The renderer + validator are *almost* there — they already chain `parent` for state nodes inside CSPECs (level 2). What's missing is the *process-level* hierarchy: process nodes that have other process nodes as children.

This design adds that. After the locked questions resolve, the implementation is bounded — pipeline + emitter + renderer + validator changes, no schema overhaul.

## Why hierarchical (Option X) and not system-of-systems (Option Y)

The H.3 finding in [INGEST_TUNING_DESIGN.md](INGEST_TUNING_DESIGN.md) names two design choices:

- **Option X — Hierarchical single-dictionary**: one `dictionary.yaml` with multi-level `parent` chains. Recursion target.
- **Option Y — SoS multi-project**: each subsystem becomes its own HP project. Multiple dictionaries linked by file paths.

Per locked Q1 (this doc): **build X first**. Reasoning:

- **Monorepo target.** acme-cp has 8+ subsystems but one team owns the architecture. A single `dictionary.yaml` matches the team's mental model: one review surface, one provenance trail, one glossary, one set of bounded contexts.
- **HP-native.** Recursive `parent`-linked decomposition is exactly what HP §4.2 (levelled DFDs) describes. We're filling out the methodology's existing shape, not adding a new one.
- **Renderer is closer than it looks.** The level-1 DFD code generalizes — same Mermaid + D2 + cytoscape pattern, just keyed on parent-process-id instead of `sys_root`.
- **Y becomes a sibling later** if a multi-repo / multi-team target appears (no toolkit changes prevent it). Composable, not exclusive.

## Architecture: pipeline + recursion model

The pipeline shape change is **Stage 2 becomes recursive**; everything else stays sequential.

```
Phase 0       Scan + docs walker + glossary + user-docs + testbeds + recipes (no change)
Phase 0.5     External-context solicitation (no change)
Phase 1       hp-ingest-boundary (no change)

Phase 2 ──────┬── hp-ingest-processes (recursion root)
              │     emits level-1 process candidates
              │
              ├── for each process P where _should_recurse(P):
              │     ┌── narrow context: scope scan + docs + candidates to P.implemented_by[]
              │     ├── dispatch hp-ingest-processes again as a SUBAGENT for P
              │     │     emits level-2 sub-processes with parent: P
              │     ├── _should_recurse(sub) again? → level 3 → … up to --max-recursion-depth
              │     └── merge sub-process IR back into the main hp-graph.json
              │
              └── exit recursion when all leaf processes have been emitted

Phases 3 + 4  hp-ingest-leaf (per leaf — leaves can now be at any level)
Phase 5       hp-ingest-architect (ONCE at top, sees full hp-graph.json with hierarchy)
Merge + emit  (unchanged shape; emitter handles multi-level parent chains per below)
Review        (unchanged)
```

**Recursion trigger** (per locked Q2 — auto-threshold):

A process `P` recurses if **all** of:
- `len(P.implemented_by) ≥ --recurse-threshold-files` (default: 30)
- `sum(line-count of P.implemented_by) ≥ --recurse-threshold-lines` (default: 3000)
- Current depth `< --max-recursion-depth` (default: 3)

The thresholds are tunable per-target via CLI flags; the defaults aim for acme-cp-scale (where ~3–8 of the 8 level-1 processes deserve a level-2 decomposition).

**Per-subsystem context window:**

When the orchestrator dispatches `hp-ingest-processes` for process `P` as a recursion call, it passes:
- A **scoped scan view** (only files in `P.implemented_by[]` — written to `intermediate/<P-id>/scan.json`)
- A **scoped process-candidates view** (only directory clusters under `P.implemented_by[]`)
- The full `intermediate/glossary.curated.json` (terminology is repo-wide, not per-subsystem)
- The full `intermediate/docs-corpus.json` filtered via `corpus.near(P-dir)` for rationale (docs are also repo-wide, but each recursion focuses on its own subdir)
- The parent-process metadata: `parent_process_id`, `parent_label`, summary, parent flows

The subagent emits sub-process nodes with `parent: P-id` and `level: <current+1>`. Internal flows between sub-processes carry over the parent's flow IDs as `refined_source` / `refined_target` (same H.1 mechanism the boundary→Stage-2 refinement uses today).

## IR shape

Minimal schema changes — existing fields are already permissive.

**`IRNode.parent`** (already exists, currently used for `sys_root`):
- Sub-process IR nodes set `parent: <parent-proc-id>` (e.g. `parent: proc_svc_query`).
- Sub-process `level` becomes `parent.level + 1`.

**Flow refinement:** the existing `refined_source` / `refined_target` mechanism on flow edges extends naturally:
- A level-1 flow `proc_svc_query → proc_svc_c` carries `refined_source: proc_svc_query_resolvers, refined_target: proc_svc_c_ingest` when those sub-processes exist.
- The renderer reads the refinement chain to pick the right pair for the level it's drawing.

**No new IR fields needed.** The Pydantic schema already supports arbitrary `parent` values + integer `level`. The H.5 `architecture_modules.allocated_processes` lists allocate **leaf processes** (the bottom of the recursion tree) — non-leaf processes are organizational, not deployment units.

## Per-subsystem intermediate-file layout

Recursion calls write their per-subsystem outputs under `intermediate/<parent-proc-id>/`:

```
intermediate/
├── scan.json                       ← root scan
├── docs-corpus.json                ← root docs walk
├── glossary-candidates.json
├── glossary.curated.json
├── boundary.json
├── processes.json                  ← level-1 processes
├── proc_svc_query/
│   ├── scan.json                   ← scoped to svc-query's implemented_by[]
│   ├── process-candidates.json     ← scoped
│   ├── processes.json              ← level-2 sub-processes (parent: proc_svc_query)
│   ├── proc_svc_query_resolvers/
│   │   └── processes.json          ← level-3 (if it recurses further)
│   └── ...
├── proc_svc_a/
│   └── ...
├── hp-graph.json                   ← merged across all levels
└── progress.log
```

This keeps per-subsystem state isolated for `--resume`: a single subsystem's recursion can be re-run by deleting its directory without disturbing siblings.

## Renderer + validator lift

This is the biggest implementation cost — the toolkit isn't built around level-2 process DFDs today.

**Renderer changes** (in `toolkit/scripts/render_project.py` + `hp_toolkit/render/`):
- `render_level1_dfd` generalizes to `render_levelN_dfd(parent_id, level)` — same Mermaid/D2/SVG output pattern, scoped to children-of-parent.
- For each process with children, emit a `level-N/<proc-id>.html` page with its sub-DFD + sidebar entry under the parent.
- Sidebar tree gains a nested level for each non-leaf process.
- PDF render includes the per-level DFDs in tree order.

**Validator changes** (in `toolkit/hp_toolkit/validate.py`):
- Allow `parent: proc_X` (not just `sys_root`) on process nodes.
- Tighten: if process has child processes, it cannot have a CSPEC or PSPEC (a non-leaf process is purely structural).
- New rule: flow refinements must walk a valid `parent` chain (a level-1 flow's refined endpoints must be processes at level 2, etc.).

**Emitter changes** (in `hp_toolkit/ingest/emit_dictionary.py`):
- `_emit_entity` for processes: when a process has children, set `description` from rationale sources but suppress `pspecs`/`needs_cspec` (non-leaf processes don't get specs).
- The `level: N` field auto-derives from the `parent` chain depth (no longer hard-coded to 1).

**No `dictionary.yaml` schema changes.** Existing toolkit already accepts arbitrary `parent` + `level` integers; only validator rules tighten.

## What we ship

New modules:

```
toolkit/hp_toolkit/ingest/
├── recursion.py                    ← _should_recurse(P, config); per-subsystem scope helpers
└── ...

toolkit/scripts/
└── hp_ingest.py                    ← recursion-aware orchestrator; new flags below

toolkit/skills/
└── hp-ingest-processes.md          ← recursion-aware behavior (already loads scoped inputs)
```

New CLI flags:

```bash
--recurse-threshold-files N      # default 30
--recurse-threshold-lines N      # default 3000
--max-recursion-depth N          # default 3
--no-recurse                     # disable recursion entirely (back to flat level-1 — fast on small projects)
```

Existing skill markdown updates:
- `hp-ingest-processes.md` — recursion-aware behavior (emit `parent: <P-id>` when invoked in recursion mode; honor `parent_process_id` from inputs).
- `hp-ingest.md` (orchestrator) — pipeline diagram + recursion-loop description.
- `hp-ingest-architect.md` — sees full hierarchy in hp-graph.json; allocates leaves only.

## Implementation order

Four commits on `kg/hp-ingest-hierarchical`. Verifiable in isolation.

### Commit T11 — `recursion.py` + recursion decision + validator extension
- New `hp_toolkit/ingest/recursion.py` with `should_recurse(process, depth, config)`, `scope_for_subsystem(scan, process)` helpers.
- Validator extended to allow `parent: proc_X` on processes + the flow-refinement-chain rule.
- Emitter extended to derive `level` from parent chain + suppress pspecs/needs_cspec on non-leaf processes.

**Verification:** hand-craft a 2-level dictionary.yaml; validate clean; emit from a 2-level IR. No new LLM dispatch yet.

### Commit T12 — Orchestrator recursion loop in `hp_ingest.py`
- Stage-2 dispatch becomes recursive in `hp_ingest.py`.
- Per-subsystem `intermediate/<P-id>/` directory layout.
- `--recurse-threshold-files` / `--recurse-threshold-lines` / `--max-recursion-depth` / `--no-recurse` flags.
- `progress.log` gets `RECURSE_INTO <P-id> depth=<D>` events.

**Verification:** dry-run on acme-cp (no LLM yet — Stage 2 prep only); confirm the right ~3–5 processes pass the threshold.

### Commit T13 — Skill markdown recursion behavior + renderer level-N DFDs
- `hp-ingest-processes.md`: recursion-aware step (emit `parent: <P-id>`; load scoped inputs).
- `hp-ingest.md`: pipeline-diagram update.
- `hp-ingest-architect.md`: allocate leaves only.
- `render_project.py` + `hp_toolkit/render/`: generalize level-1 DFD to level-N; sidebar nesting; PDF tree order.

**Verification:** re-ingest acme-cp with LLM agents — emit 2-level dictionary; renderer produces per-level DFD pages.

### Commit T14 — Doc catch-up
- Update `INGEST_DESIGN.md` to reference this doc + hierarchical mode.
- Update `INGEST_TUNING_DESIGN.md` H.3 status to ✅.
- Update `README.md` + `TUTORIAL.md` if any CLI surface shifted.

---

## Open questions

### Q1. Decomposition mode

The two H.3 options:

- [x] **Option X — Hierarchical single-dictionary** *(recommended; locked direction of this doc)*
- [ ] Option Y — SoS multi-project (sibling design doc later if a multi-repo target appears)
- [ ] Both via `--mode hierarchical|sos` flag from the start

I lean **X first**. Y composes later — no toolkit changes prevent it.

### Q2. Recursion trigger

- [x] **Auto-threshold on implemented_by size** *(recommended)*
- [ ] Architect picks via hints
- [ ] Hybrid (auto-detect + `--no-recurse=<P-id>` / `--force-recurse=<P-id>` overrides)

I lean **auto-threshold**. Hybrid is a natural follow-up once the default thresholds prove their behavior on acme-cp.

### Q3. Stage-5 architect timing

- [x] **Once at top, after all recursion completes** *(recommended)*
- [ ] Once per recursion level

I lean **once at top**. Architecture modules allocate *leaf* processes (the bottom of the tree); the architect sees the full hierarchy in `hp-graph.json` and allocates accordingly.

### Q4. Recursion-threshold defaults

What thresholds should the auto-recurse defaults target?

- [x] **Files ≥ 30 AND lines ≥ 3000** *(recommended for acme-cp-scale)*
- [ ] Files ≥ 50 AND lines ≥ 5000 (more conservative)
- [ ] Lines ≥ 5000 only (single-metric, simpler)

I lean **30 files / 3000 lines**. Both metrics matter (30 small files is a thin process; 3 thick files isn't typically a sub-system either). Tunable via CLI flags so we can revise.

### Q5. Sub-process flow refinement — required, or best-effort?

When a level-1 flow `proc_svc_query → proc_svc_c` exists, and both ends recurse to level-2, should we **require** the LLM to emit `refined_source` + `refined_target` pointing at the right sub-processes, or **best-effort** (let the merger flag missing refinements as warnings + the reviewer repair)?

- [x] **Required at emit time + merger validates** *(recommended)* — same H.1 pattern Branch 1 established for boundary refinements. The LLM emits refinements; the merger warns; the reviewer repairs.
- [ ] Best-effort (silent); only required at validator time

I lean **required + validate**. The H.1 pattern works; matching it here keeps the discipline consistent.

---

**Status:** locked 2026-05-25.
**Branch:** `kg/hp-ingest-hierarchical`.
**Spawning context:** post-Branch-2 merge to main (`d20d777`). Q1–Q3 locked during pre-draft exploration (Option X / auto-threshold / once-at-top Stage 5); Q4 + Q5 locked at draft review (30 files / 3000 lines; required refinement). Implementation T11–T14 begins after this commit.
