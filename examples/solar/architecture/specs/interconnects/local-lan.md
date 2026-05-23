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

---

*Format: 2000 §4.2.6.2 — typical AIS contents. See [`../../../ARCH_DESIGN.md`](../../../ARCH_DESIGN.md).*
