# Modernization Tactics — AI-Interaction Layer for the 21st-Century Capabilities

**Status:** ✅ design locked 2026-05-22; implementation pending.
**Branch:** `kg/meld-tech-2026`.
**Audience:** the implementation pass that extends existing skills + drafts new skills + updates PLAN.md's Methodology Tactics section, so the AI knows how to use the modernization capabilities (Commits 1–5) during interactions with the architect.
**Why this exists:** the toolkit now has *schemas and validators* for the 10 modernization items, but the AI-interaction layer (Methodology Tactics in PLAN.md + the 10 skill files) hasn't been updated. An AI running today still works like it's pre-modernization — never asks about observability, never proposes a budget, never captures an ADR mid-decision. Same shape as [`PSPEC_DESIGN.md`](PSPEC_DESIGN.md) and [`ARCH_DESIGN.md`](ARCH_DESIGN.md) but oriented to behavior, not schema.

**Sources:** the modernization design docs ([`MODERNIZATION_DESIGN.md`](MODERNIZATION_DESIGN.md), [`BOUNDED_CONTEXTS_DESIGN.md`](BOUNDED_CONTEXTS_DESIGN.md)) and lived experience from the existing form-based proposal pattern.

---

## 1. The mapping

Modernization items → tactic additions → skill changes:

| Modernization | Tactic added | Existing skill extension | New skill |
|---|---|---|---|
| #1 Observability | Observability-first design | `hp-propose-pspec`, `hp-propose-architecture` | `hp-propose-observability` |
| #2 Flow synchronicity | (folded into Design-intent → runtime chain) | `hp-propose-decomp`, `hp-propose-architecture` | — |
| #5 Bounded Contexts | Context-boundary discipline | `hp-propose-context`, `hp-propose-decomp` | `hp-propose-bounded-contexts` |
| #8 Trust/security/STRIDE | Cross-boundary STRIDE pass; Catalog-reference discipline | `hp-propose-architecture` | `hp-propose-threat-model` |
| #10 ADRs | ADR-as-you-go | (all proposal skills can trigger ADR capture) | `hp-capture-adr` |
| #21 Budgets | Design-intent → runtime chain; Budget-allocation conservation | `hp-propose-architecture` | `hp-propose-budgets-and-tpms` |
| #22 TPMs | (folded into Design-intent → runtime chain) | `hp-propose-architecture` | (folded into the same skill as #21) |
| #25 V&V | (folded into Observability-first design) | `hp-propose-pspec`, `hp-propose-architecture` | — |
| #32 SLI/SLO/SLA | Design-intent → runtime chain | (referenced from `hp-propose-observability`) | `hp-propose-slos` |
| #33 Runbooks | (folded into Observability-first design) | (companion to `hp-propose-observability`) | — |

---

## 2. New tactics for PLAN.md > Methodology Tactics

Each tactic gets added as a sub-section under either Section A (Interaction Posture), B (Artifact Discipline), or C (Knowledge Work).

### 2.1 Design-intent → runtime chain (Section B — Artifact Discipline)

**Statement.** At architecture-time, always trace each non-functional concern through the chain: **Budget → TPM → SLO → Observability → Runbook**. Don't propose an architecture-level flow or commitment that doesn't have at least one budget concern surfaced.

**Why.** The 21st-century operational reality is that design-time constraints (a latency requirement, a cost budget, a memory ceiling) must connect to runtime measurement (TPMs), external commitment (SLOs), instrumentation (metrics + alerts), and operator action (runbooks). Each link in the chain failing creates a debugging gap that operations teams pay for. NASA SE Handbook §6.7 + Google SRE Book + Workbook collectively codify this chain.

**How to apply.** When proposing or reviewing an architecture decision:
1. Ask which budgets it touches (latency / cost / memory / throughput / monthly $).
2. For each touched budget, ask if a TPM exists tracking consumption.
3. For each TPM, ask if an SLO commits a customer-visible promise.
4. For each SLO, ask what alert(s) fire when the budget burns and what the runbook says.
5. If any link is missing, *flag it* — don't silently approve.

**Validator backing.** Commits 2 + 3 already enforce sub-rules: budget allocation conservation, TPM threshold, SLO derives_from_tpm, alert runbook existence.

### 2.2 Cross-boundary STRIDE pass (Section B — Artifact Discipline)

