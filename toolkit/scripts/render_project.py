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

    # Level-1 DFD and CSPECs would be rendered here if present.
    # For now they remain handled by the solar-specific render_dogfood.py.
    if has_internals:
        print(_color(
            "  ℹ project has level-1 internals; DFD + CSPEC rendering "
            "is not yet generic — use render_dogfood.py for solar.",
            "36"
        ))

    print(_color(f"Done. See *.generated.* files in {project_dir / '00-context'}/", "32"))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: render_project.py <project-directory>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1]).resolve()))
