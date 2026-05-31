# Modernization Design — 21st-Century Additions to HP

**Status:** ✅ shipped — design locked 2026-05-22; all nine items have model classes + validators + renderers landed. Quick map: #2 → `FlowSynchronicity`/`FlowDelivery`; #25 → `VerificationPlan`; #8.1 → `TrustZone`/`AuthRequired`/`Encryption`; #10 → `ADR` + [`render/adr.py`](hp_toolkit/render/adr.py); #21 → `Budget`; #22 → `TPM`/`TPMDirection`; #1 → `Observability`/`SLI`/`Metric`/`Trace`/`LogCategory`/`Alert`; #33 → runbook render path in [`render/markdown_artifact.py`](hp_toolkit/render/markdown_artifact.py); #32 → `SLO`. Body sections describe the as-locked design; spot-check against current code if reviewing a specific sub-item.
**Branch:** `kg/meld-tech-2026`.
**Audience:** the implementation pass that adds the top-9-of-10 modernization items to the toolkit.
**Why this exists:** the brainstorm + analysis lives in [`../proposals/MODERNIZATION.md`](../proposals/MODERNIZATION.md). This doc locks the *implementation* decisions for the 9 items that are additive (item #5 — Bounded Contexts — is a paradigm shift; see [`BOUNDED_CONTEXTS_DESIGN.md`](BOUNDED_CONTEXTS_DESIGN.md)). Same shape as [`PSPEC_DESIGN.md`](PSPEC_DESIGN.md) and [`ARCH_DESIGN.md`](ARCH_DESIGN.md).

**Scope (items locked here):** #2, #8, #10, #21, #22, #25, #32, #33, #1 — nine items, organized into four commit-sized chunks.

**Sources:** every load-bearing assertion cites its source. Mix of book-grounded (NASA SE Handbook 2017; SRE Workbook 2018), industry-standard (STRIDE 1999; ADR 2011), and consensus-cross-list (observability + async semantics — both Claude/Kevin brainstorm lists agreed).

---

## 1. The chain that emerged

The 9 items connect into a coherent **design-intent → runtime-commitment chain** that runs across the toolkit's existing surface:

```
DESIGN TIME                                          RUNTIME
┌────────────────────────┐                ┌──────────────────────────┐
│ #21 Budgets            │                │ #32 SLOs                 │
│ Declare design intent  │───┐         ┌─▶│ Commit external promise  │
│ Allocate to modules    │   │         │  │ Define error budget      │
│ Reserve margin         │   │         │  │                          │
└────────────────────────┘   │         │  └──────────────────────────┘
                             ▼         │              │
                  ┌──────────────────────┐            │
                  │ #22 TPMs             │            │
                  │ Tracked over time    │            ▼
                  │ Growth allowance     │  ┌──────────────────────┐
                  │ current_estimate     │  │ #33 Runbooks         │
                  └──────────────────────┘  │ Tied to alerts        │
                             ▲              └──────────────────────┘
                             │                          ▲
                  ┌──────────────────────┐              │
                  │ #1 Observability     │──────────────┘
                  │ Metrics / Traces /   │  (alerts trigger runbooks)
                  │ Logs / Alerts        │
                  └──────────────────────┘

PLUS — independent additions (no chain dependencies):
  #2  Async / sync semantics on flows
  #8  Trust boundaries + security + threat modeling
  #10 ADRs as first-class
  #25 V&V plans
```

Cross-references between items are first-class — `tpms.<id>.derived_from_budget`, `slos.<id>.derives_from_tpm`, `slos.<id>.runbook_on_burn`, etc. — and validator rules enforce them.

---

## 2. Items #2, #25, #8.1, #10 — small additive fields (Commit 1)

### 2.1 #2 — Synchronicity / delivery semantics on flows

**Schema additions.** New enum + two optional fields on both `Flow` and `ArchFlow`:

```python
class FlowSynchronicity(str, Enum):
    """How a flow propagates between endpoints.

    Source: Reactive Streams spec; Kafka delivery semantics; gRPC streaming;
    AMQP message patterns; AWS SQS docs."""
    SYNC_REQUEST_RESPONSE = "sync_request_response"  # caller blocks on response
    ASYNC_FIRE_AND_FORGET = "async_fire_and_forget"  # caller doesn't wait
    PUSH_NOTIFICATION     = "push_notification"      # producer pushes on event
    STREAMING             = "streaming"              # continuous data flow
    BATCHED_EVENT         = "batched_event"          # periodic batched delivery
    CONTINUOUS            = "continuous"             # HP-classical: held signal

class FlowDelivery(str, Enum):
    AT_MOST_ONCE  = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE  = "exactly_once"
```

Both `Flow` and `ArchFlow` gain `synchronicity: Optional[FlowSynchronicity]` and `delivery: Optional[FlowDelivery]`.

**Validator.** Warn at the architecture level if `synchronicity` is unset on an `ArchFlow`. Optional at the requirements level (Flow). The default-unset semantics mean older dictionaries don't break.

**Renderer.** Mermaid + D2 + Cytoscape edge label gains a synchronicity suffix when set (`"label (async)"`, `"label (streaming)"`). Distinct edge style per synchronicity (sync = solid, async = dashed, streaming = double-arrow).

### 2.2 #25 — V&V plans

**Schema additions.** New optional block on `PSpec` and `ArchModuleSpec`:

```python
class VerificationMethod(str, Enum):
    TEST          = "test"            # automated test
    ANALYSIS      = "analysis"        # mathematical / model-checking analysis
    INSPECTION    = "inspection"      # code review / static analysis
    DEMONSTRATION = "demonstration"   # human-witnessed runtime demonstration
    FORMAL_PROOF  = "formal_proof"    # formal verification
    SIMULATION    = "simulation"      # simulator / emulator

class VerificationPlan(BaseModel):
    methods: list[VerificationMethod]
    test_suite: Optional[str] = None         # path to test suite (relative)
    coverage_target: Optional[float] = None  # 0.0–100.0
    validation_scenarios: list[str] = Field(default_factory=list)
```

`PSpec.verification: Optional[VerificationPlan]` and `ArchModuleSpec.verification: Optional[VerificationPlan]`.

**Validator.** Warn if `test_suite` path doesn't exist on disk. Coverage metric: `verification_coverage_pct` = (PSpecs + AMSs with a verification block) / (total).

**Renderer.** PSPEC markdown sidecar gains a "## VERIFICATION" section. AMS sidecar gains a "## VERIFICATION" section.

**Source.** NASA SE Handbook §5.3 (Product Verification) + §5.4 (Product Validation); IEEE Std 1012-2016 (Standard for System, Software, and Hardware V&V).

### 2.3 #8.1 — Trust boundaries + interconnect security (structural fields)

**Schema additions.** Three new optional fields:

```python
class TrustZone(str, Enum):
    PUBLIC_INTERNET = "public_internet"
    DMZ             = "dmz"
    INTERNAL_LAN    = "internal_lan"
    PRIVILEGED      = "privileged"
    KERNEL          = "kernel"           # for low-level / OS-bridge modules
    AIR_GAPPED      = "air_gapped"

class AuthRequired(str, Enum):
    NONE          = "none"
    SHARED_SECRET = "shared_secret"
    OAUTH         = "oauth"
    OIDC          = "oidc"
    MTLS          = "mtls"
    JWT           = "jwt"
    SPIFFE        = "spiffe"
    PAIRED_DEVICE = "paired_device"
    CUSTOM        = "custom"             # described in AIS prose

class Encryption(str, Enum):
    NONE                  = "none"
    TLS                   = "tls"
    MTLS                  = "mtls"
    BLUETOOTH_LE_SECURE   = "bluetooth_le_secure"
    AT_REST_DISK          = "at_rest_disk"
    APPLICATION_LAYER     = "application_layer"
    CUSTOM                = "custom"
```

`ArchModule.trust_zone: Optional[TrustZone]`, `ArchInterconnect.auth_required: Optional[AuthRequired]`, `ArchInterconnect.encryption: Optional[Encryption]`.

**Validator.** Warning when an `ArchInterconnect` connects two modules in different `trust_zone`s but has `auth_required == NONE` or `encryption == NONE`. This is the threat-zone-crossing-without-mitigation check.

**Renderer.** Cytoscape AID side-panel shows trust zone for each module and auth + encryption for each interconnect.

### 2.4 #10 — ADRs as first-class

**Schema additions.** New top-level dictionary section + Pydantic class:

```python
class ADRStatus(str, Enum):
    PROPOSED   = "proposed"
    ACCEPTED   = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"

class ADR(BaseModel):
    """Architecture Decision Record — Michael Nygard 2011 format."""
    id: str
    title: str
    status: ADRStatus
    date: Union[date, str]
    author: Optional[str] = None
    context: str            # required — what's the situation?
    decision: str           # required — what did we decide?
    consequences: str       # required — what follows from this?
    alternatives: list[str] = Field(default_factory=list)
    # Cross-references — which model elements this decision affects
    affects: dict[str, list[str]] = Field(default_factory=dict)
    # e.g.: {modules: [am_x], interconnects: [ai_y], flows: [...]}
    supersedes: Optional[str] = None     # id of an ADR this replaces
```

`Project.adrs: dict[str, ADR] = Field(default_factory=dict)`. Loader picks up `adrs:` section like the others.

**Validator.** Reference integrity on `affects`. `supersedes` refers to a real ADR with `status: superseded`. Date format validation.

**Renderer.** New `hp_toolkit/render/adr.py` emits one markdown file per ADR at `adrs/<id-short>.md`:

```markdown
# ADR-001 — BLE chosen for controller-app transport

**Status:** Accepted (2026-05-22)
**Author:** Kevin Glavin

## CONTEXT
[from ADR.context]

## DECISION
[from ADR.decision]

## CONSEQUENCES
[from ADR.consequences]

## ALTERNATIVES CONSIDERED
- WiFi Direct (rejected: power budget)
- Custom 433 MHz radio (rejected: regulatory complexity)

## AFFECTS
- Modules: `am_controller`, `am_angler_app`
- Interconnects: `ai_ble`
- Flows: `af_telemetry_to_app`, `af_config_to_ctrl`
```

**Source.** Michael Nygard, "Documenting Architecture Decisions" (2011 ThoughtWorks blog post; subsequently a community standard). Modern updates: MADR (Markdown Architecture Decision Records) template.

---

## 3. Items #21, #22 — design-time discipline (Commit 2)

### 3.1 #21 — Budgets / Margins

**Schema additions.** New top-level section + Pydantic class:

```python
class Budget(BaseModel):
    id: str
    name: str
    unit: str                             # ms, USD, MB, watts, ...
    system_target: float                  # total system-level target
    system_reserve: float = 0             # margin held at system level
    allocations: dict[str, float] = Field(default_factory=dict)
    # key = ArchModule id; value = allocated amount in `unit`
    notes: Optional[str] = None
```

`Project.budgets: dict[str, Budget] = Field(default_factory=dict)`.

**Validator.** Hard rule: `sum(budget.allocations.values()) + budget.system_reserve ≤ budget.system_target`. Also: every key in `allocations` must reference a real `ArchModule`.

**Coverage metric.** `budget_allocation_completeness_pct` = (allocated_total + reserve) / system_target. A budget is "fully allocated" at 100%.

**Renderer.** New section in the architecture sidecars summarizing per-module budget consumption ("This module consumes 35ms of the 100ms end-to-end latency budget"). Mermaid renderer could grow a budget-tree diagram.

**Source.** NASA SE Handbook §6.7 (Technical Resource Management) — mass/power/data-rate budgets are NASA mission-engineering staples; cloud-native projects need the same discipline applied to latency/cost/memory/throughput.

### 3.2 #22 — TPMs (Technical Performance Measures)

**Schema additions.** New top-level section:

```python
class TPMDirection(str, Enum):
    LESS_IS_BETTER = "less_is_better"   # threshold is a ceiling (latency, cost, mass)
    MORE_IS_BETTER = "more_is_better"   # threshold is a floor (uptime, MTBF, accuracy)

class TPM(BaseModel):
    """Technical Performance Measure — tracked over time."""
    id: str
    name: str
    unit: str
    direction: TPMDirection = TPMDirection.LESS_IS_BETTER  # surfaced during impl
    threshold: float                      # don't-cross (ceiling or floor by direction)
    target: Optional[float] = None        # aim for
    current_estimate: float
    growth_allowance: float               # safety margin in the direction of threshold
    measurement_method: str
    derived_from_budget: Optional[str] = None     # cross-ref to Budget id
    derived_from_slo: Optional[str] = None        # cross-ref to SLO id (#32)
    trend_notes: Optional[str] = None
```

**Note on `direction:`** — surfaced during Commit 2 implementation when authoring a BLE-uptime TPM. Less-is-better TPMs (latency, cost) treat the threshold as a ceiling: `current + growth_allowance ≤ threshold`. More-is-better TPMs (uptime, MTBF, accuracy, throughput) treat it as a floor: `current − growth_allowance ≥ threshold`. NASA SE Handbook §6.7.2 handles both directions; missing this distinction would either falsely error on healthy uptime TPMs or silently miss real breaches on safety TPMs.

**Validator.** Direction-aware threshold rule (hard). `derived_from_budget` references a real Budget; `derived_from_slo` references a real SLO (resolvable once #32 lands).

**Coverage metric.** `tpm_within_threshold_pct` = (TPMs where current_estimate ≤ threshold) / total. `tpm_growth_safety_pct` = (TPMs where current_estimate + growth_allowance ≤ threshold) / total.

**Renderer.** Per-module sidecar gains a "## TPMs" section listing TPMs that apply to this module.

**Source.** NASA SE Handbook §6.7.2 (Technical Performance Measures).

---

## 4. Items #1, #33, #32 — runtime observability + commitment chain (Commit 3)

These three items form the design-time-to-runtime bridge and should land together to make the chain meaningful.

### 4.1 #1 — Observability as first-class

**Schema additions.** New block on `PSpec` and `ArchModule`:

```python
class MetricKind(str, Enum):
    COUNTER   = "counter"
    GAUGE     = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY   = "summary"

class AlertSeverity(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    CRITICAL = "critical"
    PAGE     = "page"

class Metric(BaseModel):
    name: str
    kind: MetricKind
    unit: Optional[str] = None
    description: Optional[str] = None

class Trace(BaseModel):
    span: str
    description: Optional[str] = None

class LogCategory(BaseModel):
    category: str
    level: str  # debug | info | warning | error | critical

class Alert(BaseModel):
    name: str
    when: str                             # PromQL-style condition or natural-language
    severity: AlertSeverity
    runbook: Optional[str] = None         # path to runbook markdown (#33)
    escalation_after_min: Optional[int] = None

class Observability(BaseModel):
    metrics: list[Metric] = Field(default_factory=list)
    traces: list[Trace] = Field(default_factory=list)
    logs: list[LogCategory] = Field(default_factory=list)
    alerts: list[Alert] = Field(default_factory=list)
```

`PSpec.observability: Optional[Observability]` and `ArchModule.observability: Optional[Observability]`.

**Validator.** Alert name uniqueness within a module. Alert `runbook` path exists on disk (warning when missing; ties to #33). Metric names follow Prometheus naming conventions (lowercase + underscores; warning, not error).

**Coverage metric.** `observability_coverage_pct` = (PSpecs/Modules with observability declared) / total.

**Renderer.** PSPEC + AMS sidecars gain an "## OBSERVABILITY" section listing metrics, alerts, runbook links.

**Source.** OpenTelemetry semantic conventions; Prometheus naming conventions; Google SRE Workbook ch. 5 (Alerting on SLOs).

### 4.2 #33 — Runbooks tied to alerts

**Schema additions.** The `runbook:` field on `Alert` (declared in #1 above). This is a string path to a markdown runbook file.

**Convention.** Runbook files live at `runbooks/<alert-name>.md` and follow a structured template:

```markdown
# Runbook — tension_sensor_stuck

**Alert:** tension_sensor_stuck
**Severity:** warning
**Module:** am_controller (proc_acquire_tension)

## SYMPTOMS
- Tension samples rate drops to zero
- Bite detector enters Fault state

## DIAGNOSIS
1. Check ADC connectivity (multimeter at sensor terminals)
2. Check motor driver doesn't have shorted output
3. Check firmware logs for `tension.calibration` errors

## RESOLUTION
- If sensor disconnected: reconnect, observe samples resume
- If ADC failure: cycle power; if persistent, replace board
- If firmware fault: ...

## ESCALATION
After 15 minutes without resolution, page #oncall-firmware.
```

**Validator.** When `Alert.runbook` is set, warning if the file doesn't exist. Hard-error if the path contains `..` or is absolute (security: don't let the dictionary point to arbitrary filesystem locations).

**Coverage metric.** `alert_runbook_coverage_pct` = (Alerts with runbook set) / total alerts.

**Renderer.** Alert listings in PSPEC + AMS sidecars become clickable links to runbooks.

**Source.** Google SRE Workbook ch. 11 (Being On-Call); PagerDuty incident management documentation.

### 4.3 #32 — SLI / SLO / SLA chain

**Schema additions.** New top-level section:

```python
class SLI(BaseModel):
    """Service Level Indicator — what's measured."""
    query: str                            # PromQL / equivalent (informational)
    unit: Optional[str] = None
    description: Optional[str] = None

class SLO(BaseModel):
    """Service Level Objective — committed target."""
    id: str
    name: str
    sli: SLI
    target: float                         # threshold value
    window: str                           # rolling window: "30d", "7d", "24h"
    error_budget_pct: float               # 0.0-100.0
    applies_to: dict[str, list[str]] = Field(default_factory=dict)
    # e.g.: {modules: [am_x], flows: [af_y]}
    sla: Optional[str] = None             # customer-facing prose
    derives_from_tpm: Optional[str] = None
    runbook_on_burn: Optional[str] = None  # path to runbook for budget burn
```

`Project.service_level_objectives: dict[str, SLO] = Field(default_factory=dict)`.

**Validator.** `applies_to` references resolve. `window` matches `^\d+(s|m|h|d|w)$`. `error_budget_pct` ∈ [0, 100]. `derives_from_tpm` references a real TPM. `runbook_on_burn` file exists (warning).

**Coverage metric.** `slo_coverage_pct` = (modules with at least one SLO applying to them) / total modules.

**Renderer.** New `slos.md` summary in `architecture/` directory; per-module sidecars list applicable SLOs.

**Source.** Google SRE Book (2016) + SRE Workbook (2018); SLO movement (Nobl9 docs; Datadog SLO product docs).

---

## 5. Item #8.2, #8.3 — threat modeling depth (Commit 4)

### 5.1 #8.2 — STRIDE annotations on cross-boundary interconnects

**Schema additions.** Optional `stride_mitigations:` block on `ArchInterconnect`:

```python
class STRIDEMitigations(BaseModel):
    """STRIDE threat category mitigations (Microsoft 1999)."""
    spoofing:           Optional[str] = None
    tampering:          Optional[str] = None
    repudiation:        Optional[str] = None
    info_disclosure:    Optional[str] = None
    denial_of_service:  Optional[str] = None
    elev_of_privilege:  Optional[str] = None

class LINDDUNMitigations(BaseModel):
    """LINDDUN privacy threat mitigations (KU Leuven 2010)."""
    linkability:      Optional[str] = None
    identifiability:  Optional[str] = None
    non_repudiation:  Optional[str] = None
    detectability:    Optional[str] = None
    disclosure:       Optional[str] = None
    unawareness:      Optional[str] = None
    non_compliance:   Optional[str] = None
```

`ArchInterconnect.stride_mitigations: Optional[STRIDEMitigations]` and `linddun_mitigations: Optional[LINDDUNMitigations]`.

**Validator.** Interconnects crossing different `trust_zone`s must have `stride_mitigations` set (error). All six STRIDE categories present (warning if missing — sometimes "out of scope" is the right answer).

**Coverage metric.** `stride_coverage_pct` = (cross-trust-zone interconnects with stride_mitigations) / total cross-trust-zone interconnects.

**Renderer.** AIS sidecar gains a "## THREAT MODEL (STRIDE)" section.

**Source.** STRIDE — Microsoft Security Development Lifecycle (Howard & Lipner 2006); LINDDUN — KU Leuven DistriNet research group (2010).

### 5.2 #8.3 — Reference-catalog discipline

**Schema additions.** Convention-only — three new optional list fields on `ArchModuleSpec`, `ArchInterconnectSpec`, and `ADR`:

```python
references_mitre_attack: list[str] = Field(default_factory=list)  # e.g., ["T1078", "T1190"]
references_cwe:          list[str] = Field(default_factory=list)  # e.g., ["CWE-79", "CWE-89"]
references_compliance:   list[str] = Field(default_factory=list)  # e.g., ["SOC2-CC6.1", "ISA-62443-SL2"]
```

**Validator.** ID format validation (regex check). Reference catalogs are external; we don't validate that the IDs exist in MITRE/NIST/etc. — just that they're well-formed.

**Renderer.** AIS / AMS / ADR sidecars list the references in a footer ("Mitigates ATT&CK T1078; CWE-89 not applicable").

**Source.** MITRE ATT&CK Framework; MITRE CWE; ISA/IEC 62443; OWASP ASVS; NIST CSF 2.0; NIST 800-53.

---

## 6. Implementation order

Five commits, each Stage-4-style chunk size:

### Commit 1 — small additive fields (no chain dependencies)
- Model: `FlowSynchronicity`, `FlowDelivery`, `TrustZone`, `AuthRequired`, `Encryption`, `VerificationMethod`, `VerificationPlan`, `ADRStatus`, `ADR` classes + enums
- Loader: pick up `adrs:` section
- Validator: rules for #2, #8.1, #10, #25
- Renderer: edge-styling for `synchronicity`; AID side-panel for `trust_zone` + `auth_required` + `encryption`; PSPEC + AMS sidecar gain `## VERIFICATION` section; new `render/adr.py` emits per-ADR sidecars
- Lived examples: add `synchronicity:` to all flows on fishing-rig + solar; add `trust_zone:` to architecture modules; add `verification:` to one PSPEC per project; add 1–2 ADRs per project retrofitting earlier decisions

### Commit 2 — design-time discipline (NASA budgets + TPMs)
- Model: `Budget`, `TPM` classes
- Loader: pick up `budgets:`, `tpms:` sections
- Validator: budget-allocation hard rule (sum ≤ target); TPM threshold rule; cross-references
- Renderer: budget summary section in AMS sidecars; TPM listing
- Lived examples: latency budget on fishing-rig + solar (each declares an end-to-end latency budget allocated across modules); 2–3 TPMs per project tracking budget consumption

### Commit 3 — runtime observability + commitment chain (SRE: observability + runbooks + SLOs)
- Model: `MetricKind`, `Alert`, `Observability`, `SLI`, `SLO` classes
- Loader: pick up `service_level_objectives:` section
- Validator: alert name uniqueness; runbook path existence; SLO cross-references
- Renderer: PSPEC + AMS sidecars gain `## OBSERVABILITY` section; new `slos.md` summary in `architecture/`
- Lived examples: observability declarations on every PSPEC; runbooks for the 3–4 most critical alerts; one or two SLOs per project demonstrating the chain (e.g., "end-to-end event-processing latency p99 < 100ms over 30 days, error budget 0.1%")

### Commit 4 — threat modeling depth
- Model: `STRIDEMitigations`, `LINDDUNMitigations` classes; `references_*:` list fields
- Validator: STRIDE coverage on cross-trust-zone interconnects; ID format checks
- Renderer: AIS gains `## THREAT MODEL (STRIDE)` section
- Lived examples: STRIDE annotations on fishing-rig's BLE interconnect + solar's local-LAN interconnect; MITRE / CWE references on 2–3 ADRs

### Commit 5 — Bounded Contexts (#5)
See [`BOUNDED_CONTEXTS_DESIGN.md`](BOUNDED_CONTEXTS_DESIGN.md). Own design pass; possibly own branch.

---

## 7. New coverage metrics added

The validator's `coverage_metrics()` will grow these new percentages:

| Metric | What it measures | Item |
|---|---|---|
| `observability_coverage_pct` | leaf processes + modules with observability declared | #1 |
| `alert_runbook_coverage_pct` | alerts with runbook path set | #33 |
| `slo_coverage_pct` | modules with ≥ 1 SLO applying to them | #32 |
| `budget_allocation_completeness_pct` | per-budget allocation as % of system_target | #21 |
| `tpm_within_threshold_pct` | TPMs where current_estimate ≤ threshold | #22 |
| `tpm_growth_safety_pct` | TPMs where current_estimate + growth_allowance ≤ threshold | #22 |
| `verification_coverage_pct` | PSPECs + AMSs with verification block | #25 |
| `stride_coverage_pct` | cross-trust-zone interconnects with STRIDE mitigations | #8.2 |
| `synchronicity_coverage_pct` | architecture flows with synchronicity set | #2 |

These join the existing `description_coverage_pct`, `pspec_coverage_pct`, `architecture_module_coverage_pct`, `ams_coverage_pct`, etc.

---

## 8. Open questions for implementation

1. **Validator severity for missing fields.** Most modernization fields are *optional* (we don't want to invalidate existing solar + fishing-rig dictionaries). Coverage metrics report adoption percentages. Should we add a "modernization adoption" overall metric that aggregates the new percentages?

2. **Runbook path validation.** Should the validator check that runbook files exist at the declared path? Current plan: warning only (the runbook may live in a separate repo). Alternative: support `runbook: external` to declare it lives elsewhere and silence the warning.

3. **TPM time-series.** First cut models TPMs as a single `current_estimate` snapshot. Eventually they'd be time-series (history of values + trend). Out-of-scope for this design; design with extension in mind (the `trend_notes:` field is a placeholder).

4. **SLI query language.** First cut: `sli.query` is a free-string field (could be PromQL, KQL, NRQL, etc.). Validator doesn't parse it. Eventually: support typed query languages.

5. **Cross-stage cross-references.** Several items have optional cross-references (`tpm.derived_from_budget`, `slo.derives_from_tpm`, `alert.runbook`, `adr.affects`). Implementation order matters — implement the *targets* before the *sources* to keep reference integrity working. Commit ordering reflects this.

6. **STRIDE-categories-out-of-scope handling.** When a STRIDE category genuinely doesn't apply, the convention is `repudiation: "out_of_scope"` rather than leaving the field empty. Validator should accept this. Could be an `OUT_OF_SCOPE` sentinel value.

7. **ADR lifecycle.** When an ADR is superseded, the superseding ADR references it via `supersedes:`. Should the validator warn when an ADR references a superseded ADR's affected modules but doesn't itself appear in the `affects:` chain?

---

## 9. See also

- Brainstorm + analysis: [`../proposals/MODERNIZATION.md`](../proposals/MODERNIZATION.md) (39 items, 2 real-project lenses)
- Companion paradigm doc: [`BOUNDED_CONTEXTS_DESIGN.md`](BOUNDED_CONTEXTS_DESIGN.md) (item #5)
- Predecessor design docs: [`PSPEC_DESIGN.md`](PSPEC_DESIGN.md), [`ARCH_DESIGN.md`](ARCH_DESIGN.md) — same shape
- Sources cited inline per item; full bibliographic list in the proposals doc

---

## 10. Source bibliography

- **NASA SE Handbook**: NASA/SP-2016-6105 Rev 2 (2017). *NASA Systems Engineering Handbook*.
- **SRE Book**: Beyer, Jones, Petoff, Murphy (eds.) (2016). *Site Reliability Engineering*. O'Reilly.
- **SRE Workbook**: Beyer, Murphy, Rensin, Kawahara, Thorne (eds.) (2018). *The Site Reliability Workbook*. O'Reilly.
- **ADR pattern**: Nygard, M. (2011). *Documenting Architecture Decisions*. ThoughtWorks blog.
- **STRIDE**: Howard, M., Lipner, S. (2006). *The Security Development Lifecycle*. Microsoft Press.
- **LINDDUN**: Wuyts, K., Joosen, W. (2015). *LINDDUN privacy threat modeling: a tutorial*. KU Leuven Technical Report.
- **MITRE ATT&CK**: mitre.org/attack — Adversarial Tactics, Techniques, and Common Knowledge.
- **ISA/IEC 62443**: ISA-62443 series, *Security for Industrial Automation and Control Systems*.
- **Reactive Streams**: reactive-streams.org — async stream-processing standard.
- **OpenTelemetry**: opentelemetry.io — observability semantic conventions.
- **IEEE 1012**: *Standard for System, Software, and Hardware Verification and Validation* (2016 ed).
