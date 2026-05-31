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

**Recommended IDE setup:** VS Code + [Markdown Preview Enhanced](https://marketplace.visualstudio.com/items?itemName=shd101wyy.markdown-preview-enhanced) (MPE). MPE renders embedded Mermaid/D2 in preview and lets you click `[ ]` → `[x]` checkboxes directly — the form-based proposal pattern (below) depends on this.

---

## The mental model

Three ideas carry the rest of the toolkit:

### 1. Dictionary as source of truth

Every project has a single `dictionary.yaml` at its root — HP's Requirements Dictionary in YAML form. Every entity, flow, edge, and transition is declared there once. All rendered artifacts (`.mmd`, `.d2`, `.html`, `.svg`) are **derived**: regenerated from the dictionary on demand. Rename a flow in one place and every diagram updates on the next render. The dictionary is the only file you hand-edit; everything else is generated.

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
- 7–8 numbered decisions; each with alternatives as `- [ ]` checkboxes; Claude's recommended default **pre-checked** with provenance ("extracted from your description"; "matches solar's pattern"; "AI inference")

You open the proposal in MPE, click `[ ]` → `[x]` for any overrides, save **once**, and ping back. The skill parses the saved file in one pass and writes the `## ✅ Status: Locked YYYY-MM-DD` header + populates `dictionary.yaml` with the resulting entities.

This replaces chat round-trips with a single-save batch review. The proposal becomes the locked audit record — every project has a permanent paper trail of what was decided, why (pre-checked defaults preserve Claude's reasoning), and what alternatives were considered.

After lock, [`hp-confirm-naming`](skills/hp-confirm-naming.md) runs a second form-based pass on every working name (`accept / rename / alias`), so the naming review is explicit and reviewable.

---

## Workflow

A full project lifecycle, end-to-end:

```text
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
(hp-status anywhere to check progress)
(hp-validate anywhere to check integrity)
```

Each `hp-render` produces three views — Mermaid, D2, Cytoscape HTML — plus SVGs. The Cytoscape HTML is the **graphical IDE view**: single-click an entity for side-panel detail, double-click a decomposable bubble to navigate to its level-N+1 DFD, `↑ Parent` link to walk back up. Every entity links to its `dictionary.yaml` entry and to its HP reference card.

---

## Skills

Ten skills make up the methodology surface. Each is documented in [`skills/`](skills/) as a Claude Code skill file (markdown + YAML frontmatter). Five have backing Python; five are conversational.

| Skill | Stage / purpose | Backing code |
|---|---|:---:|
| [`hp-init`](skills/hp-init.md) | Scaffold a new HP project | ✅ |
| [`hp-propose-context`](skills/hp-propose-context.md) | Stage 1 form-based proposal | ⬜ |
| [`hp-propose-decomp`](skills/hp-propose-decomp.md) | Stage 2 form-based proposal | ⬜ |
| [`hp-propose-cspec`](skills/hp-propose-cspec.md) | Stage 3 form-based proposal | ⬜ |
| [`hp-propose-pspec`](skills/hp-propose-pspec.md) | Stage 4 form-based proposal | ⬜ |
| [`hp-propose-architecture`](skills/hp-propose-architecture.md) | Stage 5 form-based proposal | ⬜ |
| [`hp-confirm-naming`](skills/hp-confirm-naming.md) | Form-based naming review after any move that introduces named entities | ⬜ |
| [`hp-validate`](skills/hp-validate.md) | Reference integrity / hierarchy / coverage / orphan detection / PSPEC balancing / architecture allocation | ✅ |
| [`hp-render`](skills/hp-render.md) | Regenerate diagrams + SVGs + PSPEC + AMS/AIS markdown from `dictionary.yaml` | ✅ |
| [`hp-status`](skills/hp-status.md) | Report stages reached, validation, artifact freshness, open questions | ✅ |

The conversational skills (`hp-propose-*`, `hp-confirm-naming`) work by Claude reading the skill markdown and following the behavior spec. They don't need a Python implementation to invoke — the markdown *is* the executable specification.

---

## CLI

```bash
cd toolkit

# Scaffold a new project
uv run python scripts/hp_init.py <project-name> --label "<Display>" --description "..."

# Validate a dictionary
uv run python -m hp_toolkit.validate <path/to/dictionary.yaml>

# Render all artifacts for a project
uv run python scripts/render_project.py <project-directory>

# Report stage progress
uv run python -m hp_toolkit.status <project-directory>
```

All four commands also work programmatically — see *Programmatic API* below.

---

## Programmatic API

```python
from hp_toolkit import load, validate, status_report
from hp_toolkit.render import mermaid, d2, cytoscape, svg

project = load("examples/solar/dictionary.yaml")
report  = validate(project)

if not report.ok:
    raise SystemExit(f"{len(report.errors)} validation errors")

# Generate source for any view
mmd = mermaid.render_context_diagram(project)
mmd = mermaid.render_dfd(project, parent_id="sys_root")
mmd = mermaid.render_state_machine(project, machine_id="proc_compute_balance")

# Same shape for D2 and Cytoscape (cytoscape additionally has wrap_*_html)
html = cytoscape.wrap_context_html(project)

# Render SVGs
svg.render_mermaid_to_svg("input.mmd", "output.svg")
svg.render_d2_to_svg("input.d2", "output.svg")

# Stage progress
print(status_report("examples/solar").format())
```

---

## Dictionary schema

A `dictionary.yaml` has ten top-level sections plus metadata. All keys are stable string IDs by convention (`proc_*`, `term_*`, `flow_*`, `store_*`, `event_*`, `cmd_*`, `data_*`, `state_*`, `tx_*`, `pspec_*`, `am_*`, `af_*`, `ai_*`, `ams_*`, `ais_*`).

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
```

Pydantic schemas in [`hp_toolkit/model.py`](hp_toolkit/model.py) are authoritative. Validation (`hp-validate`) catches dangling references, hierarchy inconsistencies, coverage gaps, PSPEC balancing violations, and Stage 5 allocation gaps; status (`hp-status`) reports stage progress against the same schema.

---

## Examples

Two example projects in [`../examples/`](../examples/) exercise the full pipeline; a third is scaffolded but unadvanced.

- [`examples/solar/`](../examples/solar/) — Solar Local Stack (Hoymiles microinverters + Victron + grid orchestration). **All 5 stages locked**: 6 terminators, 6 processes + 1 CSPEC (Energy Manager — 13 states / 16 transitions), 5 PSPECs, 2 architecture modules (Controller Host + Dashboard App) + 1 interconnect (Local LAN). Original dogfood — most mature.
- [`examples/fishing-rig/`](../examples/fishing-rig/) — AutoFishingRig. The transferability test — built from scratch on a completely different domain. **All 5 stages locked**: 5 terminators, 5 processes + 1 CSPEC (Bite Detector — 9 states / 18 transitions), 4 PSPECs, 2 architecture modules (Main Controller Board + Angler Mobile App) + 1 interconnect (BLE Link).
- [`examples/doorbell/`](../examples/doorbell/) — Smart Doorbell. Scaffolded via `hp-init`; Stage 1 in progress. Used as a reference for a fresh-scaffold project.

Both solar and fishing-rig render their full Context + DFD + CSPEC + PSPEC + AFD/AID + AMS/AIS pipelines through `scripts/render_project.py` with no project-specific code.

---

## Tutorial

A step-by-step read-along walkthrough of fishing-rig from `hp-init` through Stage 5 lock is at [`TUTORIAL.md`](TUTORIAL.md).

---

## Repository layout

```
toolkit/
├── README.md                  ← this file
├── TUTORIAL.md                ← worked end-to-end example (fishing-rig walk-through)
├── PSPEC_DESIGN.md            ← Stage 4 design doc (book-faithful schema + validator rules)
├── ARCH_DESIGN.md             ← Stage 5 design doc (book-faithful schema + validator rules)
├── bootstrap.sh               ← environment setup (idempotent)
├── .puppeteer-config.json     ← mmdc sandbox config for Ubuntu 23.10+
├── pyproject.toml             ← uv-managed Python project
├── uv.lock                    ← pinned dependencies
│
├── hp_toolkit/                ← Python package
│   ├── __init__.py
│   ├── model.py               ← Pydantic schemas
│   ├── load.py                ← dictionary.yaml → validated Project
│   ├── validate.py            ← validators (reference / hierarchy / coverage / orphan / PSPEC balancing / architecture allocation) + CLI
│   ├── status.py              ← stage-progress report (Stages 1–5) + CLI
│   └── render/
│       ├── mermaid.py         ← Context + DFD + CSPEC + AFD + AID
│       ├── d2.py              ← same
│       ├── cytoscape.py       ← elements JSON + full HTML wrappers (Context, DFD, CSPEC, AFD, AID)
│       ├── pspec.py           ← PSPEC markdown emitter (2000 Fig 4.46 format)
│       ├── architecture.py    ← AMS + AIS markdown emitters (2000 §4.2.5.4 / §4.2.6.2)
│       └── svg.py             ← orchestrate d2 + mmdc binaries
│
├── scripts/
│   ├── hp_init.py             ← scaffold a new project
│   ├── render_project.py      ← render any project end-to-end
│   ├── render_dogfood.py      ← solar-specific (legacy; use render_project.py)
│   └── check_dictionary.py    ← summary + hierarchy view
│
├── skills/                    ← Claude Code skill files (10 total)
│   ├── README.md              ← skill catalog
│   ├── hp-init.md
│   ├── hp-propose-{context,decomp,cspec,pspec,architecture}.md
│   ├── hp-confirm-naming.md
│   ├── hp-validate.md
│   ├── hp-render.md
│   └── hp-status.md
│
└── reference/
    └── HP_QUICK_REF.md        ← HP method vocabulary (60+ terms with modern analogs)
```

---

## Status

End-to-end render pipeline live and validated across two domains (solar, fishing-rig). Ten skills drafted (five with backing code). **All 5 HP stages supported end-to-end** — both demo projects locked from Stage 1 (Context Diagram) through Stage 5 (Architecture Model).

See [`../PLAN.md`](../PLAN.md) for design rationale, methodology tactics, the AI moves catalog, and a chronological log of decisions.

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
