---
name: hp-propose-contract
description: After Stage 5 — project the completed HP model into a machine-consumable EXECUTABLE DOMAIN CONTRACT for an autonomous-control consumer (e.g. archi). Mostly a serialization of the existing model; the genuinely-new piece is the red-line split (machine-checkable predicates vs qualitative prose). Satisfies the archi integration ask R1.
---

# hp-propose-contract

## When to use

After [`hp-propose-architecture`](hp-propose-architecture.md) (Stage 5) — you cannot emit the plant /
action surface without the architecture model that names the controlled system. Strongest after
[`hp-propose-slos`](hp-propose-slos.md), [`hp-propose-budgets-and-tpms`](hp-propose-budgets-and-tpms.md),
and [`hp-propose-threat-model`](hp-propose-threat-model.md), because those supply the *objective* and the
*red lines* the contract carries.

Use it when a completed (or seed-and-grow) HP domain needs to go to an **autonomous-control consumer** —
a system that will *run a loop against the domain*: sense the plant, choose an action, be graded against
an objective, and stay inside a safety envelope. The motivating consumer is **archi** (a closed
control/synthesis loop that authors and matures skills), which must *already know* the domain rather than
rediscover it. Satisfies **R1** of [`../../proposals/ARCHI_INTEGRATION_REQUIREMENTS.md`](../../proposals/ARCHI_INTEGRATION_REQUIREMENTS.md).

This is the **Propose + Surface Ambiguity** AI move applied to a *projection*. Most of the contract is a
mechanical serialization of the existing model; the part that needs human judgment — and the reason this
is a skill, not a `--export` flag — is the **red-line split**.

## What it does

Emits one machine-consumable **executable domain contract** (`<project>.contract.yaml`) — a self-contained
projection of `dictionary.yaml` (plus `concept.md` if the project was framed greenfield) that a consumer
ingests to run a loop **with no domain logic hand-coded in the consumer**.

It is **consumer-neutral**: the contract speaks in control terms (plant / observation / action / objective
/ envelope / seed), never in any one consumer's vocabulary. archi's mapping onto these fields is a
*binding* documented in archi, not baked into the schema (mirrors the consumer-neutral stance of the
`hp-audit` ask, R2).

Standard decision set (8 sections):

| # | Decision | What it pins down | Projected from |
|---|---|---|---|
| 1 | Contract identity | id + version pinned to the `dictionary.yaml` version (a regenerable projection, not a fork) | `project` / `version` |
| 2 | Plant / transition interface | the controlled system the consumer steps each tick | `system` + `terminator` entities + architecture modules |
| 3 | Observation schema | what the loop senses each tick | inbound level-0 boundary flows (terminator → system, `kind: data`); shape from PSPEC inputs |
| 4 | Action surface | what the loop emits each tick | outbound level-0 boundary flows (system → terminator, `data`/`control`); shape from PSPEC outputs |
| 5 | Situation vocabulary | the features the consumer reasons / selects over | glossary terms + CSPEC `state` entities + key flow labels |
| 6 | Objective (proficiency + cost) | the definition of "working" — what the consumer is graded on; the **stated** and the **intended** objective | SLOs (proficiency targets) + cost SLO/Budget (cost) + PSPEC `computational_constraints` |
| 7 | **Red-line split** | the safety envelope, split **machine-checkable** (a predicate evaluable on a proposed action/state every tick) vs **qualitative** (prose for periodic audit) | TPM `threshold`+`direction` → machine-checkable; STRIDE `accepted`/prose, `concept.md` red lines, safety constraints → qualitative |
| 8 | Seed skill (or its spec) | a baseline policy the consumer runs and must beat (seed-and-grow) | a designated leaf PSPEC `transformation` |

On lock the skill writes the contract artifact, then runs [`hp-validate`](hp-validate.md) (references
resolve; each machine-checkable red line is a well-formed predicate over the observation/action vocabulary;
objective present and non-empty; seed PSPEC exists).

## Behavior

When invoked, conversationally:

1. **Read the model.** Load `dictionary.yaml` (and `concept.md` if present). Require Stage 5 (architecture
   modules) — without it there is no plant to declare. If SLOs/TPMs/threat-model are absent, **say so**:
   the objective and the machine-checkable red lines will be thin, and the contract will be honest about
   that rather than inventing them.
2. **Auto-project the mechanical fields** (2–6 above). These are deterministic serializations — *present
   them for confirmation, do not re-elicit*. Plant = system + terminators + modules; observation =
   inbound level-0 `data` flows; action = outbound level-0 `data`/`control` flows; situation vocabulary =
   glossary + CSPEC states + flow labels; objective = SLO targets + cost budget + computational
   constraints.
