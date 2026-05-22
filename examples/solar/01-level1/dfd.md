# Solar Local Stack — Level-1 DFD (Mermaid)

First decomposition of `sys_root` into 5 + 1 (optional) internal processes plus the `System State` data store. Locked 2026-05-22. Names from [`../dictionary.yaml`](../dictionary.yaml).

## Diagram

```mermaid
graph LR
    %% External terminators
    HM[Solar Inverters]
    CM[Net Power Meter]
    VX[Battery System]
    GRID[Utility Grid]
    USR[Owner]
    SMC([S-Miles Cloud<br/><i>optional</i>])

    %% Internal processes
    P1((Acquire<br/>Telemetry))
    P2((Energy<br/>Manager))
    P3((Dispatch<br/>Commands))
    P4((Serve UI))
    P5((Handle<br/>Input))
    P6((Cloud Forward<br/><i>optional</i>))

    %% Data store
    DS[(System State)]

    %% Boundary flows F1-F8
    HM     -- "F1: telemetry"          --> P1
    P3     -- "F2: power-limit"        --> HM
    CM     -- "F3: net grid power"     --> P1
    VX     -- "F4: SoC, mode"          --> P1
    P3     -- "F5: charge / setpoint"  --> VX
    USR    -- "F6: config, override"   --> P5
    P4     -- "F7: dashboards"         --> USR
    P6     -. "F8: telemetry fwd"     .-> SMC

    %% Physical AC power
    GRID --- HM
    GRID --- VX

    %% Internal flows (event-driven per Decision 3)
    P1 -- "writes" --> DS
    DS -- "reads"  --> P2
    DS -- "reads"  --> P4
    DS -. "reads" .-> P6
    P2 -- "cmd_setpoint"        --> P3
    P2 -- "cmd_inverter_limit"  --> P3
    P2 -- "event_alert"         --> P4
    P5 -- "event_override"      --> P2
    P5 -. "event_config"       .-> P1

    %% Styling
    classDef proc        fill:#cfe5ff,stroke:#2a70c2,color:#000;
    classDef brain       fill:#7fbff5,stroke:#1f5a99,color:#000,font-weight:bold;
    classDef optional    fill:#e6f0ff,stroke:#888,stroke-dasharray:3 3;
    classDef terminator  fill:#fafafa,stroke:#444;
    classDef store       fill:#fff5cc,stroke:#b89800;
    classDef grid        fill:#fef0ef,stroke:#e74c3c;
    classDef termopt     fill:#fafafa,stroke:#888,stroke-dasharray:5 5,color:#666;
    class P1,P3,P4,P5 proc;
    class P2 brain;
    class P6 optional;
    class DS store;
    class HM,CM,VX,USR terminator;
    class GRID grid;
    class SMC termopt;
```

## Balancing check

Every level-0 boundary flow appears at the level-1 boundary as well (HP balancing rule):

| Level-0 flow | Level-1 source/target |
|---|---|
| F1 (in)  | Solar Inverters → Acquire Telemetry |
| F2 (out) | Dispatch Commands → Solar Inverters |
| F3 (in)  | Net Power Meter → Acquire Telemetry |
| F4 (in)  | Battery System → Acquire Telemetry |
| F5 (out) | Dispatch Commands → Battery System |
| F6 (in)  | Owner → Handle Input |
| F7 (out) | Serve UI → Owner |
| F8 (out) | Cloud Forward → S-Miles Cloud *(optional)* |

✅ All 8 boundary flows preserved; no flows appear or disappear at the boundary.

## Internal flows summary

Per Decision 3 (event-driven) and Decision 4 (explicit data store):

| From | To | Carries | Kind |
|---|---|---|---|
| Acquire Telemetry | System State | normalized state | data (write) |
| System State | Energy Manager | system_state | data (read) |
| System State | Serve UI | system_state | data (read) |
| System State | Cloud Forward | system_state | data (read, optional) |
| Energy Manager | Dispatch Commands | cmd_setpoint | control |
| Energy Manager | Dispatch Commands | cmd_inverter_limit | control |
| Energy Manager | Serve UI | event_alert | control |
| Handle Input | Energy Manager | event_override | control |
| Handle Input | Acquire Telemetry | event_config | control (subtle) |

## Next: Stage 3

The **Energy Manager** bubble is state-rich — diversion loop, night-discharge, outage handling all live in its CSPEC. Stage 3 formalizes that as a state-transition diagram.
