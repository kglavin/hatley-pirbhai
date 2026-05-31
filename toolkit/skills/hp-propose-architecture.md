---
name: hp-propose-architecture
description: Stage 5 — draft a form-based Architecture Model proposal. Identifies the system's architecture modules (hardware / software / organizational), the architecture flows between them, the physical interconnects carrying those flows, and the allocation of every requirements-model leaf process / CSPEC / store to the modules. Writes a reviewable proposal with Claude's recommended defaults pre-checked.
---

# hp-propose-architecture

## When to use

After the requirements model is locked through Stage 4 (all PSPECs in place). Stage 5 maps *what* the system does onto *how* it's physically built — hardware modules, software modules, organizational modules, and the channels between them. The bridge is **allocation**: every leaf requirements process / CSPEC / data store ends up assigned to one or more architecture modules.

Specifically:

- The project's Stage 4 is locked (`hp-status` reports ✅ on Stages 1–4).
- The system has enough physical reality (real components, real channels) to model — even small projects benefit from declaring "this runs on an ESP32; the angler interacts via a phone app."
- The team is starting to think about implementation, deployment, or interface contracts.

This is the **Propose + Surface Ambiguity** AI move applied to the Architecture Model.

## What it does

Drafts `architecture/proposal.md` as a form-based batch-review document covering the **Core 6** scope (per [`toolkit/ARCH_DESIGN.md`](../ARCH_DESIGN.md)): AFD + AID + AMS + AIS + Architecture Module + Architecture Dictionary integration. AMDs, MIDs, and push/pull indicators are deferred per the scope choice.

Standard decision set (7–10 decisions; project-shape varies):

| # | Decision | What it pins down |
|---|---|---|
| 1 | Top-level module decomposition | How many architecture modules at the root layer (e.g., "controller board + mobile app") |
| 2 | Module kinds | For each: `hardware` / `software` / `organizational` |
| 3 | Allocation strategy | Which requirements processes / CSPECs / stores land on which module(s); single-allocation default vs replication |
| 4 | Architecture flows | What flows between modules — data, material, or energy (1988 limited to data; 2000 broadens) |
| 5 | Interconnects | Physical channels — wired buses, wireless, mechanical, power/ground |
| 6 | Module numbering | Adopt the book's `AM 1`, `AM 1.1`, `AM 1.2` hierarchy (optional) |
| 7 | AMS depth | All 6 sections per module (description / cross-reference / rationale / justification / constraints / interfaces), or just description + cross-reference for the first cut? |
| 8 | Anything else | Free-form escape hatch |

Each decision lists alternatives with Claude's recommended default **pre-checked** and provenance noted ("matches lived example on fishing-rig"; "AI inference from your README"; "minimum coarseness given the bubble count"). The user toggles overrides in MPE, saves once, pings back.

On lock, the skill writes the `## ✅ Status: Locked YYYY-MM-DD` header, populates `dictionary.yaml`'s five new architecture sections, then runs [`hp-validate`](hp-validate.md) (catches allocation gaps + reference integrity + module-numbering uniqueness) and [`hp-render`](hp-render.md) (emits AFD/AID across three notations + AMS/AIS markdown sidecars).

## Behavior

When invoked, conversationally:

1. **Read the requirements model.** Load `dictionary.yaml`; enumerate every leaf process (`kind=process`, `needs_cspec=False`, no child processes), every CSPEC owner (`needs_cspec=True`), every data store. These are the components that must end up allocated.
2. **Identify candidate architecture modules.** From the project description + the leaf-process responsibilities, propose a small set of modules (typically 2–5 at the root layer). Apply Propose with provenance — "controller board because three processes are real-time and need physical IO"; "mobile app because the UI process needs touchscreen + BLE".
3. **Draft allocations.** Each leaf process gets allocated to ≥ 1 module. Cross-cutting concerns (faults, alerts) usually live with their CSPEC's owning module.
4. **Identify architecture flows.** For each pair of allocated-to-different-modules requirements components, draft an architecture flow that carries the relevant requirements flow(s). The validator's `architecture_flow_coverage_pct` metric reports completeness.
5. **Identify interconnects.** The physical channel for each architecture flow — BLE, RS485, JSON over WiFi, mechanical linkage, etc. Multiple flows can ride one interconnect; interconnects can exist without flows (e.g., a power/ground bus).
6. **Draft AMS skeletons.** For each module, draft the AMS with at least `description` + cross-reference (allocations are derived from the module entry, but the prose around them lives in the AMS).
7. **Write `architecture/proposal.md`** with: stage header → form-based-review instructions → AFD draft (inline Mermaid) → AID draft → allocation table (every leaf process → module) → AMS skeletons → numbered decisions with alternatives + pre-checked recommendation + provenance.
8. **Tell the user**: "Open `architecture/proposal.md` in MPE, override any defaults, save, ping me when done."
9. **On user ping**: parse decisions, write Status: Locked block + resolution table, populate `dictionary.yaml`'s five architecture sections, run [`hp-validate`](hp-validate.md), then [`hp-render`](hp-render.md) to produce AFD/AID + AMS/AIS sidecars.

