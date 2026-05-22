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
- *Toolkit code begun in earnest — first slice.* `toolkit/pyproject.toml` (uv-managed; pydantic + pyyaml), `toolkit/hp_toolkit/__init__.py`, `toolkit/hp_toolkit/model.py` (Pydantic schemas for Project / Entity / Flow / Edge + enums for kinds), `toolkit/hp_toolkit/load.py` (read dictionary.yaml → validated Project), `toolkit/scripts/check_dictionary.py` (sanity script with reference-integrity checks). `uv sync` works; the check script loads the solar dogfood dictionary (27 entities, 17 flows, 2 edges) and reports all references resolve. **First validation of the toolkit catching a hand-written artifact bug:** `version: 0.1` in dictionary.yaml was being parsed as float by PyYAML; Pydantic flagged the type mismatch. Fixed in both places (quoted in YAML + `coerce_numbers_to_str=True` on the model). Validators, renderers, more skills next.
- *Generic renderer extended to level-1 DFD; Cytoscape DFD HTML live.* `render/cytoscape.py` gained `render_dfd_elements(project, parent_id)` and `wrap_dfd_html(project, parent_id)` — same HTML template as Context, view-specific navigation (↑ Parent), legend (process/brain/store/etc.), brain bubbles get `decomposable` + drill target `cspecs/<id-without-proc>/cspec.html`. Styles consolidated into `_ALL_STYLES_JSON` (covers system/process/process-brain/process-optional/datastore/terminator variants/data/control/data-optional/control-optional/physical_ac_power/physical_dc_power/physical_interaction/decomposable marker/selected). `scripts/render_project.py` now renders level-1 DFD whenever the project has internal processes — discovered automatically via `has_internals` detection. Both fishing-rig and solar render end-to-end through the same script: 5 Context artifacts + 5 level-1 DFD artifacts each. **Stage 2 fishing-rig dogfood complete**; the only remaining renderer gap is CSPEC HTML (Mermaid + D2 + SVGs exist; HTML is solar-handwritten and not yet generic).
- *Stage 2 fishing-rig: locked.* 5 internal processes + 1 data store + 7 internal flows + 5 boundary-flow refinements added to `dictionary.yaml`. Naming review resolved with all defaults (no renames). Validates clean: 12 entities + 12 flows + 100% description coverage.
- *Toolkit transferred to a fresh project (transferability test passed).* Created `examples/fishing-rig/` — an automated fishing rig (sensor: line tension, actuator: reel motor, control: bite-detection state machine). Form-based Stage-1 proposal locked with all 7 defaults accepted. `examples/fishing-rig/dictionary.yaml` hand-written from scratch (6 entities, 5 flows, 2 edges). **The toolkit validated and rendered the new project end-to-end without modification to schema or loader.** Caught two real gaps that needed minimal fixup: (1) added `EdgeKind.PHYSICAL_DC_POWER` and `PHYSICAL_INTERACTION` for the battery edge and fish-to-line edge (one-line model.py change + parameterized d2.py `_edge_decl`); (2) parameterized `cytoscape.wrap_context_html` with `drill_target` argument and dynamic nav/legend building (was hardcoded for solar). New `scripts/render_project.py <dir>` is the generic entry point — discovers structure from the dictionary (`has_internals` query) and renders Context accordingly. Solar regression still works. **Conclusion:** the dictionary-schema-as-source-of-truth approach generalizes. Level-1 + CSPEC rendering still uses solar-specific `render_dogfood.py`; that migration is the next slice when fishing-rig grows a level-1 DFD.
- *SVG orchestration live — visual rendering loop closed.* `render/svg.py` provides `render_d2_to_svg(src, out)` and `render_mermaid_to_svg(src, out)` — invoke `d2` and `mmdc` binaries via `subprocess`. Auto-locate binaries in PATH and `~/.local/bin`. Auto-detect `.puppeteer-config.json` (for Ubuntu 23.10+ sandbox) relative to the package. Handle mmdc's `-1` suffix transparently. Raise `FileNotFoundError` if a binary isn't installed (point at `bash toolkit/bootstrap.sh`). `render_dogfood.py` now writes 12 files for the solar dogfood: source `.mmd` / `.d2` / `.html` (three views × three artifact kinds = 9 sources) plus 6 SVGs (Mermaid + D2 for each artifact, totalling 343 KB across all images). End-to-end pipeline lives: **dictionary.yaml → generated sources → static SVG images**, run via `uv run python scripts/render_dogfood.py`.
- *Cytoscape rendering live for Context view.* `render/cytoscape.py` produces the Cytoscape elements list (model-driven part) and wraps it in a self-contained HTML workspace via `wrap_context_html(project)` — full Cytoscape script + side panel + navigation links (Drill / Dictionary / HP Reference) + legend + tap/dbltap handlers for the single-click-inspect / double-click-drill semantics. Output is 14.5 KB self-contained HTML; opens in any browser, no install. `render_dogfood.py` writes `context.generated.html` as a sidecar. DFD + CSPEC Cytoscape HTML deferred to next slice — same wrapper template pattern, different style arrays + legends + element generators.
- *State machine renderer live — CSPEC as third generated artifact kind.* Schema extended: new `Transition` model (id, source_state, target_state, parent_machine, event, label, action, guard) collected under `Project.transitions`; new `is_initial: bool` field on `Entity` marks initial sub-states for composites and the machine entry point. Dictionary populated with all 16 Energy Manager transitions and 4 `is_initial` markers (Initializing as CSPEC entry; Idle as initial of GridTie; BatteryDischarge of Island; TelemetryFault of Fault). `validate.py` extended to check transition reference resolution. `render/mermaid.py:render_state_machine()` produces hierarchical Mermaid `stateDiagram-v2` with composite-state blocks and substate-to-substate transitions emitted inside their parent composite. `render/d2.py:render_state_machine()` produces D2 with composite containers and dotted-notation cross-container references. `scripts/render_dogfood.py` now diffs CSPEC against hand-written `cspec.md` + `cspec.d2`. **Caught more drifts:** transition labels differ between hand-written (longer, e.g. "Victron mode = island\n(grid lost)") and dictionary (terser, e.g. "Victron → island"); plus the hand-written D2 pointed `Initializing → Fault` (the composite) while the dictionary models the more specific `Initializing → TelemetryFault` (which the action's "startup-fault" alert actually corresponds to). Dictionary semantically more correct on that one.
- *Level-1 DFD renderer live.* Added `refined_source` / `refined_target` to the Flow schema in `model.py`. Populated F1–F8 in `dictionary.yaml` with their level-1 internal endpoints (e.g., `flow_f1_inverter_telemetry.refined_target: proc_acquire_telemetry`). Added `render_dfd(project, parent_id)` to both `render/mermaid.py` and `render/d2.py` — emits internal processes (with brain/optional/normal styling per `needs_cspec` / `optional`), data store, terminators, boundary flows refined to internal endpoints, internal flows, physical edges, classDef styling. `scripts/render_dogfood.py` now diffs level-1 too. **Caught 8 label drifts** between dictionary (full labels: "F1: per-channel telemetry") and hand-written `dfd.md` (abbreviated: "F1: telemetry") — these were level-1 compactness abbreviations baked into the hand-written diagram. **Deferred resolution:** add `short_label:` field to schema for per-level labeling; until then, dictionary's full labels are canonical. Internal-flow label drifts caught too (`"writes"`/`"reads"` vs dictionary's `"normalized state"`/`"system_state"`).
- *Renderers begun — level-0 Context Diagram now generated from the dictionary.* `hp_toolkit/render/mermaid.py` + `hp_toolkit/render/d2.py`. `scripts/render_dogfood.py` writes `*.generated.{mmd,d2}` sidecars and diffs against hand-written. Output is **deterministic** (same dictionary → same source bytes). The renderer caught a real drift on first run: `F8` label was `"optional telemetry fwd"` in the dictionary but `"optional telemetry forward"` in `context.md` — fixed in the dictionary (intent-aligned). Generated sources differ from hand-written only stylistically (long stable_ids vs short readable IDs; alignment whitespace). Companion skill `hp-render` drafted. **Level-N≥1 DFD rendering deferred** pending dictionary schema extension for boundary-flow refinement (which internal process at level N+1 consumes each level-N boundary flow). **State machine rendering deferred** pending `transitions:` schema addition.
- *Validators live in `hp_toolkit/validate.py`.* Four validators run from `python -m hp_toolkit.validate <path>` or programmatically via `from hp_toolkit import validate`: (1) **reference integrity** (parent / source / target resolve), (2) **hierarchy consistency** (parent_state only on states, etc.), (3) **coverage metrics** (description %, flow medium %, flow notes %, counts by kind/level — the "make rigor measurable" payoff with ASCII-bar output), (4) **orphan detection** (entities referenced by no flow). Dogfood passes: 100% description coverage, 27 entities / 17 flows / 2 edges, no errors/warnings. Companion skill `hp-validate` drafted in `toolkit/skills/`. **Renderers next.**
- *First skill drafted: `hp-confirm-naming`.* `toolkit/skills/hp-confirm-naming.md` — the most-validated pattern from the dogfood, codified as a Claude Code skill with frontmatter, behavior spec, discipline rules, and links back to PLAN.md tactics. Skills directory has a README cataloging planned skills (`hp-propose-context`, `hp-propose-decomp`, `hp-propose-cspec`, `hp-propose-pspec`, `hp-validate`, `hp-render`, `hp-init`, `hp-ingest`).
- *Stage 3 state machine locked — Energy Manager CSPEC.* Hierarchical state machine: 4 top-level modes (Initializing / GridTie / Island / Fault) + 9 sub-states. Hybrid event-driven + 1 Hz tick. Trust Victron's <20 ms transfer (no debounce). 13 state entries added to `dictionary.yaml` under a `level: 2` section with `parent` + `parent_state` hierarchy fields. All three views rendered: `cspec.md` (Mermaid stateDiagram-v2 + transitions table + process controls), `cspec.html` (Cytoscape with compound parent nodes for modes), `cspec.d2` (D2 with containers). Two form-based reviews (decomposition + naming) → 2 round-trips, single rename (`ACCoupledSolar` → `SolarAssist`). The `dfd.html` Energy Manager drill-link now resolves to `cspec.html`. Remaining sub-stages: event glossary + action specs.
- *Workspace as hypertext.* HTML workspaces now carry navigation links — vertical (level-up / level-down via decomposable bubbles), to `dictionary.yaml`, and to `HP_QUICK_REF.md` entries by entity kind. Decomposable nodes get a double-border marker. Demonstrated on `00-context/context.html` (sys_root → level-1 dfd) and `01-level1/dfd.html` (Energy Manager → future Stage-3 CSPEC; parent link → level-0). New tactic in Methodology Tactics > B. Generalizes to every future level. *Implication: same pattern shipped with the eventual toolkit — every generated workspace carries the links automatically based on dictionary + level metadata.*
- *Stage 2 complete — level-1 DFD locked.* The first decomposition of `sys_root` into 5 + 1 (optional) internal processes plus the `System State` data store is locked. Naming review resolved with two renames (`proc_compute_balance` → "Energy Manager"; `proc_handle_user_input` → "Handle Input"); all other working names kept. All three views rendered: `dfd.md` (Mermaid + balancing check + internal-flow summary), `dfd.html` (interactive Cytoscape workspace), `dfd.d2` (declarative), plus `dfd-mermaid.svg` and `dfd-d2.svg`. Dictionary now has 13 entities (7 level-0 + 6 level-1) and 18 flows (8 level-0 + 9 level-1, plus 2 AC edges). The form-based review pattern worked end-to-end: 2 decisions screens (decomposition + naming), 2 round-trips, no chat back-and-forth. Next: Stage 3 — CSPEC for `Energy Manager`.
- *Markdown Preview Enhanced as the recommended viewer.* The VSCode extension **Markdown Preview Enhanced (MPE)** is the right environment for working with toolkit artifacts. It (a) renders embedded SVGs (proposal diagrams, recap diagrams) natively, (b) renders fenced Mermaid blocks natively, (c) **lets the user click `[ ]` checkboxes in the preview to toggle them** — turning form-based reviews into click-to-decide instead of edit-raw-markdown. Confirmed by Kevin 2026-05-22: "the radio button changes are possible which reduces friction." The form-based review tactic depends on this affordance; without it, users would have to edit raw markdown to toggle decisions. Worth surfacing in toolkit/README.md as a prerequisite when the toolkit ships.
- *Propose graphically before prose.* When proposing a structural artifact (decomposition, control logic, architecture), ship a draft diagram first; let descriptive prose be supporting detail in a collapsible block. New tactic in Methodology Tactics > B. Applied retroactively: the level-1 decomposition in `01-level1/proposal.md` is now a rendered `proposal-dfd.svg` + compact role/flow tables + collapsible detail, replacing the 60-line dense paragraph block. Pairs with [Recap with diagrams] — together: diagrams everywhere structure matters.
- *Recap with diagrams, not text walls.* When working at level N, recap level N-1 by embedding its rendered SVG, not by reproducing its content as text/table. New tactic in Methodology Tactics > B. Applied retroactively: the level-1 proposal's "Context recap" section now embeds `../00-context/context-mermaid.svg` instead of duplicating the 8-flow table. Caught by Kevin before engaging with the proposal — instinct that the duplication was wrong was correct.
- *Form-based batch review tactic.* When the AI needs multiple decisions from a human (naming, ambiguity, decomposition choices), do not iterate chat-by-chat — emit a single form file (markdown checkboxes or YAML), human fills out once, saves, pings. AI applies in one pass. New tactic in Methodology Tactics > A. *Lived through the level-0 naming review: 11 round-trips that would have been 1.*
- *Dictionary materialized.* `examples/solar/dictionary.yaml` written — HP's Requirements Dictionary in YAML form, populated with all level-0 entities and flows from the resolved naming review. First concrete realization of the per-project dictionary architecture. Future renames edit this file; renderers will read from it.
- *Stage 2 begun.* Created `examples/solar/01-level1/` with a level-1 DFD proposal (checkbox-form for decomposition decisions). Decomposes `sys_root` into internal bubbles + internal flows.
- *Repo hierarchy mirrors HP hierarchy.* The file system is now organized to reflect HP's containment structure 1:1. Numeric-prefixed level directories (`00-context/`, future `01-level1/`, `02-level2/`, `architecture/`, `mechanisms/`) sort the listing in HP order. Same convention applies to the toolkit's eventual project-scaffolding output. Immediate consequence: all Context Diagram v0 artifacts moved from `examples/solar/views/` and `examples/solar/` → `examples/solar/00-context/`. Naming reviews are per-level too. See Methodology Tactics > B.
- *Naming dictionary + Confirm Naming AI move.* Two related insights surfaced during the presentation experiment: (1) **Names are first-class artifacts that need a dictionary** — every entity gets a stable_id + human-readable label; artifacts reference by stable_id; rename = edit one dictionary entry, regenerate everything. Kevin's framing: "mapping db." This is HP's Requirements Dictionary in modern form. (2) **New AI move added: Confirm Naming** — after any proposal that introduces named entities, list them with provenance and invite explicit rename before they harden. *Surfaced when Kevin caught Claude embedding "(b+d scope)" — internal chat shorthand — into a permanent diagram label.* See Methodology Tactics (Sections A and B) and AI Moves Catalog.
- *Workspace reframing.* The HTML5 interactive view feels like a *graphical IDE*, not just a "view." Workspaces produce their own artifacts (layout positions, annotations, view state) — a layer between model and rendered output, worth pinning in git as "the way we look at this." See Methodology Tactics > B for the layered layout (`model.yaml` → `views/*.layout.json` → rendered `*.svg`/`*.html`).
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
- 2026-05-22 update: Kevin's read after seeing rendered versions of all three — "all three are good; the HTML5 begins to look like a graphical IDE." Workspace reframing captured.

