"""Hierarchical-ingest recursion helpers (H.3 / Branch 3).

Per locked HIERARCHICAL_INGEST_DESIGN.md: Stage 2 of hp-ingest becomes
recursive on monorepo-scale targets. After level-1 processes are
emitted, each one whose `implemented_by[]` exceeds the threshold gets
its own scoped Stage-2 dispatch — emitting level-2 sub-processes with
`parent: <level-1-proc-id>`. The recursion continues to
`--max-recursion-depth` (default 3).

This module provides two helpers used by the orchestrator + the
hp-ingest-processes subagent:

- `should_recurse(process, depth, config)` — the auto-threshold decision
  (Q2 lock: 30 files AND 3000 lines, depth < max).
- `scope_for_subsystem(scan, paths)` — produces a scoped `ProjectScan`
  containing only the files in `paths`, with `import_map` restricted to
  edges where both endpoints are inside the subsystem. The scoped scan
  is what the recursive Stage-2 prep + subagent see.

Pure Python, no LLM. The recursion *decision* is deterministic; the
recursive Stage 2 dispatch produces the actual sub-process IR via the
existing LLM subagent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .schema import FileEntry, IRNode, ProjectScan


# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

@dataclass
class RecursionConfig:
    """Tunable thresholds for `should_recurse`.

    Defaults locked at Q4 (HIERARCHICAL_INGEST_DESIGN.md): a process
    recurses if it has ≥ 30 files in its `implemented_by[]` AND those
    files total ≥ 3000 lines AND the current depth is below the cap.

    Both file-count + line-count gates fire because either alone is a
    poor signal: 30 trivial files isn't a subsystem; 3 thick files
    isn't either."""

    threshold_files: int = 30
    threshold_lines: int = 3000
    max_depth: int = 3
    enabled: bool = True            # `--no-recurse` flips this off


# ─────────────────────────────────────────────────────────────────────
# Decision: should we recurse on this process?
# ─────────────────────────────────────────────────────────────────────

def should_recurse(
    process: IRNode,
    depth: int,
    scan: ProjectScan,
    config: Optional[RecursionConfig] = None,
) -> tuple[bool, str]:
    """Decide whether to dispatch a recursive Stage-2 on `process`.

    Returns (decision, reason). The reason string is for the progress
    log + the orchestrator's loud announcement (matches the locked
    F.2 verbosity discipline from Branch 1).

    A process recurses iff:
      - recursion is enabled (--recurse not opted out)
      - depth < max_depth
      - process is a leaf in the IR sense (kind=process; not data_store)
      - len(implemented_by) ≥ threshold_files
      - total lines across implemented_by ≥ threshold_lines
    """
    cfg = config or RecursionConfig()
    if not cfg.enabled:
        return False, "recursion disabled (--no-recurse)"
    if depth >= cfg.max_depth:
        return False, f"depth={depth} reached --max-recursion-depth={cfg.max_depth}"
    if process.kind.value != "process":
        return False, f"kind={process.kind.value} (only processes recurse)"
    file_count = len(process.implemented_by)
    if file_count < cfg.threshold_files:
        return False, f"files={file_count} < threshold={cfg.threshold_files}"
    lines = _total_lines(process.implemented_by, scan)
    if lines < cfg.threshold_lines:
        return False, f"lines={lines} < threshold={cfg.threshold_lines}"
    return True, f"files={file_count} ≥ {cfg.threshold_files}; lines={lines} ≥ {cfg.threshold_lines}"


def _total_lines(implemented_by: Iterable[str], scan: ProjectScan) -> int:
    """Sum line counts for paths in `implemented_by` by looking them up
    in the scan. Files missing from scan contribute 0 (the scan is
    authoritative for size — re-stat-ing would be redundant)."""
    by_path = {f.path: f for f in scan.files}
    return sum(by_path[p].size_lines for p in implemented_by if p in by_path)


# ─────────────────────────────────────────────────────────────────────
# Scope: produce a per-subsystem ProjectScan view
# ─────────────────────────────────────────────────────────────────────

