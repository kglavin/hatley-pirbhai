---
name: hp-propose-observability
description: Per leaf process (PSPEC) or architecture module — declare the runtime observability surface: metrics, traces, log categories, and alerts. Each alert references a runbook markdown file. OpenTelemetry semantic conventions + Google SRE Workbook ch. 5.
---

# hp-propose-observability

## When to use

Per leaf PSPEC or per architecture module, after the spec body (PSPEC) or AMS (architecture module) is settled — so we know *what the thing does*. The observability surface declares *what it emits at runtime*.

Specifically:

- A leaf PSPEC has been authored via `hp-propose-pspec` and has no `observability:` block yet.
- An ArchModule has an AMS declared and the team wants module-level metrics (aggregate across allocated processes).
- A new alert condition surfaces in operations that wasn't anticipated at spec time — backfill into the dictionary.

This is the **Propose + Surface Ambiguity** AI move applied to the runtime emission surface. Modernization #1 + #33.

## What it does

Drafts an observability block on the target PSPEC or ArchModule. Solicits metrics + traces + log categories + alerts. For each alert, identifies (and stubs) a runbook markdown file. Cross-links into the design-intent → runtime chain (#21 budgets → #22 TPMs → this observability → #32 SLOs).

Standard decision set (4 sections):

| # | Decision | What it pins down |
|---|---|---|
| 1 | Metrics | Names + kinds (`counter` / `gauge` / `histogram` / `summary`) + units + descriptions. Follow Prometheus conventions: lowercase + underscores, `_total` for counters, `_seconds` for durations, `_ratio` for ratios. |
| 2 | Traces | Span names + descriptions. Typically one span per major code-path through the spec body. |
| 3 | Log categories | Categories + their default level. Avoid `_debug` as the default — keep production logs informative. |
| 4 | Alerts | Per alert: name + `when:` condition (PromQL or natural-language) + severity (`info` / `warning` / `critical` / `page`) + runbook path + optional `escalation_after_min`. Every alert has a runbook (modernization #33). |

Each decision lists alternatives with Claude's recommended default **pre-checked** and provenance noted ("derived from the PSPEC body — it reads X so emit a counter on reads"; "pairs with budget X via the TPM"; "matches industry pattern for ingest-type bubbles"). The user toggles overrides in MPE, saves once, pings back.

On lock, the skill writes the `## ✅ Status: Locked YYYY-MM-DD` header, populates `dictionary.yaml`'s `observability:` block on the target entity, stubs the runbook markdown files if missing, then runs [`hp-validate`](hp-validate.md) (catches duplicate alert names + missing runbook files) and [`hp-render`](hp-render.md) (PSPEC + AMS sidecars gain `## OBSERVABILITY` sections).

## Behavior

When invoked, conversationally:

1. **Identify the target.** Either:
   - A specific PSPEC (e.g., `pspec_acquire_tension`), or
   - A specific ArchModule (e.g., `am_controller_host`), or
   - "All leaf processes that don't yet have observability" (batch mode).
2. **Read the spec body.** For PSPECs: the transformation body declares what the process *does*. Map each verb-noun pair to a candidate metric:
   - "Read F3 TENSION" → `tension_samples_total` counter + `tension_newtons` gauge
   - "Compute balance" → `balance_compute_seconds` histogram
   - "Issue F4 REEL TORQUE CMD" → `motor_commands_total` counter
3. **Propose metrics with provenance.** For each candidate, give name + kind + unit + description. Note where it came from ("derived from spec body line 3").
4. **Propose traces.** One span per major path through the spec body. For state machines (CSPECs), one span per transition.
5. **Propose log categories + levels.** Per spec, what categories of log to emit. Default level matters — too noisy in production is as bad as too quiet.
6. **Propose alerts.** Per failure mode in the spec, propose an alert:
   - Name follows the structure `<noun>_<verb>` (e.g., `tension_sensor_stuck`, `motor_stalled`, `ingest_rate_dropped`).
   - `when:` condition is PromQL-style or natural language.
   - Severity: `warning` for "human should look soon," `critical` for "action needed in minutes," `page` for "wake someone up."
   - `runbook:` path — every alert has one. If the runbook doesn't exist yet, stub it at `runbooks/<alert-name>.md` with the standard sections (Symptoms / Diagnosis / Resolution / Escalation).
7. **Write the `observability:` block** in `dictionary.yaml` on the target entity.
8. **Stub the runbook markdown files** at the declared paths, with templated sections the operator can fill in.
9. **Tell the user**: "Open `<target>-observability-proposal.md` in MPE, override any defaults, save, ping me when done."
10. **Suggest follow-ups.** Any TPM that should track one of these metrics → `hp-propose-budgets-and-tpms`. Any SLO that should commit to one of these → `hp-propose-slos`. Any alert worth a deeper runbook → fill in the stubbed runbook file.

## Discipline

- **Observability is part of the spec, not bolted on** *(tactic: Observability-first design)*. Ask "what does it emit?" alongside "what does it compute?" If the spec body manipulates a value, the emitted metric counts something — they're two views of the same behavior.
- **Prometheus naming conventions.** Lowercase + underscores. Suffixes: `_total` (counter), `_seconds` (duration), `_bytes` (size), `_ratio` (0..1 fraction). Don't include the unit in the name *and* the unit field — pick one.
- **One alert ≈ one runbook** *(modernization #33)*. Orphan alerts get muted; muted alerts hide incidents. Validator (Commit 3) warns when an alert's runbook path doesn't exist.
- **Alert severity is *operational*, not severity-of-event-described**. "Critical" means an operator must act within minutes. "Warning" means look soon. "Info" usually shouldn't be alerted — that's logging or a dashboard.
- **Default log level in production should be `info`**. Debug is for development; warn/error for issues; info should be reasonable to leave on. Spec bodies that need debug-level logging in production usually have a missing-metric problem.
- **Cardinality discipline.** Avoid metrics whose labels can take unbounded values (user IDs, request IDs, full URLs). Histograms with too many buckets blow up cardinality similarly. Mention in this proposal: which metrics have user-affecting labels.
- **Cross-link to budgets and SLOs** *(tactic: Design-intent → runtime chain)*. When proposing a metric, note which TPM (modernization #22) might track it and which SLO (modernization #32) might commit to it. If no such link makes sense, that's worth surfacing — maybe the metric isn't worth instrumenting.

## Lived examples

- [`examples/fishing-rig/dictionary.yaml` > `pspec_acquire_tension.observability`](../../examples/fishing-rig/dictionary.yaml) — 3 metrics (tension_samples_total counter; tension_newtons gauge; tension_adc_read_seconds histogram); 1 trace; 1 log category; 1 alert (`tension_sensor_stuck`) with runbook at `runbooks/tension-sensor-stuck.md`.
- [`examples/solar/dictionary.yaml` > `pspec_acquire_telemetry.observability`](../../examples/solar/dictionary.yaml) — 3 metrics; 1 alert (`telemetry_source_stale`) with runbook at `runbooks/telemetry-source-stale.md`. Demonstrates the multi-source pattern (per-source labels surfaced as a single `telemetry_source_lag_seconds` gauge).

## Implementation status

**Skill description: ✅ drafted.** Backing code: ✅ schema (`Observability`, `Metric`, `Trace`, `LogCategory`, `Alert`, `MetricKind`, `AlertSeverity`) + loader + validator (alert name uniqueness; runbook path existence checks; coverage metrics `observability_coverage_pct`, `alert_runbook_coverage_pct`) + renderer (PSPEC + AMS sidecars gain `## OBSERVABILITY` sections; alert listings link to runbook files) all live as of Commit 3.

## See also

- Tactic source: [`PLAN.md` > Modernization Tactics > Observability-first design](../../PLAN.md)
- Schema source: [`toolkit/MODERNIZATION_DESIGN.md` §4.1 — #1 Observability; §4.2 — #33 Runbooks](../MODERNIZATION_DESIGN.md)
- Predecessor: [`hp-propose-pspec`](hp-propose-pspec.md) — settles the spec body first; observability declares what it emits.
- Companion: [`hp-propose-budgets-and-tpms`](hp-propose-budgets-and-tpms.md) — the TPMs that measure these metrics over time.
- Follow-up: [`hp-propose-slos`](hp-propose-slos.md) — SLOs commit external promises tied to the metrics declared here.
- Source: OpenTelemetry semantic conventions (opentelemetry.io); Google SRE Workbook (Beyer et al. 2018) ch. 5 — Alerting on SLOs.
