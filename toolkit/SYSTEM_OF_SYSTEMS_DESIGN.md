# System-of-Systems Design

## Status: 🟡 Stub — open issues only, no questions locked yet

This is a parking lot for the SoS arc (Option Y in [HIERARCHICAL_INGEST_DESIGN.md](HIERARCHICAL_INGEST_DESIGN.md) and H.3 in [INGEST_TUNING_DESIGN.md](INGEST_TUNING_DESIGN.md)). The Hierarchical (Option X) work has shipped; SoS (Option Y — each subsystem as its own HP project, linked) is the natural sibling but deferred until a multi-repo target or a concrete use case shows up.

Entries below are issues to discuss when this design opens for real. They are not yet questions to be answered — capture first, structure later.

---

## Open issues to discuss

### Reuse of framework analysis across consumer projects

**Raised:** 2026-05-25, after the PX4 dogfood. Triggered by Kevin checking out `px4_vision_autonomy` — a small ROS 2 / MAVSDK project that *uses* PX4 — and asking whether the toolkit could reference the existing PX4 analysis rather than re-discover it.

**The observation:** A consumer project sits across a boundary (MAVLink, ROS topics, an SDK) from a framework whose internals we've already analyzed. From the consumer's perspective the framework is one opaque terminator. But the analysis exists — and many projects share the same framework. Re-running the LLM pipeline on PX4 for every consumer is wasteful, and the consumer's model is *richer* if the framework's published surface is referenced rather than collapsed.

**Two shapes worth comparing when this opens:**

1. **Framework-as-deep-terminator** — consumer imports a *boundary-surface slice* of the framework's analysis (its public command set / topics / SDK contract). Terminators stop being sticky notes and become versioned interface contracts. Cheap, decoupled, fits HP's existing terminator concept. Loses the ability to reason about internals from inside the consumer project.

2. **Framework-as-already-AMS'd-subsystem** — pull the framework's modules/interconnects (or a subset) into the consumer's architecture as pre-authored entities marked `external_ref: <framework>@<version>`. Consumer adds its own processes/flows alongside. Stronger end-to-end traces; more work to keep version-aligned + decide what's in-scope to import.

**Questions to surface when this opens:**

- Who is the primary user? The *consumer project's* author (importing PX4 to enrich their model), or the *framework's* author (publishing the analysis for downstream)?
- What does "library" mean physically? Shared filesystem cache, Git-backed registry, package-manager-like resolver?
- Granularity of import: full graph, declared-surface slice, or selective entity picks?
- Versioning: how is staleness detected when the upstream framework evolves?
- Cross-project ID stability: `proc_commander` in PX4 vs. `proc_commander` in some other project — namespacing, prefixing, or full URIs?
- Provenance: how does the dictionary mark imported-vs-local entities? Does the renderer treat them differently?
- IP / licensing: open-source frameworks are fine to publish analyses for; what's the story for closed-source?

**Relation to other work:** This composes with Bounded Contexts ([BOUNDED_CONTEXTS_DESIGN.md](BOUNDED_CONTEXTS_DESIGN.md)) — a framework reference is effectively an external bounded context with a published context map. The translation/ACL machinery may be most of what's needed at the model layer; the rest is registry + tooling.