def scope_for_subsystem(scan: ProjectScan, paths: Iterable[str]) -> ProjectScan:
    """Return a new ProjectScan containing only files in `paths`.

    Used by the recursion orchestrator to write `intermediate/<P-id>/scan.json`
    so the recursive Stage-2 candidate-prep + subagent see exactly the
    subsystem's files. The import_map is restricted to edges where both
    source + target are inside the subsystem (cross-subsystem imports
    are summarized in the parent process's flows, not surfaced in the
    sub-scan)."""
    path_set = set(paths)
    scoped_files: list[FileEntry] = [f for f in scan.files if f.path in path_set]
    scoped_imports: dict[str, list[str]] = {}
    for src, targets in scan.import_map.items():
        if src not in path_set:
            continue
        inner = [t for t in targets if t in path_set]
        if inner:
            scoped_imports[src] = inner
    return ProjectScan(
        project=scan.project,
        files=scoped_files,
        import_map=scoped_imports,
    )


# ─────────────────────────────────────────────────────────────────────
# Per-subsystem intermediate directory
# ─────────────────────────────────────────────────────────────────────

def subsystem_dir(intermediate_dir: Path, process_id: str) -> Path:
    """Per-locked design: `intermediate/<P-id>/` keeps the recursion's
    scoped outputs isolated from the parent + siblings.

    Used for `--resume`: re-running a single subsystem's recursion only
    requires deleting its directory."""
    return Path(intermediate_dir) / process_id


# ─────────────────────────────────────────────────────────────────────
# Level derivation
# ─────────────────────────────────────────────────────────────────────

def derive_level(node: IRNode, by_id: dict[str, IRNode]) -> int:
    """Walk the `parent` chain back to `sys_root` + count the depth.

    Used by the emitter (per design doc) so `level:` isn't hard-coded
    to 1 — it falls out of the parent chain. `sys_root` itself is level
    0; immediate children are level 1; their children are level 2; etc.

    Defensive: if the chain hits a missing parent, return the current
    accumulated depth (the validator catches the broken chain
    separately)."""
    if node.parent is None or node.parent == "sys_root":
        # By HP convention: terminators sit at level 0; processes at
        # level 1 when their direct parent is sys_root.
        if node.kind.value == "terminator":
            return 0
        return 1
    depth = 1
    cursor = by_id.get(node.parent)
    while cursor is not None and depth < 10:        # bound — paranoia against cycles
        if cursor.parent is None or cursor.parent == "sys_root":
            return depth + 1
        depth += 1
        cursor = by_id.get(cursor.parent)
    return depth + 1


def is_leaf_process(process_id: str, all_nodes: Iterable[IRNode]) -> bool:
    """A process is a leaf iff no other process node lists it as `parent`.

    Used by the emitter to decide whether to attach a PSPEC / set
    `needs_cspec` (only leaf processes get specs — non-leaf processes
    are organizational, per Q3 lock)."""
    for n in all_nodes:
        if n.kind.value == "process" and n.parent == process_id:
            return False
    return True


# ─────────────────────────────────────────────────────────────────────
# Subsystem prep — write scoped intermediates per process to recurse on
# ─────────────────────────────────────────────────────────────────────

