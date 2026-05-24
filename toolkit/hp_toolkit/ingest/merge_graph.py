"""Deterministic IR merge — combines all the agents' intermediate JSONs into
a single validated `intermediate/hp-graph.json`.

Pure Python, no LLM. Reads:
  - intermediate/scan.json
  - intermediate/boundary.json           (output of hp-ingest-boundary)
  - intermediate/processes.json          (output of hp-ingest-processes)
  - intermediate/leaf-<process-id>.json  (one per process from hp-ingest-leaf)
  - intermediate/architecture.json       (output of hp-ingest-architect)

Each of those files contains nodes + edges in IR shape. Merge logic:

1. Concatenate all nodes + edges.
2. Normalize enum drift via alias tables (LLMs emit `Terminator/terminator/
   external_actor/external_system` for the same thing — collapse to canonical).
3. De-duplicate by id (keep the highest-confidence version).
4. Drop dangling edges (both endpoints must exist as nodes).
5. Validate against `IRGraph` schema.
6. Log all corrections to stderr so the reviewer LLM can repair what couldn't
   be normalized deterministically.

The output is `hp-graph.json` — input to the assembler-reviewer (Commit 3).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from .schema import IREdge, IREdgeKind, IRGraph, IRNode, IRNodeKind, ProjectScan


# ─────────────────────────────────────────────────────────────────────
# Alias tables — collapse LLM enum drift to canonical values
# ─────────────────────────────────────────────────────────────────────

_NODE_KIND_ALIASES: dict[str, IRNodeKind] = {
    # terminator
    "terminator": IRNodeKind.TERMINATOR,
    "Terminator": IRNodeKind.TERMINATOR,
    "external_actor": IRNodeKind.TERMINATOR,
    "external_entity": IRNodeKind.TERMINATOR,
    "external_system": IRNodeKind.TERMINATOR,
    "actor": IRNodeKind.TERMINATOR,
    # process
    "process": IRNodeKind.PROCESS,
    "Process": IRNodeKind.PROCESS,
    "internal_process": IRNodeKind.PROCESS,
    "bubble": IRNodeKind.PROCESS,
    # data store
    "data_store": IRNodeKind.DATA_STORE,
    "dataStore": IRNodeKind.DATA_STORE,
    "datastore": IRNodeKind.DATA_STORE,
    "store": IRNodeKind.DATA_STORE,
    "DataStore": IRNodeKind.DATA_STORE,
    # state
    "state": IRNodeKind.STATE,
    "State": IRNodeKind.STATE,
    "mode": IRNodeKind.STATE,
    # composite state
    "state_composite": IRNodeKind.STATE_COMPOSITE,
    "composite_state": IRNodeKind.STATE_COMPOSITE,
    "compositeState": IRNodeKind.STATE_COMPOSITE,
    # pspec
    "pspec": IRNodeKind.PSPEC,
    "PSPEC": IRNodeKind.PSPEC,
    "process_spec": IRNodeKind.PSPEC,
    # architecture module
    "architecture_module": IRNodeKind.ARCHITECTURE_MODULE,
    "arch_module": IRNodeKind.ARCHITECTURE_MODULE,
    "module": IRNodeKind.ARCHITECTURE_MODULE,
    "ArchModule": IRNodeKind.ARCHITECTURE_MODULE,
    # architecture interconnect
    "architecture_interconnect": IRNodeKind.ARCHITECTURE_INTERCONNECT,
    "arch_interconnect": IRNodeKind.ARCHITECTURE_INTERCONNECT,
    "interconnect": IRNodeKind.ARCHITECTURE_INTERCONNECT,
}


_EDGE_KIND_ALIASES: dict[str, IREdgeKind] = {
    # data flow
    "data_flow": IREdgeKind.DATA_FLOW,
    "dataFlow": IREdgeKind.DATA_FLOW,
    "flow": IREdgeKind.DATA_FLOW,
    "data": IREdgeKind.DATA_FLOW,
    # control flow
    "control_flow": IREdgeKind.CONTROL_FLOW,
    "controlFlow": IREdgeKind.CONTROL_FLOW,
    "control": IREdgeKind.CONTROL_FLOW,
    # physical
    "physical_edge": IREdgeKind.PHYSICAL_EDGE,
    "physical": IREdgeKind.PHYSICAL_EDGE,
    # allocates_to
    "allocates_to": IREdgeKind.ALLOCATES_TO,
    "allocatesTo": IREdgeKind.ALLOCATES_TO,
    "allocates": IREdgeKind.ALLOCATES_TO,
    "allocation": IREdgeKind.ALLOCATES_TO,
    # triggers
    "triggers": IREdgeKind.TRIGGERS,
    "trigger": IREdgeKind.TRIGGERS,
    "transition": IREdgeKind.TRIGGERS,
    # refines
    "refines": IREdgeKind.REFINES,
    "refine": IREdgeKind.REFINES,
    "decomposes_into": IREdgeKind.REFINES,
    # `deploys` — invented by the Stage-5 architect agent on the cloudctlplane
    # dogfood (modeled "this deployment unit composes these constituent
    # modules"). Maps to `refines` per locked tuning Q1 (alias-only; promote
    # to first-class IREdgeKind only if it recurs across multiple dogfood
    # targets). See INGEST_TUNING_DESIGN.md §E.1.
    "deploys": IREdgeKind.REFINES,
    "deploy": IREdgeKind.REFINES,
    "deployed_by": IREdgeKind.REFINES,
    # carries
    "carries": IREdgeKind.CARRIES,
    "carry": IREdgeKind.CARRIES,
}


# Edge kinds the LLM agents emit that are NOT first-class HP relationships
# and should be silently dropped during merge (with a single normalization
# log line) instead of cluttering the merge-report as unrecoverable. Per
# locked tuning Q1 + E.3.
#
# `depends_on_library` was invented by the Stage-5 architect agent on the
# cloudctlplane dogfood to express "this module uses this shared library/
# SDK." That's implementation detail, not HP architecture — library use is
# captured (if anywhere) via `implemented_by`, not as a top-level edge.
_EDGE_KINDS_TO_DROP: set[str] = {
    "depends_on_library",
    "depends_on_libraries",
    "uses_library",
    "library_dependency",
}


# ─────────────────────────────────────────────────────────────────────
# Report — stderr-style for the reviewer LLM
# ─────────────────────────────────────────────────────────────────────

class MergeReport:
    """Accumulates structured warnings/corrections during merge. Fed to the
    reviewer LLM so it can repair what the merger couldn't normalize."""

    def __init__(self) -> None:
        self.normalizations: list[str] = []   # alias substitutions
        self.duplicates: list[str] = []       # duplicate ids resolved
        self.dropped_edges: list[str] = []    # edges with missing endpoints
        self.unrecoverable: list[str] = []    # schema validation failures
        self.warnings: list[str] = []         # recoverable issues for reviewer attention

    def log(self, kind: str, message: str) -> None:
        bucket = getattr(self, kind, None)
        if bucket is None:
            raise ValueError(f"unknown report bucket: {kind}")
        bucket.append(message)

    def render(self) -> str:
        sections: list[str] = []
        if self.normalizations:
            sections.append("=== normalizations ===\n" + "\n".join(self.normalizations))
        if self.duplicates:
            sections.append("=== duplicates resolved ===\n" + "\n".join(self.duplicates))
        if self.dropped_edges:
            sections.append("=== dropped dangling edges ===\n" + "\n".join(self.dropped_edges))
        if self.warnings:
            sections.append("=== warnings (recoverable; reviewer attention) ===\n"
                            + "\n".join(self.warnings))
        if self.unrecoverable:
            sections.append("=== unrecoverable issues (needs LLM repair) ===\n"
                            + "\n".join(self.unrecoverable))
        return "\n\n".join(sections) if sections else "(no issues)"

    def is_clean(self) -> bool:
        return not (self.duplicates or self.dropped_edges or self.unrecoverable
                    or self.warnings)


