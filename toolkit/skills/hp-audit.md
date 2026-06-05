---
name: hp-audit
description: Periodic governance — re-certify an EVOLVING HP-modeled system against its declared concept/envelope using operational evidence, and classify drift (scope-creep, objective-gaming, compositional, distributional, red-line-margin). Composes hp-ingest. Consumer-neutral; archi is one consumer. Satisfies the archi integration ask R2 (governance layer 3).
---

# hp-audit

(alias: `hp-recertify`)

## When to use

Periodically, when an HP-modeled system has **evolved since it was last certified** and you need to know
whether it still lives inside the concept/envelope it was specified against. Two situations, one skill:

- **A human team has added modules / changed code** and the implemented system has drifted from the
  declared architecture (`dictionary.yaml` / `concept.md`).
- **An autonomous process has grown the system** — e.g. archi's synthesis loop maturing and adding skills
  to a corpus. Each addition individually passed a per-change gate, but the *collective* may have crept.

This is **governance layer 3** in the bounded-autonomy model (see
[`../../proposals/ARCHI_INTEGRATION_REQUIREMENTS.md`](../../proposals/ARCHI_INTEGRATION_REQUIREMENTS.md) §2):
a per-change quality gate bounds *quality* drift, never *trust/safety* drift — individually-conformant
changes can still creep collectively. `hp-audit` is the periodic, human-in-the-loop check that catches
what the per-change gate structurally cannot. Satisfies **R2** of that ask.

