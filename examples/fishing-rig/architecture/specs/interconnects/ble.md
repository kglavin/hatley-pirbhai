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

## THREAT MODEL (STRIDE)

Per Microsoft SDL (Howard & Lipner 2006). Each row is the narrative describing how the threat category is addressed.

| Category | Mitigation |
|---|---|
| **S**poofing | Paired-device pairing (BLE LE Secure Connections, P-256 ECDH) prevents unauthorized peripherals from impersonating the controller. The first pairing is in-person (proximity-based); subsequent reconnections use the bonded long-term key.  |
| **T**ampering | BLE 5.0 LE Secure Connections provides AES-CCM authenticated encryption on every link-layer packet. In-flight tampering would invalidate the MIC and drop the packet.  |
| **R**epudiation | out_of_scope — single-user session; no third-party audit requirement.  |
| **I**nfo disclosure | AES-CCM encryption per BLE 5.0. Telemetry contains fishing-session data only (no PII beyond the angler's pairing key, which is a random bond).  |
| **D**enial of service | Rate-limit pairing attempts to mitigate pairing-storm DoS. Reconnect backoff (exponential, capped) prevents reconnect-flood. The motor + sensor remain locally authoritative if BLE drops — degraded mode but no safety impact.  |
| **E**lev. of privilege | Custom GATT service exposes only telemetry-notify and config-write characteristics. No firmware-update path over BLE (firmware updates require physical USB connection — explicit design choice).  |

---

*Format: 2000 §4.2.6.2 — typical AIS contents. See [`../../../ARCH_DESIGN.md`](../../../ARCH_DESIGN.md).*
