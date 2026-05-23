# Modernizing Hatley-Pirbhai for 21st-Century Architectures

**Status:** Brainstorm pass — no decisions, no implementation. Lives on branch `kg/meld-tech-2026` while we figure out which proposals make it into the toolkit. Once we converge on which subset is genuinely *valid, valuable, and novel*, a separate design doc (mirroring `PSPEC_DESIGN.md` / `ARCH_DESIGN.md`) captures the locked decisions per area.

**Audience:** us, deciding what's worth doing. Not external.

**Sources:** Claude's independent brainstorm + Kevin's brainstorm (pasted into the conversation; appears to be from a separate AI tool) + a NASA-SE-derived pass + a DevOps / SecOps / AIOps / SRE pass, both surfaced via follow-up questions. Each entry below labels its source: `C` = Claude, `K` = Kevin's brainstorm, `B` = both, `N` = NASA Systems Engineering practice (SP-2016-6105 Rev 2 / 2017 + MBSE adoption guidance), `O` = modern operational disciplines (DevOps / SecOps / AIOps / SRE).

---

## 1. Why this document exists

The Hatley-Pirbhai methodology was developed 1984–2000 for static, monolithic, mostly single-machine embedded systems. Boeing 777 flight control, factory automation, medical devices. The assumptions baked into the methodology are:

- **Static topology.** Modules exist on hardware that was designed before the software was written. The number of CPUs fits on one hand.
- **Static interconnects.** A bus, a backplane, a serial line. The path from A to B is hardwired and reliable.
- **Co-located state.** Data stores are local memory or local files. Shared memory is a feature, not an anti-pattern.
- **Synchronous data flow.** A sensor reading propagates through the system at predictable cadence.
- **Single ubiquitous language.** One global Requirements Dictionary defines every term system-wide.
- **Built once, runs forever.** The architecture is fixed at design time; deployment is a one-shot install.
- **Determinism.** Same input → same output, same timing.

Modern distributed / cloud / containerized / web-scale systems break every one of these. CPUs by the thousand, ephemeral nodes, network as a fabric not a wire, eventual consistency, async events, multi-team / multi-context vocabularies, continuous deployment, scaling on demand, and runtime topology that changes faster than any document can keep up with.

The question this document enumerates: **what additions to HP would make it usable and applicable in CPU / server / cloud / container / cluster / webscale architectures, without throwing out HP's actual strengths** (rigor, balancing rules, separation of what/how, dictionary as single source of truth, hierarchical decomposition with stable IDs)?

---

## 2. Summary table

Each proposal is tagged:
- **Source:** `C` = Claude's list; `K` = Kevin's list; `B` = both
- **Tier:** 1 = top leverage, 2 = structural / bigger surface, 3 = smaller-scope, D = deferred / out-of-scope
- **Schema impact:** how invasive — `field` (add a field), `section` (new top-level dictionary section), `paradigm` (changes a core assumption)

