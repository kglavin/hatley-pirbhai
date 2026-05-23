# AutoFishingRig — Service Level Objectives

*Generated from `dictionary.yaml`. Do not hand-edit.*

SLOs commit external promises about the runtime behavior of the architecture model. Each declares the SLI being measured, the target value, the rolling window, and the error budget that gates release decisions (Google SRE Book 2016).

## slo_bite_to_set_latency

**Bite detection → hook-set latency**

- **Target:** 0.2 seconds
- **Window:** 7d
- **Error budget:** 1.0%
- **SLA (customer-facing):** Bite-to-set latency under 200 ms for 99% of detections over any 7-day window.

### SLI

p95 latency from tension spike to motor command latch.

```
histogram_quantile(0.95, rate(bite_to_set_seconds_bucket[5m]))
```

### Applies to

- **Modules:** `am_controller`

### Derived from TPM

[`tpm_bite_to_set_currently`](../dictionary.yaml) — Measured bite-to-set latency (lab bench) (current 165.0 ms)

### Runbook on budget burn

[`runbooks/slo-bite-to-set-burn.md`](../runbooks/slo-bite-to-set-burn.md)

---

*See [`../toolkit/MODERNIZATION_DESIGN.md`](../toolkit/MODERNIZATION_DESIGN.md) §4.3 — SLI/SLO/SLA chain.*
