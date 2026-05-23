---
name: hp-propose-bounded-contexts
description: When team boundaries or vocabulary divergence become visible — identify bounded contexts (Evans 2003 / Vernon 2013), tag existing entities with `context:`, and propose Anti-Corruption Layer translations between contexts that share data. Paradigm-shift skill; usually invoked retroactively on existing projects.
---

# hp-propose-bounded-contexts

## When to use

When team boundaries or vocabulary divergence become visible — typically at Stage 2 if there are >5 internal processes, definitively at Stage 5 if multi-team. Can also be invoked retroactively on an existing project once the scale or team complexity makes the global Requirements Dictionary the wrong shape.

Specifically:

- The same word means different things to different parts of the system (e.g., `Node` means VM-config in Orchestration, time-series source in Telemetry, billable SKU in Billing).
- Multiple teams own different subsystems and don't share a single ubiquitous language.
- The project has crossed ~50 entities or ~5 detected community clusters in the knowledge graph.
- A polyglot stack (Rust + Python + TypeScript + Go) makes naming idioms diverge naturally.
- A merge / restructuring is forcing two previously-separate models to coexist.

This is the **Propose + Surface Ambiguity** AI move applied to organizational scaling. Modernization #5 — *paradigm shift*, not just a field addition.

## What it does

Drafts `bounded-contexts-proposal.md` as a form-based batch-review document. Identifies the system's bounded contexts (typically 2–5), assigns owners + ubiquitous-language narratives. Walks the existing dictionary and proposes a `context:` tag for every entity. Identifies cross-context flows that need translation, and proposes `kind: translation` entities (ACLs) per Evans 2003 pattern.

Standard decision set (6 sections):

| # | Decision | What it pins down |
|---|---|---|
| 1 | Context identification | How many contexts (2–5 typically), names, owner teams (CODEOWNERS-style). |
| 2 | Per-context ubiquitous language | One-paragraph narrative of each context's lexicon. The owner team's vocabulary. |
| 3 | Entity-to-context assignment | Bulk tag: every existing entity gets a `context:` (or `default` if cross-cutting). Untagged in multi-context projects is a validator error (Commit 5). |
| 4 | Cross-context flow review | Identify flows / ArchFlows whose endpoints span contexts. Each needs either a translation entity OR a re-decomposition. |
| 5 | ACL pattern per translation | For each cross-context flow, declare the Evans pattern: `shared_kernel` / `customer_supplier` / `conformist` / `anti_corruption_layer` / `open_host_service` / `published_language` / `separate_ways`. |
| 6 | Translation entity authoring | For each ACL, write a `kind: translation` entity with `source_context`, `target_context`, `source_term`, `target_term`, `pattern`. ACL prefix: `acl_*`. |

Each decision lists alternatives with Claude's recommended default **pre-checked** and provenance noted ("inferred from CODEOWNERS"; "matches graph-community structure"; "AI inference from differing naming idioms"). The user toggles overrides in MPE, saves once, pings back.

On lock, the skill writes the `## ✅ Status: Locked YYYY-MM-DD` header, populates `dictionary.yaml`'s `bounded_contexts:` section + adds `context:` fields to every tagged entity + creates `acl_*` translation entities, then runs [`hp-validate`](hp-validate.md) (catches missing context tags + unmediated cross-context references) and [`hp-render`](hp-render.md) (emits `context-map.generated.{mmd,d2,svg}` at project root).

## Behavior

When invoked, conversationally:

1. **Decide if the project is ready for contexts.** If fewer than ~5 entities or single-team, lean *defer* — the synthetic `default` context still works and contexts can be retrofitted later (strangler-fig migration).
2. **Identify candidate contexts.** Cluster-analysis hints: graph community structure (if `graphify-out/` exists), CODEOWNERS-style ownership boundaries, language/runtime boundaries (Rust service vs Python pipeline vs TypeScript UI), distinct domain vocabularies.
3. **Name each context + assign owner.** Names should be domain-y (`ctx_controller`, `ctx_dashboard`, `ctx_billing`) — not technology-y (`ctx_rust`, `ctx_python`). Owner is a team or person.
4. **Author ubiquitous-language narratives.** One paragraph per context describing its lexicon. Example: "Controller speaks setpoints + modes; Dashboard speaks views + actions; Billing speaks SKUs + cost centers."
5. **Tag every existing entity with a context.** Walk `entities`, `flows`, `architecture_modules`, `architecture_flows`. Default proposed value is inferred from the entity's parent module's allocation. Surface AI-inferred tagging for review.
6. **Identify cross-context references.** Walk flows + architecture_flows. For each whose source and target are in different contexts, flag as needing a translation.
7. **Propose ACL patterns.** Per cross-context reference, suggest the Evans pattern:
   - `anti_corruption_layer` — most common; downstream context protects its model from an external one.
   - `customer_supplier` — upstream commits to backward-compatible evolution; downstream consumes.
   - `published_language` — both contexts share an industry-standard vocabulary (e.g., HL7, FIX, OpenAPI schema).
   - `shared_kernel` — narrow, mutually-agreed shared model. Tight coupling — use sparingly.
   - Others as appropriate.
