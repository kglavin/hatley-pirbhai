# AMS — Dashboard Web App (AM 2)

**Module:** [`am_dashboard_app`](../../dictionary.yaml)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## DESCRIPTION

SPA served from the controller host. Renders live dashboards
(power flows, SoC, mode, recent history); surfaces alerts in a
banner; exposes config controls and manual override buttons.
Runs entirely in the owner's browser; talks back via WebSocket
and HTTP.

## CROSS-REFERENCE (allocation)

| Requirements component | Kind |
|---|---|
| `proc_serve_ui` | process |
| `proc_handle_user_input` | process |

## DESIGN RATIONALE

Browser-based UI chosen over a native app to avoid app-store
friction and to make the controller usable from any device on
the owner's LAN without install.

## REQUIRED CONSTRAINTS

- **Reliability:** Reconnects to controller within 5 s of WebSocket drop; surfaces 'disconnected' state to the owner.
- **Physical:** Runs in any modern browser (Chrome, Safari, Firefox).

## BUDGETS (allocations to this module)

| Budget | Unit | This module | System target | Reserve |
|---|---|---:|---:|---:|
| `budget_monthly_cloud_cost` — Monthly cloud cost | USD | 1.0 | 5.0 | 1.0 |

## TPMs (tracking this module's budgets)

| TPM | Unit | Current | Growth allowance | Threshold |
|---|---|---:|---:|---:|
| `tpm_actual_monthly_cost` — Actual monthly cloud cost (last 30d) | USD | 2.3 | 2.7 | 5.0 |

---

*Format: 2000 §4.2.5.4 — typical AMS contents. See [`../../ARCH_DESIGN.md`](../../ARCH_DESIGN.md).*
