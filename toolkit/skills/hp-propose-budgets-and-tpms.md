---
name: hp-propose-budgets-and-tpms
description: Post-Stage-5 — declare design-time budgets (latency / cost / memory / throughput / mass / power) allocated top-down across architecture modules, plus the TPMs (Technical Performance Measures) that track consumption against each. NASA SE Handbook §6.7 discipline applied to cloud-native systems.
---

# hp-propose-budgets-and-tpms

## When to use

After Stage 5 (Architecture Model) is settled — modules + flows + allocations are known. Also any time a new non-functional concern (latency, cost, memory, throughput) becomes architecturally visible and needs to be allocated across modules.

Specifically:

- Stage 5 is locked (`hp-status` reports ✅ on Stages 1–5) and the team is ready to declare non-functional commitments.
- A new operational concern emerged (e.g., cloud cost ballooning; latency SLO at risk).
- A new module is added that consumes from existing budgets and needs an allocation.

This is the **Propose + Surface Ambiguity** AI move applied to design-time non-functional discipline. Modernization #21 + #22.

## What it does

Drafts `architecture/budgets-tpms-proposal.md` as a form-based batch-review document. Identifies system-level budget categories, allocates each across modules, then identifies the TPMs that track current consumption against each budget. Locks both as new `budgets:` and `tpms:` entries in `dictionary.yaml`.

Standard decision set (6 sections):

| # | Decision | What it pins down |
|---|---|---|
| 1 | Budget categories | Which non-functional concerns become budgets: latency / cost / memory / CPU / throughput / mass / power / cloud-monthly-$ |
| 2 | Per-budget system target | Total system-level target + `system_reserve` (margin held at system level) |
| 3 | Per-budget allocations | For each module, what share of the budget it consumes. *Sum + reserve must equal target* (validator hard rule). |
| 4 | TPM identification | For each budget, what TPM(s) measure current consumption. (Budgets without TPMs are wishes; TPMs without budgets are unanchored.) |
| 5 | Per-TPM direction | `less_is_better` (ceiling: latency/cost/memory) vs `more_is_better` (floor: uptime/MTBF/accuracy/throughput) |
| 6 | Per-TPM measurement method | How the TPM is computed — PromQL query, formula, log query. Names referenced from `observability:` metrics if possible. |

Each decision lists alternatives with Claude's recommended default **pre-checked** and provenance noted ("derived from the deployment-strategy answer in `hp-propose-architecture`"; "industry typical for cloud-native"; "AI inference from the bubble's role"). The user toggles overrides in MPE, saves once, pings back.

On lock, the skill writes the `## ✅ Status: Locked YYYY-MM-DD` header, populates `dictionary.yaml`'s `budgets:` and `tpms:` sections, then runs [`hp-validate`](hp-validate.md) (catches over-allocated budgets + TPM headroom-exhausted errors) and [`hp-render`](hp-render.md) (AMS sidecars gain `## BUDGETS` and `## TPMs` sections per module).

## Behavior

When invoked, conversationally:

1. **Read the locked architecture.** Load `dictionary.yaml`; enumerate architecture modules + interconnects + allocations. Look for deployment-strategy hints from `hp-propose-architecture` (cloud-native → cost/latency budgets; embedded → memory/CPU/power; hybrid → both).
2. **Propose budget categories.** From the project's nature, propose 2–5 budget categories. Examples: end-to-end latency p99, monthly cloud cost, per-module memory ceiling, sustained throughput. Surface AI-inferred ones with provenance.
3. **Set system targets + reserves.** For each budget: what's the system-level target? What's the reserve held at system level (typical: 10–20% of target)?
4. **Allocate across modules.** Walk each architecture module and propose its share of each budget. Sum + reserve must equal target — if it doesn't, force a reconcile.
5. **Identify TPMs.** For each budget, propose 1–2 TPMs tracking current consumption. Identify direction (less_is_better / more_is_better) and the measurement query/formula.
6. **Cross-link to observability.** If `observability:` metrics already exist on the relevant modules (via `hp-propose-observability`), reference them. Otherwise, note as a follow-up.
7. **Write `architecture/budgets-tpms-proposal.md`** with: stage header → form-based-review instructions → proposed budgets table → allocation matrix (one row per module, one column per budget) → TPM table.
8. **Tell the user**: "Open `architecture/budgets-tpms-proposal.md` in MPE, override any defaults, save, ping me when done."
9. **On user ping**: parse decisions, write Status: Locked block, populate `dictionary.yaml`'s `budgets:` + `tpms:` sections, run [`hp-validate`](hp-validate.md), then [`hp-render`](hp-render.md) to regenerate AMS sidecars with the new sections.
10. **Suggest follow-ups.** Each TPM is a candidate SLI for `hp-propose-slos`. Each newly-identified concern with no current observability is a candidate for `hp-propose-observability`.

