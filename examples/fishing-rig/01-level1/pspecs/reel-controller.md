# PSPEC — Reel Controller

**Process:** [`proc_reel_controller`](../../dictionary.yaml) (level-1 DFD)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## INPUTS

| Flow | From | Medium |
|---|---|---|
| `flow_motor_command` — motor cmd | `proc_bite_detector` | — |

## OUTPUTS

| Flow | To |
|---|---|
| `flow_f4_torque` — F4: reel torque cmd | `term_line` |

## TRANSFORMATION (textual)

```
On receipt of MOTOR CMD:
  Decode direction, target torque, and speed.
  Enforce safety limits — max current, stall threshold, and max
  continuous run time.
  Drive the reel actuator via F4 REEL TORQUE CMD with the bounded
  torque value at the requested direction.
  When stall or current limit is reached, hold torque at the
  enforced limit until MOTOR CMD changes.
```

## COMPUTATIONAL CONSTRAINTS

- **Accuracy:** Commanded torque honored to within ±5% under non-saturated load
- **Timing:** MOTOR CMD → F4 REEL TORQUE CMD latency < 10 ms

## COMMENTS

Safety limits live in this PSPEC; the bite-detection state machine
(CSPEC for Bite Detector) trusts that they are enforced here.

*Not a formal part of the specification (1988 §13.5).*

---

*Format: 2000 Fig 4.46 — INPUTS / OUTPUTS / TRANSFORMATION. See [`../../../toolkit/PSPEC_DESIGN.md`](../../../toolkit/PSPEC_DESIGN.md).*
