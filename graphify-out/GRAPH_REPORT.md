# Graph Report - /home/kevin/hatley-pirbhai  (2026-05-21)

## Corpus Check
- Corpus is ~0 words - fits in a single context window. You may not need a graph.

## Summary
- 187 nodes · 234 edges · 20 communities detected
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Authors, Books & Modern Extensions|Authors, Books & Modern Extensions]]
- [[_COMMUNITY_Architecture Realization & Integration|Architecture Realization & Integration]]
- [[_COMMUNITY_Control Modeling & State Machines|Control Modeling & State Machines]]
- [[_COMMUNITY_Process Model & Notation Primitives|Process Model & Notation Primitives]]
- [[_COMMUNITY_Requirements Modeling Layers|Requirements Modeling Layers]]
- [[_COMMUNITY_Architecture Templates & Mechanisms|Architecture Templates & Mechanisms]]
- [[_COMMUNITY_Intellectual Foundations & Examples|Intellectual Foundations & Examples]]
- [[_COMMUNITY_System Development Process Models|System Development Process Models]]
- [[_COMMUNITY_Requirements Engineering Activities|Requirements Engineering Activities]]
- [[_COMMUNITY_Architecture Flow & Traceability|Architecture Flow & Traceability]]
- [[_COMMUNITY_Flow Types & Dictionary Primitives|Flow Types & Dictionary Primitives]]
- [[_COMMUNITY_Modeling Discipline & Heuristics|Modeling Discipline & Heuristics]]
- [[_COMMUNITY_Project Management Roles|Project Management Roles]]
- [[_COMMUNITY_Software Design Approaches|Software Design Approaches]]
- [[_COMMUNITY_System Hierarchy & Lifecycle|System Hierarchy & Lifecycle]]
- [[_COMMUNITY_Development Spiral|Development Spiral]]
- [[_COMMUNITY_Multiple Hierarchies|Multiple Hierarchies]]
- [[_COMMUNITY_System Network|System Network]]
- [[_COMMUNITY_User Role|User Role]]
- [[_COMMUNITY_External Stakeholder|External Stakeholder]]

## God Nodes (most connected - your core abstractions)
1. `Architecture Model` - 27 edges
2. `Requirements Model` - 21 edges
3. `Strategies for Real-Time System Specification (1988)` - 18 edges
4. `Architecture Template (4 surrounding blocks)` - 16 edges
5. `Hatley-Pirbhai Methodology` - 13 edges
6. `Data Flow Diagram (DFD)` - 12 edges
7. `Process for System Architecture and Requirements Engineering (2000)` - 12 edges
8. `Control Specification (CSPEC)` - 10 edges
9. `Control Flow Diagram (CFD)` - 7 edges
10. `Requirements Dictionary (RD)` - 6 edges

## Surprising Connections (you probably didn't know these)
- `Extended Traceability` --extends--> `Strategies for Real-Time System Specification (1988)`  [EXTRACTED]
  Process for System Architecture and Requirements Engineering ... 2000.pdf → Strategies for Real-Time System Specification ... 1988.pdf
- `Derived Requirement` --extends--> `Strategies for Real-Time System Specification (1988)`  [EXTRACTED]
  Process for System Architecture and Requirements Engineering ... 2000.pdf → Strategies for Real-Time System Specification ... 1988.pdf
- `Mechanisms Model (intermediate solution-pattern layer)` --follows--> `Requirements Model`  [INFERRED]
  Process for System Architecture and Requirements Engineering ... 2000.pdf → Strategies for Real-Time System Specification ... 1988.pdf
- `Architecture Model` --part_of--> `Architecture Interconnect Context Diagram (AICD)`  [EXTRACTED]
  Strategies for Real-Time System Specification ... 1988.pdf → Process for System Architecture and Requirements Engineering ... 2000.pdf
- `What/How Separation` --references--> `Architecture Model`  [EXTRACTED]
  Process for System Architecture and Requirements Engineering ... 2000.pdf → Strategies for Real-Time System Specification ... 1988.pdf

