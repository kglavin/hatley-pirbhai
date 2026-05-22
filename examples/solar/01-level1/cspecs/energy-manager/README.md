# Energy Manager — CSPEC

[Control Specification](../../../../toolkit/reference/HP_QUICK_REF.md#cspec--control-specification) for the `Energy Manager` bubble in the [level-1 DFD](../../dfd.html). State-rich; covers the diversion control loop, night-discharge, outage coordination, and fault handling as **one hierarchical state machine** (per Decision 2 in level-1 proposal).

## Status

**Stage 3 state machine locked 2026-05-22.** Decomposition decisions ([proposal.md](proposal.md)) and state names ([naming-review.md](naming-review.md)) both resolved. State machine rendered in all three views. Event glossary and action specs are the remaining sub-stages.

## Files

| File | Status |
|---|---|
| `proposal.md` | ✅ Locked — 8 decisions resolved |
| `proposal-states.{mmd,svg}` | Historical — the as-proposed draft |
| `naming-review.md` | ✅ Resolved — 1 rename (SolarAssist), 12 kept |
| `cspec.md` / `cspec.html` / `cspec.d2` | ✅ Locked state-machine views |
| `cspec-mermaid.svg` / `cspec-d2.svg` | ✅ Rendered |
| `events.yaml` | Pending — formalize transition triggers into stable IDs |
| `actions.yaml` | Pending — side-effect specs per transition |
| `process-controls.yaml` | Pending — per-mode sub-process activation (anticipated in proposal Decision 7) |

## HP discipline at this stage

- The CSPEC defines **states + transitions + events + actions**, plus the **process controls** (the bar-notation in classic HP) that activate/deactivate sibling processes in the level-1 DFD.
- The state machine must cover **every reachable system condition** — no implicit states, no dangling transitions.
- Each transition has an **event** that triggers it and (optionally) an **action** that runs when it fires.
- **Refuse to proceed** to Stage 4 (PSPECs for leaves) until the CSPEC is locked.
