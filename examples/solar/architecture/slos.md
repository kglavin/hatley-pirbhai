# Solar Local Stack — Service Level Objectives

*Generated from `dictionary.yaml`. Do not hand-edit.*

SLOs commit external promises about the runtime behavior of the architecture model. Each declares the SLI being measured, the target value, the rolling window, and the error budget that gates release decisions (Google SRE Book 2016).

## slo_diversion_loop_latency

**Diversion-loop response latency**

- **Target:** 1.0 seconds
- **Window:** 30d
- **Error budget:** 0.5%
- **SLA (customer-facing):** Diversion-loop p99 response under 1 second over any 30-day window.

### SLI

p99 latency from grid-sense reading to inverter setpoint command.

```
histogram_quantile(0.99, rate(diversion_loop_seconds_bucket[5m]))
```

### Applies to

- **Modules:** `am_controller_host`

### Derived from TPM

[`tpm_diversion_response_p99`](../dictionary.yaml) — Diversion loop p99 response latency (measured) (current 750.0 ms)

### Runbook on budget burn

[`runbooks/slo-diversion-burn.md`](../runbooks/slo-diversion-burn.md)

---

## slo_monthly_cost

**Monthly cloud cost SLO**

- **Target:** 5.0 USD
- **Window:** 30d
- **Error budget:** 20.0%

### SLI

Sum of all cloud-cost-explorer line items tagged solar-stack.

```
sum(cloud_cost_usd_monthly_total)
```

### Applies to

- **Modules:** `am_controller_host`, `am_dashboard_app`

### Derived from TPM

[`tpm_actual_monthly_cost`](../dictionary.yaml) — Actual monthly cloud cost (last 30d) (current 2.3 USD)

---

*See [`../toolkit/MODERNIZATION_DESIGN.md`](../toolkit/MODERNIZATION_DESIGN.md) §4.3 — SLI/SLO/SLA chain.*
