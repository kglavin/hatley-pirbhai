#!/usr/bin/env python
"""hp-ingest — brownfield codebase → HP `dictionary.yaml` (Commit 1: scanner only).

Usage:
    uv run python scripts/hp_ingest.py <codebase-path> --output <project-dir> [options]

Options (Commit 1):
    --scan-only           Run only the Stage-0 scanner; emit `intermediate/scan.json`
                          and stop. (Default for now since downstream agents land
                          in later commits.)

Options (planned, Commits 2 + 3):
    --no-architecture     Skip Stage 5 (architecture model).
    --resume              Resume from existing `intermediate/` if present.
    --incremental         Only re-ingest what changed since the last commit.

Example:
    uv run python scripts/hp_ingest.py \\
        /home/kevin/hatley-pirbhai \\
        --output /home/kevin/hatley-pirbhai/examples/_self-ingest \\
        --scan-only

See toolkit/INGEST_DESIGN.md for the full design.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hp_toolkit.ingest.scan import scan_codebase, write_scan


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
                        help="Run only the Stage-0 scanner (Commit 1 default)")
    # Planned flags — accepted but currently equivalent to --scan-only.
    parser.add_argument("--no-architecture", action="store_true",
                        help="(Commit 3) skip Stage 5")
    parser.add_argument("--resume", action="store_true",
                        help="(Commit 2+) resume from existing intermediate/")
    parser.add_argument("--incremental", action="store_true",
                        help="(Commit 2+) re-ingest only what changed since last commit")

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
    scan_path = output / "intermediate" / "scan.json"
    print(_color(f"==> Writing {scan_path.relative_to(output)}", "1"))
    write_scan(scan, scan_path)
    print(_color(f"  wrote {scan_path.name} ({scan_path.stat().st_size} bytes)", "32"))
    print()

    if not args.scan_only:
        print(_color("⚠ Stages 1–5 not yet implemented in this commit. "
                     "Re-run with --scan-only or wait for Commit 2.", "33"))

    print(_color("Done.", "32"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
