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

    # Per HIERARCHICAL_INGEST_DESIGN.md: `level` derives from the parent
    # chain depth + non-leaf processes drop their CSPEC/PSPEC. Pre-compute
    # an id→node map + child-process set so we don't re-walk for every
    # node we emit.
    by_id: dict[str, IRNode] = {n.id: n for n in graph.nodes}
    non_leaf_processes: set[str] = {
        n.parent for n in graph.nodes
        if n.kind == IRNodeKind.PROCESS and n.parent and n.parent != "sys_root"
        and by_id.get(n.parent) is not None
        and by_id[n.parent].kind == IRNodeKind.PROCESS
    }

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
            entities[n.id] = _emit_entity(n, by_id=by_id, non_leaf_processes=non_leaf_processes)
        elif n.kind in (IRNodeKind.STATE, IRNodeKind.STATE_COMPOSITE):
            entities[n.id] = _emit_entity(n, by_id=by_id, non_leaf_processes=non_leaf_processes)
        elif n.kind == IRNodeKind.PSPEC:
            # Non-leaf processes don't get PSPECs (per HIERARCHICAL_INGEST_DESIGN.md
            # Q3 lock — specs live at hierarchy leaves)
            parent_proc_id = n.parent or n.id.replace("pspec_", "proc_")
            if parent_proc_id in non_leaf_processes:
                continue
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

def _emit_entity(
    n: IRNode,
    *,
    by_id: Optional[dict[str, IRNode]] = None,
    non_leaf_processes: Optional[set[str]] = None,
) -> dict[str, Any]:
    """Render one IR entity node into its dictionary.yaml entry.

    `level` is derived from the parent chain depth (HIERARCHICAL_INGEST_DESIGN.md):
    sub-processes nested under another process come out at level=N+1 of
    their parent's level. `needs_cspec` is suppressed on non-leaf
    processes since their decomposition is a sub-DFD, not a CSPEC."""
    out: dict[str, Any] = {
        "kind": n.kind.value,
        "label": n.label,
        "description": n.summary or n.description or "",
    }
    by_id = by_id or {}
    non_leaf_processes = non_leaf_processes or set()

    if n.kind == IRNodeKind.TERMINATOR:
        out["level"] = 0
        out["parent"] = n.parent or "sys_root"
    elif n.kind in (IRNodeKind.PROCESS, IRNodeKind.DATA_STORE):
        out["level"] = _process_level(n, by_id)
        out["parent"] = n.parent or "sys_root"
        # Only LEAF processes carry needs_cspec — a non-leaf process is
        # organizational (decomposed into sub-processes), not state-rich.
        if n.kind == IRNodeKind.PROCESS and n.needs_cspec and n.id not in non_leaf_processes:
            out["needs_cspec"] = True
    elif n.kind in (IRNodeKind.STATE, IRNodeKind.STATE_COMPOSITE):
        # States sit one level below the process they belong to.
        out["level"] = _state_level(n, by_id)
        if n.parent_machine:
            out["parent_machine"] = n.parent_machine
        if n.parent:
            out["parent"] = n.parent
        if n.is_initial:
            out["is_initial"] = True
    if n.optional:
        out["optional"] = True
    return out


def _process_level(n: IRNode, by_id: dict[str, IRNode]) -> int:
    """Derive level for a process / data_store node by walking the parent
    chain. parent=sys_root → level 1; parent=other-process → level 2; etc."""
    if not n.parent or n.parent == "sys_root":
        return 1
    depth = 1
    cursor = by_id.get(n.parent)
    while cursor is not None and depth < 10:
        if not cursor.parent or cursor.parent == "sys_root":
            return depth + 1
        depth += 1
        cursor = by_id.get(cursor.parent)
    return depth + 1


def _state_level(n: IRNode, by_id: dict[str, IRNode]) -> int:
    """States sit one level below their owning process. The state's
    `parent` is the process id; we ask `_process_level` for the
    process's level and add 1. Composite-state nesting is handled via
    `parent_state`, not `level`."""
    if not n.parent:
        return 2
    parent = by_id.get(n.parent)
    if parent is None or parent.kind != IRNodeKind.PROCESS:
        return 2
    return _process_level(parent, by_id) + 1


