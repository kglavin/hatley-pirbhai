# HP Toolkit

An AI-augmented toolkit around the **Hatley-Pirbhai methodology** for systems requirements and architecture specification. Brings the rigor of HP (1988 + 2000 books) into modern AI-assisted development.

## What this toolkit is for

Modern AI-assisted development has a coherence problem: proposals get to 85% then trail off, features rathole into subsystems, interfaces get lost in implementation, and there's no single northstar across a growing pile of `.md` files. HP was invented in 1988 for exactly this — keeping large, long-lived, multi-author systems coherent on FAA-certified avionics. This toolkit makes HP's rigor affordable in 2026 by automating its bookkeeping with AI, while preserving the discipline that made it work.

It's for senior engineers and architects who've watched UML, Agile, and "just-enough docs" fail to scale, and want a rigorous method that doesn't require expensive enterprise tooling.

---

## What HP is, in 60 seconds

Hatley-Pirbhai is a structured-analysis method developed in the late 1980s and refined in 2000 for specifying real-time systems. It separates **requirements** (what the system must do, observable from outside) from **architecture** (how the system is decomposed and implemented) with a small set of canonical work products:

- **Context Diagram** — the system boundary; every external actor (terminator) and every flow crossing the boundary.
- **Data Flow Diagram (DFD)** — internal processes that produce/consume the flows. Hierarchical: a DFD can decompose any process into its own level-N+1 DFD.
- **Control Specification (CSPEC)** — for state-rich processes: a state machine specifying modes, transitions, events, actions.
- **Process Specification (PSPEC)** — for leaf processes: input → output spec (pseudocode, formula, decision table).
- **Requirements Dictionary** — the canonical naming registry. Every entity, flow, state, event, and action has exactly one entry.

Plus an **Architecture Model** branch (added in the 2000 book) — AFD, AID, AMS, AIS — that maps the requirements model onto modules, hardware, and channels.

Full method glossary with modern analogs: [`reference/HP_QUICK_REF.md`](reference/HP_QUICK_REF.md).

---

## Install

```bash
bash toolkit/bootstrap.sh
```

User-space only (`~/.local/bin/`); no sudo; idempotent. Installs:

- **`uv`** — Python project/env manager (Astral)
- **`d2`** — declarative diagrams renderer
- **`mmdc`** — Mermaid CLI

After install: ensure `~/.local/bin` is on your `$PATH`.

The Python dependencies — Pydantic, PyYAML, Python-Markdown, WeasyPrint — are installed by `uv sync` (run via `uv run`). **WeasyPrint** is used for the project PDF; it has system dependencies (pango, cairo, gdk-pixbuf, fonts) that are usually pre-installed on Ubuntu/Debian. If PDF rendering fails with a font-related error, install `libpango-1.0-0 libpangoft2-1.0-0` via your system package manager.

