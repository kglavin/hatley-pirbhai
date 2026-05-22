---
name: hp-init
description: Scaffold a new HP toolkit project — creates the directory structure, an empty dictionary.yaml template, and a Stage 1 (Context Diagram) proposal stub.
---

# hp-init

## When to use

Starting work on a new HP-modeled project from scratch — before any context diagram exists. Sets up the canonical directory layout + `dictionary.yaml` template + a Stage 1 proposal file that's ready for form-based review.

Specifically when:

- The user wants to apply the HP toolkit to a project for the first time
- A fresh dogfood case is needed (transferability testing)
- A practitioner is onboarding their first project

## What it creates

Given a project name (e.g., `coffee-machine`), `hp-init` produces:

```
examples/<project-name>/
├── README.md                   # project overview (filled in from initial questions)
├── dictionary.yaml             # empty schema-valid skeleton (sys_root + placeholder terminator)
└── 00-context/
    └── proposal.md             # Stage 1 form-based proposal stub
```

The `dictionary.yaml` template has the schema skeleton:

```yaml
project: <Project Name>
version: "0.1"
last_updated: <today's date>

entities:
  sys_root:
    kind: system
    label: "<Project Name>"
    level: 0
    description: |
      <Fill in: what is this system?>

  # Add terminators here as you identify them in Stage 1
  # term_<name>:
  #   kind: terminator
  #   label: ...
  #   level: 0
  #   description: ...

flows: {}    # populated in Stage 1
edges: {}    # populated if any physical edges (power, etc.)
transitions: {}  # populated in Stage 3 when a CSPEC exists
```

The `00-context/proposal.md` template contains the same form-based decision structure used in `examples/solar/00-context/` and `examples/fishing-rig/00-context/`:

- System name
- System scope (narrow / medium / wide)
- Terminator inventory
- Optional terminators (cloud / monitoring)
- Power-source modeling
- Flow naming convention
- "Anything else"

Each decision has Claude's recommended default pre-checked; the user fills in the form via Markdown Preview Enhanced.

## Behavior

When invoked, conversationally:

1. Ask the user: project name; one-paragraph description of what the system does.
2. Identify likely terminators from the description (Propose move) and pre-populate the proposal's terminator list.
3. Write the three files above.
4. Tell the user: "Open `examples/<name>/00-context/proposal.md` in MPE, fill in any overrides, save, ping when done."
5. Follow the standard form-based review loop from that point.

## Discipline

- **Don't pre-fill the dictionary with guesses.** Until Stage 1 is locked, the dictionary should be intentionally minimal (just `sys_root`). Forcing the user through the proposal pass catches things AI-inference would get wrong.
- **The directory layout is fixed convention** (`00-context/`, then `01-level1/`, then `cspecs/<name>/` inside that). `hp-init` enforces it so later renderers know where to find / write things.
- **`last_updated` is auto-set** to today; user updates manually thereafter when significant edits land.

## Implementation status

**Skill description + code: ✅ live.** Implemented at [`toolkit/scripts/hp_init.py`](../scripts/hp_init.py).

CLI usage:

```bash
cd toolkit
uv run python scripts/hp_init.py <project-name> [--label "<Display>"] [--description "..."] [--dest PATH]
```

Programmatic:

```python
from pathlib import Path
import sys; sys.path.insert(0, "toolkit/scripts")
from hp_init import init_project

project_dir = init_project(
    project_name="doorbell",
    label="Smart Doorbell",
    description="A connected doorbell with motion detection...",
)
```

Templates are inline string constants in `hp_init.py`:
- `_DICTIONARY_TEMPLATE` — produces a schema-valid skeleton with `sys_root` + commented templates for terminators, flows, edges, and transitions to copy-paste into
- `_PROPOSAL_TEMPLATE` — Stage 1 form-based proposal with 7 standard decisions (system name, scope, terminator inventory, optional terminators, power modeling, flow naming, anything-else)
- `_README_TEMPLATE` — project README with status + planned structure + how-to-advance instructions

Refuses to overwrite an existing project directory (raises `FileExistsError`).

**Lived example:** [`examples/doorbell/`](../../examples/doorbell/) — a tiny "Smart Doorbell" project created by `hp-init` as a working demonstration. Minimal dictionary (just `sys_root`); validates clean; renders a near-empty Context Diagram via `render_project.py`. Shows what a fresh-scaffolded project looks like before any Stage 1 work begins.

## See also

- Tactic source: [`PLAN.md` > Methodology Tactics > B > Repo hierarchy mirrors HP hierarchy](../../PLAN.md)
- Lived examples:
  - [`examples/solar/00-context/`](../../examples/solar/00-context/) — first dogfood (created ad-hoc; `hp-init` would have produced this scaffold)
  - [`examples/fishing-rig/`](../../examples/fishing-rig/) — second dogfood (also created ad-hoc; the gap that prompted writing this skill)
- Companion skills: [`hp-propose-context`](hp-propose-context.md) *(planned)* fills in the proposal; [`hp-confirm-naming`](hp-confirm-naming.md) follows up after the proposal locks.
