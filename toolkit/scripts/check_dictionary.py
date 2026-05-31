#!/usr/bin/env python
"""Sanity script — load the solar dogfood dictionary, summarize, and run
light cross-reference checks. Validates that the Python model can read
the dictionary.yaml we've been writing by hand.

Usage:
    cd toolkit && uv run python scripts/check_dictionary.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from hp_toolkit import load


def color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def main(dict_path: Path) -> int:
    print(color(f"==> Loading {dict_path}", "1"))
    project = load(dict_path)
    print(color("  ✓ loaded and validated", "32"))
    print()

    print(color("==> Project metadata", "1"))
    print(f"  name:         {project.project}")
    print(f"  version:      {project.version}")
    print(f"  last_updated: {project.last_updated}")
    print()

    print(color("==> Entities", "1"))
    print(f"  total: {len(project.entities)}")
    kinds = Counter(e.kind.value for e in project.all_entities())
    for kind, n in sorted(kinds.items()):
        print(f"    {kind:18s} {n}")
    print()

    levels = sorted({e.level for e in project.all_entities()})
    print(color("==> Levels present", "1"))
    for level in levels:
        n = sum(1 for e in project.all_entities() if e.level == level)
        print(f"  level {level}: {n} entities")
    print()

    print(color("==> Flows", "1"))
    print(f"  total: {len(project.flows)}")
    flow_kinds = Counter(f.kind.value for f in project.all_flows())
    for kind, n in sorted(flow_kinds.items()):
        print(f"    {kind:18s} {n}")
    print()

    print(color("==> Edges (physical / non-data)", "1"))
    print(f"  total: {len(project.edges)}")
    print()

    # ─── Cross-reference checks ───

    print(color("==> Reference integrity checks", "1"))
    issues: list[str] = []

    entity_ids = set(project.entities.keys())

    for e in project.all_entities():
        if e.parent and e.parent not in entity_ids:
            issues.append(f"entity {e.id!r}: parent {e.parent!r} not in dictionary")
        if e.parent_state and e.parent_state not in entity_ids:
            issues.append(f"entity {e.id!r}: parent_state {e.parent_state!r} not in dictionary")

    for f in project.all_flows():
        if f.source not in entity_ids:
            issues.append(f"flow {f.id!r}: source {f.source!r} not in dictionary")
        if f.target not in entity_ids:
            issues.append(f"flow {f.id!r}: target {f.target!r} not in dictionary")

    for ed in project.all_edges():
        if ed.source not in entity_ids:
            issues.append(f"edge {ed.id!r}: source {ed.source!r} not in dictionary")
        if ed.target not in entity_ids:
            issues.append(f"edge {ed.id!r}: target {ed.target!r} not in dictionary")

    if issues:
        print(color(f"  ✗ {len(issues)} reference issue(s):", "31"))
        for issue in issues:
            print(f"    - {issue}")
        return 1
    else:
        print(color("  ✓ all parent / parent_state / source / target references resolve", "32"))
    print()

    # ─── Hierarchy summary ───

    print(color("==> Hierarchy (top-level + immediate children)", "1"))
    top_level = project.entities_at_level(0)
    for top in top_level:
        marker = "○" if top.kind.value != "system" else "◎"
        print(f"  {marker} {top.label} ({top.id}, level 0, {top.kind.value})")
        children = project.children_of(top.id)
        for c in children:
            print(f"     └─ {c.label} ({c.id}, level {c.level}, {c.kind.value})")
    print()

    print(color("All checks passed.", "32"))
    return 0


if __name__ == "__main__":
    # Repo layout: <repo-root>/toolkit/scripts/this.py + <repo-root>/examples/solar/dictionary.yaml
    repo_root = Path(__file__).resolve().parent.parent.parent
    default_dict = repo_root / "examples" / "solar" / "dictionary.yaml"

    dict_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_dict
    if not dict_path.exists():
        print(color(f"ERROR: {dict_path} does not exist", "31"), file=sys.stderr)
        sys.exit(2)

    sys.exit(main(dict_path))
