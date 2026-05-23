# Tutorial — Walking through an HP project

This tutorial walks you through a complete HP project from scaffold to Stage 5 lock, using the **fishing-rig** example that ships with this repo. You'll run real toolkit commands against artifacts that already exist, see how each stage produces its outputs, and understand the form-based proposal pattern by inspecting how the decisions were made.

**Estimated time:** 45 minutes reading + running.
**Prerequisite:** install completed (`bash toolkit/bootstrap.sh`); VS Code + Markdown Preview Enhanced recommended.
**Reference:** [README.md](README.md) for concepts; [`reference/HP_QUICK_REF.md`](reference/HP_QUICK_REF.md) for HP terminology.

---

## The project: AutoFishingRig

A motorized fishing rig that detects a bite (line-tension spike), sets the hook automatically, and reels the fish in. Sensors: line-tension. Actuators: reel motor. Operator: angler. Optional cloud catch-log. Small enough to fit on one page, real enough to exercise every stage.

It lives at [`../examples/fishing-rig/`](../examples/fishing-rig/). Run all commands below from the **repo root** unless noted otherwise.

---

## Stage 0 — Scaffolding (already done; here's how)

Every new HP project starts with `hp-init`:

```bash
cd toolkit
uv run python scripts/hp_init.py fishing-rig \
    --label "AutoFishingRig" \
    --description "Motorized rig that auto-detects bites and reels in fish."
```

This creates the directory layout + an empty `dictionary.yaml` with only `sys_root`, plus a Stage 1 proposal stub. fishing-rig already has this from when it was created — you can see what a fresh scaffold looks like at [`../examples/doorbell/`](../examples/doorbell/) instead (a smart-doorbell project produced by `hp-init` but not yet advanced).

Check fishing-rig's current state:

```bash
cd toolkit
uv run python -m hp_toolkit.status ../examples/fishing-rig
```

You should see:

```
=== AutoFishingRig — Project Status ===

Stages
  ✅ Stage 1 — Context Diagram                5 terminator(s); proposal locked
  ✅ Stage 2 — Level-1 DFD                    5 internal process(es); proposal locked
  ✅ Stage 3 — CSPECs                         1 locked CSPEC(s); 9 states + 18 transitions
  ✅ Stage 4 — PSPECs                         4/4 leaf processes have PSPECs
  ✅ Stage 5 — Architecture model             2 module(s); 2 flow(s); 1 interconnect(s); 5/5 leaf processes allocated; 2/2 AMS
```

All five implemented stages are locked. We'll walk through them in order.

---

## Stage 1 — Context Diagram

**Goal of this stage:** pin down the system boundary. What's *inside* the box? What's outside? What flows cross the boundary?

### What was decided

Open [`../examples/fishing-rig/00-context/proposal.md`](../examples/fishing-rig/00-context/proposal.md). At the top you'll see the **decisions table** — what got locked and how:

```
| # | Decision                          | Resolution                                              |
|---|-----------------------------------|---------------------------------------------------------|
| 1 | System name                       | AutoFishingRig                                          |
| 2 | System scope                      | Medium — controller + integrated sensors/actuators      |
| 3 | Fish as a separate terminator     | Yes — interacts with Line via a physical edge           |
| 4 | Cloud terminator                  | Optional — off by default; angler-enabled               |
| 5 | Power modeling                    | Physical edge (no data flow)                            |
| 6 | Flow naming                       | F1-Fn numbering with descriptive labels                 |
| 7 | Anything else                     | No overrides                                            |
```

Scroll down. Below the locked block you'll see the **proposal section** as it looked before lock: a draft Mermaid diagram of the proposed Context, followed by each decision with alternatives as `- [x]` (chosen) and `- [ ]` (not chosen) checkboxes, each with provenance ("matches solar's pattern"; "AI inference from your description").

**This is the form-based proposal pattern.** Claude drafted the proposal with recommended defaults pre-checked. The user opened it in MPE, toggled overrides (none in this case), saved once, and Claude locked it. No chat round-trips; one durable artifact.

### What was produced

The lock-in populated [`../examples/fishing-rig/dictionary.yaml`](../examples/fishing-rig/dictionary.yaml) with:

