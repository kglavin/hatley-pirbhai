# Architecture Model Design — Stage 5 Schema, Validators, and Renderer

**Status:** ✅ design locked 2026-05-22; implementation pending.
**Audience:** the implementation pass that adds Stage 5 (Architecture Model) support to the toolkit.
**Why this exists:** Stage 5 is genuinely larger than Stages 1–4 combined — six new element types (Module, AFD, AID, AMS, AIS, Architecture Dictionary) plus the bridge to the requirements model (allocation). This design doc captures the book-faithful decisions so they don't have to be re-derived during implementation. Same approach as [`PSPEC_DESIGN.md`](PSPEC_DESIGN.md).

**Source of truth:** Hatley, Hruschka & Pirbhai (2000), chapter 4, §4.2 (the Architecture Model). Every load-bearing assertion below cites its source. The 1988 book did not have the Architecture Model in this form — Stage 5 is essentially a 2000-book contribution.

**Scope choice:** "Core 6" — AFD + AID + AMS + AIS + Architecture Module + Architecture Dictionary. Deferred: AMDs (alternative to AFD; §4.2.5.2), MIDs (rare per book; §4.2.7), push/pull indicators, architecture context diagrams beyond AFCD.

---

## 1. What the Architecture Model is

> "The architecture model shows the physical reality of the system as it is, or will be, built. Everything in it conforms to reality: the components, their interfaces, their functionality, and so on. This real-world structure of the architecture model packages the requirements into building blocks, and it is the structure that is well known to those dealing with the system." — 2000 §4.2.1

The Architecture Model answers *how* the system is built, in contrast to the Requirements Model (Stages 1–4) which answered *what* the system must do. The bridge is **allocation**: every requirements-model process, CSPEC, and data store gets allocated to one or more architecture modules.

> "System architecture comprises the major physical properties, style, structure, interactions, and purpose of a system." — 2000 §4.2.1

---

## 2. The six core element types

| Element | Book ref | What it is |
|---|---|---|
| **Architecture Module** | §4.2.2.1 | Basic building block — hardware, software, or organizational. "Bubtangle" (rounded rectangle) with name + number. Can be nested. |
| **Architecture Flow** | §4.2.2.3 | Data, material, or energy flowing between modules. Push/pull indicators optional (we defer). |
| **Architecture Interconnect** | §4.2.2.7 | Physical channel (bus, network) over which flows travel. Can exist without flows (e.g., power/ground buses). |
| **AFD** (Architecture Flow Diagram) | §4.2.5.1 | Modules + flows. The workhorse architecture view. Can decompose hierarchically. |
| **AID** (Architecture Interconnect Diagram) | §4.2.6.1 | Modules + interconnects. Decomposes parallel to the AFD. |
| **AMS** (Architecture Module Specification) | §4.2.5.4 | Per-module spec: description, cross-reference to requirements, design rationale, design justification, required constraints, interfaces. |
| **AIS** (Architecture Interconnect Specification) | §4.2.6.2 | Per-channel spec: protocol, format, framing, timing. "HP's answer to interfaces lost in implementation." |
| **Architecture Dictionary** | §4.2.8 | Definitions of all architecture flows + their allocation to requirements flows. Integrated into our existing `dictionary.yaml`. |

The AFCD (Architecture Flow Context Diagram, §4.2.3) is the level-0 of the architecture model — analogous to the Context Diagram of the requirements model. Terminators are shared with the requirements model.

---

## 3. The allocation bridge

This is the relationship that ties Stages 1–4 to Stage 5.

> "An architecture module specification contains the physical definition of a module, with cross-references to the enhanced requirements model components that are allocated to it." — 2000 §4.2.5.4

Per the AMS contents (§4.2.5.4): "cross reference — a listing of the enhanced requirements model's processes, CSPECs, and stores that are allocated to the module and its sub-modules (if any), possibly as a traceability matrix."

Allocation lives **on the architecture module**, not as a separate table. One requirements component can be allocated to multiple modules (replication, redundancy).

---

## 4. Dictionary schema

Five new top-level sections in the existing `dictionary.yaml`. Stable IDs by convention: `am_*` (modules), `af_*` (flows), `ai_*` (interconnects), `ams_*` (module specs), `ais_*` (interconnect specs).

