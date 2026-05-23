# Runbook — diversion-loop SLO error budget burning

**SLO:** `slo_diversion_loop_latency`
**Trigger:** error budget burn rate above 2× normal over the trailing 6 hours.

## SYMPTOMS

- p99 diversion-loop response latency rising above 1 s target.
- Risk of grid-export events during surplus-solar bursts (cloud-clearing, sunrise spikes).

## DIAGNOSIS

1. **Check telemetry ingest stage.** If `telemetry_ingest_seconds` p99 is climbing, the bottleneck is on the read side — see `telemetry-source-stale.md`.
2. **Check Energy Manager CSPEC cycle time.** If state-machine evaluation is slow, may be GC pause (controller is Python) or excessive logging in the diversion-control loop.
3. **Check dispatch path.** If `cmd_setpoint` → DTU write is taking long, check DTU connection quality.
4. **Check host load.** Pi 4 thermal throttling (~80°C) will slow the loop; ensure passive cooling is adequate.

## RESOLUTION

- **Ingest bottleneck:** tune source polling intervals; reduce simultaneity if necessary.
- **CSPEC cycle:** review recent code changes to `proc_compute_balance`; profile and optimize the diversion-loop tick path.
- **DTU dispatch slow:** if OpenDTU, check WiFi quality; if DTU-Pro-S, verify Sub-1G channel isn't congested.
- **Thermal:** add or improve passive cooling; document if owner's mounting location is thermal-marginal.

## ESCALATION

If error budget continues burning at >2× over 24 hours, notify the owner: there's a real risk of grid-export events under sunlight surges. Consider engaging Victron's onboard fallback (zero-export mode) as a stopgap.
