# PSPEC — Cloud Forward

**Process:** [`proc_cloud_forward`](../../dictionary.yaml) (level-1 DFD)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## INPUTS

| Flow | From | Medium |
|---|---|---|
| `flow_state_to_cloud` — system_state | `store_system_state` | — |

## OUTPUTS

| Flow | To |
|---|---|
| `flow_f6_catch_log` — F6: catch log | `term_cloud` |

## TRANSFORMATION (textual)

```
If cloud forwarding is enabled by configuration:
  When SYSTEM STATE indicates a completed catch or session event,
  issue F6 CATCH LOG containing the relevant fields (timestamp,
  tension peak, bite-to-set delay, reel-in duration).
Otherwise, do nothing.
```

## COMPUTATIONAL CONSTRAINTS

- **Timing:** Best-effort; not in the bite-detection critical path

## COMMENTS

Optional bubble. The "issue" keyword in the body marks F6 CATCH LOG
as time-transient (1988 §13.3) — emitted once per event, not held.

*Not a formal part of the specification (1988 §13.5).*

---

*Format: 2000 Fig 4.46 — INPUTS / OUTPUTS / TRANSFORMATION. See [`../../../toolkit/PSPEC_DESIGN.md`](../../../toolkit/PSPEC_DESIGN.md).*