8. **Author translation entities.** For each ACL, write a `kind: translation` entity with full cross-references.
9. **Write `bounded-contexts-proposal.md`** with: stage header → form-based-review instructions → proposed context map (Mermaid inline) → per-context entity assignments → cross-context translation table.
10. **Tell the user**: "Open `bounded-contexts-proposal.md` in MPE, review the per-entity tagging + ACL proposals, save, ping me when done."
11. **On user ping**: parse, populate `dictionary.yaml`, run `hp-validate`, then `hp-render` (Context Map emitted at project root).

## Discipline

These come from Evans 2003 + Vernon 2013 + Khononov 2021 + lived experience from Commit 5.

- **Bounded contexts are team-owned, not just architecture-owned** (Vernon 2013). Every context has an owner. CODEOWNERS-style ownership is the operational reality; the context tagging makes it explicit in the dictionary.
- **Strangler-fig migration is the path.** Existing projects don't need to declare all contexts upfront. Tag entities incrementally as you discover the boundaries. Commit 5's validator only enforces context discipline once `bounded_contexts:` is non-empty — but then it enforces strictly.
- **ACL pattern is explicit, not implied** (Evans 2003 ch. 14). Each translation entity declares its pattern. The seven patterns are: shared_kernel / customer_supplier / conformist / anti_corruption_layer / open_host_service / published_language / separate_ways. Don't write a translation without naming its pattern.
- **`anti_corruption_layer` is the default for most cross-context cases.** It protects the downstream model from upstream changes. `shared_kernel` should be rare — it re-introduces the coupling DDD was invented to solve.
- **Context naming is domain-y, not tech-y.** "Controller" / "Dashboard" / "Billing" / "Telemetry" — not "Rust" / "Python" / "Backend". The context describes *what the team owns conceptually*, not the implementation choice.
- **One context can span multiple languages**; one language can span multiple contexts. The boundary is *meaning*, not *runtime*.
- **Cross-context flows must route through a translation entity** *(Commit 5 validator rule)*. If a flow's source and target are in different contexts, there must be an `acl_*` entity bridging the two. The validator errors if missing.
- **Untagged entities in multi-context projects are validator errors, not defaults** *(tactic: Context-boundary discipline)*. Once you've declared bounded contexts, tagging every new entity is required. The synthetic `default` context only applies to projects that haven't declared any bounded contexts.

## Lived examples

- [`examples/solar/dictionary.yaml` > `bounded_contexts`](../../examples/solar/dictionary.yaml) — `ctx_controller` (controller-team) + `ctx_dashboard` (frontend-team). 6 entities in controller; 3 in dashboard. One ACL: `acl_user_action_to_config` (anti_corruption_layer pattern) bridging user-actions on the dashboard side ↔ typed config/override events on the controller side.
- [`examples/solar/context-map.generated.mmd`](../../examples/solar/context-map.generated.mmd) — rendered Mermaid Context Map showing the two bounded contexts + the ACL between them.
- [`examples/solar/context-map.generated-mermaid.svg`](../../examples/solar/context-map.generated-mermaid.svg) — the SVG rendering.
- *fishing-rig is intentionally single-context* (no bounded_contexts declared) — too small to benefit from the discipline. Demonstrates the backward-compatible "synthetic default context" path.

## Implementation status

**Skill description: ✅ drafted.** Backing code: ✅ schema (`BoundedContext`, `ACLPattern` enum, `EntityKind.TRANSLATION`, optional `context:` field on Entity / Flow / ArchModule / ArchFlow) + loader + validator (8 rules covering reference integrity, translation completeness, cross-context flow routing, missing-ACL warnings, BoundedContext-with-no-entities warning) + renderer (`render_context_map` in mermaid + d2; emits Mermaid + D2 + 2 SVGs at project root) all live as of Commit 5.

## See also

- Design doc: [`toolkit/BOUNDED_CONTEXTS_DESIGN.md`](../BOUNDED_CONTEXTS_DESIGN.md) — full schema rationale, Path A vs Path B decision, migration strategy
- Tactic source: [`PLAN.md` > Modernization Tactics > Context-boundary discipline](../../PLAN.md)
- Sources:
  - Evans, E. (2003). *Domain-Driven Design: Tackling Complexity in the Heart of Software*. Addison-Wesley. (The original.)
  - Vernon, V. (2013). *Implementing Domain-Driven Design*. Addison-Wesley. (Context-Map patterns hardened; explicit ACLs.)
  - Khononov, V. (2021). *Learning Domain-Driven Design*. O'Reilly. (Modern, concise re-presentation.)
- Predecessors: any earlier proposal skill — can be invoked retroactively to label existing entities. Most natural at Stage 2 (when team boundaries first become apparent) or Stage 5 (when team-owns-module structure is locked).
- Companions: [`hp-capture-adr`](hp-capture-adr.md) — declaring bounded contexts is architecturally significant; capture an ADR documenting the choice + the alternatives (per-context files vs context-labels in one file — see BOUNDED_CONTEXTS_DESIGN.md Path A vs Path B).
- Future: a per-context filtered renderer view (`hp-render-context <ctx_id>`) is planned but not yet implemented.
