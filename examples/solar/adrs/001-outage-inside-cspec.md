# ADR — Outage handling lives inside the Energy Manager CSPEC

**ID:** `adr_001_outage_inside_cspec`
**Status:** Accepted
**Date:** 2026-05-22
**Author:** solar dogfood

*Generated from `dictionary.yaml`. Do not hand-edit.*

## CONTEXT

The system needs to handle grid outages (utility goes down → battery
takes over → utility returns) without dropping into a fault state. Two
approaches were on the table during Stage 2: (a) make outage handling
a separate process bubble that gates the diversion loop; (b) make
outage handling a mode of the Energy Manager's CSPEC alongside
GridTie and Fault.

## DECISION

Outage handling is an `Island` mode of the Energy Manager CSPEC,
peer to GridTie and Fault. The diversion-loop sub-states live
under GridTie; the Island mode has its own setpoint-passthrough
behavior; transitions are driven by Victron's reported mode.

## CONSEQUENCES

- The CSPEC is the single source of truth for "what mode is the
  system in" — no separate outage-state bubble to keep in sync.
- Victron is trusted as the authoritative mode source; we don't
  debounce its mode reports (the AC transfer is < 20 ms, fast
  enough that our 1 Hz tick has nothing meaningful to add).
- Future "manual override" behavior is a modifier *within* a
  mode (Decision 5), not a separate Manual mode.

## ALTERNATIVES CONSIDERED

- Separate outage-handler process bubble — rejected: forces every level-1 reader to gate on two states.
- Manual mode as a peer to GridTie/Island/Fault — rejected: doubles state count and pairs poorly with diversion sub-states.

## AFFECTS

- **Modules:** `am_controller_host`
- **Processes:** `proc_compute_balance`
- **States:** `state_grid_tie`, `state_island`, `state_fault`

---

*Format: Michael Nygard 2011 — Context / Decision / Consequences / Alternatives. See [`../toolkit/MODERNIZATION_DESIGN.md`](../toolkit/MODERNIZATION_DESIGN.md).*
