# ADR — BLE chosen for controller ↔ app transport

**ID:** `adr_001_ble_transport`
**Status:** Accepted
**Date:** 2026-05-22
**Author:** controller team

*Generated from `dictionary.yaml`. Do not hand-edit.*

## CONTEXT

The controller needs a wireless link to the angler's mobile device
that satisfies three constraints simultaneously: low controller-side
power draw (battery-powered enclosure), simple no-account pairing
(no cloud login required), and adequate range from a vest pocket.
WiFi Direct, classic Bluetooth, and a custom 433 MHz radio were
candidates.

## DECISION

Use Bluetooth Low Energy 5.0 with a custom GATT service. BLE LE
Secure Connections (P-256 ECDH) handles pairing + encryption;
paired-device authentication is sufficient for the threat model
(single-user session, no audit requirement).

## CONSEQUENCES

- Controller-side power budget is met (~10 µA average BLE current).
- Angler app must support BLE on iOS 15+ / Android 11+.
- Range is range-limited to ~30 m line-of-sight, ~10 m through
  clothing. Acceptable for the angling use case.
- Future expansion to remote-monitoring (cloud forwarding) is
  independent: the cloud_forward bubble uses WiFi/HTTPS, not BLE.

## ALTERNATIVES CONSIDERED

- WiFi Direct — rejected: power budget on controller side.
- Classic Bluetooth — rejected: pairing UX worse than BLE; higher power.
- Custom 433 MHz LoRa-style radio — rejected: regulatory complexity, certification cost.

## AFFECTS

- **Modules:** `am_controller`, `am_angler_app`
- **Interconnects:** `ai_ble`
- **Flows:** `af_telemetry_to_app`, `af_config_to_ctrl`

## CATALOG REFERENCES

**MITRE ATT&CK:** [`T1078`](https://attack.mitre.org/techniques/T1078/), [`T1565`](https://attack.mitre.org/techniques/T1565/)

**CWE:** [`CWE-319`](https://cwe.mitre.org/data/definitions/319.html), [`CWE-294`](https://cwe.mitre.org/data/definitions/294.html)

---

*Format: Michael Nygard 2011 — Context / Decision / Consequences / Alternatives. See [`../toolkit/MODERNIZATION_DESIGN.md`](../toolkit/MODERNIZATION_DESIGN.md).*
