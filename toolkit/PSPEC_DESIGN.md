# PSPEC Design — Stage 4 Schema, Validators, and Renderer

**Status:** ✅ shipped — design locked 2026-05-22; model + validators + renderer landed (`PSpec`/`Transformation`/`ComputationalConstraints`/`VerificationPlan`/`PSpecStyle` in [`hp_toolkit/model.py`](hp_toolkit/model.py); [`hp_toolkit/render/pspec.py`](hp_toolkit/render/pspec.py)). Body sections describe the as-locked design; spot-check against current code if reviewing a specific sub-item.
**Audience:** the implementation pass that adds PSPEC support to the toolkit.
**Why this exists:** the first design pass was inferred from modern practice + [`reference/HP_QUICK_REF.md`](reference/HP_QUICK_REF.md). After reading chapter 13 of the 1988 book and §4.3.3.9 + appendix A.2.12 of the 2000 book, several recommendations changed. This document captures the book-faithful design so it doesn't have to be re-derived.

**Source of truth:** Hatley & Pirbhai (1988) chapter 13 and Hatley, Hruschka & Pirbhai (2000) §4.3.3.9 + appendix A.2.12. Every load-bearing assertion below cites its source.

---

## 1. What a PSPEC is

A PSPEC is the **leaf-level functional contract** for a process bubble that does not decompose further into a sub-DFD AND does not have a CSPEC. It specifies *what* the process does — how inputs become outputs — and leaves *how* to the Architecture Model.

> "The primary role of the process specification is to describe how its outputs are generated from its inputs; it must do nothing more and nothing less." — 1988 §13.1
>
> "PSPECs must state what happens to the inputs to create the outputs. It should leave the details of how to the architecture model." — 2000 §4.3.3.9

Every functional primitive process must have exactly one PSPEC (2000 §4.3.3.9 rules).

In the current toolkit projects, this means PSPECs are needed for:

- **fishing-rig:** 4 PSPECs (`proc_acquire_tension`, `proc_reel_controller`, `proc_serve_ui`, `proc_cloud_forward`). `proc_bite_detector` has a CSPEC instead.
- **solar:** 5 PSPECs (`proc_acquire_telemetry`, `proc_dispatch_commands`, `proc_serve_ui`, `proc_handle_user_input`, `proc_cloud_forward`). `proc_compute_balance` has its CSPEC.

---

## 2. Canonical PSPEC structure

The 2000 book Figure 4.46 defines the generic PSPEC format. Every PSPEC has three formal sections:

```
PSPEC <number>: <NAME>
INPUTS:
OUTPUTS:
TRANSFORMATION:
```

The toolkit follows this exactly, plus two optional sections from the books:

- **Computational constraints** (2000 §4.3.3.9, A.2.12) — accuracy, timing, frequency.
- **Comments** (1988 §13.5) — rationale, derivation history, not part of formal spec.

---

## 3. Dictionary schema

PSPECs live in a separate top-level section of `dictionary.yaml`, mirroring how `transitions:` is separate. Each entry is keyed by a stable id (`pspec_*` prefix by convention).

```yaml
pspecs:
  pspec_acquire_tension:
    parent_process: proc_acquire_tension      # references entities.<process>

    # INPUTS and OUTPUTS are NOT declared here — derived at validate time
    # from dictionary.flows. The validator enforces balancing (§4 below).

    transformation:
      style: textual                          # textual | equation | table | diagram | mixed
      body: |
        Every cycle:
          Read F3_TENSION from the ADC.
          Normalize F3_TENSION to TENSION_SAMPLE.
          Write TENSION_SAMPLE to store_system_state.

    computational_constraints:                # optional — 2000 §4.3.3.9, A.2.12
      frequency: "200 Hz sampling"
      accuracy: "±1% of measured value"
      timing: ""                              # e.g., "max latency 5 ms"

    comments: |                               # optional — 1988 §13.5
      Conversion factor calibrated from sensor data sheet rev 2.
      Not a formal part of the specification.
```

### Style enum

The five styles cover the books' explicit list (1988 §13.2; 2000 §4.3.3.9 Fig 4.47):

