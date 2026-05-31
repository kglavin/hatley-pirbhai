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
)


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


def render_context(project_dir: Path, project, has_internals: bool) -> None:
    """Render the level-0 Context across all notations + SVGs."""
    ctx_dir = project_dir / "00-context"
    ctx_dir.mkdir(parents=True, exist_ok=True)

    drill_target = "../01-level1/dfd.html" if has_internals else None

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
    html = render_cytoscape.wrap_context_html(project, drill_target=drill_target)
    out = ctx_dir / "context.generated.html"
    out.write_text(html)
    print(f"  wrote {out.name} ({len(html)} bytes)")
    print()


def main(project_dir: Path) -> int:
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

    # Discover structure: does this project have level-1 internal processes?
    has_internals = any(
        e.parent == "sys_root" and e.level == 1
        for e in project.all_entities()
    )

    # Render the Context (always)
    render_context(project_dir, project, has_internals=has_internals)

    # ─── Level-1 DFD (if internal processes exist) ───
    if has_internals:
        render_level1_dfd(project_dir, project)

    # ─── CSPECs (one per process flagged needs_cspec) ───
    cspec_processes = [
        e for e in project.all_entities()
        if e.kind == EntityKind.PROCESS and e.needs_cspec
    ]
    for proc in cspec_processes:
        render_cspec(project_dir, project, proc)

    # ─── PSPECs (one per leaf process that has one declared) ───
    if project.pspecs:
        render_pspecs(project_dir, project)

    # ─── Architecture Model (Stage 5) ───
    if project.architecture_modules:
        render_architecture(project_dir, project)

    # ─── ADRs (Modernization #10) ───
    if project.adrs:
        render_adrs(project_dir, project)

    # ─── Context Map (Modernization #5) ───
    if project.bounded_contexts:
        render_context_map(project_dir, project)

    print(_color(f"Done.", "32"))
    return 0


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


def render_adrs(project_dir: Path, project) -> None:
    """Render each ADR into a sidecar markdown file at adrs/."""
    adr_dir = project_dir / "adrs"
    adr_dir.mkdir(parents=True, exist_ok=True)
    print(_color(f"==> ADRs ({len(project.adrs)})", "1"))
    for adr in project.all_adrs():
        md = render_adr.render_adr_markdown(project, adr)
        out = adr_dir / render_adr.adr_filename(adr.id)
        out.write_text(md)
        print(f"  wrote adrs/{out.name} ({len(md)} bytes)")
    print()


def render_architecture(project_dir: Path, project) -> None:
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
    html = render_cytoscape.wrap_afd_html(project, parent_id=None)
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
        html = render_cytoscape.wrap_aid_html(project, parent_id=None)
        out = arch_dir / "aid.generated.html"
        out.write_text(html)
        print(f"  wrote {out.name} ({len(html)} bytes)")
        print()

    # AMS markdown sidecars
    if project.architecture_module_specs:
        print(_color(f"==> AMS sidecars ({len(project.architecture_module_specs)})", "1"))
        for ams in project.all_architecture_module_specs():
            md = render_arch.render_ams_markdown(project, ams)
            out = specs_dir / f"{render_arch.ams_subdir_name(ams.parent_module)}.md"
            out.write_text(md)
            print(f"  wrote specs/{out.name} ({len(md)} bytes)")
        print()

    # AIS markdown sidecars
    if project.architecture_interconnect_specs:
        print(_color(f"==> AIS sidecars ({len(project.architecture_interconnect_specs)})", "1"))
        for ais in project.all_architecture_interconnect_specs():
            md = render_arch.render_ais_markdown(project, ais)
            out = ic_dir / f"{render_arch.ais_subdir_name(ais.parent_interconnect)}.md"
            out.write_text(md)
            print(f"  wrote specs/interconnects/{out.name} ({len(md)} bytes)")
        print()

    # SLOs project-level summary (modernization #32)
    if project.service_level_objectives:
        print(_color(f"==> SLOs summary ({len(project.service_level_objectives)} SLO(s))", "1"))
        md = render_arch.render_slos_summary(project)
        out = arch_dir / "slos.md"
        out.write_text(md)
        print(f"  wrote {out.name} ({len(md)} bytes)")
        print()


def render_pspecs(project_dir: Path, project) -> None:
    """Render each declared PSPEC into its own markdown sidecar.

    Output: ``01-level1/pspecs/<process-id-short>.md``.
    """
    pspec_dir = project_dir / "01-level1" / "pspecs"
    pspec_dir.mkdir(parents=True, exist_ok=True)

    print(_color(f"==> PSPECs ({len(project.pspecs)})", "1"))
    for ps in project.all_pspecs():
        md = render_pspec.render_pspec_markdown(project, ps)
        out = pspec_dir / f"{render_pspec.pspec_subdir_name(ps.parent_process)}.md"
        out.write_text(md)
        print(f"  wrote {out.name} ({len(md)} bytes)")
    print()


def render_level1_dfd(project_dir: Path, project) -> None:
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
    html = render_cytoscape.wrap_dfd_html(project, parent_id="sys_root")
    out = l1_dir / "dfd.generated.html"
    out.write_text(html)
    print(f"  wrote {out.name} ({len(html)} bytes)")
    print()


def render_cspec(project_dir: Path, project, proc) -> None:
    """Render a CSPEC for one process (needs_cspec=True): Mermaid + D2 + HTML + SVGs."""
    subdir = proc.id.replace("proc_", "").replace("_", "-")
    cspec_dir = project_dir / "01-level1" / "cspecs" / subdir
    cspec_dir.mkdir(parents=True, exist_ok=True)

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
    html = render_cytoscape.wrap_state_machine_html(project, proc.id)
    out = cspec_dir / "cspec.generated.html"
    out.write_text(html)
    print(f"  wrote {out.name} ({len(html)} bytes)")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: render_project.py <project-directory>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1]).resolve()))
