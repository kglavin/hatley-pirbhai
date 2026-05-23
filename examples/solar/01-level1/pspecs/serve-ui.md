# PSPEC — Serve UI

**Process:** [`proc_serve_ui`](../../dictionary.yaml) (level-1 DFD)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## INPUTS

| Flow | From | Medium |
|---|---|---|
| `flow_state_to_ui` — system_state | `store_system_state` | — |
| `flow_event_alert` — event_alert | `proc_compute_balance` | — |

## OUTPUTS

| Flow | To |
|---|---|
| `flow_f7_user_view` — F7: dashboards, alerts | `term_user` |

## TRANSFORMATION (textual)

```
Render F7 DASHBOARDS ALERTS combining:
  the current SYSTEM STATE (power flows, SoC, mode, recent
  history),
  and any EVENT ALERT received from the Energy Manager.
Provide drill-in views for inverter-side, grid-side, and
battery-side detail.
```

## COMPUTATIONAL CONSTRAINTS

- **Frequency:** Dashboard refresh ≥ 1 Hz; alert latency < 500 ms

## COMMENTS

Read-only presentation. No commands originate here; user actions
go through proc_handle_user_input.

*Not a formal part of the specification (1988 §13.5).*

---

*Format: 2000 Fig 4.46 — INPUTS / OUTPUTS / TRANSFORMATION. See [`../../../toolkit/PSPEC_DESIGN.md`](../../../toolkit/PSPEC_DESIGN.md).*
