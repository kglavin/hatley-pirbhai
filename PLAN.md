# HP Toolkit — Plan & Document of Record

**What this is:** the living record of decisions, agreements, AI/methodology vocabulary, and open questions for the HP Toolkit project. It captures *what we've agreed on, what we're exploring, and what's still open*. The chat is ephemeral; this is durable. Updated as we go.

**Source of truth:** this file is canonical for project intent and state. Claude's memory under `~/.claude/projects/-home-kevin-hatley-pirbhai/memory/` supports cross-session continuity but is private to Claude; this file is shared.

---

## Status (2026-05-22)

**Where we are:** exploring the AI+HP workflow on a real dogfood project (residential solar local stack). Methodology has been grounded; dogfood project picked and framed; Context Diagram v0 drafted.

**Just finished:**
- Graphified both HP books — 187 nodes / 234 edges / 20 communities (see `graphify-out/`).
- Mapped Kevin's six AI-development pains 1:1 to specific HP work products (the "this is the right tool" moment).
- Picked the dogfood project (solar) and its system-boundary framing — (b)+(d).
- Drafted Context Diagram v0 (in chat; not yet on disk pending presentation-format decision).

**In flight right now:**
- Establishing this document of record (← this commit).
- Next: iterate on presentation format (Mermaid vs HTML5-interactive vs D2 vs Excalidraw vs Obsidian Canvas).
- After that: resolve the 6 Context Diagram v0 uncertainties; move to Stage 2 (level-1 DFD) on the solar dogfood.

---

## Purpose & Core Insight

**Purpose:** an AI-augmented toolkit around the Hatley-Pirbhai methodology (1988 + 2000 books) that makes the method's rigor affordable in 2026 — and uses HP as the substrate that disciplines AI-assisted development.

**Core insight (2026-05-21):** the six pains Kevin named about AI-assisted .md-based development map *exactly* onto HP work products that exist to prevent each one. The mapping is too clean to be coincidence:

| Pain (Kevin's wording) | HP work product that prevents it |
|---|---|
| No single northstar | Context Diagram + Architecture Context Diagram + level-1 DFD |
| 85% syndrome — features lost in the noise | Leveling rule + flow balancing + traceability matrix |
| Ratholing — one line becomes a subsystem | Leveling rule + abstraction discipline |
| Coherence / traceability / consistency lost | Requirements Dictionary + indexed entries |
| Interfaces lost in implementation | Architecture Interconnect Diagram (AID) + AIS interface contracts |
| Testability and consistency of testing lost | PSPECs + CSPECs + TSPECs + trace-from-tests |

**Project reframing.** This isn't "modernize HP" or "make HP cheap to draw." It's: **make HP the substrate that disciplines AI-assisted development — before code starts, and as code evolves.**

---

## Working Agreements

How we work, not what we build.

1. **Explore before build (greenfield/strategic).** For greenfield design work in this project, talk through who/what/how-used before proposing architecture. Architecture diagrams and decision-question batches belong after problem-space mapping. *(Lived: corrected when Claude jumped to a three-layer architecture sketch before users were named.)*

2. **Jokes are illustrations, not directives.** Colloquial examples (e.g., "the stereotypical vending machine `<smile>`") signal a *category*, not a specific exemplar to build for. Ask before committing to the literal reading. *(Lived: corrected when Claude built a four-step textbook ladder from a throwaway joke.)*

3. **IP firewall — guardrail project ↔ this toolkit.** Kevin's in-flight guardrail control plane project lives at `~/bluerock/cloudctlplane/`. Claude may inspect it read-only for *pattern-level* observations (proposal structure, directory shape, git history patterns) but **must not** write specifics (filenames, feature names, novel approaches, IP-bearing details) into the toolkit's code, docs, or memory. Two modes: *inspection* (read on guardrail repo) vs *toolkit* (design/build here). The firewall lives at the write boundary.

4. **Memory is for Claude; this file is for both.** Memory under `~/.claude/projects/-home-kevin-hatley-pirbhai/memory/` is Claude's continuity layer; the canonical durable record is this file.

5. **HP experience calibration.** Kevin's HP-method experience is **beginner-level** (last practiced more than 15 years ago); general engineering experience is high. Claude explains HP terminology inline on first use, anchors to modern analogs where possible, and signals explicitly when starting to taper teaching depth. Kevin can override the depth at any time. *(Tactic detail in Methodology Tactics > A.)*

---

## Decisions Made

Chronological, most recent first.

**2026-05-22**
- *Workshop / toolkit split.* Repo restructured to separate the **workshop** (where we develop the toolkit — PLAN.md, examples, graphify analysis, source PDFs) from the **toolkit** (the deliverable that ships to practitioners — under `toolkit/`). Files moved: `bootstrap.sh` → `toolkit/bootstrap.sh`; `reference-docs/HP_QUICK_REF.md` → `toolkit/reference/HP_QUICK_REF.md`. PDFs moved to `reference-docs/` (gitignored). Future Python package, skills, and pyproject.toml live under `toolkit/`.
- *Toolkit coding begun.* First code artifact: `toolkit/bootstrap.sh` — sets up uv (Python env manager) + d2 + mmdc (the renderers the methodology needs). User-space install, no sudo, idempotent. **This marks the transition from design conversation to actually building the toolkit.** Future `toolkit/pyproject.toml` and `toolkit/hp_toolkit/` Python package land on this foundation.
- *Document of record established.* This file (`PLAN.md`) is canonical for project decisions, in-progress vocabulary, and open questions.

**2026-05-21**
- *Dogfood system-boundary framing = (b) + (d).* "Medium scope" — orchestration software + local telemetry abstraction (the open-source stack replacing Hoymiles S-Miles Cloud). **First deep-dive = (d)** — the excess-solar diversion control loop, as the inaugural paired PSPEC + CSPEC exercise.
- *Dogfood project = residential solar local stack.* Hoymiles HMS-2000-4T-NA microinverters + DTU-Pro-S (or OpenDTU/AhoyDTU) + Chint DTSU666 meter + Victron MultiPlus / Cerbo GX. Real stakes (Kevin's actual planning conversation), architecturally mirrors his guardrail project without IP overlap, HP-shaped in every dimension.
- *First medium = smaller exploration project (not brownfield, not textbook examples).* Brownfield ingest is the eventual nut to crack, but not the first focus. Greenfield textbook examples (vending machine etc.) were Claude's over-literal reading of a joke; not the actual direction.
- *Direction = HP-inspired, modernized output.* Preserve the concepts (essential vs architecture, data vs control, four templates, mechanisms layer); render in modern notations (Mermaid / HTML5 / SVG / etc.), not strict 1988 bar notation.
- *Packaging = Claude Code plugin + Python package* (mirror graphify's pattern).
- *Primary user = Kevin himself* — senior engineer/architect who's seen UML, Agile, and "just-enough docs" all fail to scale, and wants rigor without expensive tooling. Other personas (aerospace SE, embedded teams, robotics startups, educators) are secondary at most.
- *Methodology grounded via graphify.* Both HP books processed — output at `graphify-out/`. God nodes (degree order): Architecture Model (27), Requirements Model (21), the two books themselves, Architecture Template, HP Methodology, DFD, CSPEC, CFD, Requirements Dictionary.

---

## Open Questions (resolve as we go)

**Context Diagram v0 — solar dogfood (drafted in chat 2026-05-22):**
1. DTU choice — official DTU-Pro-S only, OpenDTU/AhoyDTU only, or both as variants? Affects flow F2 (power-limit setpoints).
2. PG&E Utility Meter as a distinct terminator from PG&E Grid, or rolled together?
3. EV charger / future loads — model now as placeholder, or defer?
4. Weather forecast service — in or out for the b+d cut?
5. S-Miles Cloud as optional terminator (F8) — keep dashed/optional, or drop entirely?
6. Outage handling boundary — does the system **observe** outage state, **participate** in it (adjust setpoints during island mode), or **stay out of the way**? Big implication for the CSPEC.

**Presentation format (in flight):**
- Mermaid (rendered) vs HTML5-interactive (Cytoscape/D3/vis) vs D2 vs Excalidraw vs Obsidian Canvas vs static SVG.
- Working hypothesis: model = source of truth (JSON/YAML); multiple derived views, each best for a different moment.

---

## AI Moves Catalog (in progress)

The toolkit's vocabulary. Three tiers: mundane → genuinely new → transformative. The transformative tier is where the most value lives.

**Mundane but high-volume — saves typing, makes HP affordable**
- **Auto-fill / Complete** — draft PSPECs for the bubbles that don't have them yet.
- **Translate** — model ↔ Mermaid / NL summary / test plan / code skeleton.
- **Explain on demand** — "what does this CSPEC mean?" / "blast radius if I add this flow?"

**Genuinely new — couldn't do with pen and paper**
- **Interview / Extract** — turn transcripts, prose, meeting notes into draft HP entities.
- **Propose** — "here are 4 candidate level-1 bubbles; pick or correct."
- **Challenge** — "you said one bubble, but described three transformation patterns. Did you mean to merge them?"
- **Surface Ambiguity** — explicitly flag choices made under uncertainty; invite human steering. *(Added 2026-05-22 during Context Diagram v0 — the numbered "things I'm uncertain about" list was doing real work.)*
- **Semantic completeness check** — "CSPEC moves to Ready on event X; Bubble 4's PSPEC needs Bubble 3 first. Possible race."
- **Cross-model reasoning** — "your Coin Acceptor is like a Card Reader in another project; apply the same TSPEC?"

**Transformative — changes what HP fundamentally is**
- **Trace evolution** — when a proposal / note / PR arrives, figure out *which part of the model it changes*; propose the diff.
- **Drift detection** — compare model against code / schema / runtime; flag divergence as work items.
- **Refactor coaching** — "this bubble is doing two things; HP discipline says split."

---

## Workflow Strawman

Current hypothesis: **the toolkit's job is mostly to ask good questions and refuse to proceed, not generate.** Inversion of the typical AI-in-.md-proposal flow where the AI is eager to write code or text. Here, the AI is patient, probing, and adversarial about completeness.

| Stage | What happens | AI moves used |
|---|---|---|
| 1. Establish context | Tool asks discovery questions OR extracts from existing prose; proposes Context Diagram. *Refuses to proceed until accepted.* | Interview / Extract / Propose / Surface Ambiguity |
| 2. Level-1 DFD | Tool proposes 3–5 internal bubbles + flows. *Refuses to go deeper into any bubble until level 1 is accepted.* (Anti-rathole mechanism.) | Propose / Challenge |
| 3. Identify control bubbles | For each bubble: transformational or stateful? CSPEC with STD where needed. | Propose / Challenge |
| 4. PSPECs for leaves | Draft short PSPECs for terminal bubbles. | Auto-fill / Translate |
| 5. Architecture model | Wrap in the four templates: Input / Output / UI / Self-Test. | Propose |
| 6. Mechanisms (2000-book layer) | What patterns? Polling/push, event-driven, fault recovery, etc. | Propose / Cross-model |
| 7. Validate | Flow-balance / trace coverage / completeness checks. *Always report numbers.* | Semantic completeness check |
| 8. Implement | Code skeleton from model, or hand model to coding agent. | Translate |

Stages 1–4 make the model fail to be silent on the hard parts. Stages 5–6 give it physical shape. Stage 7 is the discipline gate. Stage 8 is the payoff.

**Open question on the strawman:** stages here are linear, but real design isn't strictly waterfall. The toolkit probably needs to support iterating between Stage 2 and Stage 4 freely — discovering at the leaves that the level-1 was wrong is a normal and important event.

---

## Methodology Tactics (draft for eventual `skills/*.md`)

These are the *meta-tactical patterns* for how an AI applies the methodology — distinct from the AI Moves Catalog above. **Moves name *what* the AI does** (Propose, Challenge, Auto-fill, …); **tactics name *when, how, and why*** to apply them. This section is the working draft of what will eventually become the toolkit's skill definitions — per-stage `skills/*.md` files in the eventual Claude Code plugin distribution. Captured here so the meta-knowledge doesn't live only in chat or in Claude's memory.

Each tactic notes what it implies for the toolkit's eventual implementation.

### A. Interaction Posture

**Check existing context before interviewing.**
If rich technical material is already available (transcripts, prior docs, code, prose pasted into chat), default to **Propose + Extract** rather than 10 discovery questions. Discovery interviews are for *gaps*, not for re-asking what the human already typed. *Implication:* the toolkit's Stage 1 interview pass parses what's available first, then asks only about what's missing or ambiguous.

**Calibrate teaching depth to the user's HP experience.**
HP-method experience is *independent* of general engineering experience. A senior engineer with 25 years in systems and no recent HP practice is technically sophisticated but a *beginner at HP* — vocabulary, artifacts, and relationships need fresh introduction. At project start, ask the user to self-assess (or detect from interaction). Three baselines:
- **Beginner** — never practiced HP, or rusty (>5 years since active use). Explain HP terminology inline on first use; anchor to modern analogs (e.g., *"a PSPEC is like a docstring-plus-contract for a leaf process"*); briefly explain relationships (*"CSPECs partner with DFDs to handle state"*).
- **Intermediate** — knows the vocabulary, rusty on application. Brief tooltip-style explanations on first use; otherwise use HP terms freely.
- **Expert** — actively practiced recently. Use HP vocabulary fluently; explain only on request.

**Taper over the project's life.** As the user demonstrates fluency (uses HP terms correctly, picks up the workflow's rhythm, stops asking "what's an AID?"), reduce teaching depth incrementally. **Always tell the user this is happening** — explicitly, e.g., *"I'm going to start using these terms without re-explaining them; ask if you want me to keep teaching at the current depth."* Transparency preserves agency.

**Always honor the user's override.** A user who asks for re-teaching at any point gets it without friction.

*Implication for the toolkit:* per-user-per-project state includes (1) a self-declared or inferred HP-experience level, (2) a vocabulary log of HP terms the user has used correctly, (3) explicit override settings. Recalibration signals: correct usage → level the user up; explicit confusion ("what's X?") → level down; user override always wins.

*Lived 2026-05-22:* Kevin self-identifies as **beginner** (last practiced HP 15+ years ago). Claude's responses through this date had been jargon-heavy — PSPEC/CSPEC/AFD/AID/TSPEC used without inline explanation, with only the end-of-file Glossary as scaffold. Adjusting going forward: HP terms get explained on first use, anchored to modern analogs, with explicit taper signals later in the project.

**Surface Ambiguity, not yes/no.**
When the AI makes assumptions, do not hide them. Surface them as a numbered list of *axes of decision* that the human can steer along. A "things I'm uncertain about" list is more useful than a binary confirmation request, because it tells the human *which dimensions matter*. *Lived 2026-05-22 with the six Context Diagram uncertainties.* *Implication:* every proposal artifact ships with an explicit ambiguity sidebar.

**Refuse to proceed until the prior stage is locked.**
At each methodology stage (Context, Level-1 DFD, CSPECs, …), the AI's discipline is partly *not advancing* until the prior level is signed off. This is the structural anti-rathole mechanism — discipline as a property of the toolkit, not human willpower. *Implication:* the toolkit literally refuses to draft level-N+1 content until level-N is accepted, and tells the human *why*.

**Explore before build (greenfield/strategic).**
For greenfield design work, talk through who/what/how-used before proposing architecture. Architecture diagrams and structured decision batches belong *after* problem-space mapping, not as the way to organize early exploration. *(Also a working agreement; restated here as a tactic.)*

**Treat colloquial examples as categories, not exemplars.**
Hear the *category* an example illustrates, not the specific instance. "The stereotypical vending machine `<smile>`" means "a small bounded problem," not "build a vending machine specifically." Confirm before committing to the literal reading. *(Also a working agreement; restated here as a tactic.)*

### B. Artifact Discipline

**Make rigor measurable.**
Every validation reports a *number*. Coverage percentages (Trace coverage, Interface coverage, Test coverage, PSPEC completeness, flow-balance %, etc.) are progress metrics, not just status indicators. Avoid "looks good" — quantify or it didn't happen. *Implication:* the toolkit's validator always emits percentages; progress is the percentage climbing toward 100.

**Model = source of truth; views are derived.**
Storage form (JSON / YAML / markdown-with-frontmatter) is separate from presentation form (Mermaid / HTML5-interactive / Excalidraw / SVG / D2 / Canvas). The toolkit maintains the model; multiple views render on demand, each best for a different moment. *Implication:* the toolkit's data model is notation-neutral; renderers are pluggable.

**Reflect on each significant move; let the methodology evolve.**
Each substantive AI move ends with a brief reflection: *what moves were used, what worked, what was missing*. Missing moves get added to the AI Moves Catalog. Working tactics get added to this section. **The methodology improves *through* its use, not separately.** *Lived 2026-05-22 — the "Surface Ambiguity" move was added to the catalog mid-flight after I noticed I'd been using it unnamed.* *Implication:* a "reflect" step is built into the toolkit's workflow — not optional, not skippable on busy days.

### C. Knowledge Work

**Brownfield ingest is semantic, not structural.**
When extracting HP entities from existing prose (proposals, docs, code comments), do not rely on header patterns (`## Test`, `## Architecture`) — most projects don't have consistent templates. Use LLM semantic understanding: *what is this about, what flows does it imply, what interfaces does it touch, what state does it manage*. *Implication:* the ingest subsystem is LLM-driven, not regex-driven.

**Pattern-level observations only when inspecting firewalled material.**
When inspecting code or docs from a project under IP firewall, derive *structural patterns* (file counts, directory shapes, naming conventions, section frequency, commit density) — not *specific content* (feature names, novel approaches, IP-bearing details). The discipline lives on the **write boundary** — what gets recorded into toolkit artifacts — not on the read boundary. (You can't unsee what you read; you *can* control what you write.) *Implication:* inspection-mode tools never emit content into versioned toolkit artifacts without a pattern-translation pass.

**Code structure ≠ requirements structure.**
A flow-organized HP graph and a directory-organized code graph are *different views of the same system*. Both have value. The toolkit needs both, with traceability across them — answering "which code modules implement this requirement" and "which flows are touched by changes in this directory." *Implication:* brownfield ingest produces *two* graphs and cross-links them.

**Drift detection is the primary ongoing job after first ingest.**
Once a model exists, the long-term value of the toolkit is keeping it aligned with code / schema / runtime, not the initial reverse-engineering. Implementation activity tends to *accelerate*, not stabilize; drift is continuous. *Implication:* the toolkit's compute budget after first ingest is mostly spent on incremental sync, not on re-ingesting from scratch.

---

## Artifacts Index

Where things live in this repo.

| Path | What it is | Status |
|---|---|---|
**Workshop (repo root) — where we develop the toolkit:**

| Path | What it is | Status |
|---|---|---|
| `PLAN.md` | This file — plan / document of record | Active |
| `examples/solar/` | Dogfood project artifacts — Context Diagram, DFDs, CSPECs, PSPECs as they emerge | Active |
| `examples/solar/views/` | Candidate presentation experiments for Context Diagram v0 (Mermaid `.md`, HTML5 Cytoscape `.html`, D2 `.d2`) | Active — under review |
| `graphify-out/` | Knowledge graph of both HP books (187 nodes / 234 edges / 20 communities) | One-time workshop reference; see `graphify-out/GRAPH_REPORT.md` |
| `reference-docs/` | Workshop reading aids — source PDFs (1988 and 2000 HP books). `.gitignore`'d. | Local-only |
| `proposals/` | (empty, placeholder) | Reserved |

**Toolkit (`toolkit/`) — the deliverable that ships to practitioners:**

| Path | What it is | Status |
|---|---|---|
| `toolkit/README.md` | Practitioner-facing entry point | Active |
| `toolkit/bootstrap.sh` | Environment setup script — installs uv, d2, mmdc to user space. Idempotent. | Active |
| `toolkit/reference/HP_QUICK_REF.md` | HP method vocabulary card (60+ terms with modern analogs, cross-links). The deep-link target Claude uses when introducing HP terminology in chat. | Active |
| `toolkit/pyproject.toml` | (planned) Python project | Not yet created |
| `toolkit/hp_toolkit/` | (planned) Python package — model core, validators, renderers | Not yet created |
| `toolkit/skills/` | (planned) Claude Code skill files (one per workflow stage) | Not yet created |

---

## Dogfood Project — Solar Local Stack

**Intent (clarified 2026-05-21):** a **local-first, open-source orchestration layer** that does:
1. **Dynamic excess-solar diversion** — sense surplus via Chint meter; command Victron to absorb into battery; keep PG&E net export near zero (PG&E non-export compliance + avoid curtailment waste).
2. **Auto-discharge at night** — Victron ESS keeps net grid import near zero until battery SoC minimum.
3. **Outage handling** — Victron's <20 ms transfer switch + AC-coupled microgrid with frequency-shift signaling to throttle Hoymiles during outages.

Explicitly **replaces S-Miles Cloud dependence**. Compliance constraints: PG&E zero-export rule + NEC 690.12 rapid shutdown.

**Hardware (off-the-shelf — NOT what we're designing):**
- Hoymiles HMS-2000-4T-NA microinverters (Sub-1G RF telemetry)
- Hoymiles DTU-Pro-S (official, restricted) **or** OpenDTU/AhoyDTU (ESP32-based open-source replacement that exposes local MQTT + HTTP/JSON)
- Chint DTSU666 utility-grade meter (Modbus RTU over RS485)
- Victron MultiPlus inverter-charger + Cerbo GX (Venus OS, two-way MQTT, Modbus TCP)
- Home Assistant or Node-RED for orchestration

**What we ARE designing:** the **control-and-observability stack on top** of that hardware. Per the (b)+(d) framing: orchestration software + local telemetry abstraction layer; first concrete deep-dive is the excess-diversion control loop.

**Already-surfaced requirements (from Kevin's planning chats, unprompted):**
- Non-cloud-dependent / open-source monitoring (S-Miles + paid API tier is the explicit pain)
- PG&E zero-export compliance (CT direction, dedicated voltage taps, real-time direction detection)
- Polling cadence: 30 s for official DTU-Pro-S; near-realtime via OpenDTU
- Dynamic-balance control loop with sub-second latency budget for surplus diversion
- Multi-vendor integration: Hoymiles RF, Chint Modbus RTU, Victron Modbus TCP / MQTT
- 4-step diversion loop already sketched in prose ("read net grid → trigger diverter → command charger → balance point") — **this is an early-draft PSPEC waiting to be formalized**

**Safety caveat:** if the design ever touches NEC compliance, grid interconnect, or anything requiring an electrician / inspector signoff, a real licensed reviewer must be in the loop before hardware is installed. The model can be developed fearlessly; physical implementation needs human authority. The toolkit must not pretend to substitute for that.

**Current artifacts:** Context Diagram v0 drafted in chat 2026-05-22; not yet on disk pending presentation-format decision. To be saved under `examples/solar/` once presentation is settled.

---

## Brownfield Notes (firewalled, IP-free)

Pattern-level observations from a one-time inspection of Kevin's in-flight guardrail control plane. Inform the toolkit's eventual brownfield-ingest design *abstractly*. No specifics from that project are recorded here or elsewhere in the toolkit.

- AI-assisted projects accumulate proposals in **federated subsystem folders**, not a centralized location. Brownfield ingest must discover proposal directories anywhere in the tree.
- **No template uniformity.** Each proposal is freeform; heading text rarely repeats across proposals. Brownfield ingest cannot rely on structural cues; it must semantically extract.
- **Proposal size has huge variance** — note-shaped to mini-architecture-shaped. The tool must handle both.
- **Section coverage is heavily skewed.** Implementation/Architecture sections are common; Test, Trace, Interface, and Acceptance sections are typically present in well under 20% of proposals. **The six pains are measurable as percentages** — Trace coverage, Interface coverage, Test coverage start near zero and need to climb. This is also a clean progress metric.
- **Commit-to-proposal linkage is sparse.** Most implementation work has no paper trail back to a stated intent.
- **Lifecycle conventions emerge organically.** Teams invent their own "retired/deprecated" conventions. The toolkit must model proposal lifecycle states (proposed → active → fallow → satisfied → superseded), not just current state.
- **Code-organized graphs ≠ requirements-organized graphs.** Code clusters by directory; HP clusters by flow boundary. The toolkit needs both views with traceability across them.
- **Commit velocity tends to accelerate**, not stabilize. Drift detection is the *primary ongoing job* after first ingest.

**Design implications for brownfield ingest (deferred to phase ≥ 5):**
1. Auto-discover federated `proposals/`-shaped directories.
2. LLM semantic extraction, not structural parsing.
3. Treat each top-level subsystem with its own proposals as a candidate level-1 DFD bubble.
4. First-class lifecycle states.
5. Cross-link code-graph and HP-graph with traceability queries across.
6. Section coverage as a measurable progress metric.

---

## Glossary

For the **full HP method vocabulary** (60+ entries, with modern analogs and cross-links), see [`toolkit/reference/HP_QUICK_REF.md`](toolkit/reference/HP_QUICK_REF.md). That's the deep-link target Claude uses when introducing terms in chat.

This section is just the **project-specific** vocabulary (dogfood domain + project shorthand):

- **HP** — Hatley-Pirbhai (1988 method, *Strategies for Real-Time System Specification*)
- **HHP** — Hatley-Hruschka-Pirbhai (2000 process book, *Process for System Architecture and Requirements Engineering*)
- **(b)+(d)** — current scope framing for the solar dogfood: orchestration + local telemetry abstraction layer, with the diversion control loop as first concrete deep-dive
- **S-Miles** — Hoymiles' cloud monitoring platform (the thing the dogfood project is replacing)
- **DTU** — Data Transfer Unit (Hoymiles gateway between microinverters and network)
- **PG&E** — Pacific Gas & Electric, Kevin's California utility (zero-export tariff applies)
- **NEC 690.12** — National Electrical Code provision for rapid shutdown of PV systems
- **ESS** — Victron's Energy Storage System assistant (handles night-time discharge, grid setpoint)
- **MPPT** — Maximum Power Point Tracking (per-channel solar optimization)
- **SoC** — State of Charge (battery)

---

*This file is a living document. Updated as we make decisions or learn things. Last update: 2026-05-22.*
