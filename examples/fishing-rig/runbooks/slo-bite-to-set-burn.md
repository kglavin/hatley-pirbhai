# Runbook — bite-to-set SLO error budget burning

**SLO:** `slo_bite_to_set_latency`
**Trigger:** error budget burn rate above 2× normal over the trailing 1 hour.

## SYMPTOMS

- p95 bite-to-set latency rising above 200 ms target.
- Customers may report missed hook-sets ("the rig saw the bite but didn't pull").

## DIAGNOSIS

1. **Check tension-sampling rate.** If sample rate has dropped below 100 Hz, the ADC path is the bottleneck — see `tension-sensor-stuck.md`.
2. **Check motor command path.** Latency between `bite_detected` and `motor_command` issued. If high, the bite-detection state machine may be blocked on a fault check.
3. **Check reel motor stall.** If motor isn't responding promptly, mechanical stall in the spool will manifest as bite-to-set latency.
4. **Check enclosure temperature.** ESP32 thermal throttling can slow the bite-detection loop in extreme heat.

## RESOLUTION

- **ADC bottleneck:** reduce other sampling tasks if the controller is overloaded; consider firmware update to the 200 Hz ADC path.
- **State-machine block:** inspect for the `state_fault` transition firing too eagerly; tune the fault threshold.
- **Motor stall:** mechanical inspection of the reel spool + drag adjustment.
- **Thermal:** check enclosure ventilation; document customer environment for product team.

## ESCALATION

If error budget continues to burn at >2× over 4 hours, page `#oncall-controller-team` and consider pausing new field-beta units until root cause is identified.
