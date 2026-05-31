---
name: hp-ingest-architect
description: Stage 5 of brownfield ingest — given the architecture-candidate list (Dockerfiles, docker-compose services, k8s pods, terraform resources, package manifests) and the merged IR graph, name Stage-5 modules + interconnects, classify their kind (hardware/software/organizational), and allocate every leaf process / CSPEC / data store to a module. Emits IR nodes for architecture_modules + architecture_interconnects + edges for allocates_to.
---

# hp-ingest-architect

## When to use

Stage 5 of the `/hp-ingest` orchestration. Runs after Stages 1–4 have produced the merged `intermediate/hp-graph.json` (with terminators, processes, data stores, states, and pspecs). Consumes that graph + `intermediate/architecture-candidates.json` (deployment-unit candidates from infra files). Emits `intermediate/architecture.json`.

The LLM's value-add: deciding which deployment candidates become real Stage-5 modules, naming them, drawing the interconnect graph, and **allocating every leaf process / CSPEC / data store** to exactly the right module.

## What it does

Given:
- `intermediate/hp-graph.json` (merged IR with all Stage 1–4 nodes)
- `intermediate/architecture-candidates.json` (per-Dockerfile / per-k8s-Deployment / etc. candidates with `kind_hint` + `name_hint` + evidence)

Produce:

