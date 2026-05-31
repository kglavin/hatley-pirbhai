#!/usr/bin/env python
"""Generic project renderer — works on any HP toolkit project directory
with a dictionary.yaml.

Discovers what to render from the project's structure:
- Always renders the level-0 Context Diagram (Mermaid + D2 + Cytoscape HTML + 2 SVGs)
- If level-1 entities exist (entities with parent=sys_root, level=1), renders DFD
  *(planned — for now, only Context)*
- For each process with needs_cspec=True, renders the CSPEC
  *(planned — for now, only Context)*

Usage:
    cd toolkit && uv run python scripts/render_project.py <project-dir>

Examples:
    uv run python scripts/render_project.py ../examples/solar
    uv run python scripts/render_project.py ../examples/fishing-rig
"""

from __future__ import annotations

import sys
from pathlib import Path

from hp_toolkit import load, EntityKind
from hp_toolkit.render import (
    mermaid as render_mermaid,
    d2 as render_d2,
    cytoscape as render_cytoscape,
    svg as render_svg,
    pspec as render_pspec,
    architecture as render_arch,
    adr as render_adr,
    index as render_index,
    markdown_artifact as render_md,
    pdf as render_pdf,
)
from hp_toolkit.render.tree import build_project_tree, TreeNode


def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def _try_svg(source: Path, output: Path, kind: str) -> None:
    """Best-effort SVG render; warn on missing binary, fail silent on render error."""
    try:
        if kind == "d2":
            ok = render_svg.render_d2_to_svg(source, output)
        elif kind in ("mermaid", "mmd"):
            ok = render_svg.render_mermaid_to_svg(source, output)
        else:
            raise ValueError(f"unknown SVG renderer kind: {kind!r}")
        if ok:
            print(_color(f"  ✓ SVG: {output.name} ({output.stat().st_size} bytes)", "32"))
        else:
            print(_color(f"  ✗ render failed for {source.name}", "31"))
    except FileNotFoundError as e:
        print(_color(f"  ⚠ SVG skipped: {e}", "33"))


def render_context(project_dir: Path, project, has_internals: bool, *, tree: TreeNode | None = None) -> None:
    """Render the level-0 Context across all notations + SVGs."""
    ctx_dir = project_dir / "00-context"
    ctx_dir.mkdir(parents=True, exist_ok=True)

    drill_target = "../01-level1/dfd.generated.html" if has_internals else None

    print(_color("==> Level-0 Context — Mermaid", "1"))
    src = render_mermaid.render_context_diagram(project)
    out = ctx_dir / "context.generated.mmd"
    out.write_text(src)
    print(f"  wrote {out.name} ({len(src)} bytes)")
    _try_svg(out, ctx_dir / "context.generated-mermaid.svg", "mermaid")
    print()

    print(_color("==> Level-0 Context — D2", "1"))
    src = render_d2.render_context_diagram(project)
    out = ctx_dir / "context.generated.d2"
    out.write_text(src)
    print(f"  wrote {out.name} ({len(src)} bytes)")
    _try_svg(out, ctx_dir / "context.generated-d2.svg", "d2")
    print()

    print(_color("==> Level-0 Context — HTML (Cytoscape)", "1"))
    html = render_cytoscape.wrap_context_html(
        project,
        drill_target=drill_target,
        tree=tree,
        current_path="00-context/context.generated.html",
    )
    out = ctx_dir / "context.generated.html"
    out.write_text(html)
    print(f"  wrote {out.name} ({len(html)} bytes)")
    print()


