# Smart Doorbell — Stage 1: Context Diagram Proposal

**Form-based batch review.** Open in Markdown Preview Enhanced → click `[ ]` → `[x]` → fill `Custom:` / `Notes:` lines → save once → ping with "context proposal reviewed."

---

## What the system does

> A connected doorbell with motion detection, video capture, two-way audio, and mobile alerting. Triggered by physical button press OR motion sensor; uploads to cloud and notifies homeowner.

---

## Proposed Context Diagram

*Draft to be filled in. Once you identify the system's terminators and boundary flows (Decisions 2–3 below), the diagram will be embedded here.*

---

## Decisions

### Decision 1 — System name

- [x] **Smart Doorbell** *(default — from `hp-init`)*
- [ ] Other:

Custom name:
>

Notes:
>

### Decision 2 — System scope

What's inside the system vs external?

- [x] **Medium**: brain + integrated sensors / actuators. External terminators are the user-facing entities, physical interfaces, and external services. *(Default — matches solar and fishing-rig pattern.)*
- [ ] **Narrow**: controller software only. Hardware is also terminators.
- [ ] **Wide**: the whole physical system including mounting / casing.

Notes:
>

### Decision 3 — Terminator inventory

What external entities does the system interact with? List candidates (the conversational AI working with you typically pre-populates these from your description).

- [ ] User / Operator
- [ ] *(add others)*
- [ ] Cloud / Remote service (optional)
- [ ] Power source

Custom additions / removals:
>

Notes:
>

### Decision 4 — Optional terminators

Which terminators are optional (e.g., off by default, toggleable)?

- [ ] Cloud forwarding (off by default)
- [ ] Other:

Notes:
>

### Decision 5 — Power-source modeling

- [x] **Show as physical edge** *(default — matches solar's AC power, fishing-rig's DC power)*
- [ ] **Model with data flows** for battery state / charging events
- [ ] **Don't model power** (assume always available)

Notes:
>

### Decision 6 — Boundary flow naming convention

- [x] **F1-Fn numbering with descriptive labels** *(default — matches solar and fishing-rig)*
- [ ] Descriptive names only (no F-numbers)
- [ ] Other:

Notes:
>

### Decision 7 — Anything else worth raising?

Notes:
>

---

## After this form

When you ping me:

1. Apply your decisions; lock the proposal.
2. Add terminator entities to `../dictionary.yaml`.
3. Populate boundary flow entries (F1-Fn) from the terminator inventory.
4. Run `python -m hp_toolkit.validate ../dictionary.yaml` (sanity).
5. Run `python scripts/render_project.py ../examples/doorbell` to produce the level-0 Context Diagram in all three views.
6. Generate `naming-review.md` for any flow / entity working names worth reviewing.

Then Stage 2: level-1 decomposition.
