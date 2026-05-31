# hp-ingest Tuning — design (dogfood-driven)

## ✅ Status: Locked 2026-05-24

Q1–Q6 all resolved with recommended defaults:
- **Q1.** `deploys` edge kind: **alias-only** (`deploys → refines` in merger alias table).
- **Q2.** Resume verbosity: **loud** (per-skipped-stage summary stats).
- **Q3.** Progress log: **augment** stderr (both have a role).
- **Q4.** H.5 deployment-configuration: **informational-only** (provenance + implemented_by only; no schema extension this round).
- **Q5.** H.7 testbed detection: **always-on with override** (`--no-testbed-detect`).
- **Q6.** H.8 external-context: **auto-detect with fallback ask** (use `external-context/` if present; prompt at phase 0.5 if absent).

8 H-findings captured + 3-branch organization. **Branch 1 (this branch)** implements 4 commits T1–T4 covering A · B · C · D · E.1 · E.3 · F.1 · F.2 · G.1–G.4 · H.1. **Branches 2 + 3** spawn after this branch lands.

**Status:** locked.
**Branch:** `kg/hp-ingest-dogfood-tuning`.
**Spawning context:** the first real-world dogfood run of `hp-ingest` against `/home/kevin/bluerock/cloudctlplane` (commit `9dedb93dad1a`, 2026-05-23 → 2026-05-24). Pipeline completed end-to-end despite a mid-run power outage; review agent recovered cleanly from on-disk state and emitted a 39.6 KB `dictionary.yaml` with 0 validation errors + 34 warnings. The dogfood surfaced concrete classifier / filter / vocabulary / orchestration gaps which this branch addresses.

## How to use this doc

Two roles:

1. **Already-surfaced findings** (sections A–G below) — captured from the dogfood run before architect review. Each has evidence, proposed fix, and an estimate.
2. **Open slots for Kevin's review findings** (section H — `## Review-driven findings`). Kevin appends here as he walks `dictionary.yaml` + `ingest-report.md`. Each new finding should follow the template:

   ```
   ### N. <short title>
   **Evidence:** <file path, command output, or specific entity that demonstrates the issue>
   **Observed:** <what hp-ingest produced>
   **Expected:** <what a correct ingest should have produced>
   **Proposed fix:** <classifier regex / schema field / agent prompt / orchestration step>
   **Touch list:** <files that need editing>
   **Priority:** [high | medium | low]
   ```

This is the form-based-proposal pattern from prior design docs (`MODERNIZATION_DESIGN.md`, `PORTAL_DESIGN.md`, `INGEST_DESIGN.md`). Save this file as you add findings; we lock + iterate once the list is complete.

## Goal

Fold the dogfood signal into the toolkit so the **next** hp-ingest run produces a tighter, more-immediately-architect-reviewable `dictionary.yaml`. Specifically:

- **Sharper classifier** — fewer false positives in the role-hint and framework detection.
- **Smarter clustering** — monorepo-aware (e.g., `--max-depth` per subproject).
- **Schema vocabulary** — close gaps that forced the architect agent to invent edge kinds (`deploys`, `depends_on_library`).
- **Run resilience** — `--resume` + progress log so power outages / context-window crashes don't lose work.
- **Agent prompt fixes** — surface the warning categories that recur across the run.
- **Tuning guide** — document the configuration curve so a user with a 200-file project tunes differently from one with a 4000-file monorepo.

The branch is intentionally bounded: **no schema-paradigm changes, no new ingest stages, no LLM-vs-Python boundary re-draws.** All those go in a future arc. Tuning = polish.

---

## Provenance

The cloudctlplane dogfood run produced (in chronological order):

```
~/hatley-pirbhai/examples/cloudctlplane/intermediate/
├── scan.full.json                       (1003K — initial full scan, all 4012 files)
├── scan.json                            (352K  — pruned to 1551 significant)
├── boundary-candidates.json             (7.1K)
├── process-candidates.json              (40K)
├── state-machine-candidates.json        (9.3K)
├── architecture-candidates.json         (44K)
├── boundary.json                        (18K  — Stage 1 agent output)
├── processes.json                       (34K  — Stage 2 agent output)
├── leaf-proc_*.json                     (8 files, 47K total — Stages 3+4 per leaf)
├── architecture.json                    (38K  — Stage 5 agent output)
├── hp-graph.json                        (493K — merged IR, 56 nodes + 87 edges post-repair)
├── merge-report.txt                     (7.8K — 25 unrecoverable edges pre-repair)
└── (output)
    examples/cloudctlplane/
    ├── dictionary.yaml                  (39.6K — emitted; hp-validate clean)
    └── ingest-report.md                 (34 warnings + 1 info)
```

Final IR composition: 5 terminators · 8 processes · 17 architecture modules · 4 interconnects · 3 PSPECs · 19 states · 20 data flows · 26 allocations · 23 transitions · 18 refines.

---

## A. Classifier false positives — `data-store` over-eager

**Evidence:** Stage 0 scan classified `.gitignore`, `multi_agent.py` (2585 lines, an LLM-agent orchestrator), `shipping_agent.py`, and several other files as `data-store` because of bare-token matches on `dgraph`, `clickhouse`, `redis` etc. in comments, docstrings, system-prompt strings, and `.gitignore` path entries.

**Root cause:** `role_classifier._DATA_STORE_PATTERNS` matches any occurrence of DB/cache/queue keywords. No import-context requirement.

**Proposed fix:** Require import-context matching (same shape as the earlier `motor` regex tightening done during fishing-rig debugging). Patterns become:

- Python: `(import|from)\s+(psycopg2|asyncpg|...)\b`
- Rust:   `\buse\s+(sqlx|redis|mongodb)::`
- TS/JS:  `(import|require\()['"]?(redis|mongodb|...)`
- Go:     `"github\.com/(go-redis|jackc/pgx|...)"` (import path inside quotes)

Plus a separate "ORM model declaration" path-pattern for files with `#[derive(sqlx::FromRow)]`, `class.*Base.*declarative_base`, etc.

**Touch list:**
- `hp_toolkit/ingest/role_classifier.py` — rewrite `_DATA_STORE_PATTERNS`.

**Impact:** Significantly fewer false-positive data-store classifications on the next cloudctlplane run; same tightening applies to any monorepo with internal references to data-store tech in non-data-store files.

**Priority:** high.

---

## B. Path filtering gap — dot-files

**Evidence:** `.gitignore` got scanned + classified (as `data-store` because of token matches — see A). It's tracked by `git ls-files` (and so passed `_enumerate_files`) but isn't architecturally significant.

**Root cause:** `significance._ALWAYS_SKIP_PATH_PATTERNS` doesn't include dot-files.

**Proposed fix:** Add `re.compile(r"(^|/)\.[a-zA-Z]")` (any file whose basename starts with `.`) to `_ALWAYS_SKIP_PATH_PATTERNS`. Skips `.gitignore`, `.env*`, `.dockerignore`, `.editorconfig`, `.eslintrc*`, `.prettierrc*` — none of which carry HP architectural signal.

**Touch list:**
- `hp_toolkit/ingest/significance.py` — add one pattern.

**Impact:** Trivial. ~5-10 files per project drop from scan output.

**Priority:** high (very cheap; closes off a class of false positives).

---

## C. `min_pure_logic_lines` default for monorepos

**Evidence:** cloudctlplane scan: 638 `pure-logic` significant files, of which 348 (55%) are under 200 lines. Default `SignificanceConfig.min_pure_logic_lines = 50` was calibrated against fishing-rig + solar (<100-file projects). For a 4000-file monorepo, the resulting candidate pool inflates token cost on the leaf-analyzer pass.

**Root cause:** Single global default doesn't scale.

**Proposed fix:** Two parts:
1. **Document the tuning curve** in INGEST_DESIGN.md (or this doc):
   - <200 files: `min_pure_logic_lines: 30–50` (default works)
   - 200–1000 files: `min_pure_logic_lines: 75–125`
   - >1000 files (monorepo): `min_pure_logic_lines: 150–250`
2. **Expose as CLI flag** on `hp_ingest.py`: `--min-pure-logic <N>` that threads through to `SignificanceConfig`.

**Touch list:**
- `scripts/hp_ingest.py` — add `--min-pure-logic` argparse flag; thread to `scan_codebase(..., significance_config=SignificanceConfig(min_pure_logic_lines=N))`.
- `toolkit/INGEST_DESIGN.md` — add "Tuning guide" section with the size→threshold curve.

**Impact:** Architect can size the filter for the project. Default behavior unchanged for small projects.

**Priority:** medium.

---

## D. Cluster heuristic — `--max-depth` for monorepos

**Evidence:** Kevin already implemented this during the dogfood (kept on disk in `process_candidates.py`). Default clustering by *immediate parent directory* over-fragmented cloudctlplane (4012 → 1551 significant → many leaf clusters). Capping at `--max-depth 3` (`<repo>/<category>/<service>`) consolidates into manageable per-service clusters.

**Root cause:** Single-strategy clustering doesn't scale across project sizes / structures.

**Proposed fix:** Already implemented locally. **Just needs to land in a commit on this branch.** The change is additive (default `max_depth=None` preserves prior behavior).

**Touch list:**
- `hp_toolkit/ingest/process_candidates.py` — already modified locally.
- `scripts/hp_ingest.py` — pass `--max-depth` through to `extract_process_candidates`.
- `toolkit/INGEST_DESIGN.md` — note in tuning guide alongside C.

**Impact:** Big win for monorepos; no impact on small projects.

**Priority:** high (already working; just needs the commit).

---

## E. Schema vocabulary gap — `deploys` (and `depends_on_library`)

**Evidence:** Stage 5 architect agent invented two edge kinds that aren't in `IREdgeKind`:
- `deploys` × 18 — used to express "this deployment module composes / contains these constituent modules" (e.g., `am_deploy_aws_basic` → `am_hramp` / `am_pulse` / `am_prism` / ...).
- `depends_on_library` × 7 — used to express "this module uses this shared library/SDK" (e.g., `am_hramp` → `am_shared_clients`).

The review agent remapped `deploys` → `refines` (correct: deployment-composes-modules is a refinement relationship) and dropped `depends_on_library` (correct: library use is implementation detail, not HP architecture).

**Root cause:** HP's edge vocabulary was designed for embedded / real-time systems and doesn't natively name two patterns common in cloud-native architectures:
1. **Deployment composition** — a deployment unit (Helm chart, CDK stack, terraform module) contains multiple service modules. The `refines` remap captures this, but it's a slight misuse: `refines` was intended for level-N → level-N+1 decomposition, not for deployment-unit composition.
2. **Library / SDK dependency** — separate from `allocates_to` (process-to-physical-module) and `carries` (interconnect-to-flow). Closest HP analog is none.

**Proposed fix:** Two options for `deploys`:

- **E.1 (lightweight):** Add `deploys` as an alias to `refines` in `merge_graph._EDGE_KIND_ALIASES`. The merger normalizes silently; the IR records `refines`; the YAML reads as `refines`. Architect can rename to a custom field via `hp-propose-architecture` post-ingest if they want.
- **E.2 (heavyweight):** Add `deploys` as a first-class `IREdgeKind` value. Update the schema, validator, renderer, dictionary YAML format. Document `deploys` semantics. **Out of scope for tuning branch — needs design discussion.**