| # | Proposal | Source | Tier | Schema impact |
|---|---|:---:|:---:|---|
| 1 | Observability as first-class on PSPECs + ArchModules | B | 1 | field |
| 2 | Async / sync / streaming / event semantics on flows | B | 1 | field |
| 3 | Dynamic AID / service fabric (vs static wire) | B | 1 | field + new diagram kind |
| 4 | Deployment topology as a distinct view from logical AFD | C | 1/2 | new diagram kind |
| 5 | DDD Bounded Contexts (vs single global dictionary) | K | 2 | paradigm |
| 6 | Orthogonal / parallel states in CSPECs (Harel) | K | 2 | field + validator |
| 7 | Backpressure / overflow strategies on ArchFlow | K | 2 | field |
| 8 | Trust boundaries + interconnect security | C | 2 | field |
| 9 | Machine-readable interface contracts from AIS | C | 3 | field |
| 10 | ADRs as first-class artifacts | C | 3 | section |
| 11 | Compute / storage tiering on data stores | K | 3 | field |
| 12 | Module kind extensions (ml_model, etc.) | C | 3 | enum extension |
| 13 | Executable specifications (Harmony-SE) | K | D | paradigm |
| 14 | Stakeholder concerns mapping (TOGAF / arc42) | C | D | section |
| 15 | CESAM 3-view (Operational/Functional/Constructional) | K | D | framing |
| 16 | Supply chain / SBOM / dependency tracking | C | D | section |
| 17 | Event sourcing patterns (state-as-events) | C | D | paradigm |
| 18 | Test coverage as a coverage metric | C | D | metric |
| 19 | SysML 2.0 / MBSE re-platform | K | D | replace methodology |
| 20 | Implementation-detail content (ring buffers, eBPF, LMAX) | K | D | not methodology |
| 21 | Budgets / Margins as first-class (mass / power / latency / cost) | N | 1 | section + field |
| 22 | Technical Performance Measures (TPMs) — tracked over time | N | 1 | section |
| 23 | Trade studies as a first-class artifact (distinct from ADRs) | N | 2 | section |
| 24 | Risk register with probability × consequence matrix | N | 2 | section |
| 25 | V&V plan per requirement / per module | N | 2 | field |
| 26 | TRL (Technology Readiness Level) on architecture modules | N | 3 | field |
| 27 | Off-nominal analysis / fault behavior PSPECs | N | 3 | paired-with-PSPEC |
| 28 | Lifecycle phase awareness (Pre-A through F) | N | 3 | metadata |
| 29 | ConOps (Concept of Operations) as a pre-Stage-1 artifact | N | D | new pre-stage |
| 30 | FFBDs (Functional Flow Block Diagrams) — time-sequenced view | N | D | new diagram kind |
| 31 | Deployment strategy + CI/CD pipeline as architectural artifact | O | 2 | field + section |
| 32 | SLI / SLO / SLA chain as a structural surface | O | 2 | section |
| 33 | Runbooks tied to alerts | O | 2 | field |
| 34 | Production-readiness criteria as a structured checklist | O | 2 | section |
| 35 | Compliance frameworks as module-level declarations | O | 2 | field |
| 36 | Agent / ML-pipeline module kinds (extension of #12) | C+real-project lens | 2 | enum extension |
| 37 | Module ownership (CODEOWNERS-style) on architecture modules | second-lens | 2 | field |
| 38 | Runtime / environment compatibility matrix on modules | second-lens | 2 | field |
| 39 | Cross-project / system-of-systems composition | second-lens | 2 | section + paradigm |

---

## 3. Tier 1 — biggest leverage, both lists agree

### 3.1 Observability as first-class on PSPECs + ArchModules (#1)

**Statement.** Every PSPEC and ArchModule declares what it observes at runtime — emitted metrics, log categories, trace spans, alert conditions. The same dictionary that records *what the bubble computes* records *what the bubble emits to operators*.

**Gap in HP.** HP's TSPEC covers timing *requirements*, and the Architecture Template's bottom-row "Maintenance & Self-Test Support" zone is a passive health-check block. Neither concept models **runtime observability** as practiced by modern SRE / observability teams.

**Modern practice.** OpenTelemetry, Prometheus metrics, structured logs, distributed tracing (Jaeger / Tempo), SLO frameworks. Every leaf component declares its observability surface; ops teams debug across services via traces and metrics.

**Fit.** Additive. New optional field on `PSpec.computational_constraints` (or alongside it) and new optional field on `ArchModule`:

```yaml
observability:
  metrics:
    - { name: "tension_samples_total", kind: counter }
    - { name: "tension_normalized_newtons", kind: gauge }
  traces:
    - { span: "tension.acquire_cycle" }
  logs:
    - { category: "tension.calibration", level: info }
  alerts:
    - { name: "tension_sensor_stuck", when: "rate(tension_samples_total[1m]) == 0" }
```

**Benefit.** Makes the methodology *operable*. The PSPEC + AMS become the source of truth for what the system emits at runtime; teams know what metrics to expect; SLO definitions can be derived from the dictionary; the gap between "what we said the system would do" and "what we can see it doing" closes.

**Cost.** Small schema growth. Validator could add a `observability_coverage_pct` metric (leaf processes that declare observability). Risk: temptation to over-specify metrics names at design time when they're properly a runtime concern — the discipline rule needs to say "declare *what* you emit, not *how*."

**Source.** Both lists. Kevin's pasted set framed it as the *single biggest missing link* in HP. Claude's list had it as #3.

---

### 3.2 Async / sync / streaming / event semantics on flows (#2)

**Statement.** Every Flow and ArchFlow declares its delivery semantics: synchronous request/response, async fire-and-forget, push notification, streaming, batched event. Whether `flow_state_to_ui` is polled at 1 Hz or pushed on change is an architectural decision the model should record, not leave implicit.

**Gap in HP.** HP flows are presumed continuous data — in 1984 the canonical flow was a sensor reading or a control voltage held at a value. Modern systems are messages, events, streams, request/response, pub/sub. The propagation semantics radically change reasoning (latency, ordering, reliability, idempotency).

**Modern practice.** Kafka, NATS, gRPC streaming, WebSockets, REST polling, GraphQL subscriptions, SQS, EventBridge. Every service interface declares whether it's sync, async, streaming, or one-shot.

**Fit.** Additive. Single field on `Flow` and `ArchFlow`:

```yaml
synchronicity: sync_request_response | async_fire_and_forget | push_notification | streaming | batched_event
delivery: at_most_once | at_least_once | exactly_once  # optional pairing
```

**Benefit.** Architecture reviews can immediately spot mismatches (e.g., a flow whose downstream assumes sync but whose upstream is async-only). Backpressure and timeout reasoning become anchored. PSPEC bodies can use the right vocabulary ("on receipt of EVENT X" vs "every cycle").

**Cost.** Small. Validator can warn on missing field at the architecture level; require it at the architecture layer but make it optional at the requirements layer.

**Source.** Both lists. Kevin's pasted set framed it as the death of the centralized CSPEC FSM model; Claude's #1.

---

### 3.3 Dynamic AID / service fabric (#3)

**Statement.** The AID can model a *fabric* — a logical communication medium provided by infrastructure (service mesh, message bus, API gateway, pub/sub topic) — not just a static wire. Modules can attach to a fabric; the fabric provides discovery, routing, retry, observability.

**Gap in HP.** The 2000 book's AID assumes physical channels (RS485, PCIe, CAN bus, shared memory). Service meshes (Istio, Linkerd, Consul Connect), API gateways (Kong, Envoy), and event buses (Kafka, NATS, RabbitMQ) didn't exist when the methodology was written. The hardwired AID maps poorly onto runtime topologies where the path from A to B is *discovered*, not wired.

**Modern practice.** Service discovery (Consul, K8s services, DNS-SD), service mesh (sidecar proxies), pub/sub topics, message brokers. The interconnect is no longer a wire; it's a programmable substrate.

**Fit.** Add a new `ArchInterconnect.fabric_kind: wire | bus | service_mesh | pubsub_topic | api_gateway | network` field. Possibly elevate fabric kinds into their own diagram-type (e.g., AFCD — Architecture Fabric Context Diagram), parallel to AID, but that's a larger surface.

**Benefit.** Distinguishes "the BLE link is hardwired between exactly two endpoints" from "the message bus carries N publishers to M subscribers." The validator can apply different rules (a wire requires ≥ 2 endpoints; a topic doesn't — it has publishers and subscribers that come and go).

**Cost.** Modest. Schema gains one field; renderer needs to differentiate visually (wire vs fabric).

**Source.** Both lists. Kevin's pasted set: "The AID is no longer a wire; it is a logical fabric." Claude's #6 (deployment topology) is a related but distinct facet — see #4 below.

---

## 4. Tier 1/2 — deployment topology as a distinct view from logical AFD (#4)

**Statement.** Separate the *logical* AFD ("what are the modules and what flows between them") from the *runtime* topology ("which Kubernetes namespace / cluster / region runs each module instance, and how many replicas"). New diagram type — DTD (Deployment Topology Diagram) — alongside AFD/AID.

**Gap in HP.** HP conflates logical architecture and physical realization in one model. In a containerized environment, a single logical `am_dashboard_app` may run as N replicas in M regions behind a load balancer, with K8s Deployments, Services, and HPA controllers. None of that fits in an AID.

**Modern practice.** Helm charts, K8s manifests, Terraform, Pulumi. Deployment topology is captured *separately* from architecture — and they need to balance with each other.

**Fit.** New top-level dictionary section: `deployment_topology:` declaring runtime placement annotations per module. Could also be done as a *new view* over existing modules (each module gains optional `deployment:` block with `namespace`, `region`, `replicas`, `placement_constraints`).

**Benefit.** Separates "what the system is" from "where it runs." Makes operational reviews possible against the same dictionary that specifies the requirements model. Captures the K8s-namespace / cloud-region reality without polluting AFD.

**Cost.** Larger schema addition. Could be deferred to Tier 2 if we want Tier 1 to be additive-only.

**Source.** Claude's list only (#6). Kevin's pasted set touched it implicitly through "service fabric" but didn't separate logical from runtime cleanly.

**Decision tradeoff:** This is between Tier 1 and Tier 2. If we add fabric kind (#3) without a separate deployment view, the fabric annotation has to do double-duty for both "what's the logical channel" and "what's the runtime infrastructure." A separate deployment view is cleaner but bigger.

---

## 5. Tier 2 — structural additions

### 5.1 DDD Bounded Contexts (#5)

**Statement.** Replace the single global Requirements Dictionary with multiple *per-context* dictionaries (or context-labeled regions within one file). Each context owns the meaning of its terms; cross-context translation is explicit (Anti-Corruption Layers).

**Gap in HP.** The Requirements Dictionary assumes one global ubiquitous language. At scale, `Node` means three different things to Orchestration, Telemetry, and Billing — forcing one definition is the wrong shape.

**Modern practice.** Eric Evans 2003, Vaughn Vernon 2013. Bounded contexts are now standard in microservice / multi-team systems. Each context has its own ubiquitous language; cross-context maps are explicit.

**Fit.** This is the biggest paradigm question on the list. Two plausible paths:
- **A. Minimal disruption.** Add `context:` field to every entity. Single `dictionary.yaml` but with labeled regions. Translation entities at boundaries (`kind: translation` entities or a new `translations:` section).
- **B. Full bounded contexts.** Split per-context dictionaries into separate files; cross-context refs require explicit ACL declarations. Like a multi-module Rust crate.

**Benefit.** Real teams can co-own different contexts without forcing global vocabulary agreement. Solves a real problem at >5 teams or >50 entities.

**Cost.** Significant. The toolkit's "one file is the truth" guarantee softens. Validator needs cross-context reference rules. The form-based proposal pattern needs to address "which context is this for?"

**Source.** Kevin's list (extensive treatment in his pasted set). Claude's list explicitly excluded it — Claude reasoned the Requirements Dictionary already IS a ubiquitous language and the mapping was implicit.

**Decision tradeoff:** Genuine paradigm shift. If we never deploy past one project's worth of contexts, this stays academic. If we plan to apply the toolkit to multi-team enterprises, this becomes essential.

---

### 5.2 Orthogonal / parallel states in CSPECs (#6)

**Statement.** Support **parallel (orthogonal) state machines** within a single bubble. A bubble can be in state `(GridTie, NormalLoad, ReadyForOverride)` simultaneously — three independent state variables, not one.

**Gap in HP.** Our current CSPEC supports *hierarchical* nesting (state_composite + parent_state) but not *parallel*. Real systems often have multiple independent state variables (e.g., a connection is `(Connected, Authenticated, Encrypted)` — three orthogonal axes).

**Modern practice.** Harel statecharts (1987 paper), UML statecharts, SCXML (W3C standard), modern reactive frameworks (XState, Statelights, Akka FSM). Orthogonal regions are bread-and-butter.

**Fit.** Add `state_parallel` as a new EntityKind alongside `state_composite`. A parallel-state container has multiple regions; each region is independent. The CSPEC renderer needs to visualize this (Mermaid `state X { region 1 -- region 2 }` syntax exists).

**Benefit.** Eliminates state-space explosion in CSPECs that today have to enumerate every cross-product. Models real reality (multi-axis state) accurately.

**Cost.** Modest schema addition; rendering complexity increases (parallel regions in Cytoscape need careful layout). Transition semantics need updates (a transition can target one region's sub-state without affecting other regions).

**Source.** Kevin's list (mentions Harel statecharts explicitly). Claude's list missed this entirely — we have hierarchical states and Claude didn't realize the parallel-state gap.

---

### 5.3 Backpressure / overflow strategies on ArchFlow (#7)

**Statement.** Every architecture flow at scale declares what happens when the downstream can't keep up. Explicit options: drop-oldest, drop-newest, spill-to-disk, block-upstream, error-out.

**Gap in HP.** Static-bandwidth assumptions. The 1984 sensor reading didn't have "what happens if the consumer is too slow" as a real concern.

**Modern practice.** Every streaming framework (Kafka, Pulsar, Reactive Streams, RxJava, Flink) has explicit backpressure semantics. Every queue declares its overflow strategy. Every async API documents its retry / dead-letter behavior.

**Fit.** Add `overflow: drop_oldest | drop_newest | spill_to_disk | block_upstream | error | buffer_unbounded` field on `ArchFlow`. Optional `buffer_size_hint:` for sizeable queues.

**Benefit.** Makes data-loss vs latency vs memory-pressure tradeoffs explicit at architecture time, not discovered in production.

**Cost.** Small. Validator can require this field for any `synchronicity: streaming | async_fire_and_forget` flow, leave it optional otherwise.

**Source.** Kevin's list. Claude's list mentioned it implicitly under "idempotency / retry semantics" but didn't formalize it.

---

### 5.4 Trust boundaries + interconnect security + threat modeling (#8)

This proposal has three layers — structural fields, a process overlay, and reference-catalog discipline. Each adds independently; together they bring HP up to modern security-engineering practice.

#### 5.4.1 Structural fields (the minimum)

**Statement.** Modules declare their trust zone; interconnects declare authentication and encryption characteristics. Threat modeling becomes part of the architecture model, not a separate document.

**Gap in HP.** Terminators are just "external"; interconnects are just "physical." STRIDE / zero-trust / mTLS / OAuth predate HP's last revision by maybe a year, and never made it in.

**Fit.** Two new optional fields:

```yaml
am_main_controller:
  trust_zone: internal_lan       # internal_lan | dmz | public | privileged

ai_ble:
  auth_required: paired_device   # none | shared_secret | mtls | oauth | paired_device | spiffe | ...
  encryption: bluetooth_le_secure  # none | tls | mtls | bluetooth_le_secure | ...
```

#### 5.4.2 Threat modeling as a process overlay (STRIDE / LINDDUN)

**Statement.** Every interconnect crossing a trust boundary carries explicit STRIDE annotations — which threat categories have been considered, and how. LINDDUN provides the privacy-focused complement for systems handling PII.

**STRIDE** (Microsoft, 1999): **S**poofing / **T**ampering / **R**epudiation / **I**nformation disclosure / **D**enial of service / **E**levation of privilege. Six threat categories that every networked interface should address (or explicitly decline to address).

**LINDDUN** (KU Leuven, 2010): **L**inkability / **I**dentifiability / **N**on-repudiation / **D**etectability / **D**isclosure / **U**nawareness / **N**on-compliance. The privacy complement; critical for AI / consumer / health systems.

**Fit.** Per-interconnect annotation:

```yaml
ai_ble:
  stride_mitigations:
    spoofing:        "Paired-device pairing prevents unauthorized peripherals"
    tampering:       "BLE LE Secure Connections (P-256 ECDH) protects in-flight"
    repudiation:     "out-of-scope (single-user session; no audit requirement)"
    info_disclosure: "AES-CCM encryption per BLE 5.0"
    denial_of_service: "Rate-limit pairing attempts; reconnect-backoff"
    elev_of_privilege: "Custom GATT service exposes only telemetry + config"
```

Validator rule: any interconnect whose endpoints span different `trust_zone` values must have `stride_mitigations:` filled in. Coverage metric: `stride_coverage_pct`.

#### 5.4.3 Reference-catalog discipline (MITRE family + others)

**Statement.** Security-related decisions reference industry catalogs by ID rather than re-deriving threats and defenses. Like how AIS already references "Bluetooth Core Spec 5.0" or "RFC 6455," security claims reference MITRE entries.

**Catalogs worth referencing:**

| Catalog | Purpose | Where it lands in HP |
|---|---|---|
| **MITRE ATT&CK** | Adversary tactics + techniques (real-world threat library) | AMS / AIS prose, ADR Context sections. "Mitigates T1078 (valid accounts) via mTLS." |
| **MITRE D3FEND** | Defensive countermeasures (companion to ATT&CK) | AMS `design_justification:` cites D3FEND techniques by ID. |
| **MITRE CWE** | Software weakness catalog (CWE-79, CWE-89, ...) | PSPEC + AMS declares which CWEs the design specifically addresses. |
| **MITRE CAPEC** | Attack pattern catalog (complements ATT&CK) | Cross-reference vocabulary in threat-model annotations. |
| **OWASP ASVS** | Application Security Verification Standard (levels 1–3) | Web-tier AMS declares target ASVS level as a constraint. |
| **NIST CSF 2.0** | Identify / Protect / Detect / Respond / Recover | Coverage metric: which architecture modules participate in which CSF function. |
| **NIST 800-53 / 800-160** | Security controls catalog (1,000+ controls); systems-security engineering | AMS `required_constraints` can cite specific control IDs. |
| **ISA/IEC 62443** | Industrial cybersecurity standards; defines Security Levels SL1–SL4 | **Directly relevant to HP's original audience** (industrial / control systems). Module-level SL declaration. |
| **IEC 61508 / 62061** | Functional safety (SIL levels) | Module `required_constraints.safety:` declares SIL. |
| **SPIFFE / SPIRE** | Service identity framework (workload identity for distributed systems) | An `auth_required:` enum value. |
| **CVSS** | Common Vulnerability Scoring System (severity 0.0–10.0) | ADRs carry CVSS scores for accepted-risk decisions. |

These don't add schema by themselves; they provide *vocabulary* for AMS / AIS / ADR / PSPEC bodies. Reference rather than duplicate.

**Threat-modeling process methodologies** (alternatives — pick one per project):
- **PASTA** (7-stage Process for Attack Simulation and Threat Analysis)
- **Trike** (risk-based threat modeling)
- **TARA** (MITRE Threat Assessment and Remediation Analysis)
- STRIDE per-element (lightweight; what 5.4.2 codifies)

#### 5.4.4 Modern practice

STRIDE threat modeling (Microsoft, 1999); MITRE ATT&CK (2013), D3FEND (2021); zero-trust architectures (Beyond Corp 2014, SPIFFE/SPIRE 2018); mTLS by default in service meshes (Istio, Linkerd); OWASP guidance (2003+); ISA/IEC 62443 (2009+, the industrial counterpart). Every interconnect either declares its security posture or it's wrong by default in 2026.

#### 5.4.5 Benefit / Cost / Source

**Benefit.** Threat modeling becomes a structured pass against the dictionary, not a separate Word doc that drifts. Validator catches unencrypted interconnects crossing trust zones. ADRs and AMS prose anchor to industry-standard vocabulary. Security audits can be performed against the dictionary as the source of truth.

**Cost.** 5.4.1 (structural fields) — small. 5.4.2 (STRIDE annotations) — modest schema; validator coverage metric. 5.4.3 (catalog references) — zero schema cost; convention/discipline only.

**Source.** Claude (security entirely missing from Kevin's pasted set — interesting blind spot given his project is an AI guardrail control plane). Security frameworks dimension surfaced by Kevin in follow-up.

---

## 5bis. Tier 1/2 additions from NASA Systems Engineering practice

These came from a separate pass against NASA SP-2016-6105 Rev 2 (the current public NASA SE Handbook, 2017) and its MBSE-adoption companion. NASA's practice has substantial structural overlap with HP — hierarchical decomposition, traceability, technical reviews, allocation — but adds a few patterns HP genuinely lacks.

### 5bis.1 Budgets / Margins as first-class (#21)

**Statement.** Add an explicit `budgets:` top-level section. The system declares budget items (latency, cost-per-request, memory, CPU, monthly $, mass, power); each architecture module is *allocated* a portion of each budget; explicit reserves / margins are declared at the system level.

**Gap in HP.** HP has `required_constraints` per module ("must be < 100 ms"), but no concept of budgets that get *allocated top-down* across modules with explicit margin. NASA practice: every spacecraft system has a mass budget, power budget, data-rate budget, schedule margin, cost margin — each a tracked artifact across the lifecycle.

**Modern equivalent.** Cloud-cost budgets per service, latency budgets allocated across microservices (e.g., 100 ms p99 end-to-end means each hop gets X ms), memory budgets per container, throughput budgets per partition. Modern SRE practice is rediscovering NASA's budget discipline.

**Fit.** New top-level dictionary section:

```yaml
budgets:
  budget_e2e_latency_p99:
    name: "End-to-end latency p99"
    unit: ms
    system_target: 100
    system_reserve: 15           # explicit margin; only allocator can claim it
    allocations:
      am_main_controller:    35
      ai_ble:                20
      am_angler_app:         30
      # Sum of allocations + system_reserve must equal system_target

  budget_cost_per_request:
    name: "Cost per processed event"
    unit: USD
    system_target: 0.0001
    allocations:
      am_controller_host:    0.00007
      am_dashboard_app:      0.00002
      ai_local_lan:          0.00001
```

Validator rule: `sum(allocations.values()) + reserve ≤ system_target`.

**Benefit.** Catches "we're already 90% of our latency budget at module 2 of 5" at design time. Forces explicit conversation about where to allocate scarce budgets. The reserve concept (NASA's contribution) makes risk-of-overrun visible.

**Cost.** New section; new validator rule per budget. Modest.

**Source.** NASA (#N1 — derived from NASA SE Handbook §6.7 "Technical Resource Management").

---

### 5bis.2 Technical Performance Measures (TPMs) — tracked over time (#22)

**Statement.** TPMs are *tracked-over-time* performance measures, distinct from static constraints. Each TPM has a current estimate, a threshold, a growth allowance, and a trend. Reviewed across lifecycle gates.

**Gap in HP.** HP's `required_constraints` are static statements ("must be < 100 ms"). TPMs are *currently-87-ms-trending-up-3-ms-per-quarter*. Different artifact: live operational metric anchored to a design constraint.

**Modern equivalent.** Modern SRE's SLO + error budget: the latency SLO is the design-time constraint; the actual measured latency is the TPM; the error budget is the growth allowance. The toolkit could be the *origin* of these — derived from the dictionary, exported to monitoring.

**Fit.** New top-level dictionary section:

```yaml
tpms:
  tpm_latency_p99:
    name: "End-to-end latency p99"
    unit: ms
    threshold: 100             # don't-cross
    target: 80                 # aim for
    current_estimate: 87
    growth_allowance: 13       # threshold - current_estimate
    measurement_method: "Distributed trace span 'event_in' → 'event_out'"
    derived_from_budget: budget_e2e_latency_p99
```

**Benefit.** Establishes the bridge from design-time constraints to runtime SLOs. Auditable record of *intended* performance vs *measured*. The growth_allowance field is uniquely NASA — it makes "how much room do we have" visible.

**Cost.** New section. Could integrate with the observability proposal (#1): the metric named in `observability.metrics` is what feeds a TPM's current_estimate.

**Source.** NASA (NASA SE Handbook §6.7.2 "Technical Performance Measures").

---

### 5bis.3 Trade studies as a first-class artifact (#23)

**Statement.** A `trade_studies:` top-level section. Each trade study captures: the decision being made, alternatives considered, evaluation criteria + weights, scores per alternative, the recommendation. Lives *before* the corresponding ADR.

**Gap in HP.** Closest current artifact is ADR's `alternatives_considered:` field — but that's a list, not structured analysis. Trade studies are the *analysis that produces a decision*; ADRs are the *decision and its consequences*.

**Modern practice.** AHP (Analytic Hierarchy Process), pugh-matrix, weighted decision matrices. NASA's `Decision Analysis and Resolution (DAR)` process formalizes this. Modern teams mostly skip it; the toolkit could re-introduce the discipline cheaply.

**Fit.** New top-level dictionary section:

```yaml
trade_studies:
  ts_001_ble_vs_wifi:
    title: "Controller-to-app transport"
    decision_drivers:
      - { name: "Power consumption", weight: 5 }
      - { name: "Range", weight: 3 }
      - { name: "Setup complexity", weight: 4 }
      - { name: "Latency", weight: 2 }
    alternatives:
      ble_5:
        scores:  { power: 5, range: 3, setup: 5, latency: 4 }
        total: 60
      wifi_direct:
        scores:  { power: 2, range: 5, setup: 2, latency: 5 }
        total: 43
    recommendation: ble_5
    references_adr: adr_005_ble_transport
```

**Benefit.** Captures the *why-among-alternatives* with quantitative rigor. Distinguishes "we considered X and Y and picked Y for these scored reasons" from "we picked Y" (ADR).

**Cost.** New section; primarily prose discipline (don't need a sophisticated validator).

**Source.** NASA (NASA SE Handbook §6.8 "Decision Analysis"; companion ECSS-E-ST-10-12C standard).

---

### 5bis.4 Risk register with probability × consequence (#24)

**Statement.** A `risks:` top-level section with quantitative likelihood/impact, ownership, status, mitigations, and links to affected modules. Distinct from ADRs (decisions) and trade studies (decision analysis).

**Gap in HP.** ADRs are not risks. AMS `required_constraints.reliability` is a static constraint, not a tracked risk. NASA practice: explicit 5×5 risk matrix; risks have lifecycle (identified → assessed → mitigated → retired); modern complement to the static reliability constraint.

**Modern equivalent.** Modern engineering teams maintain risk registers in tools like Jira / Atlassian — but they drift away from the architecture model. Anchoring risks to architecture modules in the dictionary keeps them connected to the design.

**Fit.** New top-level dictionary section:

```yaml
risks:
  risk_001_ble_interference:
    title: "BLE interference in crowded environments"
    likelihood: 3              # 1 (rare) to 5 (almost certain)
    impact: 4                  # 1 (negligible) to 5 (catastrophic)
    severity: 12               # likelihood × impact
    status: mitigated          # identified | assessed | mitigated | retired | realized
    owner: "controller team"
    affected:
      modules: [am_main_controller, am_angler_app]
      interconnects: [ai_ble]
    mitigation: |
      Adaptive channel hopping; user-visible RSSI indicator;
      degraded-mode operation if BLE drops.
    references_adr: adr_005_ble_transport
```

**Benefit.** Risk register stays anchored to the architecture model rather than drifting into a separate spreadsheet. Validator can require risks to reference real modules/interconnects.

**Cost.** New section. Modest.

**Source.** NASA (NASA SE Handbook §6.4 "Technical Risk Management").

---

### 5bis.5 V&V plan per requirement / per module (#25)

**Statement.** Each leaf process / CSPEC / architecture module declares its verification method and validation criteria. Closes the "spec said X — how do we confirm" loop.

**Gap in HP.** HP has no explicit verification surface. PSPEC says what the process does; CSPEC says state transitions; but neither says *how to confirm the implementation matches*.

**Modern practice.** NASA's V&V methods: Test / Analysis / Inspection / Demonstration. Modern teams: unit tests, integration tests, end-to-end tests, formal verification, simulation, manual inspection, demonstration to stakeholders.

**Fit.** Add `verification:` field to PSPEC + ArchModuleSpec:

```yaml
pspec_acquire_tension:
  parent_process: proc_acquire_tension
  transformation: { ... }
  verification:
    methods: [test, analysis]           # test | analysis | inspection | demonstration | formal_proof | simulation
    test_suite: "tests/test_acquire_tension.py"
    coverage_target: 95%
    validation_scenarios:
      - "Sustained 100 Hz sampling for 10 minutes without buffer overflow"
      - "Calibration drift < 0.5% over 24-hour soak test"
```

**Benefit.** Every spec carries its verification posture. Validator could check the test_suite path exists. Coverage metric: `verification_coverage_pct`.

**Cost.** New field on existing PSPEC + AMS; small. Discipline rule: verification is methodology, not testing implementation.

**Source.** NASA (NASA SE Handbook §5.3 "Product Verification" + §5.4 "Product Validation"). Also: IEEE 1012 Standard for V&V.

---

## 5ter. Tier 3 — smaller-scope NASA-derived hardenings

Items #26–#28 add small fields/sections from NASA practice. Worth mentioning; no detailed treatment.

- **TRL on architecture modules (#26).** Single integer field `technology_readiness_level: 1-9` on `ArchModule`. Useful when a project depends on technology maturity (e.g., "we're betting on TRL 9 by deployment date"). Cheap; valuable for risk-aware planning.
- **Off-nominal analysis (#27).** Pair each PSPEC with a fault-behavior counterpart. New field `off_nominal:` on `PSpec` (or new section), describing what the process does under each declared fault mode. Pairs naturally with the risk register and FMEA.
- **Lifecycle phase awareness (#28).** Metadata tag on each artifact: which lifecycle phase produced it (Pre-A / A / B / C / D / E / F). Overlay on the form-based proposal pattern — Stage 1 lock ≈ SRR (System Requirements Review); Stage 5 lock ≈ PDR (Preliminary Design Review). Mostly process discipline; useful for regulated industries.

## 5penta. Tier 2 additions from operational disciplines (DevOps / SecOps / AIOps / SRE)

These came from a separate pass against the operational disciplines that emerged 2008–2020: DevOps (CI/CD, IaC, GitOps), SecOps / DevSecOps (shift-left security, compliance), AIOps (ML on operations), and SRE (Google's SLI/SLO/error-budget discipline). All four overlap substantially with one another; the additions below pick out the structural elements that aren't already in the observability / budget / risk surface.

### 5penta.1 Deployment strategy + CI/CD pipeline as architectural artifact (#31)

**Statement.** Each `ArchModule` declares its deployment strategy and references its build/deploy pipeline. The pipeline (build → test → deploy → verify) is itself a structural artifact.

**Gap in HP.** Modern modules can't be modeled without acknowledging *how they get to production*. Blue/green vs canary vs rolling vs feature-flagged is an architectural decision with consequences (rollback time, failure blast radius, observability requirements).

**Modern practice.** GitHub Actions / GitLab CI / Jenkins / CircleCI for pipelines; ArgoCD / Flux for GitOps; Helm / Kustomize / Terraform / Pulumi for IaC; LaunchDarkly / Unleash for feature flags. Every module has a pipeline; every pipeline has stages and gates.

**Fit.** Add to `ArchModule`:

```yaml
am_controller_host:
  deployment:
    strategy: rolling           # blue_green | canary | rolling | feature_flagged | one_shot | continuous
    pipeline_ref: .github/workflows/controller-deploy.yml
    iac_refs:
      - terraform/modules/controller-host/
      - helm/charts/controller/
    rollback_budget_seconds: 60
```

**Benefit.** Captures deployment-strategy decisions as part of the architecture model. Validator could require deployment strategy be set for any module in production lifecycle phase. Pipeline reference closes the loop from "this is the architecture" to "this is how it gets built."

**Cost.** Modest. Field on `ArchModule`. Could pair with #4 (Deployment topology) as part of a broader operational-architecture surface.

**Source.** DevOps practice.

---

### 5penta.2 SLI / SLO / SLA chain as a structural surface (#32)

**Statement.** Add a `service_level_objectives:` top-level section. Each SLO declares its SLI (what's measured), target, time window, error budget, and (optionally) an external SLA. SLOs reference architecture modules + architecture flows.

**Gap in HP.** Distinct from TPMs (#22). TPMs track *measured* performance against design constraints. SLOs are *commitments* — service-level promises with explicit error budgets and consequences. The SLI → SLO → error budget → SLA chain is the modern SRE backbone.

**Modern practice.** Google SRE workbook (2018); the SLO movement (Nobl9, Datadog SLO tooling); error-budget-based release decisions. SLIs are time-series queries; SLOs are commitments; error budgets are derived; SLAs are customer-facing.

**Fit.** New top-level dictionary section:

```yaml
service_level_objectives:
  slo_event_processing_latency:
    sli:
      query: 'histogram_quantile(0.99, request_duration_seconds_bucket{service="controller"})'
      unit: seconds
    target: 0.100               # p99 < 100ms
    window: 30d                 # rolling window
    error_budget_pct: 0.1       # 0.1% of requests may exceed target
    applies_to:
      modules: [am_controller_host]
      flows: [af_state_to_dashboard]
    sla: "Customers can expect p99 event latency under 100ms 99.9% of the time over any 30-day window."
    derives_from_tpm: tpm_latency_p99   # link to the tracked measure
    runbook_on_burn: runbooks/slo-burn-event-latency.md
```

**Benefit.** Anchors SLOs to the architecture model rather than living in a monitoring tool out-of-sync with the design. Error-budget burn-rate alerts have a structural home. SLA commitments are traceable to the modules that must deliver them.

**Cost.** New section; non-trivial validation surface (the sli.query field is a referenced PromQL or equivalent, validatable only loosely).

**Source.** SRE practice (Google SRE Book + Workbook).

---

### 5penta.3 Runbooks tied to alerts (#33)

**Statement.** Every alert declaration (in the observability section, #1) carries a `runbook:` reference pointing to a markdown runbook. Validator can check the runbook file exists.

**Gap in HP.** Closes the loop from "observability declares an alert" to "operator knows what to do." Without this link, alerts become noise that operators dismiss.

**Fit.** Single optional field on each alert declaration (extends #1 observability):

```yaml
observability:
  alerts:
    - name: tension_sensor_stuck
      when: "rate(tension_samples_total[1m]) == 0"
      severity: warning
      runbook: runbooks/tension-sensor-stuck.md   # NEW
      escalation_after_min: 15
```

**Benefit.** Operational maturity captured in one field. Validator metric: `alert_runbook_coverage_pct`. The runbook itself is a markdown file with structured sections (Symptoms / Diagnosis / Resolution / Escalation).

**Cost.** Trivial schema addition; the discipline lives in keeping runbooks current.

**Source.** SRE + DevOps practice (Google SRE workbook; PagerDuty's runbook discipline).

---

### 5penta.4 Production-readiness criteria as a structured checklist (#34)

**Statement.** Each `ArchModule` declares its production-readiness checklist — the gate criteria that must be satisfied before the module can be considered "live." Overlays the Stage-5-to-running transition.

**Gap in HP.** HP has technical reviews at design gates (we modeled these via locked proposals) but no equivalent for "ready to go live in production." Modern SRE teams have production-readiness reviews (PRRs) with explicit checklists.

**Modern practice.** Google PRR checklists; Spotify's golden-path templates; AWS Well-Architected Framework reviews; Microsoft's production readiness reviews.

**Fit.** Add to `ArchModule` (or `ArchModuleSpec`):

```yaml
production_readiness:
  status: in_review              # not_started | in_review | passed | conditional | rejected
  checklist:
    slo_defined: true            # SLOs exist for this module
    dashboard_exists: true       # observability dashboard wired up
    alerts_have_runbooks: true   # all alerts in #33 have runbook refs
    on_call_assigned: true       # rotation exists
    escalation_path: true        # documented
    capacity_plan: true          # known headroom
    security_review_passed: true # SecOps sign-off
    backup_verified: false       # ← outstanding gap
    chaos_tested: false          # ← optional but recommended
    rollback_tested: true
  reviewer: "@sre-team"
  review_date: 2026-05-22
```

**Benefit.** Makes operational readiness a first-class architectural concern. Validator can compute a per-module readiness percentage and a project-level readiness metric.

**Cost.** New section per module. Discipline: the checklist contents are per-project — could ship with a default schema and allow per-project extensions.

**Source.** SRE practice (Google's PRR culture); analogous to NASA's PDR/CDR gates but operationally focused.

---

### 5penta.5 Compliance frameworks as module-level declarations (#35)

**Statement.** Each `ArchModule` declares which compliance frameworks it must satisfy. Distinct from threat modeling (#8) — compliance is about external assertions to auditors, not internal threat analysis.

**Gap in HP.** Modern systems often must satisfy SOC2 / HIPAA / FedRAMP / PCI-DSS / ISO 27001 / GDPR / etc. — each with specific evidence requirements. Compliance evidence currently lives in audit tools; tying it back to the architecture model keeps it anchored.

**Modern practice.** Drata / Vanta for SOC2 evidence collection; AWS Artifact for compliance attestations; HIPAA-eligible service designations; FedRAMP authorization boundaries. Each is a *scope* — which modules are in-scope, which are out-of-scope.

**Fit.** Field on `ArchModule`:

```yaml
am_controller_host:
  compliance:
    - framework: SOC2_Type_II
      scope: in_scope
      controls: [CC1.1, CC2.1, CC6.1, CC7.1]
      evidence_ref: compliance/soc2/controller-evidence.md
    - framework: HIPAA
      scope: out_of_scope
      rationale: "No PHI handled; out-of-scope per data-classification review."
    - framework: GDPR
      scope: in_scope
      lawful_basis: legitimate_interest
      data_categories: [config, telemetry]
```

**Benefit.** Compliance scope decisions are anchored to the architecture model. Validators / audits can be run against the dictionary. Out-of-scope rationales are captured (often more important than in-scope declarations).

**Cost.** Field per module; references to external evidence docs.

**Source.** SecOps / GRC practice. Pairs with #8 (security frameworks).

---

## 5quad. Deferred NASA-derived items

- **ConOps as a pre-Stage-1 artifact (#29).** Operational scenarios from the user's perspective. Lives *before* the Context Diagram. Useful but adds a layer the toolkit doesn't currently model; bigger paradigm question (probably out of scope for this modernization cycle).
- **FFBDs (Functional Flow Block Diagrams) (#30).** Time-sequenced functional view; DFDs show data flow without time, FFBDs add the temporal sequencing. New diagram type alongside DFD; meaningful complement but not essential — our CSPEC partially covers time via state transitions.

---

## 6. Tier 3 — smaller-scope hardenings

### 6.1 Machine-readable interface contracts from AIS (#9)

**Statement.** AIS gains a `contract:` field pointing to a machine-readable interface spec file (OpenAPI, gRPC IDL, GraphQL schema, Modbus register map, Protobuf .proto). AIS prose still describes the channel; the contract file is the source of truth for *what messages travel on it*.

**Gap in HP.** AIS is prose. Modern interfaces have machine-readable contracts.

**Fit.** Optional field; validator can check the file exists if the path is given. Small, useful, low cost.

**Source.** Claude (#4). Kevin touched it via "Protobuf messages" and "versioned contracts" without formalizing.

---

### 6.2 ADRs as first-class artifacts (#10)

**Statement.** Architecture Decision Records (Michael Nygard, 2011) as a new top-level dictionary section. Each ADR has Context / Decision / Consequences / Alternatives. AMS prose references the ADRs that drove the design.

**Gap in HP.** AMS has `design_rationale:` and `design_justification:` — close but not disciplined. ADRs are a more rigorous format with explicit alternatives-considered and consequence tracking.

**Fit.** New `adrs:` top-level section. Each ADR has `id`, `title`, `status: proposed|accepted|deprecated|superseded`, `context`, `decision`, `consequences`, `alternatives`. AMS/AIS specs can list `adrs: [adr_001_ble_choice, ...]` to cross-reference.

**Benefit.** Captures *why* the architecture is what it is in a form that survives team turnover, audits, and architectural reviews.

**Cost.** New section; small validator surface; markdown render.

**Source.** Claude only. Kevin missed it.

---

### 6.3 Compute / storage tiering on data stores (#11)

**Statement.** `Entity[kind: data_store]` gains a `tier:` field: `hot_memory`, `warm_analytical`, `cold_archive`, plus a `consistency:` annotation (`strong`, `eventual`, `causal`, `read_your_writes`).

**Gap in HP.** Data stores are flat. No way to model "this store is an in-memory ring buffer at 10 µs latency" vs "this store is a 6-month S3 archive at multi-second latency."

**Fit.** Two optional fields on the entity.

**Benefit.** Reflects modern storage reality. Performance / cost reasoning anchored at architecture time.

**Source.** Kevin (extensive). Claude touched it under "data schema as first-class" but didn't propose the tier framing.

---

### 6.4 Module kind extensions (ml_model, etc.) (#12)

**Statement.** Extend `ArchModuleKind` enum: `hardware | software | organizational | ml_model | data_pipeline | function_as_a_service`. New kinds get specialized fields when relevant.

**Gap in HP.** The 3 kinds (hardware / software / organizational) miss meaningful 21st-century categories.

**Fit.** Enum extension; new kind-specific optional fields. `ml_model` needs training-data references, model version, drift-detection observable; `function_as_a_service` needs cold-start budget, max-execution-time, trigger source.

**Source.** Claude (#10 in earlier brainstorm). Kevin didn't separate this as a top concern.

---

## 7. Deferred — out of scope for the modernization cycle

| # | Item | Why deferred |
|---|---|---|
| 13 | Executable specifications (Harmony-SE) | Major paradigm shift; would require a simulator. Real value but huge surface; would dwarf the modernization cycle. |
| 14 | Stakeholder concerns mapping (TOGAF / arc42) | Useful but feels like a TOGAF-y addition, not a core HP gap. |
| 15 | CESAM 3-view (Operational/Functional/Constructional) | Our existing Stages already implicitly cover this (Stage 1 ≈ Operational; Stages 2–4 ≈ Functional; Stage 5 ≈ Constructional). Reframing rather than adding. |
| 16 | Supply chain / SBOM / dependency tracking | Important for security/compliance but mostly orthogonal to HP's structural concerns. Could be a Tier 3 extension later. |
| 17 | Event sourcing patterns | Alternative state-modeling philosophy; doesn't fit HP cleanly without paradigm shift. |
| 18 | Test coverage as a coverage metric | Real but the toolkit's coverage metrics already work; this is just adding one more number. Low-priority once Tier 1-3 land. |
| 19 | SysML 2.0 / MBSE re-platform | Replaces the methodology rather than extending it. Out of scope. |
| 20 | Implementation-detail items (ring buffers, LMAX, eBPF, kernel bypass) | Implementation patterns that go *inside* an AMS body or design_rationale field, not new methodology surface. Conflating "what should HP model" with "how should you build a specific ingest module" — they're different layers. |

---

## 8. Cross-cutting observations

**On the "What HP misses" question, both lists converge most strongly on:**
1. Runtime visibility (observability)
2. Async/event semantics (HP assumes synchronous-data)
3. Dynamic infrastructure (HP assumes static interconnects)

**Where the lists differ tells us something:**
- Kevin's set emphasizes **performance, scale, and distribution** (ring buffers, backpressure, bounded contexts, async events). Blind spot: security / threat modeling, decision rationale capture, budgets / margins.
- Claude's set emphasizes **observability, security, and decision discipline** (trust zones, ADRs, machine-readable contracts). Blind spot: parallel states, bounded contexts, storage tiering, budgets / TPMs.
- NASA SE practice emphasizes **disciplined accounting** (budgets, margins, TPMs, risks, V&V, trade studies). Blind spot: nothing missing from a structural standpoint, but skews toward heavyweight processes appropriate for spacecraft, possibly overkill for typical software systems.
- Operational disciplines (DevOps / SecOps / SRE) emphasize **the architecture-to-running bridge** (deployment strategies, SLOs, runbooks, production readiness, compliance). Blind spot: weak on design-time discipline (assumes you already have a coherent design); strong on operational realism. The natural complement to NASA's design-time accounting.

The union covers a meaningfully complete picture of what 35 years of SE + 35 years of computing + 15 years of cloud-ops evolution looks like. The intersection of all four (observability + async + dynamic interconnect + budgets + SLOs) is the smallest safe-bet set, and notably each of the four sources surfaced something the others missed.

**HP's existing strengths NOT to lose during modernization:**
- Strict separation of *what* (requirements) and *how* (architecture)
- Balancing rules as hard validation
- Hierarchical decomposition with stable IDs
- Dictionary as single source of truth (carefully — this tension with bounded contexts)
- Form-based proposal pattern (our addition; preserve)
- Diagrams + structured text together (no diagrams-only or text-only)

**HP's already-implicit modern wins** (worth noting we don't need to add):
- Our Stage 5 already does allocation as a first-class navigable relationship, which is SysML's «allocate». We're closer to MBSE than the pasted set realizes.
- Our Stages 1→5 progression already aligns with CESAM's Operational/Functional/Constructional split.
- Our form-based proposal pattern IS executable methodology — the proposal markdown drives toolkit code.

---

## 8.5 Prioritization lens — patterns from a real modern project

To stress-test the modernization list against a realistic 21st-century target, we did an IP-firewalled, read-only inspection of a real in-flight project (Kevin's `cloudctlplane` — kept anonymous; no IP-specific names, components, or architecture details land in this doc). The aim is *pattern-level signal*: which modernization items would have most helped a project of *this shape*?

### What we observed at the pattern level

- **Scale.** ~1,600 files; ~16,400 entities; ~32,000 edges; ~615 communities (per knowledge-graph extraction). 15–17 top-level subprojects mixing services, libraries, tools, and agent components.
- **Polyglot stack.** Rust + Python + TypeScript + Go — separate CI templates per language; each language tends to map to a different bounded context.
- **Observability infrastructure already deployed.** Prometheus + Grafana + VictoriaMetrics in the runtime config; observability is solved at the *infrastructure* layer but not at the *architectural model* layer.
- **Deployment infrastructure present.** Both Terraform and Kubernetes manifests; multi-target IaC patterns.
- **CI/CD discipline.** Per-language pipeline templates; a dedicated security CI template; gitleaks for secrets scanning.
- **Auth boundary visible.** A discrete auth-service community shows up in the graph — trust-zone crossings are real, but no `THREAT_MODEL.md` or formal STRIDE pass appears in the file structure.
- **Event-driven + pipeline patterns.** Events models and explicit pipeline communities suggest async / event-driven architecture rather than synchronous data flow.
- **Multi-agent / AI layer.** Distinct agent communities (multi-agent code) — a 21st-century module category HP doesn't anticipate.
- **Heavy doc culture, informal structure.** 563 markdown docs in the repo. Proposals directory with formal proposals. Architecture docs subdirectory. But: no ADRs by that name, no SLO definitions as structured files, no runbook discipline as file-based artifacts.
- **Spec-vs-reality tracking already happening informally.** A "deviation-from-PRD-phase-1.md" implies the team already tracks where reality drifted from specification — exactly what HP gives you *formally* and *continuously*.
- **AI-output auditing already happening.** A "slop-audit-…" doc implies discipline around AI-generated content quality — consistent with the form-based-proposal pattern's value proposition.

### What this pattern tells us about the modernization items

Mapping each modernization item to its likelihood of payoff on a project of this shape:

**Tier A — directly addresses an observed gap or pain on this project pattern:**

| # | Item | Why it would have helped |
|---|---|---|
| 1 | Observability as first-class | Infrastructure is there (Prom/Graf/VM) but the architecture model has nowhere to declare which metrics each module emits — leading to dashboards and metrics drifting from the design |
| 2 | Async / sync / streaming / event semantics | Events + pipeline communities visible; flows are clearly mixed sync/async; current methodology can't distinguish |
| 5 | DDD Bounded Contexts | At 615 communities and a polyglot 4-language stack, a single global Requirements Dictionary is the wrong shape — each subproject already operates as its own bounded context |
| 8 | Trust boundaries + interconnect security | Auth-service exists as a distinct module → real trust zones; no formal STRIDE pass visible → the structural opportunity is wide open |
| 10 | ADRs as first-class | 563 .md docs but no formal ADR discipline — the team is *already* writing decision docs, just without the structured Context/Decision/Consequences/Alternatives format |
| 21 | Budgets / Margins | Cloud-cost + latency + memory budgets are real concerns at this scale; the methodology would give them a home |
| 22 | TPMs (tracked over time) | "Deviation from PRD" doc proves the team is already tracking spec-vs-reality; TPMs formalize this practice |
| 31 | Deployment strategy + CI/CD pipeline | Terraform + K8s + multi-language CI templates already exist; the architecture model should reference these as artifacts, not duplicate the info |
| 32 | SLI/SLO/SLA chain | Observability infra present, but no SLO files visible → SLO definitions live in dashboards (drift-prone) instead of the dictionary |
| 33 | Runbooks tied to alerts | No runbooks/ dir visible despite alert-capable infra; the methodology would force the alert↔runbook link |
| 34 | Production-readiness criteria | A multi-team, multi-agent project at this scale benefits from PRR-style structured gates before subsystems go live |

**Tier B — useful but not directly addressing an observed gap:**

| # | Item | Notes |
|---|---|---|
| 3 | Dynamic AID / service fabric | Service-mesh patterns probably implicit; would clean up but not addressing an *observed* gap |
| 4 | Deployment topology as separate view | Overlaps with #31; pick one |
| 7 | Backpressure on flows | Event/pipeline patterns suggest this is real; less visible without reading IP |
| 9 | Machine-readable contracts from AIS | Polyglot stack benefits from formal contracts at language boundaries |
| 11 | Storage tiering | Prometheus/Grafana/VictoriaMetrics + likely Dgraph/ClickHouse imply real tier choices being made |
| 12 | Module kind extensions (agent / ml_model) | Multi-agent code visible → `agent` as a kind would be a real addition |
| 23 | Trade studies | Useful at this scale but the team is already proposal-heavy; lower marginal value |
| 24 | Risk register | Useful but ADRs (#10) probably go first |
| 25 | V&V plans | Useful; would land naturally alongside production-readiness (#34) |
| 35 | Compliance | Depends on customer/regulatory exposure not visible from structure |

**Tier C — lower priority for this project pattern:**

Items #6 (orthogonal states), #26 (TRL), #27 (off-nominal), #28 (lifecycle phases), #29 (ConOps), #30 (FFBDs) — these are mostly relevant to safety-critical, embedded, or aerospace contexts. They don't surface as obvious wins on a cloud-control-plane pattern.

### What the lens changes about the recommendation

The previous recommendation (Tier 1 core + NASA budgets/TPMs + operational SLOs/runbooks) **survives the real-project pressure test** — every item in Section 10's "go first" recommendation maps to an observable gap in the project pattern.

Two items get **promoted** by this lens:
- **#5 (Bounded Contexts)** — at 615 communities + polyglot stack, this is no longer just "compelling but bigger surface." It's *essential* for the toolkit to be applicable to a project of this scale at all. Without bounded contexts, the global dictionary becomes unmaintainable past ~50 entities.
- **#10 (ADRs)** — 563 doc files with no formal ADR structure tells us that *the team is already writing decisions* but without the discipline. Adding ADRs is high-leverage retroactive cleanup; the demand is observable in the file structure.

Two items get **deprioritized** by this lens:
- **#6 (Orthogonal/parallel states)** — useful but not surfaced by the cloud-control-plane pattern. Worth keeping in the list but lower priority for the first modernization pass.
- **#29 (ConOps) and #30 (FFBDs)** — confirmed out-of-scope.

One **new item should be added**:
- **#36 — Agent / ML-pipeline module kind (extension of #12).** The multi-agent layer in the observed project is genuinely a 21st-century module category. The toolkit's `ArchModuleKind` currently has `hardware | software | organizational`; modern AI-bearing systems want `software_agent`, `ml_model`, `ml_pipeline`, possibly `llm_endpoint` as first-class kinds.

### Caveats on this lens

- **Single-project sample.** One real project pattern; n=1. Other modern projects (e.g., a heavily-regulated fintech, an embedded IoT platform, a high-frequency trading system) would weight the list differently. The lens here is biased toward cloud-control-plane / multi-agent / observability-heavy projects. *(See Section 8.6 for a second sample.)*
- **No reading of IP content.** Observations are purely structural — file counts, directory shape, knowledge-graph community structure, presence/absence of common file patterns. Nothing about the project's actual *function* or *implementation* leaks into this analysis.
- **Absence isn't proof.** "No `THREAT_MODEL.md` in file structure" doesn't prove no threat modeling happened — it could live in a wiki or be implicit in code review. But absence-from-file-structure is a real signal about *whether the discipline is treated as a first-class artifact*.

---

## 8.6 Second prioritization lens — a kernel-adjacent enforcement layer

A second IP-firewalled, read-only inspection on a sibling project at a *different system tier* — the lower sensor + policy-enforcement layer that pairs with the cloud control plane reviewed in Section 8.5. Same IP-firewall discipline: pattern-level signal only, no project-specific names or details. Two samples isn't statistical proof but it lets us distinguish *cross-cutting modern signal* from *project-specific noise*.

### What we observed at the pattern level

- **Scale and language mix is fundamentally different.** ~238,000 files, but ~166,000 are kernel source (C, H, DTS, DTSI files) — this stack vendors Linux kernel trees targeting **three different kernel versions** for ABI compatibility. The actual project-owned code is much smaller; the bulk is the kernel itself.
- **Dominant languages:** C/kernel + Rust (performance-critical userspace services) + Python (analytical models) + Java + PHP (language bindings). Polyglot but skewed toward systems languages.
- **Kernel-userspace boundary is a first-class architectural concern.** A kernel-sensor module bridges kernel-side observation to userspace daemons. This is a tier boundary with very different concurrency, latency, and reliability semantics than cloud-service-to-cloud-service.
- **Hardware-description files (device tree, DTS/DTSI) present.** HP's classical strength — embedded systems, hardware abstraction layers — is genuinely relevant here. A modernized HP that drifts too far toward cloud-native loses applicability to this kind of stack.
- **Observability instrumentation already wired** via OpenTelemetry references (different stack from the control plane's Prometheus/Grafana/VictoriaMetrics — but same *concern*).
- **Per-area team ownership made explicit** via CODEOWNERS at the repo root. Multi-team project; team boundaries align with subsystem boundaries.
- **Tiny formal-doc footprint** (~90 .md files for a project of substantial scope) — even less formal-documentation discipline than the control plane sample.
- **Explicit testing infrastructure.** A dedicated testing subproject plus a sensor_tests directory inside the sensor framework. Testing is treated as a first-class concern at the project structure level.
- **No proposals/, no ADR/, no threat-model file, no SLO files** — same gaps as the control plane, even starker here.

### What this second sample reveals that the first lens missed

1. **Runtime / environment compatibility as a first-class architectural concern.** Three kernel versions targeted simultaneously (5.10, 6.1, 6.12) is itself an architectural decision with consequences (ABI surface to test, conditional-compilation surface, support-window calculus). Cloud-side projects rarely surface this so explicitly. HP has no concept of "this module must work across kernel ABI versions X–Y" or "this client must work on iOS 15+." Could be a sub-aspect of #34 (production readiness) or a new field.

2. **Hardware-abstraction layers / device-tree-style hardware descriptions** are real artifacts at this tier. HP's classical strength is here — but the modernization pass has drifted entirely toward cloud-native concerns. We should keep at least one foot in HP's original embedded territory.

3. **Module ownership as a first-class field.** CODEOWNERS-style explicit "team X owns this module" is genuinely missing from HP and from the existing modernization list. At multi-team scale, ownership is what makes Bounded Contexts (#5) operationalizable in practice.

4. **Multi-tier system-of-systems composition.** This project is the *enforcement layer* that pairs with the *control plane* (Section 8.5's sample). HP's `Project` currently models one project's worth of dictionary. Real systems are compositions where one project's terminator is another project's `sys_root`. We probably need either a `linked_project:` reference concept, or explicit "external system" entries that point at sibling repositories.

5. **Microsecond-level latency budgets** become essential at the kernel-sensor tier. Reinforces #21 (Budgets) and #22 (TPMs) — they aren't just nice-to-have for safety-critical projects; they're load-bearing for any low-latency stack.

6. **V&V (#25) gets reinforced earlier in the priority list.** Both projects have dedicated testing infrastructure; at the sensor tier, testing is *visibly* a first-class concern (separate testing subproject + sensor_tests dir). The toolkit's V&V plans should ship with Tier 1.

### Cross-project signal: what holds across both lenses

Items that show up as gaps in *both* projects (cloud control plane *and* kernel enforcement layer) — these are the most defensible additions because they're not project-specific noise:

| # | Item | Cross-project signal |
|---|---|---|
| 1 | Observability as first-class | Both projects have observability *infra* deployed but neither has the architectural model declaring what each module emits |
| 8 | Trust boundaries + security | Both have real trust crossings (auth-service, kernel↔userspace boundary) but neither has a formal threat-model file |
| 10 | ADRs | Both have many docs but no structured ADR format |
| 21 | Budgets | Both have multi-axis budget concerns (cost/latency for cloud; latency/memory for kernel) |
| 22 | TPMs | Both have informal spec-vs-reality tracking but no structured TPM artifacts |
| 25 | V&V plans | Both have testing infrastructure but no V&V plan as a first-class architectural artifact |
| 32 | SLI/SLO/SLA | Neither has formal SLO files |
| 33 | Runbooks tied to alerts | Neither has a runbooks/ directory |

### Cross-project signal: where the projects differ

- **Module kinds.** Cloud project surfaces agent / ml_model needs (→ #36). Kernel project surfaces hardware-driver / kernel-module / userspace-daemon / device-tree-binding needs. The `ArchModuleKind` enum needs more category granularity than the current hardware / software / organizational trio — possibly *much* more.
- **Backpressure (#7) and Storage tiering (#11)** are more visible signals in the cloud project (event/pipeline patterns; multiple persistence tiers). Less visible at the kernel tier.
- **Bounded Contexts (#5)** are visible as community structure in the cloud project and as CODEOWNERS-derived team boundaries in the kernel project. Both signal high payoff, by different mechanisms.

### What changes with two lenses

New items surfaced by the second lens (added below to the summary table):

- **#37 — Module ownership (CODEOWNERS-style) on architecture modules.** Explicit team-ownership field. Important for any multi-team project; closes the loop between architecture decomposition and organizational structure (Conway's Law made explicit).
- **#38 — Runtime / environment compatibility matrix on modules.** "Works on kernel ABI 5.10–6.12" or "iOS 15+" or "Python 3.11+". Non-functional constraint that crosses architecture and operations.
- **#39 — Cross-project / system-of-systems composition.** A project's terminator can be another project's `sys_root`. Need a `linked_project:` reference field and the validator + renderer needs to support cross-project navigation.

Items that get **promoted** by the second lens:
- **#25 (V&V plans)** — from Tier 2 to Tier 1. Both projects treat testing as a first-class concern at the project-structure level; the methodology should match.
- **#5 (Bounded Contexts)** — already promoted by Section 8.5; this lens *triples down*. Multi-team + multi-tier + multi-language projects can't function on a single global dictionary.

Items the second lens **doesn't change**:
- The previous Tier 1 picks (#1, #2, #3, #21, #22, #32, #33, #10) all still map to observable gaps.
- #6 (orthogonal states) — interesting case: the kernel-side has multi-mode reactive state machines (interrupt context vs syscall context vs softirq), so orthogonal states might be more relevant here than Section 8.5 suggested. Tentatively reinstate to Tier 2.

### Caveat for this second sample

- The kernel project's massive file count is mostly vendored Linux kernel source — most of those 238k files are NOT project-owned code. Without reading content, we can't separate "the team's own code" from "vendored kernel." File-count signal alone should be discounted.
- "Kernel-sensor enforcement" is a specific architectural pattern (probably eBPF-adjacent given the modern context). Other lower-tier projects — embedded firmware, RTOS, FPGA / VHDL toolchains — would surface yet different patterns.
- Two samples is better than one but still n=2. A third sample from a yet-different system tier (e.g., a regulated/safety-critical project, or a high-frequency-trading low-latency system) would strengthen the cross-cutting signal further.

---

## 9. Open questions for the convergence pass

- **Tier 1 alone (3 items) vs Tier 1+2 (8 items)?** Tier 1 is unambiguously valuable and additive. Tier 2 includes the genuinely paradigm-shifting Bounded Contexts question, which deserves its own debate.
- **For #4 (deployment topology):** does it warrant a *new diagram type* (DTD) or is it just annotations on existing modules? The first is more honest about runtime/logical separation; the second is cheaper.
- **For #5 (Bounded Contexts):** minimum-disruption (label entities with context) vs full split (separate files per context)? Depends on whether we expect the toolkit to scale to >50-entity projects with multiple teams.
- **For #20 (implementation patterns):** should we capture some of Kevin's pasted ring-buffer / LMAX content as a *reference pattern library* (e.g., `toolkit/patterns/high-throughput-ingest.md`) that AMS bodies can link to? It's valuable content even if not new methodology.
- **Source-attribution:** Kevin's pasted set came from a separate AI tool; some of its content (especially the Rust implementation deep-dive) reads as AI-generated explanation rather than original methodology proposal. Worth treating as a brainstorm input, not an authoritative source.

---

## 10. Recommendation (Claude's read; convergence pending)

If we want one clear "modernization landing" on `kg/meld-tech-2026` that meaningfully advances the toolkit without overcommitting:

**Pursue core Tier 1 first — #1, #2, #3.** All additive, all validatable, all consensus across lists. Schema impact is small (three fields). Lived examples drop straight onto solar's BLE/HTTP flows and fishing-rig's BLE flow. Roughly the same effort as the Stage 4 PSPECs implementation.

**Then layer in NASA Tier 1 — #21 (Budgets) and #22 (TPMs).** Both are concrete, fit HP cleanly, and bring the modern SRE / budget-discipline dimension that the Claude/Kevin lists missed. Budgets without TPMs is half the picture — they pair naturally (TPMs measure consumption against the allocated budget; the growth_allowance field becomes meaningful only against a declared budget).

**Then layer in operational Tier 2 — #32 (SLI/SLO/SLA chain) and #33 (Runbooks).** These complete the design-time-to-runtime bridge: budgets (#21) declare design intent; TPMs (#22) track current state; SLOs (#32) commit to external promises; runbooks (#33) close the loop to operator action. The four together are the modern SRE backbone, anchored to the architecture model rather than living in disconnected monitoring tools.

**Then debate Tier 2 — #5 (Bounded Contexts), #8 (Trust boundaries + security), #23 (Trade studies), #24 (Risks), #25 (V&V), #31 (Deployment strategy), #34 (Production readiness), #35 (Compliance).** These are the highest-value structural additions. #5 is a paradigm question deserving its own ARCH_DESIGN.md-style book-faithful grounding (Eric Evans 2003, Vaughn Vernon 2013). #8 is small but high-impact for any networked system. #23/#24/#25 form a coherent NASA-derived "engineering rigor" subsystem. #31/#34/#35 form a coherent operations-discipline subsystem (DevOps + SRE + SecOps). Pick what matches the target audience: regulated/safety-critical projects benefit most from #23/#24/#25; cloud-native projects benefit most from #31/#34/#35.

**Defer Tier 3 + Deferred** until Tier 1 + 2 land. Pick selectively based on actual project needs.

---

## 11. Next step

Kevin reviews this enumeration; we converge on which subset to actually pursue; a dedicated design doc (e.g., `MODERNIZATION_DESIGN.md`) captures the locked decisions; implementation follows the now-familiar Stage 4 / Stage 5 cadence (model → validator → renderer → skill → lived example).
