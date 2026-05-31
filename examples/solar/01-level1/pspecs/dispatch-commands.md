# PSPEC — Dispatch Commands

**Process:** [`proc_dispatch_commands`](../../dictionary.yaml) (level-1 DFD)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## INPUTS

| Flow | From | Medium |
|---|---|---|
| `flow_cmd_setpoint` — cmd_setpoint | `proc_compute_balance` | — |
| `flow_cmd_inverter_limit` — cmd_inverter_limit | `proc_compute_balance` | — |

## OUTPUTS

| Flow | To |
|---|---|
| `flow_f2_power_limit` — F2: power-limit setpoints | `term_inverters` |
| `flow_f5_battery_command` — F5: max-charge, grid setpoint | `term_battery_system` |

## TRANSFORMATION (textual)

```
On receipt of CMD SETPOINT:
  Translate the desired inverter power-limit setpoint into the
  vendor-specific frame and issue F2 POWER LIMIT SETPOINTS to
  the inverter side via the configured DTU adapter.
On receipt of CMD INVERTER LIMIT:
  Translate the desired battery charge / grid-setpoint command
  and issue F5 MAX CHARGE GRID SETPOINT to the battery system
  via MQTT publish.
```

## COMPUTATIONAL CONSTRAINTS

- **Accuracy:** Translated values honor command to within vendor protocol resolution
- **Timing:** Command → actuator latency < 500 ms

## COMMENTS

Adapter logic. The "issue" keyword in the body marks F2 and F5 as
time-transient (1988 §13.3) — each command propagates once, not
held by this bubble.

*Not a formal part of the specification (1988 §13.5).*

---

*Format: 2000 Fig 4.46 — INPUTS / OUTPUTS / TRANSFORMATION. See [`../../../toolkit/PSPEC_DESIGN.md`](../../../toolkit/PSPEC_DESIGN.md).*
