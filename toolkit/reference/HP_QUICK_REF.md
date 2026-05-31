# Hatley-Pirbhai Quick Reference

Concise refresh on HP vocabulary. Each entry: one-line definition · modern analog where helpful · tiny example · cross-links to related terms.

Anchor links work from chat: e.g. `[DFD](toolkit/reference/HP_QUICK_REF.md#dfd--data-flow-diagram)`. Headings use kebab-case anchors automatically.

**Sourced from** the 1988 book (*Strategies for Real-Time System Specification*, Hatley & Pirbhai) and the 2000 book (*Process for System Architecture and Requirements Engineering*, Hatley, Hruschka & Pirbhai). Some entries note where they were introduced.

---

## 1. The Two (then Three) Models

### Requirements Model
The **"what"** half of HP — what the system must do, independent of how. Composed of: a Process Model (DFDs + PSPECs), a Control Model (CFDs + CSPECs), a Requirements Dictionary, and Timing Specs. Modern analog: a behavior spec + state machine + interface contracts, all kept consistent. *See also:* [Architecture Model](#architecture-model), [Essential vs Implementation Model](#essential-vs-implementation-model).

### Architecture Model
The **"how"** half — physical/logical realization of the requirements. Composed of: Architecture Flow Diagrams (AFDs), Architecture Interconnect Diagrams (AIDs), Architecture Module Specs (AMS), Architecture Interconnect Specs (AIS), Architecture Dictionary. Modern analog: deployment diagram + component diagram + interface contracts + the wiring spec. *See also:* [Architecture Templates](#the-four-architecture-templates).

### Mechanisms Model (added in 2000)
A **middle layer between Requirements and Architecture**, introduced in the 2000 book. Captures *generic solution patterns* (control loops, state-machine engines, fault-handling schemes) before committing to specific hardware/software modules. Modern analog: design patterns — but named, traceable, and explicit. *See also:* [Layered Models](#layered-models), [Enhanced Requirements Model](#enhanced-requirements-model).

### Essential vs Implementation Model
HP's foundational distinction. **Essential** = what the system must do regardless of technology (the "perfect" technology-independent view). **Implementation** = how it's actually built with real components. The Architecture Model is the bridge. Modern analog: domain model vs deployment model.

### Layered Models
The 2000 book's three-tier framing: Essential Requirements Model → Mechanisms Model → Architecture Model. Each layer refines the previous without losing intent. *See also:* [Mechanisms Model](#mechanisms-model-added-in-2000).

### Enhanced Requirements Model
The 2000 book's name for the requirements model *after* the four architecture templates have been applied. Refines the essential model with the bookkeeping the implementation will need (I/O, UI, self-test). *See also:* [The Four Architecture Templates](#the-four-architecture-templates).

---

## 2. Notation Primitives (what you draw)

### Process (Bubble)
The basic data-transformation unit. Drawn as a **circle** with a name and a hierarchical number (e.g., "2.3 Validate Coin"). Each non-leaf bubble decomposes into a child DFD; each leaf bubble has a PSPEC. Modern analog: a function (leaf) or a module (non-leaf).

### Terminator
An **external entity** that sits *outside* the system boundary but exchanges data or control with it. Drawn as a **rectangle**. People, other systems, sensors, actuators, regulators. Modern analog: external actor on a context diagram, or "external service" in a service map. *See also:* [Context Diagram](#context-diagram-dcd--ccd--acd).

### Data Store
A **place data is held** between processes (file, database, table, queue, buffer). Drawn as **two parallel lines** with a name between. Modern analog: a database table, a Redis key, a Kafka topic — anything where one process writes and another later reads.

### Control Store
Same shape as a data store, but for **control information** (state values, mode flags). Less common in practice; usually merged with state machines inside CSPECs. *See also:* [CSPEC](#cspec--control-specification).

### Data Flow
A **labeled arrow** from a source (process, store, terminator) to a destination, carrying named data. Solid line. Modern analog: a function argument, a message on a queue, a struct passed somewhere.

### Control Flow
Like data flow but carries **events, triggers, or state signals** that *cause* processes to do something. Drawn with a **dashed line** in classic HP. Modern analog: an event, an interrupt, a signal, a webhook.

### CSPEC Bar (Short Unlabeled Bar)
A small **horizontal bar** drawn into a DFD that represents a CSPEC reaching into the data world to **activate, deactivate, trigger, or enable** processes. The "magic" notation that connects control to data without cluttering the DFD. Modern analog: the rules engine reaching in to enable/disable handlers based on state. *See also:* [Process Controls](#process-controls).

### Process Controls
The actual signals the CSPEC bar emits into processes — **activator** (start running), **deactivator** (stop), **trigger** (run once). Modern analog: lifecycle hooks (`start()`, `stop()`, `tick()`).

---

## 3. Diagrams

### Context Diagram (DCD / CCD / ACD)
The **level-0 diagram** — single bubble (the system) plus all terminators around it, with flows crossing the system boundary. Three variants: **DCD** = Data Context Diagram (data flows only), **CCD** = Control Context Diagram (control flows only), **ACD** = Architecture Context Diagram (the architecture-side equivalent). *Drawn first; the methodology refuses to go deeper until it's locked.* Modern analog: a system context diagram in C4 architecture notation.

### DFD — Data Flow Diagram
The **bread and butter** of HP. Bubbles (processes) connected by data flows, with terminators around the edge and data stores between processes. Hierarchical — each non-leaf bubble has a child DFD that decomposes it. Modern analog: a structured flowchart-of-transformations, or a Petri-net-like view of data movement. *See also:* [Leveling](#leveling), [Balancing](#balancing).

### CFD — Control Flow Diagram
The **partner to a DFD** for the control-flow dimension. Shows control flows between processes and to/from CSPEC bars. Often drawn on the same sheet as the corresponding DFD. Modern analog: the signaling layer of an event-driven system.

### AFD — Architecture Flow Diagram
The **architecture-side counterpart to a DFD**. Shows physical/logical *modules* (rounded rectangles) connected by *architecture flows* (which group the underlying data/control flows). Modern analog: a deployment diagram showing what runs where. *See also:* [AID](#aid--architecture-interconnect-diagram), [Architecture Module](#architecture-module).

### AID — Architecture Interconnect Diagram
Shows the **physical channels** (buses, network links, RS-485, MQTT, file paths) carrying architecture flows between modules. **AID + AFD together = the full architecture picture.** Modern analog: the wiring/network diagram for a deployment. *See also:* [AIS](#ais--architecture-interconnect-specification).

### AICD / AFCD (added in 2000)
Architecture-side **context diagrams** — same idea as DCD/CCD but for the architecture model. AICD = Architecture Interconnect Context Diagram (level-0 of AID). AFCD = Architecture Flow Context Diagram (level-0 of AFD).

---

## 4. Specifications (the textual artifacts)

### PSPEC — Process Specification
The **leaf-level functional contract** for a bubble that doesn't decompose further. Specifies: inputs consumed, outputs produced, preconditions, postconditions, the transformation rule. Often written in structured English or a decision table. Modern analog: a docstring-plus-contract; a JSDoc/PEP-257 with formal pre/post conditions. *Required for every leaf bubble.* *See also:* [Process (Bubble)](#process-bubble), [Primitive (Leaf Bubble)](#primitive-leaf-bubble).

### CSPEC — Control Specification
The **state/sequencing logic** that controls when processes activate. Usually contains a state-transition diagram, a decision table, or both. Reaches into the DFD via the CSPEC bar to activate/deactivate/trigger processes. Modern analog: a state machine spec, a rules engine config, an FSM library setup. *See also:* [STD](#std--state-transition-diagram), [Decision Table](#decision-table), [CSPEC Bar](#cspec-bar-short-unlabeled-bar).

### TSPEC — Timing Specification
A **formal capture of timing requirements**: response times, repetition rates, deadlines, latencies. First-class artifact, not just a comment. Example: "F3 (net grid power read) latency ≤ 1 s; sampling rate ≥ 1 Hz." Modern analog: SLO definitions, but at the requirements level. *See also:* [Timing Requirements](#timing-requirements).

### AMS — Architecture Module Specification
Like a PSPEC but for an **architecture module** (a deployable component). Describes the module's responsibilities, the data/control flows it handles, its internal allocations. Modern analog: a service README / component contract.

### AIS — Architecture Interconnect Specification
Like a PSPEC but for an **interconnect** — a physical/logical channel. Specifies the protocol, format, timing, framing, error handling. **This is HP's answer to "interfaces lost in implementation"** — interfaces are first-class artifacts. Modern analog: a protocol spec, an OpenAPI document, a gRPC IDL, a Modbus register map.

### Requirements Dictionary
The **central glossary of every named flow, store, and data element** in the requirements model. Every arrow/store/element on every diagram has an entry. Modern analog: a data dictionary, schema registry, or shared types library. *See also:* [Group Structure](#group-structure), [Primitive Attributes](#primitive-attributes).

### Architecture Dictionary
The dictionary's architecture-side counterpart — every architecture module, flow, and interconnect has an entry.

### Group Structure
A way of specifying **composite data elements** in the Requirements Dictionary (e.g., "telemetry_packet = timestamp + channel_id + voltage + current"). Modern analog: a struct/record type definition.

### Primitive Attributes
The leaf-level attributes in the dictionary — units, ranges, precision, encoding. Modern analog: a primitive type definition with constraints.

---

## 5. Concepts & Discipline

### Leveling
The **hierarchical decomposition** of DFDs. Level-0 = context diagram (one bubble). Level-1 = the first decomposition (3-7 bubbles). Each non-leaf bubble at level N becomes its own DFD at level N+1. The leveling rule: **every bubble at the same level is at the same level of abstraction**. *Anti-rathole mechanism: you can't go deep on one bubble while leaving siblings under-specified.*

### Balancing
The conservation law of DFDs. **Flows in and out of a parent bubble must match flows in and out of its child DFD.** A child DFD must preserve the parent's interface exactly. *Modern analog:* a function's signature must be consistent with what its body actually consumes and produces. Validation: balancing checks find drift early.

### Decomposition
The process of taking one bubble and breaking it into a child DFD with multiple bubbles. HP demands that decomposition be *justified* — typically because the bubble has 3+ distinct responsibilities, or its PSPEC would be too long. *See also:* [Leveling](#leveling).

### Seven-Plus-or-Minus-Two
HP's rule of thumb: **a DFD should have 5-9 bubbles**. Below 5, you haven't decomposed enough. Above 9, the diagram is incomprehensible. Sourced from Miller's classic cognitive-load paper. Modern analog: the "team size of two pizzas" or "module file under 500 lines" heuristic.

### Traceability
The **explicit links** from requirements to architecture to implementation (and ideally to tests). HP demands that every requirement be allocated to an architecture module, and every architecture module justify itself against requirements. Modern analog: requirement-IDs on commits, story-to-test mapping, but enforced as a first-class artifact. *See also:* [Traceability Matrix](#traceability-matrix), [Extended Traceability](#extended-traceability-added-in-2000).

### Traceability Matrix
The **table** that records traceability links — typically requirements as rows, architecture modules as columns, with cells marking allocations. *Anti-85%-syndrome mechanism: uncovered requirements stand out as empty rows.*

### Primitive (Leaf Bubble)
A bubble that **doesn't decompose further** — its behavior is captured in a PSPEC instead of a child DFD. The bottom of the hierarchy. Modern analog: a pure function with a docstring.

### System Hierarchy / Universal Hierarchy
HP's view that all systems exist in a containing hierarchy — your system is part of a larger system (the *environment*), and contains smaller systems (the *subsystems*). The context diagram defines the boundary between *your* system and the level above it. *See also:* [Multiple Hierarchies](#multiple-hierarchies-added-in-2000).

### Transaction Center
A bubble that **dispatches between multiple downstream processes based on input** (often command/event-driven). Modern analog: a switch statement, a router, a dispatcher.

### Primitive Network
The DFD at its **finest level of decomposition** — only leaf bubbles remain, all with PSPECs, no further decomposition possible. Modern analog: the "leaf functions" of a refactored codebase.

---

## 6. The Four Architecture Templates

The 1988 book's contribution: every architecture wraps the requirements model in **four standard "process blocks" surrounding a core**. These are the things real systems need that pure structured analysis ignored.

### Input Processing
The **block that handles incoming data/control from terminators** — sensor reads, network input, button presses, file reads. Decouples the rest of the system from physical-input concerns. Modern analog: input adapters in hexagonal architecture.

### Output Processing
The **block that handles outgoing data/control to terminators** — actuator commands, displays, network output, file writes. Modern analog: output adapters in hexagonal architecture.

### User Interface Processing
The **block that handles human interaction** — dashboards, configuration, manual override, alerts. Separate from generic I/O because human latency, error tolerance, and presentation needs differ. Modern analog: presentation layer.

### Maintenance / Self-Test / Redundancy Management
The **block that handles non-functional concerns** — health checks, diagnostics, failover, recovery, redundancy. The "what keeps this thing running" layer. Modern analog: SRE/observability + HA features.

### Architecture Template (4 surrounding blocks)
The collective name. Every architecture is the **requirements model "core" surrounded by these four blocks**. Forces you to think about I/O, UI, and self-test as first-class architecture concerns, not afterthoughts.

---

## 7. Control Formalisms (inside CSPECs)

### FSM — Finite State Machine
Classic state machine: states + transitions + events + actions. HP uses FSMs inside CSPECs for any process with non-trivial sequencing. *See also:* [STD](#std--state-transition-diagram), [State Transition Matrix](#state-transition-matrix--table).

### STD — State Transition Diagram
The **graphical form of a state machine** — circles for states, arrows for transitions labeled with event/action pairs. Modern analog: a state-chart in XState or similar.

### State Transition Matrix / Table
The **tabular form of a state machine** — rows are current states, columns are events, cells are next-state-and-action. Equivalent to STD, sometimes more compact for large state spaces.

### Decision Table
A **tabular form for combinational logic** (no state). Rows are conditions, columns are rule combinations, cells say which actions fire. Modern analog: a rules engine ruleset, a truth table.

### Combinational vs Sequential Machine
**Combinational** = output depends only on current inputs (decision table). **Sequential** = output depends on inputs *and* current state (STD/state matrix). HP CSPECs may contain either or both.

### State Chart (Harel, added in 2000)
A **hierarchical state machine** with nested states and parallel regions. From David Harel's 1987 work. The 2000 book brings these into HP for cases where a flat FSM is too noisy.

### Composite CSPEC / Multi-Sheet CSPEC
A **CSPEC that spans multiple sheets** because the control logic is too complex for one page. Same logic, just paginated.

---

## 8. 2000-Book Additions

The 2000 book (Hatley/Hruschka/Pirbhai, "PSARE") added a *process* layer on top of the 1988 *notation*, plus refinements.

### Process / Methods / Tools Precedence
The 2000 book's mantra: **process drives methods, methods drive tools** — pick in that order, not the reverse. Modern analog: "don't pick the tool first."

### Concurrent Development Process
The 2000 book's alternative to waterfall: requirements, mechanisms, and architecture evolve *concurrently*, with iteration loops between them. Modern analog: agile-but-with-actual-architecture-work.

### Superbubble
A **virtual bubble grouping multiple related bubbles** for navigation or abstraction purposes. Doesn't change the leveling rules; just a viewing aid. Modern analog: a "lens" or "selection" in a diagram tool.

### Extended Traceability (added in 2000)
Refinement of 1988's traceability: links extend not just requirements→architecture but **requirements→mechanisms→architecture→implementation→tests**, with bidirectional navigation. *See also:* [Traceability](#traceability).

### Derived Requirement
A **requirement that emerges during architecture or design** — not in the original stakeholder ask, but necessary because of how the system is being built. The 2000 book makes these first-class so they're traceable too. Modern analog: "non-functional requirement discovered during implementation."

### Object Orientation Integration
The 2000 book acknowledges UML had arrived and offers patterns for combining HP's structured analysis with OO design (class diagrams alongside DFDs, state charts in CSPECs). Modern analog: "structured analysis and OO are complementary, not exclusive."

### Multiple Hierarchies (added in 2000)
Recognition that real systems live in **multiple overlapping hierarchies** (organizational, physical, functional, control). The 1988 book assumed one. The 2000 book lets you model several.

### Meta-Model / Development Process Meta-Model
The 2000 book's framing of the *development process itself* using the same notation. The development project becomes a system, the team are processes, the deliverables are flows. Reflexive use of HP on the work of doing HP. Modern analog: "we used our own tool on our own project."

### Business Object Architecture
A 2000-book pattern for organizing architecture around **business-domain objects** rather than purely-functional decomposition. Bridge between HP and domain-driven design.

### Workflow-Centered Architecture
2000-book pattern: organize the architecture around **end-to-end workflows** (start at the user, follow the data, end at the persistence layer). Modern analog: vertical slice architecture.

---

## 9. Common Examples (from the 1988 book)

The HP books illustrate everything through four canonical worked examples, in increasing complexity. Worth knowing about as reference points:

- **Vending Machine** — transactional, discrete events, basic FSM. The "hello world" of HP.
- **Home Heating System** — continuous control with sensors and actuators. Introduces continuous data flow and closed-loop control.
- **Automobile Management** — multiple cooperating subsystems. Introduces inter-process control and decomposition across subsystems.
- **Flight Management (Avionics)** — full real-time, safety-critical, redundant. The "go-to" complex example; the methodology's origin domain.

---

## 10. Antecedents & Influences

HP didn't appear in a vacuum — it builds on (and credits) several prior methods:

- **DeMarco Structured Analysis** (1979) — the original DFD notation, no control.
- **Yourdon/Constantine Structured Design** (1979) — the architecture-side counterpart, structure charts.
- **Ward-Mellor Real-Time Structured Analysis** (early 1980s) — an alternative real-time extension to DeMarco. HP and Ward-Mellor are parallel approaches with different control notations.
- **Finite State Machine Theory** — the formal underpinning of CSPECs.
- **Harel State Charts** (1987) — incorporated into the 2000 book.
- **Putnam Model** — project sizing/scaling, referenced in the 1988 book.

---

*This is a quick-reference card, not a tutorial. For the deep dive, see the source books: Hatley & Pirbhai (1988), *Strategies for Real-Time System Specification*; and Hatley, Hruschka & Pirbhai (2000), *Process for System Architecture and Requirements Engineering*.*

*Last updated: 2026-05-22.*
