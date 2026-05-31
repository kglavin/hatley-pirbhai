#!/usr/bin/env python
# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

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
import json
import sys
from pathlib import Path
from typing import Optional

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
from hp_toolkit.ingest.architecture_candidates import ArchitectureCandidates
from hp_toolkit.ingest.boundary_candidates import BoundaryCandidates
from hp_toolkit.ingest.docs_walker import DocCorpus, load_corpus, walk_docs, write_corpus
from hp_toolkit.ingest.external_context import ensure_external_context_dir, summarize_presence
from hp_toolkit.ingest.glossary_extractor import GlossaryCandidates, extract as extract_glossary, write_candidates as write_glossary_candidates
from hp_toolkit.ingest.hints import ensure_hints_dir, list_dropped_hints
from hp_toolkit.ingest.process_candidates import ProcessCandidates
from hp_toolkit.ingest.progress_log import log_done, log_skip, log_start
from hp_toolkit.ingest.rationale_sources import RationaleSources, gather as gather_rationale, write_sources as write_rationale_sources
from hp_toolkit.ingest.recipe_parser import RecipeHarvest, gather as gather_recipes, write_harvest as write_recipes
from hp_toolkit.ingest.scan import scan_codebase, write_scan
from hp_toolkit.ingest.testbed_miner import TestbedHarvest, detect_and_mine as detect_testbeds, write_harvest as write_testbeds
from hp_toolkit.ingest.user_docs_gatherer import UserDocsHarvest, gather as gather_user_docs, write_harvest as write_user_docs
from hp_toolkit.ingest.schema import IRGraph, ProjectScan
from hp_toolkit.ingest.significance import SignificanceConfig
from hp_toolkit.ingest.state_machine_detector import (
    StateMachineCandidates,
    extract_candidates as extract_state_machine_candidates,
    write_candidates as write_state_machine_candidates,
)


def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def _try_load(path: Path, model_cls) -> Optional[object]:
    """Resume helper: if `path` exists and parses as `model_cls`, return the
    loaded instance; otherwise return None.

    Used by --resume to detect already-completed stages."""
    if not path.exists():
        return None
    try:
        return model_cls.model_validate(json.loads(path.read_text()))
    except Exception:
        return None


def _print_scan_summary(scan: ProjectScan) -> None:
    print(_color(f"  ✓ {scan.project.name}", "32"))
    if scan.project.git_commit_hash:
        print(f"    commit: {scan.project.git_commit_hash[:12]}")
    print(f"    languages: {', '.join(scan.project.languages) or '(none detected)'}")
    print(f"    frameworks: {', '.join(scan.project.frameworks) or '(none detected)'}")
    print(f"    files scanned: {len(scan.files)}")
    significant = [f for f in scan.files if f.is_significant]
    by_role: dict[str, int] = {}
    for f in significant:
        key = f.hp_role_hint.value if f.hp_role_hint else "(unclassified)"
        by_role[key] = by_role.get(key, 0) + 1
    print(f"    files significant: {len(significant)} / {len(scan.files)}")
    for role, count in sorted(by_role.items(), key=lambda kv: -kv[1]):
        print(f"      {role:18s} {count}")


def _scan_stats(scan: ProjectScan) -> dict[str, int]:
    """Compact stats for the progress log."""
    return {
        "files": len(scan.files),
        "significant": sum(1 for f in scan.files if f.is_significant),
    }