def main(project_dir: Path, *, pdf_only: bool = False, no_pdf: bool = False) -> int:
    if not project_dir.is_dir():
        print(_color(f"ERROR: {project_dir} is not a directory", "31"), file=sys.stderr)
        return 2

    dictionary_path = project_dir / "dictionary.yaml"
    if not dictionary_path.exists():
        print(_color(f"ERROR: {dictionary_path} does not exist", "31"), file=sys.stderr)
        return 2

    print(_color(f"==> Loading {dictionary_path}", "1"))
    project = load(dictionary_path)
    print(_color(f"  ✓ {project.project} v{project.version}", "32"))
    print()

    if pdf_only:
        # Assume HTML/SVG artifacts already rendered; just regenerate the PDF.
        render_project_pdf(project_dir, project)
        print(_color("Done (PDF only).", "32"))
        return 0

    # Build the project tree once. Both the per-page sidebar and the
    # index page (and the PDF, Commit 3) consume the same tree.
    tree = build_project_tree(project, project_dir)

    # Discover structure: does this project have level-1 internal processes?
    has_internals = any(
        e.parent == "sys_root" and e.level == 1
        for e in project.all_entities()
    )

    # Render the Context (always)
    render_context(project_dir, project, has_internals=has_internals, tree=tree)

    # ─── Level-1 DFD (if internal processes exist) ───
    if has_internals:
        render_level1_dfd(project_dir, project, tree=tree)

    # ─── Level-N DFDs (one per non-leaf process; HIERARCHICAL_INGEST_DESIGN.md) ───
    non_leaf = _non_leaf_processes(project)
    for parent_proc in non_leaf:
        render_leveln_dfd(project_dir, project, parent_proc, tree=tree)

    # ─── CSPECs (one per process flagged needs_cspec) ───
    cspec_processes = [
        e for e in project.all_entities()
        if e.kind == EntityKind.PROCESS and e.needs_cspec
    ]
    for proc in cspec_processes:
        render_cspec(project_dir, project, proc, tree=tree)

    # ─── PSPECs (one per leaf process that has one declared) ───
    if project.pspecs:
        render_pspecs(project_dir, project, tree=tree)

    # ─── Architecture Model (Stage 5) ───
    if project.architecture_modules:
        render_architecture(project_dir, project, tree=tree)

    # ─── ADRs (Modernization #10) ───
    if project.adrs:
        render_adrs(project_dir, project, tree=tree)

    # ─── Context Map (Modernization #5) ───
    if project.bounded_contexts:
        render_context_map(project_dir, project)

    # ─── Runbook .generated.html wrappers ───
    runbook_dir = project_dir / "runbooks"
    if runbook_dir.is_dir() and any(runbook_dir.glob("*.md")):
        render_runbook_htmls(project_dir, tree=tree)

    # ─── Project portal index ───
    render_project_index(project_dir, project)

    # ─── PDF (default: yes; opt out with --no-pdf) ───
    if not no_pdf:
        render_project_pdf(project_dir, project)

    print(_color(f"Done.", "32"))
    return 0


def render_project_pdf(project_dir: Path, project) -> None:
    """Render the single-file portable PDF (Portal — Commit 3)."""
    print(_color("==> Project PDF", "1"))
    out = render_pdf.render_project_pdf(project, project_dir)
    print(f"  wrote {out.name} ({out.stat().st_size} bytes)")
    print()


def render_runbook_htmls(project_dir: Path, *, tree: TreeNode | None = None) -> None:
    """For every runbook .md, emit a sidebar'd .generated.html sibling."""
    if tree is None:
        return
    runbook_dir = project_dir / "runbooks"
    md_files = sorted(runbook_dir.glob("*.md"))
    if not md_files:
        return
    print(_color(f"==> Runbook HTML wrappers ({len(md_files)})", "1"))
    for md_path in md_files:
        md_text = md_path.read_text()
        title = _extract_title(md_text) or md_path.stem.replace("-", " ").title()
        html = render_md.render_markdown_artifact_html(
            md_text=md_text, tree=tree,
            current_path=f"runbooks/{md_path.stem}.generated.html",
            title=title,
        )
        out_html = runbook_dir / f"{md_path.stem}.generated.html"
        out_html.write_text(html)
        print(f"  wrote runbooks/{out_html.name} ({len(html)} bytes)")
    print()


