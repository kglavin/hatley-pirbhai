# Runbook — tension_sensor_stuck

**Alert:** `tension_sensor_stuck`
**Severity:** warning
**Module:** `am_controller` (proc_acquire_tension)
**Triggered when:** `rate(tension_samples_total[1m]) == 0`

## SYMPTOMS

- Tension samples rate drops to zero — no new readings being acquired.
- Bite Detector CSPEC enters `state_fault` after timeout.
- App stops receiving telemetry updates.

## DIAGNOSIS

1. Check sensor connectivity (multimeter at load-cell amplifier output — expect 0–3.3V).
2. Check ADC clock + chip-select on the ESP32 via logic analyzer if available.
3. Check firmware logs for `tension.calibration` errors (would indicate cal-table corruption).
4. Verify power rail to the load-cell amplifier (5V ±5%).

## RESOLUTION

- **Sensor disconnected:** reconnect the load-cell cable; verify in-board screw terminals seated.
- **ADC SPI failure:** power-cycle the controller; if persistent, the ESP32 module needs replacement.
- **Firmware calibration corruption:** restore last known-good calibration from cloud backup or recalibrate from a known mass.
- **Power rail failure:** check enclosure DC-DC converter; replace if output is below spec.

## ESCALATION

After 15 minutes without resolution, page `#oncall-firmware` with diagnosis notes. Capture board logs and a photograph of the sensor cable before escalating.