For `depends_on_library`:

- **E.3:** Add to alias table mapping to no-op (drop silently with a debug log). The merger already drops unrecoverable edges; this just makes it transparent rather than reaching the review agent.

**Recommendation:** E.1 + E.3 in this branch. E.2 is a separate design conversation if `deploys` proves common across multiple dogfood targets.

**Touch list:**
- `hp_toolkit/ingest/merge_graph.py` — extend `_EDGE_KIND_ALIASES` with `deploys → refines` and `depends_on_library → (drop)`.

**Impact:** No more "25 unrecoverable edges" pre-review on similar cloud-native targets. Review agent has less repair work.

**Priority:** high.

---

## F. Run resilience — `--resume` + progress log

**Evidence:** Mid-run power outage killed the cloudctlplane run after Stages 1–5 + first merge completed (after ~3 hours of LLM work). Recovery required Kevin to manually inspect on-disk state, identify what was missing (review pass), and prompt the new Claude session to dispatch the single missing agent. Doable but fragile — requires understanding of the pipeline internals.

**Root cause:** Two gaps:
1. **`--resume` is in the CLI flag list but not implemented.** No automatic detection of completed stages from on-disk artifacts.
2. **No progress log.** Run state is implicit in the file mtimes in `intermediate/`; an external observer (or a recovery prompt) has to reason from filenames.

**Proposed fix:**

**F.1 — Progress log** (cheaper, lands first):

Add `intermediate/progress.log` — append-only timestamped lines. Every agent (orchestrator + subagents) appends on entry + exit. Example shape:

```
2026-05-23T19:32:14Z START   stage=0 agent=hp-ingest-scan
2026-05-23T19:33:42Z DONE    stage=0 agent=hp-ingest-scan files_scanned=4012 significant=1551
2026-05-23T19:34:01Z START   stage=1 agent=hp-ingest-boundary
2026-05-23T19:40:17Z DONE    stage=1 agent=hp-ingest-boundary terminators=5 flows=8
2026-05-23T19:57:09Z START   stage=3-4 agent=hp-ingest-leaf process=proc_emit_pulse batch=1/3
2026-05-23T19:57:42Z DONE    stage=3-4 agent=hp-ingest-leaf process=proc_emit_pulse kind=pspec confidence=0.78
...
```

Implementation:
- New helper `hp_toolkit/ingest/progress_log.py` with `log_start(stage, agent, **kwargs)` and `log_done(stage, agent, **kwargs)`.
- Each Python script calls these around its work.
- Each LLM-subagent skill markdown gets a new step: "Before reading inputs: `Bash` append a START line to progress.log. After writing output: `Bash` append a DONE line with summary stats."
- Observer can `tail -f intermediate/progress.log` from another terminal.

**F.2 — Resume support** (builds on F.1):

`hp_ingest.py --resume` (and skill-level resume logic):

1. Read `intermediate/progress.log` (if exists) — extract list of completed stages + per-process leaf completions.
2. For each phase in the orchestrator runbook, check: is its output file present + non-empty + valid JSON?
   - Yes → skip dispatch; print "[resume] skipping <stage> — already complete".
   - No → run normally.
3. For Stages 3+4 (leaf): per-process file check. Re-dispatch only processes without a `leaf-<process-id>.json`.
4. Merge + emit always re-run (cheap, deterministic, idempotent).

The orchestrator skill (`hp-ingest.md`) gains a new phase-0 step: "If progress.log exists, parse it to determine resume state. For each subagent, only dispatch if its output JSON isn't already present."

**Touch list:**
- `hp_toolkit/ingest/progress_log.py` — new module.
- `hp_toolkit/ingest/scan.py`, `boundary_candidates.py`, `process_candidates.py`, `state_machine_detector.py`, `architecture_candidates.py`, `merge_graph.py`, `emit_dictionary.py` — each adds a `log_start` / `log_done` pair.
- `scripts/hp_ingest.py` — implement `--resume` skip logic.
- `skills/hp-ingest.md` — phase-0 resume detection step + per-subagent progress-log step.
- `skills/hp-ingest-{scan,boundary,processes,leaf,architect,review}.md` — add the standard START/DONE log lines to each agent's Behavior section.

**Impact:** Power-outage-class recoveries become a single `hp_ingest.py --resume` call. Progress log gives an observer a live tail of where the run is.