def _extract_title(md_text: str) -> str | None:
    """Pull the first H1 from a markdown document, if any."""
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("# ") and not line.startswith("## "):
            return line[2:].strip()
        if line:
            # First non-empty line is not an H1 — give up
            return None
    return None


def render_project_index(project_dir: Path, project) -> None:
    """Render the project_index.generated.html landing page (Portal — Commit 1)."""
    print(_color("==> Project index (portal landing)", "1"))
    html = render_index.render_project_index_html(project, project_dir)
    out = project_dir / "project_index.generated.html"
    out.write_text(html)
    print(f"  wrote {out.name} ({len(html)} bytes)")
    print()


def render_context_map(project_dir: Path, project) -> None:
    """Render the Context Map (Evans 2003) — bounded contexts + ACLs."""
    print(_color(f"==> Context Map ({len(project.bounded_contexts)} contexts, "
                 f"{len(project.all_translations())} ACL(s))", "1"))

    src = render_mermaid.render_context_map(project)
    out = project_dir / "context-map.generated.mmd"
    out.write_text(src)
    print(f"  wrote {out.name} ({len(src)} bytes)")
    _try_svg(out, project_dir / "context-map.generated-mermaid.svg", "mermaid")

    src = render_d2.render_context_map(project)
    out = project_dir / "context-map.generated.d2"
    out.write_text(src)
    print(f"  wrote {out.name} ({len(src)} bytes)")
    _try_svg(out, project_dir / "context-map.generated-d2.svg", "d2")
    print()


def render_adrs(project_dir: Path, project, *, tree: TreeNode | None = None) -> None:
    """Render each ADR into a sidecar markdown file + sidebar'd HTML at adrs/."""
    adr_dir = project_dir / "adrs"
    adr_dir.mkdir(parents=True, exist_ok=True)
    print(_color(f"==> ADRs ({len(project.adrs)})", "1"))
    for adr in project.all_adrs():
        md = render_adr.render_adr_markdown(project, adr)
        out_md = adr_dir / render_adr.adr_filename(adr.id)
        out_md.write_text(md)
        print(f"  wrote adrs/{out_md.name} ({len(md)} bytes)")

        if tree is not None:
            short = out_md.stem
            html = render_md.render_markdown_artifact_html(
                md_text=md,
                tree=tree,
                current_path=f"adrs/{short}.generated.html",
                title=adr.title,
            )
            out_html = adr_dir / f"{short}.generated.html"
            out_html.write_text(html)
            print(f"  wrote adrs/{out_html.name} ({len(html)} bytes)")
    print()


