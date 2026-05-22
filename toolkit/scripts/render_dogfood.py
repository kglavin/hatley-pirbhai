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

    print(_color("Done. See *.generated.* files for the renderer output.", "32"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