```yaml
# ─── Architecture Model (Stage 5) ───

architecture_modules:
  am_root:
    name: "AutoFishingRig Controller"
    module_number: "AM 0"             # 2000 §4.2.5.1 — optional, for display
    kind: hardware                    # hardware | software | organizational
    description: |
      The top-level architecture module — what the requirements model
      calls sys_root at the architecture level.
    # No parent → this is the root.

  am_main_controller:
    name: "Main Controller Board"
    module_number: "AM 1"
    kind: hardware
    parent: am_root                   # nested module; 2000 §4.2.2.1 ("Modules can be nested")
    # Allocation — 2000 §4.2.5.4 cross-reference
    allocated_processes:
      - proc_acquire_tension
      - proc_bite_detector
      - proc_reel_controller
    allocated_cspecs:
      - proc_bite_detector            # process whose CSPEC lives here
    allocated_stores:
      - store_system_state
    description: |
      ESP32-based main board. Carries the tension-sampling ADC, the
      motor driver, and the bite-detection state machine.

  am_angler_app:
    name: "Angler Mobile App"
    module_number: "AM 2"
    kind: software
    parent: am_root
    allocated_processes:
      - proc_serve_ui

architecture_flows:                   # 2000 §4.2.2.3, §4.2.8
  af_tension_telemetry:
    name: "tension telemetry"
    source: am_main_controller        # architecture module id
    target: am_angler_app
    kind: data                        # data | material | energy
    physical_description: "JSON over BLE; 10 Hz aggregated samples"
    allocated_flows:                  # which requirements flows this carries
      - flow_state_to_ui

architecture_interconnects:           # 2000 §4.2.6.1
  ai_ble:
    name: "BLE Link"
    endpoints: [am_main_controller, am_angler_app]
    carries: [af_tension_telemetry]   # architecture flows riding this channel
    description: "Bluetooth Low Energy 5.0; angler app pairs to controller"

architecture_module_specs:            # 2000 §4.2.5.4
  ams_main_controller:
    parent_module: am_main_controller
    description: |
      ESP32 ... etc.
    design_rationale: |               # optional
      Chose ESP32 over Cortex-M0+ for BLE + WiFi in one package ...
    design_justification: |           # optional
      MIPS budget ...
    required_constraints:             # optional
      reliability: "MTBF > 5000 hours field operation"
      safety: "Motor cutoff on stall ..."
      physical: "Fits in 80×50×20 mm enclosure"
      cost: "BOM ≤ $40"
    interfaces: |                     # optional
      Inputs:  F3_TENSION (analog), motor encoder feedback
      Outputs: F4_REEL_TORQUE_CMD (PWM), BLE telemetry frames

architecture_interconnect_specs:      # 2000 §4.2.6.2
  ais_ble:
    parent_interconnect: ai_ble
    description: |
      Bluetooth Low Energy 5.0 link ...
    protocol_standard: "BLE 5.0 per Bluetooth Core Spec 5.0; GATT custom service"
    design_rationale: |
      Chose BLE over WiFi for power budget ...
    required_constraints:
      timing: "Max round-trip latency 100 ms"
      physical: "Range ≥ 30 m line-of-sight"
```

### What's NOT in this schema (deferred)

- **AMD** (Architecture Message Diagram) — alternative to AFD; §4.2.5.2/3
- **MID** (Module Inheritance Diagram) — §4.2.7; "rarely used in practice" per book
- **Push/pull indicators** on architecture flows — §4.2.5.1 calls them optional
- **Multiple-module symbol** — §4.2.2.1 for identical copies

---

## 5. Pydantic model additions