**Priority:** F.1 high (cheap, broadly useful). F.2 medium (more work; F.1 alone would have made Kevin's manual recovery a 1-line prompt instead of a multi-step inspection).

**F.3 — Bidirectional: observer can interrupt with guidance.** *(Added 2026-05-24 from Kevin's review question. F.1 + F.2 are read/recovery only; F.3 closes the architect-in-the-loop steering loop.)*

The full vision: an observer watching `progress.log` can see when the pipeline is going off-course — e.g., Stage 2 emitted 30 over-fragmented processes when 8 was right; the architect agent named a module poorly; CSPEC inference looks wrong — and **interrupt with guidance that subsequent stages read**.

Cloudctlplane example: if a tail of progress.log had shown `Stage 2: emitted 30 process candidates` at 19:45 (before leaf-analyzer dispatch), Kevin could have intervened with "too granular; cluster at hydra/services/<svc> rather than per-file-cluster" — Stage 2 re-runs cheap, Stage 3+4 proceed with the corrected base. Current pipeline doesn't support this; observer can only watch helplessly until completion and repair via review or re-run.

**Three sub-mechanisms, design-wise:**

- **F.3.a — Hints directory** (`intermediate/hints/`). Observer can drop files at any time: `intermediate/hints/processes.md`, `intermediate/hints/architecture.md`, `intermediate/hints/leaf-<process-id>.md`. Each subsequent agent's skill markdown is taught: *"Before producing your output, check `intermediate/hints/<your-stage>.md` (if present) — it contains architect guidance you must honor."* Lowest-friction; works asynchronously; no synchronization complexity.

- **F.3.b — Stage-boundary checkpoints** (optional). The orchestrator (`/hp-ingest`) skill gains a `--pause-after <stage>` flag (or asks at each stage in interactive mode). After each stage completes, the orchestrator emits *"Stage N done. Inspect outputs at `intermediate/<X>.json`. Drop guidance at `intermediate/hints/<next-stage>.md` if needed. Reply `proceed` or `revise <stage>` to continue."* Pause-points are at natural agent boundaries — between Stage 1 / 2 / 3+4 / 5 / review.

- **F.3.c — Confidence-driven auto-pause.** When the architect agent or leaf-analyzer self-rates confidence below a threshold on a substantial fraction of outputs, the orchestrator auto-pauses and asks the observer to weigh in *before* the bad confidence propagates downstream. E.g., "Stage 2 produced 8 processes; 5 are confidence < 0.6. Pausing for architect review of `intermediate/processes.json` before dispatching leaf-analyzer."

**Why this matters:** the current pipeline assumes the architect reviews *after* the pipeline completes (via `ingest-report.md` + `dictionary.yaml`). That's expensive on cloudctlplane-scale targets where Stages 1–5 burn 300–800k tokens. Course-correcting after a 3-hour run is wasteful; course-correcting at the Stage-1 boundary or Stage-2 cluster step can save 80% of the token spend and produce a better dictionary on the first try.

**Touch list:**
- `hp_toolkit/ingest/hints.py` — new helper: load + validate `intermediate/hints/<stage>.md` files for an agent on dispatch.
- All `skills/hp-ingest-*.md` — each gets a "Before emitting: check `intermediate/hints/<your-stage>.md`" behavior step.
- `skills/hp-ingest.md` (orchestrator) — `--pause-after` flag + interactive-mode pause logic (F.3.b).
- `skills/hp-ingest.md` + per-stage skills — confidence-driven auto-pause logic (F.3.c).
- `progress_log` helper (F.1) — agents log `HINT_LOADED` / `PAUSED_FOR_GUIDANCE` / `RESUMED_WITH_GUIDANCE` events alongside START/DONE.

**Priority:** F.3.a (hints dir) **high** — small new module, big architect-time payoff, works asynchronously with F.1 progress log. F.3.b (explicit pauses) **medium** — affects orchestrator skill shape. F.3.c (confidence-driven) **low** — refinement once thresholds are calibrated from more dogfood runs.

**Notes:**
- F.3 is a meaningful capability extension, not just a tuning fix. Could be argued for its own design doc + branch (similar to H.3 system-of-systems). My current judgment: F.3.a alone is small enough to land in this tuning branch; F.3.b + F.3.c are follow-up. But if F.3 + the SoS work both grow, they could merge into a "hp-ingest interactive mode" design.
- Hints + system-of-systems compose naturally: at recursive Stage 2 dispatch, the observer can drop hints scoped to a single subsystem before its inner ingest runs.

---

## G. Agent-prompt fixes from review warnings

**Evidence:** ingest-report.md surfaced 34 warnings + 1 info clustering into 4 categories per Kevin's run-summary:

- **G.1 — Terminator parent style** — terminators emitted with wrong / missing `parent` style.
- **G.2 — State nodes missing parent** — Stage 3 leaf-analyzer agent didn't always populate `parent` / `parent_machine` correctly on state nodes.
- **G.3 — Architecture flows not yet `carries:` by interconnects** — Stage 5 architect agent populated `architecture_flows` but didn't always add them to the matching interconnect's `carries:` list.
- **G.4 — Low-confidence modules** (`am_shared_lib`, `am_kafka`) — Stage 5 architect emitted modules where the evidence is thin; reviewer surfaced for architect attention.

**Root cause:** Each category points at a specific agent prompt or emit path that needs tightening.

**Proposed fix:** Each category gets investigated separately once Kevin's review yields more specifics. For now, each category gets a slot below:

### G.1 Terminator parent style

*(Awaiting specifics from Kevin's review of `dictionary.yaml` + `ingest-report.md`. Expected fix: tighten `hp-ingest-boundary.md` skill to specify the exact `parent: sys_root` convention + level: 0.)*

### G.2 State nodes missing parent

*(Awaiting specifics. Expected fix: tighten `hp-ingest-leaf.md` CSPEC-mode emission spec to require `parent_machine: proc_X` on every state node.)*

### G.3 Architecture flows not yet `carries:` by interconnects

*(Awaiting specifics. Expected fix: in `hp-ingest-architect.md`, the "draw the interconnect graph" step should always populate `carries:` lists. Possibly: deterministic post-pass in `merge_graph.py` that auto-populates `carries:` from architecture flow endpoints + interconnect endpoint matching.)*

### G.4 Low-confidence module audit

*(Probably not a fix — these are working-as-intended. The reviewer flagged them for architect attention. Worth documenting "low-confidence is a signal to spot-check, not a bug.")*

**Touch list:**
- `skills/hp-ingest-boundary.md`, `hp-ingest-leaf.md`, `hp-ingest-architect.md` — agent-prompt tightening per category.
- Possibly `merge_graph.py` — deterministic carries: population.

**Priority:** medium (depends on which warnings are systematic vs. one-offs).

---

## H. Review-driven findings

*(Kevin adds findings here as he walks `dictionary.yaml` + `ingest-report.md`. Use the template at the top of this doc.)*

### H.1 Level-1 DFD renders empty (no boundary-flow refinement)

**Evidence:**
- `examples/cloudctlplane/01-level1/dfd.generated.{mmd,svg,html}` show terminators + processes as floating nodes, with boundary-flow arrows pointing at the (undeclared) `sys_root` node — Mermaid silently renders these as dangling arrows; Cytoscape view shows no level-1 graph at all.
- `intermediate/hp-graph.json`: 10 Stage-1 boundary edges, **0 with `refined_source` / `refined_target` set**.

**Observed:** Stage-2 LLM agent emitted Stage-2 processes (8) + internal flows (10), but did *not* go back and refine the boundary flows from Stage 1. So the level-1 DFD has correct internal-flow shape but broken boundary endpoints.

**Expected:** Every Stage-1 boundary edge should have `refined_source` or `refined_target` pointing at the internal process that handles it (per `hp-ingest-processes.md` step 4: *"Refine boundary flows. Each Stage-1 boundary flow has `source=term_X, target=sys_root`. At Stage 2, set `refined_source` / `refined_target` to the actual internal process that handles the boundary flow."*). The renderer uses these to draw the level-1 DFD with terminator→process edges instead of terminator→sys_root edges.

**Proposed fix:** Three layered defenses:

1. **Strengthen the `hp-ingest-processes.md` skill prompt** — promote step 4 from a paragraph in *Behavior* to a hard checklist at the end of the skill: *"Before emitting `processes.json`: confirm every Stage-1 boundary flow now has either `refined_source` or `refined_target` set. If any are missing, identify the handling process and set the refinement. This is required for the level-1 DFD to render."*
2. **Validator warning in the merger** (`merge_graph.py`): when assembling the final IR, count Stage-1 boundary edges missing refinements. Log to merge-report.txt as a recoverable warning (`boundary-flow refinement missing on N edges — Stage 2 agent gap; review repair required`). Reviewer agent picks it up.
3. **Add to `hp-ingest-review.md` skill's repair checklist** — among the standard repair patterns, "If boundary flows lack `refined_source` / `refined_target`, cross-reference with `processes.json` to identify the handling process for each terminator + add the refinement."

**Touch list:**
- `skills/hp-ingest-processes.md` — promote step 4 to required checklist.
- `hp_toolkit/ingest/merge_graph.py` — boundary-flow-refinement check + warning log.
- `skills/hp-ingest-review.md` — add to repair-checklist examples.

**Priority:** **high.** Renders the level-1 DFD unusable on cloudctlplane; would do the same on any project where Stage 2 forgets the refinement step.

### H.2 Sidecars feel lifeless — the "why" available in source isn't folded in

**Evidence:**
- `examples/cloudctlplane/architecture/specs/prism.md`: DESCRIPTION has 4–5 facts (tech stack, endpoints, nginx placement), but DESIGN RATIONALE is the placeholder `(ingest-authored; architect review pending)`.
- Inspecting the IR for `am_prism`: `provenance.rationale` field contains a partial "why" line *("TS package + Dockerfile + compose service across deployments. Single node:22-alpine runtime. Owns proc_explore_graphql including the WS subscription lifecycle CSPEC.")* — but the emitter discards it.
- The codebase clearly has rationale-rich material the architect agent didn't see: service-level README files (`hydra/services/<name>/README.md`), top-of-module docstrings, deployment notes in compose comments, ADRs that may live in `docs/`.

**Observed:** AMS / AIS / PSPEC sidecars present as terse structural extractions. Architect reading them can't see *why* the module exists, *why* it was structured this way, *why* a particular technology was chosen, or what constraints drove the design. They read like generated reference docs, not the engineering record an architect actually wants.

**Expected:** Per 2000 §4.2.5.4, an AMS should carry — alongside DESCRIPTION + CROSS-REFERENCE — a substantive DESIGN RATIONALE (why this module exists, why it's separate from siblings), DESIGN JUSTIFICATION (key technology/protocol choices + alternatives considered), REQUIRED CONSTRAINTS (reliability, safety, physical, cost), and INTERFACES. hp-ingest should populate as much of this as the source material allows; the architect's `hp-propose-architecture` form-based pass refines + extends, not starts-from-blank.

**Three-part root cause:**

1. **Emitter discards what the IR has.** `emit_dictionary._emit_ams()` hard-codes the design_rationale placeholder; doesn't surface `provenance.rationale` or any `design_rationale` field the LLM may have emitted as an extra.
2. **Agent prompts ask for minimums.** `hp-ingest-architect.md` directs the LLM to write a 1-sentence `summary`. It never asks for the longer rationale / justification / constraints prose. Same gap on `hp-ingest-processes.md` (process descriptions are 1-sentence) and `hp-ingest-leaf.md` (PSPEC bodies are functional but skip the "why" the lived examples have in `comments:`).
3. **Agent inputs are too narrow.** The architect agent reads `hp-graph.json` + `architecture-candidates.json`. It does not read service-level `README.md` files, top-of-file docstrings, compose-file comments, or `docs/`-tree architecture notes. Even if asked to write rationale, it would be guessing — most of the "why" lives in those un-ingested sources.

**Proposed fix (three commits' worth, all in this tuning branch):**

- **H.2.a — Emitter surfaces what the IR has.** `_emit_ams` / `_emit_ais` / `_emit_pspec` use `provenance.rationale` (when present + length > 1 sentence) as the seed for `design_rationale`. If the LLM emitted a richer `design_rationale` / `design_justification` / `required_constraints` as extras on the IR node, those flow through verbatim. The placeholder only fires when there's truly nothing to surface.

- **H.2.b — Widen architect agent inputs.** A new deterministic prep helper (`hp_toolkit/ingest/rationale_sources.py`) gathers, per module candidate, the rationale-rich files associated with it: any `README.md` in the module's `implemented_by[]` directories, the top-N lines of each implementation file (module docstring / file header), Dockerfile + compose comments. Output: `intermediate/rationale-sources.json` keyed by candidate id. Architect agent's input set grows to include this. Cost: bounded — only top-of-file or known doc files, no full source.

- **H.2.c — Strengthen agent prompts to demand prose.** Update `hp-ingest-architect.md` to require: a 3–5 sentence `design_rationale` per module (what does it do at architecture level, why is it a separate module, what's the key tech choice + alternatives), a 1–2 sentence `design_justification` (constraints driving the choice), and a `required_constraints` block extracted from infra (resource limits in compose, replica counts in k8s, etc.). Same shape for `hp-ingest-leaf.md` PSPEC mode: require a `comments:` block per PSPEC with the architect-facing "why" beyond the functional body. And `hp-ingest-processes.md`: process descriptions become 2–3 sentences capturing scope + rationale.

**Touch list:**
- `hp_toolkit/ingest/emit_dictionary.py` — surface IR fields instead of hard-coded placeholders (H.2.a).
- `hp_toolkit/ingest/rationale_sources.py` — new helper (H.2.b).
- `scripts/hp_ingest.py` — wire in the rationale-prep step before the architect agent fires.
- `skills/hp-ingest-architect.md` — require rationale / justification / constraints prose (H.2.c).
- `skills/hp-ingest-processes.md` — require richer process descriptions.
- `skills/hp-ingest-leaf.md` — require PSPEC `comments:` prose.

**Priority:** **high.** This is the single biggest quality lever in the tuning branch. Each individual fix is small; together they transform sidecars from "structural reference" to "engineering record."

**Notes / scope:**
- This is *not* a modernization-layer expansion. ADRs / SLOs / budgets / TPMs / observability / V&V / STRIDE remain out of scope for hp-ingest per the locked Q3 — those are decisions, not extractable facts. The rationale prose here is the standard 2000 §4.2.5.4 AMS content, which has *always* been part of the HP toolkit's vocabulary; hp-ingest just wasn't populating it.
- Token cost on H.2.b + H.2.c rises modestly (architect agent reads more files; writes longer prose). Net is probably +50–100k tokens on a cloudctlplane-scale run. The improved review-quality / architect-time payoff is large.

### H.3 System-of-systems: recursive decomposition for monorepos ✅ *(landed in Branch 3 / `kg/hp-ingest-hierarchical`)*

**Status:** ✅ shipped. See [HIERARCHICAL_INGEST_DESIGN.md](HIERARCHICAL_INGEST_DESIGN.md) for the full design + locked Q1–Q5 decisions. Implementation T11–T14. Option X (Hierarchical single-dictionary) landed; Option Y (SoS multi-project) deferred as a sibling design doc if a multi-repo target appears.

**Evidence:**
- cloudctlplane is a monorepo containing 8+ independently-deployable subsystems (hramp, prism, aurora, pulse, sentinel, gfl_toolchain, dgraph, clickhouse, …). Each is a substantial software system with its own internal boundaries, state machines, and architecture.
- Current hp-ingest emitted 8 level-1 processes for the entire 4012-file repo. Each level-1 process is really a subsystem. Reading `dictionary.yaml`: the structure is correct, but every entity is one level too coarse — the latent richness of each subsystem (its internal decomposition, state machines, per-service architecture) is folded into a single bubble.
- Kevin's read: "it gets the structure but misses the intent because its too broad and does not go deep enough to capture the essence."

**Observed:** hp-ingest produces a flat 2-level model (Stage 1 boundary, Stage 2 single-level internals). 8 level-1 processes; no level-2 decomposition.

**Expected:** HP methodology natively supports recursive decomposition. Level-1 DFD shows the system's internal processes; each process with sufficient internal complexity gets its own level-2 DFD; and so on. The renderer + validator already handle multi-level decomposition (see `parent`-linked entities in solar/fishing-rig). hp-ingest should use this.

**Two design choices, both HP-valid:**

**Option X — Hierarchical single-dictionary** *(recommended for monorepos like cloudctlplane):* recursively re-run Stage 2+ on each level-1 process whose `implemented_by[]` cluster exceeds a threshold (say >100 files or >5k lines). Produces one `dictionary.yaml` with multi-level decomposition. `proc_prism` (level 1) gets its own level-2 DFD: `proc_prism_resolvers`, `proc_prism_cache`, `proc_prism_ws_lifecycle` (each with `parent: proc_prism`). CSPECs and PSPECs live at the deepest level. Stage 5 architecture allocates leaves of the tree.

**Option Y — System-of-systems multi-project** *(for multi-repo / multi-team cases):* each subsystem becomes its own HP project. cloudctlplane decomposes into `examples/cloudctlplane/dictionary.yaml` (integration view: subsystems as level-1 processes, cross-subsystem interconnects as flows) + `examples/cloudctlplane/prism/dictionary.yaml` (Prism's own full HP analysis) + one per subsystem. Each independently rendered, validated, reviewable; the top-level is sparse, just the integration story.

For a monorepo with unified architecture work, **X**. For multi-repo team-owned-services, **Y**. They're not mutually exclusive — could even co-exist via a `--mode hierarchical|sos` flag.

**Why this can't be a tuning-branch fix:**

- **Pipeline shape changes.** Stage 2 becomes recursive (or Stage 2.5 becomes "should we recurse?"). New decision logic: when does a process deserve its own deeper analysis? Threshold tuning.
- **Skill markdown changes.** `hp-ingest-processes.md` gains a recursion behavior + decision criterion. `hp-ingest-leaf.md` only fires at the actual leaves (which might be deeper than level 1).
- **Orchestrator changes.** `hp-ingest.md` walks a tree, not a linear sequence. Per-subsystem token budget. Per-subsystem progress log.
- **Emitter changes.** Multi-level `parent`-link emission; nested architecture allocation.
- **Open design questions.** Threshold for "should recurse"? Different SignificanceConfig per recursion level? How does Stage-5 architecture span the subsystem hierarchy?

**Proposed handling:** **Spawn `SYSTEM_OF_SYSTEMS_DESIGN.md` (or `HIERARCHICAL_INGEST_DESIGN.md`) + a follow-up branch `kg/hp-ingest-hierarchical`.** Same form-based-proposal pattern as the prior design docs. Lock the design, then implement in 2–3 commits. This is the natural next major arc after the current tuning branch lands.

**Touch list (in the future branch — not this one):**
- `hp_toolkit/ingest/recursion.py` — new module: decide when a process candidate deserves deeper analysis; orchestrate per-subsystem sub-runs.
- `hp_toolkit/ingest/schema.py` — IR `parent` field already exists; tighten validation around multi-level hierarchies.
- `skills/hp-ingest-processes.md` — recursion-aware behavior.
- `skills/hp-ingest.md` — tree-walking orchestrator runbook.
- `hp_toolkit/ingest/emit_dictionary.py` — nested `parent` link emission.

**Touch list (in this branch — small partial mitigations):**
- `scripts/hp_ingest.py` — make `--max-depth` (Kevin's existing change) prominent in CLI help + tuning guide. *Note this is a finer-grained level-1 clustering, not real recursion. Mention as a "v0 monorepo mitigation".*
- `toolkit/INGEST_DESIGN.md` — add a "System-of-systems" caveat in *Provenance* / *Open questions* sections referencing this finding + the follow-up design doc.

**Priority for tuning branch:** **none** (out of scope). **Priority for follow-up design:** **high.** Without this, hp-ingest is qualitatively a "small-project ingest" tool that produces oversimplified models on monorepo-scale targets. cloudctlplane proves the limitation; any other team's monorepo would hit the same wall.

### H.4 Domain glossary extraction — seed agents with the project's ubiquitous language

**Evidence:**
- cloudctlplane modules carry domain names where they were directly named in the codebase: `am_prism`, `am_hramp`, `am_aurora`, `am_sentinel`, `am_pulse`, `am_dgraph`, `am_clickhouse` (the project's brand vocabulary, lifted from `hydra/services/<name>/` directories + Dockerfile/compose tags).
- But processes drift into generic English: `proc_explore_graphql`, `proc_ingest_signals`, `proc_evaluate_rules`, `proc_query_api`. None of these use the project's own vocabulary even though the codebase + docs almost certainly have domain-specific terms (pulse, archi, signals, rules, alerts, gfl, etc.) defined in READMEs / proposals / docs.
- Flow labels are similarly generic: `F11: pulse signals`, `F13: archi gRPC responses` — they *partially* pick up domain terms when those terms appear in code/file names, but lose the surrounding domain vocabulary that the project's documentation has formalized.
- Anywhere the agent has a directly named artifact (directory, Dockerfile, compose service), it preserves the domain term. Anywhere it has to *describe what something does*, it falls back to plain English.

**Observed:** The Stage-1/2/5 agents have no access to the project's domain glossary. They read structural candidates (file clusters, infra files) and infer English-language process / module names from scratch.

**Expected:** Every project of cloudctlplane's scale has a ubiquitous language already formed in its docs — README headings, "definitions" sections, recurring capitalized terms, glossary tables, the project's own naming for the things it does. The ingest should **derive that glossary and seed every agent's prompt with it**, so process/flow/state names match the team's existing vocabulary rather than re-inventing generic English.

This is exactly the DDD ubiquitous-language principle the toolkit already speaks to in `BOUNDED_CONTEXTS_DESIGN.md` (Evans 2003 / Vernon 2013 / Khononov 2021). Currently the toolkit honors it post-ingest via `hp-propose-bounded-contexts`; the proposal here is to honor it *during* ingest, when entity names are still being formed.

**Proposed fix — a deterministic glossary-extraction prep step that fires before any LLM agent:**

**H.4.a — `hp_toolkit/ingest/glossary_extractor.py`** (new module, no LLM):

Scan documentation sources in the codebase:
- `README.md` (root + per-subdirectory READMEs in `services/`, `packages/`, etc.)
- `docs/**/*.md`
- `proposals/**/*.md`
- `architecture/**/*.md`
- Any other markdown tree the project conventionally uses

Extract candidate glossary terms by deterministic heuristics:
- Bold or italicized capitalized phrases (`**Pulse**` / `*Archi*`)
- Defined terms after a colon or dash (`Pulse: ...` / `Pulse — ...`)
- Recurring CamelCase or capitalized-multi-word phrases (frequency > N across docs)
- Terms inside `<dt>` / `<dfn>` HTML / markdown definition lists
- Headings in glossary-named sections (`## Glossary`, `## Terminology`, `## Concepts`)
- Quoted/back-ticked single words appearing >5 times across the doc tree

Output: `intermediate/glossary.json` keyed by canonical term, with:
- `term`: the canonical form
- `aliases`: case variants, abbreviations
- `definition_excerpt`: the surrounding sentence/paragraph from the source doc
- `source_files`: where the term was found + frequency
- `category` (optional, LLM-curated in a small follow-up pass): `concept` / `actor` / `event` / `artifact` / `process` / `state`

**H.4.b — Optional LLM curation pass** (`hp-ingest-glossary` skill, runs after extraction):

The deterministic extractor produces a candidate list of ~50–200 terms (depends on project doc volume). A small LLM call ranks + categorizes:
- Drop terms that are too generic ("the system", "a service")
- Merge synonyms + variant casings
- Categorize each term
- Pick the top 30–60 canonical entries

Output: `intermediate/glossary.curated.json` — the final glossary that subsequent agents consume.

Cost: small. One LLM call with ~3–5k tokens in (the candidate list) + ~2k out. Maybe ~$0.02 per run.

**H.4.c — Seed every downstream agent's input** with the curated glossary:

Every agent skill (`hp-ingest-boundary`, `hp-ingest-processes`, `hp-ingest-leaf`, `hp-ingest-architect`) gets a new behavior step at the top:

> *"Read `intermediate/glossary.curated.json`. The project has an existing ubiquitous language — when naming terminators / processes / flows / states / modules, prefer terms from this glossary over generic English. If a glossary term matches the entity you're naming, use it (e.g., 'Pulse Stream' not 'event stream'; 'Archi' not 'architecture model'). Flow labels likewise: use 'pulse signals' if 'pulse' is the project's term for what the system observes, not 'telemetry events'."*

The agent prompts also gain a "Domain language faithfulness" item on the discipline list.

**Touch list:**
- `hp_toolkit/ingest/glossary_extractor.py` — new module (H.4.a).
- `scripts/hp_ingest.py` — call glossary extraction after scan, before any LLM agent dispatch.
- `skills/hp-ingest-glossary.md` — new skill for the LLM curation pass (H.4.b). Could be optional if the deterministic extractor alone produces a usable glossary.
- `skills/hp-ingest-boundary.md`, `hp-ingest-processes.md`, `hp-ingest-leaf.md`, `hp-ingest-architect.md` — each gets the glossary-loading behavior step (H.4.c).
- `skills/hp-ingest.md` — orchestrator runbook gains the glossary phase.
- `toolkit/INGEST_DESIGN.md` — note the glossary step in the pipeline diagram.

**Priority:** **high.** This is the second-biggest quality improvement after H.2 (rationale prose). Both share the same diagnosis: the LLM has access to too narrow an input set, so it can't draw on the project's existing vocabulary or "why." H.2 fixes per-entity prose; H.4 fixes naming across every entity. Together they should make ingest output read like a project's own engineering record rather than a generic structural extraction.

**Notes / interactions:**
- **Composes cleanly with H.2 (rationale sources):** the glossary extractor and the rationale-source gatherer both scan READMEs / docs. They can share an underlying file walker. The rationale gatherer focuses on *prose blocks per module*; the glossary extractor focuses on *terms across the whole doc tree*.
- **Composes cleanly with H.3 (system-of-systems):** in a hierarchical ingest, each subsystem's recursive run uses *that subsystem's* localized glossary in addition to the project-wide one. A subsystem named "Prism" might have its own internal terminology (resolvers, stitching, the cache layer) that should be honored when decomposing it.
- **Foreshadows `hp-propose-bounded-contexts`:** the glossary becomes evidence the architect can use later when declaring formal bounded contexts. If the glossary shows two clusters of terminology that rarely co-occur, that's a bounded-context boundary signal.

### H.5 Deployment artifacts under-extracted — the highest-signal architecture sources are scanned shallowly

**Evidence:**
- `architecture_candidates.py` extracts only service *names* from `docker-compose.yml` (one module per service + a single "default network" interconnect). Doesn't read `depends_on:`, `networks:`, `ports:`, `volumes:`, `environment:`, `image:` vs `build:`, or `profiles:`.
- `Dockerfile` extraction captures only `FROM` lines. Doesn't read `EXPOSE` / `ENTRYPOINT` / `CMD` / `WORKDIR` / `HEALTHCHECK` / `ENV`.
- cloudctlplane has *two* deployment models (`bluerockccpd/compose.yml`, `hydra/deployments/agate-test-deployment/compose.yml`, plus `hydra/deployments/aws-basic/compose.yml`). The pipeline treats them as independent candidate files; the architect agent has no notion of "deployment configuration" or per-config interconnect topology.
- Architect agent's emission for `am_prism`: `implemented_by` correctly references the Dockerfile + multiple compose files, but the *relationship structure* between those facts (which service does prism depend on per-deployment, which network it lives on, what env-var URLs it expects) is never captured as IR edges.

**Observed:** Deployment artifacts are the highest-signal architectural sources in any real codebase — they encode the executable, validated architecture. The current extractor produces a candidate *list* of modules + interconnects; it doesn't read the *graph* the compose / k8s files already encode.

**Expected:** The architect agent should arrive at Stage 5 with the deployment topology already substantially decoded from infra files, deterministically, before any LLM judgment fires. Specifically:

1. **Inter-module dependency graph** from `depends_on:` + cross-service env-var references + k8s `Service` selectors.
2. **Network topology** from explicit `networks:` blocks + k8s NetworkPolicies (where to draw interconnects, not just "everything → default network").
3. **External-facing surface** from `ports:` exposures + k8s `LoadBalancer` / `Ingress` (which modules carry inbound terminator flows).
4. **Data store allocations** from `volumes:` + k8s PersistentVolumeClaim mappings (which modules own which data stores).
5. **Module kind / deployment pattern** from `image:` vs `build:` (SaaS / pre-built / in-tree-built — different module kinds in HP).
6. **Deployment variants** when multiple compose / k8s configs exist (cloudctlplane's bluerockccpd + agate-test + aws-basic). Each is a distinct deployment configuration; module set is their union; per-config interconnects + allocations differ. Architect agent should produce *one* module set + *N* deployment-config-specific views.

**Proposed fix:**

**H.5.a — Deep parsers per infra format.** Replace the regex-only extraction in `architecture_candidates.py` with proper format parsers:

- `compose_parser.py` — uses PyYAML to load compose, then walks the typed structure: per-service `depends_on`, `networks`, `ports`, `volumes`, `environment`, `image` vs `build`, `profiles`. Emits *typed candidate edges* (`compose_depends_on` from svc-A to svc-B, `compose_port_exposed` for inbound surface, `compose_volume_mount` for data-store allocation) on top of the candidate modules.
- `dockerfile_parser.py` — reads `EXPOSE` (network surface), `ENTRYPOINT` + `CMD` (process role hint), `HEALTHCHECK` (liveness signal), `ENV` (config-via-env pattern).
- `k8s_parser.py` — uses PyYAML, but typed-walks Deployment + Service + Ingress + NetworkPolicy + PVC, surfacing the relationship graph the k8s manifests already encode.
- `terraform_parser.py` — parse HCL2 (lightweight subset is fine; `python-hcl2` is small) to extract resource graphs + dependencies.

All feed into a richer `intermediate/architecture-candidates.json` with explicit candidate edges, not just candidate modules.

**H.5.b — Deployment-configuration grouping.** New helper recognizes multiple compose / k8s configs and groups them as deployment *variants* rather than independent module sources. For cloudctlplane:

```jsonc
{
  "deployments": {
    "bluerockccpd":           { "source": "bluerockccpd/compose.yml",            "services": [...], "networks": {...} },
    "agate-test-deployment":  { "source": "hydra/deployments/agate-test-.../compose.yml", "services": [...] },
    "aws-basic":              { "source": "hydra/deployments/aws-basic/compose.yml",      "services": [...] }
  },
  "modules": [
    // union of services across all deployments; each module records which deployments include it
    { "candidate_id": "compose-prism", "deployments": ["bluerockccpd", "agate-test-deployment", "aws-basic"], ... }
  ],
  "interconnects_per_deployment": {
    "bluerockccpd":          [...],
    "agate-test-deployment": [...]
  }
}
```

Stage 5 architect agent then knows: "produce *one* module set; allocate processes the same way across deployments; but architecture-interconnects are *per-deployment* (or annotated with which deployments include them)."

**H.5.c — Architect skill updates to consume the richer candidates.** `hp-ingest-architect.md` gains behavior:

- *"For each candidate module: its `image` vs `build` field tells you the `module_kind` — `build:` means in-tree software (your default); `image:` from a public registry means SaaS/managed service (still software but the team doesn't own it); `image:` from an internal registry means pre-built in-tree."*
- *"`compose_depends_on` candidate edges are evidence of inter-module dependency. Translate to architecture flow (typically `carries:` a corresponding requirements flow) or — if the relationship is asymmetric init-order with no data flow — `refines:` for deployment dependency."*
- *"If multiple deployment configurations exist, emit module nodes for the union, then emit interconnects scoped by `deployment_config` if topology differs per-config."*

**Touch list:**
- `hp_toolkit/ingest/compose_parser.py`, `dockerfile_parser.py`, `k8s_parser.py`, `terraform_parser.py` — new format-specific parsers.
- `hp_toolkit/ingest/architecture_candidates.py` — refactor to dispatch to parsers + emit richer candidates.
- `hp_toolkit/ingest/schema.py` — extend `ModuleCandidate` / `InterconnectCandidate` with the new edge-evidence fields + per-deployment annotation.
- `skills/hp-ingest-architect.md` — behavior updates for consuming the richer input + handling deployment variants.
- Possibly `hp_toolkit/ingest/schema.py` — add `deployment_config` field to ArchInterconnect-equivalent IR nodes (would need to mirror in the HP toolkit's `model.py` if we want it in the final dictionary; may or may not be worth — to be decided).

**Priority:** **high.** Deployment artifacts encode the most authoritative architecture data in any deployed system; under-extracting them means the architect agent has to guess at relationships the compose file plainly states. Same general theme as H.2 / H.4: the LLM has too narrow an input set, this time on the *structural* side rather than the prose side.

**Notes / interactions:**

- **Direct lift for H.3 (system-of-systems):** in a hierarchical ingest, deployment artifacts are the canonical SoS-integration boundary. The top-level integration dictionary's level-1 processes correspond to compose services / k8s pods; their interconnects come from the compose network graph. So H.5 + H.3 share substantial mechanism — H.5's deployment-configuration grouping IS the SoS integration view.
- **Composes cleanly with H.2 (rationale prose):** compose comments (`# This service handles X`) + `labels:` blocks are first-class rationale sources the gatherer in H.2.b should also pick up.
- **A new edge kind worth considering:** `compose_depends_on` → likely maps to a new `IREdgeKind.DEPENDS_ON` or recycles `refines:` for init-order dependencies. To decide alongside the `deploys` edge-kind question in section E.
- **Existing `--max-depth` flag (D)** doesn't help here; this is orthogonal — finer file clustering wouldn't have surfaced the compose-graph richness either.

### H.6 User-facing documentation — gold for Stage 1 boundary inference

**Evidence:**
- cloudctlplane terminators currently: `term_ws_client`, `term_query_client`, `term_otlp_client`, `term_cli_operator`, `term_ops_monitor`. Generic protocol-shaped names. The actual project README + docs almost certainly use *role-shaped* names (the user / dev / SRE personas this system serves) that would produce richer terminator labels and richer boundary-flow narratives.
- The current boundary agent reads `scan.json` + `boundary-candidates.json` (HTTP listener / CLI / consumer grep evidence). It does NOT read:
  - `README.md` "Usage" / "Getting Started" / "Quickstart" sections
  - `docs/user-guide*`, `docs/tutorials/`, `docs/howtos/`, `docs/usage/`
  - `examples/` directory with runnable usage examples
  - API spec files: `openapi.yaml`, `swagger.json`, `*.graphql` schema with descriptions
  - Per-service READMEs with usage examples

**Observed:** Stage 1 boundary inference is purely *protocol-shaped* — what HTTP routes exist, what consumers are wired, what CLI entries are defined. The semantic *who and why* of each boundary — *which user persona*, *what they're trying to accomplish*, *what shape the interaction takes from the outside* — is invisible to the agent.

**Expected:** Terminators are *external actors*, defined in HP by what they want from the system. The richest, most architect-friendly source for that information is **user-facing documentation**: tutorials, howtos, user guides, README usage sections, API docs. Those describe the system from outside-in, which is exactly Stage 1's perspective. The boundary agent should read these and use them to:

1. **Name terminators by role, not protocol** — `term_developer` / `term_sre` / `term_telemetry_producer` instead of `term_ws_client` / `term_otlp_client`. Protocol is the *medium*; role is the *terminator*.
2. **Write better terminator descriptions** — the README's "this is for developers who want to query their service graph" line is the exact prose an HP terminator entry should carry.
3. **Identify boundary flows by intent** — a tutorial step "first the developer queries the catalog, then drills into a service" defines two boundary flows by their *purpose*, not just their wire shape.
4. **Capture optional / privileged terminator variants** — docs frequently distinguish "developer" from "admin" from "ops"; that maps to HP's `optional:` flag or to bounded-context-scoped terminators.
5. **Surface unused or rare-use boundary flows** — docs that describe rarely-used endpoints flag them as `optional:` candidates; conversely, docs that emphasize one usage pattern signal it's the primary flow.

**Proposed fix — `hp_toolkit/ingest/user_docs_gatherer.py`** (new deterministic prep step):

Scans for user-facing documentation in known locations:

- `README.md` — extract sections matching headings like `## Usage`, `## Getting Started`, `## Quickstart`, `## Examples`, `## API`, `## Tutorial`.
- `docs/{user-guide,tutorial,howto,how-to,usage,getting-started,quickstart}*/` — full-content harvest.
- `examples/` directory — README + per-example README.
- API specs: `openapi.{yaml,json}`, `swagger.{yaml,json}`, `*.graphql`, `*.proto`, `schema.{yaml,json}`. These are typed boundary surface specs — high-precision input.
- Per-service `README.md` (under `services/`, `packages/`, etc.) — service-level usage sections.

Output: `intermediate/user-docs.json` keyed by candidate boundary file or candidate terminator, containing:
- `usage_excerpts`: paragraphs describing typical usage of this boundary
- `actor_phrases`: extracted noun-phrases for the external party (`the developer`, `an SRE operator`, `the telemetry producer`)
- `intent_phrases`: extracted verb-phrases for what the actor does
- `examples`: code/command examples (kept short — 5–10 lines each)
- `source_files`: where the excerpts came from

The boundary agent's input grows by ~5–20k tokens for a cloudctlplane-scale project (bounded; usage docs are usually small). Architect-friendliness payoff is large.

**`hp-ingest-boundary.md` skill update:**

- New behavior step: *"Read `intermediate/user-docs.json` (if present). For each candidate boundary file, check whether user docs describe its usage; if so, prefer role-named terminators (`term_developer`, `term_sre`) over protocol-named ones (`term_ws_client`, `term_http_client`), and use the docs' own phrasing in terminator descriptions + flow labels."*
- Discipline addition: *"Terminators are external **roles**, not external **protocols**. If two protocol-shaped endpoints serve the same role, collapse to one terminator with multiple flows. The user docs are the canonical source for role identification."*

**Touch list:**
- `hp_toolkit/ingest/user_docs_gatherer.py` — new helper.
- `scripts/hp_ingest.py` — call gatherer after scan, before boundary candidates step.
- `skills/hp-ingest-boundary.md` — read `user-docs.json` + use as naming/description source.
- `skills/hp-ingest.md` (orchestrator runbook) — new phase 0.5: user-docs gathering.

**Priority:** **high.** Same input-too-narrow theme as H.2 / H.4 / H.5; specific application to Stage 1 boundary which produces the user-facing top-of-pyramid HP artifacts (Context Diagram, terminator list). Architect-quality lift from naming terminators by role rather than protocol is large.

**Notes / interactions:**

- **Shared file walker with H.2 (rationale) + H.4 (glossary):** all three scan documentation; they should share a `docs_walker.py` that enumerates doc-like files once. Each downstream extractor (rationale-source / glossary / user-docs) consumes the file list with its own extraction rules.
- **Cross-stage value:** user docs can also inform Stage 2 (usage tutorials often walk through internal processes step-by-step, hinting at process boundaries) and Stage 4 (example bodies describe PSPEC transformation in user-facing terms). Initial scope is Stage 1; expansion to Stage 2/4 is a follow-up if signal is strong.
- **Composes with H.4 (glossary):** the user docs are also a prime glossary source. Single doc walker; one harvest per extractor.
- **OpenAPI / GraphQL schemas are typed inputs** — could be parsed structurally (each operation = candidate boundary flow with typed inputs + outputs). Stretch goal in `user_docs_gatherer.py`.

**Pattern emerging across H.2 + H.4 + H.5 + H.6:** every finding so far points at *the agents' input is too narrow*. The codebase contains far more architectural signal than the deterministic prep currently surfaces. **The unifying fix is to systematically extend each agent's input set with the appropriate source-bundle:**

| Source | Read by | Feeds |
|---|---|---|
| Code structure + imports | scan + boundary/process/leaf agents | structural extraction (current) |
| Infra files | architecture_candidates + architect | Stage 5 module/interconnect topology (H.5 expansion) |
| Service READMEs + module docstrings + compose comments | rationale gatherer + every spec-writing agent | rationale prose for AMS/AIS/PSPEC (H.2) |
| Whole-project docs | glossary extractor + every naming agent | ubiquitous-language faithfulness in naming (H.4) |
| User-facing docs + API specs | user-docs gatherer + boundary agent | role-shaped terminators + intent-shaped flows (H.6) |

This collectively becomes the "agents read the project's documentation, not just its code structure" tuning theme. Worth surfacing in the eventual commit message for whichever single commit (or commit-set) lands H.2 + H.4 + H.5 + H.6.

### H.7 Purpose-built testbeds — executable specifications hp-ingest currently ignores or misclassifies

**Evidence:**
- cloudctlplane includes `agent-gym/` — a purpose-built testbed specifically written to exercise the hydra/odyssey system. It's not unit-test noise; it's an architectural asset:
  - **Scenarios** that walk through operational use cases ("when X happens, system does Y")
  - **Fixtures** that document environment + deployment expectations
  - **System-spin-up scripts** (likely its own compose/k8s setup) that confirm topology
  - **Assertions** that document expected behaviors + invariants
  - **Test data** that documents the shapes flowing through the system
- Current ingest: `agent-gym/` doesn't match any path filter in `significance.py` (no `tests/` prefix, no `_test.*` suffix), so it's NOT dropped. But its files also get *no special treatment* — they get classified by the same generic role-hint rules as production code, blended into Stage-2 clusters, and (likely) inflate the leaf-analyzer pass with what looks like noise.
- The Stage-5 architect agent's allocations almost certainly include testbed-side modules as if they were production-deployable units. Worth verifying once Kevin reviews `architecture_modules:` in `dictionary.yaml`.

**Observed:** Testbed code is treated indistinguishably from production code. Its unique signal — operational scenarios, deployment expectations, behavioral assertions — is invisible to every agent. Worse: testbed files inflate process clusters + architecture-module candidates, producing spurious entities.

**Expected:** Testbeds are a *separate input class*: not production architecture, but **executable specifications of how production architecture is meant to operate**. Architecturally they should:

1. **Inform Stage 1** — scenario titles + setup code describe operational use cases from the outside. Direct boundary-intent signal.
2. **Inform Stage 2** — scenario walk-throughs describe what processes do step-by-step. Direct process-purpose signal.
3. **Inform Stage 4 (PSPECs)** — assertions describe expected transformation behavior in the testbed's vocabulary. Direct PSPEC-content signal.
4. **Inform Stage 5** — testbed spin-up scripts (compose / k8s / Helm) are a *third deployment configuration* alongside prod deployments. Direct topology evidence.
5. **Inform modernization #21 (budgets)** — performance-test parameters document expected scale / latency / throughput. Direct budget-seed signal (though out of v1 scope per locked Q3).
6. **NOT** be treated as production architecture — testbed modules shouldn't appear in the dictionary's `architecture_modules:` section; testbed processes shouldn't appear in `entities:` as if they were system processes.

**Proposed fix:**

**H.7.a — Detect purpose-built testbeds** (new helper `hp_toolkit/ingest/testbed_detector.py`):

Heuristics to identify a directory as a purpose-built testbed (not a unit-test directory):

- Top-level position (`<repo>/<dir>/` not `<repo>/services/<svc>/tests/`)
- Has its own `README.md` or `docs/` describing the testbed's purpose
- Has its own `compose.yml` / `Dockerfile` / `k8s/` (spins up the system being tested)
- Imports across multiple production services (not isolated to one)
- Filename + content patterns matching scenario-shaped tests (`scenario_*`, `e2e_*`, `integration_*`, `acceptance_*`)
- Markers like `pytest.mark.integration`, `pytest.mark.e2e`, `@pytest.mark.slow`, `tox -e integration`
- Has `fixtures/` or `data/` subdirectories with non-trivial setup data
- Long-running indication: README or CI config marks it as separate from unit tests

When ≥3 of these match, flag the directory as a `testbed` in scan.json with a new `is_testbed: true` field on the FileEntry (or a new top-level `testbeds: []` section in the scan).

**H.7.b — Mark testbed files in scan + exclude from production candidate pools:**

- `scan.json` files inside a detected testbed get `is_testbed: true` + a non-significant flag for *production-architecture* purposes (they don't compete for production process / module candidacy).
- `process_candidates.py` skips testbed files when clustering production processes.
- `architecture_candidates.py` skips testbed `Dockerfile` / `compose.yml` / `k8s/` files when surfacing production deployment modules (or handles them as a distinct deployment-configuration class — see Notes below).

**H.7.c — Mine testbeds as a separate input source:**

A new gatherer (`hp_toolkit/ingest/testbed_mining.py`) extracts per-testbed:

- `scenarios`: scenario file → title + docstring + sequence of high-level steps
- `fixtures`: fixture name → what it sets up (parsed from fixture function bodies / YAML / etc.)
- `assertions`: per-scenario top assertions in plain text (the test's check of "this should be true at the end")
- `system_topology`: parsed from testbed's own compose / k8s files (which production services participate, what extra test scaffolding is added)
- `setup_data`: example payloads / inputs the testbed feeds the system

Output: `intermediate/testbeds.json` keyed by detected testbed name.

**H.7.d — Feed testbed signal to relevant agents:**

- `hp-ingest-boundary.md`: *"Read `intermediate/testbeds.json`. Each testbed scenario describes a real operational use case from the outside; use these to validate terminator + boundary-flow names against actual usage patterns. If `intermediate/testbeds.json` references a terminator pattern your boundary candidates don't cover, surface it as a possible missing terminator."*
- `hp-ingest-processes.md`: scenario walk-throughs are evidence for process boundaries + needs_cspec flagging.
- `hp-ingest-leaf.md` (PSPEC mode): assertions describe expected transformation outcomes; use them to validate / enrich PSPEC bodies.
- `hp-ingest-architect.md`: testbed topology is evidence of how the system *is meant to be operated*; cross-check production-deployment inference against testbed-spin-up scripts to catch missing modules or wrong allocations.

**Touch list:**

- `hp_toolkit/ingest/testbed_detector.py` — new helper (H.7.a).
- `hp_toolkit/ingest/testbed_mining.py` — new gatherer (H.7.c).
- `hp_toolkit/ingest/scan.py` + `schema.py` — add `is_testbed` field on FileEntry; optionally a `testbeds: list[TestbedInfo]` section.
- `hp_toolkit/ingest/process_candidates.py` + `architecture_candidates.py` — exclude testbed files from production candidate pools (H.7.b).
- `skills/hp-ingest-{boundary,processes,leaf,architect}.md` — load + use `intermediate/testbeds.json` (H.7.d).
- `skills/hp-ingest.md` (orchestrator) — new phase: testbed detection + mining alongside scan.

**Priority:** **high.** Same input-set expansion theme as H.2 / H.4 / H.5 / H.6 — and arguably higher *quality lift* than any of them, because testbeds are *executable* specifications: they encode not just what the system does but what it's *expected to do*, in a form that's been validated by execution. Plus they're written by the same team using the project's vocabulary, so they're glossary-rich (H.4) and intent-rich (H.6) by definition.

**Notes / interactions:**

- **Composes with H.5 (deployment artifacts):** testbed compose / k8s files are *additional deployment configurations*. cloudctlplane currently has 3 production-side compose files (bluerockccpd, agate-test-deployment, aws-basic); agent-gym likely adds a 4th (testbed-side). H.5's deployment-configuration grouping should naturally include this with a `kind: testbed` annotation.
- **Composes with H.4 (glossary):** testbed code uses the project's domain vocabulary extensively (test names, fixture names, assertion messages). The glossary extractor should mine testbeds heavily — they're a high-density vocabulary source.
- **Composes with H.6 (user docs):** testbed scenario docstrings often double as usage documentation. Same shared `docs_walker.py` from the H.6 synthesis can pick up scenario files in addition to README sections.
- **Significance filter discipline:** the unit-test filter patterns in `significance.py` stay — they correctly drop `services/X/tests/` directories. The testbed detector adds *recognition* of a separate category, not a filter relaxation.

**Updated synthesis table** (extending the table at the end of H.6):

| Source | Read by | Feeds | Captured in |
|---|---|---|---|
| Code structure + imports | scan + boundary/process/leaf agents | structural extraction | current |
| Infra files | architecture_candidates + architect | Stage 5 module/interconnect topology | H.5 |
| Service READMEs + module docstrings + compose comments | rationale gatherer + every spec-writing agent | rationale prose for AMS/AIS/PSPEC | H.2 |
| Whole-project docs | glossary extractor + every naming agent | ubiquitous-language faithfulness in naming | H.4 |
| User-facing docs + API specs | user-docs gatherer + boundary agent | role-shaped terminators + intent-shaped flows | H.6 |
| **Purpose-built testbeds** | testbed_detector + testbed_mining + every agent | executable-specification cross-validation across all stages | **H.7** |

### H.8 External context solicitation — QA plans, ADRs, requirements docs that don't live in the repo

**Evidence:**
- Kevin's note: QA test plans for cloudctlplane exist *outside* the repo (Confluence, Notion, Google Docs, or similar). They aren't surfaced by any code-scan strategy and won't be — they're not files hp-ingest can reach.
- Generalizes: every non-trivial system has architectural context that lives outside the source tree. Common categories:
  - **QA test plans** — what the system is supposed to do, from the test-engineer's perspective. Strongest single signal for Stage 1 boundary intent + Stage 4 PSPEC outcome expectations.
  - **Architecture review documents** — wiki / drive design docs from prior architecture passes. Direct rationale + glossary source.
  - **ADR archives outside the repo** — many teams keep ADRs in Confluence rather than `docs/adrs/`. Capturing them seeds modernization #10 work post-ingest.
  - **Stakeholder requirements documents** — what the system *should* do, vs what it does. The Stage 1 outside-in perspective at its most authoritative.
  - **Operational runbooks** — how the system *runs in production*, often kept in ops wikis. Strong signal for modernization #33 (runbook) work post-ingest.
  - **Domain glossaries maintained outside the repo** — Confluence-hosted "Term of the Day" pages, brand-vocabulary documents.
  - **Past ADRs / design memos / postmortems** — historical decisions + their consequences. Anchors `hp-propose-architecture` form-based review post-ingest.

**Observed:** Zero mechanism for any of this. hp-ingest's universe is the codebase directory; everything else is invisible.

**Expected:** hp-ingest should explicitly *solicit* external context from the user at the start of the run (and optionally at stage boundaries), provide a structured drop point for that context, and feed it to the appropriate agents the same way internal docs would feed them.

**Proposed fix:**

**H.8.a — External-context solicitation in the orchestrator skill.** New phase 0.5 in `hp-ingest.md` (after scan, before Stage 1):

The orchestrator asks the user (a single message with a structured menu):

> *"hp-ingest works best when it has access to the project's architectural context, not just its code. The repo scan picked up `README.md`, `docs/`, and `agent-gym/` (a detected testbed). Are there additional context sources outside the repo that would help? Common categories:*
> - *QA test plans / acceptance criteria*
> - *Architecture decision records (ADRs) in a wiki*
> - *Design docs / proposals in shared drives*
> - *Stakeholder requirements documents*
> - *Operational runbooks*
> - *Domain glossary / vocabulary documents*
> - *Postmortems / incident reports informing architecture*
> 
> *If yes: paste content (or point at a path on the local filesystem) and tell me which category each piece falls into. I'll add them to `intermediate/external-context/` and feed them to the relevant stages. If nothing applies, reply 'continue' and I'll proceed with code-only context."*

**H.8.b — Structured drop directory `<project-dir>/external-context/`:**

Either auto-created or user-managed. Convention:

```
external-context/
├── qa-test-plans/
│   ├── plan-001-graphql-bff.md           (pasted by user)
│   └── plan-002-pulse-ingest.md
├── adrs/
│   ├── confluence-export-2026-03.md
│   └── design-prism-bff-2026-04.md
├── requirements/
│   └── stakeholder-brief-2026.md
├── runbooks/
│   └── prism-restart-procedure.md
├── glossary/
│   └── ops-vocabulary.md
└── manifest.json                          (auto-managed: maps each file to its category)
```

User pastes / copies content; the orchestrator (or a small helper script) maintains `manifest.json` so downstream agents know which file belongs to which category.

**H.8.c — Stage-aware feeding.** Each agent's skill markdown gains:

- **`hp-ingest-boundary.md`**: read `external-context/qa-test-plans/*` + `external-context/requirements/*` — these are the strongest outside-in signal for terminator + boundary-flow inference.
- **`hp-ingest-processes.md`**: read `external-context/qa-test-plans/*` (per-process acceptance criteria) + `external-context/adrs/*` (process-boundary decisions).
- **`hp-ingest-leaf.md`** (PSPEC mode): read QA plan assertions relevant to the leaf process; use them as expected-outcome guidance for the PSPEC transformation body.
- **`hp-ingest-architect.md`**: read `external-context/adrs/*` + `external-context/design-docs/*` — these are the authoritative source for Stage 5 module + interconnect rationale.
- **All naming agents**: glossary extractor (H.4) also scans `external-context/glossary/*` for terms.

**H.8.d — Continuous availability (composes with F.3 hints):**

The user can drop files into `external-context/` *at any time before the relevant stage fires*. This is the same lifecycle as F.3 hints — drop a file, the next agent reads it. Could share the same loader infrastructure; the directories are siblings (`intermediate/hints/` for guidance, `external-context/` for evidence).

**H.8.e — Persistence + audit trail:**

`external-context/` is project-local — gitignored by default (per the existing `examples/**/*.generated.*` pattern, extended), but the user can opt-in to commit it. The IR records `provenance.external_context_used: ["external-context/qa-test-plans/plan-001-graphql-bff.md", ...]` on every node that drew on external context. Architect can audit "which entities derived from this QA plan" later.

**Touch list:**

- `skills/hp-ingest.md` — phase 0.5 (solicitation) + stage-aware reminders to load external-context.
- `hp_toolkit/ingest/external_context.py` — new helper: manage the directory + manifest, expose category-filtered file lists to each agent.
- `skills/hp-ingest-{boundary,processes,leaf,architect}.md` — each agent reads its category-filtered slice.
- `.gitignore` — extend `examples/**/*.generated.*` rule to also ignore `examples/**/external-context/` by default (with override possible).
- `hp_toolkit/ingest/schema.py` — `Provenance` gains optional `external_context_used: list[str]` field.

**Priority:** **medium.** Mechanism is small + general; pattern fits the existing input-bundle approach (sibling to `intermediate/hints/` from F.3). The payoff depends entirely on whether the user has external context to provide — for cloudctlplane, Kevin says yes; for many other targets, no. Worth implementing so the *mechanism* is available; users without external context don't pay any cost.

**Notes / interactions:**

- **Composes directly with F.3 (bidirectional hints):** `external-context/` for *evidence* + `intermediate/hints/` for *guidance*. Both are file-drop directories with similar loaders; should share one helper module. Naming distinguishes intent: evidence vs steering.
- **Composes with H.2 / H.4 / H.6:** external-context categories overlap with the file-scan extractors. external-context/glossary/* feeds H.4 alongside repo docs; external-context/adrs/* feeds the rationale gatherer alongside service READMEs. Same `docs_walker.py` consumes external-context directories as additional inputs.
- **Token cost rises proportionally** to what the user pastes. Heavy paste (full QA test plan suite) could add 50–100k tokens; minimal paste (one stakeholder brief) ~10k. Each user can scale to taste.
- **The solicitation interaction is itself an architect-in-the-loop pattern** — fits naturally with F.3.b (stage-boundary pauses). The phase-0.5 prompt is just F.3.b applied at the start.

### H.9 Domain-specific Python prep — generic engine + LLM-discovered profiles

**Finding raised:** 2026-05-25 — surfaced reviewing the Branch 4 (embedded-firmware) work. The deterministic prep scripts in [`hp_toolkit/ingest/`](hp_toolkit/ingest/) (`boundary_candidates.py`, `embedded_arch_extractor.py`, `role_classifier.py`, `state_machine_detector.py`, etc.) have substantial *domain-specific knowledge baked in*. Branch 1–3 was implicitly cloud-shaped (HTTP listeners, file clusters, Docker/k8s/compose); Branch 4 doubled the vocabulary to include firmware (FreeRTOS / NuttX / Zephyr / ChibiOS / Mbed / ESP-IDF / Arduino / AUTOSAR / STM32 HAL / Micro-ROS / ROS 2 / MAVLink / uORB / DDS + hardware peripherals + `px4_add_module` + `.ioc` + `.px4board` + linker scripts).

Each new dogfood domain — scientific simulation, data pipeline, mobile app, robotics-other-than-PX4, etc. — will hit the same wall: add patterns to the Python, ship a branch, dogfood, repeat. **That doesn't scale.**

**Proposed direction.** Refactor the prep into three layers:

| Layer | What it owns | Hardcoded or data? |
|---|---|---|
| HP semantic categories | `boundary` / `pure-logic` / `state-machine` / `data-store` / `infra` / `config` — methodology vocabulary | **Hardcoded** (these are HP, not domain) |
| Domain-specific patterns | Which file shapes / regexes / manifest names / build-system idioms / framework signatures map into each HP category for *this* repo | **Becomes data** (a profile) |
| Scanner engine | The Python that walks files + applies patterns + emits candidates | **Becomes generic** (engine reads the profile) |

A new pipeline stage — **Stage 0a: domain reconnaissance** — would run before the deterministic scan. An LLM agent reads top-level manifests + README + a sample of file headers + directory shape, then emits a `domain-profile.yaml` that parameterizes the scanner. Token spend is bounded (~50–100k tokens for one shot) and it's a one-time-per-repo cost (cache by repo signature).

**Why this matters.** Branch 4 is effectively a checked-in "embedded firmware" domain profile, just compiled into Python rather than stored as data. The cloud patterns are similarly a profile, just older. Making the profile *data* means new domains add a checked-in YAML (or trigger LLM discovery), not a new branch of Python edits. This is how production scanners work — Tree-sitter language grammars, Semgrep rule packs, ESLint plugins.

**Open questions to lock in a follow-up design doc:**

- [ ] **What does the LLM emit?** Narrow (enum sets per HP category), medium (declarative profile with patterns + framework signatures + manifest paths), or wide (actual regex/scanner code — most general, most risky)?
- [ ] **Community-contributed profiles vs always-discovered?** Well-known domains (PX4, ROS, FastAPI, Django, Rails) get checked-in `toolkit/domain-profiles/*.yaml`. Unknown domains trigger LLM discovery. Reduces token cost + variance for common cases; preserves generality for novel ones.
- [ ] **Caching + persistence.** Keyed by repo signature (Git remote + top-level manifest hash?). Explicit `--rediscover` flag forces re-run.
- [ ] **Validation.** LLM-discovered patterns can be wrong. Current hand-tuned patterns survived dogfood validation; LLM-generated ones haven't. Mitigation: reviewer agent at pipeline end gets the profile in context and flags pattern misses.

**Proposed handling:** **Defer to a follow-up design doc + branch** (e.g., `DOMAIN_PROFILE_DESIGN.md` + `kg/hp-ingest-domain-profiles`). Same form-based-proposal pattern as the prior arcs (HIERARCHICAL / EMBEDDED). Trigger to actually spawn the doc: **the third concrete domain target** (scientific simulation? data pipeline? mobile? robotics?) — at that point the cost of adding patterns in-code exceeds the refactor cost, and we have enough triangulation to know what the abstraction should look like.

**Priority for tuning branch:** **none** (architectural pivot — too big for this branch). **Priority for follow-up design:** **medium-high** when triggered. Without this, the Python prep ossifies around the two domains we've seen, and the third-domain dogfood will be painful enough to make the refactor undeniable.

**Composes with other findings:**
- **H.4 (glossary):** the glossary extractor's vocabulary is itself partly domain-shaped. A generic glossary extractor + domain-profile vocabulary list is the cleaner factoring.
- **H.5 (deployment artifacts):** compose/k8s/dockerfile parsers are cloud-domain-specific. The firmware analog (CMake / `.ioc` / `.px4board`) is in `embedded_arch_extractor.py`. Same pattern: deployment-artifact parser is generic, the *which artifacts to parse* is in the domain profile.

### H.10 *(placeholder — add as you find more)*

*(... etc — add as many as needed)*

---

## Branch organization

Originally scoped as a single tuning branch. After review (8 H-findings, several substantial), splitting into **three branches**, each with a coherent narrative + bounded scope. Same pattern as prior arcs (modernization / portal / brownfield-ingest).

### Branch 1 — `kg/hp-ingest-dogfood-tuning` ✅ *(merged 2026-05-24 — `Tuning Commit T1`–`T4`)*

**Theme:** small fixes from the dogfood signal. Classifier sharpening, filter gaps, resume support, agent prompt tightening, the DFD-refinement bug. Cheap, foundational; should land first because better candidates feed the input-expansion work in Branch 2.

**Scope:** A · B · C · D · E.1 · E.3 · F.1 · F.2 · G.1–G.4 · H.1 — all landed.

### Branch 2 — `kg/hp-ingest-input-expansion` ✅ *(in-flight; T5–T10 landed on this branch)*

**Theme:** *"the agents read the project's documentation, not just its code structure."* Shared `docs_walker.py` infrastructure + per-source extractors (rationale, glossary, user-docs, testbed-miner) + deep deployment parsers + external-context solicitation + bidirectional hints mechanism (since hints + external-context share file-drop infrastructure).

**Scope:** F.3.a · H.2 · H.4 · H.5 · H.6 · H.7 · H.8.a/b/c — all landed. **Scope additions during implementation:** Makefile + Justfile recipe parser (`recipe_parser.py`; landed in T9 per Kevin's question during T8). **Deferred from this branch:** `terraform_parser.py` (H.5.a's 4th parser; the regex extractor still surfaces .tf as `infra_resource` modules — re-evaluate when a re-ingest confirms terraform-resource typing carries architect-decision value); F.3.b explicit stage-boundary pauses + F.3.c confidence-driven auto-pause (kept out of this branch as a follow-up if dogfood signal warrants).

### Branch 3 — `kg/hp-ingest-hierarchical` ✅ *(in-flight; T11–T14 landed; see [HIERARCHICAL_INGEST_DESIGN.md](HIERARCHICAL_INGEST_DESIGN.md))*

**Theme:** recursive system-of-systems decomposition. Pipeline shape change: Stage 2 becomes recursive; orchestrator walks a tree.

**Scope:** H.3 only — Option X (Hierarchical single-dictionary) per locked Q1. Option Y (SoS multi-project) deferred until a multi-repo target appears.

---

## Proposed implementation order — Branch 1 (this branch)

Four commits on `kg/hp-ingest-dogfood-tuning`. Each verifiable in isolation.

### Commit T1 — Cheap classifier + filter fixes
- A — `data-store` import-context regex.
- B — dot-file skip pattern.
- D — `--max-depth` flag (already-modified `process_candidates.py` lands here).
- E.1 + E.3 — alias-table additions (`deploys → refines`; `depends_on_library` dropped).
- H.1.2 (validator warning half of H.1) — `merge_graph.py` flags boundary flows missing refinements.

**Verification:** re-run scanner + candidate prep against cloudctlplane (no LLM cost) — classifier output tightens; merge-report warns on unrefined boundary flows.

### Commit T2 — Progress log + resume support
- F.1 — `progress_log.py` helper + integration into all Python scripts.
- F.1 (skill half) — START / DONE log lines in each subagent skill markdown.
- F.2 — `--resume` skip logic in CLI + orchestrator skill.

**Verification:** delete one `leaf-*.json` from a completed run; `--resume` dispatches only the missing leaf. `tail -f intermediate/progress.log` shows live progress during a fresh run.

### Commit T3 — Tuning guide + agent prompt fixes
- C — tuning guide section in INGEST_DESIGN.md + `--min-pure-logic` CLI flag.
- G.1 (terminator parent style) — `hp-ingest-boundary.md` tightening.
- G.2 (state nodes missing parent) — `hp-ingest-leaf.md` CSPEC-mode tightening.
- G.3 (architecture flows not carried) — `hp-ingest-architect.md` + optional deterministic post-pass in `merge_graph.py`.
- G.4 (low-confidence audit) — `hp-ingest-review.md` discipline note ("low-confidence is a signal, not a bug").
- H.1.1 + H.1.3 (the agent-prompt halves of H.1) — `hp-ingest-processes.md` checklist + `hp-ingest-review.md` repair checklist.

**Verification:** re-run hp-ingest on cloudctlplane (full LLM run, cheaper now thanks to T1). New `ingest-report.md` should have ≤10 warnings; level-1 DFD renders.

### Commit T4 — Doc catch-up
- Update `toolkit/INGEST_DESIGN.md` with lived findings (Branch 1 only — Branches 2 + 3 update their respective docs).
- Update `toolkit/README.md` if any CLI flags shifted (`--min-pure-logic`, `--max-depth`, `--resume`).
- Update `toolkit/skills/README.md` if any skill behavior changed.

Same pattern as prior arc catch-ups.

---

## Implementation order — Branch 2 ✅ *(landed in 6 commits, T5–T10)*

- **T5** ✅ — Shared `docs_walker.py` + `external-context/` + `intermediate/hints/` infrastructure (F.3.a + H.8.b). Skill markdowns teach every agent to read its stage's slice.
- **T6** ✅ — Rationale gatherer (`rationale_sources.py`) + emitter fix to surface `provenance.rationale` + LLM-emitted prose extras (H.2.a/b) + skill prompt tightening to demand `design_rationale` / `design_justification` / `required_constraints` / PSPEC `comments` (H.2.c).
- **T7** ✅ — Deterministic `glossary_extractor.py` + optional `hp-ingest-glossary` curator skill + boundary/processes/leaf/architect read `glossary.curated.json` (H.4.a/b/c).
- **T8** ✅ — Deep deployment parsers: `compose_parser.py` + `dockerfile_parser.py` + `k8s_parser.py` with typed `CandidateEdge` rows (`compose_depends_on` / `compose_port_exposed` / `compose_volume_mount` / `dockerfile_exposes` / `k8s_service_selector` / `k8s_ingress_target`) + `DeploymentConfig` grouping (H.5.a/b). `terraform_parser.py` deferred.
- **T9** ✅ — `user_docs_gatherer.py` (H.6) + `testbed_miner.py` (H.7) + `recipe_parser.py` (Makefile / Justfile; T8 followup) + H.8.a orchestrator solicitation phase.
- **T10** ✅ — Doc catch-up across INGEST_DESIGN.md + this design doc + README + skills/README.

---

## Implementation order — Branch 3 ✅ *(landed in 4 commits, T11–T14)*

Design locked in [HIERARCHICAL_INGEST_DESIGN.md](HIERARCHICAL_INGEST_DESIGN.md) (2026-05-25). See that doc for the full per-commit detail; one-line summary here:

- **T11** ✅ — `recursion.py` helpers (should_recurse, scope_for_subsystem, derive_level, is_leaf_process) + validator extensions (allow `parent: proc_X` on processes; non-leaf process can't carry CSPEC/PSPEC; flow-refinement-chain rule) + emitter (derive level from parent chain; suppress non-leaf process specs).
- **T12** ✅ — Orchestrator recursion loop: `python -m hp_toolkit.ingest.recursion` CLI + `prepare_subsystem_recursions` helper + `RECURSE_DECISION` / `RECURSE_INTO` progress.log events + orchestrator skill Phase 2-recurse + processes skill recursive-mode discipline.
- **T13** ✅ — Renderer level-N generalization (mermaid + d2 + cytoscape relative `child_level = parent.level + 1`) + per-parent DFD walker in `render_project.py` writing `02-decomp/<slug>/dfd.generated.*` + sidebar nesting under Stage 2 + architect skill leaves-only allocation rule.
- **T14** ✅ — Doc catch-up: this section + HIERARCHICAL_INGEST_DESIGN status notes + INGEST_DESIGN file-tree + README skill table.

---

## Open questions

Mark up here once Kevin's review surfaces specifics.

### Q1. `deploys` edge kind — alias-only or first-class?

- [x] **Alias-only** (recommended for this branch): `deploys → refines` in `_EDGE_KIND_ALIASES`. The IR records `refines`. Easy fix; preserves vocabulary discipline.
- [ ] **First-class** (heavier): add `IREdgeKind.DEPLOYS`, update validator + renderer + emit_dictionary. New HP vocabulary.
- [ ] **Defer**: keep current behavior (review agent repairs case-by-case).

I lean alias-only for now. Promote to first-class only if `deploys` shows up in 2+ dogfood targets — that would be evidence it's a recurring cloud-native concept worth naming.

### Q2. Resume verbosity — quiet skip vs. loud skip?

- [ ] **Quiet** — `[resume] skipping stage 1 (boundary.json fresh)` once per skipped stage.
- [x] **Loud** — same + summary stats (`5 terminators / 8 flows from prior run`).

I lean loud — small extra output; large reassurance value.

### Q3. Should progress log replace stderr-output OR augment it?

- [x] **Augment** (recommended): scripts still print to stderr as today; progress.log adds the structured timestamped log alongside.
- [ ] **Replace**: scripts redirect their stderr to progress.log; console stays clean.

I lean augment. The console output is human-readable; progress.log is machine-readable. Both have a role.

### Q4. H.5 deployment-configuration modeling — informational vs first-class?

cloudctlplane has 3+ compose configurations (bluerockccpd, agate-test-deployment, aws-basic) + likely a 4th from agent-gym (testbed-side). Each represents a distinct deployment topology. How should hp-ingest represent them in the IR + dictionary?

- [x] **Informational-only (recommended for Branch 2):** record per-deployment compose evidence on each module's `provenance` + `implemented_by`; no schema extension. Architect distinguishes deployment-specific behavior in the `hp-propose-architecture` form-based pass post-ingest.
- [ ] **First-class** — add `deployment_config:` annotation on `ArchInterconnect` (or a new `deployment_configurations:` top-level section in dictionary.yaml). Requires extending `hp_toolkit/model.py` schema + validator + renderer. Bigger lift; not in Branch 2 scope.
- [ ] **Defer** — punt the modeling question to a future schema-discussion design doc.

I lean **informational-only** for Branch 2. The schema extension is meaningful enough to warrant its own design conversation; informational-only captures the evidence today without locking the schema shape.

### Q5. H.7 testbed detection — opt-in or always-on?

The testbed detector heuristic looks at top-level directory naming + `compose.yml` presence + multi-service imports + test-shaped filenames. False-positive risk exists (a directory could accidentally trip the heuristic).

- [ ] **Always-on default** — every ingest runs testbed detection; if found, files get `is_testbed: true` + excluded from production candidate pools + mined separately. Most ergonomic for users; risk is false positives misclassifying a real subsystem as a testbed.
- [ ] **Opt-in flag** — `--detect-testbeds` flag required to run detection. Safer; requires user awareness.
- [x] **Always-on with override** — default on; `--no-testbed-detect` to disable. Middle ground.

I lean **always-on with override**. False positives surface in the testbed-detection summary at scan-end; user can re-run with override if needed.

### Q6. H.8 external-context solicitation — always ask, flag-gated, or auto-detect?

The phase-0.5 prompt asking the user for external context adds an interaction every run. Some users will have nothing to provide.

- [ ] **Always ask upfront** — every ingest pauses for the solicitation prompt. Most thorough; ensures the question is never missed; adds friction for "I have nothing" users.
- [ ] **Flag-gated** — `--external-context` flag triggers solicitation; default ingest skips it. User must know to ask. Less friction; lower discoverability.
- [x] **Auto-detect with fallback ask** — if `<project-dir>/external-context/` already exists, use its contents without prompting; if absent, ask once at phase 0.5. Smart default; supports both one-shot and iterative ingest workflows.

I lean **auto-detect with fallback ask**. Users who pre-populate the directory (or are iterating on a re-ingest) don't get re-prompted; first-time users see the prompt once.

---

## Notes

- Schema vocabulary expansion (E.2) is intentionally **out of scope** for this branch. If Kevin reviewing cloudctlplane decides `deploys` deserves to be first-class, that lands as a follow-up design doc (`SCHEMA_V2_DESIGN.md` or similar).
- No new ingest stages, no LLM-vs-Python boundary changes, no agent-topology changes. This branch is polish, not architecture.
- The H-findings slot is meant to be filled as Kevin reviews — each one a small targeted improvement. The doc isn't meant to be exhaustive on day one.

---

*Drafted 2026-05-24 on `kg/hp-ingest-dogfood-tuning`. Pattern matches the prior design docs.*
