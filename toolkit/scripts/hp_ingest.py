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

from hp_toolkit.ingest.architecture_candidates import (
    extract_candidates as extract_architecture_candidates,
    write_candidates as write_architecture_candidates,
)
from hp_toolkit.ingest.boundary_candidates import (
    extract_candidates as extract_boundary_candidates,
    write_candidates as write_boundary_candidates,
)
from hp_toolkit.ingest.emit_dictionary import emit_dictionary
from hp_toolkit.ingest.merge_graph import merge_intermediates, write_graph, write_report
from hp_toolkit.ingest.process_candidates import (
    extract_candidates as extract_process_candidates,
    write_candidates as write_process_candidates,
)
from hp_toolkit.ingest.scan import scan_codebase, write_scan
from hp_toolkit.ingest.schema import IRGraph
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
                        help="Run Stage 0 + all candidate-prep scripts (Stages 1/2/3/5) — "
                             "produces all the JSON inputs the LLM agents consume, "
                             "without dispatching any LLM calls. Useful for inspecting "
                             "what hp-ingest will hand to the agents.")
    parser.add_argument("--merge-emit", action="store_true",
                        help="After LLM agents have written their intermediates, run the "
                             "deterministic merge + emit dictionary.yaml. Useful for "
                             "post-agent dry-run or manual re-emit.")
    parser.add_argument("--no-architecture", action="store_true",
                        help="Skip Stage 5 (architecture model) in prep + emit.")
    parser.add_argument("--resume", action="store_true",
                        help="(future) resume from existing intermediate/")
    parser.add_argument("--incremental", action="store_true",
                        help="(future) re-ingest only what changed since last commit")

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

    if args.merge_emit:
        # Skip scan + candidate prep; assume agents have written their
        # intermediates and just run merge + emit.
        return _run_merge_emit(output)

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

        # Stage 5 — architecture candidates (unless suppressed)
        if not args.no_architecture:
            print(_color("==> Stage 5 — architecture candidates", "1"))
            ac = extract_architecture_candidates(scan, codebase)
            ac_path = intermediate / "architecture-candidates.json"
            write_architecture_candidates(ac, ac_path)
            print(_color(f"  wrote {ac_path.name} "
                         f"({len(ac.modules)} module candidates, "
                         f"{len(ac.interconnects)} interconnect candidates)", "32"))
            for m in ac.modules[:5]:
                print(f"    module:     {m.kind_hint:16s} {m.name_hint or '(unnamed)':20s} from {m.source_file}")
            for i in ac.interconnects[:3]:
                print(f"    interconnect: {i.kind_hint:14s} {i.name_hint or '(unnamed)':20s} from {i.source_file}")
            print()

    if args.prep_candidates:
        print(_color("Done (candidates prepped). Dispatch the /hp-ingest skill in Claude "
                     "Code to run the LLM agents (boundary, processes, leaf×N, architect, "
                     "review) → dictionary.yaml.", "32"))
        return 0

    print(_color("LLM dispatch happens via the /hp-ingest skill in Claude Code — this "
                 "Python CLI only handles deterministic prep + merge + emit.", "33"))
    print(_color("Re-run with --prep-candidates to prep, or --merge-emit after agents "
                 "have written their intermediates.", "33"))
    print(_color("Done.", "32"))
    return 0


def _run_merge_emit(output: Path) -> int:
    """Deterministic post-agent steps: merge intermediates → IR → dictionary.yaml.

    Assumes the LLM agents (boundary, processes, leaf-*, architect) have
    already written their JSON intermediates. Runs the merge, validates,
    writes the merge report, and emits dictionary.yaml.
    """
    intermediate = output / "intermediate"
    if not (intermediate / "scan.json").exists():
        print(_color(f"ERROR: {intermediate/'scan.json'} not found — run --prep-candidates first",
                     "31"), file=sys.stderr)
        return 2

    print(_color("==> Merging IR intermediates", "1"))
    graph, report = merge_intermediates(intermediate)
    graph_path = intermediate / "hp-graph.json"
    write_graph(graph, graph_path)
    report_path = intermediate / "merge-report.txt"
    write_report(report, report_path)
    print(_color(f"  wrote hp-graph.json ({len(graph.nodes)} nodes, {len(graph.edges)} edges)", "32"))
    if not report.is_clean():
        print(_color(f"  ⚠ merge report has issues — see {report_path.name}", "33"))
        # Print a brief summary
        for label, count in [
            ("normalizations", len(report.normalizations)),
            ("duplicates", len(report.duplicates)),
            ("dropped edges", len(report.dropped_edges)),
            ("unrecoverable", len(report.unrecoverable)),
        ]:
            if count:
                print(f"    {label}: {count}")
    print()

    print(_color("==> Emitting dictionary.yaml", "1"))
    dict_path = output / "dictionary.yaml"
    emit_dictionary(graph, dict_path)
    print(_color(f"  wrote {dict_path.name} ({dict_path.stat().st_size} bytes)", "32"))
    print()

    if report.unrecoverable:
        print(_color("⚠ Unrecoverable merge issues remain — dispatch /hp-ingest-review "
                     "to repair them before relying on the emitted dictionary.", "33"))
    else:
        print(_color("Next: run `uv run python -m hp_toolkit.validate "
                     f"{dict_path}` to check the emitted dictionary.", "36"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