```python
class ArchModuleKind(str, Enum):
    HARDWARE = "hardware"
    SOFTWARE = "software"
    ORGANIZATIONAL = "organizational"

class ArchFlowKind(str, Enum):
    DATA = "data"
    MATERIAL = "material"
    ENERGY = "energy"

class ArchModule(BaseModel):
    id: str
    name: str
    kind: ArchModuleKind
    module_number: Optional[str] = None       # e.g., "AM 1.2"
    parent: Optional[str] = None              # parent module id, if nested
    description: Optional[str] = None
    # Allocation (2000 §4.2.5.4 cross-reference)
    allocated_processes: list[str] = Field(default_factory=list)
    allocated_cspecs: list[str] = Field(default_factory=list)
    allocated_stores: list[str] = Field(default_factory=list)

class ArchFlow(BaseModel):
    id: str
    name: str
    source: str                                # architecture module id
    target: str
    kind: ArchFlowKind
    physical_description: Optional[str] = None
    allocated_flows: list[str] = Field(default_factory=list)   # requirements flows carried

class ArchInterconnect(BaseModel):
    id: str
    name: str
    endpoints: list[str]                       # 2+ architecture module ids
    carries: list[str] = Field(default_factory=list)   # architecture flow ids
    description: Optional[str] = None

class ArchModuleConstraints(BaseModel):
    """2000 §4.2.5.4 required-constraints categories."""
    reliability: Optional[str] = None
    maintainability: Optional[str] = None
    safety: Optional[str] = None
    physical: Optional[str] = None
    design: Optional[str] = None
    manufacturability: Optional[str] = None
    cost: Optional[str] = None
    schedule: Optional[str] = None

class ArchModuleSpec(BaseModel):
    """AMS — 2000 §4.2.5.4. Six typical sections; only description +
    parent_module required. Cross-reference lives on ArchModule
    (allocated_*); the spec captures the prose around the allocation."""
    id: str
    parent_module: str
    description: str                           # required
    design_rationale: Optional[str] = None
    design_justification: Optional[str] = None
    required_constraints: Optional[ArchModuleConstraints] = None
    interfaces: Optional[str] = None

class ArchInterconnectSpec(BaseModel):
    """AIS — 2000 §4.2.6.2. Similar to AMS; references industry standards."""
    id: str
    parent_interconnect: str
    description: str
    protocol_standard: Optional[str] = None
    design_rationale: Optional[str] = None
    design_justification: Optional[str] = None
    required_constraints: Optional[ArchModuleConstraints] = None  # same shape
```

`Project` gains five new fields, parallel to `pspecs:`:

```python
architecture_modules: dict[str, ArchModule] = Field(default_factory=dict)
architecture_flows: dict[str, ArchFlow] = Field(default_factory=dict)
architecture_interconnects: dict[str, ArchInterconnect] = Field(default_factory=dict)
architecture_module_specs: dict[str, ArchModuleSpec] = Field(default_factory=dict)
architecture_interconnect_specs: dict[str, ArchInterconnectSpec] = Field(default_factory=dict)
```

---

## 6. Validator rules

All rules derive from book sources; encoded as `architecture_validation()` in `validate.py`.

| # | Rule | Source | Severity |
|---|---|---|:---:|
| 1 | Every leaf requirements process (kind=process, not decomposed) is allocated to ≥ 1 architecture module | §4.2.5.4 cross-reference | error |
| 2 | Every CSPEC's parent process is allocated to ≥ 1 module that has it in `allocated_cspecs` | §4.2.5.4 | error |
| 3 | Every requirements data store is allocated to ≥ 1 module | §4.2.5.4 | error |
| 4 | Every requirements flow at level ≥ 1 is allocated to ≥ 1 architecture flow OR carried within one module's allocations | §4.2.8 "the architecture dictionary contains for each flow: source(s)" + AIS guidance | warning |
| 5 | `architecture_modules.parent` references a real module | reference integrity | error |
| 6 | `architecture_flows.{source,target}` reference real modules | reference integrity | error |
| 7 | `architecture_interconnects.endpoints` reference real modules; ≥ 2 endpoints | reference integrity | error |
| 8 | `architecture_interconnects.carries` references real architecture flows | reference integrity | error |
| 9 | `architecture_module_specs.parent_module` references a real module | reference integrity | error |
| 10 | `architecture_interconnect_specs.parent_interconnect` references a real interconnect | reference integrity | error |
| 11 | Every architecture module has an AMS | §4.2.5.4 "every module must have an AMS" | error |
| 12 | Every architecture interconnect has an AIS | §4.2.6.2 implicit | warning |
| 13 | `allocated_processes`/`allocated_cspecs`/`allocated_stores` reference real requirements entities of the correct kind | reference integrity + kind check | error |
| 14 | `architecture_flows.allocated_flows` references real requirements flows | reference integrity | error |
| 15 | Module numbers (when present) are unique throughout the model | §4.2.2.1 ("names and numbers of modules should be unique") | warning |

