# PSPEC — Serve UI

**Process:** [`proc_serve_ui`](../../dictionary.yaml) (level-1 DFD)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## INPUTS

| Flow | From | Medium |
|---|---|---|
| `flow_f1_angler_config` — F1: config, arm/disarm | `term_angler` | UI |
| `flow_state_to_ui` — system_state | `store_system_state` | — |
| `flow_alert` — event_alert | `proc_bite_detector` | — |

## OUTPUTS

| Flow | To |
|---|---|
| `flow_f2_status` — F2: status, alerts | `term_angler` |
| `flow_override` — event_override | `proc_bite_detector` |

## TRANSFORMATION (textual)

```
Render F2 STATUS ALERTS from the current SYSTEM STATE
(tension samples + bite-detection mode + reel state) and from
any EVENT ALERT received.
Display F1 CONFIG ARM DISARM controls to the angler.
On angler override actions taken in the UI (manual cast/reel,
disarm), emit EVENT OVERRIDE.
```

## COMPUTATIONAL CONSTRAINTS

- **Frequency:** UI refresh ≥ 10 Hz; alert latency < 100 ms

## COMMENTS

Presentation layer. Decisions about which alerts to surface vs
suppress live with the user; this PSPEC just renders what arrives.

*Not a formal part of the specification (1988 §13.5).*

---

*Format: 2000 Fig 4.46 — INPUTS / OUTPUTS / TRANSFORMATION. See [`../../../toolkit/PSPEC_DESIGN.md`](../../../toolkit/PSPEC_DESIGN.md).*
