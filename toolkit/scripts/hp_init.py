#!/usr/bin/env python
"""hp-init — scaffold a new HP toolkit project.

Creates the canonical directory structure + a minimal schema-valid
dictionary.yaml + a Stage 1 (Context Diagram) proposal stub that's
ready for form-based review.

Usage:
    cd toolkit
    uv run python scripts/hp_init.py <project-name> [options]

Examples:
    uv run python scripts/hp_init.py doorbell \\
      --label "Smart Doorbell" \\
      --description "A connected doorbell with motion detection..."

    uv run python scripts/hp_init.py thermostat \\
      --label "Smart Thermostat" \\
      --dest ../examples
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────
# Templates
# ─────────────────────────────────────────────────────────────────────

_DICTIONARY_TEMPLATE = '''# {label} — Naming Dictionary
#
# Created {today} via hp-init. HP's Requirements Dictionary for this
# project. Populate as you advance through stages:
#   - Stage 1 adds terminators + boundary flows
#   - Stage 2 adds internal processes + data stores + internal flows
#   - Stage 3 adds states + transitions for any process with needs_cspec=true

project: {label}
version: "0.1"
last_updated: {today}

entities:

  sys_root:
    kind: system
    label: "{label}"
    level: 0
    description: |
      {description}

  # ─── Terminators (add via Stage 1) ───
  # Template:
  # term_<name>:
  #   kind: terminator
  #   label: "<Display Name>"
  #   level: 0
  #   description: |
  #     <What is this external entity? What's its relationship to the system?>

flows: {{}}
  # ─── Boundary flows (Stage 1) ───
  # Template:
  # flow_f1_<name>:
  #   label: "F1: <flow purpose>"
  #   source: term_<name>
  #   target: sys_root
  #   kind: data            # or control / data+control
  #   level: 0
  #   medium: "<HTTP / RS485 / etc.>"
  #   notes: "<context>"

edges: {{}}
  # ─── Non-data physical edges (Stage 1, for context) ───
  # Template:
  # edge_<name>:
  #   label: "<short label>"
  #   source: term_<name>
  #   target: sys_root
  #   kind: physical_dc_power      # or physical_ac_power / physical_interaction
  #   level: 0
  #   notes: "<context>"

transitions: {{}}
  # ─── CSPEC transitions (Stage 3) ───
  # Populated when a process with needs_cspec=true has its state machine locked.
'''


_PROPOSAL_TEMPLATE = '''# {label} — Stage 1: Context Diagram Proposal

**Form-based batch review.** Open in Markdown Preview Enhanced → click `[ ]` → `[x]` → fill `Custom:` / `Notes:` lines → save once → ping with "context proposal reviewed."

---

## What the system does

> {description}

---

## Proposed Context Diagram

*Draft to be filled in. Once you identify the system's terminators and boundary flows (Decisions 2–3 below), the diagram will be embedded here.*

---

## Decisions

### Decision 1 — System name

- [x] **{label}** *(default — from `hp-init`)*
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
5. Run `python scripts/render_project.py ../examples/{project_name}` to produce the level-0 Context Diagram in all three views.
6. Generate `naming-review.md` for any flow / entity working names worth reviewing.

Then Stage 2: level-1 decomposition.
'''


_README_TEMPLATE = '''# {label} — HP Toolkit Project

> {description}

## Status

**Stage 1 in progress.** Created {today} via `hp-init`. See [`00-context/proposal.md`](00-context/proposal.md) for the form-based Context Diagram review.

## Planned structure

```
examples/{project_name}/
├── README.md                    ← this file
├── dictionary.yaml              ← HP Requirements Dictionary (minimal skeleton)
├── 00-context/
│   ├── proposal.md              ✅ active (form-based Stage 1 review)
│   ├── naming-review.md         pending after proposal locks
│   ├── context.{{md,html,d2}}     generated from dictionary
│   └── context-*.svg            rendered
├── 01-level1/                   (future — Stage 2)
└── ...
```

## How to advance

1. **Engage with `00-context/proposal.md`** — fill in checkboxes, save, ping.
2. **Apply decisions** — terminator inventory populated in `dictionary.yaml`.
3. **Validate**: `cd toolkit && uv run python -m hp_toolkit.validate ../examples/{project_name}/dictionary.yaml`
4. **Render**: `uv run python scripts/render_project.py ../examples/{project_name}`
5. **Continue to Stage 2** (level-1 DFD decomposition).

## See also

- [`../../PLAN.md`](../../PLAN.md) — methodology + design log
- [`../../toolkit/reference/HP_QUICK_REF.md`](../../toolkit/reference/HP_QUICK_REF.md) — HP vocabulary
- [`../solar/`](../solar/) — mature reference dogfood (all 3 stages locked)
- [`../fishing-rig/`](../fishing-rig/) — transferability test dogfood
'''


# ─────────────────────────────────────────────────────────────────────
# Implementation
# ─────────────────────────────────────────────────────────────────────

def init_project(
    project_name: str,
    label: str | None = None,
    description: str | None = None,
    dest_dir: Path | None = None,
) -> Path:
    """Scaffold a new HP project. Returns the project directory path.

    Raises FileExistsError if the project directory already exists.
    """
    if label is None:
        # Convert "smart-doorbell" → "Smart Doorbell"
        label = " ".join(w.capitalize() for w in project_name.replace("-", " ").replace("_", " ").split())
    if description is None:
        description = f"(TODO: describe what {label} does in 1-2 sentences.)"
    if dest_dir is None:
        # Default: ../examples/ relative to this script
        dest_dir = Path(__file__).resolve().parent.parent.parent / "examples"

    project_dir = dest_dir / project_name
    if project_dir.exists():
        raise FileExistsError(f"{project_dir} already exists; refusing to overwrite")

    project_dir.mkdir(parents=True)
    (project_dir / "00-context").mkdir()

    today = date.today().isoformat()

    ctx = dict(
        project_name=project_name,
        label=label,
        description=description.replace("\n", "\n      "),  # YAML block-scalar indent
        today=today,
    )

    (project_dir / "dictionary.yaml").write_text(
        _DICTIONARY_TEMPLATE.format(**ctx)
    )
    (project_dir / "00-context" / "proposal.md").write_text(
        _PROPOSAL_TEMPLATE.format(**ctx)
    )
    (project_dir / "README.md").write_text(
        _README_TEMPLATE.format(**ctx)
    )

    return project_dir


def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a new HP toolkit project (directory + dictionary template + Stage 1 proposal)."
    )
    parser.add_argument("project_name", help="kebab-case name for the project directory (e.g., 'doorbell')")
    parser.add_argument("--label", help="System display name (defaults to title-cased project_name)")
    parser.add_argument("--description", help="One-paragraph system description (used in sys_root.description)")
    parser.add_argument("--dest", type=Path, help="Parent directory (defaults to ../examples/ relative to script)")

    args = parser.parse_args()

    try:
        project_dir = init_project(
            project_name=args.project_name,
            label=args.label,
            description=args.description,
            dest_dir=args.dest,
        )
    except FileExistsError as e:
        print(_color(f"ERROR: {e}", "31"), file=sys.stderr)
        return 1

    print(_color(f"✓ Created {project_dir}/", "32"))
    for f in sorted(project_dir.rglob("*")):
        if f.is_file():
            rel = f.relative_to(project_dir.parent.parent)
            print(f"  {rel}  ({f.stat().st_size} bytes)")
    print()
    print(_color("Next steps:", "1"))
    print(f"  1. Engage with: {project_dir / '00-context' / 'proposal.md'}")
    print(f"  2. Once Stage 1 is locked, populate {project_dir / 'dictionary.yaml'} with terminators + flows")
    print(f"  3. Run: cd toolkit && uv run python -m hp_toolkit.validate {project_dir.parent.name + '/' + project_dir.name}/dictionary.yaml")
    print(f"  4. Render: cd toolkit && uv run python scripts/render_project.py ../{project_dir.relative_to(project_dir.parent.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