**Dictionary / naming architecture (deferred to Stage 2):**
- Stable-id format — kebab-case? snake_case? prefix-by-kind (e.g., `term_*`, `flow_*`, `sys_*`)?
- Dictionary file format — one `dictionary.yaml` at project root? per-stage files? embedded in `model.yaml`?
- Provenance fields per entry — what to track (extracted-from / AI-inference / user-defined / default).
- Rename command semantics — regenerate just the views, or also rewrite the model file? (Probably both, with backup.)
- Defer detailed design until we hit enough entities to need it (likely Stage 2 — level-1 DFD on solar dogfood, with ~10–15 internal bubbles + dictionary entries for every flow).

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
- **Confirm Naming** — after any move that introduces named entities, list them with provenance ("extracted from your paste"; "AI inference"; "your wording, kept"); invite accept / rename / alias on each. Don't bury chat shorthand into permanent artifacts. This is HP's Requirements Dictionary in operation. *(Added 2026-05-22 — Kevin caught Claude embedding "(b+d scope)" — internal conversation shorthand — into a permanent diagram label.)*
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

**Batch human review via files, not chat round-trips.**
When the AI needs multiple decisions from a human (naming, ambiguity resolution, scope choices, decomposition), do **not** iterate decision-by-decision through chat. Round-trip cost is high (each answer is a separate LLM invocation), the human's mental context fragments, and total wall-clock time grows linearly with the number of decisions. Instead: emit a single **form file** — markdown task list with `[ ]` / `[x]` checkboxes plus free-text override and notes lines, *or* a YAML structure with `choose:` fields. The human fills it out in one editing session, saves once, pings when done. The AI parses everything in one pass and applies. *Lived 2026-05-22: the level-0 naming review took 11 chat round-trips via IDE selections; the same content as a single checkbox form would have been one round-trip.* *Implication:* every multi-decision AI move offers a form file by default — proposals, naming reviews, ambiguity resolutions, decomposition picks. Each form is also a **traceable artifact** of the decisions, preserved in git history.

