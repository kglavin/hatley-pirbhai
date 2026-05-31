#!/usr/bin/env python
"""hp-ingest — brownfield codebase → HP `dictionary.yaml`.

Pipeline stages (matches INGEST_DESIGN.md):
    Stage 0: scan + role-hint per file               (Python; --scan-only)
    Stage 1: boundary candidates → LLM terminators   (script + LLM)
    Stage 2: process candidates → LLM processes      (script + LLM)
    Stage 3+4: state-machine candidates → CSPEC/PSPEC (script + LLM-per-process)
    Stage 5: architecture candidates → LLM modules   (script + LLM)
    Merge:   deterministic IR merge → hp-graph.json  (Python)
    Emit:    IR → dictionary.yaml                    (Python)

Commit 2 ships Stages 0 + the deterministic prep for Stages 1/2/3 (the
candidate JSONs the LLM agents will consume) + the merge_graph script.
LLM dispatch (the `/hp-ingest` orchestrator skill) lands in Commit 3.

Usage:
    # Just the Stage 0 scanner
    uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --scan-only

    # Stage 0 + all the deterministic candidate-prep scripts (no LLM dispatch yet)
    uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> --prep-candidates

Planned (Commit 3):
    uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir>
    # ↑ full pipeline including LLM agent dispatch via /hp-ingest skill

Other planned flags:
    --no-architecture     Skip Stage 5 (architecture model).
    --resume              Resume from existing `intermediate/` if present.
    --incremental         Only re-ingest what changed since the last commit.

See toolkit/INGEST_DESIGN.md for the full design.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hp_toolkit.ingest.boundary_candidates import (
    extract_candidates as extract_boundary_candidates,
    write_candidates as write_boundary_candidates,
)
from hp_toolkit.ingest.process_candidates import (
    extract_candidates as extract_process_candidates,
    write_candidates as write_process_candidates,
)
from hp_toolkit.ingest.scan import scan_codebase, write_scan
from hp_toolkit.ingest.state_machine_detector import (
    extract_candidates as extract_state_machine_candidates,
    write_candidates as write_state_machine_candidates,
)


def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hp-ingest",
        description="Brownfield codebase → HP dictionary.yaml (see INGEST_DESIGN.md).",
    )
    parser.add_argument("codebase", help="Path to the codebase to ingest")
    parser.add_argument("--output", "-o", required=True,
                        help="HP project directory to populate")
    parser.add_argument("--scan-only", action="store_true",
                        help="Run only the Stage-0 scanner")
    parser.add_argument("--prep-candidates", action="store_true",
                        help="Run Stage 0 + all candidate-prep scripts (Stages 1/2/3) — "
                             "produces all the JSON inputs the LLM agents consume, "
                             "without dispatching any LLM calls. Useful for inspecting "
                             "what hp-ingest will hand to the agents.")
    # Planned flags — accepted but require Commit 3.
    parser.add_argument("--no-architecture", action="store_true",
                        help="(Commit 3) skip Stage 5")
    parser.add_argument("--resume", action="store_true",
                        help="(Commit 3+) resume from existing intermediate/")
    parser.add_argument("--incremental", action="store_true",
                        help="(Commit 3+) re-ingest only what changed since last commit")

    args = parser.parse_args(argv)

    codebase = Path(args.codebase).resolve()
    output = Path(args.output).resolve()

    if not codebase.is_dir():
        print(_color(f"ERROR: codebase {codebase} is not a directory", "31"), file=sys.stderr)
        return 2

    output.mkdir(parents=True, exist_ok=True)

    print(_color(f"==> Scanning {codebase}", "1"))
    scan = scan_codebase(codebase)
    print(_color(f"  ✓ {scan.project.name}", "32"))
    if scan.project.git_commit_hash:
        print(f"    commit: {scan.project.git_commit_hash[:12]}")
    print(f"    languages: {', '.join(scan.project.languages) or '(none detected)'}")
    print(f"    frameworks: {', '.join(scan.project.frameworks) or '(none detected)'}")
    print(f"    files scanned: {len(scan.files)}")

    # Role-hint + significance breakdown
    significant = [f for f in scan.files if f.is_significant]
    by_role: dict[str, int] = {}
    for f in significant:
        key = f.hp_role_hint.value if f.hp_role_hint else "(unclassified)"
        by_role[key] = by_role.get(key, 0) + 1
    print(f"    files significant: {len(significant)} / {len(scan.files)}")
    for role, count in sorted(by_role.items(), key=lambda kv: -kv[1]):
        print(f"      {role:18s} {count}")
    print()

    # Write scan.json
    intermediate = output / "intermediate"
    scan_path = intermediate / "scan.json"
    print(_color(f"==> Writing {scan_path.relative_to(output)}", "1"))
    write_scan(scan, scan_path)
    print(_color(f"  wrote {scan_path.name} ({scan_path.stat().st_size} bytes)", "32"))
    print()

    if args.scan_only:
        print(_color("Done (scan-only).", "32"))
        return 0

    if args.prep_candidates or not (args.resume or args.incremental or args.no_architecture):
        # Stage 1 — boundary candidates
        print(_color("==> Stage 1 — boundary candidates", "1"))
        bc = extract_boundary_candidates(scan, codebase)
        bc_path = intermediate / "boundary-candidates.json"
        write_boundary_candidates(bc, bc_path)
        print(_color(f"  wrote {bc_path.name} ({len(bc.boundary_files)} boundary candidates)", "32"))
        for cand in bc.boundary_files[:5]:
            print(f"    {cand.kind_hint or '(no kind)':16s} {cand.path}")
        if len(bc.boundary_files) > 5:
            print(f"    ... and {len(bc.boundary_files) - 5} more")
        print()

        # Stage 2 — process candidates
        print(_color("==> Stage 2 — process candidates", "1"))
        pc = extract_process_candidates(scan)
        pc_path = intermediate / "process-candidates.json"
        write_process_candidates(pc, pc_path)
        print(_color(f"  wrote {pc_path.name} ({len(pc.clusters)} process candidates)", "32"))
        for cand in pc.clusters[:5]:
            mix = " ".join(f"{k}:{v}" for k, v in sorted(cand.role_hint_mix.items()))
            print(f"    {cand.cluster_id:20s} ({len(cand.files)} files; {mix})")
        if len(pc.clusters) > 5:
            print(f"    ... and {len(pc.clusters) - 5} more")
        print()

        # Stage 3 — state-machine candidates
        print(_color("==> Stage 3 — state-machine candidates", "1"))
        sm = extract_state_machine_candidates(scan, codebase)
        sm_path = intermediate / "state-machine-candidates.json"
        write_state_machine_candidates(sm, sm_path)
        print(_color(f"  wrote {sm_path.name} ({len(sm.candidates)} state-machine candidates)", "32"))
        for cand in sm.candidates[:5]:
            print(f"    {cand.owning_file:60s} "
                  f"{len(cand.states_extracted)} states, "
                  f"{len(cand.transitions_extracted)} transitions")
        print()

    if args.prep_candidates:
        print(_color("Done (candidates prepped). LLM dispatch will land in Commit 3 "
                     "via the /hp-ingest skill.", "32"))
        return 0

    print(_color("⚠ LLM agent dispatch + Stage 5 + dictionary.yaml emission not yet "
                 "implemented. Re-run with --prep-candidates or --scan-only, or wait "
                 "for Commit 3.", "33"))
    print(_color("Done.", "32"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