It is **not** a per-change gate (that is the consumer's, every change) and **not** a per-tick guardrail
(also the consumer's, every tick). It is the *rare, periodic re-certification* — run on a cadence, per
release, or `on_surprise` when a cheap drift monitor trips.

## What it does

Reconstructs the **implicit current concept** from the evolved artifacts (by **composing
[`hp-ingest`](hp-ingest.md)** — deriving the concept latent in what now exists is exactly hp-ingest's
brownfield job), **diffs it against the declared envelope**, classifies the drift, and produces a
**re-certification verdict** that names concrete artifacts/regions and either re-confirms or re-draws the
envelope.

It is **consumer-neutral**: it consumes a general input contract, never a consumer's vocabulary. archi's
constructs (skills, *capability vectors*, *telemetry*, *corpus*) map onto the general inputs via a thin
adapter the consumer supplies — `hp-audit` only ever sees "an artifact's declared behavior
characterization," not "a capability vector."

**Inputs — the general contract** (from *any* consumer):

| Input | What it is |
|---|---|
| evolved artifact set + provenance | what was added/changed since the last certification, when, the triggering justification, and **each artifact's declared characterization** (what it claims to do + the conditions under which it is valid) |
| operational evidence | what the system actually did/encountered: observed inputs, decisions, outcomes, and the **distribution of situations** met in operation |
| declared envelope | the original concept: boundary, objective (**stated** *and* **intended**), and red lines — i.e. the [`hp-propose-contract`](hp-propose-contract.md) output (R1) |

**Detects** (the drift modes the per-change gate structurally cannot):

| Drift mode | What it looks like |
|---|---|
| scope-creep | artifacts operating in regions outside the intended boundary |
| objective-gaming | the system beats the *stated* objective by exploiting the gap to the *intended* one |
| compositional drift | individually-conformant artifacts combining into collective behavior nearing a red line |
| distributional drift | the observed situation distribution has moved away from what the envelope was specified against (the envelope itself may need redrawing) |
| red-line-margin proximity | growth trending toward a declared boundary |

**Produces** a re-certification **verdict**: confirm, or re-draw the envelope; flag specific
artifacts/regions to veto or re-spec; and/or re-spec the objective — fed back into the contract.

## Behavior

When invoked, conversationally:

1. **Load the declared envelope.** Read the R1 contract (boundary, objective — *stated and intended* —
   red lines). If the *intended* objective is `UNSET` (R1 leaves it flagged), **stop and elicit it** —
   objective-gaming is undetectable without the intended/stated gap.
2. **Reconstruct the implicit current concept.** Run [`hp-ingest`](hp-ingest.md) over the evolved artifact
   set to derive the concept now latent in what exists — boundary, behaviors, the situation regions the
   artifacts actually cover. *Compose hp-ingest; do not reimplement brownfield reading.*
3. **Diff implicit vs declared.** Per drift mode: which artifacts operate outside the declared boundary
   (scope-creep)? does aggregate behavior approach a red line no single artifact crosses (compositional)?
   has the operational situation distribution moved off the envelope's basis (distributional)? is any
   red-line margin trending to zero (proximity)? does optimizing the stated objective diverge from the
   intended one (objective-gaming)?
4. **Ground every finding in operational evidence.** A finding is a *claim about what the system did* —
   cite the decisions/outcomes/situation-distribution that show it. A drift hypothesis with no operational
   evidence behind it is a question for the next audit, not a verdict.
5. **Classify and rank.** Each finding: drift mode + the concrete artifacts/regions + severity (margin to
   the red line / size of the objective gap) + evidence.
6. **Produce the verdict.** For each finding, recommend one of: *confirm* (in-envelope), *re-draw the
   envelope* (the world moved; update boundary/objective/red lines), *veto/quarantine* the artifact(s),
   *re-spec* the artifact, or *re-spec the objective* (close the stated/intended gap the system gamed).
7. **Feed back.** The verdict updates the contract/`concept.md` (a re-drawn envelope re-emits via
   [`hp-propose-contract`](hp-propose-contract.md)); vetoes/re-specs go to the consumer to enact.

## Discipline

- **Consumer-neutral — never bake one consumer's vocabulary in.** The audit consumes the general contract
  (evolved artifacts + provenance, operational evidence, declared envelope). archi's *capability vector* is
  "a declared behavior characterization"; its *telemetry* is "operational evidence"; its *corpus* is "the
  evolved artifact set." The binding lives in the consumer's adapter, not in this skill — same rule R1
  follows. A human-evolved codebase is as valid a consumer as an autonomous corpus.
- **Compose `hp-ingest`, do not reimplement it.** Reconstructing the implicit current concept *is* the
  brownfield-ingest job. If you find yourself re-deriving boundary/behaviors from artifacts here, stop and
  call hp-ingest.
- **The stated/intended objective gap is the whole game.** Objective-gaming is invisible if you only have
  the stated objective — the system *is* beating it; that is the point. The audit needs the *intended*
  objective (R1 captures it; this skill refuses to run useful objective-gaming detection without it).
- **The trigger is the consumer's responsibility, not the skill's.** A fast machine consumer (archi) runs
  a cheap deterministic *drift monitor* and escalates `on_surprise`; a human-evolved system runs per
  release or on a cadence. The *audit* is the same skill regardless. Do not build the trigger into the
  audit — it consumes whatever the consumer's monitor escalates with.
- **A verdict names names.** "There is drift" is not a verdict. "Skill X operates in region R outside the
  declared boundary; evidence: it fired on N situations with feature f beyond the envelope; recommend
  veto" is. Concrete artifacts/regions, evidence, and a recommended action — every finding.
- **Re-drawing the envelope is a first-class outcome, not a failure.** Distributional drift often means
  the *world* moved, not that the system misbehaved. "Re-draw the envelope" is a legitimate, common
  verdict — the audit keeps the declared concept honest, it does not assume the original was sacred.
- **No findings is a real result — but only with evidence behind it.** A clean re-certification must rest
  on operational evidence that the covered situation distribution stayed in-envelope, not on absence of
  looking.

## Consumer binding (reference: archi)

One consumer's mapping onto the general inputs (shown to make them concrete; **not** part of the skill):

| general input | archi instantiation |
|---|---|
| evolved artifact set + provenance | the synthesized/matured **skills** + the synthesis log (`EpisodeReport.synthesized` — `(tick, ref)` of each registration: when, for which escalation) |
| each artifact's declared characterization | the skill's **capability vector** (`Skill.capability` — its Pareto behavior profile across situation-space) + proficiency standard |
| operational evidence | run/use **telemetry** (the Executor port's `read_telemetry(session) -> list[dict]`) + objective scores + the estimated situation vectors the supervisor saw |
| declared envelope | the **R1 domain contract** (`<dir>.contract.yaml`) — `objective.stated` + `objective.intended` + `red_lines` |

**Trigger (archi's, not the skill's):** a cheap deterministic drift monitor — corpus-growth rate,
situation-distribution shift, red-line-margin proximity, objective-vs-proxy divergence — escalates
`on_surprise`, mirroring run/use's own escalation, so governance stays cheap enough to actually happen.
archi owns the monitor + acting on the verdict (veto / re-spec / re-emit the contract); `hp-audit` owns
the audit + the verdict schema.

## Lived examples

None yet — full proof needs a consumer actually running a grown corpus to produce operational evidence
(archi is not yet there; this is why R2 follows R1, which declares the envelope R2 audits). Illustrative,
grounded in the real [`examples/solar/solar.contract.yaml`](../../examples/solar/solar.contract.yaml)
envelope:

- *Scope-creep + red-line-margin*: a grown corpus adds a skill that forwards richer telemetry to
  `term_smiles_cloud` to improve a dashboard SLI; individually it passes the per-change gate, but the
  aggregate cloud egress trends `tpm_actual_monthly_cost` toward its `≤ $5` red line. `hp-audit` flags
  **red-line-margin proximity** (machine-checkable line) + **scope-creep** (operating in a region the
  intended objective — local-first control — did not sanction), evidence = the cost-trend telemetry;
  verdict: *re-spec or veto the forwarding skill*.
- *Objective-gaming*: a skill hits the diversion-latency SLO by skipping the fail-safe-to-zero-export
  check under load — beating the *stated* objective (latency) while violating the *intended* one (safe
  diversion). Detectable only against the captured intended objective; verdict: *re-spec the objective*
  to make the fail-safe explicit in the stated form.

## Implementation status

**Skill description: ✅ drafted.** Composes [`hp-ingest`](hp-ingest.md) (✅ drafted + code live) for the
implicit-concept reconstruction. Its **novel core — drift detection against a declared envelope + the
verdict schema — is not yet coded**; that, and a worked proof, are deferred until a consumer is running a
grown corpus emitting operational evidence (the R1-before-R2, envelope-before-audit ordering). The
declared-envelope input already exists as the R1 contract; the consumer-side adapter (archi) and the
drift monitor are the consumer's, not this skill's.

## See also

- Originating ask: [`../../proposals/ARCHI_INTEGRATION_REQUIREMENTS.md`](../../proposals/ARCHI_INTEGRATION_REQUIREMENTS.md) — **R2** (this skill), and §2 (the three governance layers).
- Declares the envelope this audits: [`hp-propose-contract`](hp-propose-contract.md) (R1) — its `objective.stated` / `objective.intended` / `red_lines` are the declared envelope; re-drawing the envelope re-emits via it.
- Composed: [`hp-ingest`](hp-ingest.md) — reconstructs the implicit current concept from the evolved artifacts.
- Related governance: [`hp-propose-threat-model`](hp-propose-threat-model.md) (the qualitative red lines audited here may extend it), [`hp-validate`](hp-validate.md) (per-model integrity, not drift).
- Downstream consumer (reference binding): archi `concept.md` — *PERIODIC GOVERNANCE* / *GOVERNANCE TRIGGER* open questions; archi owns the drift monitor + acting on the verdict.
