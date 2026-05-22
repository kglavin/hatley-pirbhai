# Naming Review — Level 0 / Context Diagram v0

*Per-level review: this file covers level-0 (Context) entities only. Future levels (level-1 DFD internal bubbles, level-2 child DFDs, etc.) will each get their own naming review file in their level's directory.*

**How to use this file** *(review-as-file workflow):*

1. Open in VSCode. Edit inline — fill in each `Decision:` line, strike-through with `~~text~~` what you don't want, leave the line as-is to accept the current label, or use `Decision: keep` explicitly.
2. Free-form thoughts go on the `Other notes:` line. Anything is welcome — alternate naming schemes, "this should be split into two terminators," etc.
3. **Bulk shortcuts** are at the top — use these to avoid editing every entity individually.
4. Save the file. Ping me ("naming review done" or similar). I'll read it back, apply renames to `context.md` / `context.html` / `context.d2`, re-render the SVGs, and we move on.

This file itself is a **traceable artifact** of the renaming decisions — useful later when you want to remember why we named something the way we did. It can stay in `examples/solar/` (with git history) or be deleted after processing; your call.

---

## ✅ Status: Resolved 2026-05-22

All decisions captured and applied to `context.md`, `context.html`, `context.d2`. SVGs re-rendered.

| Stable ID | Final label | Note |
|---|---|---|
| `sys_root` | **Solar Local Stack** | parenthetical scope dropped |
| `term_inverters` | **Solar Inverters** | (was: Hoymiles HMS-2000-4T-NA Array) |
| `term_meter` | **Net Power Meter** | (was: Chint DTSU666 Meter) |
| `term_battery_system` | **Battery System** | (was: Victron Cerbo GX + MultiPlus) |
| `term_grid` | **Utility Grid** | (was: PG&E Utility Grid) |
| `term_user` | **Owner** | (was: User / Homeowner) |
| `term_smiles_cloud` | **S-Miles Cloud** | unchanged — kept as exception to bulk vendor-strip; vendor name carries the meaning |
| `flow_f1` … `flow_f8` | unchanged | F-flow labels accepted as-is via bulk shortcut |
| `edge_grid_to_*` | unlabeled | AC power edges kept default |

Bulk shortcuts that applied:
- Strip model numbers from terminators: **yes**
- Strip vendor names from terminators: **yes** (except `term_smiles_cloud`)
- F-flow names fine as-is: **yes**
- Naming style: **terse**

This file is kept as a **traceable artifact** of the renaming decisions. The form fields below remain in their unfilled state for reference; the canonical decisions are in this Status block.

---

## Bulk shortcuts (apply to multiple entities)

Fill in any that apply; leave blank/unchanged otherwise. These are applied *before* per-entity decisions.

- **Strip model numbers from all terminator labels?** (e.g. drop "HMS-2000-4T-NA", "DTSU666"): `_<yes / no / select>_`
- **Strip vendor names from all terminator labels?** (e.g. drop "Hoymiles", "Chint", "Victron"): `_<yes / no / select>_`
- **Are all F-flow names (F1-F8) fine as-is?** (skip per-entity flow review): `_<yes / no / mostly with exceptions>_`
- **Naming style preference for labels:** `_<verbose / medium / terse, e.g. one or two words>_`
- **Other bulk preferences:** `_<free-form>_`

---

## System (1)

### `sys_root`

- **Current label:** Solar Local Stack (b+d scope)
- **Provenance:** Claude's invention + internal chat shorthand "(b+d scope)". The shorthand is opaque outside this conversation.
- **Suggestions:**
  - `Solar Local Stack`  *(recommended — drop the parenthetical)*
  - `Local Solar Orchestrator`
  - `Solar Control Plane`
  - `Local Solar`
- **Decision:** _<fill in, or "keep">_
- **Other notes:** _<free-form>_

---

## Terminators (6)

### `term_inverters`

- **Current label:** Hoymiles HMS-2000-4T-NA Array
- **Provenance:** Verbatim from your hardware paste — precise but verbose.
- **Suggestions:**
  - `Hoymiles Microinverters`
  - `Microinverter Array`
  - `Solar Inverters`
  - `Hoymiles`
- **Decision:** _<fill in, or "keep">_
- **Other notes:** _<free-form>_

### `term_meter`

