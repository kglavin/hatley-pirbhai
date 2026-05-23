---
name: hp-propose-threat-model
description: Per cross-trust-zone architecture interconnect — full STRIDE six-category threat-model pass with per-category narrative mitigations. Optional LINDDUN privacy pass. Anchor to MITRE ATT&CK / CWE / compliance frameworks. Microsoft SDL discipline.
---

# hp-propose-threat-model

## When to use

Per cross-trust-zone architecture interconnect — the validator forces this during `hp-validate` (Commit 4's STRIDE rule errors out if cross-zone interconnects lack `stride_mitigations:`). Also per architecture module with a non-trivial attack surface (auth servers, payment processors, anything bridging public ↔ privileged).

Specifically:

- `hp-propose-architecture` has locked an interconnect whose endpoints span different `trust_zone:` values (e.g., `internal_lan` ↔ `privileged`).
- `hp-validate` is failing with `interconnect crosses trust zones ... but has no stride_mitigations`.
- A new threat-modeling pass is requested (e.g., compliance audit, design review, post-incident).
- A LINDDUN privacy pass is needed because the system handles PII.

This is the **Propose + Surface Ambiguity** AI move applied to security threat modeling. Modernization #8.2 + #8.3.

## What it does

Drafts `architecture/threat-model-<interconnect-id>-proposal.md` as a form-based batch-review document. For each in-scope interconnect, walks the six STRIDE categories (Spoofing / Tampering / Repudiation / Info disclosure / Denial of service / Elev. of privilege) and proposes per-category narrative mitigations. Optionally adds a LINDDUN privacy pass (7 categories for PII-handling systems). Cross-links to MITRE ATT&CK / CWE / compliance framework IDs (modernization #8.3).

Standard decision set per interconnect (8 + optional sections):

| # | Decision | What it pins down |
|---|---|---|
| 1 | **Spoofing** mitigation | How is impersonation prevented? Auth mechanism + identity verification. Out-of-scope is valid when justified. |
| 2 | **Tampering** mitigation | How is in-flight modification detected/prevented? Integrity check (HMAC / MIC / TLS / signed messages). |
| 3 | **Repudiation** mitigation | How are actions logged + attributable? `out_of_scope` is common (single-user; no audit requirement). |
| 4 | **Info disclosure** mitigation | How is the channel protected against eavesdropping? Encryption + data minimization. |
| 5 | **DoS** mitigation | Rate limits, backpressure, degradation strategy, blast-radius isolation. |
| 6 | **Elev. of privilege** mitigation | Capability boundaries, principle of least privilege, scope restriction. |
| 7 *(optional)* | **LINDDUN** privacy pass | 7 categories — Linkability / Identifiability / Non-repudiation / Detectability / Disclosure / Unawareness / Non-compliance. Required when PII is involved. |
| 8 | Catalog references | MITRE ATT&CK technique IDs (T1078 etc.); CWE IDs (CWE-79 etc.); compliance framework IDs (SOC2-CC6.1, ISA-62443-SL2, NIST-AC-2, CCPA-1798.100). |

Each decision lists alternatives with Claude's recommended default **pre-checked** and provenance noted ("derived from the interconnect's `auth_required:` field"; "matches industry pattern for BLE-class links"; "out-of-scope because this is a single-user session"). The user toggles overrides in MPE, saves once, pings back.

On lock, the skill writes the `## ✅ Status: Locked YYYY-MM-DD` header, populates `dictionary.yaml`'s `stride_mitigations:` block on the target interconnect (and `linddun_mitigations:` if applicable), then runs [`hp-validate`](hp-validate.md) (satisfies the cross-trust-zone STRIDE rule; checks catalog-reference ID formats) and [`hp-render`](hp-render.md) (AIS sidecar gains `## THREAT MODEL (STRIDE)` table + `## CATALOG REFERENCES` footer).

## Behavior

When invoked, conversationally:

1. **Identify in-scope interconnects.** Default: every architecture interconnect whose endpoints span two different `trust_zone:` values. Optional: any single interconnect by id. Optional batch: "all of them."
2. **Per interconnect, walk STRIDE.** For each of the 6 categories:
   - Pose the threat question (e.g., for spoofing: "How could an attacker impersonate one endpoint to the other?").
   - Propose a mitigation narrative based on the interconnect's `auth_required:` + `encryption:` fields + the protocol_standard in the AIS.
   - Mark `out_of_scope` (with rationale) for genuinely-not-applicable categories. Empty fields are validator warnings.
3. **Decide on LINDDUN.** If the system handles PII (user data, behavioral data, location, biometrics), walk the 7 LINDDUN categories. Otherwise, skip — but note the rationale.
4. **Identify catalog references.** From the proposed mitigations, ask which MITRE ATT&CK techniques are *addressed* (and which are explicitly *not addressed*, with rationale). Same for CWE entries. Compliance framework IDs for relevant audits (SOC2, ISA-62443, NIST CSF, CCPA, HIPAA).
5. **Write the proposal markdown** at `architecture/threat-model-<interconnect-id>-proposal.md`.
6. **Tell the user**: "Open the proposal in MPE, override any defaults, save, ping me when done."
7. **On user ping**: parse, populate `dictionary.yaml`'s `stride_mitigations:` + optional `linddun_mitigations:` + catalog reference fields on the AIS, run `hp-validate`, then `hp-render` to regenerate the AIS sidecar.

## Discipline

These come from Microsoft SDL (Howard & Lipner 2006) + LINDDUN (Wuyts & Joosen 2015) + lived experience from Commit 4.

- **Out-of-scope is valid; blank is not** *(modernization #8.2)*. Each STRIDE category gets either a narrative mitigation or an explicit `out_of_scope` with rationale. Validator warns on missing-but-empty fields. *Reason:* a blank field looks like an oversight; explicit out-of-scope shows the team thought about it and decided.
- **Catalog references by ID, not by prose** *(tactic: Catalog-reference discipline)*. "Mitigates T1078 (Valid Accounts) via mTLS" not "addresses credential-based attacks." MITRE catalogs are the shared vocabulary; auditors expect them.
- **STRIDE categories are independent.** A mitigation that addresses tampering doesn't automatically cover info disclosure. Authors often try to write one narrative covering multiple categories — resist this. If three categories really share a single mitigation, *reference the same paragraph from all three* explicitly.
- **Trust-zone-crossing is the trigger; same-zone interconnects don't require STRIDE**. Within a single trust zone, the assumption is that lateral-movement protections are handled at the zone boundary. (This isn't always defensible — but the validator only forces STRIDE on zone-crossings.)
- **Privacy ≠ security**. LINDDUN is the privacy companion to STRIDE. Personal data (PII, behavioral, location) deserves its own pass. Skipping LINDDUN for a PII-handling system is a real gap, not a stylistic choice.
- **Reference the *operative* catalog entry, not the most general one.** "T1078 (Valid Accounts)" is more useful than "T1078" alone in the prose; precise sub-techniques (T1078.001 Default Accounts; T1078.003 Local Accounts) are more useful still when applicable.
- **ISA/IEC 62443 for industrial/embedded contexts.** Where the system has industrial-control aspects, prefer 62443 security-level (SL1–SL4) classifications over generic IT-security frameworks. The toolkit's classical HP audience often falls here.
- **Don't over-claim mitigation strength**. "Mitigates X" should mean "addresses to a defensible degree." If the mitigation is partial, say so — "Partially mitigates X via Y; full mitigation requires Z which is out of scope for this iteration."

## Lived examples

- [`examples/fishing-rig/dictionary.yaml` > `ai_ble.stride_mitigations`](../../examples/fishing-rig/dictionary.yaml) — full 6-category STRIDE pass on BLE link. Pairs with ADR-001's MITRE T1078 + T1565 + CWE-319 + CWE-294 references.
- [`examples/solar/dictionary.yaml` > `ai_local_lan.stride_mitigations`](../../examples/solar/dictionary.yaml) — full 6-category STRIDE pass on LAN link. Pairs with ADR-002's MITRE T1190 + T1078 + CWE-306 + CWE-319 + CCPA-1798.100 references.
- [`examples/fishing-rig/architecture/specs/interconnects/ble.md`](../../examples/fishing-rig/architecture/specs/interconnects/ble.md) — rendered AIS with `## THREAT MODEL (STRIDE)` table.

## Implementation status

**Skill description: ✅ drafted.** Backing code: ✅ schema (`STRIDEMitigations`, `LINDDUNMitigations`; `references_mitre_attack`/`references_cwe`/`references_compliance` fields on AMS / AIS / ADR) + loader + validator (cross-trust-zone STRIDE rule; ID format checks; coverage metric `stride_coverage_pct`) + renderer (AIS gets `## THREAT MODEL (STRIDE)` + optional `## PRIVACY THREAT MODEL (LINDDUN)` + `## CATALOG REFERENCES` sections) all live as of Commit 4.

## See also

- Tactic source: [`PLAN.md` > Modernization Tactics > Cross-boundary STRIDE pass](../../PLAN.md); [`PLAN.md` > Methodology Tactics > C > Catalog-reference discipline](../../PLAN.md)
- Schema source: [`toolkit/MODERNIZATION_DESIGN.md` §5 — #8.2 STRIDE + #8.3 catalog references](../MODERNIZATION_DESIGN.md)
- Predecessor: [`hp-propose-architecture`](hp-propose-architecture.md) — declares trust zones on modules + interconnects; this skill fills the STRIDE narratives for the cross-zone ones.
- Companion: [`hp-capture-adr`](hp-capture-adr.md) — significant threat-model decisions warrant ADRs that reference back to the STRIDE pass.
- Sources:
  - Howard, M., Lipner, S. (2006). *The Security Development Lifecycle*. Microsoft Press.
  - Wuyts, K., Joosen, W. (2015). *LINDDUN privacy threat modeling*. KU Leuven Technical Report.
  - MITRE ATT&CK Framework (attack.mitre.org); MITRE CWE (cwe.mitre.org); MITRE D3FEND (d3fend.mitre.org).
  - ISA/IEC 62443 series — *Security for Industrial Automation and Control Systems*.
  - NIST CSF 2.0; NIST 800-53; OWASP ASVS.
