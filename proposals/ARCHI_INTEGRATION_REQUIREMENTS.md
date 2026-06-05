# archi ↔ HP Toolkit — Integration Requirements (inbound ask from the archi project)

**Status:** Requirements ask. No HP implementation yet — this enumerates *what* archi needs the HP
toolkit to provide and *why*. The *how* (formats, schemas, skill mechanics) belongs to the HP team.

**Audience:** the HP toolkit team (implementers). Not a spec archi will build against internally —
archi is the consumer; these are requirements *on* HP.

**Origin:** archi's concept framing (`~/archi/concept.md`), 2026-06-02 `hp-frame` session. archi
is a separate project that depends on the HP toolkit as its **authoring front-end** and as the home
of one **governance skill**. archi will NOT recode HP here; it files this ask so a different team can
implement it separately.

**Traceability:** maps to archi `concept.md` → the *bounded-autonomy* tension, the *red-line*
load-bearing constraint, and the open_questions on PERIODIC GOVERNANCE / GOVERNANCE TRIGGER /
HP AS AUTHORING FRONT-END.

---

## 1. Why archi needs HP

archi is a closed control loop: a fast deterministic hot path runs compiled "skills," a slow LLM
supervisory loop selects/escalates, and a synthesis loop authors → verifies → registers new skills
when the corpus can't cover a situation. Two needs fall naturally to HP, not to archi:

1. **A domain has to get *into* archi.** The synthesis loop authors against a domain it must already
   *know* — it does not rediscover the domain. Today (in archi's dogfoods) a human hand-wrote the
   plant, the objective, and the seed skills inline. In the real workflow, **HP is the human-driven
   front-end that captures a domain and emits a machine-consumable *domain contract*** archi ingests.
   This is mostly a *serialization* of artifacts HP already produces (`concept.md`, `dictionary.yaml`,
   p-specs / c-specs), not new analysis.

2. **Seed-and-grow needs a safety envelope.** archi's chosen base-skill model is *seed-and-grow*: the
   human authors the contract + objective + a minimal (possibly naive) seed skill, and archi matures
   and expands the corpus autonomously. archi's per-skill curation gate bounds **quality** drift
   ("beat the incumbent on the objective"); it does **not** bound **trust/safety** drift. An
   autonomously-grown corpus can "grow tendrils" — scope-creep, objective-gaming, compositional
   drift — while every skill individually passes the gate. The countermeasure is *bounded autonomy*
   across three governance layers; the third is **periodic, human, and is an HP skill**.

## 2. The three governance layers (so R2 lands in context)

| Layer | Frequency | Owner | Mechanism |
|---|---|---|---|
| 1 — hot-path guardrail | every tick | **archi** | deterministic safety supervisor vetoes any out-of-envelope action regardless of which skill proposed it |
| 2 — per-synthesis gate | per authored skill | **archi** | the curation gate rejects a candidate that violates the envelope on the verification battery |
| 3 — periodic governance audit | on drift (rare) | **HP** (this ask) | re-certify the *evolved system* + operational evidence against the declared red lines (a general HP skill; archi is one consumer) |

Layers 1–2 are archi's to build. **Layer 3 is the new HP skill (R2).** Red lines must be *declared*
in the contract (R1), split into machine-checkable (→ layer 1) and qualitative (→ layer 3).

---

## R1 — HP emits archi's DOMAIN CONTRACT (the authoring front-end)

> **Status (2026-06-04): picked up in HP as [`hp-propose-contract`](../toolkit/skills/hp-propose-contract.md)
> (drafted).** Built consumer-NEUTRAL (an "executable domain contract"; archi is a documented binding, not
> baked into the schema — mirroring R2's stance). Backing projector/validator is planned next, alongside
> the first real contract (solar). R2 (`hp-audit`) intentionally deferred until a consumer is actually
> running a grown corpus to audit — R1 declares the envelope R2 will audit against, so R1 comes first.

**What:** completing an HP analysis for a domain produces a machine-consumable **domain contract**
archi can ingest and run a loop against, without the human re-stating the domain in code.

**Required fields** (archi needs these; the *names/format* are HP's to choose). Plausible source —
HP team owns the real mapping:

| Contract field | What archi needs it for | Plausible HP source |
|---|---|---|
| plant / transition interface | the environment archi steps each tick | architecture model / boundary (the controlled system) |
| observation schema | what the loop senses each tick | Stage-1 context dataflow inputs |
| situation vocabulary | features the supervisor + arbitrage reason over | the control/dataflow model + `dictionary.yaml` |
| action surface | the action/order schema the skill emits | boundary (controlled outputs) |
| **objective** (proficiency standard + cost) | the definition of "working" — the synthesis verify gate and run/use scoring grade against it | just-enough specs / CBEA outcomes (`effect/standard/conditions`) |
| boundary + **red lines** | the safety envelope; split *machine-checkable* vs *qualitative* | boundary triage + `load_bearing_constraints`; red lines may extend `hp-propose-threat-model` |
| seed skill (or its spec) | base-skill line C — gives the loop something to run and a baseline to beat | a p-spec the human authors / specs |

**Interface:** one artifact (or a small bundle) emitted at the end of an HP pass and read by archi.
archi only needs the *fields above to be present and unambiguous*; the serialization format is HP's
call. Likely a projection/serialization of existing `concept.md` + `dictionary.yaml` + p-spec/c-spec
content, plus the red-line split, which is the genuinely new piece.

**Acceptance criteria:**
- archi can ingest the contract and run a control loop for the domain with **no domain logic
  hand-coded in archi** beyond what the contract supplies (objective + seed + schemas).
- The contract distinguishes **machine-checkable** red lines (a predicate archi can evaluate on a
  proposed action/state every tick) from **qualitative** red lines (prose for the layer-3 audit).
- Re-running the HP pass on an updated domain re-emits an updated contract (the contract is a
  regenerable projection, not a hand-maintained fork).

**Ownership:** HP **produces**; archi **consumes**. archi will not author the contract.

**Open for the HP team:** exact serialization format; how much is auto-projected from existing
artifacts vs newly elicited; whether the red-line split warrants extending `hp-propose-threat-model`.

---

## R2 — new skill `hp-audit` / `hp-recertify` (periodic governance, layer 3)

> **Status (2026-06-04): drafted as [`../toolkit/skills/hp-audit.md`](../toolkit/skills/hp-audit.md).**
> Consumer-neutral; composes `hp-ingest`; consumes the R1 contract as the declared envelope. The novel
> drift-detection core + verdict schema are intentionally NOT yet coded — full proof needs a consumer
> running a grown corpus to emit operational evidence (archi isn't there yet). The skill spec fixes the
> WHAT (inputs, drift modes, verdict, the consumer-owns-the-trigger seam) so the code can follow.

**What (general — NOT archi-specific):** a dedicated HP skill that periodically **re-certifies an
evolving HP-modeled system against its declared concept/envelope, using operational evidence**, and
classifies drift. This is a *general* HP governance capability: any HP-architected system that keeps
changing drifts from its `concept.md` over time — a **human team adding modules** (the code drifts
from the declared architecture) just as much as an **autonomous process adding components**. **It
composes `hp-ingest`** — deriving the *implicit current* concept from the evolved artifacts is exactly
hp-ingest's brownfield job; `hp-audit` adds the *diff against the declared envelope* and the *drift
classification* on top.

> **archi is one consumer, not the definition.** Its corpus is fast and machine-grown and needs the
> drift-monitor trigger below — but the input contract is specified in **consumer-neutral** terms so
> HP does not bake archi's vocabulary (*capability vectors*, *corpus*, *synthesis*, *arbitrage*) into
> a general skill. archi's mapping is shown separately as a worked example (the "binding").

**Inputs — the general contract** (what `hp-audit` consumes from *any* consumer):
- **the evolved artifact set + provenance** — what was added/changed since the last certification,
  when, the justification or triggering situation, and **each artifact's declared characterization**
  (what it claims to do, and the conditions under which it is valid);
- **operational evidence** — what the system actually did and encountered: observed inputs,
  decisions, outcomes, and the distribution of situations met in operation;
- **the declared envelope** — the original concept: boundary, objective (the *stated* one **and** the
  *intended* one — see the Open note), and red lines.

**Inputs — the archi binding** (one consumer's mapping onto the general contract above):

| general input | archi's instantiation |
|---|---|
| evolved artifact set + provenance | synthesized / matured **skills** + the synthesis log (when, why, for which situation) |
| each artifact's declared characterization | the skill's **capability vector** (its Pareto behavior profile across situation-space) + proficiency standard |
| operational evidence | run/use **telemetry** (the Executor port's `read_telemetry`) + objective scores + estimated situation vectors |
| declared envelope | the **R1 domain contract** / `concept.md` (red lines + objective) |

archi supplies a thin **adapter** that emits these from its own constructs; `hp-audit` never sees a
"capability vector" — it sees "an artifact's declared behavior characterization."

**Detects (the drift modes layers 1–2 structurally cannot):**
- **scope-creep** — artifacts operating in regions outside the intended envelope;
- **objective-gaming** — the system beats the *stated* objective by exploiting the gap to the
  *intended* one;
- **compositional drift** — individually-conformant artifacts combining into collective behavior that
  approaches a red line (in archi: safe skills composed via the selector/arbitrage);
- **distributional drift** — the observed situation distribution has moved away from what the
  envelope was specified against (the envelope itself may need redrawing);
- **red-line-margin proximity** — growth trending toward a declared boundary.

**Produces:** a re-certification **verdict** — confirm / re-draw the envelope, flag specific skills or
regions to veto or re-spec, and/or re-spec the objective — fed back into the contract. (Verdict schema
is HP's to design.)

**Trigger (the seam — the consumer's responsibility, not the skill's):** the *trigger* varies by
consumer; the *audit* is the same skill. A fast machine-driven consumer (archi) runs a cheap
deterministic **drift monitor** and escalates `on_surprise`, so governance stays cheap enough to
actually happen; a human-evolved system might run `hp-audit` per release or on a cadence. **archi
owns its monitor; HP owns the audit.** What a consumer's trigger emits on escalation, and what
`hp-audit` consumes, is the interface to agree.

**Acceptance criteria:**
- Given an evolved artifact set + operational evidence + the declared envelope, `hp-audit` produces a
  verdict that names concrete artifacts/regions and a re-certified (or re-drawn) envelope.
- An injected drift case (an artifact that games the stated objective, or operates near a qualitative
  red line) is **flagged** even though it conformed to whatever per-artifact gate the consumer ran.
- The audit reuses `hp-ingest` for reading the evolved artifacts rather than reimplementing it.
- The skill takes no archi-specific input type: the contract is the consumer-neutral one above, and
  archi (or any consumer) adapts onto it.

**Ownership:** HP **owns** the audit skill + verdict schema. archi owns the drift monitor + acting on
the verdict (veto/re-spec/feed-back).

**Open for the HP team:** the verdict schema; how `hp-audit` represents "objective-gaming" detection
(likely needs the *intended* objective captured at R1 framing time, not just the stated one).

---

## The seam — interface ownership (what to agree on)

| Artifact | Writer | Reader | Status |
|---|---|---|---|
| domain contract (R1) | HP | archi | **needs format agreed** |
| audit input bundle (evolved artifacts + provenance + operational evidence) | archi (via adapter) | `hp-audit` | consumer-neutral contract; archi binds onto it |
| audit verdict (R2) | `hp-audit` | archi + human | HP designs; archi acts |
| drift-monitor escalation signal | archi | (wakes `hp-audit`) | archi emits; trigger contract |

## Explicitly out of scope for HP

- archi's **layer-1 hot-path guardrail**, **layer-2 per-synthesis safety gate**, and the **drift
  monitor** — these are archi's, not asked of HP.
- archi's corpus store, executor, synthesis loop — archi's.
- The HP team owns all **HOW** decisions (formats, schemas, skill internals); this ask fixes only the
  **WHAT** and the **interface fields** archi depends on.

## Why this is lower-effort than it looks

R1 is largely a *projection/serialization* of artifacts HP already emits (`concept.md`,
`dictionary.yaml`, p-specs/c-specs) — the genuinely new part is the **red-line split** and a stable
machine-readable shape. R2 is a new skill but **composes `hp-ingest`** rather than building corpus
reading from scratch; its novel core is drift-detection against a declared envelope.