def render_architecture(project_dir: Path, project, *, tree: TreeNode | None = None) -> None:
    """Render the Stage 5 architecture surface: AFD + AID across all three
    notations, plus AMS + AIS markdown sidecars."""
    arch_dir = project_dir / "architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    specs_dir = arch_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    ic_dir = specs_dir / "interconnects"
    if project.architecture_interconnect_specs:
        ic_dir.mkdir(parents=True, exist_ok=True)

    # AFD — root layer
    print(_color("==> AFD (root) — Mermaid", "1"))
    src = render_mermaid.render_afd(project, parent_id=None)
    out = arch_dir / "afd.generated.mmd"
    out.write_text(src)
    print(f"  wrote {out.name} ({len(src)} bytes)")
    _try_svg(out, arch_dir / "afd.generated-mermaid.svg", "mermaid")
    print()

    print(_color("==> AFD (root) — D2", "1"))
    src = render_d2.render_afd(project, parent_id=None)
    out = arch_dir / "afd.generated.d2"
    out.write_text(src)
    print(f"  wrote {out.name} ({len(src)} bytes)")
    _try_svg(out, arch_dir / "afd.generated-d2.svg", "d2")
    print()

    print(_color("==> AFD (root) — HTML (Cytoscape)", "1"))
    html = render_cytoscape.wrap_afd_html(
        project, parent_id=None,
        tree=tree, current_path="architecture/afd.generated.html",
    )
    out = arch_dir / "afd.generated.html"
    out.write_text(html)
    print(f"  wrote {out.name} ({len(html)} bytes)")
    print()

    # AID — root layer
    if project.architecture_interconnects:
        print(_color("==> AID (root) — Mermaid", "1"))
        src = render_mermaid.render_aid(project, parent_id=None)
        out = arch_dir / "aid.generated.mmd"
        out.write_text(src)
        print(f"  wrote {out.name} ({len(src)} bytes)")
        _try_svg(out, arch_dir / "aid.generated-mermaid.svg", "mermaid")
        print()

        print(_color("==> AID (root) — D2", "1"))
        src = render_d2.render_aid(project, parent_id=None)
        out = arch_dir / "aid.generated.d2"
        out.write_text(src)
        print(f"  wrote {out.name} ({len(src)} bytes)")
        _try_svg(out, arch_dir / "aid.generated-d2.svg", "d2")
        print()

        print(_color("==> AID (root) — HTML (Cytoscape)", "1"))
        html = render_cytoscape.wrap_aid_html(
            project, parent_id=None,
            tree=tree, current_path="architecture/aid.generated.html",
        )
        out = arch_dir / "aid.generated.html"
        out.write_text(html)
        print(f"  wrote {out.name} ({len(html)} bytes)")
        print()

    # AMS markdown sidecars + .generated.html wrappers
    if project.architecture_module_specs:
        print(_color(f"==> AMS sidecars ({len(project.architecture_module_specs)})", "1"))
        for ams in project.all_architecture_module_specs():
            short = render_arch.ams_subdir_name(ams.parent_module)
            md = render_arch.render_ams_markdown(project, ams)
            out_md = specs_dir / f"{short}.md"
            out_md.write_text(md)
            print(f"  wrote specs/{out_md.name} ({len(md)} bytes)")

            if tree is not None:
                m = project.architecture_modules.get(ams.parent_module)
                title = f"{m.name} — AMS" if m else f"{ams.parent_module} — AMS"
                html = render_md.render_markdown_artifact_html(
                    md_text=md, tree=tree,
                    current_path=f"architecture/specs/{short}.generated.html",
                    title=title,
                )
                out_html = specs_dir / f"{short}.generated.html"
                out_html.write_text(html)
                print(f"  wrote specs/{out_html.name} ({len(html)} bytes)")
        print()

    # AIS markdown sidecars + .generated.html wrappers
    if project.architecture_interconnect_specs:
        print(_color(f"==> AIS sidecars ({len(project.architecture_interconnect_specs)})", "1"))
        for ais in project.all_architecture_interconnect_specs():
            short = render_arch.ais_subdir_name(ais.parent_interconnect)
            md = render_arch.render_ais_markdown(project, ais)
            out_md = ic_dir / f"{short}.md"
            out_md.write_text(md)
            print(f"  wrote specs/interconnects/{out_md.name} ({len(md)} bytes)")

            if tree is not None:
                ic = project.architecture_interconnects.get(ais.parent_interconnect)
                title = f"{ic.name} — AIS" if ic else f"{ais.parent_interconnect} — AIS"
                html = render_md.render_markdown_artifact_html(
                    md_text=md, tree=tree,
                    current_path=f"architecture/specs/interconnects/{short}.generated.html",
                    title=title,
                )
                out_html = ic_dir / f"{short}.generated.html"
                out_html.write_text(html)
                print(f"  wrote specs/interconnects/{out_html.name} ({len(html)} bytes)")
        print()

    # SLOs project-level summary (modernization #32)
    if project.service_level_objectives:
        print(_color(f"==> SLOs summary ({len(project.service_level_objectives)} SLO(s))", "1"))
        md = render_arch.render_slos_summary(project)
        out_md = arch_dir / "slos.md"
        out_md.write_text(md)
        print(f"  wrote {out_md.name} ({len(md)} bytes)")

        if tree is not None:
            html = render_md.render_markdown_artifact_html(
                md_text=md, tree=tree,
                current_path="architecture/slos.generated.html",
                title=f"{project.project} — SLOs Summary",
            )
            out_html = arch_dir / "slos.generated.html"
            out_html.write_text(html)
            print(f"  wrote {out_html.name} ({len(html)} bytes)")
        print()


