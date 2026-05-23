# PSPEC — Acquire Tension

**Process:** [`proc_acquire_tension`](../../dictionary.yaml) (level-1 DFD)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## INPUTS

| Flow | From | Medium |
|---|---|---|
| `flow_f3_tension` — F3: tension feedback | `term_line` | analog sensor → ADC |

## OUTPUTS

| Flow | To |
|---|---|
| `flow_tension_to_state` — tension samples | `store_system_state` |

## TRANSFORMATION (textual)

```
Every sampling cycle:
  Read F3 TENSION from the analog input.
  Convert to engineering units using the sensor calibration.
  Update TENSION SAMPLES in store_system_state with the latest value
  and append it to the recent-history buffer (retain N most recent).
```

## COMPUTATIONAL CONSTRAINTS

- **Frequency:** 50–200 Hz sampling rate (configurable; default 100 Hz)
- **Accuracy:** ±1% of measured tension
- **Timing:** Sample → store_system_state write latency < 5 ms

## VERIFICATION

- **Methods:** test, analysis
- **Coverage target:** 95.0%
- **Validation scenarios:**
  - Sustained 200 Hz sampling for 10 minutes without buffer overflow
  - Calibration drift < 0.5% over 24-hour soak test
  - Recovery from transient ADC fault within one sample period

## COMMENTS

First-cut PSPEC. Recent-history buffer size N pending Stage 5 sizing —
see TSPEC notes once that artifact exists.

*Not a formal part of the specification (1988 §13.5).*

---

*Format: 2000 Fig 4.46 — INPUTS / OUTPUTS / TRANSFORMATION. See [`../../../toolkit/PSPEC_DESIGN.md`](../../../toolkit/PSPEC_DESIGN.md).*