## Hyperedges (group relationships)
- **Four Architecture Template Blocks (surrounding core)** — hp1988_input_processing_template, hp1988_output_processing_template, hp1988_ui_template, hp1988_self_test_template [EXTRACTED 1.00]
- **Requirements Model Components** — hp1988_process_model, hp1988_control_model, hp1988_timing_requirements, requirements_dictionary [EXTRACTED 1.00]
- **Architecture Model Components** — architecture_context_diagram, architecture_flow_diagram, architecture_interconnect_diagram, architecture_module_specification, hp1988_architecture_interconnect_specification, architecture_dictionary [EXTRACTED 1.00]
- **Three Model Layers (Requirements / Mechanisms-Enhanced / Architecture)** —  [EXTRACTED 0.90]
- **Roles in the System Development Process** —  [EXTRACTED 1.00]
- **Meta-Model Top-Level Activities (Specify / Configure / Specify Elements / Build-Integrate-Test)** —  [EXTRACTED 1.00]

## Communities

### Community 0 - "Authors, Books & Modern Extensions"
Cohesion: 0.1
Nodes (26): Derek J. Hatley, Imtiaz A. Pirbhai, Strategies for Real-Time System Specification (1988), Tom DeMarco (Foreword author), Architecture Interconnect Context Diagram (AICD), Process for System Architecture and Requirements Engineering (2000), Business Object Architecture, Avionics / Flight Management (example) (+18 more)

### Community 1 - "Architecture Realization & Integration"
Cohesion: 0.08
Nodes (25): Architecture Interconnect Diagram (AID), Architecture Dictionary, Architecture Interconnect Diagram (AID), Architecture Model, Architecture Interconnect Specification (AIS), Hardware Architecture Model, Implementation (technology-dependent) Model, Information Flow Channel (bus/link) (+17 more)

### Community 2 - "Control Modeling & State Machines"
Cohesion: 0.11
Nodes (21): Control Flow Diagram (CFD), Control Context Diagram (CCD), Control Flow Diagram (CFD), Control Model, Control Specification (CSPEC), Combinational Machine (Decision Table), Composite CSPEC, Control Model (Requirements) (+13 more)

### Community 3 - "Process Model & Notation Primitives"
Cohesion: 0.14
Nodes (20): Architecture Context Diagram (ACD), Architecture Flow Diagram (AFD), Architecture Module Specification (AMS), Data Context Diagram (DCD), Data Flow Diagram (DFD), Data Store, Allocation to Hardware and Software, Architecture Module (rounded rectangle) (+12 more)

### Community 4 - "Requirements Modeling Layers"
Cohesion: 0.12
Nodes (16): Data Flow Diagram (DFD), Information Modeling: The Third Perspective, Essential (technology-independent) Model, Model as Feedback Control Loop, Military Standards Documentation Mapping, Repetition Rate (Timing), Input-to-Output Response Time Specification, Timing Requirements (+8 more)

### Community 5 - "Architecture Templates & Mechanisms"
Cohesion: 0.13
Nodes (16): Architecture Template (4 surrounding blocks), Architecture Development Process, Enhancing the Requirements Model (with templates), Input Processing (architecture template block), Output Processing (architecture template block), Requirements Template (Process+Control core), Maintenance, Self-Test, and Redundancy Management Processing, Technology-Independent vs Technology-Nonspecific (+8 more)

### Community 6 - "Intellectual Foundations & Examples"
Cohesion: 0.18
Nodes (11): Avionics System (FAA-certified, origin of method), DeMarco Structured Analysis, Example: Automobile Management System, Example: Flight Management System (avionics), Example: Home Heating System, Example: Vending Machine, Finite State Machine Theory (foundation), Putnam Model (project scaling) (+3 more)

### Community 7 - "System Development Process Models"
Cohesion: 0.22
Nodes (9): Capability Maturity Model (CMM), Concurrent Development Process, Concurrent Engineering (SOCE), Process-Methods-Tools Order of Precedence, PSARE (Process for System Architecture and Requirements Engineering), Spiral Model (Boehm), Total System Life Cycle, Waterfall Model (+1 more)

### Community 8 - "Requirements Engineering Activities"
Cohesion: 0.25
Nodes (9): Requirement Categorizing, Requirement Deriving, Requirement Detailing, Requirement Feasibility Analysis, Requirement Gathering, Requirement Integrity Analysis, Derived Requirement, Customer (Role) (+1 more)

