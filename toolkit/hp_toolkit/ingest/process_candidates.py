# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Stage 2 candidate extractor — clusters significant non-boundary files
into candidate processes for the LLM to name and classify.

Pure Python, no LLM. Reads `intermediate/scan.json` + (optionally)
`intermediate/boundary-candidates.json`. Groups remaining significant files
by directory proximity + role-hint mix into candidate process clusters.
Emits `intermediate/process-candidates.json`.

The LLM agent (`hp-ingest-processes`) takes these clusters and decides which
are real Stage-2 internal processes, names them, and sets `needs_cspec` on
state-rich ones.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .schema import HpRoleHint, ProjectScan


class ProcessCandidate(BaseModel):
    """One candidate cluster — a directory grouping with role-hint mix +
    aggregate stats the LLM uses to decide whether to promote it to a Stage-2
    process node."""

    cluster_id: str                                       # synthetic short id
    directory: str                                        # cluster root path
    files: list[str] = Field(default_factory=list)
    role_hint_mix: dict[str, int] = Field(default_factory=dict)
    total_lines: int = 0
    has_state_machine: bool = False                       # any state-machine role-hint inside
    has_data_store: bool = False                          # any data-store role-hint inside
    is_boundary_owner: bool = False                       # one of the files was classified boundary


class ProcessCandidates(BaseModel):
    """`intermediate/process-candidates.json` shape."""

    clusters: list[ProcessCandidate] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Clustering
# ─────────────────────────────────────────────────────────────────────

def extract_candidates(
    scan: ProjectScan,
    max_depth: Optional[int] = None,
) -> ProcessCandidates:
    """Cluster significant files by their immediate parent directory.

    First-cut heuristic: parent directory of each file = cluster key. Boundary-
    only clusters are still surfaced (the LLM may decide they don't deserve a
    Stage-2 process node, e.g., because they're pure terminator handlers).

    `max_depth` caps the cluster key at N path components — useful for
    monorepos where the natural process boundary is `<repo>/<category>/<service>`
    (depth 3) rather than the leaf directory. Default `None` = unlimited (original
    behavior).

    Per EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding F: embedded targets get
    two cluster-key adjustments:
    1. Files under `src/modules/<name>/` cluster by `<name>` (PX4 module
       convention — the directory name IS the module name).
    2. FSM-heavy files (state-machine role hint AND ≥ 200 lines) become
       their own per-file cluster — firmware "architecture-in-one-file"
       deserves a process bubble of its own."""
    clusters: dict[str, list[tuple[str, HpRoleHint, int]]] = defaultdict(list)
    for f in scan.files:
        if not f.is_significant:
            continue
        if f.hp_role_hint == HpRoleHint.CONFIG:
            # Config files inform other clusters via cross-references, not
            # by being their own process cluster
            continue
        if f.hp_role_hint == HpRoleHint.INFRA:
            # Infra files inform Stage 5 architect, not Stage 2 processes
            continue

        # Finding F.2: FSM-heavy file gets its own cluster keyed on file path
        if f.hp_role_hint == HpRoleHint.STATE_MACHINE and f.size_lines >= 200:
            cluster_key = f"__fsm__/{f.path}"
        else:
            cluster_key = _cluster_key_for(f.path, max_depth=max_depth)
        clusters[cluster_key].append((f.path, f.hp_role_hint, f.size_lines))

    out: list[ProcessCandidate] = []
    for key, entries in sorted(clusters.items()):
        if not entries:
            continue
        role_mix = Counter(hint.value if hint else "(unclassified)"
                           for _, hint, _ in entries)
        total_lines = sum(line for _, _, line in entries)
        has_state = HpRoleHint.STATE_MACHINE in {hint for _, hint, _ in entries}
        has_store = HpRoleHint.DATA_STORE in {hint for _, hint, _ in entries}
        has_boundary = HpRoleHint.BOUNDARY in {hint for _, hint, _ in entries}
        out.append(ProcessCandidate(
            cluster_id=_cluster_id_for(key),
            directory=key,
            files=sorted(p for p, _, _ in entries),
            role_hint_mix=dict(role_mix),
            total_lines=total_lines,
            has_state_machine=has_state,
            has_data_store=has_store,
            is_boundary_owner=has_boundary,
        ))
    return ProcessCandidates(clusters=out)


