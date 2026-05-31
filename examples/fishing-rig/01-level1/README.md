# Level 1 / First Decomposition — AutoFishingRig

The first decomposition of `sys_root` (AutoFishingRig) into internal processes + data store + internal flows.

## Status

**Stage 2 in progress.** Decomposition under review via [`proposal.md`](proposal.md) — form-based batch review with embedded draft DFD.

## HP discipline at this level (recap)

- **Balancing** — every level-0 boundary flow into/out of `sys_root` must appear at the level-1 DFD as a boundary-crossing flow, refining its endpoint to an internal process.
- **Leveling** — all level-1 bubbles at the same level of abstraction.
- **7±2** — aim for 5–7 internal bubbles.
- **Refuse to proceed** — no level-2 / CSPEC work until level-1 is locked.

## Files (planned, in order)

| File | Status |
|---|---|
| `proposal.md` | Active — form-based decomposition review |
| `proposal-dfd.{d2,svg}` | Draft visual (pre-lock) |
| `naming-review.md` | Pending — after decomposition locks |
| `dfd.md` / `dfd.html` / `dfd.d2` | Pending — generated from dictionary after lock |
| `dfd-mermaid.svg` / `dfd-d2.svg` | Pending — rendered after sources |
| `cspecs/bite-detector/` | Pending — CSPEC for the brain bubble |
