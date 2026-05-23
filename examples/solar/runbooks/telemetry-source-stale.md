# Runbook — telemetry_source_stale

**Alert:** `telemetry_source_stale`
**Severity:** warning
**Module:** `am_controller_host` (proc_acquire_telemetry)
**Triggered when:** `max(telemetry_source_lag_seconds) > 30`

## SYMPTOMS

- One or more telemetry sources (inverter, meter, battery) has gone silent.
- `store_system_state` becomes stale for the affected source's portion.
- Energy Manager CSPEC may degrade to conservative behavior (no diversion, no discharge).

## DIAGNOSIS

Identify which source by checking `telemetry_source_lag_seconds{source="..."}`:

1. **Inverter side stale (DTU):** check DTU power + Sub-1G antenna; ping the DTU's web UI.
2. **Meter side stale (Modbus RTU):** check RS485 wiring + termination; ping Modbus address; check RTU baud rate config.
3. **Battery side stale (MQTT / Modbus TCP):** check Cerbo GX is online and MQTT broker reachable.

## RESOLUTION

- **DTU reachable but no telemetry:** restart DTU service (Hoymiles-specific procedure).
- **DTU offline:** power-cycle the DTU; if persistent, check antenna position.
- **Meter offline:** verify RS485 termination; check meter is powered.
- **Battery offline:** check Cerbo GX network; verify MQTT broker logs.

## ESCALATION

After 15 minutes without resolution, page `#oncall-solar-team`. If the diversion loop is degraded (cannot read all three sources), notify the owner that zero-export compliance may not be enforced — they may want to disable the inverter manually until restored.
