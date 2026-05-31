# AMS — Controller Host (AM 1)

**Module:** [`am_controller_host`](../../dictionary.yaml)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## DESCRIPTION

Single-board computer running Linux + the HP-derived controller
service. Carries all the device-facing protocols (Sub-1G RF to
the DTU, Modbus RTU to the meter, MQTT/Modbus TCP to the
battery system), the diversion-control state machine, and the
output adapters that translate cmd_setpoint / cmd_inverter_limit
back into vendor protocols.

## CROSS-REFERENCE (allocation)

| Requirements component | Kind |
|---|---|
| `proc_acquire_telemetry` | process |
| `proc_dispatch_commands` | process |
| `proc_cloud_forward` | process |
| `proc_compute_balance` | process (state-rich; CSPEC lives here) |
| `store_system_state` | data store |

## DESIGN RATIONALE

Single-host architecture chosen over a distributed setup because
the dataset is small enough (sub-kHz aggregate) to fit on one
modest controller, and a single failure domain simplifies the
diversion-control safety story.

## DESIGN JUSTIFICATION

Pi 4 with 2 GB RAM is overprovisioned for the workload: ~50 KB/s
aggregate ingest, ~100 KB heap working set. Vendor adapters are
Python or Go processes well within budget.

## REQUIRED CONSTRAINTS

- **Reliability:** MTBF > 8000 hours indoor mounted.
- **Safety:** Diversion command path must fail-safe to 'zero export' on host failure (Victron's fallback handles outage transfer independently).
- **Physical:** Indoor mount; passive cooling; mains UPS.
- **Cost:** BoM ≤ $200 including UPS and enclosure.

## INTERFACES

Inputs:  F1 PER CHANNEL TELEMETRY (Sub-1G RF via DTU-Pro-S or
         OpenDTU); F3 NET GRID POWER (RS485 Modbus RTU);
         F4 SOC MODE AC IN (MQTT or Modbus TCP).
Outputs: F2 POWER LIMIT SETPOINTS (OpenDTU only);
         F5 MAX CHARGE GRID SETPOINT (MQTT publish);
         F8 OPTIONAL TELEMETRY FORWARD (HTTPS, off by default).
LAN:     WebSocket + HTTP to the Dashboard Web App.

## BUDGETS (allocations to this module)

| Budget | Unit | This module | System target | Reserve |
|---|---|---:|---:|---:|
| `budget_diversion_loop_latency` — Grid sense → inverter setpoint latency | ms | 800.0 | 1000.0 | 200.0 |
| `budget_monthly_cloud_cost` — Monthly cloud cost | USD | 3.0 | 5.0 | 1.0 |

## TPMs (tracking this module's budgets)

| TPM | Unit | Current | Growth allowance | Threshold |
|---|---|---:|---:|---:|
| `tpm_diversion_response_p99` — Diversion loop p99 response latency (measured) | ms | 750.0 | 250.0 | 1000.0 |
| `tpm_actual_monthly_cost` — Actual monthly cloud cost (last 30d) | USD | 2.3 | 2.7 | 5.0 |

---

*Format: 2000 §4.2.5.4 — typical AMS contents. See [`../../ARCH_DESIGN.md`](../../ARCH_DESIGN.md).*
