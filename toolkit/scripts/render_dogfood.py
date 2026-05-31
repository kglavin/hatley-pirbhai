#!/usr/bin/env python
"""Regenerate the solar dogfood diagrams from the dictionary.

Currently renders level-0 only (Mermaid + D2). Writes generated sources
to *.generated.* sidecars next to the hand-written originals so the diff
is visible without overwriting.

Usage:
    cd toolkit && uv run python scripts/render_dogfood.py
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

from hp_toolkit import load
from hp_toolkit.render import mermaid as render_mermaid
from hp_toolkit.render import d2 as render_d2
from hp_toolkit.render import cytoscape as render_cytoscape
from hp_toolkit.render import svg as render_svg


def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def _extract_mermaid_block(md_text: str) -> str | None:
    """Pull the first ```mermaid ... ``` block out of a markdown file."""
    m = re.search(r"```mermaid\n(.*?)\n```", md_text, re.DOTALL)
    return m.group(1) + "\n" if m else None


def _diff(a: str, b: str, label_a: str, label_b: str) -> str:
    return "".join(difflib.unified_diff(
        a.splitlines(keepends=True),
        b.splitlines(keepends=True),
        fromfile=label_a,
        tofile=label_b,
    ))


def _try_svg(source: Path, output: Path, kind: str) -> None:
    """Render source → SVG via the right binary. Best-effort; warn on
    failure but don't abort."""
    try:
        if kind == "d2":
            ok = render_svg.render_d2_to_svg(source, output)
        elif kind in ("mermaid", "mmd"):
            ok = render_svg.render_mermaid_to_svg(source, output)
        else:
            raise ValueError(f"unknown SVG renderer kind: {kind!r}")
        if ok:
            size = output.stat().st_size
            print(_color(f"  ✓ rendered SVG: {output.name} ({size} bytes)", "32"))
        else:
            print(_color(f"  ✗ render failed for {source.name}", "31"))
    except FileNotFoundError as e:
        print(_color(f"  ⚠ SVG skipped: {e}", "33"))


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent.parent
    dict_path = repo_root / "examples" / "solar" / "dictionary.yaml"
    ctx_dir = repo_root / "examples" / "solar" / "00-context"

    print(_color(f"==> Loading dictionary: {dict_path}", "1"))
    project = load(dict_path)
    print(_color("  ✓ loaded", "32"))
    print()

    # ─── Mermaid (level-0 context) ───
    print(_color("==> Rendering level-0 context — Mermaid", "1"))
    gen_mermaid = render_mermaid.render_context_diagram(project)

    out_mermaid = ctx_dir / "context.generated.mmd"
    out_mermaid.write_text(gen_mermaid)
    print(f"  wrote {out_mermaid.relative_to(repo_root)} ({len(gen_mermaid)} bytes)")
    _try_svg(out_mermaid, ctx_dir / "context.generated-mermaid.svg", "mermaid")

    # Compare to the block in the hand-written context.md
    hand_md = (ctx_dir / "context.md").read_text()
    hand_mermaid = _extract_mermaid_block(hand_md)
    if hand_mermaid:
        if hand_mermaid.strip() == gen_mermaid.strip():
            print(_color("  ✓ matches hand-written context.md mermaid block", "32"))
        else:
            print(_color("  ≠ differs from hand-written (see diff below)", "33"))
            d = _diff(hand_mermaid, gen_mermaid,
                      "hand-written (context.md block)", "generated")
            for line in d.splitlines():
                if line.startswith("+"):
                    print(_color(line, "32"))
                elif line.startswith("-"):
                    print(_color(line, "31"))
                else:
                    print(line)
    print()

    # ─── D2 (level-0 context) ───
    print(_color("==> Rendering level-0 context — D2", "1"))
    gen_d2 = render_d2.render_context_diagram(project)

    out_d2 = ctx_dir / "context.generated.d2"
    out_d2.write_text(gen_d2)
    print(f"  wrote {out_d2.relative_to(repo_root)} ({len(gen_d2)} bytes)")
    _try_svg(out_d2, ctx_dir / "context.generated-d2.svg", "d2")

    hand_d2 = (ctx_dir / "context.d2").read_text()
    if hand_d2.strip() == gen_d2.strip():
        print(_color("  ✓ matches hand-written context.d2", "32"))
    else:
        # Compare ignoring leading comments + blank lines
        def _normalize(s: str) -> str:
            keep = [ln for ln in s.splitlines()
                    if ln.strip() and not ln.strip().startswith("#")]
            return "\n".join(keep)

        if _normalize(hand_d2) == _normalize(gen_d2):
            print(_color("  ✓ matches hand-written context.d2 (ignoring comments/blanks)", "32"))
        else:
            print(_color("  ≠ differs from hand-written (see diff below)", "33"))
            d = _diff(hand_d2, gen_d2,
                      "hand-written context.d2", "generated")
            for line in d.splitlines()[:50]:  # cap for noise
                if line.startswith("+"):
                    print(_color(line, "32"))
                elif line.startswith("-"):
                    print(_color(line, "31"))
                else:
                    print(line)
            print("  (diff truncated)")
    print()

    # ─── Cytoscape HTML (level-0 Context) ───
    print(_color("==> Rendering level-0 context — HTML (Cytoscape)", "1"))
    gen_ctx_elements = render_cytoscape.render_context_elements(project)
    gen_ctx_html = render_cytoscape.wrap_context_html(project, gen_ctx_elements)

    out_ctx_html = ctx_dir / "context.generated.html"
    out_ctx_html.write_text(gen_ctx_html)
    print(f"  wrote {out_ctx_html.relative_to(repo_root)} ({len(gen_ctx_html)} bytes)")
    print(f"  elements: {len(gen_ctx_elements)}  (nodes + edges)")
    print(f"  hand-written context.html exists; the generated version is a sidecar.")
    print(f"  open both in a browser to compare interactivity.")
    print()

    # ─── Mermaid (level-1 DFD) ───
    l1_dir = repo_root / "examples" / "solar" / "01-level1"
    print(_color("==> Rendering level-1 DFD — Mermaid", "1"))
    gen_l1_mermaid = render_mermaid.render_dfd(project, parent_id="sys_root")

    out_l1_mermaid = l1_dir / "dfd.generated.mmd"
    out_l1_mermaid.write_text(gen_l1_mermaid)
    print(f"  wrote {out_l1_mermaid.relative_to(repo_root)} ({len(gen_l1_mermaid)} bytes)")
    _try_svg(out_l1_mermaid, l1_dir / "dfd.generated-mermaid.svg", "mermaid")

    hand_l1_md = (l1_dir / "dfd.md").read_text()
    hand_l1_mermaid = _extract_mermaid_block(hand_l1_md)
    if hand_l1_mermaid:
        if hand_l1_mermaid.strip() == gen_l1_mermaid.strip():
            print(_color("  ✓ matches hand-written dfd.md mermaid block", "32"))
        else:
            print(_color("  ≠ differs from hand-written (see diff below)", "33"))
            d = _diff(hand_l1_mermaid, gen_l1_mermaid,
                      "hand-written (dfd.md block)", "generated")
            for line in d.splitlines()[:80]:
                if line.startswith("+"):
                    print(_color(line, "32"))
                elif line.startswith("-"):
                    print(_color(line, "31"))
                else:
                    print(line)
    print()

    # ─── D2 (level-1 DFD) ───
    print(_color("==> Rendering level-1 DFD — D2", "1"))
    gen_l1_d2 = render_d2.render_dfd(project, parent_id="sys_root")

    out_l1_d2 = l1_dir / "dfd.generated.d2"
    out_l1_d2.write_text(gen_l1_d2)
    print(f"  wrote {out_l1_d2.relative_to(repo_root)} ({len(gen_l1_d2)} bytes)")
    _try_svg(out_l1_d2, l1_dir / "dfd.generated-d2.svg", "d2")

    hand_l1_d2 = (l1_dir / "dfd.d2").read_text()
    if hand_l1_d2.strip() == gen_l1_d2.strip():
        print(_color("  ✓ matches hand-written dfd.d2", "32"))
    else:
        def _normalize(s: str) -> str:
            keep = [ln for ln in s.splitlines()
                    if ln.strip() and not ln.strip().startswith("#")]
            return "\n".join(keep)
        if _normalize(hand_l1_d2) == _normalize(gen_l1_d2):
            print(_color("  ✓ matches hand-written dfd.d2 (ignoring comments/blanks)", "32"))
        else:
            print(_color("  ≠ differs from hand-written (see diff below)", "33"))
            d = _diff(hand_l1_d2, gen_l1_d2,
                      "hand-written dfd.d2", "generated")
            for line in d.splitlines()[:80]:
                if line.startswith("+"):
                    print(_color(line, "32"))
                elif line.startswith("-"):
                    print(_color(line, "31"))
                else:
                    print(line)
            print("  (diff truncated)")
    print()

    # ─── Mermaid (CSPEC — Energy Manager state machine) ───
    cspec_dir = repo_root / "examples" / "solar" / "01-level1" / "cspecs" / "energy-manager"
    print(_color("==> Rendering Energy Manager CSPEC — Mermaid", "1"))
    gen_cspec_mermaid = render_mermaid.render_state_machine(
        project, parent_machine_id="proc_compute_balance"
    )
    out_cspec_mermaid = cspec_dir / "cspec.generated.mmd"
    out_cspec_mermaid.write_text(gen_cspec_mermaid)
    print(f"  wrote {out_cspec_mermaid.relative_to(repo_root)} ({len(gen_cspec_mermaid)} bytes)")
    _try_svg(out_cspec_mermaid, cspec_dir / "cspec.generated-mermaid.svg", "mermaid")

    # Hand-written is in cspec.md (Mermaid block) and proposal-states.mmd
    hand_cspec_md = (cspec_dir / "cspec.md").read_text()
    hand_cspec_mermaid = _extract_mermaid_block(hand_cspec_md)
    if hand_cspec_mermaid:
        if hand_cspec_mermaid.strip() == gen_cspec_mermaid.strip():
            print(_color("  ✓ matches hand-written cspec.md mermaid block", "32"))
        else:
            print(_color("  ≠ differs from hand-written (see diff below)", "33"))
            d = _diff(hand_cspec_mermaid, gen_cspec_mermaid,
                      "hand-written (cspec.md block)", "generated")
            for line in d.splitlines()[:80]:
                if line.startswith("+"):
                    print(_color(line, "32"))
                elif line.startswith("-"):
                    print(_color(line, "31"))
                else:
                    print(line)
            print("  (diff truncated if long)")
    print()

    # ─── D2 (CSPEC) ───
    print(_color("==> Rendering Energy Manager CSPEC — D2", "1"))
    gen_cspec_d2 = render_d2.render_state_machine(
        project, parent_machine_id="proc_compute_balance"
    )
    out_cspec_d2 = cspec_dir / "cspec.generated.d2"
    out_cspec_d2.write_text(gen_cspec_d2)
    print(f"  wrote {out_cspec_d2.relative_to(repo_root)} ({len(gen_cspec_d2)} bytes)")
    _try_svg(out_cspec_d2, cspec_dir / "cspec.generated-d2.svg", "d2")

    hand_cspec_d2 = (cspec_dir / "cspec.d2").read_text()
    if hand_cspec_d2.strip() == gen_cspec_d2.strip():
        print(_color("  ✓ matches hand-written cspec.d2", "32"))
    else:
        def _normalize(s: str) -> str:
            keep = [ln for ln in s.splitlines()
                    if ln.strip() and not ln.strip().startswith("#")]
            return "\n".join(keep)
        if _normalize(hand_cspec_d2) == _normalize(gen_cspec_d2):
            print(_color("  ✓ matches hand-written cspec.d2 (ignoring comments/blanks)", "32"))
        else:
            print(_color("  ≠ differs from hand-written (see diff below)", "33"))
            d = _diff(hand_cspec_d2, gen_cspec_d2,
                      "hand-written cspec.d2", "generated")
            for line in d.splitlines()[:80]:
                if line.startswith("+"):
                    print(_color(line, "32"))
                elif line.startswith("-"):
                    print(_color(line, "31"))
                else:
                    print(line)
            print("  (diff truncated)")
    print()

    print(_color("Done. See *.generated.* files for the renderer output.", "32"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
