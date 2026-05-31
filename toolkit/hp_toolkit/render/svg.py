# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""SVG orchestration — invoke `d2` and `mmdc` binaries to render
generated source files to static SVGs.

Both binaries are installed by `toolkit/bootstrap.sh` into `~/.local/bin`.

Functions:
    render_d2_to_svg(source, output)        -> bool
    render_mermaid_to_svg(source, output)   -> bool

Each raises FileNotFoundError if the binary isn't on PATH or in
~/.local/bin; otherwise returns True on success, False on render failure.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _find_binary(name: str) -> Optional[str]:
    """Locate a binary — PATH first, then ~/.local/bin fallback."""
    path = shutil.which(name)
    if path:
        return path
    local = Path.home() / ".local" / "bin" / name
    if local.exists():
        return str(local)
    return None


def render_d2_to_svg(source: str | Path, output: str | Path) -> bool:
    """Invoke `d2 <source> <output>` to render a .d2 file to SVG.

    Returns True on success. Raises FileNotFoundError if `d2` isn't
    installed (run `bash toolkit/bootstrap.sh`).
    """
    d2 = _find_binary("d2")
    if d2 is None:
        raise FileNotFoundError(
            "d2 binary not found. Run `bash toolkit/bootstrap.sh` to install."
        )

    source = Path(source)
    output = Path(output)

    result = subprocess.run(
        [d2, str(source), str(output)],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        sys.stderr.write(f"d2 stderr: {result.stderr}\n")
        return False

    return output.exists()


def render_mermaid_to_svg(
    source: str | Path,
    output: str | Path,
    puppeteer_config: Optional[str | Path] = None,
) -> bool:
    """Invoke `mmdc -i <source> -o <output>` to render Mermaid → SVG.

    Source can be `.mmd` (raw Mermaid) or `.md` (markdown with fenced
    mermaid blocks). For `.md` input, mmdc appends `-1` to the output
    filename; this function detects that and moves the file to the
    requested output path.

    On Ubuntu 23.10+, mmdc needs `--no-sandbox` passed via a puppeteer
    config file. Defaults to `toolkit/.puppeteer-config.json` if found.

    Returns True on success. Raises FileNotFoundError if `mmdc` isn't
    installed (run `bash toolkit/bootstrap.sh`).
    """
    mmdc = _find_binary("mmdc")
    if mmdc is None:
        raise FileNotFoundError(
            "mmdc binary not found. Run `bash toolkit/bootstrap.sh` to install."
        )

    source = Path(source)
    output = Path(output)

    # Auto-locate puppeteer config relative to the package root if not provided
    if puppeteer_config is None:
        # render/svg.py → hp_toolkit/render → hp_toolkit → toolkit
        pkg_dir = Path(__file__).resolve().parent.parent.parent
        candidate = pkg_dir / ".puppeteer-config.json"
        if candidate.exists():
            puppeteer_config = candidate

    cmd = [mmdc, "-i", str(source), "-o", str(output)]
    if puppeteer_config:
        cmd.extend(["-p", str(puppeteer_config)])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        sys.stderr.write(f"mmdc stderr: {result.stderr}\n")
        return False

    # Handle the -1 suffix mmdc appends when input is a markdown file
    # containing a single fenced block (vs. a raw .mmd file).
    suffix_output = output.with_name(output.stem + "-1" + output.suffix)
    if suffix_output.exists():
        if output.exists():
            output.unlink()  # remove any stale prior output
        suffix_output.rename(output)

    return output.exists()