- `sys_root` — the AutoFishingRig system
- 5 terminator entities — `term_angler`, `term_fish`, `term_line`, `term_power`, `term_cloud`
- 4 boundary data flows + 1 optional flow (`flow_f1_angler_config`, `flow_f2_status`, `flow_f3_tension`, `flow_f4_torque`, `flow_f6_catch_log`)
- 2 physical edges — power source → system, fish → line

Open [`../examples/fishing-rig/dictionary.yaml`](../examples/fishing-rig/dictionary.yaml) and find the entities. Each entity has a `kind`, a `label`, a `level`, and a `description`. This is the canonical Requirements Dictionary — every artifact below is regenerated from this file.

### Rendering

The rendered Context Diagram lives at three sidecar files under `00-context/`:

```bash
ls examples/fishing-rig/00-context/
# context.generated.html               — Cytoscape interactive workspace
# context.generated-mermaid.svg        — static SVG from Mermaid
# context.generated-d2.svg             — static SVG from D2
# proposal.md                          — the locked form-based proposal
```

**Open [`../examples/fishing-rig/00-context/context.generated.html`](../examples/fishing-rig/00-context/context.generated.html) in a browser.** This is the graphical IDE view:

- **Single-click** any entity → side panel shows its dictionary description.
- **Double-click** the central `AutoFishingRig` bubble (it has a double border = decomposable) → navigates to the level-1 DFD.
- Top-right legend explains every node + edge kind.
- Top nav has links to `dictionary.yaml` and `HP_QUICK_REF.md`.

To regenerate every view from `dictionary.yaml`:

```bash
cd toolkit
uv run python scripts/render_project.py ../examples/fishing-rig
```

This is the **dictionary-as-source-of-truth** payoff: edit a label in `dictionary.yaml`, rerun this command, and every diagram updates.

---

## Stage 2 — Level-1 DFD

**Goal of this stage:** decompose the single `sys_root` bubble into the internal processes that produce/consume the level-0 flows. Identify which internal process is *state-rich* enough to need a CSPEC.

### What was decided

Open [`../examples/fishing-rig/01-level1/proposal.md`](../examples/fishing-rig/01-level1/proposal.md). The decision set is larger than Stage 1:

```
| # | Decision                          | Resolution                                              |
|---|-----------------------------------|---------------------------------------------------------|
| 1 | Decomposition coarseness          | 5 bubbles (4 mandatory + Cloud Forward optional)        |
| 2 | Sensor sampling / tension history | store_system_state holds latest + recent buffer         |
| 3 | Data store explicit vs implicit   | Explicit store_system_state                             |
| 4 | Bite Detector scope               | Combined: state machine + motor command generation      |
| 5 | Internal flow style               | Hybrid — events + periodic 50–200 Hz tension sampling   |
| 6 | Fault handling                    | Inside Bite Detector's CSPEC                            |
| 7 | Naming convention                 | Keep proc_* / store_* / event_* prefixes                |
| 8 | Anything else                     | No overrides                                            |
```

Decision 4 is the key one: **Bite Detector is the state-rich bubble** — it gets `needs_cspec: true` in the dictionary and unlocks Stage 3.

Scroll past the locked block in the proposal. You'll see:

- A **context recap** at the top — an embedded SVG of the locked level-0 Context Diagram. Every level-1 proposal recaps the parent so the reader doesn't have to context-switch. (Tactic: *Recap with diagrams, not text walls*.)
- A **proposed decomposition diagram** — [`../examples/fishing-rig/01-level1/proposal-dfd.svg`](../examples/fishing-rig/01-level1/proposal-dfd.svg). This is the draft DFD with working names, embedded inline so the reader sees the *shape* before reading the decisions. (Tactic: *Propose graphically before prose*.)
- A **bubble roles table** with one-line summaries of each proposed internal process.
- Then the 8 numbered decisions.

### Boundary flow refinement

Every level-0 boundary flow must appear at level-1 with its endpoint refined to an internal process. Open [`../examples/fishing-rig/dictionary.yaml`](../examples/fishing-rig/dictionary.yaml) and find a boundary flow, e.g.:

