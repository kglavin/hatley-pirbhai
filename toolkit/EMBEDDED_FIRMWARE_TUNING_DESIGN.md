# Embedded Firmware Tuning Design

## ✅ Status: Locked 2026-05-25

All four open questions resolved:
- **Q1** Branch shape → Single Branch 4 (T15–T18); all findings A–H land together
- **Q2** RTOS / vendor coverage → **Wide**: FreeRTOS / NuttX / Zephyr / ChibiOS / Mbed / ESP-IDF / Arduino / AUTOSAR + STM32 HAL + STM32CubeMX + PX4 uORB + MAVLink + Micro-ROS + ROS 2
- **Q3** CMakeLists parsing → Regex extraction of common forms (`add_executable`, `px4_add_module`, `target_link_libraries`); no new dep
- **Q4** Embedded boundary confidence → Tiered by detection kind (`hw_peripheral_*` 0.9 / `mavlink_*` 0.8 / `dds_*` 0.7 / `ros_*` + `uorb_*` 0.6)

---

## Goal

Make `hp-ingest` produce useful output on **embedded firmware targets** — STM32 HAL projects, NuttX-based autopilots, Zephyr / Mbed / ESP-IDF / FreeRTOS projects, ROS 2 / Micro-ROS firmware. Today the pipeline is tuned for cloud workloads (containers, k8s, HTTP / gRPC / DDS-over-network); on firmware it produces near-empty Stage 1 + degenerate Stage 5.

The fix is **additive**: per-domain detectors that recognize firmware-shaped signals + a few targeted prompt updates so the existing LLM agents handle a hardware-flavored architecture. The cloud-side detectors stay unchanged; embedded targets just get a new arm of patterns.

## Spawning context — dogfood against two real targets

Two embedded targets dogfooded 2026-05-25:

| Target | Files | Significant | Boundary candidates | Process candidates | Arch candidates | State-machine extraction |
|---|---|---|---|---|---|---|
| **leocore_firmware_ros2** (STM32 + Micro-ROS, ~150 files) | 153 | 51 | **0** | 6 (5 vendor-dirs) | **0** | 22 transitions / **0 states** in `App/Src/app.cpp` |
| **PX4-Autopilot** (NuttX + uORB, ~14k files) | 13916 | 785 | 52 (**all host-side CLI scripts**, not firmware) | 237 (over-fragmented) | 1 (dev-setup Dockerfile) | 129 detected / **0 states / 0 transitions** |

Both runs completed in seconds; cost zero LLM tokens. The signal is consistent: the deterministic pre-LLM phases miss firmware-shaped patterns across the board. Without that signal, the LLM stages have nothing to work with.

This doc captures the findings + proposes a Branch-4 implementation arc.

## Why a separate design doc

The prior tuning arcs ([INGEST_TUNING_DESIGN.md](INGEST_TUNING_DESIGN.md) Branches 1+2, [HIERARCHICAL_INGEST_DESIGN.md](HIERARCHICAL_INGEST_DESIGN.md) Branch 3) tuned the *behavior* of the existing cloud-shaped pipeline. Embedded support is different: it requires recognizing a **different vocabulary of architectural signals** — hardware peripherals, RTOS tasks, pub/sub middleware (uORB, ROS 2, DDS), board configs, linker scripts, RTOS-aware init patterns. Each of these is its own detector class.

Keeping the work in its own design doc + branch:
- Doesn't churn the cloud detectors that landed in Branches 1+2.
- Makes the embedded scope reviewable as one unit.
- Sets the precedent for per-domain tuning arcs (a future "scientific simulation" or "data pipeline" target might warrant its own arc).

---

## Findings

Eight findings, lettered for consistency with the prior tuning docs. Severity = how much architectural signal is lost; priority = whether to fix in this branch or defer.

### A. Framework detector misses embedded RTOS + comm middleware

**Evidence:**
- leocore: `frameworks: (none detected)`. Project uses STM32 HAL + Micro-ROS heavily.
- PX4: `frameworks: Docker`. Project uses NuttX + uORB + MAVLink + ROS 2 (`rclcpp` bindings).

**Root cause:** [`role_classifier.py`](hp_toolkit/ingest/role_classifier.py)'s `_FRAMEWORK_MARKERS` is a curated list of web/cloud frameworks (Axum, Flask, React, PostgreSQL, etc.). No embedded entries.

