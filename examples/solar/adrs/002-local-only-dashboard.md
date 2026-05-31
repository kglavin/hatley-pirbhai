# ADR — Dashboard is local-LAN only by default

**ID:** `adr_002_local_only_dashboard`
**Status:** Accepted
**Date:** 2026-05-22
**Author:** solar dogfood

*Generated from `dictionary.yaml`. Do not hand-edit.*

## CONTEXT

The owner needs a dashboard to view solar production, battery state,
and recent events; and to push config + manual overrides. Public
remote access is a tempting feature but adds significant attack
surface (any control-plane mistake becomes internet-exposed) and
compliance considerations (CCPA disclosure for usage telemetry).

## DECISION

Dashboard runs as a browser-side SPA served by the controller host
over the owner's local LAN. No public-internet exposure by default.
Owner-led reverse-proxy setup is documented for remote access as
an opt-in, but it is out of scope for the supported configuration.

## CONSEQUENCES

- Reduced attack surface: dashboard authentication can use a shared
  secret on LAN rather than full OAuth/OIDC.
- Owners who want remote access must run their own reverse proxy
  and assume responsibility for its security posture.
- Cloud Forward (the optional S-Miles bridge) is unaffected — it's
  a separate optional outbound path with its own threat model.

## ALTERNATIVES CONSIDERED

- Public cloud-hosted dashboard with per-user OAuth — rejected for now (compliance + scope).
- VPN-only access — rejected: too high friction for typical owners.

## AFFECTS

- **Modules:** `am_dashboard_app`, `am_controller_host`
- **Interconnects:** `ai_local_lan`

---

*Format: Michael Nygard 2011 — Context / Decision / Consequences / Alternatives. See [`../toolkit/MODERNIZATION_DESIGN.md`](../toolkit/MODERNIZATION_DESIGN.md).*