```yaml
flow_f3_tension:
  label: "F3: tension feedback"
  source: term_line                    # level-0 source (still the terminator)
  target: sys_root                     # level-0 target (still sys_root)
  refined_target: proc_acquire_tension # level-1 target (which internal consumes this)
  kind: data
  medium: "analog sensor → ADC"
```

The `refined_target` is what makes the level-1 DFD balance — the internal endpoint of every boundary flow is known.

`hp-validate` catches missed refinements. Try it:

```bash
cd toolkit
uv run python -m hp_toolkit.validate ../examples/fishing-rig/dictionary.yaml
```

You should see no errors and a coverage report.

### Hypertext navigation

**Open [`../examples/fishing-rig/01-level1/dfd.generated.html`](../examples/fishing-rig/01-level1/dfd.generated.html) in a browser.**

- The five internal bubbles are visible.
- `Bite Detector` has a double border (it's `needs_cspec: true` — decomposable into a CSPEC).
- **Double-click `Bite Detector`** → navigates to its CSPEC.
- `↑ Parent` link in the top nav → back to the Context Diagram.
- `store_system_state` (the data store) renders as a barrel shape per HP convention.

---

## Stage 3 — CSPEC

**Goal of this stage:** specify the control behavior of the `needs_cspec: true` bubble as a hierarchical state machine.

### What was decided

Open [`../examples/fishing-rig/01-level1/cspecs/bite-detector/proposal.md`](../examples/fishing-rig/01-level1/cspecs/bite-detector/proposal.md). Decision set is again 7–8 items covering state structure, sub-states, fault granularity, timing model (event-driven? periodic? hybrid?), override handling, etc.

The proposal embeds:

- A **context recap** — the locked level-1 DFD with the Bite Detector bubble highlighted, so the reader sees which bubble this CSPEC specifies.
- A **proposed state diagram** — [`../examples/fishing-rig/01-level1/cspecs/bite-detector/proposal-states.svg`](../examples/fishing-rig/01-level1/cspecs/bite-detector/proposal-states.svg). A Mermaid `stateDiagram-v2` showing modes + sub-states + transitions, with working names.
- The 7–8 numbered decisions with alternatives.

### What was produced

The lock-in added to `dictionary.yaml`:

- 9 state entities (kind `state`)
- 18 transition entries (`tx_*`) with `parent_machine: proc_bite_detector`, `source_state`, `target_state`, `event`, `action`

Open the dictionary and find a state:

```yaml
state_initializing:
  kind: state
  label: "Initializing"
  level: 2
  parent: proc_bite_detector           # which CSPEC owns this state
  is_initial: true                     # exactly one state per machine is initial
  description: "Startup self-test. Verify motor and sensor are responsive."
```

And a transition:

```yaml
tx_armed_to_bite:
  label: "tension spike"
  source_state: state_armed
  target_state: state_bite_detected
  parent_machine: proc_bite_detector
  event: "tension > bite_threshold (rising)"
  action: "start hook_set_delay timer; emit alert (bite)"
```

### Hypertext navigation

**Open [`../examples/fishing-rig/01-level1/cspecs/bite-detector/cspec.generated.html`](../examples/fishing-rig/01-level1/cspecs/bite-detector/cspec.generated.html) in a browser.**

- Hierarchical state machine rendered with compound nodes (Cytoscape supports nested groups).
- Single-click any state → side panel shows description.
- `↑ Parent` link → back to the level-1 DFD.
- The initial state is marked distinctly.

---

## Stage 4 — PSPECs

**Goal of this stage:** specify each *remaining* leaf process — the bubbles that don't decompose further and don't have a CSPEC. Each gets one PSPEC: a functional contract following the 2000 Fig 4.46 format (INPUTS / OUTPUTS / TRANSFORMATION).

> "The primary role of the process specification is to describe how its outputs are generated from its inputs; it must do nothing more and nothing less." — 1988 §13.1

In fishing-rig, Bite Detector has a CSPEC (Stage 3), so it's exempt. The remaining four leaf processes each need a PSPEC:

| Process | PSPEC |
|---|---|
| `proc_acquire_tension` | [`pspecs/acquire-tension.md`](../examples/fishing-rig/01-level1/pspecs/acquire-tension.md) |
| `proc_reel_controller` | [`pspecs/reel-controller.md`](../examples/fishing-rig/01-level1/pspecs/reel-controller.md) |
| `proc_serve_ui` | [`pspecs/serve-ui.md`](../examples/fishing-rig/01-level1/pspecs/serve-ui.md) |
| `proc_cloud_forward` | [`pspecs/cloud-forward.md`](../examples/fishing-rig/01-level1/pspecs/cloud-forward.md) |

### What a PSPEC looks like

Open [`../examples/fishing-rig/01-level1/pspecs/acquire-tension.md`](../examples/fishing-rig/01-level1/pspecs/acquire-tension.md). This is the rendered sidecar for `proc_acquire_tension`. The format is exactly Fig 4.46 from the 2000 HP book:

- **INPUTS** — the flows whose `target` (or `refined_target`) is this process. The PSPEC author does *not* declare these; they are derived from `dictionary.flows` at render time.
- **OUTPUTS** — same, on the source side.
- **TRANSFORMATION** — the spec body. One of five styles: `textual` (structured English; the most common), `equation`, `table`, `diagram`, or `mixed`. Books explicitly forbid code/pseudocode (1988 §13.2).
- **COMPUTATIONAL CONSTRAINTS** (optional, 2000 §4.3.3.9) — frequency, accuracy, timing.
- **COMMENTS** (optional, 1988 §13.5) — rationale; not part of the formal spec.

### What's in the dictionary

The PSPEC entry itself is small — it carries only the transformation body + optional constraints + optional comments. Open [`../examples/fishing-rig/dictionary.yaml`](../examples/fishing-rig/dictionary.yaml) and find `pspec_acquire_tension`:

```yaml
pspec_acquire_tension:
  parent_process: proc_acquire_tension
  transformation:
    style: textual
    body: |
      Every sampling cycle:
        Read F3 TENSION from the analog input.
        Convert to engineering units using the sensor calibration.
        Update TENSION SAMPLES in store_system_state with the latest value
        and append it to the recent-history buffer (retain N most recent).
  computational_constraints:
    frequency: "50–200 Hz sampling rate (configurable; default 100 Hz)"
    accuracy: "±1% of measured tension"
    timing: "Sample → store_system_state write latency < 5 ms"
  comments: |
    First-cut PSPEC. Recent-history buffer size N pending Stage 5 sizing.
```

Notice the textual body uses **capitalized flow names** (`F3 TENSION`, `TENSION SAMPLES`) — 1988 §13.4 requires names to match dictionary entries exactly; this is what makes the **balancing rule** validatable.

### Balancing

The 1988 book is precise (§13.1): every PSPEC input must appear in the body, every output must be generated by the body, and the body must not reference flows that aren't inputs or outputs. The validator enforces this.

Try breaking balancing to see the error. Open [`../examples/fishing-rig/dictionary.yaml`](../examples/fishing-rig/dictionary.yaml), find `pspec_acquire_tension`, and temporarily remove the `TENSION SAMPLES` reference from the body. Then:

```bash
cd toolkit
uv run python -m hp_toolkit.validate ../examples/fishing-rig/dictionary.yaml
```

You should see:

```
✗ pspec [pspec_acquire_tension]: output flow 'flow_tension_to_state' (label 'tension samples') not generated by transformation body — balancing rule (1988 §13.1)
```

Revert the change when you're done.

### Hypertext navigation

**Open [`../examples/fishing-rig/01-level1/dfd.generated.html`](../examples/fishing-rig/01-level1/dfd.generated.html) in a browser** and click `Acquire Tension`. The side panel now shows a `► PSPEC` link — single-click to navigate. This same pattern applies to every leaf process with a PSPEC.

---

## Stage 5 — Architecture Model

**Goal of this stage:** map the *what* (Stages 1–4) onto the *how* — the actual hardware, software, and organizational modules the system is built from. The bridge is **allocation**: every leaf requirements process / CSPEC / data store gets assigned to one or more architecture modules.

> "The architecture model shows the physical reality of the system as it is, or will be, built." — 2000 §4.2.1

The Architecture Model has six core element types (per [`ARCH_DESIGN.md`](ARCH_DESIGN.md)): Architecture Module, Architecture Flow, Architecture Interconnect, AMS (per-module spec), AIS (per-interconnect spec), and the Architecture Dictionary (integrated into the existing `dictionary.yaml`).

### What was decided

Fishing-rig's architecture is intentionally small: an ESP32-based controller board and a mobile app. Open [`../examples/fishing-rig/dictionary.yaml`](../examples/fishing-rig/dictionary.yaml) and scroll to `architecture_modules:`. Two modules:

| Module | Kind | Allocations |
|---|---|---|
| `am_controller` (AM 1) — Main Controller Board | hardware | `proc_acquire_tension`, `proc_reel_controller`, `proc_cloud_forward`, `proc_bite_detector` (CSPEC), `store_system_state` |
| `am_angler_app` (AM 2) — Angler Mobile App | software | `proc_serve_ui` |

Notice the **allocation bridge**: every leaf process from Stages 1–4 lands on exactly one architecture module here. `proc_bite_detector` is listed under `allocated_cspecs:` (state-rich) rather than `allocated_processes:` (book convention: 2000 §4.2.5.4).

### Architecture flows

Two flows between the modules, carrying the requirements-level flows:

```yaml
af_telemetry_to_app:        # controller → app (BLE notifications)
  allocated_flows: [flow_state_to_ui, flow_alert, flow_f2_status]

af_config_to_ctrl:          # app → controller (BLE writes)
  allocated_flows: [flow_f1_angler_config, flow_override]
```

`allocated_flows:` is the architecture dictionary's record of which requirements flows ride each architecture flow (2000 §4.2.8). The validator's `architecture_flow_coverage_pct` reports how many requirements flows are accounted for.

### Architecture interconnects

One physical channel — BLE — carries both architecture flows. Interconnects can also exist without flows (e.g., power/ground buses) per 2000 §4.2.6.1.

```yaml
ai_ble:
  endpoints: [am_controller, am_angler_app]
  carries:   [af_telemetry_to_app, af_config_to_ctrl]
  description: "Bluetooth Low Energy 5.0 link ..."
```

### AMS — Architecture Module Specification

Open [`../examples/fishing-rig/architecture/specs/controller.md`](../examples/fishing-rig/architecture/specs/controller.md). This is the rendered sidecar for `am_controller`. The format follows the 2000 §4.2.5.4 typical-contents layout: DESCRIPTION → CROSS-REFERENCE (the allocation table) → DESIGN RATIONALE → DESIGN JUSTIFICATION → REQUIRED CONSTRAINTS (reliability/safety/physical/cost/...) → INTERFACES.

The CROSS-REFERENCE table is derived from the module entry's `allocated_*` lists — you don't repeat them in the AMS prose. The spec captures the *prose around* the allocation: why this design was chosen, what constraints it must meet, what its external interfaces look like.

### AIS — Architecture Interconnect Specification

Open [`../examples/fishing-rig/architecture/specs/interconnects/ble.md`](../examples/fishing-rig/architecture/specs/interconnects/ble.md). This is `ai_ble`'s AIS. It describes the physical channel — protocol standard, design rationale, timing/physical constraints — and lists which architecture flows ride on it. Per 2000 §4.2.6.2, the AIS describes the *channel*; the dictionary records *what rides on it*.

### Rendering

**Open [`../examples/fishing-rig/architecture/afd.generated.html`](../examples/fishing-rig/architecture/afd.generated.html) in a browser.** The AFD shows the two modules as bubtangles (rounded rectangles, distinct from DFD process circles), color-coded by kind (hardware = orange tint; software = blue tint). The architecture flows are labeled arrows.

**Open [`../examples/fishing-rig/architecture/aid.generated.html`](../examples/fishing-rig/architecture/aid.generated.html).** Same modules but with the BLE interconnect as a thick blue undirected link — the physical channel view.

### Allocation as a hard validator rule

Try breaking allocation to see the error. Open [`../examples/fishing-rig/dictionary.yaml`](../examples/fishing-rig/dictionary.yaml), find `am_controller`, and temporarily remove `proc_acquire_tension` from its `allocated_processes:` list. Then:

```bash
cd toolkit
uv run python -m hp_toolkit.validate ../examples/fishing-rig/dictionary.yaml
```

You should see:

```
✗ architecture [proc_acquire_tension]: leaf requirements process not allocated to any architecture module (2000 §4.2.5.4)
```

Revert the change when you're done. This is the **allocation completeness rule** — every leaf process / CSPEC / data store from Stages 1–4 must end up assigned to ≥ 1 architecture module.

---

## Closing the loop

You've now seen what each stage produces. Two more commands close the loop.

### Validate the whole project

```bash
cd toolkit
uv run python -m hp_toolkit.validate ../examples/fishing-rig/dictionary.yaml
```

Output (truncated):

```
== Coverage metrics ==
  description_coverage_pct           [████████████████████] 100.0%
  flow_medium_coverage_pct           [████████░░░░░░░░░░░░]  41.7%
  flow_notes_coverage_pct            [████████████████░░░░]  83.3%

== Counts ==
  architecture_flows                 2
  architecture_interconnects         1
  architecture_modules               2
  entities__terminator               5
  entities__process                  5
  entities__state                    9
  leaf_processes                     4
  pspecs_total                       4
  ...

VALID — no errors
```

Note the four Stage-5 coverage metrics (`architecture_module_coverage_pct`, `architecture_flow_coverage_pct`, `ams_coverage_pct`, `ais_coverage_pct` — all at 100% on fishing-rig) and the Stage-4 `pspec_coverage_pct` (also 100%). `hp-validate` catches dangling references, hierarchy inconsistencies (e.g., `parent_state` on a non-state entity), orphan entities, coverage gaps, PSPEC balancing violations, and Stage-5 allocation gaps. Run it after every dictionary edit.

### Try the dictionary-as-source-of-truth payoff

Open `../examples/fishing-rig/dictionary.yaml` and rename one entity's label — say change `"Bite Detector"` to `"Bite Sensor"` on `proc_bite_detector`. Save.

```bash
cd toolkit
uv run python scripts/render_project.py ../examples/fishing-rig
```

Every generated artifact (Mermaid, D2, Cytoscape HTML, SVG, PSPEC markdown, AMS markdown) — at all five stages — picks up the new label. Revert the change when you're done.

---

## What you've seen

Seven ideas, all grounded in the artifacts you just walked through:

1. **`dictionary.yaml` is the only file you hand-edit.** Every diagram, PSPEC, AMS, and AIS sidecar is derived.
2. **Each stage locks through a form-based proposal**, not a chat conversation. The proposal is the audit record: decisions, alternatives considered, defaults pre-checked, provenance attached.
3. **Three views per artifact** (Mermaid, D2, Cytoscape HTML) serve three moments: docs, declarative, interactive IDE.
4. **The Cytoscape HTML is hypertext.** Drill down on decomposable bubbles, walk up via `↑ Parent`, link to dictionary entries, PSPEC sidecars, AMS sidecars, and HP reference cards.
5. **PSPECs follow 2000 Fig 4.46 exactly** — INPUTS / OUTPUTS / TRANSFORMATION. INPUTS and OUTPUTS are derived from `dictionary.flows`; the PSPEC only carries the transformation body, optional constraints, and optional comments. The validator enforces balancing (1988 §13.1).
6. **Stage 5 is the bridge from requirements to architecture.** Every leaf process / CSPEC / data store from Stages 1–4 gets *allocated* to an architecture module. The validator's allocation-completeness rule (2000 §4.2.5.4) catches every leak.
7. **`hp-validate` and `hp-status` keep you honest** — reference integrity, hierarchy consistency, PSPEC balancing, architecture allocation, stage progress, artifact freshness.

---

## Next steps

- **Try it on your own project**: `uv run python scripts/hp_init.py <name>`. Scaffolds the directory + empty dictionary + Stage 1 proposal stub. Follow the workflow chain from [README.md > Workflow](README.md#workflow).
- **Read [`reference/HP_QUICK_REF.md`](reference/HP_QUICK_REF.md)** — 60+ HP terms with modern-software analogs.
- **Read the [skills/](skills/) directory** — one markdown file per workflow stage; each documents *when to use*, *what it does*, and *discipline rules*.
- **For deeper method context**, the source books are Hatley & Pirbhai 1988 (*Strategies for Real-Time System Specification*) and Hatley, Hruschka & Pirbhai 2000 (*Process for System Architecture and Requirements Engineering*).