# ─────────────────────────────────────────────────────────────────────
# Merge
# ─────────────────────────────────────────────────────────────────────

def merge_intermediates(intermediate_dir: Path) -> tuple[IRGraph, MergeReport]:
    """Read every JSON in `intermediate_dir`, build a unified `IRGraph`.

    The scan.json must exist; others are optional (allows partial pipelines
    e.g. Commit 2 with no architecture.json yet).
    """
    report = MergeReport()

    scan_path = intermediate_dir / "scan.json"
    if not scan_path.exists():
        raise FileNotFoundError(f"missing required intermediate: {scan_path}")
    scan = ProjectScan.model_validate(json.loads(scan_path.read_text()))

    raw_nodes: list[dict] = []
    raw_edges: list[dict] = []

    # Per-agent intermediate files we know about
    candidate_files = [
        "boundary.json", "processes.json", "architecture.json",
    ]
    for name in candidate_files:
        p = intermediate_dir / name
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        raw_nodes.extend(data.get("nodes", []))
        raw_edges.extend(data.get("edges", []))

    # Per-process leaf outputs land as leaf-<process-id>.json
    for p in sorted(intermediate_dir.glob("leaf-*.json")):
        data = json.loads(p.read_text())
        raw_nodes.extend(data.get("nodes", []))
        raw_edges.extend(data.get("edges", []))

    # ─── Normalize + de-dupe nodes ───
    by_id: dict[str, dict] = {}
    for raw in raw_nodes:
        canonical = _normalize_node(raw, report)
        if canonical is None:
            continue
        existing = by_id.get(canonical["id"])
        if existing is None:
            by_id[canonical["id"]] = canonical
        else:
            keep = _prefer_higher_confidence(existing, canonical, report)
            by_id[canonical["id"]] = keep

    # Validate each into IRNode. sys_root is special — it's auto-injected
    # by emit_dictionary and is always a valid edge endpoint (terminators
    # and processes flow to/from it), so we pre-seed it.
    nodes: list[IRNode] = []
    valid_ids: set[str] = {"sys_root"}
    for nid, raw in by_id.items():
        try:
            node = IRNode.model_validate(raw)
            nodes.append(node)
            valid_ids.add(node.id)
        except ValidationError as e:
            report.log("unrecoverable", f"node {nid}: {e}")

    # ─── Normalize edges + drop danglers ───
    edges: list[IREdge] = []
    seen_edges: set[tuple] = set()
    for raw in raw_edges:
        canonical = _normalize_edge(raw, report)
        if canonical is None:
            continue
        src, tgt = canonical.get("source"), canonical.get("target")
        if not src or not tgt:
            report.log("dropped_edges", f"edge missing endpoint: {canonical}")
            continue
        if src not in valid_ids or tgt not in valid_ids:
            report.log("dropped_edges",
                       f"edge {src} -> {tgt} ({canonical.get('kind')}): endpoint not in nodes")
            continue
        # De-dupe identical edges (same src/tgt/kind)
        key = (src, tgt, canonical.get("kind"))
        if key in seen_edges:
            continue
        seen_edges.add(key)
        try:
            edges.append(IREdge.model_validate(canonical))
        except ValidationError as e:
            report.log("unrecoverable", f"edge {src}->{tgt}: {e}")

    # H.1.2 — flag Stage-1 boundary flows that never got a refined endpoint.
    # The Stage-2 agent is supposed to set `refined_source` / `refined_target`
    # on every boundary flow so the level-1 DFD renders with internal-process
    # endpoints instead of dangling at sys_root. When the Stage-2 agent skips
    # that step, the reviewer needs to repair.
    unrefined = []
    for e in edges:
        if (e.stage == 1
                and (e.source == "sys_root" or e.target == "sys_root")
                and not getattr(e, "refined_source", None)
                and not getattr(e, "refined_target", None)):
            extras = e.model_dump(exclude={"source", "target", "kind", "stage",
                                            "confidence", "provenance", "label"})
            extras = {k: v for k, v in extras.items() if v is not None}
            if not (extras.get("refined_source") or extras.get("refined_target")):
                unrefined.append(f"{e.source} -> {e.target} ({e.label or '(no label)'})")
    if unrefined:
        report.log("warnings",
                   f"boundary-flow refinement missing on {len(unrefined)} edge(s) — "
                   f"Stage-2 agent did not set refined_source/refined_target; "
                   f"level-1 DFD will render dangling. Reviewer should repair "
                   f"by cross-referencing processes.json to identify the "
                   f"handling process for each boundary flow:\n  "
                   + "\n  ".join(unrefined))

    graph = IRGraph(
        project=scan.project,
        nodes=nodes,
        edges=edges,
        scan=scan,
    )
    return graph, report