3. **Elicit the red-line split** (the genuinely-new step). Enumerate constraint candidates — every TPM
   `threshold`, each numeric SLO target, each cross-trust-zone interconnect, each STRIDE mitigation marked
   `accepted`/`out_of_scope`, each `load_bearing_constraint`/red line from `concept.md`. For each, classify:
   - **machine-checkable** — expressible as a predicate the consumer evaluates on a proposed action/state
     each tick (→ the consumer's hot-path guardrail). *Default* for TPM thresholds (they already carry a
     `direction` = ceiling/floor) and numeric SLO targets.
   - **qualitative** — prose the consumer cannot evaluate per-tick; goes to the periodic human audit
     (`hp-audit`, R2). *Default* for STRIDE prose, safety narrative, intent statements.
4. **Capture the intended objective, not just the stated one.** Alongside the SLO-derived *stated*
   objective, record the *intended* objective in prose. The gap between them is exactly what an
   autonomously-grown corpus games — `hp-audit` (R2) needs the intended objective to detect it.
5. **Designate the seed skill.** Point at a leaf PSPEC whose `transformation` is a runnable baseline (a
   naive policy is fine — it is the bar to beat, not the answer). If none fits, author a minimal one via
   [`hp-propose-pspec`](hp-propose-pspec.md) first.
6. **Write the proposal markdown** at `architecture/contract-proposal.md` (form-based review): the
   auto-projected fields shown read-only, the red-line split + intended-objective + seed designation as
   editable decisions with recommended defaults pre-checked.
7. **Tell the user**: "Open `architecture/contract-proposal.md`, confirm the projections, set the red-line
   split + intended objective + seed, save, ping me."
8. **On user ping**: emit `<project>.contract.yaml`, run [`hp-validate`](hp-validate.md). Note that the
   contract is **regenerable** — re-running after the model changes re-emits it; it is never hand-edited.

## Discipline

- **Consumer-neutral, always.** The contract is a *general* executable-domain export; archi is one
  consumer. Never bake a consumer's vocabulary (archi's *capability vectors* / *corpus* / *synthesis* /
  *arbitrage*) into the schema — the binding lives in the consumer. Same rule the `hp-audit` ask (R2)
  fixes for the audit; it applies here for symmetry.
- **A projection, never a fork.** The contract is regenerated from the model, not maintained beside it.
  If a field is wrong, fix `dictionary.yaml` and re-emit. A hand-edited contract that has drifted from the
  model is the failure this skill exists to prevent.
- **The machine-checkable / qualitative split is load-bearing.** It is the whole reason red lines are
  declared here: machine-checkable ones arm the consumer's per-tick guardrail (it can *enforce* them);
  qualitative ones can only be *audited* periodically by a human. Misclassifying a qualitative red line as
  machine-checkable produces a guardrail predicate the consumer can't actually evaluate — worse than
  leaving it qualitative. **Harvest TPM thresholds** — `threshold` + `direction` is already a don't-cross.
- **Only as executable as the model is precise.** The contract can only be as runnable as the model's
  flows and objective are specified. Where an observation/action flow is named but not *typed* (no shape),
  **surface the gap** in the proposal — do not invent a schema. An explicit `underspecified: <flow>` beats
  a fabricated one; it tells the consumer (and the modeller) exactly what to tighten.
- **Stated vs intended objective — capture both.** The stated objective is what the consumer optimizes;
  the intended one is what you actually want. The gap is where a grown corpus games the metric. Recording
  only the stated objective hands `hp-audit` half the information.
- **Seed, don't solve** *(seed-and-grow)*. The seed skill is a baseline for the consumer to beat, not a
  finished policy. A naive PSPEC (order-up-to, restart-only, volume-split) is the right seed; the consumer
  matures it.
- **No red lines is a finding, not a pass.** If the model declares no constraints, the contract says
  `red_lines: []` explicitly and the proposal flags it — an autonomous consumer with an empty envelope is
  a governance risk, not a clean bill of health.

## Consumer binding (reference: archi)

This is **one consumer's mapping** onto the neutral contract — shown to make the fields concrete, *not*
part of the schema. archi runs a domain through `run_use(*, executor, stages, objective, transition,
observe, target_schedule, initial_state, ticks, hot_path, …)`; the contract supplies exactly the
domain-specific arguments it would otherwise hand-code:

| neutral contract field | archi construct it feeds |
|---|---|
| plant / transition interface | `transition(state, action) -> next_state` + `initial_state` |
| observation schema | `observe(state, target) -> obs` — what each `Stage`'s skill reads per tick |
| action surface | the action the `hot_path` returns from the stages' skills, passed to `transition` |
| situation vocabulary | the weights the supervisor + `Corpus.best_by(weights)` arbitrate over (capability-vector selection) |
| objective (proficiency + cost) | `Objective.sample(...) -> Sample(proficiency∈[0,1], effort, failed)` — proficiency = "working", effort = cost |
| machine-checkable red lines | the per-tick hot-path **guardrail** that vetoes an out-of-envelope action (e.g. oncall's `guard()` / `RedLineGuard`) + the per-synthesis gate; a breach also sets `Sample.failed` |
| qualitative red lines | the periodic human audit (`hp-audit`, R2) — *outside* `run_use` |
| seed skill | the seed `Skill` placed in a `Stage`'s corpus (archi's dogfoods: naive-volume coordinator, restart-only playbook, order-up-to policy) — the baseline the synthesis loop must beat |