**Confirm names early, before they propagate.**
After any AI move that introduces new named entities (Propose, Extract, Auto-fill), pause and list the proposed names with their *provenance* — "extracted from your paragraph 2"; "AI inference"; "kept your wording"; "default from acronym". Invite explicit **accept / rename / alias** on each. Auto-generated names from chat shorthand, acronyms, or AI inference often look fine in the moment but are opaque to anyone (including future-you) outside the conversation. Naming is high-leverage: getting it right early costs little; getting it wrong is expensive to undo. *Lived 2026-05-22 — Kevin caught Claude embedding "(b+d scope)" into a permanent diagram label.* *Implication:* every artifact-proposal move ends with a Confirm Naming pass, not just a "thoughts?" prompt. See also tactic **Names are first-class artifacts** in Section B.

**Refuse to proceed until the prior stage is locked.**
At each methodology stage (Context, Level-1 DFD, CSPECs, …), the AI's discipline is partly *not advancing* until the prior level is signed off. This is the structural anti-rathole mechanism — discipline as a property of the toolkit, not human willpower. *Implication:* the toolkit literally refuses to draft level-N+1 content until level-N is accepted, and tells the human *why*.

**Explore before build (greenfield/strategic).**
For greenfield design work, talk through who/what/how-used before proposing architecture. Architecture diagrams and structured decision batches belong *after* problem-space mapping, not as the way to organize early exploration. *(Also a working agreement; restated here as a tactic.)*