def write_graph(graph: IRGraph, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(graph.model_dump_json(indent=2))


def write_report(report: MergeReport, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.render())


# ─────────────────────────────────────────────────────────────────────
# Normalization
# ─────────────────────────────────────────────────────────────────────

def _normalize_node(raw: dict, report: MergeReport) -> Optional[dict]:
    """Apply alias tables + strip common ID prefixes. Returns the canonicalized
    dict, or None if the node is too broken to recover."""
    if "id" not in raw or "kind" not in raw:
        report.log("unrecoverable", f"node missing id/kind: {raw}")
        return None
    out = dict(raw)
    out["id"] = _normalize_id(out["id"])
    raw_kind = out["kind"]
    if isinstance(raw_kind, str) and raw_kind in _NODE_KIND_ALIASES:
        canonical = _NODE_KIND_ALIASES[raw_kind]
        if canonical.value != raw_kind:
            report.log("normalizations",
                       f"node {out['id']}: kind {raw_kind!r} -> {canonical.value!r}")
        out["kind"] = canonical.value
    return out


def _normalize_edge(raw: dict, report: MergeReport) -> Optional[dict]:
    if "source" not in raw or "target" not in raw or "kind" not in raw:
        report.log("unrecoverable", f"edge missing fields: {raw}")
        return None
    out = dict(raw)
    out["source"] = _normalize_id(out["source"])
    out["target"] = _normalize_id(out["target"])
    raw_kind = out["kind"]
    # Silently drop edges in the drop-set (library deps, etc.) — they're not
    # HP-architectural and shouldn't reach the reviewer as unrecoverable. Log
    # the drop as a normalization for audit.
    if isinstance(raw_kind, str) and raw_kind in _EDGE_KINDS_TO_DROP:
        report.log("normalizations",
                   f"edge {out['source']}->{out['target']}: "
                   f"kind {raw_kind!r} dropped (not an HP-architectural relationship)")
        return None
    if isinstance(raw_kind, str) and raw_kind in _EDGE_KIND_ALIASES:
        canonical = _EDGE_KIND_ALIASES[raw_kind]
        if canonical.value != raw_kind:
            report.log("normalizations",
                       f"edge {out['source']}->{out['target']}: "
                       f"kind {raw_kind!r} -> {canonical.value!r}")
        out["kind"] = canonical.value
    return out


def _normalize_id(raw_id: str) -> str:
    """Strip type-prefix variations LLMs sometimes emit (e.g., `terminator:user`
    or `Terminator(user)`)."""
    raw = raw_id.strip()
    # Strip type prefix like `terminator:user`
    if ":" in raw:
        prefix, rest = raw.split(":", 1)
        if prefix.lower() in {k.lower() for k in _NODE_KIND_ALIASES}:
            raw = rest
    # Strip parens like `Terminator(user)`
    if "(" in raw and raw.endswith(")"):
        head, _, rest = raw.partition("(")
        if head.lower() in {k.lower() for k in _NODE_KIND_ALIASES}:
            raw = rest[:-1]
    return raw


def _prefer_higher_confidence(a: dict, b: dict, report: MergeReport) -> dict:
    """When the same node id appears twice, keep the higher-confidence version.

    Logs a duplicate for the reviewer."""
    a_conf = float(a.get("confidence", 0.0))
    b_conf = float(b.get("confidence", 0.0))
    winner = a if a_conf >= b_conf else b
    loser = b if winner is a else a
    report.log("duplicates",
               f"node {a['id']}: kept conf={max(a_conf, b_conf):.2f}, "
               f"dropped conf={min(a_conf, b_conf):.2f} (label '{loser.get('label')}')")
    return winner


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def _main(argv: Optional[list[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="hp_merge_graph",
        description="Deterministic merge of ingest intermediates → hp-graph.json.",
    )
    parser.add_argument("--intermediate", required=True,
                        help="Directory containing scan.json + agent outputs")
    parser.add_argument("--output", required=True, help="Output path for hp-graph.json")
    parser.add_argument("--report", help="Optional path for merge-report.txt")
    args = parser.parse_args(argv)

    graph, report = merge_intermediates(Path(args.intermediate))
    write_graph(graph, Path(args.output))
    print(f"wrote {args.output} ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")

    if args.report:
        write_report(report, Path(args.report))
        if not report.is_clean():
            print(f"merge report (issues): {args.report}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
