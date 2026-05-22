# Naming Review — Level 1 / DFD (AutoFishingRig)

## ✅ Status: Resolved 2026-05-22

All defaults accepted. No renames applied; working names become locked names.

| Stable ID | Final label |
|---|---|
| `proc_acquire_tension` | **Acquire Tension** |
| `proc_bite_detector` | **Bite Detector** |
| `proc_reel_controller` | **Reel Controller** |
| `proc_serve_ui` | **Serve UI** |
| `proc_cloud_forward` | **Cloud Forward** |
| `store_system_state` | **System State** |
| All 7 internal flows | unchanged (accepted via bulk shortcut) |

Working names = locked names. No dictionary changes; ready for level-1 rendering via the now-generalized `render_project.py`.

---

*Per-level review: covers the **new** level-1 entities (5 processes + 1 data store + 7 internal flows). Level-0 terminators keep their names.*

**How to use:** open in MPE → click `[ ]` → `[x]` → save once → ping me with "level-1 naming done." I'll apply renames, regenerate `dfd.{md,html,d2}` + SVGs via `render_project.py` (this is the next slice where the generic renderer learns level-1).

---

## What we're naming

The locked level-1 decomposition — working names shown:

![Level-1 DFD draft](proposal-dfd.svg)

---

## Bulk shortcuts

- **Naming style:** (matches solar)
  - [x] **PascalCase labels with `proc_*` / `store_*` prefixed stable IDs** *(default)*
  - [ ] Other

- **Process names — accept working names as-is?**
  - [x] **Yes, accept all five** *(default — names are descriptive enough; see specific-candidate items below if you want alternatives)*
  - [ ] Review individually

- **Internal flow names fine as-is?** (`tension samples`, `system_state`, `motor cmd`, `event_alert`, `event_override`)
  - [x] **Yes, all fine** *(default — bulk accept)*
  - [ ] Review individually

- **Data store name** (`store_system_state` → "System State")
  - [x] **Keep "System State"** *(default — matches solar)*
  - [ ] Rename (specify in entity section)

---

## Specific candidates worth a second look

Only the two processes where alternatives might genuinely improve things.

### `proc_bite_detector` — current: **Bite Detector**

This is the brain. "Bite Detector" understates its role (it doesn't just detect — it runs the whole fishing sequence). Alternatives:

- [x] **Bite Detector** *(current — accurate for the entry point; the full state machine is implied)*
- [ ] **Fishing Sequencer** — describes what the brain actually does (sequence of fishing states)
- [ ] **Strike Manager** — fishing terminology ("strike" = bite)
- [ ] **Rig Controller** — generic "brain" framing
- [ ] **Catch Manager** — focuses on outcome

Custom name:
> 

Notes:
> 

### `proc_acquire_tension` — current: **Acquire Tension**

- [x] **Acquire Tension** *(current — descriptive)*
- [ ] **Sample Tension** — emphasizes sampling/timing
- [ ] **Tension Sensor** — names the role (it IS the sensor interface)
- [ ] **Line Sensor**

Custom name:
> 

Notes:
> 

---

## Everything else — accepting working names

| Stable ID | Label | Notes |
|---|---|---|
| `proc_reel_controller` | Reel Controller | clean |
| `proc_serve_ui` | Serve UI | matches solar |
| `proc_cloud_forward` | Cloud Forward | matches solar |
| `store_system_state` | System State | matches solar |

Override via:
> 

---

## After this form

1. Apply your selections to `../dictionary.yaml` (label changes only; stable IDs unchanged).
2. **Generalize `render_project.py` to handle level-1 DFD** (currently it only does Context). The fishing-rig is the test case.
3. Regenerate `dfd.{md,html,d2}` + SVGs.
4. Update the level-0 `context.generated.html` drill link to point at the now-existing level-1 (already configured via `has_internals` detection in `render_project.py`).
5. Move to **Stage 3** — CSPEC for `Bite Detector` (or whatever it's renamed to). The fishing state machine.

*Created 2026-05-22.*
