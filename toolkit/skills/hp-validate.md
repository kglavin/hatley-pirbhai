---
name: hp-validate
description: Run validators against the project dictionary — reference integrity, hierarchy consistency, coverage metrics, orphan detection. Reports errors/warnings/info plus "rigor measurable" percentages.
---

# hp-validate

## When to use

Run after any significant edit to the dictionary or model files:

- After a naming review applies renames (verifies references still resolve).
- After a new level's decomposition is locked (catches dangling parent pointers).
- After a CSPEC's states are added.
- **Before every commit** (catch hand-written drift before it lands in git).
- Periodically — from a git hook or CI — to catch drift over time.

## What it does

Loads the project's `dictionary.yaml` and runs four validators:

| # | Validator | Severity | What it checks |
|---|---|---|---|
| 1 | `reference_integrity` | **error** | every `parent` / `parent_state` / `source` / `target` resolves to a valid entity id |
| 2 | `hierarchy_consistency` | warning | `parent_state` only on states; states have parents; terminators don't have parents; sub-states point at composite parents |
| 3 | `coverage_metrics` | (metrics) | description %, flow medium %, flow notes %, entity counts by kind, level distribution — the **make-rigor-measurable** payoff |
| 4 | `find_orphans` | info | entities referenced by no flow/edge and not parents of anything — usually a forgotten flow or stale entry |

Reports are structured: `errors` block (must fix), `warnings` document, `info` catches drift, metrics report as percentages with ASCII bars.

## Behavior

**CLI** (one-shot from any context):

```bash
cd toolkit && uv run python -m hp_toolkit.validate path/to/dictionary.yaml
```

**Programmatic** (from the toolkit code or another skill):

```python
from hp_toolkit import load, validate

project = load("examples/solar/dictionary.yaml")
report = validate(project)

if not report.ok:
    raise SystemExit(f"{len(report.errors)} validation errors")

print(f"Description coverage: {report.metrics['description_coverage_pct']}%")
```

**Sample output** (against the solar dogfood, 2026-05-22):

```
== Coverage metrics ==
  description_coverage_pct           [████████████████████] 100.0%
  flow_medium_coverage_pct           [█████████░░░░░░░░░░░]  47.1%
  flow_notes_coverage_pct            [████████████████░░░░]  82.4%

== Counts ==
  entities__data_store               1
  entities__process                  6
  entities__state                    10
  entities__state_composite          3
  entities__system                   1
  entities__terminator               6
  entities_total                     27
  flows_total                        17
  level_0_entities                   7
  level_1_entities                   7
  level_2_entities                   13

VALID — no errors
```

## Discipline

- **Errors block.** If reference integrity fails, every downstream artifact (diagrams, skill outputs, traceability queries) is unsound. Block commits with `hp-validate` from a pre-commit hook.
- **Warnings document.** Hierarchy oddities are usually intentional (e.g., terminator with `parent` for a special case) but should be explained in the entity's `description` field.
- **Info catches drift.** Orphans typically indicate forgotten flows or stale entries from obsolete iterations. Worth a periodic sweep.
- **Metrics drive progress.** Each percentage should trend toward 100 over the life of the project. Watch for regressions — a drop in coverage means recent edits skimped on documentation.
- **Internal flows legitimately lack `medium`.** A flow between two internal processes (e.g., `proc_acquire_telemetry` → `store_system_state`) has no transport medium — it's in-memory event passing. The medium-coverage % will plateau below 100 because of this; that's correct, not a bug. Future refinement: split medium-coverage into boundary-only.

## Lived example

The first run of `hp-validate` against the hand-written solar dogfood dictionary **caught a real bug**: `version: 0.1` in the YAML was parsed as a float, mismatching the model's `version: str`. This is the kind of value the validator layer creates — catching what human review missed. Fixed in both places (YAML quoted; model relaxed via `coerce_numbers_to_str=True`).

## See also

- Tactic: [`PLAN.md` > Methodology Tactics > B > Make rigor measurable](../../PLAN.md)
- HP reference: [Balancing](../reference/HP_QUICK_REF.md#balancing) · [Traceability](../reference/HP_QUICK_REF.md#traceability) · [Requirements Dictionary](../reference/HP_QUICK_REF.md#requirements-dictionary)
- Code: [`toolkit/hp_toolkit/validate.py`](../hp_toolkit/validate.py)
- Companion skill: [`hp-confirm-naming`](hp-confirm-naming.md) (typically run *before* `hp-validate` after a rename)