Concrete domains that show the shape: archi's `examples/warehouse` (plant = multi-product inventory;
action = per-product order/allocation; objective = penalty-weighted service vs holding cost; seed =
naive volume split), `examples/oncall` (action = remediation per service; guardrail = protected-service
red line; judged objective), `examples/flowshop` (online dispatch). archi binds these onto the contract
fields above with a thin adapter; it never authors the contract — HP does.

## Lived examples

- [`examples/solar/dictionary.yaml`](../../examples/solar/dictionary.yaml) → a contract for the Solar
  Local Stack:
  - **plant** = `sys_root` + `term_inverters` / `term_meter` / `term_battery_system` / `term_grid`,
    realized by `am_controller_host`;
  - **observation** = inbound telemetry flows (→ `proc_acquire_telemetry`);
  - **action surface** = the `control` flows out of `proc_dispatch_commands` to `term_inverters` /
    `term_battery_system`;
  - **objective** = `slo_diversion_loop_latency` (p99 < 1s) as proficiency + `slo_monthly_cost` (≤ $5/30d)
    as cost;
  - **machine-checkable red lines** = the 3 TPM thresholds (`tpm_diversion_response_p99` ≤ 1000 ms,
    `tpm_actual_monthly_cost` ≤ $5, `tpm_dashboard_render_p99` ≤ 2000 ms); **qualitative red lines** =
    the AMS `required_constraints.safety` ("fail-safe to zero export on host failure") + a STRIDE residual;
  - **seed skill** = the `proc_dispatch_commands` PSPEC (a baseline to beat).
- [`examples/solar/solar.contract.yaml`](../../examples/solar/solar.contract.yaml) — **emitted** by
  `python -m hp_toolkit.contract examples/solar/dictionary.yaml`. The 13 `proc_compute_balance` CSPEC
  states (Diverting / Holding / Island / Fault / …) became the situation vocabulary; the intended
  objective is flagged `UNSET` (not invented). Re-running produces byte-identical output — the
  regenerable-projection discipline, demonstrated.

## Implementation status

**Skill description: ✅ drafted. Backing code: ✅ live** — [`hp_toolkit/contract.py`](../hp_toolkit/contract.py)
projects `dictionary.yaml` → `<dir>.contract.yaml` (`python -m hp_toolkit.contract <path/to/dictionary.yaml>`).
It auto-derives the mechanical fields (2–6), the **machine-checkable** red lines (from each TPM's
`threshold` + `direction`) and the **qualitative** red lines (AMS `required_constraints.safety` + STRIDE
mitigations marked accepted/out-of-scope), auto-picks the seed PSPEC (the process emitting the action
surface), flags the *intended* objective `UNSET` rather than inventing it, lists `underspecified` flows,
and runs a structural self-check. Proven on solar (see Lived examples); re-run is byte-identical.
⏳ Remaining: the form-based human-refinement layer (confirm the intended objective; reclassify any red
line machine-checkable ↔ qualitative) and folding the self-check into [`hp-validate`](hp-validate.md) proper.

## See also

- Originating ask: [`../../proposals/ARCHI_INTEGRATION_REQUIREMENTS.md`](../../proposals/ARCHI_INTEGRATION_REQUIREMENTS.md) — **R1** (this skill) and **R2** (`hp-audit`, the periodic governance skill that audits the envelope this contract declares).
- Predecessors (the model this projects): [`hp-propose-architecture`](hp-propose-architecture.md) (plant/action), [`hp-propose-slos`](hp-propose-slos.md) (objective), [`hp-propose-budgets-and-tpms`](hp-propose-budgets-and-tpms.md) (machine-checkable red lines), [`hp-propose-threat-model`](hp-propose-threat-model.md) (qualitative red lines), [`hp-propose-pspec`](hp-propose-pspec.md) (the seed skill).
- Greenfield source: [`hp-frame`](hp-frame.md) — `concept.md`'s `outcomes` (objective), `boundary` (plant), `load_bearing_constraints` + red lines feed the contract when the project was framed rather than ingested.
- Post-checks: [`hp-validate`](hp-validate.md), [`hp-render`](hp-render.md).
- Downstream consumer (reference binding): archi `concept.md` — *HP as authoring front-end*; the consumer maps its own constructs onto this contract, it does not author the contract.