**Proposed fix (per locked Q2 — wide coverage):** Extend `_FRAMEWORK_MARKERS` with:
- **RTOSes:** `FreeRTOS` (`xTaskCreate`, `osThreadDef`, `vTaskDelay`), `NuttX` (`apps/`, `nuttx/`, `up_*` syms), `Zephyr` (`k_thread_create`, `CONFIG_*` in Kconfig), `ChibiOS` (`chThdCreate`, `evtRegister`), `Mbed` (`mbed.h`, `Thread`/`EventQueue`), `ESP-IDF` (`esp_*` family + `idf.py` + `app_main`)
- **STM32 ecosystem:** `STM32 HAL` (`HAL_*_Init`, `stm32f4xx_hal.h`), `STM32CubeMX` (`.ioc` file), `LL drivers` (`stm32f4xx_ll_*.h`)
- **Arduino:** `setup()` + `loop()` in `.ino`; `Arduino.h` include
- **AUTOSAR:** `Rte_*` API, `BswM_*`, `Os_*`, `Com_*`, `MemMap.h` patterns
- **ROS family:** `ROS 2 rclcpp` (`rclcpp::create_publisher`), `Micro-ROS` (`rclc_*`, `rmw_microros_*`), `MAVLink` (`mavlink_msg_*`), `uORB` (`orb_advertise`, `ORB_ID(...)`)
- **DDS:** `Fast-DDS`, `Cyclone DDS` (`dds_create_writer`), `Connext DDS`