1. **`architecture_module` nodes** — one per deployable unit. Names follow HP convention (`am_<short>`, label is 1–3 words like "Controller Host" / "API Gateway"). Set `kind`: most are `software`; physical devices / single-board computers are `hardware`; team-owned services are `organizational`.
2. **`architecture_interconnect` nodes** — one per physical/logical channel between modules. `ai_<short>` id, label like "Local LAN" / "BLE Link" / "Internal RPC bus".
3. **`allocates_to` edges** — for every process / CSPEC / data store node in `hp-graph.json`, decide which module owns its runtime. Convention: edge source = module id, target = entity id.
4. **`carries` edges** — for each interconnect, identify which Stage-1/2 flows ride on it (the LLM checks each flow's source/target → module mapping; if both endpoints are on the same interconnect, that flow is carried).
5. **Set provenance + confidence** on every emitted node/edge.

Output JSON shape:

```json
{
  "nodes": [
    { "id": "am_api_gateway", "kind": "architecture_module", "label": "API Gateway",
      "stage": 5, "confidence": 0.85,
      "implemented_by": ["Dockerfile.api", "k8s/api-deployment.yaml"],
      "summary": "Edge HTTP/gRPC layer; auth + rate-limit + routing.",
      "module_kind": "software",
      "trust_zone": null,                            // deferred to hp-propose-architecture per Q3
      // ── Prose fields (H.2.c) — required, not optional ────────────
      "design_rationale": "Edge ingress for all external clients. Lives as its own deployment unit because (a) auth/rate-limit policies need a single chokepoint, (b) the team operates this layer separately from downstream services, and (c) horizontal scale here is decoupled from order-service scale. Built on axum + tower middleware.",
      "design_justification": "Backpressure isolation + auth concentration. Alternative (auth-in-each-service) was rejected during the auth-rewrite discussion last quarter.",
      "required_constraints": "Sub-100ms p99 routing latency; replicas ≥ 3 in production (compose says 1 for local dev); never call downstream services synchronously from request path.",
      // ────────────────────────────────────────────────────────────
      "provenance": { "agent": "hp-ingest-architect",
                      "rationale": "k8s Deployment 'api' + Dockerfile.api; serves /v1/* endpoints. README at services/api/README.md confirms ingress role." } },
    { "id": "ai_internal_rpc", "kind": "architecture_interconnect",
      "label": "Internal RPC", "stage": 5, "confidence": 0.8,
      "endpoints": ["am_api_gateway", "am_order_service"],
      "carries": ["flow_order_event"],
      "summary": "gRPC over the cluster network.",
      "design_rationale": "Internal service mesh — all in-cluster RPC. Single interconnect because the cluster's network policy treats all in-cluster traffic as one trust zone." }
  ],
  "edges": [
    { "source": "am_api_gateway", "target": "proc_route_request",
      "kind": "allocates_to", "stage": 5, "confidence": 0.85 },
    { "source": "am_order_service", "target": "proc_validate_order",
      "kind": "allocates_to", "stage": 5, "confidence": 0.85 }
  ]
}
```

## Behavior

**Progress log:** at entry, append a START line; after writing `architecture.json`, append a DONE line. Per `hp-ingest.md` orchestrator convention:
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START    stage=5 agent=hp-ingest-architect" >> <intermediate-dir>/progress.log`
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DONE     stage=5 agent=hp-ingest-architect modules=$N interconnects=$I allocations=$A" >> <intermediate-dir>/progress.log`

When invoked, conversationally:

1. **Read the project glossary (H.4.c).** Load `intermediate/glossary.curated.json` (if present). Module + interconnect labels MUST use project vocabulary when a glossary term applies — `am_archi` not `am_query_service`; `ai_pulse_bus` not `ai_event_bus`. The categories `concept` + `process` + `artifact` are most relevant for module naming; `event` for interconnects-that-carry-events.
2. **Read pre-stage file drops (architect guidance + external evidence).**
   - **Hints:** check `intermediate/hints/architect.md`. If present, treat as binding architect guidance — common cases are "split this module" / "collapse these two" / "rename module X to Y" / "this isn't really a module, drop it". Append a `HINT_LOADED` line: `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) HINT_LOADED stage=5 agent=hp-ingest-architect path=intermediate/hints/architect.md" >> <intermediate-dir>/progress.log`.
   - **External context:** read every file under `external-context/adrs/` (architecture decision records — authoritative for Stage-5 module + interconnect rationale) and `external-context/design-docs/` (design memos that didn't make it into the repo). When an architecture_module / architecture_interconnect node derives from an external doc, record the source path in its `provenance.external_context_used`.
3. **Read inputs.** Load `hp-graph.json` (nodes/edges from Stages 1–4) + `architecture-candidates.json` (deployment-unit candidates) + `rationale-sources.json` (per-candidate rationale evidence: nearby READMEs, file headers, infra comments — produced by the H.2.b prep step). The rationale evidence is the bulk of your input by token count; read it carefully, it's the project's own "why" for each module. Also load — when present:
   - `intermediate/recipes.json` (T9.c) — Makefile / Justfile recipes. The `deploy` + `up` categories show the project's *canonical* deployment commands; cross-reference with the architecture-candidates' deployment_config. A `deploy-prod` target invoking compose against three of your candidate modules is strong evidence those three are co-deployed. Recipe comments (`# ...` above a target) are first-class rationale sources alongside the H.2.b nearby READMEs.
   - `intermediate/testbeds.json` (H.7) — testbed compose / k8s files are a *separate deployment configuration*. Cross-reference their `compose_files` / `k8s_files` against the production deployments in `architecture-candidates.deployments`. Don't conflate testbed modules with production architecture (the testbed harvest marks their directories — suppress from production allocation). Testbed scenarios also describe how production modules are *meant* to operate; check against your allocation choices for sanity.

   **Per H.5: the candidates carry richer structure now.** Each `ModuleCandidate` has `image` / `build_context` / `ports_exposed` / `volumes_mounted` / `environment_keys` / `replicas` / `healthcheck` / `deployment_config`. The `edges:` array contains typed `CandidateEdge` rows: `compose_depends_on` (inter-service init dependency), `compose_port_exposed` / `dockerfile_exposes` (external surface), `compose_volume_mount` (data-store evidence), `k8s_service_selector` (which Service routes to which Deployment), `k8s_ingress_target` (external ingress targets). The `deployments:` array groups candidates by configuration (e.g. cloudctlplane has `bluerockccpd` / `agate-test-deployment` / `aws-basic` — the same logical module can appear in multiple deployments).

   **Use the typed structure:**
   - `image:` from a public registry + no `build:` → module is **off-the-shelf software** (still `module_kind: software`; mention the SaaS / managed-service nature in `design_rationale`)
   - `image:` from an internal registry → **pre-built in-tree**
   - `build:` set (compose) or in-tree Dockerfile → **in-tree software** (the team builds + owns it)
   - `compose_depends_on` edges → typically a `refines:` deployment-order dependency (init order, not a data flow) unless the depends_on target is a data store the source genuinely sends data to
   - `compose_port_exposed` / `dockerfile_exposes` → module carries an inbound external flow from a terminator (cross-reference with Stage-1 boundary)
   - `compose_volume_mount` / `volumes_mounted=[pvc:foo]` → module owns the data store at the mount target (architect should `allocates_to` the relevant `data_store` IR node here)
   - `k8s_service_selector` / `k8s_ingress_target` → the interconnect endpoint set is given to you; honor it
4. **Build the module set.** For each candidate, decide if it's a real Stage-5 module:
   - **Promote** Dockerfiles, k8s Deployments/StatefulSets, single-purpose npm/cargo packages.
   - **Collapse** multiple candidates for the same module (a Dockerfile + a k8s Deployment for the same service → one module; both files go into `implemented_by`).
   - **Skip** candidates that are infrastructure-of-infrastructure (e.g., a Dockerfile for a build image that nothing in the runtime uses).
5. **Pick `module_kind` per module.** Default `software`. Use `hardware` for SBCs / embedded controllers / physical sensors-and-actuators (rare in cloud projects; common in fishing-rig-style HW projects). Use `organizational` for modules owned by a team-as-a-service (rare for ingest — usually appears in retrofit cases).
6. **Draw the interconnect graph.** From compose networks + k8s Services + cross-module imports in the codebase, identify which modules talk. Each unique channel = one interconnect. Be conservative — most modules talk over a single shared interconnect (e.g., "Cluster RPC") plus 1–2 external ones (e.g., "Internet ingress").
7. **Allocate every Stage 1–4 entity** that has a runtime presence:
   - Every leaf `process` → exactly one `architecture_module`.
   - Every state-rich process (`needs_cspec: true`) → as `allocated_cspecs` (HP convention, see 2000 §4.2.5.4).
   - Every `data_store` → the module that owns its persistence (DB pod / cache pod / message queue pod).
   - Terminators DO NOT get allocated — they're external.
8. **`carries` per interconnect.** For each flow node in `hp-graph.json`, look up its source + target modules. If both endpoints are on the same interconnect's endpoint list, add the flow id to `carries`.
9. **Confidence calibration.** A clear k8s Deployment + Dockerfile + 1 obvious responsibility → 0.85+. A package manifest at the repo root with no clear runtime → 0.5. Allocations: 0.8+ when one process is clearly inside one container; lower when the same process is implemented across multiple files spanning containers (the architect must adjudicate).
10. **Set provenance + confidence** on every emitted node/edge.
11. **Write `intermediate/architecture.json`.**

## Discipline

- **Allocation is total.** Every leaf process / CSPEC / data store from Stages 1–4 must land in exactly one module's `allocated_*` list. Anything unallocated is a validator failure downstream (2000 §4.2.5.4). If you can't pick a module, emit `allocates_to` with `confidence: 0.3` + a `provenance.rationale` flagging the ambiguity so the reviewer surfaces it.
- **One module per deployment unit, not per file.** A microservice running in one container is one module — even if it's implemented by 20 files. The `implemented_by[]` array on the module enumerates those files.
- **Per-deployment-config grouping (H.5.b).** When `architecture-candidates.json`'s `deployments:` array has more than one entry (cloudctlplane has three: `bluerockccpd` / `agate-test-deployment` / `aws-basic`), the candidates appear once per deployment they're part of. **Collapse to a union module set** — one `architecture_module` IR node per logical service, even if it appears across multiple deployments. Use the union's `deployment_config` provenance to record which configurations include it. Interconnect topology, however, is per-deployment — if `bluerockccpd` puts service A on a network B doesn't, emit one interconnect per network and let the rationale say "in deployment X". Don't try to unify mutually-exclusive interconnect graphs.
- **Interconnects are sparse.** Most projects have 1–3 interconnects (e.g., "Cluster RPC" + "Public Internet" + "Internal Storage"). A dozen interconnects is a sign you're modeling individual network policies rather than HP physical channels.
- **`carries:` is required on every interconnect (G.3).** Each interconnect's `carries:` list MUST enumerate the architecture-flow ids whose endpoints are both in the interconnect's `endpoints:` list. The merger applies a deterministic post-pass that auto-populates `carries:` from flow-endpoint ↔ interconnect-endpoint matching (so a missing entry gets backfilled), but you should still populate the list directly to declare intent: it tells the reviewer "this flow rides this physical channel," which the auto-pass can't infer when the topology is ambiguous (two interconnects could carry the same flow). When in doubt, emit the `carries:` entry with a `provenance.rationale` documenting the routing decision.
- **Trust zone is deferred.** Per the locked Q3 in INGEST_DESIGN.md, do **not** infer `trust_zone` here. The follow-up `hp-propose-architecture` skill (Decision 9) handles it form-based after ingest completes.
- **`module_kind` matches HP convention** (hardware/software/organizational from 2000 §4.2.2.1 Fig 4.3). Don't invent new kinds.
- **AMS/AIS rationale prose is required, not optional (H.2.c).** Every `architecture_module` node MUST carry:
  - `design_rationale`: 3–5 sentences. What does this module do at the architecture level? Why is it a separate module from its siblings? What's the key technology / protocol choice? Pull from `rationale-sources.json` for this candidate — the nearby README + file headers + infra comments carry most of the prose you need.
  - `design_justification`: 1–2 sentences. The constraint that drove the structure / choice. Often phrased as "alternative X was rejected because Y" or "this isolation exists because Z".
  - `required_constraints`: 1–3 sentences. Resource / scaling / safety constraints extractable from infra evidence (`replicas:`, `resources.limits`, `restart_policy`, etc.) or stated in nearby docs.

  The emitter (per H.2.a) surfaces these directly into AMS / AIS — placeholder text only fires when the architect agent emits nothing. **Treat the placeholder as a sign of underperforming, not a default.**

  For `architecture_interconnect` nodes, `design_rationale` is required (1–3 sentences: what channel is this, what protocol, why is it its own interconnect). `design_justification` + `required_constraints` are optional for interconnects.

## Implementation status

**Skill description: ✅ drafted.** Backing scripts: ✅ `hp_toolkit/ingest/architecture_candidates.py` (Commit 3). Orchestrator dispatch via `/hp-ingest` skill (Commit 3).

## See also

- Design doc: [`toolkit/INGEST_DESIGN.md`](../INGEST_DESIGN.md).
- Predecessors: [`hp-ingest-scan`](hp-ingest-scan.md), [`hp-ingest-boundary`](hp-ingest-boundary.md), [`hp-ingest-processes`](hp-ingest-processes.md), [`hp-ingest-leaf`](hp-ingest-leaf.md).
- Follower: [`hp-ingest-review`](hp-ingest-review.md) — final merge + emit.
- IR schema: [`hp_toolkit/ingest/schema.py`](../hp_toolkit/ingest/schema.py).
- HP Stage 5 reference: [`toolkit/ARCH_DESIGN.md`](../ARCH_DESIGN.md), [`examples/solar/architecture/`](../../examples/solar/architecture/), [`examples/fishing-rig/architecture/`](../../examples/fishing-rig/architecture/).
- Companion (post-ingest): [`hp-propose-architecture`](hp-propose-architecture.md) — adds trust zones, deployment strategy, design rationale, ADRs.
