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
| 4 — PSPECs | ✅ N of M locked / 🟡 in flight / ⬜ not started | Every leaf process (non-CSPEC) has a `pspec_*` entry in dictionary |
| 5 — Architecture | ✅ locked / 🟡 in flight / ⬜ not started | All leaf processes / CSPECs / data stores allocated; every module has an AMS |

**Modernization layer summary:** one-line counts for each modernization section the project declares (ADRs by status, budgets vs. TPMs that track them, SLOs tied to TPMs, leaf-PSPEC observability + V&V coverage, cross-trust-zone interconnects with STRIDE, bounded contexts + ACLs). Each row reads "none declared" when absent — the modernization layer is optional and incremental.

**Validation status:** runs `hp_toolkit.validate` and reports `VALID` / `N errors` plus the coverage percentages (including modernization metrics: `observability_coverage_pct`, `slo_coverage_pct`, `stride_coverage_pct`, `verification_coverage_pct`, `synchronicity_coverage_pct`, `tpm_within_threshold_pct`, `tpm_growth_safety_pct`, `budget_allocation_completeness_pct`, `alert_runbook_coverage_pct`).

**Artifact freshness:** for each level, compares the modification time of `dictionary.yaml` against the `*.generated.*` artifacts. If dictionary is newer, suggests `python scripts/render_project.py <dir>` to regenerate.

**Open questions:** scans `00-context/proposal.md`, `01-level1/proposal.md`, etc. for `⬜` or unchecked `[ ]` items — flags any unresolved decisions.

## Sample output

```
=== AutoFishingRig — Project Status ===

Stages
  ✅ Stage 1 — Context Diagram          5 terminator(s); proposal locked
  ✅ Stage 2 — Level-1 DFD              5 internal process(es); proposal locked
  ✅ Stage 3 — CSPECs                   1 locked CSPEC(s); 9 states + 18 transitions
  ✅ Stage 4 — PSPECs                   4/4 leaf processes have PSPECs
  ✅ Stage 5 — Architecture model       2 module(s); 2 flow(s); 1 interconnect(s); 5/5 leaf processes allocated; 2/2 AMS

Modernization layer
  ADRs                   1 (1 accepted)
  Budgets / TPMs         2 budget(s); 2 TPM(s) [1/2 budget(s) tracked by TPM]
  SLOs                   1 SLO(s) [1/1 tied to a TPM]
  Observability          1/4 leaf PSPEC(s) declare observability
  V&V plans              1/4 leaf PSPEC(s) declare verification
  STRIDE                 ✅ 1/1 cross-trust-zone interconnect(s) have STRIDE mitigations
  Bounded contexts       none declared (single-context project)

Validation
  ✅ no errors
  ais_coverage_pct                   [████████████████████] 100.0%
  ...
  observability_coverage_pct         [███░░░░░░░░░░░░░░░░░]  16.7%
  slo_coverage_pct                   [██████████░░░░░░░░░░]  50.0%
  stride_coverage_pct                [████████████████████] 100.0%
  verification_coverage_pct          [███░░░░░░░░░░░░░░░░░]  16.7%

Artifact freshness
  ✅ all generated artifacts are fresh

Open questions: ✅ none — all reviewable decisions resolved
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

**Skill description: ✅ drafted.** Backing code: ✅ live in [`hp_toolkit/status.py`](../hp_toolkit/status.py) — Stages 1–5 detection, modernization-layer summary (ADRs / Budgets / TPMs / SLOs / observability / V&V / STRIDE / bounded contexts), validation summary with coverage metrics, artifact-freshness scan, open-questions scan. CLI: `uv run python -m hp_toolkit.status <project-dir>`.

## See also

- Tactic source: [`PLAN.md` > Methodology Tactics > B > Make rigor measurable](../../PLAN.md)
- Companion: [`hp-validate`](hp-validate.md) (which `hp-status` calls internally)