def _announce_file_drops(intermediate: Path, project: Path) -> None:
    """Surface dropped hints + external-context at run start.

    Idempotent visibility — every run, the observer sees what guidance
    + evidence is in flight so they know what's being honored. Quiet
    when nothing has been dropped."""
    hints = list_dropped_hints(intermediate)
    ext = summarize_presence(project)
    ext_present = {k: v for k, v in ext.items() if v > 0}
    if not hints and not ext_present:
        return
    print(_color("==> File drops detected", "1"))
    if hints:
        for stage, path in hints.items():
            print(f"    {_color('hint', '36')}  intermediate/hints/{path.name}  (stage={stage})")
    if ext_present:
        for category, count in ext_present.items():
            print(f"    {_color('ext', '35')}   external-context/{category}/  ({count} file{'s' if count != 1 else ''})")
    print()


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
    parser.add_argument("--max-depth", type=int, default=None,
                        help="Process-candidate clustering: cap cluster key at N path "
                             "components. Useful for monorepos where the natural process "
                             "boundary is `<repo>/<category>/<service>` (depth 3) rather "
                             "than the leaf directory. Default unlimited.")
    parser.add_argument("--min-pure-logic", type=int, default=None,
                        metavar="LINES",
                        help="Minimum line count for a pure-logic file to be considered "
                             "significant. Default 50 — works for small projects (<200 "
                             "files). Tighten to 100–125 for medium projects (200–1000 "
                             "files), 150–250 for acme-cp-scale monorepos (>1000 "
                             "files). Highest-leverage cost lever per INGEST_DESIGN.md > "
                             "Tuning guide.")
    parser.add_argument("--resume", action="store_true",
                        help="Skip stages whose output JSON already exists in intermediate/. "
                             "Per-stage check: scan.json, boundary-candidates.json, "
                             "process-candidates.json, state-machine-candidates.json, "
                             "architecture-candidates.json. Each skip logs to progress.log + "
                             "prints a summary line.")
    parser.add_argument("--incremental", action="store_true",
                        help="(future) re-ingest only what changed since last commit")

    args = parser.parse_args(argv)

    codebase = Path(args.codebase).resolve()
    output = Path(args.output).resolve()

    if not codebase.is_dir():
        print(_color(f"ERROR: codebase {codebase} is not a directory", "31"), file=sys.stderr)
        return 2

    output.mkdir(parents=True, exist_ok=True)

    intermediate = output / "intermediate"
    intermediate.mkdir(parents=True, exist_ok=True)

    # Bootstrap the two file-drop directories (per tuning F.3.a + H.8.b).
    # Idempotent — creates the dir + README stub if absent. We do this every
    # run so the user always has somewhere to drop hints / external context.
    ensure_hints_dir(intermediate)
    ensure_external_context_dir(output)
    _announce_file_drops(intermediate, output)

    # --merge-emit short-circuits: scan + candidate prep already done; just
    # run merge + emit. Resume is implicit here.
    if args.merge_emit:
        return _run_merge_emit(output)

    # ─── Stage 0: scan ─────────────────────────────────────────────
    scan_path = intermediate / "scan.json"
    existing_scan = _try_load(scan_path, ProjectScan) if args.resume else None
    if existing_scan is not None:
        scan = existing_scan  # type: ignore[assignment]
        print(_color(
            f"[resume] skipping Stage 0 — {scan_path.name} present", "36"))
        _print_scan_summary(scan)
        log_skip(intermediate, stage="0", agent="hp-ingest-scan",
                 reason="output_present", **_scan_stats(scan))
    else:
        sig_config = (SignificanceConfig(min_pure_logic_lines=args.min_pure_logic)
                      if args.min_pure_logic is not None else None)
        log_start(intermediate, stage="0", agent="hp-ingest-scan",
                  codebase=str(codebase),
                  min_pure_logic=str(args.min_pure_logic) if args.min_pure_logic else "default")
        print(_color(f"==> Scanning {codebase}", "1"))
        scan = scan_codebase(codebase, significance_config=sig_config)
        _print_scan_summary(scan)
        write_scan(scan, scan_path)
        print(_color(f"  wrote {scan_path.name} ({scan_path.stat().st_size} bytes)", "32"))
        log_done(intermediate, stage="0", agent="hp-ingest-scan",
                 **_scan_stats(scan),
                 frameworks=len(scan.project.frameworks))
    print()

    if args.scan_only:
        print(_color("Done (scan-only).", "32"))
        return 0

    # ─── Stage 0b: documentation corpus ─────────────────────────────
    # Walk doc-like files (READMEs, usage docs, ADRs, glossaries, API
    # specs) once + cache the corpus. Shared infrastructure for the
    # input-expansion extractors (T6 rationale_sources, future T7
    # glossary, T9 user-docs). Cheap pass.
    docs_path = intermediate / "docs-corpus.json"
    existing_docs = _try_load(docs_path, DocCorpus) if args.resume else None
    if existing_docs is not None:
        corpus = existing_docs  # type: ignore[assignment]
        print(_color(f"[resume] skipping Stage 0b — {docs_path.name} present "
                     f"({len(corpus.files)} docs)", "36"))
        log_skip(intermediate, stage="0-docs", agent="docs_walker",
                 reason="output_present", docs=len(corpus.files))
    else:
        log_start(intermediate, stage="0-docs", agent="docs_walker")
        print(_color("==> Stage 0b — documentation corpus", "1"))
        corpus = walk_docs(codebase)
        write_corpus(corpus, docs_path)
        print(_color(f"  wrote {docs_path.name} ({len(corpus.files)} doc files)", "32"))
        log_done(intermediate, stage="0-docs", agent="docs_walker",
                 docs=len(corpus.files))
    print()

    # ─── Stage 0c: glossary candidates ──────────────────────────────
    # Deterministic extraction of project-vocabulary terms from the
    # doc corpus. Output feeds the LLM curator (hp-ingest-glossary
    # skill) which produces the curated 30–60-entry glossary the
    # naming agents consume. Per locked tuning H.4.a.
    gc_path = intermediate / "glossary-candidates.json"
    existing_gc = _try_load(gc_path, GlossaryCandidates) if args.resume else None
    if existing_gc is not None:
        print(_color(f"[resume] skipping Stage 0c — {gc_path.name} present "
                     f"({len(existing_gc.terms)} candidates)", "36"))
        log_skip(intermediate, stage="0-glossary", agent="glossary_extractor",
                 reason="output_present", terms=len(existing_gc.terms))
    else:
        log_start(intermediate, stage="0-glossary", agent="glossary_extractor")
        print(_color("==> Stage 0c — glossary candidates", "1"))
        gc = extract_glossary(corpus, codebase)
        write_glossary_candidates(gc, gc_path)
        print(_color(f"  wrote {gc_path.name} ({len(gc.terms)} candidate terms)", "32"))
        if gc.terms:
            top = ", ".join(t.term for t in gc.terms[:8])
            print(f"    top: {top}")
        log_done(intermediate, stage="0-glossary", agent="glossary_extractor",
                 terms=len(gc.terms))
    print()

    # ─── Stage 0d: user-facing documentation harvest (H.6) ─────────
    # Extracts Usage / Getting Started / Tutorial sections + actor +
    # intent phrases + API specs. The boundary agent reads this to
    # name terminators by role rather than protocol.
    ud_path = intermediate / "user-docs.json"
    existing_ud = _try_load(ud_path, UserDocsHarvest) if args.resume else None
    if existing_ud is not None:
        print(_color(f"[resume] skipping Stage 0d — {ud_path.name} present "
                     f"({len(existing_ud.usage_excerpts)} excerpts)", "36"))
        log_skip(intermediate, stage="0-user-docs", agent="user_docs_gatherer",
                 reason="output_present", excerpts=len(existing_ud.usage_excerpts))
    else:
        log_start(intermediate, stage="0-user-docs", agent="user_docs_gatherer")
        print(_color("==> Stage 0d — user-facing docs harvest", "1"))
        ud = gather_user_docs(corpus, codebase)
        write_user_docs(ud, ud_path)
        print(_color(f"  wrote {ud_path.name} "
                     f"({len(ud.usage_excerpts)} usage excerpts, "
                     f"{len(ud.code_examples)} code examples, "
                     f"{len(ud.api_specs)} API specs, "
                     f"{len(ud.actor_phrases)} actor phrases)", "32"))
        log_done(intermediate, stage="0-user-docs", agent="user_docs_gatherer",
                 excerpts=len(ud.usage_excerpts),
                 examples=len(ud.code_examples),
                 api_specs=len(ud.api_specs))
    print()

    # ─── Stage 0e: testbed detection + mining (H.7) ────────────────
    # Identifies purpose-built testbeds (testbed-style top-level dirs)
    # + mines their scenarios + fixtures + spin-up topology. The
    # boundary / processes / leaf / architect agents all read this as
    # executable-spec evidence.
    tb_path = intermediate / "testbeds.json"
    existing_tb = _try_load(tb_path, TestbedHarvest) if args.resume else None
    if existing_tb is not None:
        print(_color(f"[resume] skipping Stage 0e — {tb_path.name} present "
                     f"({len(existing_tb.testbeds)} testbeds)", "36"))
        log_skip(intermediate, stage="0-testbeds", agent="testbed_miner",
                 reason="output_present", testbeds=len(existing_tb.testbeds))
    else:
        log_start(intermediate, stage="0-testbeds", agent="testbed_miner")
        print(_color("==> Stage 0e — testbed detection + mining", "1"))
        tb = detect_testbeds(codebase)
        write_testbeds(tb, tb_path)
        scenarios = sum(len(t.scenarios) for t in tb.testbeds)
        print(_color(f"  wrote {tb_path.name} "
                     f"({len(tb.testbeds)} testbeds, {scenarios} scenarios)", "32"))
        for t in tb.testbeds[:5]:
            print(f"    {t.directory:30s} score={t.detection_score} scenarios={len(t.scenarios)}")
        log_done(intermediate, stage="0-testbeds", agent="testbed_miner",
                 testbeds=len(tb.testbeds), scenarios=scenarios)
    print()

    # ─── Stage 0f: Make/Justfile recipe parse ──────────────────────
    # Recipes are deployment-recipe artifacts the architect agent
    # reads alongside compose/k8s; run-targets feed the boundary
    # agent's CLI-entry inference.
    rp_path = intermediate / "recipes.json"
    existing_rp = _try_load(rp_path, RecipeHarvest) if args.resume else None
    if existing_rp is not None:
        print(_color(f"[resume] skipping Stage 0f — {rp_path.name} present "
                     f"({len(existing_rp.recipes)} recipes)", "36"))
        log_skip(intermediate, stage="0-recipes", agent="recipe_parser",
                 reason="output_present", recipes=len(existing_rp.recipes))
    else:
        log_start(intermediate, stage="0-recipes", agent="recipe_parser")
        print(_color("==> Stage 0f — Make/Justfile recipe parse", "1"))
        rp = gather_recipes(codebase)
        write_recipes(rp, rp_path)
        from collections import Counter
        by_cat = Counter(r.category for r in rp.recipes)
        cat_summary = ", ".join(f"{k}:{v}" for k, v in by_cat.most_common(5)) or "none"
        print(_color(f"  wrote {rp_path.name} ({len(rp.recipes)} recipes; {cat_summary})", "32"))
        log_done(intermediate, stage="0-recipes", agent="recipe_parser",
                 recipes=len(rp.recipes),
                 **{k: v for k, v in by_cat.items() if v})
    print()

    # The candidate-prep block runs by default. --no-architecture skips
    # Stage 5; --resume short-circuits any stage whose output JSON already
    # exists + parses.
    if args.prep_candidates or not (args.incremental):
        # ─── Stage 1: boundary candidates ───────────────────────
        bc_path = intermediate / "boundary-candidates.json"
        existing_bc = _try_load(bc_path, BoundaryCandidates) if args.resume else None
        if existing_bc is not None:
            print(_color(f"[resume] skipping Stage 1 prep — {bc_path.name} present "
                         f"({len(existing_bc.boundary_files)} candidates)", "36"))
            log_skip(intermediate, stage="1-prep", agent="boundary_candidates",
                     reason="output_present", count=len(existing_bc.boundary_files))
        else:
            log_start(intermediate, stage="1-prep", agent="boundary_candidates")
            print(_color("==> Stage 1 — boundary candidates", "1"))
            bc = extract_boundary_candidates(scan, codebase)
            write_boundary_candidates(bc, bc_path)
            print(_color(f"  wrote {bc_path.name} ({len(bc.boundary_files)} boundary candidates)", "32"))
            for cand in bc.boundary_files[:5]:
                print(f"    {cand.kind_hint or '(no kind)':16s} {cand.path}")
            if len(bc.boundary_files) > 5:
                print(f"    ... and {len(bc.boundary_files) - 5} more")
            log_done(intermediate, stage="1-prep", agent="boundary_candidates",
                     count=len(bc.boundary_files))
        print()

        # ─── Stage 2: process candidates ────────────────────────
        pc_path = intermediate / "process-candidates.json"
        existing_pc = _try_load(pc_path, ProcessCandidates) if args.resume else None
        if existing_pc is not None:
            print(_color(f"[resume] skipping Stage 2 prep — {pc_path.name} present "
                         f"({len(existing_pc.clusters)} candidates)", "36"))
            log_skip(intermediate, stage="2-prep", agent="process_candidates",
                     reason="output_present", count=len(existing_pc.clusters))
        else:
            log_start(intermediate, stage="2-prep", agent="process_candidates",
                      max_depth=str(args.max_depth) if args.max_depth else "unlimited")
            print(_color("==> Stage 2 — process candidates", "1"))
            pc = extract_process_candidates(scan, max_depth=args.max_depth)
            write_process_candidates(pc, pc_path)
            print(_color(f"  wrote {pc_path.name} ({len(pc.clusters)} process candidates)", "32"))
            for cand in pc.clusters[:5]:
                mix = " ".join(f"{k}:{v}" for k, v in sorted(cand.role_hint_mix.items()))
                print(f"    {cand.cluster_id:20s} ({len(cand.files)} files; {mix})")
            if len(pc.clusters) > 5:
                print(f"    ... and {len(pc.clusters) - 5} more")
            log_done(intermediate, stage="2-prep", agent="process_candidates",
                     count=len(pc.clusters))
        print()

        # ─── Stage 3: state-machine candidates ──────────────────
        sm_path = intermediate / "state-machine-candidates.json"
        existing_sm = _try_load(sm_path, StateMachineCandidates) if args.resume else None
        if existing_sm is not None:
            print(_color(f"[resume] skipping Stage 3 prep — {sm_path.name} present "
                         f"({len(existing_sm.candidates)} candidates)", "36"))
            log_skip(intermediate, stage="3-prep", agent="state_machine_detector",
                     reason="output_present", count=len(existing_sm.candidates))
        else:
            log_start(intermediate, stage="3-prep", agent="state_machine_detector")
            print(_color("==> Stage 3 — state-machine candidates", "1"))
            sm = extract_state_machine_candidates(scan, codebase)
            write_state_machine_candidates(sm, sm_path)
            print(_color(f"  wrote {sm_path.name} ({len(sm.candidates)} state-machine candidates)", "32"))
            for cand in sm.candidates[:5]:
                print(f"    {cand.owning_file:60s} "
                      f"{len(cand.states_extracted)} states, "
                      f"{len(cand.transitions_extracted)} transitions")
            log_done(intermediate, stage="3-prep", agent="state_machine_detector",
                     count=len(sm.candidates))
        print()

        # ─── Stage 5: architecture candidates (unless suppressed) ──
        if not args.no_architecture:
            ac_path = intermediate / "architecture-candidates.json"
            existing_ac = _try_load(ac_path, ArchitectureCandidates) if args.resume else None
            if existing_ac is not None:
                print(_color(f"[resume] skipping Stage 5 prep — {ac_path.name} present "
                             f"({len(existing_ac.modules)} module + "
                             f"{len(existing_ac.interconnects)} interconnect candidates)", "36"))
                log_skip(intermediate, stage="5-prep", agent="architecture_candidates",
                         reason="output_present",
                         modules=len(existing_ac.modules),
                         interconnects=len(existing_ac.interconnects))
            else:
                log_start(intermediate, stage="5-prep", agent="architecture_candidates")
                print(_color("==> Stage 5 — architecture candidates", "1"))
                ac = extract_architecture_candidates(scan, codebase)
                write_architecture_candidates(ac, ac_path)
                print(_color(f"  wrote {ac_path.name} "
                             f"({len(ac.modules)} module candidates, "
                             f"{len(ac.interconnects)} interconnect candidates)", "32"))
                for m in ac.modules[:5]:
                    print(f"    module:     {m.kind_hint:16s} {m.name_hint or '(unnamed)':20s} from {m.source_file}")
                for i in ac.interconnects[:3]:
                    print(f"    interconnect: {i.kind_hint:14s} {i.name_hint or '(unnamed)':20s} from {i.source_file}")
                log_done(intermediate, stage="5-prep", agent="architecture_candidates",
                         modules=len(ac.modules),
                         interconnects=len(ac.interconnects))
            print()

            # ─── Stage 5-rationale: per-candidate evidence (H.2.b) ──
            rs_path = intermediate / "rationale-sources.json"
            existing_rs = _try_load(rs_path, RationaleSources) if args.resume else None
            if existing_rs is not None:
                print(_color(f"[resume] skipping Stage 5-rationale — {rs_path.name} present "
                             f"({len(existing_rs.by_candidate)} candidates)", "36"))
                log_skip(intermediate, stage="5-rationale", agent="rationale_sources",
                         reason="output_present", candidates=len(existing_rs.by_candidate))
            else:
                log_start(intermediate, stage="5-rationale", agent="rationale_sources")
                print(_color("==> Stage 5-rationale — per-candidate rationale evidence", "1"))
                # Load candidates from disk (may have been resumed above)
                ac_loaded = _try_load(ac_path, ArchitectureCandidates) or ac
                rs = gather_rationale(ac_loaded, corpus, codebase)
                write_rationale_sources(rs, rs_path)
                total_readmes = sum(len(e.nearby_readmes) for e in rs.by_candidate.values())
                total_headers = sum(len(e.file_headers) for e in rs.by_candidate.values())
                total_infra = sum(len(e.infra_comments) for e in rs.by_candidate.values())
                print(_color(f"  wrote {rs_path.name} "
                             f"({len(rs.by_candidate)} candidates: "
                             f"{total_readmes} READMEs, {total_headers} file headers, "
                             f"{total_infra} infra-comment blocks)", "32"))
                log_done(intermediate, stage="5-rationale", agent="rationale_sources",
                         candidates=len(rs.by_candidate),
                         readmes=total_readmes, headers=total_headers,
                         infra_blocks=total_infra)
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

    log_start(intermediate, stage="merge", agent="merge_graph")
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
            ("warnings", len(report.warnings)),
            ("unrecoverable", len(report.unrecoverable)),
        ]:
            if count:
                print(f"    {label}: {count}")
    log_done(intermediate, stage="merge", agent="merge_graph",
             nodes=len(graph.nodes), edges=len(graph.edges),
             warnings=len(report.warnings),
             unrecoverable=len(report.unrecoverable))
    print()

    log_start(intermediate, stage="emit", agent="emit_dictionary")
    print(_color("==> Emitting dictionary.yaml", "1"))
    dict_path = output / "dictionary.yaml"
    emit_dictionary(graph, dict_path)
    print(_color(f"  wrote {dict_path.name} ({dict_path.stat().st_size} bytes)", "32"))
    log_done(intermediate, stage="emit", agent="emit_dictionary",
             bytes=dict_path.stat().st_size)
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
