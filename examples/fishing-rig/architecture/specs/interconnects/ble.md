# AIS — BLE Link

**Interconnect:** [`ai_ble`](../../../dictionary.yaml)
**Endpoints:** `am_controller`, `am_angler_app`
*Generated from `dictionary.yaml`. Do not hand-edit.*

## DESCRIPTION

BLE 5.0 GATT service connecting the controller to the angler app.
The controller acts as peripheral; the app acts as central. One
custom service exposes a telemetry notify characteristic and a
config write characteristic.

## CARRIES

Architecture flows allocated to this channel:

- `af_telemetry_to_app` — telemetry (data)
- `af_config_to_ctrl` — angler config + override (data)

## PROTOCOL STANDARD

Bluetooth Core Specification 5.0. Custom GATT service UUID
assigned per project; characteristic UUIDs documented in the
app's protocol spec.

## DESIGN RATIONALE

BLE chosen over classic Bluetooth or WiFi for low power on the
controller side and simple pairing for the angler.

## REQUIRED CONSTRAINTS

- **Physical:** Range ≥ 30 m line-of-sight; ≥ 10 m through a vest pocket.

---

*Format: 2000 §4.2.6.2 — typical AIS contents. See [`../../../ARCH_DESIGN.md`](../../../ARCH_DESIGN.md).*