**Statement.** Any time an architecture flow or interconnect crosses trust zones, force a STRIDE pass before locking the architecture proposal. Every interconnect that bridges different `trust_zone:` values declares mitigations for all six STRIDE categories.

**Why.** The 2000 book doesn't model threat boundaries; the modern reality of network-everything systems makes this non-negotiable. STRIDE (Microsoft 1999; Howard & Lipner 2006) is the canonical lightweight categorization. ISA/IEC 62443 makes it auditable for industrial systems.

**How to apply.** When `hp-propose-architecture` or `hp-propose-threat-model` runs, for each interconnect:
1. Compute `trust_zone(source)` and `trust_zone(target)`.
2. If they differ, the proposal must include `stride_mitigations:` with narratives for all six categories (out-of-scope is a valid narrative when justified).
3. The validator's commit-4 STRIDE rule fires automatically; the tactic ensures the question is *asked* during proposal authoring.

**Validator backing.** Commit 4's stride_coverage rule.

### 2.3 ADR-as-you-go (Section A — Interaction Posture)

**Statement.** When making a non-obvious architectural decision — one with viable alternatives and real trade-offs — capture an ADR immediately, not retroactively. The form-based proposal pattern is the *entry point*; the ADR is the durable artifact.

**Why.** Decisions decay in memory and in team turnover. Nygard's 2011 observation: teams forget *why* something was chosen, then re-debate the choice when the original constraints have changed. The Context / Decision / Consequences / Alternatives format is small enough to write as you decide but substantive enough to outlast the team.

