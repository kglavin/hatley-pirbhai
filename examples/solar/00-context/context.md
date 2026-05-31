# Solar Local Stack — Context Diagram v0 (Mermaid)

Status: draft for review. Six uncertainty items pending Kevin's call (see PLAN.md > Open Questions).

## Diagram

```mermaid
graph LR
    HM[Solar Inverters]
    CM[Net Power Meter]
    VX[Battery System]
    GRID[Utility Grid]
    USR[Owner]
    SMC([S-Miles Cloud<br/><i>optional</i>])

    SYS(("Solar Local Stack"))

    HM     -- "F1: per-channel telemetry"   --> SYS
    SYS    -- "F2: power-limit setpoints"   --> HM
    CM     -- "F3: net grid power, V/I/PF"  --> SYS
    VX     -- "F4: SoC, mode, AC-in"        --> SYS
    SYS    -- "F5: max-charge, grid setpoint" --> VX
    USR    -- "F6: config, override"        --> SYS
    SYS    -- "F7: dashboards, alerts"      --> USR
    SYS    -. "F8: optional telemetry forward" .-> SMC

    GRID --- HM
    GRID --- VX

    classDef system fill:#4a90e2,stroke:#2a70c2,color:#fff,font-weight:bold;
    classDef terminator fill:#fafafa,stroke:#444;
    classDef optional fill:#fafafa,stroke:#888,stroke-dasharray:5 5,color:#666;
    classDef grid fill:#fef0ef,stroke:#e74c3c;
    class SYS system;
    class HM,CM,VX,USR terminator;
    class SMC optional;
    class GRID grid;
```

## Flow specification (the formal artifact)

| ID | Source | Target | Name | Kind | Medium | Notes |
|----|--------|--------|------|------|--------|-------|
| F1 | Solar Inverters | System | per-channel power / V / I / temp / fault state | data | Sub-1G RF → DTU-Pro-S *or* OpenDTU | ~30 s native; near-realtime via OpenDTU |
| F2 | System | Solar Inverters | per-channel power-limit setpoint | control | OpenDTU only | **Conditional on DTU architectural choice** |
| F3 | Net Power Meter | System | net grid power, per-phase V/I/PF, direction | data | RS485 Modbus RTU | *primary* sensing input for diversion loop |
| F4 | Battery System | System | battery SoC, charging state, AC-in power, system mode | data | MQTT / Modbus TCP | inbound side of bidirectional channel |
| F5 | System | Battery System | max-charge current, grid setpoint, ESS params | control | MQTT publish | *primary* actuating output for diversion loop |
| F6 | Owner | System | config, manual override, enable/disable | data + control | UI | mostly config; some are control events |
| F7 | System | Owner | dashboard views, alerts, status | data | UI | reverse of F6 |
| F8 | System | S-Miles Cloud | optional telemetry forward | data | HTTPS | off by default |

## Open uncertainties (resolve next)

1. DTU choice — official DTU-Pro-S only, OpenDTU/AhoyDTU only, or both as variants? Affects F2.
2. PG&E Utility Meter as a distinct terminator from PG&E Grid, or rolled together?
3. EV charger / future loads — model now as placeholder, or defer?
4. Weather forecast service — in or out for the b+d cut?
5. S-Miles Cloud (F8) — keep dashed/optional, or drop entirely?
6. Outage handling — does the system *observe*, *participate*, or *stay out of the way*?