def write_candidates(c: ProcessCandidates, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(c.model_dump_json(indent=2))


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

def _cluster_key_for(rel_path: str, max_depth: Optional[int] = None) -> str:
    """Cluster key = immediate parent directory of the file (capped at
    `max_depth` components if set).

    For files at the repo root, the cluster key is the project name placeholder
    `.` so they don't all merge into one. Most real projects have very few
    significant files at the repo root.

    Per EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding F.1: PX4-style module
    structure (`src/modules/<name>/...`, `src/drivers/<name>/...`,
    `src/lib/<name>/...`) collapses to `src/<category>/<name>` regardless
    of depth — every file under one PX4 module becomes the same cluster,
    matching `px4_add_module(MODULE <name>)` convention."""
    p = Path(rel_path)
    parts = p.parts

    # Finding F.1: PX4 module-tree shortcut — cluster at depth 3 when the
    # path starts with src/modules/ / src/drivers/ / src/lib/ / src/examples/.
    if len(parts) >= 3 and parts[0] == "src" and parts[1] in {"modules", "drivers", "lib", "examples"}:
        return "/".join(parts[:3])

    parent = p.parent.as_posix()
    if not parent or parent == ".":
        return "."
    if max_depth is not None:
        partsp = parent.split("/")
        if len(partsp) > max_depth:
            parent = "/".join(partsp[:max_depth])
    return parent


def _cluster_id_for(directory: str) -> str:
    """Synthetic short id derived from the directory path.

    `src/orders/validation` → `orders-validation`. Strips common code-tree
    prefixes (`src/`, `lib/`, etc.) since they don't carry semantic info.

    Per EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding F.2: FSM-heavy
    file-as-cluster gets a `fsm-<filename>` id."""
    if directory == ".":
        return "_root"
    if directory.startswith("__fsm__/"):
        return "fsm-" + Path(directory[len("__fsm__/"):]).stem.replace("_", "-")
    parts = directory.split("/")
    # Strip leading common prefixes
    prefixes_to_skip = {"src", "lib", "internal", "pkg", "cmd", "app"}
    while parts and parts[0] in prefixes_to_skip:
        parts = parts[1:]
    if not parts:
        return directory.replace("/", "-")
    return "-".join(parts)


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def _main(argv: Optional[list[str]] = None) -> int:
    import argparse
    from .progress_log import log_done, log_start
    parser = argparse.ArgumentParser(
        prog="hp_process_candidates",
        description="Cluster significant files into Stage-2 process candidates.",
    )
    parser.add_argument("--scan",   required=True, help="Path to intermediate/scan.json")
    parser.add_argument("--output", required=True, help="Output path for process-candidates.json")
    parser.add_argument("--max-depth", type=int, default=None,
                        help="Cap cluster key at N path components (monorepo helper; default unlimited)")
    args = parser.parse_args(argv)

    intermediate = Path(args.output).parent
    log_start(intermediate, stage="2-prep", agent="process_candidates",
              max_depth=str(args.max_depth) if args.max_depth else "unlimited")

    scan_data = json.loads(Path(args.scan).read_text())
    scan = ProjectScan.model_validate(scan_data)
    candidates = extract_candidates(scan, max_depth=args.max_depth)
    write_candidates(candidates, Path(args.output))
    print(f"wrote {args.output} ({len(candidates.clusters)} process candidates)")

    log_done(intermediate, stage="2-prep", agent="process_candidates",
             count=len(candidates.clusters))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