**Cost:** small — ~35 new regex patterns. **Priority: high** (framework detection feeds every downstream agent's context).

### B. Boundary detector misses hardware peripherals + pub/sub middleware

**Evidence:**
- leocore: **0 boundary candidates** despite the firmware clearly having boundaries (motor PWM out, IMU I2C in, encoder GPIO interrupts, UART for Micro-ROS).
- PX4: 52 boundary candidates, **all host-side CLI scripts in `Tools/`** (`Tools/boot_now.py`, `Tools/ci/check_pr_title.py`, etc.). Zero firmware boundaries surfaced. The actual PX4 boundaries are uORB topics, MAVLink frames, hardware peripherals (PWM, GPIO, I2C, SPI, CAN), shell commands (NSH).

**Root cause:** [`boundary_candidates.py`](hp_toolkit/ingest/boundary_candidates.py) detects HTTP listeners, gRPC servers, CLI entries, message-bus consumers. None of these apply to firmware.

**Proposed fix:** New embedded-boundary detectors:

1. **Hardware peripheral init:** `HAL_TIM_PWM_Start`, `HAL_GPIO_EXTI_*`, `HAL_UART_Init`, `HAL_I2C_Init`, `HAL_SPI_Init`, `HAL_CAN_*`, `HAL_ADC_*`, NuttX equivalents (`px4_arch_*`, board-specific drivers), Zephyr (`device_get_binding`, `gpio_pin_configure`)
2. **ROS / Micro-ROS topic surfaces:**
   - Publishers: `rclcpp::create_publisher`, `rcl_publisher_init`, `rclc_publisher_init_default`
   - Subscribers: `rclcpp::create_subscription`, `rcl_subscription_init`, `rclc_subscription_init_default`
   - Services / Actions
3. **uORB (PX4-specific):**
   - `orb_advertise(ORB_ID(<topic>), ...)`, `orb_subscribe(ORB_ID(...))`, `ORB_DECLARE` macros
4. **MAVLink endpoints:**
   - `mavlink_msg_*_pack`, `mavlink_msg_*_decode`, mavlink-router instances
5. **DDS endpoints:** `dds_create_writer`, `dds_create_reader`, `dds_create_topic`

Each match produces a `BoundaryCandidate` with a new `kind_hint` value (`hw_peripheral_pwm`, `ros_publisher`, `uorb_publisher`, etc.). The Stage 1 LLM gets these alongside the existing HTTP/gRPC/CLI hints; the prompt is taught to interpret them.

**Cost:** moderate — new module `hp_toolkit/ingest/embedded_boundary_detector.py` (or expand `boundary_candidates.py`). **Priority: high** (without boundaries, Stage 1 produces nothing meaningful).

### C. Architecture candidate detector misses embedded deployment artifacts

**Evidence:**
- leocore: **0 architecture candidates**. The project's deployment artifacts are CMakeLists.txt + the STM32CubeMX `.ioc` + the linker scripts.
- PX4: 1 architecture candidate — `Tools/setup/Dockerfile`. That's the *developer-environment* container, not the firmware deployment. Real PX4 deployment artifacts are the per-board configs under `boards/<vendor>/<board>/` (50+ boards), CMake target definitions, NuttX `defconfig` files.

**Root cause:** [`architecture_candidates.py`](hp_toolkit/ingest/architecture_candidates.py) recognizes Dockerfile / compose / k8s / package.json / Cargo.toml / pyproject.toml / go.mod / `.tf`. Nothing for embedded.

**Proposed fix:** New embedded-specific candidate extractors dispatched in `architecture_candidates._process_file`:

1. **CMakeLists.txt** — when it contains `add_executable(<target> ...)` or PX4-style `px4_add_module(...)`, surface each target as a `ModuleCandidate` with `kind_hint=firmware_target`. Extract from `target_link_libraries` for dependency edges.
2. **STM32CubeMX `.ioc`** — declares the MCU + pinout + peripheral config. Parse as YAML-ish (it's a key=value format). Each enabled peripheral becomes evidence on a candidate `module_kind: hardware` (the MCU itself).
3. **Linker scripts (`*.ld`)** — describe memory map (flash + RAM regions, sections). Treat as deployment-config evidence.
4. **PX4 board configs (`boards/<vendor>/<board>/<board>.px4board`)** — PX4-specific YAML-ish file. Each board is a deployment configuration; modules can be selected per-board.
5. **NuttX `defconfig`** — board feature selection. Same role as PX4 board configs.
6. **Zephyr / PlatformIO config:** `platformio.ini`, west manifest (`west.yml`), `prj.conf`, `app.overlay`.
7. **Arduino sketches (`.ino`):** one sketch = one firmware module candidate.

Each emits a `ModuleCandidate` with `kind_hint` reflecting the artifact type (`firmware_target`, `mcu`, `embedded_board_config`, etc.). The Stage 5 architect learns to handle these (per finding H).

**Cost:** large — multiple new format parsers. Plausible to share infrastructure with the existing compose/k8s parsers from Branch 2 T8. **Priority: high** (without architecture candidates, Stage 5 produces nothing).

### D. State-machine detector misses C/C++ switch-case FSMs

**Evidence:**
- leocore: `App/Src/app.cpp` — detector reports **22 transitions, 0 states**. The file has a state-driven robot controller; the detector pulled the `case X: ... break;` patterns but missed the state enum.
- PX4: 129 state-machine candidates detected; **all show 0 states / 0 transitions**. The detector finds candidates but extracts nothing.

**Root cause:** [`state_machine_detector.py`](hp_toolkit/ingest/state_machine_detector.py) is tuned for Rust enums + TypeScript discriminated unions. Firmware FSMs use:
- C/C++ `enum State { ST_INIT, ST_RUN, ... };` followed by `switch (state) { case ST_INIT: ... }`
- Function-pointer state tables: `void (*state_funcs[])() = {init_fn, run_fn, ...};`
- State-variable updates: `state = ST_NEXT;` patterns
- Sometimes C++ class hierarchies with `virtual void enter()` / `exit()` methods

**Proposed fix:** Extend the detector with C/C++-shaped FSM patterns:
- Match `enum [class] <Name> { <STATE_LIST> };` to extract state names
- Match `switch (<var>) { case <STATE_NAME>: ... }` to extract transitions
- Match assignment `<state_var> = <NEW_STATE>;` inside a case body as the transition target
- For function-pointer tables: match `<rettype> (*<name>[])(...) = {...};` + extract the function names

**Cost:** moderate — extend the existing detector's pattern set. **Priority: medium-high** (already finding the candidates; just need extraction).

### E. Role classifier misses embedded-specific file roles

**Evidence:** Vendor directories like `Drivers/CMSIS-Include/` (25 files) get classified `pure-logic` and surface as process candidates; they're vendor scaffolding, not architecture. HAL init files get classified `pure-logic` instead of `infra`. FreeRTOS task creation patterns don't bubble up.

**Root cause:** [`role_classifier.py`](hp_toolkit/ingest/role_classifier.py) patterns don't recognize embedded signals.

**Proposed fix:**
- `HAL_*_Init` / `MX_*_Init` (CubeMX-generated init) → `infra`
- `osThreadDef` / `xTaskCreate` / `k_thread_create` → `process` (RTOS task is the firmware "process")
- `rcl_*_init` / `rclc_*_init` / `orb_advertise` / `mavlink_msg_*_pack` → `boundary`
- Vendor directories: extend `_ALWAYS_SKIP_PATH_PATTERNS` with `(^|/)(CMSIS|cmsis|st-link|stm32cubemx-generated)/`, `(^|/)(boards/.+/cube|boards/.+/cubemx)/`, NuttX vendor dirs

**Cost:** small — pattern additions. **Priority: high** (process clustering quality depends on role hints).

### F. Process clustering doesn't fit "architecture-in-one-file" firmware

**Evidence:**
- leocore: `App/Src/app.cpp` (single file, 22 state-machine transitions, IS the architecture) becomes ONE candidate `App-Src` with 1 file. Meanwhile `Drivers-CMSIS-Include` becomes a 25-file candidate — vendor noise.
- PX4: 237 process candidates at `--max-depth 3`. Way too many. The actual PX4 architecture is ~25 high-level modules (commander, navigator, mc_pos_control, mc_att_control, sensors, mavlink, uorb, ...).

**Root cause:** [`process_candidates.py`](hp_toolkit/ingest/process_candidates.py) clusters by directory. Firmware projects often have:
- A "monolithic" single-file architecture (small projects)
- A modules/ tree where each subdirectory IS a process (PX4) — but at varying depths
- Vendor directories that shouldn't cluster as processes

**Proposed fix:**
- **Per-RTOS-task clustering:** when role-hint = `process` (an RTOS task declaration), use the *task name* as the cluster, not the directory.
- **File-as-process when the file has many transitions:** if a single file has ≥10 state-machine transitions OR ≥3 RTOS tasks OR ≥5 hardware-boundary inits, treat it as its own process candidate.
- **PX4-style module recognition:** when a `CMakeLists.txt` at any depth contains `px4_add_module(MODULE <name>)`, declare the directory as a process candidate with cluster name `<name>`.
- **Increase vendor-skip aggressiveness:** any directory matched in finding E's path patterns is suppressed from clustering.

**Cost:** moderate — add the new clustering rules; existing directory-based heuristic stays as fallback. **Priority: medium** (the Stage-2 LLM can over-cluster as a partial mitigation).

### G. Testbed detector false-positives on doc trees

**Evidence:**
- PX4: `docs/` flagged as a testbed with score=3. Reason: 33 markdown files matching scenario-shaped filenames (`integration-*.md`, `system-test.md`, etc.); only 2 .py files. The "scenarios dominate the .py pool" rule fires because 33/2 = 1650%.

**Root cause:** [`testbed_miner.py`](hp_toolkit/ingest/testbed_miner.py)'s `_SCENARIO_FILENAME` pattern matches against all file paths, but the ratio gate is .py-only. A docs/ directory full of `integration-guide.md` files looks like a testbed.

**Proposed fix:** The "scenarios dominate" rule should require scenario-shaped files to be **executable** (`.py`, `.cpp`, `.cc`, `.rs`, `.go` — anything that can run). Markdown / RST / Adoc scenario-shaped files signal documentation, not a testbed.

**Cost:** trivial — one-line filter. **Priority: low** (the LLM agents would notice and ignore; but the cleaner the prep, the less the LLM has to filter).

### H. Architect skill needs embedded-mode tutorial

**Evidence:** Even when findings A–F land, the Stage 5 LLM (per `hp-ingest-architect.md`) doesn't know how to model an embedded system. Its current discipline assumes deployments are containers / k8s pods / packages. For embedded:
- The "module" is the MCU (one hardware module per board), possibly with the firmware as a `software` sub-module hosted on the hardware module.
- "Interconnects" are physical buses: I2C, SPI, CAN, UART, USB. Not Cluster RPC / Internet ingress.
- "Allocations" map RTOS tasks to the MCU module.
- Multi-MCU systems (sensor MCU + main MCU): each MCU is its own hardware module; the comm bus between them is an interconnect.

**Proposed fix:** Update `hp-ingest-architect.md` discipline with an "Embedded mode" section:
- Recognize `kind_hint: firmware_target` / `mcu` / `embedded_board_config` candidates.
- Treat the MCU as `module_kind: hardware`; firmware-as-software optional sub-module per HP §4.2.2.1.
- Interconnect kind hints: `uart_bus`, `i2c_bus`, `spi_bus`, `can_bus`, `usb_bus`, `gpio_lines`.
- Allocation discipline for RTOS tasks: each task → the MCU module's `allocated_processes`.
- Multi-MCU systems: each MCU = one module, comm buses between them = interconnects.

**Cost:** moderate — substantial skill-markdown update; no code changes. **Priority: high** (no point producing embedded boundary/architecture candidates if the LLM doesn't know how to use them).

---

## What we ship

```
toolkit/hp_toolkit/ingest/
├── embedded_boundary_detector.py   ← new (B)
├── embedded_arch_extractor.py       ← new (C); houses CMakeLists / .ioc / .ld / .px4board parsers
├── role_classifier.py               ← extended (A + E)
├── state_machine_detector.py        ← extended (D)
├── process_candidates.py            ← extended (F)
└── testbed_miner.py                 ← patched (G)

toolkit/skills/
└── hp-ingest-architect.md           ← embedded-mode section (H)
```

## Implementation order

Sketched as Branch 4 / `kg/hp-ingest-embedded-firmware`. Four commits, verifiable in isolation.

- **T15** — Cheap pattern additions (A + E + G + D pattern half). Re-run prep on leocore + PX4 → classifier output improves; testbed false positive cleared; state-machine extraction starts producing state lists.
- **T16** — Embedded boundary detector (B). New `embedded_boundary_detector.py`; integrated into the orchestrator. Re-run: leocore + PX4 produce non-zero firmware-shaped boundary candidates.
- **T17** — Embedded arch extractor (C). New `embedded_arch_extractor.py` with CMakeLists + .ioc + .ld + .px4board parsers. Re-run: PX4 produces ~25 firmware-target architecture candidates (one per `px4_add_module`); leocore produces 1 (the MCU).
- **T18** — Process clustering (F) + architect skill (H) + doc catch-up. Re-run with LLM agents → produces a real Stage-5 architecture for both targets.

After T18 lands: dispatch the full LLM pipeline against leocore + PX4 and capture the dictionary.yaml outputs as a second-tier validation (similar to how cloudctlplane was the canonical test for Branches 1+2).

---

## Open questions

### Q1. Branch shape ✅ Single Branch 4

All A–H land together in T15–T18.

### Q2. Coverage breadth ✅ Wide

FreeRTOS / NuttX / Zephyr / ChibiOS / Mbed / ESP-IDF / Arduino / AUTOSAR + STM32 + PX4 + Micro-ROS + ROS 2. The patterns are cheap individually (one regex each); covering all the obvious next-targets at landing time is worth the small extra work.

### Q3. CMakeLists parsing ✅ Regex extraction

Match `add_executable(<name>`, `px4_add_module(MODULE <name>`, `target_link_libraries`, etc. No new dep. Re-evaluate if a target proves it matters.

### Q4. Embedded boundary confidence ✅ Tiered by detection kind

`hw_peripheral_*` → 0.9 / `mavlink_*` → 0.8 / `dds_*` → 0.7 / `ros_*` + `uorb_*` → 0.6.

---

**Status:** ✅ shipped 2026-05-25. T15–T18 landed; all findings A–H closed.

**Branch:** `kg/hp-ingest-embedded-firmware`.

**Spawning context:** dogfood runs against `leocore_firmware_ros2` + `PX4-Autopilot` on 2026-05-25. Both produced near-empty Stage 1 + Stage 5 with the current pipeline. Eight findings (A–H) captured here as the implementation basis.

**Verified deltas after T18 (deterministic prep only; no LLM):**

| metric | leocore pre | leocore post | PX4 pre | PX4 post |
|---|---:|---:|---:|---:|
| frameworks detected | 0 | 4 | 1 | 5 |
| boundary candidates | 0 | 6 | 52 (host CLI) | 893 |
| with topic surface | 0 | 1 (7 topics) | 0 | 42 |
| process clusters | 6 (5 vendor noise) | 2 | 237 | 481 (109 PX4-shaped + 177 FSM file-as-cluster) |
| state-machine extracted | 0 / 22 (wrong) | 4 states / 3 txs | 0 / 0 | 67 with states / 149 with txs |
| architecture candidates | 0 | 2 (MCU + memory map) | 1 (dev dockerfile) | 516 (330 px4_modules + 178 memory layouts + 7 firmware targets) |
| px4_module_depends_on edges | n/a | 0 | n/a | 248 |
| .px4board deployment configs | n/a | 0 | 0 | 264 |
| false-positive testbeds | n/a | 0 | 1 (docs/) | 0 |