**Treat colloquial examples as categories, not exemplars.**
Hear the *category* an example illustrates, not the specific instance. "The stereotypical vending machine `<smile>`" means "a small bounded problem," not "build a vending machine specifically." Confirm before committing to the literal reading. *(Also a working agreement; restated here as a tactic.)*

### B. Artifact Discipline

**Make rigor measurable.**
Every validation reports a *number*. Coverage percentages (Trace coverage, Interface coverage, Test coverage, PSPEC completeness, flow-balance %, etc.) are progress metrics, not just status indicators. Avoid "looks good" — quantify or it didn't happen. *Implication:* the toolkit's validator always emits percentages; progress is the percentage climbing toward 100.

**Model = source of truth; views are derived; some views are *workspaces*.**
Storage form (JSON / YAML / markdown-with-frontmatter) is separate from presentation form (Mermaid / HTML5-interactive / Excalidraw / SVG / D2 / Canvas). The toolkit maintains the model; multiple views render on demand, each best for a different moment. *Implication:* the toolkit's data model is notation-neutral; renderers are pluggable.

*Subtlety added 2026-05-22:* some views are **workspaces**, not just static renderings. The HTML5 interactive view in particular feels like a *graphical IDE* — drag nodes, click into specs, drill into bubbles, annotate. **Workspaces generate their own artifacts** (saved layout positions, annotations, view state) that are separate from the model and worth pinning in git as "the way we look at this." That introduces a third layer between model and rendered output:

