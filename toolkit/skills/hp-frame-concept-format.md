---
name: hp-frame-concept-format
description: Schema specification for `concept.md` — the Stage-0 framing artifact produced by `hp-frame` and consumed by `hp-init` (or equivalent). YAML frontmatter contract + prose body convention. Companion to `hp-frame.md`.
---

# concept.md format

`concept.md` is the artifact `hp-frame` emits at the project root before `hp-init` runs. It is **not** a spec, **not** a roadmap, **not** a feature list. It is the *framing* — the synthesis-level answers to "what is this thing for, who does it serve, what counts as working, what's in vs. out of our control" — captured precisely enough that an HP Stage 1 boundary pass can be seeded from it.

The frontmatter is the structured contract the consumer parses. The body is the conversation narrative — prose elaborations of each frontmatter field, in the order they came up during framing.

## Frontmatter contract

```yaml
---
concept: <slug>                          # required; lowercase-kebab, matches project name

# Why — synthesis (Rebovich Ch 2 §2.4, §2.2)
purpose: <prose>                         # required; one sentence. Why does this exist?
serves:                                  # required; the containing whole(s)
  - <prose item>

# What working looks like — CBEA-structured outcomes (Anderson & Webb Ch 4 §4.2.2.1)
outcomes:                                # required; ≥1
  - id: <kebab-slug>
    effect: <prose>                      # the change the user experiences
    standard: <prose>                    # the proficiency required to call it "working"
    conditions: <prose>                  # environmental variables that must hold

# Who cares — stakeholders with stakes (Anderson & Webb Ch 4 §4.3.1.1)
stakeholders:                            # required; ≥1
  - role: <prose>
    interest: <prose>                    # what they need from the outcomes
    contributes: <prose>                 # what they bring to the framing
    depends_on: <prose>                  # what they require to be served

# Boundary triage — terminator seed (Rebovich Ch 2 §2.2, Fig 2.4)
boundary:                                # required
  controlled:                            # what's yours to build
    - <prose item>
  influenced:                            # what you integrate with but don't own
    - <prose item>
  environment:                           # what you live with but can't influence
    - <prose item>

# What's already out there — reference portfolio (Anderson & Webb Ch 4 §4.3.2.5)
reference_portfolio:                     # required; ≥1
  - name: <prose>
    relation: <prose>                    # how it relates (vendor-native, adjacent, hobbyist, etc.)
    why_inadequate: <prose>              # optional — why what exists isn't enough
    why_relevant: <prose>                # optional — what it shows us

# Tensions surfaced + reframed (Rebovich Ch 2 §2.4.1, complementarity)
tensions:                                # optional; record those that came up
  - statement: <prose>                   # the apparent "A vs. B"
    reframed_as_and: <prose>             # optional; the "A and B" if found

# Slack indicators (Rebovich Ch 2 §2.4.2, interdependence)
slack_indicators:                        # optional
  - <prose item>                         # where optimization may hit a system-caused wall

# Variation recorded (Rebovich Ch 2 §2.5.4)
alternatives_considered:                 # optional but encouraged
  - approach: <prose>
    rejected_because: <prose>            # operative reason, not vague

# Where in the variation cycle (Rebovich Ch 2 §2.5.4.1, Table 2.1)
phase: <emergence | convergence | efficiency>  # optional
phase_rationale: <prose>                 # optional

# Bound the uncertainties (CBEA principle 5)
unknowns:                                # optional; things we can't currently answer
  - <prose item>
open_questions:                          # optional; decisions deliberately deferred
  - <prose item>
---
```

## Body convention

Below the frontmatter:

```markdown
# <Concept name> — concept framing

## Outcomes
(prose elaboration of each outcome — the conversation that produced effect/standard/conditions)

## Stakeholders
(prose elaboration of each stakeholder's role + stake)

## Boundary
(prose narration of the controlled/influenced/environment triage and how it was decided)

## Reference portfolio
(prose comparison + what each reference contributed to the framing)

## Tensions and reframings
(prose narration of each tension and the reframing conversation, if any)

## Open ends
(prose narration of unknowns + open_questions, in the order they came up)
```

