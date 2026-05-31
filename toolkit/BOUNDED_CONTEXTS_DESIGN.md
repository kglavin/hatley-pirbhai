# Bounded Contexts Design — Modernization Item #5

**Status:** ✅ shipped — design locked 2026-05-22; model + skill landed (`BoundedContext`/`ACLPattern` + translation machinery in [`hp_toolkit/model.py`](hp_toolkit/model.py); [`skills/hp-propose-bounded-contexts.md`](skills/hp-propose-bounded-contexts.md); rendered via context-map.generated-d2.svg in the Modernization sidebar section). Body sections describe the as-locked design; spot-check against current code if reviewing a specific sub-item.
**Branch (proposed):** `kg/meld-tech-2026` or split into `kg/bounded-contexts`.
**Audience:** the implementation pass that brings Domain-Driven Design Bounded Contexts into the HP toolkit's Requirements Dictionary.
**Why this exists:** modernization item #5 from the [`../proposals/MODERNIZATION.md`](../proposals/MODERNIZATION.md) brainstorm is *triple-confirmed* (Kevin's brainstorm + cloud-control-plane project lens + kernel-enforcement project lens). At >50 entities, >5 teams, or multi-language stacks, the global Requirements Dictionary is the wrong shape. This doc captures the paradigm-shift decisions before implementation.

**Sources:** Eric Evans (2003), Vaughn Vernon (2013), Vlad Khononov (2021). Bounded Contexts are now standard in microservice / multi-team systems; the question is *how* HP integrates them, not *whether*.

---

## 1. The problem the global dictionary creates

HP's Requirements Dictionary assumes one ubiquitous language across the whole system. Every entity (`proc_*`, `term_*`, `flow_*`, `store_*`, …) is defined exactly once and means the same thing everywhere it's referenced.

This works for HP's original audience — a single project, single team, hundreds of entities maximum, single domain (avionics, factory automation, medical device).

It breaks for modern multi-team microservice systems because:

- **The same word means different things to different teams.** The cloud-control-plane lens (Section 8.5 of the proposals doc) surfaced ~615 graph communities — many of which would call the same concept by different names (`Node` means different things to Orchestration, Telemetry, Billing). Forcing a global name destroys the local meaning.
- **Team boundaries are organizational, not just technical.** The kernel-enforcement lens (Section 8.6) surfaced CODEOWNERS-style team ownership. A single global dictionary can't capture "the kernel-sensor team owns this term; the userspace daemon team owns that term."
- **Polyglot stacks have language-native idioms.** Rust naming idioms differ from Python differ from TypeScript. A global dictionary that forces one naming convention misrepresents at least three out of four languages.
- **Independent evolution velocity.** Two teams updating their respective halves of a global dictionary collide constantly. Independent local dictionaries with explicit boundary translations don't collide.

The paradigm-shift that DDD codified (Evans 2003) is: **each bounded context owns the meaning of its terms; cross-context translation is explicit, not implicit.**

---

## 2. The book grounding

### 2.1 Eric Evans, *Domain-Driven Design* (2003)

Core concepts:

> "Multiple models are in play on any large project. Yet when code based on distinct models is combined, software becomes buggy, unreliable, and difficult to understand. Communication among team members becomes confused. … Explicitly define the context within which a model applies. … Keep the model strictly consistent within these bounds, but don't be distracted or confused by issues outside." — Evans 2003, ch. 14

Six context-mapping patterns (Evans, also expanded by Vernon):

| Pattern | What it means |
|---|---|
| **Shared Kernel** | Two contexts share a small subset of model + code by mutual agreement. Tight coupling — use sparingly. |
| **Customer / Supplier** | Upstream context dictates the model; downstream consumes. Upstream commits to backward-compatible evolution. |
| **Conformist** | Downstream simply conforms to an upstream model it can't influence. |
| **Anti-Corruption Layer (ACL)** | Downstream wraps an external model in a translation layer to keep its own model clean. The most architecturally important pattern. |
| **Open Host Service** | Upstream publishes a stable, well-documented protocol for any consumer. |
| **Published Language** | Both contexts agree to use a shared, well-documented vocabulary (often an industry standard — e.g., HL7, FIX). |
| **Separate Ways** | Two contexts have no integration — they can develop independently. |