**How to apply.** During any proposal locking, if the user accepted a non-default option *or* if the proposal raised viable alternatives even when accepting the default:
1. Offer to capture an ADR. Suggest a title.
2. Pre-fill Context from the proposal's context section.
3. Pre-fill Alternatives from the proposal's `[ ]` options that were considered but not chosen.
4. Ask the user only for Consequences (the bit that's genuinely forward-looking).
5. Save under `adrs:` with appropriate `affects:` cross-references.

### 2.4 Observability-first design (Section B — Artifact Discipline)

**Statement.** When proposing a new bubble (process, architecture module), ask "what does it emit?" alongside "what does it compute?" The observability surface is part of the spec, not bolted on. Same for V&V plans — what verifies this spec?

**Why.** Modern systems are debugged through observability; SRE practice tracks design-time → runtime via SLOs anchored to observed metrics. If observability is a post-hoc concern, the metrics drift from the design. NASA SE Handbook §5.3 (V&V) similarly: verification isn't an afterthought.

**How to apply.** `hp-propose-pspec` should solicit:
1. **Emitted metrics:** counters / gauges / histograms with names + units + descriptions.
2. **Emitted alerts:** condition + severity + runbook reference.
3. **Verification:** test/analysis/inspection/demonstration methods + scenarios.

`hp-propose-architecture` should solicit the module-level analog (metrics aggregated to module; alerts that span the module).

### 2.5 Context-boundary discipline (Section B — Artifact Discipline)

**Statement.** When entities are added in a project with declared `bounded_contexts:`, every new entity must be tagged with its context. Untagged entities in a multi-context project are an error, not a default.

**Why.** Once a project crosses the bounded-context threshold (>50 entities or >1 team), implicit "all entities in the default context" silently re-introduces the global-dictionary trap that DDD bounded contexts were invented to solve. Evans 2003 ch. 14: "Multiple models are in play on any large project. Yet when code based on distinct models is combined, software becomes buggy."

**How to apply.** In any skill that creates or modifies entities (`hp-propose-context`, `hp-propose-decomp`, `hp-confirm-naming`, etc.):
1. Check `project.bounded_contexts` at the start.
2. If empty, treat all entities as `default` (current behavior).
3. If non-empty, *require* the user to declare a `context:` for each new entity.
4. When a flow / ArchFlow crosses contexts, require either a translation entity (existing) or surface the missing-ACL as a follow-up decision.

**Validator backing.** Commit 5's BoundedContexts rule fires on missing context refs and cross-context flows without translation.

### 2.6 Catalog-reference discipline (Section C — Knowledge Work)

**Statement.** Security-related decisions reference industry catalogs (MITRE ATT&CK, CWE, OWASP ASVS, ISA-62443, NIST 800-53) by ID rather than re-deriving threats and defenses in prose. Like how AIS already references protocol standards (BLE Core Spec 5.0; RFC 6455), security claims reference catalog entries.

**Why.** Reinventing threat-model vocabulary is the most common source of "we forgot about that attack class." Anchoring to MITRE ATT&CK means the analysis can be cross-referenced against threat intel + auditor expectations. ISA-62443 specifically expects this discipline for industrial systems.

**How to apply.** In `hp-propose-threat-model`, `hp-propose-architecture`, and `hp-capture-adr`:
1. When the user describes a threat or a defense in prose, ask which catalog entry it maps to.
2. Validate IDs against the catalog's format (T-numbers, CWE-numbers, control IDs).
3. The validator (commit 4) warns on malformed IDs; the tactic ensures they're proposed in the first place.

### 2.7 Budget-allocation conservation (Section C — Knowledge Work)

**Statement.** When allocating budgets across modules, the sum of allocations + reserve must equal the system target — not less (under-allocated), not more (over-allocated). Surface this as a hard validator-anchored discipline; never propose a budget without immediately allocating it.

**Why.** Budgets that aren't allocated are a wish list. NASA SE practice (mass, power, schedule budgets) treats unallocated budget as the most dangerous kind — it implies the system can absorb work that hasn't been planned. Same applies to cloud latency, cost, memory.

**How to apply.** In `hp-propose-budgets-and-tpms`:
1. Propose the budget with a `system_target` and `system_reserve`.
2. Walk through every relevant module and ask for its allocation share.
3. The remainder, after all allocations, should equal `system_reserve`. If it doesn't, force a reconcile.

**Validator backing.** Commit 2's budget allocation hard rule.

---

## 3. Existing skill extensions

Each of the 5 form-based proposal skills already in the catalog gains new decisions. Same form-based-batch-review pattern; same Discipline section style.

### 3.1 `hp-propose-context` — Bounded Contexts question

Add Decision item *(after the existing 7)*:

> **Bounded contexts at this stage** — Multi-team or multi-language project? Declare bounded_contexts now (Stage 1 is the cheapest time) or defer (default, simpler). If declared, each terminator + sys_root gains a `context:` tag.

This invites — but doesn't require — the team to think about bounded contexts as early as Stage 1. The validator only enforces context discipline if `bounded_contexts:` is actually declared.

### 3.2 `hp-propose-decomp` — Synchronicity + Bounded Context tagging

Add Decisions:

> **Internal flow synchronicity** — For each internal flow, what's its delivery semantic? `sync_request_response | async_fire_and_forget | push_notification | streaming | batched_event | continuous`. Default: `continuous` for HP-classical projects.
>
> **Per-process bounded context** — If `bounded_contexts:` is declared, tag every internal process with its context (`ctx_X`). Translation entities at the cross-context flow points.

The CSPEC owner question already exists; the bounded-context question doesn't shift it but does add per-process tagging if contexts are in use.

### 3.3 `hp-propose-cspec` — Per-transition observability

Add Decision:

> **Per-mode observability** — Should mode transitions emit traces? Should each top-level mode emit a gauge for time-in-mode? Default: emit a `mode_transitioned_total` counter per transition.

Light extension; CSPEC stage doesn't change much but the observability surface starts here for state-rich processes.

### 3.4 `hp-propose-pspec` — Observability + V&V

Add Decisions:

> **Observability surface** — What metrics does this leaf process emit? List by name + kind (counter/gauge/histogram). What log categories at what levels? What alerts when the spec is violated?
>
> **V&V plan** — How is this PSPEC verified? Select methods: `test`, `analysis`, `inspection`, `demonstration`, `formal_proof`, `simulation`. If `test`, what's the test suite path? What's the coverage target?

These are now genuinely first-class fields on the PSPEC schema (Commit 1 + Commit 3); the proposal should solicit them.

### 3.5 `hp-propose-architecture` — Trust zones + STRIDE prep + Deployment

Add Decisions:

> **Per-module trust zone** — Each architecture module's trust_zone: `public_internet | dmz | internal_lan | privileged | kernel | air_gapped`.
>
> **Interconnect auth + encryption** — Each ArchInterconnect: `auth_required` + `encryption` posture.
>
> **STRIDE pre-pass** — For each interconnect crossing two different `trust_zone` values, surface as a follow-up `hp-propose-threat-model` invocation. The architecture proposal locks the *fields*; the threat model fills in the *narratives*.
>
> **Deployment strategy** *(future-ready field)* — Blue-green / canary / rolling / feature-flagged / continuous. Optional in this iteration; flag for follow-up if not declared.

---

## 4. New skills to draft

Each new skill is a markdown file in [`toolkit/skills/`](skills/) following the established frontmatter + sections format (When to use / What it does / Behavior / Discipline / Lived examples / Implementation status / See also).

### 4.1 `hp-capture-adr`

**When to use.** Mid-decision capture, *not* stage-end. Whenever any other skill encounters a non-obvious choice (one with real alternatives + trade-offs), invoke this as a follow-up to capture the ADR.

**What it does.** Pre-fills Context from the invoking proposal; pre-fills Alternatives from the proposal's `[ ]` options that weren't chosen; solicits Consequences from the user; saves under `adrs:` with `affects:` cross-references.

**Discipline.** ADRs are written *when* the decision is made, not retroactively. ADR titles are short and decision-y ("BLE chosen for transport"). Consequences are forward-looking ("future cloud-monitoring is independent"), not redescriptions of the decision.

### 4.2 `hp-propose-budgets-and-tpms`

**When to use.** Immediately after Stage 5 architecture is settled (modules + flows + allocations known). Also any time a new non-functional concern (latency, cost, memory) becomes architecturally visible.

**What it does.** Identifies the system-level budgets (latency, cost, memory, throughput). For each: target + reserve + allocations across modules (must sum to target − reserve). Then identifies TPMs that track each budget (current_estimate, growth_allowance, direction).

**Discipline.** Sum-equals-target-minus-reserve is a hard rule, not a guideline. Direction-aware (less_is_better vs more_is_better) avoids the BLE-uptime-validator trap. TPMs without budgets are unanchored; budgets without TPMs are wishes.

### 4.3 `hp-propose-observability`

**When to use.** Per leaf PSPEC, per architecture module. After PSPEC body is settled (so we know what the bubble does).

**What it does.** For each leaf, proposes: metrics (counters / gauges / histograms with names + units), traces (span names), log categories, alerts (condition + severity + runbook reference). For each alert, the companion `hp-author-runbook` (or just the runbook markdown stub) follows.

**Discipline.** Metric names follow Prometheus conventions (lowercase + underscores + _total / _seconds / _ratio suffixes). One alert ≈ one runbook; no orphan alerts. Pairs naturally with `hp-propose-slos` — SLIs are measured via this observability surface.

### 4.4 `hp-propose-slos`

**When to use.** After observability lands (you can't write an SLO without an SLI to measure). Defines the customer-visible promises that gate release decisions.

**What it does.** For each architecturally-meaningful concern: SLI query, target, window, error_budget_pct, applies_to modules, optional SLA prose, derives_from_tpm cross-reference, runbook_on_burn reference.

**Discipline.** SLOs are *commitments*, not aspirations. Error budgets ≥ 0 means the team accepts the trade-off and will enforce it (e.g., halt feature releases when burning). Multi-window burn-rate alerts pair with this; not in the schema yet, future extension.

### 4.5 `hp-propose-threat-model`

**When to use.** Per cross-trust-zone interconnect (the validator forces this in Commit 4). Also per ArchModule with a non-trivial attack surface.

**What it does.** Six-category STRIDE pass on each interconnect: narrative mitigations for spoofing / tampering / repudiation / info disclosure / DoS / elev_of_privilege. Optional LINDDUN privacy pass when PII is involved. Catalog references (MITRE ATT&CK / CWE / compliance frameworks).

**Discipline.** Out-of-scope is a valid narrative; *blank* is not. Catalog references by ID, not by prose name. STRIDE categories are independent — a mitigation that addresses tampering doesn't automatically cover info-disclosure.

### 4.6 `hp-propose-bounded-contexts`

**When to use.** When team boundaries or vocabulary divergence become visible — typically Stage 2 if >5 internal processes, definitively Stage 5 if multi-team. Can also be invoked retroactively to surface contexts in an existing project.

**What it does.** Identifies the system's bounded contexts (2–5 typically). For each: name, owner team, ubiquitous-language narrative. Then per existing entity, asks for context tag. Then identifies cross-context references and proposes ACL translation entities (with Evans pattern: shared_kernel / customer_supplier / conformist / anti_corruption_layer / open_host_service / published_language / separate_ways).

**Discipline.** Bounded contexts are *team-owned*, not just architecture-owned. CODEOWNERS-style ownership at the context level. ACL pattern is explicit (Evans 2003); don't write a translation without naming its pattern.

---

## 5. Implementation order

### Commit A — Design + tactics
- This document (`MODERNIZATION_TACTICS.md`)
- PLAN.md updates: add the 7 new tactics to the Methodology Tactics section
- Skills catalog README update: mark the 6 new skills as planned/drafted

### Commit B — Extend the 5 existing proposal skills
- `hp-propose-context.md`: bounded-contexts question
- `hp-propose-decomp.md`: synchronicity + per-process context tagging
- `hp-propose-cspec.md`: per-mode observability
- `hp-propose-pspec.md`: observability surface + V&V plan
- `hp-propose-architecture.md`: trust zones + auth/encryption + STRIDE pre-pass + deployment strategy
- Each extension is purely the *Behavior* + *Discipline* sections; the skill's overall shape is unchanged

### Commit C — Draft the 6 new skills
- `hp-capture-adr.md`
- `hp-propose-budgets-and-tpms.md`
- `hp-propose-observability.md`
- `hp-propose-slos.md`
- `hp-propose-threat-model.md`
- `hp-propose-bounded-contexts.md`
- Skills catalog README: 16 skills total, 5 with backing code, 11 conversational (the 5 original proposal skills + 6 new modernization skills)

Each commit is roughly one focused chunk; smaller than the modernization commits because no schema/validator/renderer work is involved — just markdown.

---

## 6. Open questions for implementation

1. **Coverage metric for tactic adherence?** Per-skill it's hard to measure, but a coverage roll-up could be: project has bounded_contexts declared → context_tagging_coverage_pct (already exists); project has cross-trust-zone interconnects → stride_coverage_pct (already exists); etc. The tactics themselves don't need a new metric; they're *behavior*, not artifact.
2. **Should `hp-capture-adr` auto-trigger from other skills?** I.e., should locking any proposal end with "any decisions worth ADR-capturing?" — Yes, by convention. Each existing skill's Behavior section gains an "Optional follow-up: hp-capture-adr if any decisions had viable alternatives."
3. **Skill granularity for `hp-propose-observability` vs folding into PSPEC + ArchModule proposals.** I propose a *separate* skill because the observability surface evolves separately from the spec (you can add metrics later without changing the PSPEC body). But it could be folded — depends on whether observability gets revisited frequently. Lean toward separate.
4. **`hp-author-runbook` as its own skill?** Not in the top 6 because runbooks are markdown documents not dictionary artifacts. They're authored conventionally; the only toolkit involvement is the validator checking that the path exists. Skip for now; can add later as a "writing aid" skill if demand exists.
5. **Tactic precedence when they conflict.** E.g., if Observability-first design says "ask about emitted metrics" but the project hasn't yet locked the PSPEC body, which goes first? The skill ordering resolves this (PSPEC body first; observability after). The tactic section in PLAN.md should mention this implicitly.

---

## 7. See also

- [`MODERNIZATION_DESIGN.md`](MODERNIZATION_DESIGN.md) — Commits 1–4 (Modernization items #1, #2, #8, #10, #21, #22, #25, #32, #33)
- [`BOUNDED_CONTEXTS_DESIGN.md`](BOUNDED_CONTEXTS_DESIGN.md) — Commit 5 (Modernization item #5)
- [`PSPEC_DESIGN.md`](PSPEC_DESIGN.md), [`ARCH_DESIGN.md`](ARCH_DESIGN.md) — predecessor design docs (same shape)
- [`../proposals/MODERNIZATION.md`](../proposals/MODERNIZATION.md) — the 39-item brainstorm + 2 real-project lenses that drove the modernization
- [`../PLAN.md`](../PLAN.md) > *Methodology Tactics* — where the 7 new tactics land
- [`skills/`](skills/) — where the 5 skill extensions and 6 new skill drafts land

---

## 8. Source bibliography

- **Evans, E.** (2003). *Domain-Driven Design*. Addison-Wesley.
- **Vernon, V.** (2013). *Implementing Domain-Driven Design*. Addison-Wesley.
- **Khononov, V.** (2021). *Learning Domain-Driven Design*. O'Reilly.
- **Howard, M., Lipner, S.** (2006). *The Security Development Lifecycle*. Microsoft Press.
- **Nygard, M.** (2011). *Documenting Architecture Decisions*.
- **Beyer et al.** (2016). *Site Reliability Engineering*. O'Reilly.
- **Beyer et al.** (2018). *The Site Reliability Workbook*. O'Reilly.
- **NASA/SP-2016-6105 Rev 2** (2017). *NASA Systems Engineering Handbook*.