The body is the human-readable record of the framing conversation. Future consumers (Stage-1 LLM passes, follow-up `hp-frame` runs, the user themselves a month later) read it for *why*; the frontmatter is for *what*.

## What does NOT belong in `concept.md`

- **Implementation choices.** "We'll use FastAPI" or "the database is Postgres" is a Stage-5 question, not a Stage-0 one. Redirect to HP.
- **Feature lists.** "The app will have a dashboard, an alerts page, and a settings screen" is structure, not framing. The dashboard is downstream of the outcome `homeowner-knows-when-it-stops`.
- **Roadmaps / phases / timelines.** "v1 does X, v2 adds Y" belongs in project planning, not the framing artifact.
- **Architecture diagrams.** Stage-0 is verbal. Diagrams are HP's job.
- **Spec language.** "The system shall…" wording is Stage-3+ rigor. `concept.md` is conversational.

If the user starts producing any of these during the framing interview, redirect: *"that's a Stage-1+ question; let's stay at the framing layer."*

## Worked example (excerpt)

```yaml
---
concept: solar-monitor

purpose: Keep a residential solar system producing — by closing the loop between
  an inverter that fails silently and a homeowner who'd otherwise not notice for weeks
serves:
  - the household's electricity economics
  - the homeowner's confidence in the install

outcomes:
  - id: knows-when-it-stops
    effect: Homeowner becomes aware that production has stopped
    standard: Within 5 minutes of cessation
    conditions: Residential install; home wifi available OR cellular fallback

stakeholders:
  - role: homeowner
    interest: Knows the system is working without having to check
    contributes: Defines what "working" means in their context
    depends_on: Outcomes 1 and 2

boundary:
  controlled:
    - the monitor service
    - the alerting layer
    - the baseline data store
  influenced:
    - Hoymiles cloud API surface + uptime
  environment:
    - internet outages
    - weather variability
    - inverter firmware updates

reference_portfolio:
  - name: Hoymiles S-Miles app
    relation: Vendor-native; what the homeowner has today
    why_inadequate: No alerting; daily-summary cadence; passive

tensions:
  - statement: Immediate push alerts vs. avoid alert fatigue
    reframed_as_and: Severity-tiered — push for outage, digest for dips

slack_indicators:
  - Polling cadence vs. Hoymiles API rate limits — if API doesn't support
    sub-15min, no code cleverness fixes that; would need vendor data export

alternatives_considered:
  - approach: Pure Hoymiles app push-notification workaround
    rejected_because: No control over alerting logic; vendor change risk

phase: emergence
phase_rationale: Multiple credible technical approaches; no obvious winner;
  low catastrophe risk from exploration

unknowns:
  - Whether Hoymiles' API supports sub-15-minute polling
  - Realistic alert false-positive rate in first 90 days

open_questions:
  - Historical production data — ours to keep, or always defer to Hoymiles?
  - Multi-system support v1 or punt to v2?
---

# Solar monitor — concept framing

## Outcomes

The homeowner gets timely awareness when the system stops producing...
```

## Consumer contract

`hp-init` (or the eventual equivalent consumer) reads `concept.md`'s frontmatter and seeds the new HP project's `dictionary.yaml` as follows:

| `concept.md` field | Becomes in `dictionary.yaml` |
|---|---|
| `boundary.influenced` + `boundary.environment` | Stage-1 terminator candidates |
| `outcomes[]` | Stage-1 flow candidates (the system-to-terminator interactions) |
| `purpose` + `serves` | `project.description` |
| `stakeholders[]` | Seeded into the dictionary's `actors:` or `terminators:` section depending on whether they consume the system or just have stake |
| `reference_portfolio[]` | Captured as `references:` for downstream proposal skills to consult |
| `tensions[]`, `alternatives_considered[]` | Become `adrs:` candidates (the consumer offers to promote each into an ADR via `hp-capture-adr` if it meets the three criteria) |
| `unknowns[]`, `open_questions[]` | Carried forward as `open_questions:` in the dictionary; resurfaced by Stage-1+ skills |

Fields the consumer does **not** read: `phase`, `phase_rationale`, `slack_indicators` — these are framing-layer artifacts useful to humans reading `concept.md` later, but HP's structural stages don't act on them directly.
