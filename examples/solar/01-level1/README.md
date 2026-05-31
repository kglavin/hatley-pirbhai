# Level 1 / First Decomposition — Solar Local Stack

This directory contains the **level-1 DFD** for the Solar Local Stack — the first decomposition of `sys_root` from the level-0 Context Diagram into internal processes (bubbles) and internal flows.

## Status

**Stage 2 complete** (locked 2026-05-22). Decomposition and naming both resolved via the form-based batch review pattern. Locked artifacts:

- `dfd.md` — Mermaid source + balancing check + internal-flow summary
- `dfd.html` — interactive Cytoscape workspace (click nodes / edges for details)
- `dfd.d2` — D2 source
- `dfd-mermaid.svg`, `dfd-d2.svg` — rendered diagrams
- `proposal.md` — proposal record (Status: Locked block at top)
- `naming-review.md` — naming review record (Status: Resolved block at top)

**Next: Stage 3** — CSPEC for the `Energy Manager` bubble (the state-rich brain: grid-tie / island / charging / fault modes).

## HP discipline at this level

- **Balancing.** Every level-0 flow into/out of `sys_root` must enter or leave the level-1 DFD through the same boundary. Flows can't appear or disappear at the boundary.
- **Leveling rule.** All level-1 bubbles must be at the same level of abstraction. None should be radically more or less detailed than its siblings.
- **7±2.** Aim for 5–7 internal bubbles. Below 5 = under-decomposed; above 9 = over-decomposed.
- **Refuse to proceed.** No level-2 decomposition until level-1 is locked.

## Files (planned, in order)

| File | Status |
|---|---|
| `proposal.md` | ✅ Locked — decomposition decisions recorded |
| `proposal-dfd.{d2,svg}` | Historical — the as-proposed draft (superseded by `dfd-*`) |
| `naming-review.md` | ✅ Resolved — naming decisions recorded |
| `dfd.md` / `dfd.html` / `dfd.d2` | ✅ Sources for the locked level-1 DFD |
| `dfd-mermaid.svg` / `dfd-d2.svg` | ✅ Rendered |
| `cspecs/` | Pending — Stage 3, starting with `Energy Manager` |
| `pspecs/` | Pending — for leaf bubbles when we reach level-2 |

## Open the form

Start at [`proposal.md`](proposal.md). Edit `[ ]` → `[x]` on choices you want; fill `Custom:` lines for anything that's not in the menu; add `Notes:` freely. Save once when done, ping when ready.
