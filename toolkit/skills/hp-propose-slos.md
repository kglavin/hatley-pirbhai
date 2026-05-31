---
name: hp-propose-slos
description: After observability lands — commit external SLOs tying TPMs to runtime SLIs + error budgets + runbooks-on-burn. The SLI → SLO → SLA chain anchored to the architecture model. Google SRE Book + Workbook practice.
---

# hp-propose-slos

## When to use

After [`hp-propose-observability`](hp-propose-observability.md) has declared metrics + alerts — you can't write an SLO without an SLI to measure it. Also after [`hp-propose-budgets-and-tpms`](hp-propose-budgets-and-tpms.md), since each SLO typically pairs with a TPM (`derives_from_tpm:`).

Specifically:

- A module has observability metrics that the team wants to commit to externally (latency SLO, error-rate SLO, uptime SLO).
- A TPM exists tracking the design-time concern, and the team is ready to commit to a customer-facing target.
- A new SLA is being negotiated with a customer — the SLO is the internal target that must beat the SLA.

This is the **Propose + Surface Ambiguity** AI move applied to runtime commitments. Modernization #32.

## What it does

Drafts a new entry in `dictionary.yaml`'s `service_level_objectives:` section. Each SLO carries: SLI query, target, window, error_budget_pct, applies_to modules/flows, optional SLA prose, cross-references to TPM (`derives_from_tpm:`) and runbook (`runbook_on_burn:`).

Standard decision set (7 sections):

| # | Decision | What it pins down |
|---|---|---|
| 1 | SLO identity | Short id (`slo_<short>`) + human-readable name |
| 2 | SLI | The *measurement*: PromQL-style query (or equivalent), unit, description. References metrics declared via `hp-propose-observability`. |
| 3 | Target | The threshold value — what counts as "meeting" the SLO. |
| 4 | Window | Rolling time window (`30d`, `7d`, `24h`, `1h`, …). Format: `\d+[smhdw]`. |
| 5 | Error budget percentage | Acceptable fraction of failures over the window (0.0–100.0). 99.9% SLO = 0.1% error budget. |
| 6 | Applies to | Which architecture modules / flows / interconnects this SLO measures. |
| 7 | Optional: SLA + derives_from_tpm + runbook_on_burn | Customer-facing prose (if SLA); TPM cross-reference; runbook to follow when burning the error budget. |

Each decision lists alternatives with Claude's recommended default **pre-checked** and provenance noted ("derived from TPM X"; "industry typical for cloud-native"; "matches sibling SLO in this project"). The user toggles overrides in MPE, saves once, pings back.

On lock, the skill writes the `## ✅ Status: Locked YYYY-MM-DD` header, populates `dictionary.yaml`'s `service_level_objectives:` section, then runs [`hp-validate`](hp-validate.md) (catches malformed window/error_budget; unresolved applies_to refs; missing TPMs/runbooks) and [`hp-render`](hp-render.md) (emits `architecture/slos.md` summary; AMS sidecars gain `## SLOs` table; PSPEC sidecars link in alerts).

## Behavior

When invoked, conversationally:

1. **Read the observability + TPM state.** Load `dictionary.yaml`; enumerate metrics on PSPECs + ArchModules; enumerate TPMs. The SLO will reference these.
2. **Identify SLO candidates.** Per architecturally-meaningful concern (latency, uptime, cost-per-request, error rate), propose an SLO. Prefer ones backed by an existing TPM — that link makes the SLO meaningful.
3. **Author the SLI.** For each candidate, propose a PromQL-style query referencing the declared metric. Example: `histogram_quantile(0.99, rate(bite_to_set_seconds_bucket[5m]))`.
4. **Pick target + window + error budget.** Industry-typical defaults:
   - 99% SLO (1% error budget) over 30d for non-critical
   - 99.5% (0.5%) over 30d for important user-facing
   - 99.9% (0.1%) over 30d for critical revenue-generating
   - 99.99% (0.01%) for safety-critical (verify cost of this!)
5. **Set `applies_to`.** Which architecture modules, flows, interconnects does this SLO cover? An SLO that spans the whole system is rare and usually decomposes into per-tier SLOs.
6. **Cross-link.** `derives_from_tpm:` if a TPM tracks this; `runbook_on_burn:` to the markdown file the on-call follows when the error budget is burning faster than allowed.
7. **Author optional SLA prose.** Customer-facing: "Customers can expect bite-to-set latency under 200ms for 99% of detections over any 7-day window." Internal-only SLOs skip this.
8. **Write the proposal markdown** at `architecture/slos-proposal.md` (form-based review).
9. **Tell the user**: "Open `architecture/slos-proposal.md` in MPE, override any defaults, save, ping me when done."
10. **On user ping**: parse, populate `dictionary.yaml`, run `hp-validate` + `hp-render` (emits `architecture/slos.md` summary + per-module SLO tables in AMS sidecars).

