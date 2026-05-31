# Tutorial — Walking through an HP project

This tutorial walks you through a complete HP project from scaffold to Stage 3 lock, using the **fishing-rig** example that ships with this repo. You'll run real toolkit commands against artifacts that already exist, see how each stage produces its outputs, and understand the form-based proposal pattern by inspecting how the decisions were made.

**Estimated time:** 30 minutes reading + running.
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
  — Stage 4 — PSPECs                         stage not yet implemented in toolkit
  — Stage 5 — Architecture model             stage not yet implemented in toolkit
```

All three implemented stages are locked. We'll walk through them in order.

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
  entities__terminator               5
  entities__process                  5
  entities__state                    9
  ...

VALID — no errors
```

`hp-validate` catches dangling references, hierarchy inconsistencies (e.g., `parent_state` on a non-state entity), orphan entities, and coverage gaps. Run it after every dictionary edit.

### Try the dictionary-as-source-of-truth payoff

Open `../examples/fishing-rig/dictionary.yaml` and rename one entity's label — say change `"Bite Detector"` to `"Bite Sensor"` on `proc_bite_detector`. Save.

```bash
cd toolkit
uv run python scripts/render_project.py ../examples/fishing-rig
```

Every generated artifact (Mermaid, D2, Cytoscape HTML, SVG) — at all three stages — picks up the new label. Revert the change when you're done.

---

## What you've seen

Five ideas, all grounded in the artifacts you just walked through:

1. **`dictionary.yaml` is the only file you hand-edit.** Every diagram is derived.
2. **Each stage locks through a form-based proposal**, not a chat conversation. The proposal is the audit record: decisions, alternatives considered, defaults pre-checked, provenance attached.
3. **Three views per artifact** (Mermaid, D2, Cytoscape HTML) serve three moments: docs, declarative, interactive IDE.
4. **The Cytoscape HTML is hypertext.** Drill down on decomposable bubbles, walk up via `↑ Parent`, link to dictionary entries and HP reference cards.
5. **`hp-validate` and `hp-status` keep you honest** — reference integrity, hierarchy consistency, stage progress, artifact freshness.

---

## Next steps

- **Try it on your own project**: `uv run python scripts/hp_init.py <name>`. Scaffolds the directory + empty dictionary + Stage 1 proposal stub. Follow the workflow chain from [README.md > Workflow](README.md#workflow).
- **Read [`reference/HP_QUICK_REF.md`](reference/HP_QUICK_REF.md)** — 60+ HP terms with modern-software analogs.
- **Read the [skills/](skills/) directory** — one markdown file per workflow stage; each documents *when to use*, *what it does*, and *discipline rules*.
- **For deeper method context**, the source books are Hatley & Pirbhai 1988 (*Strategies for Real-Time System Specification*) and Hatley, Hruschka & Pirbhai 2000 (*Process for System Architecture and Requirements Engineering*).
