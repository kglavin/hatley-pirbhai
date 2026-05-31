# AMS — Angler Mobile App (AM 2)

**Module:** [`am_angler_app`](../../dictionary.yaml)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## DESCRIPTION

Cross-platform mobile app (Flutter). Pairs with the controller via
BLE; presents a single-screen dashboard with live tension, mode
indicator, recent-events list, and config controls.

## CROSS-REFERENCE (allocation)

| Requirements component | Kind |
|---|---|
| `proc_serve_ui` | process |

## DESIGN RATIONALE

Flutter chosen to ship one codebase to iOS and Android. BLE is
the only required transport for first release; WiFi/cloud is
out-of-scope for the app.

## DESIGN JUSTIFICATION

UI refresh ≥ 10 Hz is trivial at the app's compute budget. BLE
notifications drive the display directly with no polling.

## REQUIRED CONSTRAINTS

- **Reliability:** Reconnects to controller within 5 s after BLE loss.
- **Physical:** Runs on iOS ≥ 15, Android ≥ 11.

## BUDGETS (allocations to this module)

| Budget | Unit | This module | System target | Reserve |
|---|---|---:|---:|---:|
| `budget_telemetry_to_app_latency` — Telemetry → app render latency (informational; not safety-critical) | ms | 150.0 | 300.0 | 50.0 |

---

*Format: 2000 §4.2.5.4 — typical AMS contents. See [`../../ARCH_DESIGN.md`](../../ARCH_DESIGN.md).*