def render_pspecs(project_dir: Path, project, *, tree: TreeNode | None = None) -> None:
    """Render each declared PSPEC into its own markdown sidecar + sidebar'd HTML.

    Outputs: ``01-level1/pspecs/<short>.md`` + ``01-level1/pspecs/<short>.generated.html``.
    """
    pspec_dir = project_dir / "01-level1" / "pspecs"
    pspec_dir.mkdir(parents=True, exist_ok=True)

    print(_color(f"==> PSPECs ({len(project.pspecs)})", "1"))
    for ps in project.all_pspecs():
        short = render_pspec.pspec_subdir_name(ps.parent_process)
        md = render_pspec.render_pspec_markdown(project, ps)
        out_md = pspec_dir / f"{short}.md"
        out_md.write_text(md)
        print(f"  wrote {out_md.name} ({len(md)} bytes)")

        if tree is not None:
            proc = project.entities.get(ps.parent_process)
            title = f"{proc.label} — PSPEC" if proc else f"{ps.parent_process} — PSPEC"
            html = render_md.render_markdown_artifact_html(
                md_text=md,
                tree=tree,
                current_path=f"01-level1/pspecs/{short}.generated.html",
                title=title,
            )
            out_html = pspec_dir / f"{short}.generated.html"
            out_html.write_text(html)
            print(f"  wrote {out_html.name} ({len(html)} bytes)")
    print()


def render_level1_dfd(project_dir: Path, project, *, tree: TreeNode | None = None) -> None:
    """Render the level-1 DFD across all notations + SVGs."""
    l1_dir = project_dir / "01-level1"
    l1_dir.mkdir(parents=True, exist_ok=True)

    print(_color("==> Level-1 DFD — Mermaid", "1"))
    src = render_mermaid.render_dfd(project, parent_id="sys_root")
    out = l1_dir / "dfd.generated.mmd"
    out.write_text(src)
    print(f"  wrote {out.name} ({len(src)} bytes)")
    _try_svg(out, l1_dir / "dfd.generated-mermaid.svg", "mermaid")
    print()

    print(_color("==> Level-1 DFD — D2", "1"))
    src = render_d2.render_dfd(project, parent_id="sys_root")
    out = l1_dir / "dfd.generated.d2"
    out.write_text(src)
    print(f"  wrote {out.name} ({len(src)} bytes)")
    _try_svg(out, l1_dir / "dfd.generated-d2.svg", "d2")
    print()

    print(_color("==> Level-1 DFD — HTML (Cytoscape)", "1"))
    html = render_cytoscape.wrap_dfd_html(
        project,
        parent_id="sys_root",
        tree=tree,
        current_path="01-level1/dfd.generated.html",
    )
    out = l1_dir / "dfd.generated.html"
    out.write_text(html)
    print(f"  wrote {out.name} ({len(html)} bytes)")
    print()


def _non_leaf_processes(project) -> list:
    """Per HIERARCHICAL_INGEST_DESIGN.md: a non-leaf process is one with
    child PROCESSES (state children don't count). Returned in document
    order so the per-parent DFDs render predictably."""
    parents: set[str] = set()
    for e in project.all_entities():
        if e.kind == EntityKind.PROCESS and e.parent and e.parent != "sys_root":
            # e is a sub-process; e.parent is the non-leaf
            target = project.entities.get(e.parent)
            if target and target.kind == EntityKind.PROCESS:
                parents.add(target.id)
    return [project.entity(pid) for pid in parents]


