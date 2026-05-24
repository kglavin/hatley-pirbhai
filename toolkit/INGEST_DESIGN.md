# Brownfield Ingest (hp-ingest) — design

## ✅ Status: Locked 2026-05-23

All 5 open questions resolved with recommended defaults:
- **Q1.** First demo target after hatley-pirbhai self-ingest: **cloudctlplane**.
- **Q2.** PSPEC granularity: **per-process-cluster**.
- **Q3.** hp-ingest proposes trust zones: **no, defer entirely** to `hp-propose-architecture`.
- **Q4.** Brownfield-with-existing-dictionary support in v1: **greenfield-only**; `--incremental` covers code-change reconciliation.
- **Q5.** Confidence + provenance on every IR node: **yes, every node**.

**Status:** locked.
**Branch:** `kg/brownfield-ingest`.
**Spawning context:** the original "next thing" deferred from the brownfield review back in Apr–May 2026. We've since shipped the modernization layer + the project portal, so hp-ingest now lands on a much richer toolkit. The design below incorporates patterns lifted from a focused review of [Understand-Anything](https://github.com/Lum1104/Understand-Anything) (see *Provenance* below).

## Goal

Take a brownfield codebase → produce a `dictionary.yaml` that the rest of the HP toolkit (validate, render, status, portal, PDF) can consume. The output should be:

1. **Architecturally meaningful** — entities are HP entities (terminators, processes, data stores, state-rich bubbles needing CSPECs, leaf processes needing PSPECs, architecture modules + interconnects), not "every function in the codebase."
2. **Reviewable by an architect** — every inferred entity has a confidence score + a provenance list (`implemented_by: ["src/foo.py", "src/bar.py"]`) so a human can sanity-check the inference and override.
3. **Incremental** — re-ingesting after a code change should produce a sensible diff, not blow away everything. Keyed off `gitCommitHash` in the project meta.
4. **Composable with the existing modernization skills** — hp-ingest produces the core 5 stages; `hp-propose-observability` / `hp-propose-slos` / `hp-capture-adr` / etc. enrich after.

## Why this is the right shape

