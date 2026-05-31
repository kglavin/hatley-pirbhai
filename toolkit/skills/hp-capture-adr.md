---
name: hp-capture-adr
description: Mid-decision capture of an Architecture Decision Record (Nygard 2011). Invoked as a follow-up from any other proposal skill when a non-obvious decision with viable alternatives is locked. Writes a structured ADR to `adrs:` and produces a rendered sidecar.
---

# hp-capture-adr

## When to use

**Mid-decision**, not stage-end. Whenever another skill (`hp-propose-context`, `hp-propose-decomp`, `hp-propose-cspec`, `hp-propose-pspec`, `hp-propose-architecture`, etc.) encounters a non-obvious choice with viable alternatives and real trade-offs, invoke this as a follow-up to capture the ADR.

Triggering conditions:

- A proposal decision had ≥ 2 alternatives with non-trivial trade-offs (not just defaults vs custom).
- A constraint emerged that wasn't obvious to a fresh reader of the requirements.
- A non-default option was chosen and the rationale is worth preserving.
- A new design constraint is being imposed (e.g., regulatory, compliance, deployment-environment).

This is the **Propose + Surface Ambiguity** AI move applied to *decision provenance*. Modernization #10.

## What it does

Adds a new entry to the dictionary's `adrs:` section following Michael Nygard's 2011 ADR format — Context / Decision / Consequences / Alternatives. Cross-links the ADR to the model elements it `affects:` (modules, interconnects, flows, processes, stores). Optionally adds MITRE ATT&CK / CWE / compliance framework references (modernization #8.3).

After lock, [`hp-render`](hp-render.md) produces a per-ADR markdown sidecar at `adrs/<id-short>.md`.

Standard decision set (8 fields):

| # | Decision | What it pins down |
|---|---|---|
| 1 | Title | Short and *decision-y* — "BLE chosen for transport," not "Transport considerations" |
| 2 | Status | `proposed` / `accepted` / `deprecated` / `superseded` |
| 3 | Date | When the decision was made (auto-set to today) |
| 4 | Author | Team or individual responsible |
| 5 | Context | What's the situation that forced a choice? Pre-filled from the invoking proposal. |
| 6 | Decision | What did we decide? The chosen alternative + its operative parameters. |
| 7 | Consequences | What follows? Forward-looking trade-offs and downstream effects. |
| 8 | Alternatives | What else was considered, and why rejected? Pre-filled from `[ ]` options not chosen. |
| 9 *(optional)* | Affects | Cross-references: which `modules` / `interconnects` / `flows` / `processes` / `stores` does this affect |
| 10 *(optional)* | References | MITRE ATT&CK / CWE / compliance framework IDs (modernization #8.3) |
| 11 *(optional)* | Supersedes | Prior ADR id this decision replaces |

## Behavior

When invoked, conversationally:

1. **Receive context from the invoking skill.** Take the proposal's Decisions table + the chosen alternative + the rejected alternatives as input.
2. **Propose a title.** Decision-y phrasing: "BLE chosen for controller-app transport," "Outage handling lives inside the Energy Manager CSPEC," "Dashboard is local-LAN only by default."
3. **Auto-fill Context** from the invoking proposal's prose around the decision. Edit for clarity, but keep the constraints + alternatives space visible.
4. **State the Decision crisply.** One paragraph: what was chosen, with operative parameters. Avoid restating the alternatives here — that's the next section.
5. **Author Consequences (forward-looking).** What does this decision *commit* the project to? What downstream choices become easier or harder? What's now off the table?
6. **List Alternatives explicitly.** Pre-fill from the proposal's `[ ]` options that weren't chosen. For each, note the *operative reason it was rejected* — not the alternative's general weaknesses.
7. **Identify Affects.** Walk the proposal's decisions and identify which model elements this ADR affects. Cross-link them by stable id.
8. **Offer References.** If the decision touches security, ask which MITRE ATT&CK techniques / CWE entries / compliance controls are addressed.
9. **Write to `dictionary.yaml`'s `adrs:` section.** Use prefix `adr_NNN_<short>` where NNN is the next sequential number.
10. **Render the sidecar via [`hp-render`](hp-render.md).**

## Discipline

- **Written *when* the decision is made, not retroactively** *(tactic: ADR-as-you-go)*. Retroactive ADRs are written from memory, which is what they were invented to replace. Capture immediately or not at all.
- **Title is decision-y, not topic-y.** "BLE chosen for transport" not "Transport considerations." A reader scanning the ADR list should see *what was decided*, not *what was discussed*.
- **Consequences are forward-looking.** "Future expansion to cloud monitoring is independent" — not "we discussed cloud monitoring." Consequences track what's now constrained, what's now free, what becomes the next decision.
- **Alternatives must include the operative rejection reason.** "Rejected: power budget" is the operative reason. "Rejected: complexity" is too vague — what was complex?
- **Cross-reference every affected element.** If the ADR is about an interconnect choice, list the modules + interconnects + flows it touches. The `affects:` field is what makes ADRs navigable from architecture diagrams.
- **References by ID, not prose** *(modernization #8.3 / tactic: Catalog-reference discipline)*. "Mitigates T1078" not "addresses credential-based attacks." MITRE catalogs are the shared vocabulary.
- **Status lifecycle is real.** An ADR superseded by another should have `status: superseded` and the new ADR's `supersedes:` field set. Don't silently rewrite old ADRs.
- **One decision per ADR.** If a proposal locks 5 non-obvious decisions, that's 5 ADRs. Cramming them is how the format loses value.

## Lived examples

- [`examples/fishing-rig/adrs/001-ble-transport.md`](../../examples/fishing-rig/adrs/001-ble-transport.md) — Source `adr_001_ble_transport` in fishing-rig's dictionary. Captures the BLE-vs-WiFi-vs-LoRa choice with full alternatives + MITRE T1078 + T1565 + CWE-319 + CWE-294 references. Retroactively authored as part of Commit 1; would have been better captured mid-decision.
- [`examples/solar/adrs/001-outage-inside-cspec.md`](../../examples/solar/adrs/001-outage-inside-cspec.md) — `adr_001_outage_inside_cspec` documenting why outage handling lives inside `proc_compute_balance`'s CSPEC rather than as a separate process bubble.
- [`examples/solar/adrs/002-local-only-dashboard.md`](../../examples/solar/adrs/002-local-only-dashboard.md) — `adr_002_local_only_dashboard` documenting the local-LAN-only default. Adds CCPA compliance reference.

## Implementation status

**Skill description: ✅ drafted.** Backing code: ✅ schema (`ADR`, `ADRStatus`) + loader + validator (reference integrity on `affects` + supersedes; catalog-reference ID format checks) + renderer (`render/adr.py` markdown emitter) all live as of Commit 1.

What this skill adds is the **conversational mid-decision capture pattern**. The schema is already there; this codifies the *when* and *how* the AI uses it.

## See also

- Tactic source: [`PLAN.md` > Modernization Tactics > ADR-as-you-go](../../PLAN.md)
- Schema source: [`toolkit/MODERNIZATION_DESIGN.md` > #10 ADRs](../MODERNIZATION_DESIGN.md)
- Designed-as-companion-to: all proposal skills (`hp-propose-{context,decomp,cspec,pspec,architecture}`, plus the new modernization skills) — each should end with "any decisions worth ADR-capturing?"
- Renderer: [`hp-render`](hp-render.md) emits `adrs/<id>.md` per ADR
- Source: Michael Nygard (2011). *Documenting Architecture Decisions*. ThoughtWorks blog post; community-standard format.