def render_leveln_dfd(project_dir: Path, project, parent_proc, *, tree: TreeNode | None = None) -> None:
    """Render a level-N DFD for one non-leaf process (HIERARCHICAL_INGEST_DESIGN.md).

    Output: <project>/02-decomp/<proc-slug>/dfd.generated.{mmd,d2,html} +
    accompanying SVGs.

    The underlying mermaid/d2/cytoscape render_dfd functions already accept
    `parent_id` + derive child + boundary levels from parent.level — this
    function is a thin wrapper that picks the output path + invokes the
    three notations per parent."""
    slug = parent_proc.id.replace("proc_", "").replace("_", "-")
    out_dir = project_dir / "02-decomp" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    current_path = f"02-decomp/{slug}/dfd.generated.html"

    print(_color(f"==> Level-N DFD for {parent_proc.label} — Mermaid", "1"))
    src = render_mermaid.render_dfd(project, parent_id=parent_proc.id)
    out = out_dir / "dfd.generated.mmd"
    out.write_text(src)
    print(f"  wrote {out.relative_to(project_dir)} ({len(src)} bytes)")
    _try_svg(out, out_dir / "dfd.generated-mermaid.svg", "mermaid")
    print()

    print(_color(f"==> Level-N DFD for {parent_proc.label} — D2", "1"))
    src = render_d2.render_dfd(project, parent_id=parent_proc.id)
    out = out_dir / "dfd.generated.d2"
    out.write_text(src)
    print(f"  wrote {out.relative_to(project_dir)} ({len(src)} bytes)")
    _try_svg(out, out_dir / "dfd.generated-d2.svg", "d2")
    print()

    print(_color(f"==> Level-N DFD for {parent_proc.label} — HTML (Cytoscape)", "1"))
    html = render_cytoscape.wrap_dfd_html(
        project,
        parent_id=parent_proc.id,
        tree=tree,
        current_path=current_path,
    )
    out = out_dir / "dfd.generated.html"
    out.write_text(html)
    print(f"  wrote {out.relative_to(project_dir)} ({len(html)} bytes)")
    print()


def render_cspec(project_dir: Path, project, proc, *, tree: TreeNode | None = None) -> None:
    """Render a CSPEC for one process (needs_cspec=True): Mermaid + D2 + HTML + SVGs."""
    subdir = proc.id.replace("proc_", "").replace("_", "-")
    cspec_dir = project_dir / "01-level1" / "cspecs" / subdir
    cspec_dir.mkdir(parents=True, exist_ok=True)
    current_path = f"01-level1/cspecs/{subdir}/cspec.generated.html"

    print(_color(f"==> CSPEC for {proc.label} — Mermaid", "1"))
    src = render_mermaid.render_state_machine(project, proc.id)
    out = cspec_dir / "cspec.generated.mmd"
    out.write_text(src)
    print(f"  wrote {out.name} ({len(src)} bytes)")
    _try_svg(out, cspec_dir / "cspec.generated-mermaid.svg", "mermaid")
    print()

    print(_color(f"==> CSPEC for {proc.label} — D2", "1"))
    src = render_d2.render_state_machine(project, proc.id)
    out = cspec_dir / "cspec.generated.d2"
    out.write_text(src)
    print(f"  wrote {out.name} ({len(src)} bytes)")
    _try_svg(out, cspec_dir / "cspec.generated-d2.svg", "d2")
    print()

    print(_color(f"==> CSPEC for {proc.label} — HTML (Cytoscape)", "1"))
    html = render_cytoscape.wrap_state_machine_html(
        project, proc.id, tree=tree, current_path=current_path,
    )
    out = cspec_dir / "cspec.generated.html"
    out.write_text(html)
    print(f"  wrote {out.name} ({len(html)} bytes)")
    print()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = {a for a in sys.argv[1:] if a.startswith("-")}
    if not args:
        print("usage: render_project.py <project-directory> [--no-pdf] [--pdf-only]",
              file=sys.stderr)
        sys.exit(2)
    sys.exit(main(
        Path(args[0]).resolve(),
        pdf_only="--pdf-only" in flags,
        no_pdf="--no-pdf" in flags,
    ))
