# Solar Local Stack — HP Toolkit Example

The original toolkit dogfood project. A local-first, open-source orchestration layer for a residential solar install (Hoymiles HMS-2000-4T-NA microinverters + Victron MultiPlus/Cerbo GX + Chint DTSU666 meter) that does:

1. **Dynamic excess-solar diversion** — sense surplus via the Chint meter, command Victron to absorb into the battery, keep PG&E net export near zero.
2. **Auto-discharge at night** — Victron ESS keeps net import near zero until battery SoC minimum.
3. **Outage handling** — Victron's <20 ms transfer + AC-coupled microgrid; system observes and adjusts setpoints.

Compliance constraints: PG&E zero-export tariff + NEC 690.12 rapid shutdown.

## Status

**Stages 1, 2, 3 all complete.** Used as the *first* dogfood project — the methodology and toolkit were developed alongside this example, so it's the more mature of the two.

| Stage | Artifact | Status |
|---|---|---|
| 1 | Context Diagram (level 0) | ✅ locked |
| 2 | Level-1 DFD | ✅ locked — 6 internal processes + System State data store |
| 3 | Energy Manager CSPEC | ✅ locked — 4-mode hierarchical state machine (Initializing / GridTie / Island / Fault), 13 states + 16 transitions |
| 4 | PSPECs for leaf processes | not yet started |
| 5 | Architecture model | not yet started |

## Layout

```
examples/solar/
├── README.md                         ← this file
├── dictionary.yaml                   ← HP Requirements Dictionary (27 entities, 17 flows, 16 transitions)
├── 00-context/                       ← Level 0
│   ├── README.md
│   ├── naming-review.md              ✅ resolved
│   ├── context.{md,html,d2}          hand-written; canonical
│   ├── context-{mermaid,d2}.svg      rendered
│   ├── context.generated.{md,html,d2}    generated from dictionary
│   └── context.generated-{mermaid,d2}.svg
├── 01-level1/                        ← Level 1: DFD + CSPECs
│   ├── README.md
│   ├── proposal.md                   ✅ locked
│   ├── naming-review.md              ✅ resolved
│   ├── proposal-dfd.{d2,svg}         draft, historical
│   ├── dfd.{md,html,d2}              hand-written; canonical
│   ├── dfd-{mermaid,d2}.svg          rendered
│   ├── dfd.generated.*               generated from dictionary
│   └── cspecs/compute-balance/   (subdir name = stable id of proc_compute_balance)
│       ├── README.md
│       ├── proposal.md               ✅ locked
│       ├── naming-review.md          ✅ resolved
│       ├── proposal-states.{mmd,svg} draft, historical
│       ├── cspec.{md,html,d2}        hand-written; canonical
│       ├── cspec-{mermaid,d2}.svg    rendered
│       └── cspec.generated.*         generated from dictionary
```

## How to view

```bash
# Validate the dictionary
cd toolkit
uv run python -m hp_toolkit.validate ../examples/solar/dictionary.yaml

# Regenerate all artifacts from the dictionary
uv run python scripts/render_project.py ../examples/solar
```

Then open any of the `.html` files in a browser. The navigation chain works end-to-end:

```
context.html
  ↓ double-click "Solar Local Stack"
dfd.html
  ↓ double-click "Energy Manager"  (the bold/dark "brain" bubble)
cspec.html
  ★ explore the state machine
```

Side panel in each: click nodes / edges for descriptions, kind, dictionary entries, HP reference links.

## Why this example

- **First dogfood**: the methodology + toolkit were built around this project; many tactics in `PLAN.md` were lived here.
- **Real-stakes shape**: Kevin's actual planning conversation for a real residential install. Not a hypothetical.
- **HP-shaped in every dimension**: hard real-time control loop, multi-vendor integration boundaries, state-rich state machine, regulated (PG&E + NEC), safety-critical, all four HP architecture templates apply naturally.
- **Comparable to**: [`../fishing-rig/`](../fishing-rig/) — a second dogfood built to test transferability. Same workflow, different domain.

## See also

- [`PLAN.md`](../../PLAN.md) — design log, methodology tactics, lived examples
- [`toolkit/reference/HP_QUICK_REF.md`](../../toolkit/reference/HP_QUICK_REF.md) — HP method vocabulary