```
project/
├── dictionary.yaml             ← cross-cutting naming (HP's Requirements Dictionary)
├── 00-context/                 ← HP level-0 / Context
│   ├── model.yaml              ← what the system is at this level (source of truth)
│   ├── context.html            ← workspace itself (interactive)
│   ├── context.layout.json     ← arrangement (workspace artifact, pinned)
│   ├── context-d2.svg          ← rendered (derived, static)
│   ├── context-mermaid.svg     ← rendered (derived, static)
│   └── naming-review.md        ← per-level naming review artifact
├── 01-level1/                  ← HP level-1 / first decomposition (future)
├── 02-level2/                  ← (future)
├── architecture/               ← parallel architecture branch (future)
├── mechanisms/                 ← 2000-book layer (future)
└── trace-matrix.html           ← cross-cutting traceability view (future)
```

**Workspace as hypertext: cross-link across levels and to reference.**
Each rendered workspace is not just a viewer — it's a **navigation surface** over the entire HP model. Three kinds of cross-link are first-class:
1. **Vertical (level) links.** Decomposable bubbles in level-N click-through to their level-(N+1) workspace. Every workspace has a "↑ Parent" link back to its parent level. Decomposable nodes carry a visible marker (double border) so users see at a glance which bubbles drill down.
2. **Dictionary links.** Every entity's side panel links to its entry in `dictionary.yaml` (and eventually a rendered HTML dictionary view).
3. **HP reference links.** Entity kinds (terminator, process, data store, CSPEC, etc.) link to their definition in `toolkit/reference/HP_QUICK_REF.md` via the existing anchor scheme.