**New coverage metrics:**
- `architecture_module_coverage_pct` — leaf processes with ≥ 1 allocation / total leaf processes
- `architecture_flow_coverage_pct` — requirements flows carried by ≥ 1 architecture flow / total requirements flows at level ≥ 1
- `ams_coverage_pct` — modules with an AMS / total modules
- `ais_coverage_pct` — interconnects with an AIS / total interconnects

---

## 7. Renderer plan

### AFD + AID — graph views

Add `render_afd(project)` and `render_aid(project)` to each of:
- `hp_toolkit/render/mermaid.py`
- `hp_toolkit/render/d2.py`
- `hp_toolkit/render/cytoscape.py`

Visual conventions per 2000 §4.2.2 figures:
- Architecture Module: rounded rectangle ("bubtangle"), differentiated from DFD process (circle) — different node kind in Cytoscape styles
- Architecture Flow: arrow with label; styled per `kind` (data = solid, material = thick, energy = dashed?) — decide during implementation
- Architecture Interconnect: thick line (or labeled edge), distinct from flows
- Module number (when present) appears below the module name

Decomposition: AFD 0 (root) → child AFDs for each nested module. Same hierarchical-rendering pattern as DFDs.

### AMS + AIS — markdown sidecars

New `hp_toolkit/render/architecture.py` with two emitters:

```python
def render_ams_markdown(project, ams) -> str: ...
def render_ais_markdown(project, ais) -> str: ...
```

Output convention:
- AMS: `architecture/specs/<module-id-short>.md`
- AIS: `architecture/specs/interconnects/<interconnect-id-short>.md`

AMS format (per 2000 §4.2.5.4):

```markdown
# AMS — Main Controller Board

**Module:** [`am_main_controller`](../../dictionary.yaml) (AM 1)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## DESCRIPTION
ESP32-based main board ...

## CROSS-REFERENCE (allocation)

| Requirements component | Kind |
|---|---|
| `proc_acquire_tension` | process |
| `proc_bite_detector` | process (state-rich; CSPEC lives here) |
| `proc_reel_controller` | process |
| `store_system_state` | data store |

## DESIGN RATIONALE
...

## DESIGN JUSTIFICATION
...

## REQUIRED CONSTRAINTS

- **Reliability:** MTBF > 5000 hours field operation
- **Safety:** Motor cutoff on stall ...
- **Physical:** Fits in 80×50×20 mm enclosure
- **Cost:** BOM ≤ $40

## INTERFACES
...
```

### Cytoscape navigation

Architecture module bubbles in the AFD HTML get side-panel `► AMS:` links — same pattern as PSPEC links in the level-1 DFD. Architecture flows that allocate requirements flows can show a back-link to the requirements model.

### Output directory layout

```
01-level1/
└── ...

architecture/
├── proposal.md                    # form-based Stage 5 proposal
├── afd.generated.{mmd,d2,html}    # AFD level 0
├── afd.generated-{mermaid,d2}.svg
├── aid.generated.{mmd,d2,html}    # AID level 0
├── aid.generated-{mermaid,d2}.svg
└── specs/
    ├── <module-id-short>.md       # one AMS per module
    └── interconnects/
        └── <interconnect-id-short>.md   # one AIS per interconnect
```

---

## 8. Methodology constraints (carried into `hp-propose-architecture` Discipline)

These become Discipline rules in the eventual skill markdown. Each cites its book source.

