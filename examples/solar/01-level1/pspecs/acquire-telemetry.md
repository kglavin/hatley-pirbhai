# PSPEC — Acquire Telemetry

**Process:** [`proc_acquire_telemetry`](../../dictionary.yaml) (level-1 DFD)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## INPUTS

| Flow | From | Medium |
|---|---|---|
| `flow_f1_inverter_telemetry` — F1: per-channel telemetry | `term_inverters` | Sub-1G RF → DTU-Pro-S or OpenDTU |
| `flow_f3_net_grid_power` — F3: net grid power, V/I/PF | `term_meter` | RS485 Modbus RTU |
| `flow_f4_battery_state` — F4: SoC, mode, AC-in | `term_battery_system` | MQTT / Modbus TCP |
| `flow_event_config` — event_config | `proc_handle_user_input` | — |

## OUTPUTS

| Flow | To |
|---|---|
| `flow_telemetry_to_state` — normalized state | `store_system_state` |

## TRANSFORMATION (textual)

```
Each ingest cycle:
  Read F1 PER CHANNEL TELEMETRY from the inverter side via the
  configured DTU adapter (DTU-Pro-S, OpenDTU, or AhoyDTU).
  Read F3 NET GRID POWER V I PF from the grid-tied power meter
  via Modbus RTU.
  Read F4 SOC MODE AC IN from the battery system via MQTT or
  Modbus TCP.
On receipt of EVENT CONFIG:
  Apply the new configuration values (sample rates, source
  selection, scaling).
Normalize all readings into the canonical NORMALIZED STATE shape
and write it to store_system_state.
```

## COMPUTATIONAL CONSTRAINTS

- **Frequency:** ≥ 1 Hz aggregate ingest rate; ≥ 0.5 Hz per source
- **Timing:** End-to-end ingest → store_system_state write latency < 1 s

## VERIFICATION

- **Methods:** test, analysis
- **Coverage target:** 90.0%
- **Validation scenarios:**
  - Sustained 1 Hz aggregate ingest across all three sources for 24 hours
  - DTU reconnect within 30 s of a transient network drop
  - Modbus RTU CRC failure causes only that sample to be discarded, not session drop

## COMMENTS

Sole writer into the telemetry portion of the store. Vendor adapter
details and reconnection policy live in the architecture model,
not here (PSPECs specify what, not how — 1988 §13.1).

*Not a formal part of the specification (1988 §13.5).*

---

*Format: 2000 Fig 4.46 — INPUTS / OUTPUTS / TRANSFORMATION. See [`../../../toolkit/PSPEC_DESIGN.md`](../../../toolkit/PSPEC_DESIGN.md).*