def _emit_pspec(n: IRNode) -> dict[str, Any]:
    out: dict[str, Any] = {
        "parent_process": n.parent or n.id.replace("pspec_", "proc_"),
    }
    # The leaf agent attaches `transformation` + (per H.2.c) `comments`
    # directly on the node (extra="allow")
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
    # H.2.a: if no `comments` extra was emitted but the provenance carries
    # substantive rationale, seed comments with it so the architect-facing
    # "why" isn't lost.
    if "comments" not in extras:
        seeded = _seed_from_rationale(n)
        if seeded:
            extras["comments"] = seeded
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
    """Per H.2.a: surface what the IR has rather than hard-coding the placeholder.

    The architect agent emits `design_rationale` / `design_justification` /
    `required_constraints` as extras on the IR node (per the H.2.c prompt
    tightening). If those are present, they pass through verbatim. If not,
    fall back to `provenance.rationale` when it's substantive (> 1 sentence
    worth of prose). The placeholder only fires when the IR truly has
    nothing to surface."""
    out: dict[str, Any] = {
        "parent_module": n.id,
        "description": n.summary or n.description
            or f"Module specification for {n.label}.",
    }
    extras = n.model_dump(exclude={
        "id", "kind", "label", "stage", "confidence", "provenance",
        "implemented_by", "summary", "description", "needs_cspec",
        "is_initial", "optional", "parent", "parent_machine",
        # AMS doesn't carry the architecture-module structural fields —
        # those belong on the `architecture_modules:` entry, not the AMS
        "module_kind", "trust_zone", "endpoints", "carries",
        "allocated_processes", "allocated_cspecs", "allocated_stores",
    })
    extras = {k: v for k, v in extras.items() if v is not None}

    # `design_rationale` is the marquee field; pull from extras if present,
    # else seed from provenance.rationale when it carries substantive prose.
    rationale = extras.pop("design_rationale", None) or _seed_from_rationale(n)
    out["design_rationale"] = rationale or "(ingest-authored; architect review pending)"

    # Pass through any other AMS prose fields the architect agent emitted
    out.update(extras)
    return out


def _emit_ais(n: IRNode) -> dict[str, Any]:
    """Per H.2.a: same treatment as `_emit_ams` for interconnect specs.

    The architect agent's `design_rationale` extra (when emitted) becomes
    the AIS's rationale field; otherwise fall back to provenance.rationale.
    Extras like `protocol`, `medium`, `bandwidth_estimate` flow through."""
    out: dict[str, Any] = {
        "parent_interconnect": n.id,
        "description": n.summary or n.description
            or f"Interconnect specification for {n.label}.",
    }
    extras = n.model_dump(exclude={
        "id", "kind", "label", "stage", "confidence", "provenance",
        "implemented_by", "summary", "description", "needs_cspec",
        "is_initial", "optional", "parent", "parent_machine",
        # Structural fields live on `architecture_interconnects:`, not AIS
        "endpoints", "carries",
    })
    extras = {k: v for k, v in extras.items() if v is not None}

    rationale = extras.pop("design_rationale", None) or _seed_from_rationale(n)
    if rationale:
        out["design_rationale"] = rationale

    out.update(extras)
    return out


_PLACEHOLDER_RATIONALES = {
    "(no rationale)",
    "(architect review pending)",
    "(ingest-authored; architect review pending)",
}


def _seed_from_rationale(n: IRNode) -> Optional[str]:
    """Return `provenance.rationale` if it carries substantive prose.

    Per H.2.a: the architect agent's one-line rationale (e.g. *"TS package
    + Dockerfile + compose service across deployments. Single node:22-alpine
    runtime. Owns proc_explore_graphql including the WS subscription
    lifecycle CSPEC."*) IS the seed for `design_rationale` when no richer
    prose extra was emitted. Discard placeholder strings + one-word
    rationales that aren't useful as prose."""
    if n.provenance is None:
        return None
    r = (n.provenance.rationale or "").strip()
    if not r or r in _PLACEHOLDER_RATIONALES:
        return None
    # A "substantive" rationale is anything longer than 40 characters OR
    # containing >=1 sentence-ending punctuation — captures the example
    # rationales the architect agent currently produces.
    if len(r) >= 40 or any(p in r for p in ".!?"):
        return r
    return None


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
    from .progress_log import log_done, log_start
    parser = argparse.ArgumentParser(
        prog="hp_emit_dictionary",
        description="Translate hp-graph.json → dictionary.yaml.",
    )
    parser.add_argument("--graph",  required=True, help="Path to intermediate/hp-graph.json")
    parser.add_argument("--output", required=True, help="Output path for dictionary.yaml")
    args = parser.parse_args(argv)

    intermediate = Path(args.graph).parent
    log_start(intermediate, stage="emit", agent="emit_dictionary")

    graph_data = json.loads(Path(args.graph).read_text())
    graph = IRGraph.model_validate(graph_data)
    out_path = Path(args.output)
    emit_dictionary(graph, out_path)
    print(f"wrote {args.output}")

    log_done(intermediate, stage="emit", agent="emit_dictionary",
             bytes=out_path.stat().st_size)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
