# AutoFishingRig — HP Toolkit Example

A second HP toolkit dogfood project, picked specifically to test transferability outside the solar/control-plane domain. *Real* stakes are zero (this is a thought-exercise); methodology stakes are high — we're testing whether the toolkit + workflow we built around the solar project actually generalize.

## The system, in plain language

An automated fishing rig:

1. Angler manually casts a hooked bait and sets the rod in the holder.
2. The reel controller tightens the line to a configured tension setpoint and arms.
3. Sensor watches line tension; waits for a sharp spike (= fish bite).
4. After a brief pause (let the fish swallow the bait), the rig does a sharp reel-in to set the hook.
5. If tension stays high (fish hooked), reel slowly to land the fish.
6. If tension drops (fish escaped) or any safety condition fires, back to idle / fault.

Single rod, single line, single fish at a time.

## Status

**Stage 1 — Context Diagram proposal in progress.** See [`00-context/proposal.md`](00-context/proposal.md).

## Planned structure (mirrors `examples/solar/`)

```
examples/fishing-rig/
├── dictionary.yaml                  (will be created after Stage 1 locks)
├── 00-context/
│   ├── proposal.md                  ✅ active (form-based review)
│   ├── naming-review.md             pending after lock
│   ├── context.{md,html,d2}         generated from dictionary
│   └── context-*.svg                rendered
├── 01-level1/                       (future) decomposition
└── ...
```

## Why this project

- **Domain-independent test.** Solar was sensor-→-cloud-platform; fishing rig is sensor-→-actuator on a tight real-time loop. Different shape, same HP method.
- **Tight state machine.** The fishing sequence (idle → armed → bite → hook-set → reeling → landed/fault) is *exactly* the kind of CSPEC HP was made for.
- **Small enough to finish.** Should be tractable to level-1 + CSPEC in 1–2 sessions.
- **Stakes are clean.** No risk of leaking IP from real work; no compliance entanglement.