### 2.2 Vaughn Vernon, *Implementing Domain-Driven Design* (2013)

Vernon hardened the patterns into a *Context Map* — an explicit graph of contexts + their integration patterns. The Context Map is itself a first-class artifact.

> "A Context Map provides each team with a clear and global understanding of the bounded contexts in play and the integration relationships among them." — Vernon 2013

### 2.3 Vlad Khononov, *Learning Domain-Driven Design* (2021)

Modern update: bounded contexts often map 1:1 to microservices, but the mapping isn't required. Context boundaries are *semantic*, not deployment.

---

## 3. The minimum-disruption schema choice

Two paths considered:

### Path A — **Per-context dictionary files**

Split `dictionary.yaml` into multiple files, one per context: `dictionaries/<context>.yaml`. Each context's entities are defined in their own file. Cross-context refs are explicit (`other_context/entity_id`).

- **Pro:** Strong isolation; matches multi-team file ownership; mirrors how DDD practitioners typically structure code (one bounded-context = one folder).
- **Con:** Toolkit's "one file is the source of truth" guarantee softens significantly. Validator + renderer need to handle multi-file loading + cross-file references. Big migration cost for existing dictionaries.

### Path B — **Context labels within one file** ✅ chosen for first cut

Keep `dictionary.yaml` as a single file. Add `context:` field to every entity. Bounded contexts are *named regions* within the file. Cross-context references must be marked explicitly.

- **Pro:** Backward compatible (no `context:` = "default context"; existing dictionaries keep working). Single source of truth preserved. Validator + renderer changes are surgical (additive). Migration is incremental.
- **Con:** Doesn't enforce file-level isolation; teams could conflict on edits even within their own contexts. Doesn't naturally map to per-team file ownership.

**Decision: Path B for the first cut.** Path A remains available as a future refactor once Path B is validated. The two are mutually compatible — a Path-B `context:` field is the foundation that a future Path-A migration would carry over.

---

## 4. Schema additions

### 4.1 Context as a first-class dictionary section

New top-level section declaring bounded contexts themselves:

```python
class BoundedContext(BaseModel):
    """A bounded context per Evans 2003 / Vernon 2013.

    A context is a region of the dictionary where a ubiquitous language
    applies consistently. Cross-context references must go through an
    explicit translation (= an Anti-Corruption Layer entity)."""
    id: str
    name: str
    description: Optional[str] = None
    owner: Optional[str] = None              # team or person (CODEOWNERS-style)
    ubiquitous_language: Optional[str] = None  # narrative of the context's lexicon
```

`Project.bounded_contexts: dict[str, BoundedContext] = Field(default_factory=dict)`.

### 4.2 Context label on every entity-like type

Add an optional `context: Optional[str]` field to:

- `Entity` (and therefore everything that inherits — process, terminator, data_store, system, state, etc.)
- `Flow`
- `Edge`
- `Transition`
- `PSpec`
- `ArchModule`
- `ArchFlow`
- `ArchInterconnect`
- `ArchModuleSpec`
- `ArchInterconnectSpec`
- `ADR` (from modernization #10)
- `Budget`, `TPM`, `SLO` (from modernization #21/#22/#32)

When `context:` is unset, the entity belongs to a synthetic `default` context. This preserves backward compatibility with existing dictionaries.

### 4.3 Translation entities (Anti-Corruption Layers)

Cross-context references *must* go through an explicit translation entity. New entity kind:

```python
class EntityKind(str, Enum):
    # ... existing kinds ...
    TRANSLATION = "translation"     # ACL — Anti-Corruption Layer

class TranslationEntity(Entity):
    """An Anti-Corruption Layer between two bounded contexts."""
    source_context: str               # which context produces the term
    target_context: str               # which context consumes it
    source_term: str                  # entity id in source context
    target_term: str                  # entity id in target context
    pattern: ACLPattern               # which context-mapping pattern (Evans 2003)

class ACLPattern(str, Enum):
    SHARED_KERNEL          = "shared_kernel"
    CUSTOMER_SUPPLIER      = "customer_supplier"
    CONFORMIST             = "conformist"
    ANTI_CORRUPTION_LAYER  = "anti_corruption_layer"
    OPEN_HOST_SERVICE      = "open_host_service"
    PUBLISHED_LANGUAGE     = "published_language"
    SEPARATE_WAYS          = "separate_ways"
```

Cross-context flow / interconnect references in the dictionary must either:
- Stay within the same `context:` (no translation needed), OR
- Route through a `kind: translation` entity with explicit source + target context

---

## 5. Validator rules

| # | Rule | Severity |
|---|---|---|
| 1 | Every entity with `context:` references a real `BoundedContext` | error |
| 2 | A Flow's source and target must be in the same context, OR the flow must reference a translation entity bridging the two contexts | error |
| 3 | An ArchFlow's source and target must be in the same context, OR via translation | error |
| 4 | A translation entity's `source_term` exists in `source_context`; `target_term` exists in `target_context` | error |
| 5 | A translation entity's `source_context` ≠ `target_context` (translations are between *different* contexts) | error |
| 6 | Each `BoundedContext` declared in the dictionary has at least one entity assigned to it (warning if a context exists with no entities) | warning |
| 7 | Every cross-context reference declares the ACL pattern used (warning if unspecified) | warning |
| 8 | When `owner:` is set on a BoundedContext, validator could cross-check with a project-level CODEOWNERS file if present | info |

---

## 6. New coverage metrics

| Metric | What it measures |
|---|---|
| `bounded_context_count` | Number of bounded contexts declared |
| `entities_per_context` | Distribution of entities across contexts |
| `cross_context_translation_count` | Number of explicit translation entities |
| `cross_context_reference_violations` | Flows / ArchFlows crossing contexts without a translation (error count) |
| `context_owner_coverage_pct` | Bounded contexts with `owner:` set |

---

## 7. Renderer changes

### 7.1 Cytoscape view

Each diagram (Context, DFD, AFD, AID) gains **per-context coloring** — entities in the same context share a hue. The default context renders neutral; named contexts cycle through a palette. Translation entities render with a distinctive style (e.g., diamond shape or double-bordered).

### 7.2 New "Context Map" view

New diagram type per Vernon 2013: the **Context Map** shows the contexts themselves (as bubbles) with translation entities (as labeled arrows) between them. Renderer functions:

- `mermaid.render_context_map(project)` → Mermaid `graph LR` of contexts + ACLs
- `d2.render_context_map(project)` → D2 source
- `cytoscape.render_context_map_elements(project)` + `wrap_context_map_html(project)`

Output: `context-map.generated.{mmd,d2,html,svg}` at the project root.

### 7.3 Per-context filtered views

When rendering an AFD, allow filtering: `render_afd(project, context="telemetry")` shows only modules in that context (with translation entities at the boundary). Useful for per-team views.

---

## 8. Migration strategy

Existing dictionaries (solar, fishing-rig, doorbell) have no `context:` fields. They'll continue to work after this change because:

1. Loader treats unlabeled entities as belonging to a synthetic `default` context.
2. Validator skips cross-context rules when only `default` is in play.
3. Renderer treats single-context projects identically to today.

**Adding contexts to an existing project is incremental:**

1. Declare bounded contexts in `bounded_contexts:` section.
2. Tag entities with `context:` field as you discover them.
3. Untagged entities remain in `default` — no rush to migrate all at once.
4. The first cross-context flow you declare forces a translation entity to be added.
5. The validator surfaces missing-context-on-cross-context-ref as errors so migration is guided.

This is the "strangler-fig" migration pattern applied to schema.

---

## 9. Lived example — illustrative

Solar's locked architecture has 2 modules: `am_controller_host` and `am_dashboard_app`. These are natural candidates for two bounded contexts:

```yaml
bounded_contexts:
  ctx_controller:
    name: "Controller Service"
    owner: "controller-team"
    description: |
      The Linux-side service: telemetry ingest, energy-manager state
      machine, command dispatch. Ubiquitous language oriented around
      power flows, modes, and setpoints.

  ctx_dashboard:
    name: "Dashboard App"
    owner: "frontend-team"
    description: |
      Browser-side SPA: dashboards, alerts, config UI. Ubiquitous
      language oriented around views, panels, and user actions.

entities:
  am_controller_host:
    name: "Controller Host"
    context: ctx_controller   # NEW
    # ... existing fields ...

  am_dashboard_app:
    name: "Dashboard Web App"
    context: ctx_dashboard    # NEW
    # ... existing fields ...

  # Translation entity: dashboard's `User Action` ←→ controller's `Config Event`
  txn_user_action_to_config:
    kind: translation                         # NEW kind
    context: default                          # translations sit at boundaries
    source_context: ctx_dashboard
    target_context: ctx_controller
    source_term: data_user_action_event
    target_term: data_event_config
    pattern: anti_corruption_layer            # Evans 2003 pattern
    description: |
      The dashboard emits user-action events shaped for the UI;
      the controller expects config events with validated, typed
      payloads. This ACL translates between the two shapes.
```

A real bounded-contexts-aware Stage 5 architecture would surface this naturally during the form-based proposal.

---

## 10. Implementation order

This commit (modernization Commit 5) breaks into ~6 chunks:

1. **Model:** `BoundedContext`, `TranslationEntity`, `ACLPattern`; `context:` field on all entity-like types
2. **Loader:** pick up `bounded_contexts:` section
3. **Validator:** rules 1–8 from §5
4. **Renderer (existing diagrams):** per-context coloring on Cytoscape AFD/AID/Context/DFD views
5. **Renderer (new):** Context Map diagram type (Mermaid + D2 + Cytoscape + SVG)
6. **Status reporting + skill:** Stage 5b / context-map sub-stage in `hp-status`; new `hp-propose-bounded-contexts` skill
7. **Lived example:** retrofit solar (2 contexts) + fishing-rig (probably 1 context — too small) + acme-cp-style demo (5+ contexts in a sample dictionary used for testing)

---

## 11. Open questions

1. **Path A migration trigger.** When does the "context labels in one file" approach (Path B) reach its limit? Plausible answer: when a project hits ~5 named contexts with ~50+ entities each, Path A's per-context files become more manageable. Capture as a future refactor.

2. **CODEOWNERS integration.** Should the validator cross-reference a CODEOWNERS file? Adds operational utility but increases coupling. Lean: optional, info-level only.

3. **Translation entity rendering.** Should translation entities appear inline on AFD/DFD (cluttering) or only on the Context Map (cleaner)? Lean: only on Context Map by default, with an opt-in flag to include them inline.

4. **Context inheritance.** A child entity (e.g., a state inside a CSPEC) inherits its parent's context if unspecified? Lean: yes — inheritance reduces boilerplate.

5. **The `default` context.** Should the synthetic default context appear in the Context Map, or stay invisible? Lean: invisible unless explicit translation entities reference it.

6. **Naming of translation entities.** Prefix convention: `txn_*` is already taken (transitions). Need a different prefix — `xlt_*` (translation)? `acl_*` (Anti-Corruption Layer)? Lean: `acl_*` (Evans's terminology).

7. **Per-context renderer output directories.** Should `architecture/specs/` get split into `architecture/specs/<context>/`? Lean: optional flag; default flat.

---

## 12. See also

- Companion design doc: [`MODERNIZATION_DESIGN.md`](MODERNIZATION_DESIGN.md) (items #1, #2, #8, #10, #21, #22, #25, #32, #33 — the additive set)
- Brainstorm + analysis: [`../proposals/MODERNIZATION.md`](../proposals/MODERNIZATION.md) §3.5.1 (DDD Bounded Contexts proposal); §8.5 + §8.6 (real-project lenses)
- Predecessor design docs: [`PSPEC_DESIGN.md`](PSPEC_DESIGN.md), [`ARCH_DESIGN.md`](ARCH_DESIGN.md)

---

## 13. Source bibliography

- **Evans, E.** (2003). *Domain-Driven Design: Tackling Complexity in the Heart of Software*. Addison-Wesley. (The original; chapters 14–17 on Bounded Contexts + Context Maps.)
- **Vernon, V.** (2013). *Implementing Domain-Driven Design*. Addison-Wesley. (Context-Map patterns hardened; explicit ACLs.)
- **Khononov, V.** (2021). *Learning Domain-Driven Design*. O'Reilly. (Modern, concise re-presentation.)
- **Brandolini, A.** (2013). *Strategic Domain-Driven Design*. (Event-storming as a context-discovery technique.)
