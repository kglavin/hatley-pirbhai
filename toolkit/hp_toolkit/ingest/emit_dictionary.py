"""IR → dictionary.yaml emitter.

Pure Python, no LLM. Takes the merged `intermediate/hp-graph.json` (output
of `merge_graph.py` after all 6 agents have run) and produces a valid
HP `dictionary.yaml` consumable by the existing toolkit (validate / render /
status / portal / PDF).

Translation:
  IRNode.kind=terminator               → entities[<id>] (kind: terminator)
  IRNode.kind=process                  → entities[<id>] (kind: process)
  IRNode.kind=data_store               → entities[<id>] (kind: data_store)
  IRNode.kind=state                    → entities[<id>] (kind: state)
  IRNode.kind=state_composite          → entities[<id>] (kind: state_composite)
  IRNode.kind=pspec                    → pspecs[<id>]
  IRNode.kind=architecture_module      → architecture_modules[<id>] (+ AMS)
  IRNode.kind=architecture_interconnect → architecture_interconnects[<id>] (+ AIS)

  IREdge.kind=data_flow / control_flow → flows[<id>]
  IREdge.kind=triggers                 → transitions[<id>]
  IREdge.kind=allocates_to             → architecture_modules[].allocated_processes
                                          / .allocated_cspecs / .allocated_stores

Stripped from the YAML output (lives only in `hp-graph.json` for incremental
re-ingest reconciliation):
  - confidence
  - provenance
  - implemented_by

The system root (`sys_root`) is auto-injected if not already present.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import yaml

from .schema import IREdge, IREdgeKind, IRGraph, IRNode, IRNodeKind


def emit_dictionary(graph: IRGraph, output_path: Path) -> None:
    """Write a `dictionary.yaml` at `output_path` from the merged IR graph."""
    doc = build_dictionary_dict(graph)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_yaml_dump(doc))


def build_dictionary_dict(graph: IRGraph) -> dict[str, Any]:
    """Construct the dictionary.yaml document as a Python dict — useful for
    testing the mapping without going through YAML."""
    entities: dict[str, Any] = {}
    flows: dict[str, Any] = {}
    transitions: dict[str, Any] = {}
    pspecs: dict[str, Any] = {}
    architecture_modules: dict[str, Any] = {}
    architecture_interconnects: dict[str, Any] = {}
    architecture_module_specs: dict[str, Any] = {}
    architecture_interconnect_specs: dict[str, Any] = {}

    # ─── sys_root scaffold ───
    entities["sys_root"] = {
        "kind": "system",
        "label": graph.project.name,
        "level": 0,
        "description": graph.project.description
            or f"The {graph.project.name} system under design.",
    }

    # ─── Nodes → entities / pspecs / architecture_* ───
    for n in graph.nodes:
        if n.kind in (IRNodeKind.TERMINATOR, IRNodeKind.PROCESS, IRNodeKind.DATA_STORE):
            entities[n.id] = _emit_entity(n)
        elif n.kind in (IRNodeKind.STATE, IRNodeKind.STATE_COMPOSITE):
            entities[n.id] = _emit_entity(n)
        elif n.kind == IRNodeKind.PSPEC:
            pspecs[n.id] = _emit_pspec(n)
        elif n.kind == IRNodeKind.ARCHITECTURE_MODULE:
            architecture_modules[n.id] = _emit_arch_module(n)
            # Auto-AMS scaffold (the architect agent often writes one inline)
            ams_id = "ams_" + _strip_prefix(n.id, "am_")
            architecture_module_specs[ams_id] = _emit_ams(n)
        elif n.kind == IRNodeKind.ARCHITECTURE_INTERCONNECT:
            architecture_interconnects[n.id] = _emit_arch_interconnect(n)
            ais_id = "ais_" + _strip_prefix(n.id, "ai_")
            architecture_interconnect_specs[ais_id] = _emit_ais(n)

    # ─── Edges → flows / transitions / allocation ───
    flow_counter = 1
    for e in graph.edges:
        if e.kind in (IREdgeKind.DATA_FLOW, IREdgeKind.CONTROL_FLOW):
            flow_id = _flow_id(e, flow_counter)
            flows[flow_id] = _emit_flow(e)
            flow_counter += 1
        elif e.kind == IREdgeKind.TRIGGERS:
            txn_id = _transition_id(e)
            transitions[txn_id] = _emit_transition(e)
        elif e.kind == IREdgeKind.ALLOCATES_TO:
            _apply_allocation(e, architecture_modules, entities)
        elif e.kind == IREdgeKind.PHYSICAL_EDGE:
            # Physical edges land in dictionary's `edges:` section
            # (not the same as IREdge — naming collision tolerated)
            pass

    # ─── Strip empty sections + assemble ───
    doc: dict[str, Any] = {
        "project": graph.project.name,
        "version": "0.1",
        "last_updated": graph.project.analyzed_at.date().isoformat(),
        "entities": entities,
    }
    if flows:
        doc["flows"] = flows
    if transitions:
        doc["transitions"] = transitions
    if pspecs:
        doc["pspecs"] = pspecs
    if architecture_modules:
        doc["architecture_modules"] = architecture_modules
        doc["architecture_module_specs"] = architecture_module_specs
    if architecture_interconnects:
        doc["architecture_interconnects"] = architecture_interconnects
        doc["architecture_interconnect_specs"] = architecture_interconnect_specs

    return doc


# ─────────────────────────────────────────────────────────────────────
# Per-kind emitters
# ─────────────────────────────────────────────────────────────────────

def _emit_entity(n: IRNode) -> dict[str, Any]:
    out: dict[str, Any] = {
        "kind": n.kind.value,
        "label": n.label,
        "description": n.summary or n.description or "",
    }
    # Level by kind: terminator/process/data_store at level 1; states deeper.
    if n.kind == IRNodeKind.TERMINATOR:
        out["level"] = 0
        out["parent"] = n.parent or "sys_root"
    elif n.kind in (IRNodeKind.PROCESS, IRNodeKind.DATA_STORE):
        out["level"] = 1
        out["parent"] = n.parent or "sys_root"
        if n.kind == IRNodeKind.PROCESS and n.needs_cspec:
            out["needs_cspec"] = True
    elif n.kind in (IRNodeKind.STATE, IRNodeKind.STATE_COMPOSITE):
        out["level"] = 2
        if n.parent_machine:
            out["parent_machine"] = n.parent_machine
        if n.parent:
            out["parent"] = n.parent
        if n.is_initial:
            out["is_initial"] = True
    if n.optional:
        out["optional"] = True
    return out


def _emit_pspec(n: IRNode) -> dict[str, Any]:
    out: dict[str, Any] = {
        "parent_process": n.parent or n.id.replace("pspec_", "proc_"),
    }
    # The leaf agent attaches `transformation` directly on the node (extra="allow")
    extras = n.model_dump(exclude={
        "id", "kind", "label", "stage", "confidence", "provenance",
        "implemented_by", "summary", "description", "needs_cspec",
        "is_initial", "optional", "parent", "parent_machine",
    })
    extras = {k: v for k, v in extras.items() if v is not None}
    if "transformation" not in extras:
        # Best-effort transformation scaffold for the architect to refine
        extras["transformation"] = {
            "style": "textual",
            "body": n.summary or n.description or "(transformation body pending review)",
        }
    out.update(extras)
    return out


def _emit_arch_module(n: IRNode) -> dict[str, Any]:
    extras = n.model_dump(exclude={
        "id", "kind", "label", "stage", "confidence", "provenance",
        "implemented_by", "summary", "description", "needs_cspec",
        "is_initial", "optional", "parent", "parent_machine",
    })
    extras = {k: v for k, v in extras.items() if v is not None}
    out: dict[str, Any] = {
        "name": n.label,
        "kind": extras.pop("module_kind", "software"),
        "description": n.summary or n.description or "",
        "allocated_processes": extras.pop("allocated_processes", []),
        "allocated_cspecs":    extras.pop("allocated_cspecs", []),
        "allocated_stores":    extras.pop("allocated_stores", []),
    }
    out.update(extras)
    return out


def _emit_arch_interconnect(n: IRNode) -> dict[str, Any]:
    extras = n.model_dump(exclude={
        "id", "kind", "label", "stage", "confidence", "provenance",
        "implemented_by", "summary", "description", "needs_cspec",
        "is_initial", "optional", "parent", "parent_machine",
    })
    extras = {k: v for k, v in extras.items() if v is not None}
    out: dict[str, Any] = {
        "name": n.label,
        "endpoints": extras.pop("endpoints", []),
        "carries":   extras.pop("carries", []),
        "description": n.summary or n.description or "",
    }
    out.update(extras)
    return out


def _emit_ams(n: IRNode) -> dict[str, Any]:
    return {
        "parent_module": n.id,
        "description": n.summary or n.description
            or f"Module specification for {n.label}.",
        "design_rationale": "(ingest-authored; architect review pending)",
    }


def _emit_ais(n: IRNode) -> dict[str, Any]:
    return {
        "parent_interconnect": n.id,
        "description": n.summary or n.description
            or f"Interconnect specification for {n.label}.",
    }


def _emit_flow(e: IREdge) -> dict[str, Any]:
    # Flow level is derived from the edge's stage: Stage 1 = level 0 (boundary
    # flow from terminator to sys_root); Stage 2 = level 1 (internal flow).
    # The validator uses level to drive its hierarchy checks.
    level = 0 if e.stage == 1 else 1
    return {
        "label": e.label or f"{e.source} → {e.target}",
        "kind": "data" if e.kind == IREdgeKind.DATA_FLOW else "control",
        "level": level,
        "source": e.source,
        "target": e.target,
    }


def _emit_transition(e: IREdge) -> dict[str, Any]:
    out: dict[str, Any] = {
        "label": e.label or f"{e.source} → {e.target}",
        "source_state": e.source,
        "target_state": e.target,
    }
    extras = e.model_dump(exclude={"source", "target", "kind", "stage", "confidence", "provenance", "label"})
    extras = {k: v for k, v in extras.items() if v is not None}
    if "parent_machine" in extras:
        out["parent_machine"] = extras.pop("parent_machine")
    if "event" in extras:
        out["event"] = extras.pop("event")
    if "action" in extras:
        out["action"] = extras.pop("action")
    out.update(extras)
    return out


def _apply_allocation(
    e: IREdge,
    arch_modules: dict[str, Any],
    entities: dict[str, Any],
) -> None:
    """Set `architecture_modules[module].allocated_*` from an `allocates_to`
    edge. Edge convention: source = module id, target = allocated entity id."""
    mod_id, target_id = e.source, e.target
    if mod_id not in arch_modules:
        return
    target_entity = entities.get(target_id)
    if target_entity is None:
        return
    kind = target_entity.get("kind")
    if kind == "process" and target_entity.get("needs_cspec"):
        bucket = arch_modules[mod_id].setdefault("allocated_cspecs", [])
    elif kind == "process":
        bucket = arch_modules[mod_id].setdefault("allocated_processes", [])
    elif kind == "data_store":
        bucket = arch_modules[mod_id].setdefault("allocated_stores", [])
    else:
        return
    if target_id not in bucket:
        bucket.append(target_id)


# ─────────────────────────────────────────────────────────────────────
# ID helpers
# ─────────────────────────────────────────────────────────────────────

def _flow_id(e: IREdge, counter: int) -> str:
    """Synthesize a flow id from the label or fall back to `flow_<n>_...`."""
    if e.label:
        # Extract an F<N>: prefix if the LLM already numbered it
        m = re.match(r"F(\d+)[:.]", e.label.strip())
        if m:
            slug = e.label.split(":", 1)[-1].strip()
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug).strip("_").lower() or "flow"
            return f"flow_f{m.group(1)}_{slug[:30]}"
    slug = f"{e.source}_to_{e.target}"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug).strip("_").lower()
    return f"flow_{counter:03d}_{slug[:40]}"


def _transition_id(e: IREdge) -> str:
    """Synthesize a transition id `tx_<source>_to_<target>`."""
    src = _strip_prefix(e.source, "state_")
    tgt = _strip_prefix(e.target, "state_")
    return f"tx_{src}_to_{tgt}"


def _strip_prefix(s: str, prefix: str) -> str:
    return s[len(prefix):] if s.startswith(prefix) else s


# ─────────────────────────────────────────────────────────────────────
# YAML output
# ─────────────────────────────────────────────────────────────────────

class _LiteralDumper(yaml.SafeDumper):
    """SafeDumper that emits long strings as literal block scalars (|),
    which is the convention used in the hand-written dictionaries."""


def _str_representer(dumper: yaml.SafeDumper, value: str):
    if "\n" in value:
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


_LiteralDumper.add_representer(str, _str_representer)


def _yaml_dump(data: Any) -> str:
    return yaml.dump(
        data,
        Dumper=_LiteralDumper,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def _main(argv: Optional[list[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="hp_emit_dictionary",
        description="Translate hp-graph.json → dictionary.yaml.",
    )
    parser.add_argument("--graph",  required=True, help="Path to intermediate/hp-graph.json")
    parser.add_argument("--output", required=True, help="Output path for dictionary.yaml")
    args = parser.parse_args(argv)

    graph_data = json.loads(Path(args.graph).read_text())
    graph = IRGraph.model_validate(graph_data)
    emit_dictionary(graph, Path(args.output))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