- **Architecture is *what* the system is built from, not *how* the requirements are met** (2000 §4.2.1).
- **One requirements process can be allocated to multiple architecture modules** (replication, redundancy) — §4.2.5.4.
- **Every leaf requirements process must end up allocated** (validator rule 1).
- **No 7±2 limit on modules per diagram** (2000 §4.2.5.1) — match the real system's complexity.
- **Avoid uninterpretable diagrams** (§4.2.5.2): no two unnamed messages/flows between the same modules; no identical names.
- **Architecture flows differ from requirements flows in kind** (§4.2.2.3): data, material, OR energy — the requirements model is data-only.
- **Module names: real-world names** (§4.2.2.1) — what people on the project actually call the component, not a generic descriptor.
- **Interconnects can exist without flows** (§4.2.6.1) — power/ground buses are valid AID entries.
- **AMS and AIS reference outside sources** (§4.2.5.4) — they "should make such references rather than duplicate information." Industry standards, datasheets, etc.
- **Mapping flows → interconnects lives in the architecture dictionary, NOT in the AIS** (§4.2.6.2) — i.e., `architecture_interconnects.carries:` is canonical; AIS prose describes the *channel*, not the *contents*.

---

## 9. Open questions for implementation

- **AMD (alternative to AFD)** — deferred for the first cut, but the renderer infrastructure should leave room for it. Schema reservation: a top-level `architecture_messages:` section, undefined for now.
- **Module template regions** (§4.2.5.1: input/central/output/UI processing regions of the architecture template) — book treats them as optional layout hints. Skip in first cut; rendering can add them later.
- **Push/pull indicators** — deferred. If needed later, add `push_pull: push | pull | both` field on `ArchFlow`.
- **Multiple-module symbol** for identical-copy modules — defer.
- **AFCD/AICD context diagrams** — included in scope choice. First cut: AFD at "level 0" shows the system's external terminators (shared from requirements model) plus the system's top-level architecture modules. AICD analogous.
- **Lived example sequence** — start with fishing-rig (smaller); roll out to solar second.
- **Solar's existing dictionary already has terminators with `kind: terminator`** — these are shared between requirements and architecture (2000 §4.2.3). The architecture model references them directly; no separate "architecture terminator" needed.

---

## 10. Implementation order

1. **Model:** add the 5 new dataclasses (`ArchModule`, `ArchFlow`, `ArchInterconnect`, `ArchModuleSpec`, `ArchInterconnectSpec`) + supporting enums + 5 new fields on `Project`. Loader picks them up automatically (extend `load.py` section list).
2. **Validator:** implement rules 1–15 in `validate.py` as `architecture_validation()`; add coverage metrics.
3. **Renderer:**
   - Add `render_afd()` + `render_aid()` to `render/mermaid.py`, `render/d2.py`, `render/cytoscape.py` (same shape as `render_dfd()`).
   - Add `render/architecture.py` with `render_ams_markdown()` + `render_ais_markdown()`.
   - Extend `scripts/render_project.py` to emit the Stage 5 artifacts (AFD/AID + AMS/AIS sidecars) when the dictionary has architecture entries.
   - Extend `render/cytoscape.py` to inject the `► AMS:` side-panel link on architecture module bubbles.
4. **Status reporting:** `_check_stage_5()` in `status.py` reports locked/in_progress/not_started based on AFD presence + AMS coverage.
5. **Skill:** draft `skills/hp-propose-architecture.md` codifying the book-derived Discipline.
6. **Lived example:** lock the first AFD + AMS set end-to-end on fishing-rig. Iterate the schema/validator/renderer against what the dogfooding surfaces.
7. **Roll out** to solar.

---

## 11. See also

- [`PSPEC_DESIGN.md`](PSPEC_DESIGN.md) — the Stage 4 design doc; this doc follows the same shape and conventions.
- [`reference/HP_QUICK_REF.md`](reference/HP_QUICK_REF.md) — Architecture Model entry (Architecture Templates, AMS, AIS).
- [`skills/hp-propose-architecture.md`](skills/) — *(to be drafted)* — the conversational skill that codifies this design as a user-facing methodology surface.
- [`../PLAN.md`](../PLAN.md) — Open Questions > "Architecture Model (Stage 5)" — this design resolves those questions.
- [`hp_toolkit/model.py`](hp_toolkit/model.py) — Pydantic schemas (where the new classes land).
- Hatley, Hruschka & Pirbhai (2000), chapter 4, §4.2 — *Architecture Model* (the source).
