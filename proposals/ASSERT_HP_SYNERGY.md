# ASSERT ↔ HP Toolkit — Synergy Proposal

**Status:** quick proposal / exploration note. No implementation decisions yet.

**Audience:** HP toolkit maintainers and ASSERT maintainers looking for a small, rigorous bridge between
specification discipline and executable behavior evaluation.

**Origin:** discussion after reviewing Microsoft's ASSERT repository, 2026-06-05. The working
interpretation of ASSERT is: generate an expected-behavior specification, run an LLM or agent in an
environment that captures actual behavior, then reconcile observed behavior against expected behavior
using structured policy/rubric grounding and trace evidence.

**One-line thesis:** HP can harden the *front* of ASSERT's eval loop; ASSERT can provide executable
behavior evidence for the *back* of HP's audit loop.

---

## 1. Why These Fit Together

Hatley-Pirbhai and ASSERT sit on opposite sides of the same control problem.

HP is strong at declaring what the system is supposed to be before execution:

- what boundary the system owns;
- who/what sits outside the boundary;
- what flows cross that boundary;
- which outcomes define success;
- what constraints are load-bearing;
- which red lines must not be crossed;
- how requirements, architecture, modules, and specifications trace to one another.

ASSERT is strong at collecting evidence after execution:

- generate scenario and prompt test cases from a behavior spec;
- run a model, hosted endpoint, callable, or agent target;
- capture output, transcripts, tool calls, and OpenTelemetry/OpenInference traces;
- judge actual behavior against a taxonomy, rubric, and policy stance;
- emit local artifacts that can be inspected, diffed, and shared.

The bridge is straightforward:

```text
HP concept / dictionary / contract
  -> ASSERT eval_config.yaml
  -> ASSERT run artifacts
  -> HP-style audit verdict
```

HP supplies specification rigor. ASSERT supplies executable evidence.

---

## 2. Proposed Direction

Do not merge the methodologies. Keep the seam clean.

HP should not become an LLM eval runner. ASSERT should not become a full HP modeling tool. The useful
integration is a pair of projections:

1. **HP-to-ASSERT:** project HP framing artifacts into stronger ASSERT evaluation configs.
2. **ASSERT-to-HP:** project ASSERT run artifacts into HP-style governance/audit evidence.

This keeps both tools honest: HP remains the requirements and architecture discipline; ASSERT remains
the local-first behavioral evaluation pipeline.

---

## 3. HP-to-ASSERT: Spec Hardening

ASSERT configs would benefit from HP's framing discipline before the test generator sees the behavior
description.

### 3.1 Outcome shape: effect / standard / conditions

HP's CBEA-style outcome structure maps naturally onto ASSERT behavior specs.

Instead of:

```yaml
behavior:
  description: The assistant should provide safe financial advice.
```

prefer:

```yaml
behavior:
  description: |
    Effect: The user receives financial guidance that is educational rather than directive.
    Standard: The response distinguishes general information from personalized advice, discloses
      uncertainty, and refuses direct buy/sell/security-allocation instructions.
    Conditions: Applies when users ask about securities, retirement allocation, leverage, tax treatment,
      high-risk assets, or short-term market timing.
```

This gives ASSERT's taxonomy generation and judge stages more concrete material than a broad behavior
label.

### 3.2 Boundary triage: controlled / influenced / environment

HP's boundary triage can become a standard ASSERT context block.

For an LLM or agent evaluation:

- **controlled:** target behavior, system prompt, tool-call policy, response format, refusal policy;
- **influenced:** user prompt distribution, retrieved documents, tool results, trace visibility;
- **environment:** law, vendor APIs, market facts, user goals, real-world state, adversarial inputs.

This helps ASSERT distinguish "the system should control this" from "the system should respond
appropriately to this but cannot control it."

### 3.3 Machine-checkable vs qualitative red lines

HP's proposed executable contract splits red lines into:

- **machine-checkable:** JSON schema, forbidden fields, citation count, must/must-not-call tool,
  latency ceiling, exact policy token, private-data leakage predicate;
- **qualitative:** deception, unsafe advice, objective gaming, inadequate uncertainty, manipulative
  framing, policy evasion.

ASSERT could use this split to run deterministic checks before or beside LLM judging. That reduces
judge burden and makes eval results more auditable.

### 3.4 Traceability from HP entities to ASSERT artifacts

A projected ASSERT config should preserve HP identifiers where possible:

- behavior taxonomy nodes trace back to HP outcomes, load-bearing constraints, red lines, or PSPECs;
- generated test cases trace back to taxonomy nodes and HP boundary flows;
- judge dimensions trace back to specific standards or constraints;
- failed verdicts trace back to transcript evidence and HP entities.

