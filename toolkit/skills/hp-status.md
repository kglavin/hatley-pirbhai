---
name: hp-status
description: Report what stages an HP project has reached, what's locked vs in-progress, and key coverage metrics. The "where are we?" view of a project.
---

# hp-status

## When to use

- Resuming work on a project after a break — orient quickly
- Onboarding someone new to a project
- Before deciding which stage to work on next
- For PR / commit summaries: "Stage 3 complete; CSPEC for Energy Manager locked"

## What it shows

Given a project directory, `hp-status` reports:

**Stage progression:**

| Stage | Status | Evidence |
|---|---|---|
| 1 — Context Diagram | ✅ locked / 🟡 proposal in flight / ⬜ not started | `00-context/proposal.md` Status block + `dictionary.yaml` has `sys_root` + terminators |
| 2 — Level-1 DFD | ✅ locked / 🟡 in flight / ⬜ not started | `01-level1/proposal.md` Status block + internal processes in dictionary |
| 3 — CSPECs | ✅ N of M locked / 🟡 in flight / ⬜ not started | For each process with `needs_cspec: true`: `cspecs/<id>/proposal.md` Status block + transitions in dictionary |
| 4 — PSPECs | planned | (not yet implemented) |
| 5 — Architecture | planned | (not yet implemented) |

**Validation status:** runs `hp_toolkit.validate` and reports `VALID` / `N errors` plus the coverage percentages.

**Artifact freshness:** for each level, compares the modification time of `dictionary.yaml` against the `*.generated.*` artifacts. If dictionary is newer, suggests `python scripts/render_project.py <dir>` to regenerate.

**Open questions:** scans `00-context/proposal.md`, `01-level1/proposal.md`, etc. for `⬜` or unchecked `[ ]` items — flags any unresolved decisions.

## Sample output

```
=== AutoFishingRig — Project Status ===

Stages
  ✅ Stage 1 — Context Diagram          (locked 2026-05-22)
  ✅ Stage 2 — Level-1 DFD              (locked 2026-05-22)
  ✅ Stage 3 — CSPECs (1/1 locked)       (Bite Detector: locked 2026-05-22)
  ⬜ Stage 4 — PSPECs                    (not yet started)
  ⬜ Stage 5 — Architecture              (not yet started)

Dictionary
  21 entities (6 level-0, 6 level-1, 9 level-2)
  12 flows · 2 edges · 18 transitions
  Description coverage: 100%
  Validates: ✅ no errors

Artifacts
  Context generated:  ✅ fresh (last regen: 2 min ago)
  Level-1 DFD:        ✅ fresh
  Bite Detector CSPEC: ✅ fresh

Open questions: none.

Next action: Stage 4 (PSPECs for leaf bubbles) or apply toolkit to a third
project for further transferability validation.
```

## Behavior

Programmatically (when wired):

```python
from hp_toolkit import load, validate
from hp_toolkit.status import status_report

project = load("examples/fishing-rig/dictionary.yaml")
report  = status_report(project, project_dir="examples/fishing-rig")
print(report.format())
```

CLI (when wired):

```bash
cd toolkit
uv run python scripts/status.py ../examples/fishing-rig
```

## Discipline

- **Status comes from artifact evidence, not from chat.** A stage is "locked" only if its `proposal.md` has a `Status: Locked` block AND the dictionary has the corresponding entries. Chat claims don't count.
- **Coverage percentages are the rigor measure.** Below 100% on description coverage is a sign someone shipped without writing prose; flag it.
- **Stale artifacts are drift.** If `dictionary.yaml` was edited but the generated artifacts weren't regenerated, the on-disk diagrams are *wrong*. `hp-status` should highlight this.

## Implementation status

**Skill description: drafted.** Actual `status.py` implementation is not yet written. Until then, the workflow runs by hand:

```bash
# Manual status check (today)
ls examples/<project>/00-context/proposal.md            # check Status block
ls examples/<project>/01-level1/proposal.md             # check Status block  
ls examples/<project>/01-level1/cspecs/*/proposal.md    # check Status blocks
cd toolkit && uv run python -m hp_toolkit.validate ../examples/<project>/dictionary.yaml
```

Sketched implementation:

```python
# toolkit/hp_toolkit/status.py (planned)
def status_report(project: Project, project_dir: Path) -> StatusReport:
    return StatusReport(
        stage_1=_check_stage_1(project_dir),
        stage_2=_check_stage_2(project, project_dir),
        cspec_progress=_check_cspecs(project, project_dir),
        validation=validate(project),
        artifact_freshness=_check_freshness(project_dir),
        open_questions=_scan_unresolved_form_items(project_dir),
    )
```

## See also

- Tactic source: [`PLAN.md` > Methodology Tactics > B > Make rigor measurable](../../PLAN.md)
- Companion: [`hp-validate`](hp-validate.md) (which `hp-status` calls internally)