## Discipline

These come from the 2000 book §4.2. Each cites its source.

- **Architecture is *what* the system is built from, not *how* the requirements are met** (2000 §4.2.1). If the AMS body starts describing algorithms or control flow, it's drifting into PSPEC/CSPEC territory.
- **Every leaf requirements process / CSPEC / data store must be allocated to ≥ 1 module** (2000 §4.2.5.4). The validator (`hp-validate` rule 1–3) catches this as an error.
- **One requirements component can be allocated to multiple modules** — replication, redundancy, hot/cold standby. Reflect this by listing the component in `allocated_processes` (etc.) on each module that hosts it.
- **No 7±2 limit on modules per diagram** (2000 §4.2.5.1: "An AFD can be drawn with any number of architecture modules and architecture flows. There should be as many modules as one finds in the real system."). Match physical reality, not a layout aesthetic.
- **Module names: real-world names** (2000 §4.2.2.1). "Main Controller Board" not "Module A"; the people on the project should recognize the name.
- **Architecture flows can carry data, material, OR energy** (2000 §4.2.2.3) — the requirements model is data-only, but the architecture model broadens.
- **Interconnects can exist without flows** (2000 §4.2.6.1). Power/ground buses are valid AID entries even if nothing semantic "flows" on them.
- **AMS and AIS reference outside sources** (2000 §4.2.5.4) — "they should make such references rather than duplicate information." Industry standards, datasheets, register maps go *by reference*, not *embedded*.
- **Mapping flows → interconnects lives in `architecture_interconnects.carries:`, NOT in the AIS prose** (2000 §4.2.6.2). The AIS describes the channel; the dictionary records what rides on it.
- **Module numbering, when present, must be unique throughout the model** (2000 §4.2.2.1). The validator surfaces duplicates as a warning.

## Lived examples

- *(To be populated as the first AFD + AMS lands.)* — first lived example will be fishing-rig (smaller surface; angler app + controller board + cloud logger), followed by solar.

## Implementation status

**Skill description: ✅ drafted.** Backing code: ✅ schema (`ArchModule`, `ArchFlow`, `ArchInterconnect`, `ArchModuleSpec`, `ArchInterconnectSpec`, `ArchModuleConstraints`) + loader + validator (15 rules) + renderers (AFD + AID across Mermaid/D2/Cytoscape; AMS + AIS markdown sidecars) + status reporting all live as of 2026-05-22. See [`toolkit/ARCH_DESIGN.md`](../ARCH_DESIGN.md) for the design rationale (book-cited).

What this skill adds is the **conversational front of the funnel**: identifying candidate modules from the requirements model + the project's physical reality, drafting allocations, writing AMS/AIS prose, and managing the form-based lock-and-populate loop.

## See also

- Design doc: [`toolkit/ARCH_DESIGN.md`](../ARCH_DESIGN.md)
- Predecessors: [`hp-propose-context`](hp-propose-context.md) → [`hp-propose-decomp`](hp-propose-decomp.md) → [`hp-propose-cspec`](hp-propose-cspec.md) → [`hp-propose-pspec`](hp-propose-pspec.md) — Stage 5 follows once the requirements model is fully locked.
- Followup: [`hp-confirm-naming`](hp-confirm-naming.md) reviews module names; [`hp-validate`](hp-validate.md) checks allocation balancing + reference integrity; [`hp-render`](hp-render.md) emits AFD/AID + AMS/AIS sidecars.
- HP reference: [`HP_QUICK_REF.md`](../reference/HP_QUICK_REF.md) — Architecture Model, AMS, AIS entries.
- Source: Hatley, Hruschka & Pirbhai (2000), ch. 4 §4.2 — *Architecture Model*. The 1988 book did not have the Architecture Model in this form.