- **Current label:** Chint DTSU666 Meter
- **Provenance:** Verbatim from paste.
- **Suggestions:**
  - `Chint Meter`
  - `Grid Meter`
  - `Net Power Meter`
  - `DTSU666`
- **Decision:** _<fill in, or "keep">_
- **Other notes:** _<free-form>_

### `term_battery_system`

- **Current label:** Victron Cerbo GX + MultiPlus
- **Provenance:** Verbatim from paste. Actually two physical devices (gateway + inverter-charger) but a logical unit for our purposes.
- **Suggestions:**
  - `Victron`
  - `Battery System`
  - `Inverter / Charger`
  - `ESS`
- **Decision:** _<fill in, or "keep">_
- **Other notes:** _<free-form>_

### `term_grid`

- **Current label:** PG&E Utility Grid
- **Provenance:** Reasonable default — your utility is PG&E.
- **Suggestions:**
  - `Utility Grid`  *(more portable)*
  - `Grid`
  - `PG&E`
  - keep as-is
- **Decision:** _<fill in, or "keep">_
- **Other notes:** _<free-form>_

### `term_user`

- **Current label:** User / Homeowner
- **Provenance:** Reasonable default.
- **Suggestions:**
  - `Homeowner`
  - `Operator`
  - `Owner`
  - keep as-is
- **Decision:** _<fill in, or "keep">_
- **Other notes:** _<free-form>_

### `term_smiles_cloud`

- **Current label:** S-Miles Cloud
- **Provenance:** From paste; flagged as optional throughout.
- **Suggestions:**
  - `Hoymiles Cloud`
  - keep as-is
  - **DROP** *(if committing to local-only with no cloud forward at all)*
- **Decision:** _<fill in, or "keep">_
- **Other notes:** _<free-form>_

---

## Flows (8)

### `flow_f1_inverter_telemetry`

- **Current label:** F1: per-channel telemetry
- **Provenance:** AI-generated; F-numbers sequential.
- **Decision:** _<fill in, or "keep">_

### `flow_f2_power_limit`

- **Current label:** F2: power-limit setpoints
- **Provenance:** AI-generated.
- **Decision:** _<fill in, or "keep">_

### `flow_f3_net_grid_power`

- **Current label:** F3: net grid power, V/I/PF
- **Provenance:** AI-generated; the "V/I/PF" tail is the actual data shape.
- **Decision:** _<fill in, or "keep">_

### `flow_f4_battery_state`

- **Current label:** F4: SoC, mode, AC-in
- **Provenance:** AI-generated.
- **Decision:** _<fill in, or "keep">_

### `flow_f5_battery_command`

- **Current label:** F5: max-charge, grid setpoint
- **Provenance:** AI-generated.
- **Decision:** _<fill in, or "keep">_

### `flow_f6_user_input`

- **Current label:** F6: config, override
- **Provenance:** AI-generated.
- **Decision:** _<fill in, or "keep">_

### `flow_f7_user_view`

- **Current label:** F7: dashboards, alerts
- **Provenance:** AI-generated.
- **Decision:** _<fill in, or "keep">_

### `flow_f8_cloud_forward`

- **Current label:** F8: optional telemetry fwd
- **Provenance:** AI-generated.
- **Decision:** _<fill in, or "keep" or "drop" if dropping S-Miles entirely>_

---

## AC power edges (2, minor)

These are unlabeled red lines in the diagram representing physical AC power crossing the system boundary. They render with the implicit label "AC power" in some views.

### `edge_grid_to_inverters`

- **Current label:** (carries "AC power" in some renders)
- **Decision:** _<fill in, or "keep unlabeled">_

### `edge_grid_to_battery`

- **Current label:** (carries "AC power" in some renders)
- **Decision:** _<fill in, or "keep unlabeled">_

---

## After processing

Once I've applied your decisions:
1. The Mermaid source (`context.md`) gets updated labels.
2. The HTML5 (`context.html`) source gets updated labels.
3. The D2 source (`context.d2`) gets updated labels.
4. SVGs (`context-d2.svg`, `context-mermaid.svg`) get re-rendered.
5. We discuss whether to seed a real `examples/solar/dictionary.yaml` — the first concrete piece of the eventual toolkit dictionary feature.

*Created 2026-05-22 by Claude as part of the AI+HP workflow exercise.*