## Discipline

These come from Google SRE Book (2016) + Workbook (2018) + lived experience from Commit 3.

- **SLOs are *commitments*, not aspirations**. Error budget = 0.1% means the team accepts the trade-off: when burning faster than 0.1%, halt feature releases until back in budget. If the team isn't ready to enforce that, the SLO is fiction.
- **SLI is what you measure; SLO is what you commit; SLA is the customer promise.** Three different things. The SLA is usually weaker than the SLO (so you have internal headroom). The SLI is the precise query.
- **One SLI ≈ one SLO ≈ one runbook**. Resist bundling. A "system health SLO" that aggregates 5 SLIs hides what's actually broken when it burns.
- **Window matters.** Short windows (1h, 24h) catch acute issues fast but burn out fast under chronic problems. Long windows (30d) smooth chronic issues but slow to react to acute. Industry: pair short + long windows (Workbook ch. 5 burn-rate alerts) — note in `architecture/slos.md` if a future iteration adds them.
- **Error budget burn rate matters more than absolute consumption**. Burning the entire 30-day budget in 2 hours is a different incident than burning it linearly. The `runbook_on_burn:` should describe burn-rate-aware playbook.
- **Anchor to TPMs** *(tactic: Design-intent → runtime chain)*. The chain is Budget → TPM → SLO. If you can't tie this SLO to a TPM, ask whether the underlying concern is really architecturally settled.
- **SLOs declared but not measured are worse than no SLOs**. If the SLI query can't actually run against your monitoring stack, the SLO is decoration. The validator (Commit 3) accepts free-form SLI queries; the discipline says verify them.
- **Multi-tier SLOs are the norm at scale**. A single end-to-end SLO often decomposes into per-tier SLOs (ingest, compute, dispatch). Capture both: the per-tier internal SLO + the end-to-end customer SLA.

## Lived examples

- [`examples/fishing-rig/dictionary.yaml` > `slo_bite_to_set_latency`](../../examples/fishing-rig/dictionary.yaml) — p95 bite-to-set < 200ms over 7d, 1% error budget. Applies to `am_controller`. derives_from_tpm: `tpm_bite_to_set_currently`. runbook_on_burn: `runbooks/slo-bite-to-set-burn.md`.
- [`examples/solar/dictionary.yaml` > `slo_diversion_loop_latency`](../../examples/solar/dictionary.yaml) — p99 diversion loop < 1s over 30d, 0.5% error budget. Applies to `am_controller_host`. derives_from_tpm: `tpm_diversion_response_p99`. runbook_on_burn: `runbooks/slo-diversion-burn.md`.
- [`examples/solar/dictionary.yaml` > `slo_monthly_cost`](../../examples/solar/dictionary.yaml) — monthly cloud cost ≤ $5.00 over 30d, 20% error budget (generous — cost SLOs typically are). Applies to both modules. derives_from_tpm: `tpm_actual_monthly_cost`.
- [`examples/solar/architecture/slos.md`](../../examples/solar/architecture/slos.md) — rendered SLO summary.

## Implementation status

**Skill description: ✅ drafted.** Backing code: ✅ schema (`SLI`, `SLO`) + loader + validator (window-format check; error_budget_pct ∈ [0,100]; applies_to references resolve; `derives_from_tpm` resolves to real TPM; `runbook_on_burn` path validation; coverage metric `slo_coverage_pct`) + renderer (`architecture/slos.md` summary; AMS gains `## SLOs (apply to this module)` table) all live as of Commit 3.

## See also

- Tactic source: [`PLAN.md` > Modernization Tactics > Design-intent → runtime chain](../../PLAN.md)
- Schema source: [`toolkit/MODERNIZATION_DESIGN.md` §4.3 — #32 SLI/SLO/SLA](../MODERNIZATION_DESIGN.md)
- Predecessors: [`hp-propose-observability`](hp-propose-observability.md) declares the metrics this SLO measures; [`hp-propose-budgets-and-tpms`](hp-propose-budgets-and-tpms.md) declares the TPM this SLO derives from.
- Companion: [`hp-capture-adr`](hp-capture-adr.md) — declaring an SLO is itself architecturally significant (commits the team to enforcement); often worth an ADR.
- Source: Google SRE Book (Beyer et al. 2016); Google SRE Workbook (Beyer et al. 2018) — especially ch. 1 (SLO Engineering) and ch. 5 (Alerting on SLOs).
