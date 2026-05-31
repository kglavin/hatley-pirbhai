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
2. **`architecture_flow` nodes** — one per architecture-level information stream between two modules (2000 §4.2.2.3). `af_<short>` id. Each architecture flow aggregates ≥1 requirements-model flows that share the same source-module + target-module pair (`allocated_flows:`). Set `kind: data | material | energy`. *Per H.21: this section was being skipped — the prior skill version directed the agent to put Stage-1/2 flow IDs straight into interconnect `carries:`, which doesn't satisfy the schema. The schema requires interconnect `carries:` to reference `architecture_flow` IDs, NOT requirements-model flow IDs.*
3. **`architecture_interconnect` nodes** — one per physical/logical channel between modules. `ai_<short>` id, label like "Local LAN" / "BLE Link" / "Internal RPC bus".
4. **`allocates_to` edges** — for every process / CSPEC / data store node in `hp-graph.json`, decide which module owns its runtime. Convention: edge source = module id, target = entity id.
5. **`carries` field on each interconnect** — list of `architecture_flow` IDs whose source + target modules are both endpoints of this interconnect. Every entry MUST resolve to an `architecture_flow` node emitted in the same output (referential integrity is validated; see Discipline).
6. **Set provenance + confidence** on every emitted node/edge.

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
    { "id": "af_order_submission", "kind": "architecture_flow",
      "label": "Order Submission", "stage": 5, "confidence": 0.85,
      "source": "am_api_gateway", "target": "am_order_service",
      "arch_flow_kind": "data",
      "allocated_flows": ["flow_order_event", "flow_order_validation_response"],
      "physical_description": "gRPC request/response over the cluster RPC interconnect; protobuf payload.",
      "provenance": { "agent": "hp-ingest-architect",
                      "rationale": "Aggregates flow_order_event (gateway → order service) and flow_order_validation_response (return). Both ride the same cluster-RPC interconnect; sharing source+target+kind, they're one architecture-level information stream." } },
    { "id": "ai_internal_rpc", "kind": "architecture_interconnect",
      "label": "Internal RPC", "stage": 5, "confidence": 0.8,
      "endpoints": ["am_api_gateway", "am_order_service"],
      "carries": ["af_order_submission"],
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

   **Per H.5: the candidates carry richer structure now.** Each `ModuleCandidate` has `image` / `build_context` / `ports_exposed` / `volumes_mounted` / `environment_keys` / `replicas` / `healthcheck` / `deployment_config`. The `edges:` array contains typed `CandidateEdge` rows: `compose_depends_on` (inter-service init dependency), `compose_port_exposed` / `dockerfile_exposes` (external surface), `compose_volume_mount` (data-store evidence), `k8s_service_selector` (which Service routes to which Deployment), `k8s_ingress_target` (external ingress targets). The `deployments:` array groups candidates by configuration (e.g. acme-cp has `deploy-prod` / `deploy-test` / `deploy-cloud` — the same logical module can appear in multiple deployments).

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
   - Every **leaf** `process` → exactly one `architecture_module`. A leaf process is one with no child processes in `hp-graph.json` (HIERARCHICAL_INGEST_DESIGN.md / H.3). On hierarchical-ingest runs the IR may contain level-1 + level-2 + level-3 processes; **only the leaves get allocated**. Non-leaf processes are organizational — they're the parent bubbles in the level-N DFD, not deployment units. The recursion's IR shape carries `parent: <proc-id>` chains; walk every process node + emit `allocates_to` only when no other process has it as `parent`.
   - Every state-rich process (`needs_cspec: true`) → as `allocated_cspecs` (HP convention, see 2000 §4.2.5.4). State-rich processes are leaves by definition (a non-leaf process can't carry needs_cspec — the validator errors on this; see T11 hierarchy rules).
   - Every `data_store` → the module that owns its persistence (DB pod / cache pod / message queue pod).
   - Terminators DO NOT get allocated — they're external.
8. **Aggregate requirements flows into `architecture_flow` nodes (H.21).** Walk every flow in `hp-graph.json` and look up its source + target modules. Group flows by `(source_module, target_module, kind)` triple — each unique triple becomes ONE `architecture_flow` node. The grouped requirements-model flow IDs go into the architecture flow's `allocated_flows:` list. Name the architecture flow after the *purpose* of the information stream at the architecture level ("Order Submission", "Adapter Contract", "Storage Reads"), not after any single requirements-model flow it aggregates. Architecture flows are coarser than requirements flows — usually 1 architecture flow per 1–6 requirements flows. Set `kind: data` (default), `material` (rare; physical goods), or `energy` (rare; electrical power, fuel).
9. **`carries:` per interconnect.** For each `architecture_flow` you emitted, check whether its source + target modules are both in some interconnect's `endpoints:` list. If yes, add that architecture-flow ID to that interconnect's `carries:` list. Every entry in any `carries:` list MUST be an `architecture_flow` ID that you also emitted — this is referential integrity, validated by `hp_toolkit.validate` rule 8.
10. **Confidence calibration.** A clear k8s Deployment + Dockerfile + 1 obvious responsibility → 0.85+. A package manifest at the repo root with no clear runtime → 0.5. Allocations: 0.8+ when one process is clearly inside one container; lower when the same process is implemented across multiple files spanning containers (the architect must adjudicate).
11. **Set provenance + confidence** on every emitted node/edge.
12. **Write `intermediate/architecture.json`.**

## Discipline

- **Allocation is total.** Every leaf process / CSPEC / data store from Stages 1–4 must land in exactly one module's `allocated_*` list. Anything unallocated is a validator failure downstream (2000 §4.2.5.4). If you can't pick a module, emit `allocates_to` with `confidence: 0.3` + a `provenance.rationale` flagging the ambiguity so the reviewer surfaces it.
- **One module per deployment unit, not per file.** A microservice running in one container is one module — even if it's implemented by 20 files. The `implemented_by[]` array on the module enumerates those files.
- **Per-deployment-config grouping (H.5.b).** When `architecture-candidates.json`'s `deployments:` array has more than one entry (acme-cp has three: `deploy-prod` / `deploy-test` / `deploy-cloud`), the candidates appear once per deployment they're part of. **Collapse to a union module set** — one `architecture_module` IR node per logical service, even if it appears across multiple deployments. Use the union's `deployment_config` provenance to record which configurations include it. Interconnect topology, however, is per-deployment — if `deploy-prod` puts service A on a network B doesn't, emit one interconnect per network and let the rationale say "in deployment X". Don't try to unify mutually-exclusive interconnect graphs.
- **Interconnects are sparse.** Most projects have 1–3 interconnects (e.g., "Cluster RPC" + "Public Internet" + "Internal Storage"). A dozen interconnects is a sign you're modeling individual network policies rather than HP physical channels.
- **`carries:` is required on every interconnect (G.3) AND must reference architecture-flow IDs you emitted (H.21).** Each interconnect's `carries:` list MUST enumerate **`architecture_flow`** IDs (not requirements-model `flow_*` IDs) whose source + target modules are both in the interconnect's `endpoints:` list. Every entry MUST resolve to an `architecture_flow` node you emitted in the same `architecture.json` — `hp_toolkit.validate` rule 8 checks this referential integrity at emit time. The merger applies a deterministic post-pass that auto-populates `carries:` from flow-endpoint ↔ interconnect-endpoint matching, but you should still populate the list directly to declare intent: it tells the reviewer "this flow rides this physical channel," which the auto-pass can't infer when the topology is ambiguous (two interconnects could carry the same flow). When in doubt, emit the `carries:` entry with a `provenance.rationale` documenting the routing decision.

  **The architecture-flow layer is NOT optional.** Skipping the `architecture_flow` emit (only producing `architecture_module` + `architecture_interconnect`) was the H.21 bug — the interconnects ended up with `carries:` references that didn't resolve anywhere, the validator flagged them as unrecoverable, and downstream Stage-5 modernization (threat-model, AID rendering, AIS specs, SLO chain) lost the architecture-flow layer entirely. Always emit at least one `architecture_flow` per interconnect that carries anything (which is most of them — power buses and ground rails are the rare exceptions).
- **Trust zone is deferred.** Per the locked Q3 in INGEST_DESIGN.md, do **not** infer `trust_zone` here. The follow-up `hp-propose-architecture` skill (Decision 9) handles it form-based after ingest completes.
- **`module_kind` matches HP convention** (hardware/software/organizational from 2000 §4.2.2.1 Fig 4.3). Don't invent new kinds.
- **Embedded firmware mode (per EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding H).** When the candidates include `kind_hint: mcu` / `firmware_target` / `px4_module` / `arduino_sketch` / `memory_layout`, the architecture is hardware-flavored. Apply these patterns:
  - **The MCU is one `architecture_module` with `module_kind: hardware`.** From a `.ioc` candidate, the MCU's `image` field carries the part number (e.g. `STM32F401RCT6`); use that as evidence in the `design_rationale`. Memory-layout candidates (kind `memory_layout`) attach as evidence to the MCU module, not as their own modules.
  - **Firmware is one `module_kind: software` module HOSTED on the MCU.** Use the `hosted_by:` relationship — the firmware module references the MCU as its host. `firmware_target` / `arduino_sketch` candidates become the firmware module.
  - **PX4 modules — one `architecture_module` per `kind_hint: px4_module`.** Default `module_kind: software`. The `px4_module_depends_on` candidate edges translate to `refines:` deployment-order dependencies (init order, not data flows) unless the dependency is the carrier of a known uORB topic (then it's a flow). Per-board `DeploymentConfig` records which boards include which px4_modules — collapse to a union module set + per-board interconnect topologies (matching the H.5.b cloud pattern).
  - **Interconnects are physical buses.** Hardware-mode interconnect kind hints: `uart_bus`, `i2c_bus`, `spi_bus`, `can_bus`, `usb_bus`, `gpio_lines`, `network_link` (Ethernet / WiFi). The boundary candidates' `hw_peripheral_*` kinds tell you which buses exist; each hw_peripheral_uart instance contributes to a `uart_bus` interconnect carrying its terminator's flows.
  - **Multi-MCU systems.** When multiple `.ioc` candidates exist (or multiple `mcu` modules emerge from per-board PX4 configs), each MCU = one hardware module; the bus between them (UART/SPI/CAN/USB) is an interconnect. Common on robotics: sensor-MCU + main-MCU; or autopilot + companion-computer over UART/Ethernet.
  - **Allocation discipline for embedded.** RTOS tasks (`xTaskCreate` / `osThreadDef` / `k_thread_create`) — when they emerge as leaf processes from Stage 2 — allocate to the firmware module that runs them. Interrupt handlers (`HAL_*_IRQHandler` / `*_Callback`) allocate to the MCU module as `allocated_processes` because they ARE the MCU's behavior, not the firmware-software-layer's.
  - **Don't allocate testbed modules.** The testbed_miner output flags purpose-built testbeds (testbed / testbed on the dogfood targets). Their compose / Dockerfile / scenario files are evidence of operational use, NOT production deployment units. Skip allocating to testbed modules; surface them in `ingest-report.md` as testbeds rather than `architecture_modules`.
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