Three insights from the [Understand-Anything](https://github.com/Lum1104/Understand-Anything) review (full notes in conversation log; key data sample at `understand-anything-plugin/packages/dashboard/public/knowledge-graph.json` — UA's self-analysis: 97 nodes, 183 edges, 7 layers, 12 tour steps):

1. **80/20 scripted/LLM.** UA's own graph uses 4 deterministic edge types (`contains` / `imports` / `exports` / `calls`) for 173 of 183 edges. Only 9 edges (5%) come from LLM judgment (`related` / `similar_to` / `validates`). The bulk of the graph is mechanically extracted — LLMs add a thin semantic layer. **Implication for HP:** tree-sitter / import-resolver does the heavy lifting; LLMs classify what's a Stage-1 terminator vs Stage-2 process vs Stage-5 module. That's the value-add.

2. **Aggressive significance filter.** UA's monorepo has many hundreds of TS symbols; the graph has 97 nodes. **Implication for HP:** the dictionary captures what an architect would draw on a whiteboard, not every function. For cloudctlplane-scale projects, target ~50–100 entities, not thousands.

3. **Every LLM agent gets a deterministic script in front of it.** UA's project-scanner is 95% scripted (git ls-files + extension map + import resolution); LLM only writes the description. File-analyzer: tree-sitter extracts symbols deterministically; LLM only chooses tags + complexity. **Implication for HP:** every agent in our pipeline pairs with a bundled `.py` script that emits a structured input. LLMs never write the validation/parsing scripts.

## Architecture: 6 agents + one IR

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   PROJECT ROOT ──────► hp-scanner ──────────► intermediate/             │
│                          (Stage 0)              scan.json                │
│                                                                         │
│        ┌──────────────────────────────────────────┐                     │
│        ▼                                          ▼                     │
│   hp-boundary-finder                       hp-process-extractor          │
│     (Stage 1)                                (Stage 2)                  │
│        │                                          │                     │
│        └────────────────────┬─────────────────────┘                     │
│                             ▼                                           │
│              intermediate/hp-graph.json ◄────────────────┐              │
│                             │                            │              │
│           ┌─────────────────┴────────────────┐           │              │
│           ▼                                  ▼           │              │
│   hp-leaf-analyzer (Stages 3+4)        hp-architect       │              │
│      parallel by process                  (Stage 5)      │              │
│      (3–5 concurrent)                        │           │              │
│           └────────────────┬─────────────────┘           │              │
│                            ▼                             │              │
│                  hp-assembler-reviewer ──────────────────┘              │
│                            │                                            │
│                            ▼                                            │
│                     dictionary.yaml                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### The 6 agents

| # | Agent | Job | Input | Output | Script-in-front |
|---|---|---|---|---|---|
| 1 | `hp-scanner` | Inventory files, detect languages / frameworks, classify each file with an HP role hint | project root + `.hpignore` | `scan.json`: `{project, languages, frameworks, files[{path, language, sizeLines, hp_role_hint, ...}], importMap}` | `scripts/hp_scan.py` does git-ls-files, language detection, framework heuristics, calls a small per-file classifier (tree-sitter + extension + keyword) for the HP role hint. LLM only writes the project description. |
| 2 | `hp-boundary-finder` | Identify the system boundary: terminators + boundary flows | `scan.json` | `boundary.json`: `{terminators[], boundary_flows[]}` | `scripts/hp_boundary_candidates.py` extracts CLI entry points, HTTP listeners, external client SDK calls, cron entries, message bus subscribers from `scan.json`. LLM classifies which are real Stage-1 terminators vs internal abstractions, names them, writes descriptions. |
| 3 | `hp-process-extractor` | Decompose `sys_root` into level-1 processes + data stores + internal flows | `scan.json` + `boundary.json` | `processes.json`: `{processes[], stores[], internal_flows[]}` | `scripts/hp_process_candidates.py` clusters files by directory + import-cluster + role-hint, surfaces candidate process groupings. LLM names the processes, decides which are state-rich (`needs_cspec: true`), draws internal flows between them. |
| 4 | `hp-leaf-analyzer` | Per leaf process: produce CSPEC (state machine) OR PSPEC (functional contract) | one process at a time, with its file cluster | enriched node in `hp-graph.json` | `scripts/hp_extract_state_machine.py` looks for state-enum + transition-table patterns; if found → CSPEC candidate. Otherwise → PSPEC. LLM writes the actual content (states, transitions, transformation body). **This is the only parallelizable agent** (3–5 concurrent, batched by process). |
| 5 | `hp-architect` | Stage 5: identify hardware / software / organizational modules + interconnects; allocate processes | full `hp-graph.json` | `architecture.json`: `{modules[], flows[], interconnects[], allocations[]}` | `scripts/hp_architecture_candidates.py` surfaces deployment-unit candidates from Dockerfile / docker-compose / k8s manifests / package manifests. LLM names modules, draws interconnects, allocates processes. |
| 6 | `hp-assembler-reviewer` | Merge intermediates → repair → emit final `dictionary.yaml` | all intermediates | `dictionary.yaml` + `ingest-report.md` | `scripts/hp_merge_graph.py` does deterministic merge (strip prefixes, normalize enum aliases, drop dangling edges, validate against HP schema) and writes a stderr report of unrecoverable issues. LLM repairs the flagged issues and emits the final YAML. |

### The IR: `intermediate/hp-graph.json`

A single growing JSON file, accreted across phases. Each agent reads + writes. The reviewer's merge script is the only thing that mutates by deletion.

```jsonc
{
  "version": "0.1",
  "project": {
    "name": "cloudctlplane",
    "description": "<one-paragraph LLM output from hp-scanner>",
    "languages": ["rust", "python", "typescript", "go"],
    "frameworks": ["axum", "fastapi", "react", "..."],
    "gitCommitHash": "<sha at ingest time>",
    "analyzedAt": "<ISO timestamp>"
  },
  "nodes": [
    {
      "id": "term_user_browser",
      "kind": "terminator",           // ← HP entity kinds, not UA's function/class/file
      "label": "User (browser)",
      "stage": 1,                     // which HP stage produced this
      "confidence": 0.92,             // LLM's self-rated confidence
      "implemented_by": [],           // empty for terminators (external)
      "summary": "Human operator accessing the dashboard via HTTPS.",
      "provenance": {
        "agent": "hp-boundary-finder",
        "rationale": "Inferred from axum HTTP listener + Cookie-based auth."
      }
    },
    {
      "id": "proc_validate_order",
      "kind": "process",
      "label": "Validate Order",
      "stage": 2,
      "confidence": 0.81,
      "needs_cspec": false,
      "implemented_by": ["src/orders/validate.rs", "src/orders/rules.rs"],
      "summary": "Applies business rules to inbound order events.",
      "provenance": {
        "agent": "hp-process-extractor",
        "rationale": "Directory cluster `src/orders/` exposes one inbound flow."
      }
    }
    // ... process / data_store / state / pspec / architecture_module / ...
  ],
  "edges": [
    { "source": "term_user_browser", "target": "proc_serve_ui",
      "kind": "data_flow",  "label": "F1: user actions", "stage": 1 },
    { "source": "am_controller_host", "target": "proc_validate_order",
      "kind": "allocates_to", "stage": 5 }
    // ...
  ]
}
```

**Note the differences from UA's IR:**

- **HP entity kinds, not implementation primitives.** `terminator` / `process` / `data_store` / `state` / `pspec` / `architecture_module` / `architecture_flow` / `architecture_interconnect` — the same vocabulary `dictionary.yaml` uses.
- **`implemented_by[]` provenance array.** A process can be implemented by many files; many files might compose one process. UA's path-keyed IDs (`file:src/foo.ts`) don't work here.
- **`confidence` per node.** Architect-reviewable. The reviewer can sort by lowest confidence to know what to spot-check.
- **`stage` per node.** Records which agent produced it. Drives the renderer + the "which stage produced this?" view.

## HP role hints (per file, per Stage 0)

`hp-scanner` tags every file with one of six role hints. **This single signal is the highest-leverage classifier in the pipeline.** Downstream agents use it heavily.

| Hint | Match heuristic | What it implies |
|---|---|---|
| `boundary` | HTTP handlers, gRPC servers, CLI entry points, message-bus subscribers, file-watchers, cron jobs | Likely participates in Stage-1 boundary flows; likely Stage-5 allocated to an outward-facing module |
| `pure-logic` | Files with no I/O imports, only domain types + functions | Likely Stage-4 PSPEC content. Most-likely-PSPEC role. |
| `state-machine` | Files containing state-enum + transition-table, or saga-style coordinator patterns | **`needs_cspec: true` candidate.** Stage-3 driver. |
| `data-store` | DB client init, cache client init, queue client init, ORM model declarations | Likely Stage-2 data store, sometimes Stage-5 module (DB itself). |
| `infra` | Dockerfile, docker-compose.yaml, k8s manifests, terraform, ansible | Stage-5 architecture module signal. Tells the architect what's deployable. |
| `config` | TOML/YAML/JSON config, env-var schemas | Cross-cutting; rarely a node, sometimes informs trust zones (modernization). |

The classifier is a small Python script in `scripts/hp_classify_role.py` — no LLM. Uses extension + path + a few content regexes. Cheap, deterministic, runnable on millions of files.

## Significance filter

What gets into the dictionary vs what stays out:

- **In:** files / clusters classified `boundary`, `state-machine`, `data-store`, `infra` (always). `pure-logic` clusters that exceed a threshold of lines-of-code or that have ≥1 inbound flow (= someone calls them).
- **Out:** tests (`*_test.*`, `tests/`, `spec/`). Build outputs (`dist/`, `build/`, `node_modules/`, `target/`). Generated code (heuristic: file says `// AUTO-GENERATED` or `# DO NOT EDIT`). Documentation (`*.md`, `docs/`). Trivial config that doesn't influence architecture.

The filter is in `scripts/hp_significance.py`. Configurable thresholds (e.g., min-LOC for `pure-logic` cluster). Defaults tuned to produce ~50–100 entities on a cloudctlplane-scale project.

## What we ship

```
toolkit/
├── INGEST_DESIGN.md                   ← this file
├── hp_toolkit/
│   └── ingest/
│       ├── __init__.py
│       ├── scan.py                    ← Stage 0 scanner (Python; called by hp-scanner agent script)
│       ├── role_classifier.py         ← the 6-category HP role hint
│       ├── significance.py            ← filter
│       ├── boundary_candidates.py     ← Stage 1 candidate extractor
│       ├── process_candidates.py      ← Stage 2 candidate extractor
│       ├── state_machine_detector.py  ← Stage 3 state-machine pattern matcher
│       ├── architecture_candidates.py ← Stage 5 deployment-unit extractor
│       ├── merge_graph.py             ← deterministic IR merge + normalization
│       ├── emit_dictionary.py         ← IR → dictionary.yaml writer
│       └── schema.py                  ← Pydantic schemas for the IR (mirror of dictionary.yaml but extended with confidence + provenance)
│
├── skills/
│   ├── hp-ingest.md                   ← the orchestrator skill (the SKILL.md equivalent)
│   ├── hp-ingest-scan.md              ← Stage 0 agent
│   ├── hp-ingest-boundary.md          ← Stage 1 agent
│   ├── hp-ingest-processes.md         ← Stage 2 agent
│   ├── hp-ingest-leaf.md              ← Stages 3+4 agent (single skill, dispatched in parallel)
│   ├── hp-ingest-architect.md         ← Stage 5 agent
│   └── hp-ingest-review.md            ← assembler-reviewer
│
└── scripts/
    └── hp_ingest.py                   ← CLI orchestrator (Python equivalent of UA's SKILL.md runbook)
```

CLI surface:

```bash
# Full ingest
uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir>

# Resume from intermediate
uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --resume

# Incremental — only re-ingest what changed since last commit
uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --incremental

# Skip the architect stage (Stage 5) — useful for early dogfood
uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --no-architecture
```

## Implementation order

Three commits on this branch, mirror of the portal arc:

### Commit 1 — Scanner + IR + role classifier
- `hp_toolkit/ingest/schema.py` — Pydantic IR schemas.
- `hp_toolkit/ingest/role_classifier.py` — the 6-category HP role hint.
- `hp_toolkit/ingest/scan.py` — Stage 0 scanner (no LLM, pure Python).
- `hp_toolkit/ingest/significance.py` — filter.
- `skills/hp-ingest-scan.md` — agent definition for the scanner pass.
- `scripts/hp_ingest.py` — CLI stub that runs scan-only.
- **Verified by:** running `--scan-only` against `examples/fishing-rig` and against `hatley-pirbhai` (self-test). Output: `intermediate/scan.json` with role hints on every file.

### Commit 2 — Boundary + process + leaf agents
- `hp_toolkit/ingest/boundary_candidates.py`, `process_candidates.py`, `state_machine_detector.py`.
- `hp_toolkit/ingest/merge_graph.py` — IR merge + normalization.
- `skills/hp-ingest-boundary.md`, `hp-ingest-processes.md`, `hp-ingest-leaf.md`.
- CLI advances to Stage 4 lock.
- **Verified by:** ingesting the **hatley-pirbhai toolkit itself** (~30 files, mostly Python) and producing a draft `dictionary.yaml` — IR + dictionary should be reviewable against the hand-written toolkit structure.

### Commit 3 — Architect + assembler-reviewer + dictionary emit
- `hp_toolkit/ingest/architecture_candidates.py`, `emit_dictionary.py`.
- `skills/hp-ingest-architect.md`, `hp-ingest-review.md`.
- `skills/hp-ingest.md` — the master orchestrator skill.
- CLI completes the full pipeline.
- **Verified by:** end-to-end ingest of a larger second target (TBD per Q1 below) → review the emitted dictionary against the architect's mental model.

## Token economics — Python does 70–80% of the work

The architectural decision that keeps cost sane is **the per-file role classifier in pure Python**, not an LLM. That single move drops ingest token cost roughly 10× vs the naive "ask the LLM about each file" approach. UA uses the same trick (`extract-structure.mjs` does tree-sitter parsing; LLM only summarizes).

Per-agent budget:

| Agent | Script does (free) | LLM does (paid) | Tokens / call |
|---|---|---|---|
| `hp-scanner` | git-ls-files, language detect, framework detect, **per-file role hint** (highest-volume operation) | One-paragraph project description | <1k |
| `hp-boundary-finder` | Extract CLI entries / HTTP listeners / external SDK calls from scan.json | Classify each candidate as real terminator vs internal abstraction | 5–20k |
| `hp-process-extractor` | Cluster files by directory + imports + role-hint | Name processes, set `needs_cspec`, draw internal flows | 5–15k |
| `hp-leaf-analyzer` | Gather source code for one process | **Reads actual source code.** Writes PSPEC body OR CSPEC state-machine | **20–50k × N leaf processes** (parallelizable 3–5 concurrent) |
| `hp-architect` | Extract deployment-unit candidates from infra files | Name modules, draw interconnects, allocate processes | 5–15k |
| `hp-assembler-reviewer` | Deterministic merge + schema validate | Repair only what the merge script flagged | ~5k |

**Total per full ingest:**

- Fishing-rig scale (~30 files, 4 leaf processes): **~50–100k tokens**, sub-dollar at Claude API rates.
- cloudctlplane scale (~1600 files, ~30–50 leaf processes after the significance filter): **~300–800k tokens**, $1–5 per full ingest.

`hp-leaf-analyzer` dominates because it's the only agent reading raw source code. Everything else operates on aggregated structured summaries. **The significance filter is therefore the highest-leverage cost lever** — tightening it from "every pure-logic cluster over 50 LOC" to "over 200 LOC" can cut total tokens 2–3×.

Incremental ingests are much cheaper — see below.

## Incremental updates

The full picture, not just the trigger. `--incremental` mode operates on the diff between the last ingest's commit and HEAD, re-runs only the agents whose inputs touched, and reconciles against the existing dictionary with strict preservation rules.

### Trigger + propagation

1. Read `project.gitCommitHash` + `project.analyzedAt` from existing `dictionary.yaml`.
2. `git diff <last-hash> HEAD --name-only` → list of changed files.
3. **Per-agent re-run gates:**
   - `hp-scanner`: re-classifies only the changed files.
   - `hp-boundary-finder`: re-runs only if changed files include `boundary` role hints OR if any frameworks were added/removed in scan.json.
   - `hp-process-extractor`: re-runs only if any cluster's membership shifted (file moved between role hints, or file added/removed).
   - `hp-leaf-analyzer`: re-runs **per-process**, only for processes whose `implemented_by[]` files actually changed. Most processes unaffected — most ingests touch maybe 1–3 processes.
   - `hp-architect`: re-runs only if infra files (Dockerfile / compose / k8s / terraform) changed or if a new boundary module appeared.
   - `hp-assembler-reviewer`: always runs (merge + emit).

Typical commit (3–10 files changed in 1–2 processes) costs **5–30k tokens**, an order of magnitude under a full ingest.

### Reconciliation rules — what hp-ingest writes vs what it preserves

**hp-ingest writes (and can replace on incremental):**

- `entities:` — terminators, processes, data stores, states (the Stage 1–4 structural entities)
- `flows:`, `edges:`, `transitions:` (Stages 1–3)
- `pspecs:` `transformation` body (Stage 4 main content)
- `architecture_modules:`, `architecture_flows:`, `architecture_interconnects:` (Stage 5 structural)
- `architecture_module_specs:` / `architecture_interconnect_specs:` core `description` + `design_rationale` (Stage 5 prose)

**hp-ingest preserves verbatim (never touches on incremental):**

- `adrs:` — Architecture Decision Records (modernization #10)
- `budgets:`, `tpms:` (modernization #21/#22)
- `service_level_objectives:` (modernization #32)
- `bounded_contexts:` (modernization #5)
- PSPEC `verification:` blocks (modernization #25)
- PSPEC + ArchModule `observability:` blocks (modernization #1)
- ArchInterconnect `stride_mitigations:` + `linddun_mitigations:` (modernization #8.2)
- `references_mitre_attack:` / `references_cwe:` / `references_compliance:` lists on AMS / AIS / ADR (modernization #8.3)
- Any field hp-ingest didn't author originally — including hand-written `description` overrides, custom `notes`, etc.

The mechanism: every IR node carries a `provenance.agent` field. On incremental reconcile, the merger checks per-field — if `provenance.agent` is one of `hp-ingest-*`, it's eligible for replacement; otherwise it's preserved.

### Conflict surface

When new ingest contradicts existing dictionary (process renamed, kind changed, terminator removed), the reviewer emits `ingest-conflicts.md` listing each diff for manual review **before** writing the new dictionary. Nothing changes until the user approves. User can reject individual diffs and the merger preserves the existing value.

If the user runs `--incremental --auto-accept`, conflicts are resolved by taking the new inference. Default is conservative (`--auto-accept` is opt-in).

### Orphans

When a file is deleted, it's removed from every `implemented_by[]` list. If a process's `implemented_by` becomes empty, the process is **marked as orphan** (not deleted). The reviewer logs it in `ingest-report.md`; user decides whether to delete or keep as a forward-looking placeholder. Same for terminators / data stores / modules that lose all evidence.

## Modernization fields

**Not produced by hp-ingest in v1.** Rationale: modernization fields (trust zones, observability surface, ADRs, SLOs, V&V, STRIDE) are *architectural decisions*, not extractable facts. The existing `hp-propose-*` skills do them well with form-based review.

Workflow:

1. `hp-ingest <codebase>` → produces dictionary.yaml with Stages 1–5 + role hints + provenance.
2. `hp-validate` → confirm structural soundness.
3. `hp-propose-observability` / `hp-propose-slos` / `hp-capture-adr` / etc. → user runs each modernization skill against the ingested baseline, locks one form-based proposal at a time.

The exception: **`trust_zone` per architecture module** *might* be inferrable from infrastructure files (Dockerfile labels, k8s namespaces, network policies). See Q3 below.

## Provenance

This design is informed by:

- **[Understand-Anything](https://github.com/Lum1104/Understand-Anything)** — multi-agent codebase analyzer. Reviewed in detail (conversation log). Borrowed: agent-with-script-in-front pattern, intermediate JSON IR, type-alias tables for LLM enum drift, incremental updates via gitCommitHash, aggressive significance filter, tour/traceability narrative. Skipped: file-keyed IDs (HP entities are conceptual), 21-type vocabulary (HP needs 8), domain-analyzer (HP Stage 2 IS the domain), pedagogical tour (HP needs traceability tour).
- **Earlier brownfield review** (firewalled inspection of cloudctlplane + bru) — pattern-level observations that informed [project_brownfield_ingest_patterns memory](../../memory/project_brownfield_ingest_patterns.md). The 6-category role hint taxonomy comes from this review.
- **The full HP toolkit context** — every choice here aims to produce a `dictionary.yaml` consumable by the existing validate / render / status / portal / PDF / modernization pipeline. No new vocabulary; just an automated way to populate the existing one.

## Open questions

Mark up below — I'll lock the doc + start Commit 1 once these are resolved. Same form-based-proposal pattern used for MODERNIZATION_DESIGN.md, BOUNDED_CONTEXTS_DESIGN.md, PORTAL_DESIGN.md.

### Q1. First demo target after hatley-pirbhai self-ingest?

- [x] **cloudctlplane** — real polyglot brownfield mess Kevin knows inside-out. Highest signal; output is IP-laden so reviews stay pattern-level (same firewall as the earlier brownfield study).
- [ ] **bru** — kernel sensor + userspace; smaller than cloudctlplane but kernel-version-targeted is unusual. Also IP-firewalled.
- [ ] **A small open-source project** (e.g., a moderately-sized Python or Rust project on GitHub) — open everything; no firewall, lower stakes for first dogfood.
- [ ] **Solar / fishing-rig (synthetic)** — we already have hand-written dictionaries. hp-ingest output diffable against ground truth.

I lean **cloudctlplane** for the real-world signal once Commit 1 + 2 are stable on hatley-pirbhai self-ingest. Solar / fishing-rig are useful as **regression tests** (does hp-ingest's output match the hand-authored dictionary?). Open-source as a **public demo** target later.

### Q2. PSPEC granularity — per-function or per-process-cluster?

A "process" in HP is a single bubble that may be implemented by multiple files / functions. PSPEC is the functional contract of a leaf process.

- [x] **Per-process-cluster** (recommended): the leaf-analyzer agent takes the cluster of files for one process, produces a single PSPEC describing the process's overall input→output transformation. Matches HP's intent (one PSPEC per leaf bubble).
- [ ] **Per-function then merge** — write a PSPEC per function, then merge at review time. More granular, more work, mostly redundant since the dictionary only needs one PSPEC per process.

I lean **per-process-cluster**. This is the right HP semantics. The per-function structure is preserved in `implemented_by[]` provenance.

### Q3. Should hp-ingest *propose* trust zones?

`trust_zone` is the one modernization field with strong infrastructure signal — Dockerfile `USER`, k8s namespace + network policies, VPC declarations, etc.

- [x] **No, defer entirely** — hp-ingest stops at Stages 1–5 core; `hp-propose-architecture` (which already covers trust zones in its Decision 9) handles it via form-based review. Cleanest separation.
- [ ] **Yes, infer + mark as proposed** — hp-ingest's architect agent extracts trust_zone from infra files into the IR with `confidence` < 1.0. Reviewer surfaces these for user confirmation. Faster path to a complete modernization-layer-ready dictionary.

I lean **defer entirely (the first option)** for v1. The hp-propose-architecture / hp-propose-threat-model flow is already form-based and works well; hp-ingest's job is to produce the substrate they review. Mixing in trust-zone inference blurs the responsibility boundary.

### Q4. Brownfield-with-existing-dictionary support in v1?

- [x] **Greenfield-only for v1** (recommended): hp-ingest assumes no existing `dictionary.yaml`. Output is full overwrite. User runs once; thereafter they hand-edit + use `--incremental` for code-change reconciliation.
- [ ] **Merge mode from day one** — hp-ingest takes a pre-existing `dictionary.yaml` and merges. More work, more edge cases. Useful when user has hand-authored part of the dictionary already.

I lean **greenfield-only for v1**. Merge mode is a v2 feature; the `--incremental` path covers the common case (code changes after initial ingest). If the user wants to merge a hand-authored dictionary with an ingested one, that's a feature for a future commit.

### Q5. Confidence + provenance shape — required on every node?

- [x] **Yes, every node** (recommended): both `confidence: 0..1` and `provenance: { agent, rationale }` required on every IR node. Renderer surfaces lowest-confidence entities to the architect for spot-check.
- [ ] **Confidence yes, provenance light** — confidence required; provenance only on judgment-call entities (skip on terminators inferred from clear infra signals).
- [ ] **Neither — keep IR clean** — drop both, trust the LLM, fix during reviewer pass if anything goes wrong.

I lean **every node**. Confidence is cheap to ask the LLM for (one extra field per node); provenance is the only thing that lets the architect quickly debug "why did hp-ingest infer X?". This is also what makes the renderer output reviewable in the portal — show confidence as a pill color.

---

*Drafted 2026-05-23 on `kg/brownfield-ingest`. Pattern matches the prior design docs: `MODERNIZATION_DESIGN.md`, `BOUNDED_CONTEXTS_DESIGN.md`, `PORTAL_DESIGN.md`, `ARCH_DESIGN.md`, `PSPEC_DESIGN.md`.*
