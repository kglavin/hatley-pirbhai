# PSPEC — Handle Input

**Process:** [`proc_handle_user_input`](../../dictionary.yaml) (level-1 DFD)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## INPUTS

| Flow | From | Medium |
|---|---|---|
| `flow_f6_user_input` — F6: config, override | `term_user` | UI |

## OUTPUTS

| Flow | To |
|---|---|
| `flow_event_override` — event_override | `proc_compute_balance` |
| `flow_event_config` — event_config | `proc_acquire_telemetry` |

## TRANSFORMATION (textual)

```
On receipt of F6 CONFIG OVERRIDE from the angler / owner:
  Classify the input:
    - structural changes (setpoints, source enable/disable,
      policy thresholds) → issue EVENT CONFIG;
    - immediate operational overrides (manual mode, enable/
      disable, force-recompute) → issue EVENT OVERRIDE.
  Apply input validation; reject malformed inputs.
```

## COMPUTATIONAL CONSTRAINTS

- **Timing:** Input → emitted event latency < 200 ms

## COMMENTS

Owner-facing input gateway. Both EVENT CONFIG and EVENT OVERRIDE
are transient (1988 §13.3) — the "issue" keyword reflects that.

*Not a formal part of the specification (1988 §13.5).*

---

*Format: 2000 Fig 4.46 — INPUTS / OUTPUTS / TRANSFORMATION. See [`../../../toolkit/PSPEC_DESIGN.md`](../../../toolkit/PSPEC_DESIGN.md).*