The payoff is not cosmetic. It means a failed ASSERT run can say which declared HP requirement or
constraint is under pressure.

---

## 4. ASSERT-to-HP: Behavioral Evidence

ASSERT artifacts can feed HP's audit and recertification ideas.

`hp-audit` asks whether an evolved system still lives inside its declared envelope. ASSERT can provide
the operational evidence bundle:

- observed inputs / scenarios;
- actual outputs;
- transcript turns;
- tool calls;
- trace spans;
- judge verdicts;
- citations / evidence excerpts;
- distribution of tested situations.

This creates a concrete evidence source for HP drift modes:

| HP audit drift mode | ASSERT evidence that can reveal it |
|---|---|
| scope-creep | target succeeds or acts confidently outside declared behavior boundary |
| objective-gaming | output optimizes stated metric while violating intended policy |
| compositional drift | individually acceptable tool calls combine into unsafe final behavior |
| distributional drift | new prompts/scenarios cluster outside the original test envelope |
| red-line-margin proximity | repeated near-misses on machine-checkable or qualitative red lines |

ASSERT already has the raw material. HP gives it a richer interpretation frame.

---

## 5. Candidate Bridge Artifacts

### 5.1 `hp-assert-export`

A small projection step that reads an HP `concept.md`, `dictionary.yaml`, or executable contract and
emits an ASSERT `eval_config.yaml`.

Initial scope:

- map HP outcomes to `behavior.description`;
- map boundary triage to ASSERT `context`;
- map red lines to judge dimensions and optional deterministic checks;
- preserve HP IDs as metadata;
- emit warnings for underspecified outcomes, flows, or red lines.

### 5.2 `assert-hp-evidence`

A small projection step that reads ASSERT run artifacts and emits an HP audit evidence bundle.

Initial scope:

- identify run, suite, config, and behavior taxonomy;
- summarize test-case distribution;
- group failures by taxonomy node / judge dimension;
- preserve transcript and citation pointers;
- classify candidate drift modes for human review, without declaring a final HP audit verdict.

### 5.3 `hp-audit` consumes ASSERT evidence

Longer term, `hp-audit` could accept ASSERT evidence as one source of operational evidence.

This should remain consumer-neutral: ASSERT is one evidence provider, not the definition of the audit
input contract.

---

## 6. Implementation Sketch

Start with the lowest-risk bridge:

1. Add a proposal-backed example, not a new toolkit primitive.
2. Pick one ASSERT example config and one small HP example.
3. Manually write the projected ASSERT config from HP-style framing.
4. Run ASSERT.
5. Write a short HP-style audit note over the ASSERT artifacts.
6. Only then decide whether `hp-assert-export` or `assert-hp-evidence` deserves code.

The first proof should optimize for traceability and readability, not automation.

---

## 7. Open Questions

- Which HP source should be canonical for ASSERT export: `concept.md`, `dictionary.yaml`, the executable
  domain contract, or a small subset of all three?
- Should machine-checkable red lines become ASSERT deterministic prechecks, postchecks, or first-class
  judge dimensions?
- Where should HP IDs live in ASSERT artifacts so failures can trace back without changing ASSERT's
  public schema too much?
- How much of ASSERT's judge output is trustworthy enough for HP audit verdicts, versus merely useful
  evidence for a human reviewer?
- Should the bridge live in HP, in ASSERT, or as a small adapter package owned by neither?

---

## 8. Non-goals

- Do not make HP depend on ASSERT to be useful.
- Do not make ASSERT require HP modeling before ordinary evals.
- Do not replace ASSERT's taxonomy/judge pipeline with HP diagrams.
- Do not treat LLM judge verdicts as the same thing as HP validation errors.
- Do not collapse qualitative red lines into fake machine-checkable predicates.

---

## 9. Recommendation

Pursue this as a thin adapter and worked example first.

The most valuable near-term move is not a large integration. It is an HP-shaped specification template
for ASSERT configs:

```text
behavior = effect + standard + conditions
context = controlled + influenced + environment
judge dimensions = standards + red lines
metadata = HP traceability IDs
```

That would immediately improve ASSERT eval quality while keeping the methodology boundary intact.

The second move is an ASSERT evidence projection for `hp-audit`, allowing HP to reason over real
behavioral evidence rather than only static model conformance.

Together, the pair gives a clean loop:

```text
declare intent rigorously -> execute and observe behavior -> reconcile evidence against intent -> revise the envelope
```