### Community 9 - "Architecture Flow & Traceability"
Cohesion: 0.29
Nodes (8): Architecture Flow Diagram (AFD), Requirement Allocation (to Architecture), Architecture Flow, Architecture Module, Extended Traceability, System Architect (Role), Superbubble, Traceability Matrix

### Community 10 - "Flow Types & Dictionary Primitives"
Cohesion: 0.29
Nodes (7): Control Flow, Data Flow, Continuous Signal, Discrete Signal (Event), Group Structure (Dictionary), Primitive Attributes (Dictionary), Requirements Dictionary (RD)

### Community 11 - "Modeling Discipline & Heuristics"
Cohesion: 0.4
Nodes (6): Abstraction and Decomposition, Establishing the System Context, Requirements Model Building Process, Dilemma of Detail: Requirements vs. Design, Separating Data and Control, User Requirements Statements

### Community 12 - "Project Management Roles"
Cohesion: 0.67
Nodes (3): Monitor Development, Plan System Development, Project Manager (Role)

### Community 13 - "Software Design Approaches"
Cohesion: 0.67
Nodes (3): CODARTS, Horseshoe Architecture, Structured Design

### Community 14 - "System Hierarchy & Lifecycle"
Cohesion: 1.0
Nodes (2): Total System Life Cycle, Universal Hierarchy of Systems

### Community 15 - "Development Spiral"
Cohesion: 1.0
Nodes (1): Development Life Cycle Spiral

### Community 16 - "Multiple Hierarchies"
Cohesion: 1.0
Nodes (1): Multiple Hierarchies

### Community 17 - "System Network"
Cohesion: 1.0
Nodes (1): System Network

### Community 18 - "User Role"
Cohesion: 1.0
Nodes (1): User (Role)

### Community 19 - "External Stakeholder"
Cohesion: 1.0
Nodes (1): External Stakeholder

## Knowledge Gaps
- **97 isolated node(s):** `Derek J. Hatley`, `Imtiaz A. Pirbhai`, `Tom DeMarco (Foreword author)`, `DeMarco Structured Analysis`, `Finite State Machine Theory (foundation)` (+92 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `System Hierarchy & Lifecycle`** (2 nodes): `Total System Life Cycle`, `Universal Hierarchy of Systems`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Development Spiral`** (1 nodes): `Development Life Cycle Spiral`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Multiple Hierarchies`** (1 nodes): `Multiple Hierarchies`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `System Network`** (1 nodes): `System Network`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `User Role`** (1 nodes): `User (Role)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `External Stakeholder`** (1 nodes): `External Stakeholder`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Requirements Model` connect `Requirements Modeling Layers` to `Authors, Books & Modern Extensions`, `Architecture Realization & Integration`, `Control Modeling & State Machines`, `Process Model & Notation Primitives`, `Architecture Templates & Mechanisms`, `Intellectual Foundations & Examples`, `Requirements Engineering Activities`, `Flow Types & Dictionary Primitives`, `Modeling Discipline & Heuristics`?**
  _High betweenness centrality (0.373) - this node is a cross-community bridge._
- **Why does `Architecture Model` connect `Architecture Realization & Integration` to `Authors, Books & Modern Extensions`, `Process Model & Notation Primitives`, `Requirements Modeling Layers`, `Architecture Templates & Mechanisms`, `Intellectual Foundations & Examples`, `Architecture Flow & Traceability`?**
  _High betweenness centrality (0.330) - this node is a cross-community bridge._
- **Why does `Strategies for Real-Time System Specification (1988)` connect `Authors, Books & Modern Extensions` to `Control Modeling & State Machines`, `Requirements Modeling Layers`, `Intellectual Foundations & Examples`, `Requirements Engineering Activities`, `Architecture Flow & Traceability`?**
  _High betweenness centrality (0.295) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Architecture Model` (e.g. with `Workflow-Centered Architecture` and `Mechanisms Model (intermediate solution-pattern layer)`) actually correct?**
  _`Architecture Model` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Requirements Model` (e.g. with `Model as Feedback Control Loop` and `Mechanisms Model (intermediate solution-pattern layer)`) actually correct?**
  _`Requirements Model` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Derek J. Hatley`, `Imtiaz A. Pirbhai`, `Tom DeMarco (Foreword author)` to the rest of the system?**
  _97 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Authors, Books & Modern Extensions` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._