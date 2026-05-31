# AIS — Local LAN

**Interconnect:** [`ai_local_lan`](../../../dictionary.yaml)
**Endpoints:** `am_controller_host`, `am_dashboard_app`
*Generated from `dictionary.yaml`. Do not hand-edit.*

## DESCRIPTION

The owner's local network connecting the dashboard browser to
the controller host. WebSocket carries push notifications
(state updates, alerts); HTTP serves the SPA and accepts config
POSTs.

## CARRIES

Architecture flows allocated to this channel:

- `af_state_to_dashboard` — state + alerts (data)
- `af_input_to_controller` — config + override (data)

## PROTOCOL STANDARD

HTTP/1.1 (RFC 7230) for static asset serving and config POSTs;
WebSocket (RFC 6455) for push notifications. JSON message
format documented in the controller's protocol spec.

## DESIGN RATIONALE

LAN-only by default — no public Internet exposure. Owner can
reverse-proxy externally if remote access is wanted, but that
is out-of-scope here.

## REQUIRED CONSTRAINTS

- **Reliability:** Survives router reboots without manual reconnect on the dashboard side.

## THREAT MODEL (STRIDE)

Per Microsoft SDL (Howard & Lipner 2006). Each row is the narrative describing how the threat category is addressed.

| Category | Mitigation |
|---|---|
| **S**poofing | Shared-secret authentication (rotating per-owner bearer token, served by the controller's first-login bootstrap) prevents unauthorized browsers from connecting. The LAN itself is the outer ring of defense — assumes the owner has reasonable Wi-Fi hygiene.  |
| **T**ampering | TLS (HTTPS + WSS) protects in-flight messages against tampering. Controller signs config-change responses with the session token so the browser can detect mid-session injection.  |
| **R**epudiation | out_of_scope — single owner; no audit requirement at this tier. ADR-002 explicitly defers any audit trail to a future cloud forwarding option.  |
| **I**nfo disclosure | TLS encryption protects state + telemetry in transit. Dashboard does not store usage data persistently in the browser beyond the session token.  |
| **D**enial of service | Rate-limit config-POST endpoints (10 req/min per session). WebSocket connection cap of 4 per session. Controller's diversion-control loop is decoupled from dashboard liveness — loss of LAN does not affect energy management.  |
| **E**lev. of privilege | Dashboard session token grants only configured-scope permissions (config + view; no firmware update, no factory reset). Reset and firmware update require a separate physical-button flow on the controller host.  |

---

*Format: 2000 §4.2.6.2 — typical AIS contents. See [`../../../ARCH_DESIGN.md`](../../../ARCH_DESIGN.md).*
