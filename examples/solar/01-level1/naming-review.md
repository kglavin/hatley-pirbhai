# Naming Review — Level 1 / DFD

## ✅ Status: Resolved 2026-05-22

All defaults accepted. Two label changes applied; all other working names kept; internal flows kept by bulk shortcut.

| Stable ID | Final label | Change |
|---|---|---|
| `proc_acquire_telemetry` | **Acquire Telemetry** | kept |
| `proc_compute_balance` | **Energy Manager** | renamed (was "Compute Energy Balance") |
| `proc_dispatch_commands` | **Dispatch Commands** | kept |
| `proc_serve_ui` | **Serve UI** | kept |
| `proc_handle_user_input` | **Handle Input** | renamed (was "Handle User Input") |
| `proc_cloud_forward` | **Cloud Forward** | kept |
| `store_system_state` | **System State** | kept |
| Internal flows | all kept as-is | bulk shortcut: "internal flow names fine as-is" |

Bulk shortcuts applied: terse naming style, internal flow names fine as-is, keep "System State" for data store.

Updates applied to `../dictionary.yaml`. Locked DFD rendered: `dfd.{md,html,d2}` sources + `dfd-mermaid.svg` + `dfd-d2.svg`.

---

*Per-level review: this file covers the **new** level-1 entities only (the internal processes, the data store, and the internal flows). Level-0 terminators keep their existing names from `../dictionary.yaml`.*

**How to use this file** *(form-based batch review — same as level-0)*:

1. Open in VSCode with **Markdown Preview Enhanced**.
2. In the preview, click `[ ]` → `[x]` on the option you want for each entity.
3. Use `Custom:` lines for write-ins; `Notes:` for free-form thoughts.
4. **Save once** when done. Ping me. I parse all selections in one pass, apply the renames, update `dictionary.yaml`, and render `dfd.{md,html,d2}` + SVGs.

---

## What we're naming (the level-1 diagram)

![Level-1 DFD draft](proposal-dfd.svg)

*Working names in the diagram above. Decision-form below picks the final names. Boundary terminators (Solar Inverters, Net Power Meter, etc.) are already named at level 0 and don't get re-reviewed here.*

---

## Bulk shortcuts

- **Naming style for level-1**: terse (matching level-0 preference)?
  - [x] **Yes, terse** — match the style we used for level-0 (Solar Inverters, Net Power Meter, etc.)
  - [ ] Allow longer where clarity benefits

- **Internal flow / event names fine as-is?** (`system_state`, `cmd_setpoint`, `cmd_inverter_limit`, `event_alert`, `event_override`, `event_config`)
  - [x] **Yes, all fine** — these are descriptive enough; skip per-flow review
  - [ ] Review individually (specify in Notes below)

- **Data store name** (`store_system_state` → "System State")
  - [x] **Keep "System State"**
  - [ ] Rename (specify in entity section)

- **Other bulk preferences**:
> 

---

## Processes (6, one optional)

### `proc_acquire_telemetry`

- [x] **Acquire Telemetry** — Claude's recommendation (working name; keep)
- [ ] Telemetry Ingest
- [ ] Ingest
- [ ] Telemetry Acquisition

Custom name (overrides if non-empty):
> 

Notes:
> 

### `proc_compute_balance`

- [ ] Compute Energy Balance *(verbose working name)*
- [x] **Energy Manager** — terser, conveys ownership of the brain logic
- [ ] Energy Controller
- [ ] Balance Controller
- [ ] Brain *(too colloquial probably)*

Custom name (overrides if non-empty):
> 

Notes:
> 

### `proc_dispatch_commands`

- [x] **Dispatch Commands** — Claude's recommendation (working name; keep)
- [ ] Command Dispatcher
- [ ] Actuator
- [ ] Command Out

Custom name (overrides if non-empty):
> 

Notes:
> 

### `proc_serve_ui`

- [x] **Serve UI** — Claude's recommendation (working name; keep)
- [ ] UI
- [ ] Dashboard
- [ ] Presentation

Custom name (overrides if non-empty):
> 

Notes:
> 

### `proc_handle_user_input`

- [ ] Handle User Input *(verbose working name)*
- [x] **Handle Input** — terser, the "user" is implicit (the owner is the only user)
- [ ] User Input
- [ ] Owner Input
- [ ] Input Handler

Custom name (overrides if non-empty):
> 

Notes:
> 

### `proc_cloud_forward` *(optional)*

- [x] **Cloud Forward** — Claude's recommendation (working name; keep)
- [ ] Cloud Telemetry
- [ ] S-Miles Forward
- [ ] **DROP** *(commit to local-only — also remove F8 and S-Miles Cloud terminator)*

Custom name (overrides if non-empty):
> 

Notes:
> 

---

## After this form

When you ping me, I'll:

1. Apply your name choices (overrides + checkbox selections) to `dictionary.yaml`.
2. Generate `dfd.md` (Mermaid source), `dfd.html` (interactive workspace), `dfd.d2` (D2 source).
3. Render `dfd-mermaid.svg` and `dfd-d2.svg`.
4. Replace the draft `proposal-dfd.svg` reference in `proposal.md` with the locked `dfd-*.svg`.
5. Move to **Stage 3** — CSPEC for `proc_compute_balance` (or whatever you renamed it to). That's the state machine for grid-tie / island / charging / fault modes. State-rich; needs the most design attention.

*Created 2026-05-22.*