## Discipline

These come from NASA SE Handbook §6.7 + lived experience from Commits 2–3.

- **Sum-equals-target-minus-reserve is a hard rule** *(tactic: Budget-allocation conservation)*. Don't propose a budget without immediately allocating it. Unallocated budget is the most dangerous kind — implies the system can absorb work that hasn't been planned. NASA SE Handbook §6.7 (Technical Resource Management).
- **Direction-aware TPMs** *(modernization #22)*. Less-is-better TPMs (latency, cost, memory) treat the threshold as a ceiling: `current + growth_allowance ≤ threshold`. More-is-better TPMs (uptime, MTBF, accuracy, throughput) treat it as a floor: `current − growth_allowance ≥ threshold`. Missing this distinction silently breaks the safety check (this was found and fixed during Commit 2 implementation).
- **TPMs without budgets are unanchored; budgets without TPMs are wishes**. Always propose them together. A budget without a TPM declares intent; a TPM tracks reality. Both are needed.
- **`growth_allowance` is the safety margin in the threshold direction** — not just headroom, but explicit budget for expected growth or measurement uncertainty. Set it consciously, not as `threshold - current`.
- **Cross-link to SLOs (#32) when possible**. If a TPM tracks something the team commits to externally (latency, uptime), the corresponding SLO references the TPM via `derives_from_tpm:`. The chain is Budget → TPM → SLO.
- **Reserve at the system level, not per-module**. Per-module slack invites scope creep. System-level reserve forces explicit conversation about who claims it.
- **NASA practice: mass / power / data-rate / schedule budgets are mission-engineering staples**. Cloud-native projects need the same discipline applied to cost / latency / memory / throughput. The principle transfers; the units change.

## Lived examples

- [`examples/fishing-rig/dictionary.yaml`](../../examples/fishing-rig/dictionary.yaml) — `budget_bite_to_set_latency` (200ms target, 30ms reserve, controller allocated 170ms); `budget_telemetry_to_app_latency` (300ms / 50ms reserve / split across controller + app). TPMs: `tpm_bite_to_set_currently` (165ms measured, less-is-better) + `tpm_ble_link_uptime` (99.2% measured, more-is-better — this one exercised the `direction:` field added during Commit 2).
- [`examples/solar/dictionary.yaml`](../../examples/solar/dictionary.yaml) — `budget_diversion_loop_latency` (1000ms / 200ms reserve / controller-host allocated 800ms); `budget_monthly_cloud_cost` ($5.00 / $1.00 reserve / split across modules). TPMs: `tpm_diversion_response_p99`, `tpm_actual_monthly_cost`, `tpm_dashboard_render_p99` (informational; no associated budget).

## Implementation status

**Skill description: ✅ drafted.** Backing code: ✅ schema (`Budget`, `TPM`, `TPMDirection`) + loader + validator (sum-of-allocations hard rule; direction-aware TPM threshold rule; coverage metrics `budget_allocation_completeness_pct`, `tpm_within_threshold_pct`, `tpm_growth_safety_pct`) + renderer (AMS sidecars gain `## BUDGETS` + `## TPMs` sections) all live as of Commit 2.

## See also

- Tactic source: [`PLAN.md` > Modernization Tactics > Design-intent → runtime chain](../../PLAN.md); [`PLAN.md` > Methodology Tactics > Knowledge Work > Budget-allocation conservation](../../PLAN.md)
- Schema source: [`toolkit/MODERNIZATION_DESIGN.md` §3 — #21 Budgets + #22 TPMs](../MODERNIZATION_DESIGN.md)
- Predecessor: [`hp-propose-architecture`](hp-propose-architecture.md) — needs to be locked first; budgets allocate across modules from that proposal.
- Follow-ups: [`hp-propose-observability`](hp-propose-observability.md) — declares the metrics that TPMs measure. [`hp-propose-slos`](hp-propose-slos.md) — commits external promises tied to TPMs.
- HP / NASA source: NASA SE Handbook (NASA/SP-2016-6105 Rev 2) §6.7 Technical Resource Management; §6.7.2 Technical Performance Measures.