| Value | Source | When to use |
|---|---|---|
| `textual` | 1988 §13.4 (structured English) | Procedural processes; the most common form (2000 §4.3.3.9). |
| `equation` | 1988 §13.2 (Fig 13.1) | Mathematical transformations. |
| `table` | 1988 §13.2 (Fig 13.2) | Decision tables, condition→output matrices. (PAT excluded — see §5.) |
| `diagram` | 1988 §13.2 (Figs 13.3, 13.4); 2000 Fig 4.47 | Block diagrams, geometry, flight profiles. Body references a sidecar SVG. |
| `mixed` | 1988 §13.2 ("or any combination") | Multiple styles in one PSPEC. |

For `diagram` style, the body may reference a sidecar image: `body: "see [./pspec-tension-block-diagram.svg](./pspec-tension-block-diagram.svg)"`.

---

## 4. Pydantic model additions

```python
class PSpecStyle(str, Enum):
    TEXTUAL  = "textual"
    EQUATION = "equation"
    TABLE    = "table"
    DIAGRAM  = "diagram"
    MIXED    = "mixed"

class ComputationalConstraints(BaseModel):
    """2000 §4.3.3.9 — accuracy, timing, frequency."""
    frequency: str | None = None
    accuracy: str | None = None
    timing: str | None = None

class Transformation(BaseModel):
    style: PSpecStyle
    body: str                       # required; non-empty

class PSpec(BaseModel):
    id: str
    parent_process: str
    transformation: Transformation
    computational_constraints: ComputationalConstraints | None = None
    comments: str | None = None
```

The top-level `Project` model adds:

```python
pspecs: dict[str, PSpec] = Field(default_factory=dict)
```

---

## 5. Validator rules

All rules derive from the books; encoded in `hp_toolkit/validate.py`.

| # | Rule | Source | Severity |
|---|---|---|:---:|
| 1 | Every functional primitive process (process with `needs_cspec: false`, no child DFD) has exactly one PSPEC | 2000 §4.3.3.9 rules | error |
| 2 | `parent_process` references a real process entity | reference integrity | error |
| 3 | **Balancing — inputs:** every flow with `target == parent_process` (post-refinement) appears at least once in `transformation.body` | 1988 §13.1 | error |
| 4 | **Balancing — outputs:** every flow with `source == parent_process` (post-refinement) is generated by the transformation | 1988 §13.1 | error |
| 5 | **Balancing — no extras:** body MUST NOT reference a flow name absent from the process's inputs/outputs | 1988 §13.1 | error |
| 6 | Body MUST NOT contain a process activation table | 1988 §13.2 ("only form of table illegal in PSPECs") | error |
| 7 | Body MUST NOT contain code or pseudocode | 1988 §13.2 ("not, repeat not, contain code, or even pseudocode") | warning (heuristic) |
| 8 | Textual bodies capitalize flow names exactly matching dictionary entries | 1988 §13.4 | warning |
| 9 | Transient outputs use the keyword `issue` in the body | 1988 §13.3 | info |
| 10 | Transformation body is non-empty | sanity | error |

**Heuristic for rule 7:** scan the body for `:=`, `for(`, `while(`, `if (`, `function `, `def `, `return `, `++`, `--`, `==`. Surface as a warning, not an error — equations and pseudo-pseudocode (e.g., "if X > Y") have legitimate use.

**Rule 9 implementation:** for a flow flagged as transient in its dictionary entry (future field `transient: true`), confirm the body uses the word `issue` to introduce it. Until the `transient:` field exists, this rule is informational.

---

## 6. Renderer plan

Each PSPEC produces a sidecar markdown file:

```
01-level1/pspecs/<process-id-short>.md
```

Where `<process-id-short>` strips the `proc_` prefix and converts `_` → `-`, matching the existing CSPEC subdir convention (e.g., `proc_acquire_tension` → `acquire-tension`).

Format mirrors 2000 Fig 4.46:

```markdown
# PSPEC — Acquire Tension

**Process:** [`proc_acquire_tension`](../../dictionary.yaml) (level-1 DFD)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## INPUTS

| Flow | From | Medium |
|---|---|---|
| F3_TENSION | term_line | analog sensor → ADC |

## OUTPUTS

| Flow | To |
|---|---|
| flow_tension_to_state | store_system_state |

## TRANSFORMATION (textual)

```
Every cycle:
  Read F3_TENSION from the ADC.
  Normalize F3_TENSION to TENSION_SAMPLE.
  Write TENSION_SAMPLE to store_system_state.