**Recommended IDE setup:** VS Code + [Markdown Preview Enhanced](https://marketplace.visualstudio.com/items?itemName=shd101wyy.markdown-preview-enhanced) (MPE). MPE renders embedded Mermaid/D2 in preview and lets you click `[ ]` → `[x]` checkboxes directly — the form-based proposal pattern (below) depends on this.

---

## The mental model

Three ideas carry the rest of the toolkit:

### 1. Dictionary as source of truth

Every project has a single `dictionary.yaml` at its root — HP's Requirements Dictionary in YAML form. Every entity, flow, edge, and transition is declared there once. All rendered artifacts (`.mmd`, `.d2`, `.html`, `.svg`, `.pdf`) are **derived**: regenerated from the dictionary on demand. Rename a flow in one place and every diagram updates on the next render. The dictionary is the only file you hand-edit; everything else is generated.

### 2. The five HP stages

Each project advances through stages, top to bottom. The toolkit's directory layout mirrors them 1:1 so a practitioner walking the filesystem is walking the HP model.

| Stage | Produces | Lives in | Status |
|---|---|---|---|
| 1 — Context Diagram | system boundary; terminators; boundary flows | `00-context/` | ✅ supported |
| 2 — Level-1 DFD | internal processes; data stores; internal flows; flow refinement | `01-level1/` | ✅ supported |
| 3 — CSPEC | hierarchical state machine for each `needs_cspec: true` bubble | `01-level1/cspecs/<proc-id>/` | ✅ supported |
| 4 — PSPEC | leaf-process functional contract: INPUTS / OUTPUTS / TRANSFORMATION (2000 Fig 4.46) | `01-level1/pspecs/` | ✅ supported |
| 5 — Architecture Model | AFD + AID + AMS + AIS + allocation to requirements (2000 §4.2) | `architecture/` | ✅ supported |

`hp-status <project-dir>` reports which stage each project has reached, with validation summary + artifact freshness + open questions in one screen.

### 3. Form-based proposal pattern

Each stage is locked through a **form-based proposal** rather than chat. The skill (`hp-propose-context`, `hp-propose-decomp`, `hp-propose-cspec`, `hp-propose-pspec`, `hp-propose-architecture`) drafts a `proposal.md` containing:

- A rendered draft diagram (Mermaid inline + sidecar SVG)
- 7–12 numbered decisions; each with alternatives as `- [ ]` checkboxes; Claude's recommended default **pre-checked** with provenance ("extracted from your description"; "matches solar's pattern"; "AI inference")

You open the proposal in MPE, click `[ ]` → `[x]` for any overrides, save **once**, and ping back. The skill parses the saved file in one pass and writes the `## ✅ Status: Locked YYYY-MM-DD` header + populates `dictionary.yaml` with the resulting entities.

This replaces chat round-trips with a single-save batch review. The proposal becomes the locked audit record — every project has a permanent paper trail of what was decided, why (pre-checked defaults preserve Claude's reasoning), and what alternatives were considered.

After lock, [`hp-confirm-naming`](skills/hp-confirm-naming.md) runs a second form-based pass on every working name (`accept / rename / alias`), so the naming review is explicit and reviewable.

### 4. Modernization layer — design intent → runtime

The 1988/2000 HP method nails *what* and *how*. The 21st-century reality is that "shipped" is not the end — the system runs in production, burns SLOs, gets attacked, evolves with the team. The toolkit adds a thin **modernization layer** on top of HP that wires the static spec to runtime reality, captured by ten items rolled out across [Commits 1–5](MODERNIZATION_DESIGN.md) + [Commits A–C](MODERNIZATION_TACTICS.md):

- **Async/sync semantics** on every flow (#2)
- **Trust zones + auth + encryption** on every module / interconnect (#8.1)
- **STRIDE threat models** on every cross-trust-zone interconnect (#8.2) + **MITRE ATT&CK / CWE / compliance catalog refs** (#8.3)
- **V&V plans** on every leaf process (#25)
- **ADRs** captured mid-decision (#10)
- **Design-time budgets** on architecture modules (#21) + **runtime TPMs** that track them over time (#22)
- **Observability surface** on every leaf — metrics, traces, log categories, alerts with runbooks (#1 + #33)
- **SLI / SLO / SLA chain** tied back to TPMs (#32)
- **Bounded contexts** + Anti-Corruption Layers when multi-team / multi-vocabulary scale arrives (#5)

This forms the **design-intent → runtime chain**: a Budget locks design-time → a TPM measures it over time → an Observability metric emits it → an SLO commits an external promise → a Runbook says what to do when burning. Every link is in the dictionary and the validator enforces the cross-references. The six new modernization skills (table below) each propose one slice through a form-based pass; the validator + renderer surface the rest.

See [`MODERNIZATION_DESIGN.md`](MODERNIZATION_DESIGN.md) for the schema rationale, [`BOUNDED_CONTEXTS_DESIGN.md`](BOUNDED_CONTEXTS_DESIGN.md) for the DDD path, and [`MODERNIZATION_TACTICS.md`](MODERNIZATION_TACTICS.md) for the AI-interaction layer plan.

### 5. Project portal + shareable PDF

Every render produces two top-level "land here" artifacts at the project root:

- **`project_index.generated.html`** — the front-door page. Lists every artifact organized by stage + modernization, with a one-line validation + modernization summary at the top.
- **`project.generated.pdf`** — a single self-contained PDF you can email or archive: cover page, clickable TOC with page numbers, per-stage section covers, every diagram (SVG) on landscape pages, every markdown sidecar (PSPECs, AMS, AIS, ADRs, SLOs summary, runbooks) on portrait pages, HP Quick Reference as appendix.

Every generated HTML page (Context, DFD, CSPECs, AFD, AID, plus every wrapped markdown sidecar) carries a **collapsible left-sidebar** with the full project tree. Click the ◀ toggle to reclaim canvas on wide diagrams; state persists across pages via localStorage. The same tree feeds the PDF's TOC, so portal and PDF stay in sync.

See [`PORTAL_DESIGN.md`](PORTAL_DESIGN.md) for the shape decisions (page orientation, markdown lib, PDF tracking policy, etc.).

### 6. Brownfield ingest — bootstrap from existing code

The first five ideas all assume a *greenfield* HP project — you write `dictionary.yaml` from scratch, the AI helps you lock each stage. The reality is most engineers come to HP with an existing codebase. `hp-ingest` is the bootstrap path:

```bash
uv run python scripts/hp_ingest.py /path/to/codebase --output /path/to/hp/project
```

A six-agent pipeline turns the codebase into a draft `dictionary.yaml`:

- **Stage 0 (Python; no LLM):** scan files, classify each with an HP **role hint** (`boundary` / `pure-logic` / `state-machine` / `data-store` / `infra` / `config`). The single most decision-shaping signal in the whole pipeline. Deterministic, cheap, runs in seconds even on cloudctlplane-scale repos.
- **Stage 1 (LLM):** `hp-ingest-boundary` decides which `boundary`-classified files map to real Stage-1 terminators.
- **Stage 2 (LLM):** `hp-ingest-processes` clusters significant non-boundary files into Stage-2 processes + data stores + internal flows.
- **Stage 2-recurse (Python + recursive LLM):** for monorepos, processes whose `implemented_by` exceeds the threshold get a recursive Stage-2 dispatch that emits their internal level-2 sub-processes. The recursion walks `--max-recursion-depth` (default 3). See [`HIERARCHICAL_INGEST_DESIGN.md`](HIERARCHICAL_INGEST_DESIGN.md).
- **Stages 3 + 4 (parallel LLM):** `hp-ingest-leaf` runs once per leaf process (3–5 concurrent) — writes a CSPEC for state-rich processes, a PSPEC for the rest. Leaves can be at any recursion depth.
- **Stage 5 (LLM):** `hp-ingest-architect` allocates every leaf process / CSPEC / data store to an architecture module + draws interconnects. Once at the top — sees the full hierarchy in `hp-graph.json`.
- **Review (LLM):** `hp-ingest-review` runs `hp-validate` against the projected dictionary and repairs anything broken before emission.

**Two design ideas are load-bearing:**

1. **80/20 scripted/LLM** — deterministic Python scripts surface *candidates* (HTTP listeners, file clusters, state enums, Dockerfiles); LLM agents make the *architectural judgment* (is this a real terminator? what's this process named? does it need a CSPEC?). Per-ingest token cost is moderate (~50–100k tokens for fishing-rig-scale, ~300–800k for cloudctlplane-scale) — Python does the heavy lifting.
2. **Every IR node carries confidence + provenance.** The architect reviews the lowest-confidence entities first; every field's source is recorded so re-ingest after code change preserves user edits + modernization-layer fields verbatim. Incremental updates via `git diff <last-hash>` re-run only the agents whose inputs touched.

See [`INGEST_DESIGN.md`](INGEST_DESIGN.md) for the full pipeline, token economics, incremental rules, and the locked design decisions.

---

## Workflow

A full project lifecycle, end-to-end. Two entry points — greenfield (`hp-init`) or brownfield (`hp-ingest <codebase>`):

```text
─── Greenfield: start from a blank dictionary ─────────────────────
hp-init <name>                 # scaffold directory + dictionary skeleton
   ↓
hp-propose-context             # Stage 1: terminators + boundary flows
   ↓
hp-confirm-naming              # review terminator + flow names
   ↓
hp-render                      # generate Context Diagram (Mermaid + D2 + HTML + SVG)
   ↓
hp-propose-decomp              # Stage 2: level-1 internal processes
   ↓
hp-confirm-naming              # review process + flow + data-store names
   ↓
hp-render                      # generate level-1 DFD
   ↓
hp-propose-cspec               # Stage 3: state machine for each needs_cspec bubble
   ↓
hp-confirm-naming              # review state + event + action names
   ↓
hp-render                      # generate CSPEC
   ↓
hp-propose-pspec               # Stage 4: one PSPEC per remaining leaf process
   ↓
hp-render                      # generate PSPEC markdown sidecars
   ↓
hp-propose-architecture        # Stage 5: AFD + AID + AMS + AIS + allocation
   ↓
hp-confirm-naming              # review module + flow + interconnect names
   ↓
hp-render                      # generate AFD/AID + AMS/AIS sidecars
   ↓
─── modernization layer (interleave; order is roughly fixed by dependencies) ───
   ↓
hp-propose-threat-model        # per cross-trust-zone interconnect: full STRIDE pass + catalog refs
hp-propose-budgets-and-tpms    # design-time budgets + tracked-over-time TPMs
hp-propose-observability       # per leaf: metrics + traces + log categories + alerts + runbooks
hp-propose-slos                # SLI / SLO / SLA chain, tied back to TPMs
hp-propose-bounded-contexts    # paradigm shift; when team/vocabulary boundaries become visible
hp-capture-adr                 # invoked mid-decision at any stage, not at a fixed point
   ↓
(hp-status anywhere to check progress)
(hp-validate anywhere to check integrity)
```

Or, for a brownfield codebase:

```text
─── Brownfield: ingest existing code into HP ──────────────────────
hp-ingest <codebase>           # Stage 0 scan → 1/2/3+4/5 LLM agents → draft dictionary.yaml
   ↓
hp-validate                    # confirm structural soundness
   ↓
hp-render                      # generate diagrams + portal + PDF from the ingested baseline
   ↓
hp-propose-architecture        # refine Stage 5: trust zones, design rationale, deployment strategy
   ↓
(then layer in modernization skills as for greenfield)
   ↓
# Later, after code changes:
hp-ingest <codebase> --incremental    # re-ingest only what changed; preserves user edits
```

Each `hp-render` produces three views — Mermaid, D2, Cytoscape HTML — plus SVGs. The Cytoscape HTML is the **graphical IDE view**: single-click an entity for side-panel detail, double-click a decomposable bubble to navigate to its level-N+1 DFD, `↑ Parent` link to walk back up. Every entity links to its `dictionary.yaml` entry and to its HP reference card.

The **modernization-layer skills are optional but recommended.** Validators (Commits 1–5) only *require* what's structurally implied — e.g., STRIDE mitigations on cross-trust-zone interconnects, ACLs on cross-context flows. The rest (budgets, TPMs, SLOs, observability, ADRs) are tracked as coverage metrics: declared once, the validator hardens the cross-references; declared incrementally, partial coverage is fine.

---

## Skills

Twenty-four skills make up the methodology surface — ten core HP, six modernization, eight brownfield ingest. Each is documented in [`skills/`](skills/) as a Claude Code skill file (markdown + YAML frontmatter). Seven have backing Python; seventeen are conversational (LLM-driven orchestration or form-based review).

**Core HP — one per stage + the cross-cutting tools:**

| Skill | Stage / purpose | Backing code |
|---|---|:---:|
| [`hp-init`](skills/hp-init.md) | Scaffold a new HP project | ✅ |
| [`hp-propose-context`](skills/hp-propose-context.md) | Stage 1 form-based proposal | ⬜ |
| [`hp-propose-decomp`](skills/hp-propose-decomp.md) | Stage 2 form-based proposal | ⬜ |
| [`hp-propose-cspec`](skills/hp-propose-cspec.md) | Stage 3 form-based proposal | ⬜ |
| [`hp-propose-pspec`](skills/hp-propose-pspec.md) | Stage 4 form-based proposal | ⬜ |
| [`hp-propose-architecture`](skills/hp-propose-architecture.md) | Stage 5 form-based proposal | ⬜ |
| [`hp-confirm-naming`](skills/hp-confirm-naming.md) | Form-based naming review after any move that introduces named entities | ⬜ |
| [`hp-validate`](skills/hp-validate.md) | Reference integrity / hierarchy / coverage / orphan detection / PSPEC balancing / architecture allocation / modernization rules | ✅ |
| [`hp-render`](skills/hp-render.md) | Regenerate diagrams + SVGs + PSPEC + AMS/AIS + ADR + Context Map + SLOs markdown from `dictionary.yaml` | ✅ |
| [`hp-status`](skills/hp-status.md) | Report stages reached, validation, artifact freshness, open questions | ✅ |

**Modernization layer — six new skills (Commit C):**

| Skill | Stage / purpose | Backing code |
|---|---|:---:|
| [`hp-capture-adr`](skills/hp-capture-adr.md) | Mid-decision ADR capture (#10) — Nygard-style record + MITRE/CWE refs | ⬜ |
| [`hp-propose-threat-model`](skills/hp-propose-threat-model.md) | Per cross-trust-zone interconnect — full STRIDE pass + optional LINDDUN + MITRE/CWE/compliance refs (#8.2 + #8.3) | ⬜ |
| [`hp-propose-budgets-and-tpms`](skills/hp-propose-budgets-and-tpms.md) | NASA-style design-time budgets + tracked-over-time TPMs (#21 + #22) | ⬜ |
| [`hp-propose-observability`](skills/hp-propose-observability.md) | Per leaf — metrics + traces + log categories + alerts + runbooks (#1 + #33) | ⬜ |
| [`hp-propose-slos`](skills/hp-propose-slos.md) | SLI → SLO → SLA chain anchored to TPMs (#32) | ⬜ |
| [`hp-propose-bounded-contexts`](skills/hp-propose-bounded-contexts.md) | DDD bounded contexts + Anti-Corruption Layers when multi-team scale arrives (#5) | ⬜ |

**Brownfield ingest — eight skills (kg/brownfield-ingest + the input-expansion branches):**

| Skill | Stage / purpose | Backing code |
|---|---|:---:|
| [`hp-ingest`](skills/hp-ingest.md) | Master orchestrator — codebase → dictionary.yaml via the multi-stage pipeline | ✅ |
| [`hp-ingest-scan`](skills/hp-ingest-scan.md) | Stage 0 — file walk + role-hint classification (`boundary`/`pure-logic`/`state-machine`/`data-store`/`infra`/`config`) | ✅ |
| [`hp-ingest-glossary`](skills/hp-ingest-glossary.md) | Stage 0c-curate (optional) — LLM curator that reduces deterministic glossary candidates to ~30–60 canonical entries the naming agents consume | ✅ |
| [`hp-ingest-boundary`](skills/hp-ingest-boundary.md) | Stage 1 — boundary candidates → Stage-1 terminators + boundary flows (now reads glossary + user-docs + testbeds) | ✅ |
| [`hp-ingest-processes`](skills/hp-ingest-processes.md) | Stage 2 — process candidates → internal processes + data stores + flows (now reads glossary + testbeds + external-context) | ✅ |
| [`hp-ingest-leaf`](skills/hp-ingest-leaf.md) | Stages 3 + 4 — per-process CSPEC (state machine) or PSPEC (functional contract); parallel 3–5 concurrent (now reads glossary + testbeds + external-context) | ✅ |
| [`hp-ingest-architect`](skills/hp-ingest-architect.md) | Stage 5 — architecture-candidate list → modules + interconnects + allocation (now reads typed `CandidateEdge`s, `rationale-sources.json`, recipes, testbed compose/k8s) | ✅ |
| [`hp-ingest-review`](skills/hp-ingest-review.md) | Final reviewer — repair, validate, compose ingest-report.md, emit dictionary.yaml | ✅ |

The conversational skills (`hp-propose-*`, `hp-confirm-naming`, `hp-capture-adr`, the `hp-ingest-*` subagent specs) work by Claude reading the skill markdown and following the behavior spec. They don't need a Python implementation to invoke — the markdown *is* the executable specification. The schemas + validators + renderers + ingest scripts they target *are* implemented in Python — declared values land in `dictionary.yaml`, `hp-validate` hardens cross-references, `hp-render` emits the sidecars, and `hp-ingest` Python scripts surface candidates the LLM agents judge.

---

## CLI

```bash
cd toolkit

# Scaffold a new project
uv run python scripts/hp_init.py <project-name> --label "<Display>" --description "..."

# Validate a dictionary
uv run python -m hp_toolkit.validate <path/to/dictionary.yaml>

# Render all artifacts for a project (diagrams + sidebar'd HTML + index page + PDF)
uv run python scripts/render_project.py <project-directory>

# Render only the PDF (skips HTML/SVG regeneration; uses existing artifacts)
uv run python scripts/render_project.py <project-directory> --pdf-only

# Render everything except the PDF (faster during HTML iteration)
uv run python scripts/render_project.py <project-directory> --no-pdf

# Report stage progress
uv run python -m hp_toolkit.status <project-directory>

# Brownfield ingest — scan-only (Stage 0 file walk + role hints; deterministic, no LLM)
uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --scan-only

# Brownfield ingest — full candidate prep (Stages 0/1/2/3/5 deterministic prep)
uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --prep-candidates

# Brownfield ingest — merge + emit dictionary.yaml (after LLM agents wrote intermediates)
uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --merge-emit

# Brownfield ingest — resume after a killed / power-cut run (each stage probes its output JSON)
uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --resume

# Brownfield ingest — tuning for large monorepos (see INGEST_DESIGN.md "Tuning guide")
#   --min-pure-logic LINES  significance threshold for pure-logic files (default 50)
#   --max-depth N           cap directory-cluster depth for Stage-2 process candidates
uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --min-pure-logic 200 --max-depth 3

# Brownfield ingest — hierarchical Stage-2 recursion (see HIERARCHICAL_INGEST_DESIGN.md)
# Called by the /hp-ingest orchestrator after Stage 2 LLM emits processes.json.
#   --threshold-files N       min files in implemented_by[] to recurse (default 30)
#   --threshold-lines N       min total lines (default 3000)
#   --max-depth N             hard recursion-depth cap (default 3)
#   --no-recurse              disable recursion entirely (back to flat level-1)
uv run python -m hp_toolkit.ingest.recursion \
    --processes <project-dir>/intermediate/processes.json \
    --scan <project-dir>/intermediate/scan.json \
    --intermediate <project-dir>/intermediate \
    --current-depth 1
```

All commands also work programmatically — see *Programmatic API* below. Note: the full hp-ingest LLM pipeline dispatch (boundary / processes / leaf×N / architect / review subagents) runs via `/hp-ingest` in a Claude Code session, not via the Python CLI — the CLI handles the deterministic prep + merge + emit steps only. Every ingest run appends START / DONE / SKIP rows to `<output>/intermediate/progress.log` so external observers can `tail -f` a run live.

---

## Programmatic API

```python
from pathlib import Path
from hp_toolkit import load, validate, status_report
from hp_toolkit.render import mermaid, d2, cytoscape, svg, index, pdf
from hp_toolkit.render.tree import build_project_tree

project_dir = Path("examples/solar")
project = load(project_dir / "dictionary.yaml")
report  = validate(project)

if not report.ok:
    raise SystemExit(f"{len(report.errors)} validation errors")

# Generate source for any view
mmd = mermaid.render_context_diagram(project)
mmd = mermaid.render_dfd(project, parent_id="sys_root")
mmd = mermaid.render_state_machine(project, machine_id="proc_compute_balance")

# Cytoscape wrappers now accept the project tree + a current-path; the page
# gains a collapsible left sidebar with the full project nav.
tree = build_project_tree(project, project_dir)
html = cytoscape.wrap_context_html(project, tree=tree,
                                   current_path="00-context/context.generated.html")

# Project portal landing page
home = index.render_project_index_html(project, project_dir)

# Single-file PDF
pdf.render_project_pdf(project, project_dir)  # → project_dir/project.generated.pdf

# Render SVGs
svg.render_mermaid_to_svg("input.mmd", "output.svg")
svg.render_d2_to_svg("input.d2", "output.svg")

# Stage progress
print(status_report("examples/solar").format())
```

---

## Dictionary schema

A `dictionary.yaml` has sixteen top-level sections plus metadata (ten core HP + six modernization). All keys are stable string IDs by convention (`proc_*`, `term_*`, `flow_*`, `store_*`, `event_*`, `cmd_*`, `data_*`, `state_*`, `tx_*`, `pspec_*`, `am_*`, `af_*`, `ai_*`, `ams_*`, `ais_*`, `adr_*`, `budget_*`, `tpm_*`, `slo_*`, `ctx_*`, `acl_*`).

```yaml
project: "Solar Local Stack"
version: "0.1"
last_updated: 2026-05-22

entities:
  <id>:                       # e.g., proc_compute_balance, term_inverter, state_grid_tie
    kind: process              # system | terminator | process | data_store | state | state_composite
    label: "Energy Manager"
    level: 1                   # 0 (context), 1 (level-1 DFD), 2 (CSPEC), …
    description: |
      One-paragraph description.
    parent: sys_root           # parent entity id (defaults to sys_root for level-1)
    parent_state: state_grid_tie  # for nested states only
    parent_machine: proc_X     # for state entities — which CSPEC owns this state
    needs_cspec: true          # processes only — flags state-rich bubbles for Stage 3
    is_initial: true           # states only — exactly one per machine
    optional: false            # for optional terminators/processes (dashed in renders)

flows:
  flow_f1_telemetry:
    label: "F1: per-channel telemetry"
    kind: data                 # data | control | data_and_control
    source: term_inverter      # entity id
    target: sys_root
    medium: "Sub-1GHz radio + serial"   # informational
    notes: "..."
    refined_source: term_inverter            # level-N+1 endpoint refinement
    refined_target: proc_acquire_telemetry
    synchronicity: async       # modernization #2 — async | sync | streaming | batch
    delivery: at_least_once    # modernization #2 — at_least_once | at_most_once | exactly_once | best_effort
    context: ctx_controller    # modernization #5 — only required in multi-context projects

edges:                         # physical (non-data) connections; e.g., power, mechanical
  edge_power_to_sys:
    kind: physical_ac_power    # physical_ac_power | physical_dc_power | physical_interaction
    source: term_pge_grid
    target: sys_root
    notes: "240VAC service"

transitions:                   # state machine transitions (Stage 3)
  tx_init_to_grid:
    label: "self-test passed; Victron mode settled"
    parent_machine: proc_compute_balance
    source_state: state_initializing
    target_state: state_grid_tie
    event: "Initializing complete; mode reported as GridTie"
    action: "begin diversion loop"

pspecs:                        # leaf-process functional contracts (Stage 4)
  pspec_acquire_telemetry:
    parent_process: proc_acquire_telemetry
    # INPUTS and OUTPUTS are derived from dictionary.flows at validate
    # time; balancing is a validator rule (1988 §13.1).
    transformation:
      style: textual           # textual | equation | table | diagram | mixed
      body: |
        Each ingest cycle:
          Read F1 PER CHANNEL TELEMETRY from the inverter side.
          Read F3 NET GRID POWER from the grid-tied meter.
          Normalize all readings into NORMALIZED STATE and write to
          store_system_state.
    computational_constraints:           # optional — 2000 §4.3.3.9
      frequency: "≥ 1 Hz aggregate"
      timing: "Ingest → store latency < 1 s"
    comments: |                          # optional — 1988 §13.5
      Vendor adapter details live in the architecture model, not here.

architecture_modules:           # Stage 5 — 2000 §4.2.2.1
  am_controller_host:
    name: "Controller Host"
    module_number: "AM 1"
    kind: hardware              # hardware | software | organizational
    description: |
      Raspberry Pi running the on-prem controller service.
    # Allocation — bridge to the requirements model (2000 §4.2.5.4):
    allocated_processes:  [proc_acquire_telemetry, proc_dispatch_commands]
    allocated_cspecs:     [proc_compute_balance]
    allocated_stores:     [store_system_state]
    trust_zone: internal_lan    # modernization #8.1 — public | internal_lan | privileged | air_gapped | …
    context: ctx_controller     # modernization #5 — only in multi-context projects

architecture_flows:             # Stage 5 — 2000 §4.2.2.3
  af_state_to_dashboard:
    name: "state + alerts"
    source: am_controller_host
    target: am_dashboard_app
    kind: data                  # data | material | energy
    physical_description: "WebSocket push of state snapshots"
    allocated_flows: [flow_state_to_ui, flow_event_alert]

architecture_interconnects:     # Stage 5 — 2000 §4.2.6.1
  ai_local_lan:
    name: "Local LAN"
    endpoints: [am_controller_host, am_dashboard_app]
    carries:   [af_state_to_dashboard, af_input_to_controller]
    description: "Wired/wireless LAN; WebSocket + HTTP over TCP/IP."
    auth_required: mtls         # modernization #8.1 — none | password | api_key | oauth2 | mtls | …
    encryption: tls13           # modernization #8.1 — none | tls12 | tls13 | wpa3 | …
    stride_mitigations:         # modernization #8.2 — required when endpoints span trust zones
      spoofing: "mTLS client certificates pinned at the controller; cert rotation every 90 days."
      tampering: "TLS 1.3 record-layer MAC."
      repudiation: out_of_scope  # single-user; no audit-trail requirement
      info_disclosure: "TLS 1.3 with AEAD ciphersuites."
      denial_of_service: "Connection rate limit at the controller's NGINX front-end."
      elevation_of_privilege: "Capability tokens scoped to read-or-write per session."

architecture_module_specs:      # Stage 5 — 2000 §4.2.5.4
  ams_controller_host:
    parent_module: am_controller_host
    description: |
      Single-board computer running Linux + the HP-derived controller service.
    design_rationale: |
      Single-host architecture chosen over distributed setup because ...
    required_constraints:
      reliability: "MTBF > 8000 hours indoor mounted."
      cost:        "BoM ≤ $200 including UPS and enclosure."

architecture_interconnect_specs:  # Stage 5 — 2000 §4.2.6.2
  ais_local_lan:
    parent_interconnect: ai_local_lan
    description: |
      The owner's local network connecting the dashboard browser to the controller host.
    protocol_standard: "HTTP/1.1 (RFC 7230) + WebSocket (RFC 6455); JSON messages."
    # Modernization #8.3 — catalog references (also valid on AMS + ADR)
    references_mitre_attack: ["T1190", "T1078"]
    references_cwe:          ["CWE-306", "CWE-319"]
    references_compliance:   ["CCPA-1798.100"]

# ─── Modernization sections (post-2026-05-22) ───

adrs:                            # modernization #10 — Nygard 2011
  adr_001_local_only_dashboard:
    title: "Dashboard is local-only; no cloud edition for v1"
    status: accepted             # proposed | accepted | superseded | deprecated | rejected
    date: 2026-05-22
    deciders: ["Kevin"]
    context: |
      Telemetry data is privacy-sensitive; users do not want it leaving the LAN.
    decision: |
      The dashboard runs only on the local LAN. No cloud telemetry forwarding.
    consequences: |
      No remote monitoring; no cross-property aggregate views.
    references_mitre_attack: ["T1078"]
    references_cwe:          ["CWE-306"]

verification_plans:              # modernization #25 — per leaf process
  pspec_acquire_telemetry:
    method: ground_truth_replay  # analysis | inspection | test | demonstration | simulation | …
    description: |
      Recorded inverter traces from 7-day periods get replayed; the
      normalized state is diffed against the operator-blessed baseline.
    success_criteria: "Normalized state matches baseline within ±1% over 7-day replay."

budgets:                         # modernization #21 — NASA SE Handbook §6.7
  budget_diversion_loop_latency:
    name: "Diversion control loop latency"
    description: "End-to-end p99 latency from telemetry sample to relay command."
    ceiling: 1000                # design-time hard ceiling
    unit: ms
    allocated_to: [am_controller_host]

tpms:                            # modernization #22 — NASA SE Handbook §6.7.2
  tpm_diversion_response_p99:
    name: "Diversion p99 response time (measured)"
    derives_from_budget: budget_diversion_loop_latency
    current_value: 720
    threshold: 1000
    direction: less_is_better    # less_is_better | more_is_better
    unit: ms
    measurement_method: "Histograms over rolling 24h window."
    last_measured: 2026-05-22

service_level_objectives:        # modernization #32 — Google SRE
  slo_diversion_loop_latency:
    name: "Diversion loop p99 < 1s"
    sli:
      query: 'histogram_quantile(0.99, rate(diversion_loop_seconds_bucket[5m]))'
      unit: seconds
      description: "p99 diversion-loop latency over a 5m rate window."
    target: 1.0
    window: 30d
    error_budget_pct: 0.5
    applies_to: [am_controller_host]
    derives_from_tpm: tpm_diversion_response_p99
    runbook_on_burn: runbooks/slo-diversion-burn.md
    sla: "Diversion will respond within 1s for 99.5% of events over any 30-day window."

bounded_contexts:                # modernization #5 — Evans 2003 (paradigm shift)
  ctx_controller:
    name: "Controller"
    owner: "controller-team"
    ubiquitous_language: |
      Controller speaks setpoints, modes, and override events.
  ctx_dashboard:
    name: "Dashboard"
    owner: "frontend-team"
    ubiquitous_language: |
      Dashboard speaks views, actions, and operator commands.
# ACLs are entries in `entities:` with kind: translation:
#   acl_user_action_to_config:
#     kind: translation
#     source_context: ctx_dashboard
#     target_context: ctx_controller
#     source_term: "user action"
#     target_term: "override event"
#     pattern: anti_corruption_layer
```

PSPECs and architecture modules can also carry an `observability:` block (modernization #1 — metrics, traces, log categories, alerts → runbooks). See [`MODERNIZATION_DESIGN.md`](MODERNIZATION_DESIGN.md) §4.1 for the full shape and the [examples](../examples/) for lived instances.

Pydantic schemas in [`hp_toolkit/model.py`](hp_toolkit/model.py) are authoritative. Validation (`hp-validate`) catches dangling references, hierarchy inconsistencies, coverage gaps, PSPEC balancing violations, Stage 5 allocation gaps, modernization cross-references (STRIDE on cross-trust-zone interconnects, TPMs vs budgets, SLO `derives_from_tpm` resolution, ACL routing on cross-context flows, runbook path existence, MITRE / CWE / compliance ID formats), and reports coverage metrics for every modernization section (`stride_coverage_pct`, `verification_coverage_pct`, `observability_coverage_pct`, `slo_coverage_pct`, …). Status (`hp-status`) reports stage progress against the same schema.

---

## Examples

Two example projects in [`../examples/`](../examples/) exercise the full pipeline; a third is scaffolded but unadvanced.

- [`examples/solar/`](../examples/solar/) — Solar Local Stack (Hoymiles microinverters + Victron + grid orchestration). **All 5 stages locked + modernization layer**: 6 terminators, 6 processes + 1 CSPEC (Energy Manager — 13 states / 16 transitions), 5 PSPECs, 2 architecture modules (Controller Host + Dashboard App) + 1 interconnect (Local LAN), 2 ADRs, 2 budgets + 3 TPMs, 2 SLOs, full STRIDE on `ai_local_lan`, observability + V&V on `pspec_acquire_telemetry`, **2 bounded contexts + 1 ACL** (`ctx_controller` / `ctx_dashboard` joined by `acl_user_action_to_config`). Original dogfood — most mature.
- [`examples/fishing-rig/`](../examples/fishing-rig/) — AutoFishingRig. The transferability test — built from scratch on a completely different domain. **All 5 stages locked + modernization layer**: 5 terminators, 5 processes + 1 CSPEC (Bite Detector — 9 states / 18 transitions), 4 PSPECs, 2 architecture modules (Main Controller Board + Angler Mobile App) + 1 interconnect (BLE Link), 1 ADR, 2 budgets + 2 TPMs, 1 SLO, full STRIDE on `ai_ble`, observability + V&V on `pspec_acquire_tension`. Intentionally single-context (demonstrates the backward-compatible no-`bounded_contexts` path).
- [`examples/doorbell/`](../examples/doorbell/) — Smart Doorbell. Scaffolded via `hp-init`; Stage 1 in progress. Used as a reference for a fresh-scaffold project.

Both solar and fishing-rig render their full Context + DFD + CSPEC + PSPEC + AFD/AID + AMS/AIS + ADR + (solar) Context-Map + SLOs pipelines through `scripts/render_project.py` with no project-specific code. Each project also produces `project_index.generated.html` (portal landing) and `project.generated.pdf` (the example PDFs are committed; user-project PDFs stay gitignored).

---

## Tutorial

A step-by-step read-along walkthrough of fishing-rig from `hp-init` through Stage 5 lock is at [`TUTORIAL.md`](TUTORIAL.md).

---

## Repository layout

```
toolkit/
├── README.md                       ← this file
├── TUTORIAL.md                     ← worked end-to-end example (fishing-rig walk-through)
├── PSPEC_DESIGN.md                 ← Stage 4 design doc (book-faithful schema + validator rules)
├── ARCH_DESIGN.md                  ← Stage 5 design doc (book-faithful schema + validator rules)
├── MODERNIZATION_DESIGN.md         ← modernization items #1, #2, #8.1–8.3, #10, #21, #22, #25, #32, #33 — schema + validator rules
├── BOUNDED_CONTEXTS_DESIGN.md      ← modernization #5 — Evans-DDD paradigm shift; Path A vs B; ACL patterns
├── MODERNIZATION_TACTICS.md        ← AI-interaction-layer plan (Commits A/B/C: tactics + skill extensions + 6 new skills)
├── PORTAL_DESIGN.md                ← Project portal + PDF design (Commits 1/2/3: tree + sidebar + PDF)
├── INGEST_DESIGN.md                ← Brownfield ingest design (kg/brownfield-ingest: 6 agents + IR + emit)
├── bootstrap.sh                    ← environment setup (idempotent)
├── .puppeteer-config.json          ← mmdc sandbox config for Ubuntu 23.10+
├── pyproject.toml                  ← uv-managed Python project
├── uv.lock                         ← pinned dependencies
│
├── hp_toolkit/                     ← Python package
│   ├── __init__.py
│   ├── model.py                    ← Pydantic schemas (core HP + modernization)
│   ├── load.py                     ← dictionary.yaml → validated Project
│   ├── validate.py                 ← validators: reference / hierarchy / coverage / orphan / PSPEC balancing / architecture allocation / modernization rules + CLI
│   ├── status.py                   ← stage-progress report (Stages 1–5) + CLI
│   ├── render/
│   │   ├── mermaid.py              ← Context + DFD + CSPEC + AFD + AID + Context-Map
│   │   ├── d2.py                   ← same
│   │   ├── cytoscape.py            ← elements JSON + full HTML wrappers (now sidebar-aware)
│   │   ├── pspec.py                ← PSPEC markdown emitter + V&V + observability sections
│   │   ├── architecture.py         ← AMS + AIS markdown emitters + Verification + Budgets + TPMs + Observability + SLOs + STRIDE + LINDDUN + Catalog Refs
│   │   ├── adr.py                  ← per-ADR markdown sidecar (modernization #10)
│   │   ├── tree.py                 ← Project artifact tree — shared by sidebar + index + PDF (Portal Commit 1)
│   │   ├── sidebar.py              ← Collapsible left-sidebar HTML/CSS/JS (Portal Commit 2)
│   │   ├── markdown_artifact.py    ← Wrap markdown sidecars (PSPEC/AMS/AIS/ADR/runbook/SLOs) as sidebar'd HTML (Portal Commit 2)
│   │   ├── index.py                ← project_index.generated.html landing page (Portal Commit 1)
│   │   ├── pdf.py                  ← project.generated.pdf via WeasyPrint (Portal Commit 3)
│   │   └── svg.py                  ← orchestrate d2 + mmdc binaries
│   └── ingest/                     ← Brownfield ingest pipeline (kg/brownfield-ingest)
│       ├── schema.py               ← Pydantic IR types (IRNode, IREdge, ProjectScan, IRGraph) + HpRoleHint enum
│       ├── role_classifier.py      ← Per-file 6-category HP role hint (no LLM)
│       ├── significance.py         ← Tunable filter dropping tests / vendor / docs / lockfiles
│       ├── scan.py                 ← Stage 0 codebase walker → scan.json
│       ├── boundary_candidates.py  ← Stage 1 candidate extractor (HTTP / gRPC / CLI / consumers)
│       ├── process_candidates.py   ← Stage 2 candidate clusterer (by directory + import-cluster)
│       ├── state_machine_detector.py ← Stage 3 state-enum + transition extractor
│       ├── architecture_candidates.py ← Stage 5 deployment-unit extractor (Docker / k8s / terraform / packages)
│       ├── merge_graph.py          ← Deterministic IR merge + normalization + alias tables
│       └── emit_dictionary.py      ← IR → dictionary.yaml writer
│
├── scripts/
│   ├── hp_init.py                  ← scaffold a new project
│   ├── hp_ingest.py                ← brownfield ingest CLI (scan / prep-candidates / merge-emit)
│   ├── render_project.py           ← render any project end-to-end (incl. ADRs, slos.md, context-map)
│   ├── render_dogfood.py           ← solar-specific (legacy; use render_project.py)
│   └── check_dictionary.py         ← summary + hierarchy view
│
├── skills/                         ← Claude Code skill files (24 total: 10 core HP + 6 modernization + 8 ingest)
│   ├── README.md                   ← skill catalog
│   ├── hp-init.md
│   ├── hp-propose-{context,decomp,cspec,pspec,architecture}.md
│   ├── hp-confirm-naming.md
│   ├── hp-validate.md  ·  hp-render.md  ·  hp-status.md
│   ├── hp-capture-adr.md                            ← modernization #10
│   ├── hp-propose-threat-model.md                   ← modernization #8.2 + #8.3
│   ├── hp-propose-budgets-and-tpms.md               ← modernization #21 + #22
│   ├── hp-propose-observability.md                  ← modernization #1 + #33
│   ├── hp-propose-slos.md                           ← modernization #32
│   ├── hp-propose-bounded-contexts.md               ← modernization #5
│   ├── hp-ingest.md                                  ← brownfield: master orchestrator
│   ├── hp-ingest-scan.md                             ← brownfield Stage 0
│   ├── hp-ingest-glossary.md                         ← brownfield Stage 0c-curate (optional LLM glossary curation, H.4.b)
│   ├── hp-ingest-boundary.md                         ← brownfield Stage 1
│   ├── hp-ingest-processes.md                        ← brownfield Stage 2
│   ├── hp-ingest-leaf.md                             ← brownfield Stages 3+4 (parallel per process)
│   ├── hp-ingest-architect.md                        ← brownfield Stage 5
│   └── hp-ingest-review.md                           ← brownfield: final reviewer + emit
│
└── reference/
    └── HP_QUICK_REF.md             ← HP method vocabulary (60+ terms with modern analogs)
```

---

## Status

End-to-end render pipeline live and validated across two domains (solar, fishing-rig). Twenty-four skills drafted (seven with backing code; seventeen conversational). **All 5 HP stages + the modernization layer + the project portal + the brownfield ingest pipeline shipped.** Both demo projects locked from Stage 1 through Stage 5 plus modernization sections (ADRs, budgets, TPMs, SLOs, observability, V&V, STRIDE, catalog refs; solar adds bounded contexts + ACL). Every render emits `project_index.generated.html` (front-door page with collapsible sidebar) plus `project.generated.pdf` (single-file review pack: cover + clickable TOC + per-stage covers + all diagrams + all markdown sidecars + HP Quick Reference appendix). Brownfield ingest (`hp-ingest <codebase>`) takes an existing codebase through a multi-stage pipeline (scanner → docs-walker → glossary-extractor → glossary-curator → user-docs gatherer → testbed miner → recipe parser → boundary → processes → leaf×N → architect-with-rationale-evidence → reviewer) to a draft `dictionary.yaml` — Python does ~80% of the structural work, LLM agents make the architectural judgment calls; first dogfood target was cloudctlplane (post-dogfood input-expansion arc landed on `kg/hp-ingest-input-expansion`).

See [`../PLAN.md`](../PLAN.md) for design rationale, methodology tactics (including the post-2026-05-22 Modernization Tactics section), the AI moves catalog, and a chronological log of decisions.

---

## Further reading

- [`reference/HP_QUICK_REF.md`](reference/HP_QUICK_REF.md) — HP terminology card
- [`../PLAN.md`](../PLAN.md) — design rationale, decisions, open questions
- [`skills/`](skills/) — methodology surface, one file per skill
- Hatley & Pirbhai, *Strategies for Real-Time System Specification* (1988) — the original method.
- Hatley, Hruschka & Pirbhai, *Process for System Architecture and Requirements Engineering* (2000) — adds the Architecture Model + Mechanisms.

---

## License

TBD.
