# Smart Doorbell — HP Toolkit Project

> A connected doorbell with motion detection, video capture, two-way audio, and mobile alerting. Triggered by physical button press OR motion sensor; uploads to cloud and notifies homeowner.

## Status

**Stage 1 in progress.** Created 2026-05-22 via `hp-init`. See [`00-context/proposal.md`](00-context/proposal.md) for the form-based Context Diagram review.

## Planned structure

```
examples/doorbell/
├── README.md                    ← this file
├── dictionary.yaml              ← HP Requirements Dictionary (minimal skeleton)
├── 00-context/
│   ├── proposal.md              ✅ active (form-based Stage 1 review)
│   ├── naming-review.md         pending after proposal locks
│   ├── context.{md,html,d2}     generated from dictionary
│   └── context-*.svg            rendered
├── 01-level1/                   (future — Stage 2)
└── ...
```

## How to advance

1. **Engage with `00-context/proposal.md`** — fill in checkboxes, save, ping.
2. **Apply decisions** — terminator inventory populated in `dictionary.yaml`.
3. **Validate**: `cd toolkit && uv run python -m hp_toolkit.validate ../examples/doorbell/dictionary.yaml`
4. **Render**: `uv run python scripts/render_project.py ../examples/doorbell`
5. **Continue to Stage 2** (level-1 DFD decomposition).

## See also

- [`../../PLAN.md`](../../PLAN.md) — methodology + design log
- [`../../toolkit/reference/HP_QUICK_REF.md`](../../toolkit/reference/HP_QUICK_REF.md) — HP vocabulary
- [`../solar/`](../solar/) — mature reference dogfood (all 3 stages locked)
- [`../fishing-rig/`](../fishing-rig/) — transferability test dogfood