*Implication:* the HTML workspace stops being a diagram and becomes a hypertext **system browser** for the HP model — walk the system by clicking, not by opening files in succession. Mermaid and D2 can support similar links via their native click/link primitives. *Lived 2026-05-22 — Kevin asked "is cross-linking possible?" after engaging with the level-1 HTML; the infrastructure was all in place (level directories, dictionary IDs, HP_QUICK_REF anchors), workspaces just needed to surface the links.* The two existing HTML workspaces (context.html, dfd.html) now demonstrate all three cross-link kinds.

**Click semantics for navigable bubbles:** single-click inspects (shows side-panel detail), **double-click drills** (navigates to the next-level workspace). Matches IDE / file-explorer conventions; the double-border visual cue telegraphs which bubbles are double-clickable. Cytoscape doesn't emit `dbltap` natively — implemented via a small manual timing detector (350ms threshold) in the tap handler. *Lived 2026-05-22 — Kevin asked "could clicking on a bubble navigate to the next level detail?" The answer is yes, with the double-click discipline preserving the inspect affordance.*

**Propose graphically before prose.**
When proposing a non-trivial structure (decomposition, control logic, architecture), generate a **draft visual first**, then describe details. Humans grok the *shape* from a diagram in seconds; the same shape in prose takes minutes and the cognitive load is much higher. Even a draft — pre-naming, pre-locked — is better than dense paragraphs. The text descriptions become **supporting detail** for the diagram, ideally in a collapsible `<details>` block. *Lived 2026-05-22 — Kevin flagged the 5-bubble decomposition section as dense; rendering the same content as `proposal-dfd.svg` made the shape grokable in one glance.* *Implication:* every "Propose" AI move on a structural artifact ships with a draft diagram. The diagram lives at `<level-dir>/proposal-<artifact-kind>.{d2,svg}`. Same renderers (d2, mmdc, HTML5) — just used at *proposal* time, not only at lock time. Pairs with [Recap with diagrams, not text walls](#) below.

**Recap with diagrams, not text walls.**
When working at level N of an HP decomposition, recap level N-1 by **embedding the rendered diagram** from N-1's directory — not by re-listing its content as text or a table. The level-1 doc embeds `../00-context/context-mermaid.svg`; the naming-review file embeds the current diagram so the user sees what's being renamed; CSPEC docs embed their parent DFD. Why: text recaps drift from the actual diagram, are tedious to maintain, and ignore that the artifact already exists *in the form we want*. *Lived 2026-05-22 — Kevin caught Claude duplicating the level-0 boundary as a markdown table inside the level-1 proposal when the rendered SVG was right there.* *Implication:* every "Context recap" / "Where we came from" / "Current view" section embeds the relevant prior diagram via `![...](relative/path.svg)`, not its text equivalent. Same principle for the dictionary — link to it, don't re-list entries.

**Repo / output hierarchy mirrors HP's methodology hierarchy.**
HP has a natural containment structure: Context (level 0) → Level-1 DFD → Level-2 DFDs → ... → Primitives; with a parallel Architecture Model branch (ACD → AFD → AID → AMS/AIS); plus the Mechanisms Model (2000) and cross-cutting Dictionary and Traceability. **The file system reflects this 1:1.** A practitioner walking the directory tree should be walking the HP model. Don't accumulate files at the same flat level when they belong at different levels of decomposition. *Numeric-prefixed directory names* (`00-context/`, `01-level1/`, `02-level2/`, ...) sort the listing in HP order without depending on alphabetical accident. *Lived 2026-05-22 — Kevin caught Claude letting `context-d2.svg`, `context-mermaid.svg`, `context.html`, `context.md`, `naming-review.md` all accumulate at the same flat level alongside future level-1 / level-2 / architecture artifacts.* *Implication:* every output lands in a directory named for its HP location. The cross-cutting `dictionary.yaml` lives at the project root.

**Names are first-class artifacts; reify them in a dictionary.**
Every named entity in the model gets two distinct fields: a **stable identifier** (machine-friendly, never changes — e.g., `system_root`, `term_inverters`, `flow_f3_grid_power`) and a **human-readable label** (display name; can change anytime). Labels live in a per-project **dictionary** — Kevin's "mapping db" — which is HP's Requirements Dictionary in modern form. Artifacts reference entities by stable_id; rendering pulls labels from the dictionary at render time. **Renaming = edit one dictionary entry and regenerate** — not 50 manual edits across 50 artifacts. *Lived 2026-05-22 — Kevin caught Claude embedding "(b+d scope)" into a permanent label and named the architectural fix.* *Implication:* the toolkit needs (1) a `dictionary.{yaml,json}` per project storing stable_id + label + provenance + description, (2) a `rename <id> <new-label>` command, (3) a regeneration pipeline driven from the dictionary. This is also the bridge to **drift detection** — the dictionary is where identity lives across model versions. See also tactic **Confirm names early** in Section A.

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
| `examples/solar/` | Dogfood project root — subdirectories follow HP hierarchy (`00-context/`, future `01-level1/`, `02-level2/`, `architecture/`, `mechanisms/`) | Active |
| `examples/solar/00-context/` | HP level-0 / Context Diagram artifacts — Mermaid, HTML5, D2 sources + rendered SVGs + naming-review (resolved) | ✅ Locked |
| `examples/solar/dictionary.yaml` | Per-project naming dictionary — stable IDs, labels, descriptions for every entity / flow / transition across all levels | Active |
| `examples/fishing-rig/` | Second dogfood project — automated fishing rig. **Stages 1+2 locked**: 12 entities / 12 flows / 2 edges; level-0 Context + level-1 DFD generated end-to-end via `scripts/render_project.py`. CSPEC (Stage 3) for Bite Detector future. | Active — Stages 1+2 locked |
| `examples/solar/01-level1/` | HP level-1 / first decomposition — proposal, naming review (both resolved), `dfd.{md,html,d2}` sources, rendered SVGs | ✅ Locked |
| `examples/solar/01-level1/cspecs/energy-manager/` | Level-2 CSPEC for the Energy Manager bubble — hierarchical state machine, 4 modes + 9 sub-states, 3 views | ✅ State machine locked; events/actions pending |
| `graphify-out/` | Knowledge graph of both HP books (187 nodes / 234 edges / 20 communities) | One-time workshop reference; see `graphify-out/GRAPH_REPORT.md` |
| `reference-docs/` | Workshop reading aids — source PDFs (1988 and 2000 HP books). `.gitignore`'d. | Local-only |
| `proposals/` | (empty, placeholder) | Reserved |

**Toolkit (`toolkit/`) — the deliverable that ships to practitioners:**

| Path | What it is | Status |
|---|---|---|
| `toolkit/README.md` | Practitioner-facing entry point | Active |
| `toolkit/bootstrap.sh` | Environment setup script — installs uv, d2, mmdc to user space. Idempotent. | Active |
| `toolkit/reference/HP_QUICK_REF.md` | HP method vocabulary card (60+ terms with modern analogs, cross-links). The deep-link target Claude uses when introducing HP terminology in chat. | Active |
| `toolkit/pyproject.toml` | uv-managed Python project (pydantic + pyyaml) | Active |
| `toolkit/hp_toolkit/` | Python package — `model.py` (Pydantic schemas: Project, Entity, Flow, Edge, Transition + `is_initial`) + `load.py` + `validate.py` (4 validators + transition reference checks) + `render/{mermaid,d2,cytoscape,svg}.py` (Context, DFD, CSPEC across all three source notations; Cytoscape ships full HTML wrapper for Context; SVG orchestration invokes `d2` + `mmdc` binaries). DFD + CSPEC Cytoscape HTML still planned. | End-to-end render pipeline live: dictionary → source → SVG |
| `toolkit/scripts/check_dictionary.py` | Sanity script — loads dictionary.yaml, verifies reference integrity, prints hierarchy | Active |
| `toolkit/skills/` | Claude Code skill files — `README.md` + `hp-confirm-naming.md` so far; one skill per workflow stage planned | First skill drafted |

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
