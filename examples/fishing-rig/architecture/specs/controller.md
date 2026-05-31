# AMS — Main Controller Board (AM 1)

**Module:** [`am_controller`](../../dictionary.yaml)
*Generated from `dictionary.yaml`. Do not hand-edit.*

## DESCRIPTION

ESP32-WROOM-32 module on a custom PCB. Onboard: 16-bit ADC for the
tension load cell, H-bridge motor driver for the reel, BLE
antenna, optional WiFi for cloud. Firmware is FreeRTOS + the HP
toolkit-derived CSPEC/PSPEC implementations.

## CROSS-REFERENCE (allocation)

| Requirements component | Kind |
|---|---|
| `proc_acquire_tension` | process |
| `proc_reel_controller` | process |
| `proc_cloud_forward` | process |
| `proc_bite_detector` | process (state-rich; CSPEC lives here) |
| `store_system_state` | data store |

## DESIGN RATIONALE

Chose ESP32 over a Cortex-M0+ for BLE + WiFi in a single package,
simplifying both BoM and firmware. Onboard ADC avoids an external
I2C ADC.

## DESIGN JUSTIFICATION

MIPS budget: 200 Hz tension sampling + 20 Hz BLE notify + motor
PWM is < 5% of ESP32 capacity at 80 MHz. RAM: state machine +
recent-history buffer < 16 KB.

## REQUIRED CONSTRAINTS

- **Reliability:** MTBF > 5000 hours of field operation.
- **Safety:** Motor cutoff on stall current (>2× nominal) within 50 ms.
- **Physical:** Fits in a 100×60×25 mm splashproof enclosure.
- **Cost:** BOM ≤ $45 in 100-unit lots.

## INTERFACES

Inputs:  F3 TENSION (analog, 0–3.3V from load-cell amplifier);
         reel encoder feedback (quadrature, GPIO).
Outputs: F4 REEL TORQUE CMD (PWM H-bridge);
         BLE GATT notifications (telemetry, alerts).
         WiFi/HTTPS (optional cloud forwarding).

---

*Format: 2000 §4.2.5.4 — typical AMS contents. See [`../../ARCH_DESIGN.md`](../../ARCH_DESIGN.md).*