def prepare_subsystem_recursions(
    processes_graph_path: Path,
    scan_path: Path,
    intermediate_dir: Path,
    *,
    current_depth: int,
    config: Optional[RecursionConfig] = None,
    max_depth_param: Optional[int] = None,
) -> list[dict]:
    """Given a processes.json (Stage-2 LLM output) + the original scan.json,
    decide which processes deserve recursive Stage-2 + write their scoped
    intermediates.

    For each process that passes `should_recurse`:
      - Write `<intermediate>/<P-id>/scan.json` with the scoped ProjectScan
      - Write `<intermediate>/<P-id>/process-candidates.json` by re-running
        `extract_candidates` against the scoped scan
      - Append a `RECURSE_INTO` event to progress.log

    Returns a list of `{candidate_id, process_id, label, files, lines,
    subsystem_dir, depth}` records describing the subsystems queued for
    LLM dispatch — the orchestrator skill iterates this to dispatch
    hp-ingest-processes for each."""
    from .progress_log import log_event
    from .process_candidates import extract_candidates, write_candidates
    from .scan import write_scan
    from .schema import IRGraph

    cfg = config or RecursionConfig()
    if max_depth_param is not None:
        cfg = RecursionConfig(
            threshold_files=cfg.threshold_files,
            threshold_lines=cfg.threshold_lines,
            max_depth=max_depth_param,
            enabled=cfg.enabled,
        )

    graph = IRGraph.model_validate_json(processes_graph_path.read_text())
    scan = ProjectScan.model_validate_json(scan_path.read_text())

    out: list[dict] = []
    for node in graph.nodes:
        if node.kind.value != "process":
            continue
        ok, reason = should_recurse(node, depth=current_depth, scan=scan, config=cfg)
        log_event(
            intermediate_dir,
            "RECURSE_DECISION",
            stage="2-recurse",
            agent="recursion",
            process=node.id,
            decision="yes" if ok else "no",
            depth=current_depth,
            reason=reason.replace(" ", "_"),
        )
        if not ok:
            continue

        sub_dir = subsystem_dir(intermediate_dir, node.id)
        sub_dir.mkdir(parents=True, exist_ok=True)

        scoped_scan = scope_for_subsystem(scan, node.implemented_by)
        write_scan(scoped_scan, sub_dir / "scan.json")

        scoped_candidates = extract_candidates(scoped_scan)
        write_candidates(scoped_candidates, sub_dir / "process-candidates.json")

        line_total = _total_lines(node.implemented_by, scan)
        log_event(
            intermediate_dir,
            "RECURSE_INTO",
            stage="2-recurse",
            agent="recursion",
            process=node.id,
            files=len(node.implemented_by),
            lines=line_total,
            depth=current_depth + 1,
            sub_dir=str(sub_dir.relative_to(intermediate_dir.parent)),
        )

        out.append({
            "process_id": node.id,
            "label": node.label,
            "files": len(node.implemented_by),
            "lines": line_total,
            "subsystem_dir": str(sub_dir),
            "next_depth": current_depth + 1,
            "scoped_scan": str(sub_dir / "scan.json"),
            "scoped_candidates": str(sub_dir / "process-candidates.json"),
        })

    return out


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def _main(argv: Optional[list[str]] = None) -> int:
    """python -m hp_toolkit.ingest.recursion — recursion-prep step.

    Given a processes.json (Stage-2 LLM output) + scan.json, identify
    which processes meet the recursion threshold + write their scoped
    intermediates. The orchestrator skill calls this between Stage 2
    and the recursive Stage-2 LLM dispatches."""
    import argparse
    import json
    import sys
    from .progress_log import log_done, log_start

    parser = argparse.ArgumentParser(
        prog="hp_recursion",
        description="Hierarchical-ingest recursion prep (H.3 / Branch 3).",
    )
    parser.add_argument("--processes", required=True,
                        help="Path to processes.json (Stage-2 LLM output)")
    parser.add_argument("--scan", required=True,
                        help="Path to scan.json (the scan that produced the candidates)")
    parser.add_argument("--intermediate", required=True,
                        help="Path to the intermediate dir (parent of progress.log)")
    parser.add_argument("--current-depth", type=int, default=1,
                        help="Current recursion depth (1 = top-level Stage 2). "
                             "Increment by 1 per recursive call.")
    parser.add_argument("--threshold-files", type=int, default=30,
                        help="Min files in implemented_by for a process to recurse")
    parser.add_argument("--threshold-lines", type=int, default=3000,
                        help="Min total lines for a process to recurse")
    parser.add_argument("--max-depth", type=int, default=3,
                        help="Hard depth cap (no recursion past this)")
    parser.add_argument("--no-recurse", action="store_true",
                        help="Disable recursion entirely (no subsystem prep written)")
    args = parser.parse_args(argv)

    intermediate_dir = Path(args.intermediate)
    log_start(intermediate_dir, stage="2-recurse", agent="recursion",
              depth=args.current_depth)

    cfg = RecursionConfig(
        threshold_files=args.threshold_files,
        threshold_lines=args.threshold_lines,
        max_depth=args.max_depth,
        enabled=not args.no_recurse,
    )

    subsystems = prepare_subsystem_recursions(
        processes_graph_path=Path(args.processes),
        scan_path=Path(args.scan),
        intermediate_dir=intermediate_dir,
        current_depth=args.current_depth,
        config=cfg,
    )

    log_done(intermediate_dir, stage="2-recurse", agent="recursion",
             depth=args.current_depth,
             subsystems=len(subsystems))

    # Emit JSON to stdout so the orchestrator skill can parse the list
    # of subsystems to dispatch.
    sys.stdout.write(json.dumps({"subsystems": subsystems}, indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(_main())
