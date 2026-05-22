# Bite Detector — CSPEC

[Control Specification](../../../../toolkit/reference/HP_QUICK_REF.md#cspec--control-specification) for the `Bite Detector` bubble in the [level-1 DFD](../../dfd.generated.html). State-rich; covers the entire fishing sequence (idle → tighten → armed → bite → hook-set → reel → landed) plus fault handling.

## Status

**Stage 3 in progress.** Proposal phase active — engage via [`proposal.md`](proposal.md).

## Files (planned, in order)

| File | Status |
|---|---|
| `proposal.md` | Active — form-based review of the state machine |
| `proposal-states.{mmd,svg}` | Draft state-diagram (pre-lock) |
| `naming-review.md` | Pending — after states are locked |
| `cspec.{md,html,d2}` | Pending — locked state-machine views |
| `cspec-mermaid.svg` / `cspec-d2.svg` | Pending — rendered |

## HP discipline at this stage

- The CSPEC defines **states + transitions + events + actions** for one process bubble (the brain at level 1).
- Every reachable system condition must be covered; no implicit states, no dangling transitions.
- The state machine **activates / deactivates sibling processes** in the level-1 DFD via process controls (e.g., enable Reel Controller during Tightening / SettingHook / Reeling; disable during Armed / Idle).
- **Refuse to proceed** to lower levels until the CSPEC is locked.