```

## COMPUTATIONAL CONSTRAINTS

- **Frequency:** 200 Hz sampling
- **Accuracy:** ±1% of measured value

## COMMENTS

Conversion factor calibrated from sensor data sheet rev 2.
*Not a formal part of the specification.*
```

For `diagram` style, the markdown embeds the referenced SVG inline (`![Block diagram](./pspec-tension-block-diagram.svg)`).

**Cross-linking:** the level-1 Cytoscape HTML side panel gains a `► PSPEC: <link>` line for any leaf process bubble that has a PSPEC. Single-click the bubble → side panel shows the PSPEC link. Double-click to navigate. Matches the existing CSPEC navigation pattern.

---

## 7. Methodology constraints (carried into `hp-propose-pspec` Discipline)

These become Discipline rules in the [`skills/hp-propose-pspec.md`](skills/) draft. Each cites its book source.

- **PSPECs specify what, not how** (1988 §13.1; 2000 §4.3.3.9).
- **No code, no pseudocode** (1988 §13.2). Equations and tables, yes; control-flow code, no.
- **Each PSPEC short enough to be unambiguous, long enough to be nontrivial** (1988 §13.1).
- **Time is universally available**; never model time as an input flow (1988 §13.3).
- **Large data blocks → appendix referenced from the PSPEC** (1988 §13.2; 2000 §4.3.3.9).
- **Capitalize flow names** in textual bodies; they must match dictionary entries exactly (1988 §13.4).
- **Process activation tables are CSPEC-only**; never put one in a PSPEC (1988 §13.2).
- **Decision tables and state transition matrices** *may* appear in PSPECs if their function is local, not global (1988 §13.2).
- **Default output convention is time-continuous**; transient outputs use the keyword `issue` (1988 §13.3).

---

## 8. Open questions for implementation

- **`transient: true` field on Flow:** to support validator rule 9 properly, Flow needs a way to declare it's transient. Add to `model.py` alongside this work, or defer until rule 9 is needed in practice?
- **Pseudocode heuristic (rule 7):** how aggressive? The example list (`:=`, `for(`, `if (`, etc.) catches obvious cases but misses subtle ones (function-call syntax, etc.). Likely fine to start naive and tune as we hit false positives.
- **Cytoscape side-panel UX:** show full PSPEC body in side panel, or just a link? Lean *link* — PSPEC bodies can be long; better to navigate.
- **Schema migration:** existing dictionaries (solar, fishing-rig) have no `pspecs:` section. Loader needs to default it to empty `dict[str, PSpec]`. Validator's "every leaf process needs a PSPEC" rule will fire for both projects until we lock the 9 outstanding PSPECs.

---

## 9. Implementation order

1. **Model:** add `PSpec`, `PSpecStyle`, `Transformation`, `ComputationalConstraints` to `model.py`; add `pspecs:` field to `Project`. Loader picks them up automatically.
2. **Validator:** implement rules 1–10 in `validate.py`; add coverage metric for PSPEC presence per leaf process.
3. **Renderer:** add `render/pspec.py` for the markdown emitter; extend `render_project.py` to emit one file per PSPEC; extend `render/cytoscape.py` to inject the `► PSPEC` link on leaf processes that have one.
4. **Skill:** draft `skills/hp-propose-pspec.md` codifying the book-derived Discipline.
5. **Lived example:** lock the first PSPEC end-to-end on fishing-rig (`proc_acquire_tension` — smallest surface). Iterate the schema/validator/renderer against what the dogfooding surfaces.
6. **Roll out** to the remaining 8 PSPECs (3 in fishing-rig, 5 in solar) once the pattern settles.

---

## See also

- [`reference/HP_QUICK_REF.md`](reference/HP_QUICK_REF.md) — PSPEC entry (one-paragraph summary)
- [`skills/hp-propose-pspec.md`](skills/) — *(to be drafted)* — the conversational skill that codifies this design as a user-facing methodology surface
- [`../PLAN.md`](../PLAN.md) — Open Questions > "Stage 4 / PSPEC schema" — this design resolves those questions
- [`hp_toolkit/model.py`](hp_toolkit/model.py) — Pydantic schemas (where the new classes land)
- Hatley & Pirbhai 1988, chapter 13 — *Preparing Process Specifications*
- Hatley, Hruschka & Pirbhai 2000, §4.3.3.9 + appendix A.2.12 — *Process Specification* (refined)
