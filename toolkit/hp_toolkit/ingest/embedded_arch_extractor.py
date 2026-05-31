# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Embedded-target architecture-candidate extractors (per EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding C).

Sibling to `compose_parser.py` / `dockerfile_parser.py` / `k8s_parser.py`
from Branch 2 T8. Reads firmware-specific deployment artifacts that the
cloud-shaped extractor in `architecture_candidates.py` doesn't recognize:

- **CMakeLists.txt** → `add_executable(<target>)` / `px4_add_module(MODULE <name>)` /
  `target_link_libraries(<target> <lib>)`. PX4 uses `px4_add_module` for
  every loadable firmware module; standard projects use `add_executable`.
- **STM32CubeMX `.ioc`** → declares the MCU + pinout + peripheral config.
  Each `.ioc` is one MCU module candidate; enabled peripherals become
  evidence. Parsed as key=value.
- **PX4 board configs (`*.px4board`)** → per-board feature selection
  (CONFIG_BOARD_* / CONFIG_DRIVERS_*). Each `.px4board` file is one
  DeploymentConfig.
- **Linker scripts (`*.ld`)** → memory map (FLASH/RAM regions). Surfaces
  as evidence on the MCU module candidate.
- **Arduino `.ino`** → one sketch = one module candidate.

Per locked Q3: regex extraction; no new dep (CMake is Turing-complete but
the common forms parse cleanly). Same trade-off Branch 2 made for
terraform.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .architecture_candidates import (
    CandidateEdge,
    DeploymentConfig,
    InterconnectCandidate,
    ModuleCandidate,
)


# ─────────────────────────────────────────────────────────────────────
# Patterns
# ─────────────────────────────────────────────────────────────────────

# CMake common forms (per locked Q3 — regex over python-cmake).
_CMAKE_ADD_EXECUTABLE = re.compile(
    r"\badd_executable\s*\(\s*(\w+)",
)
_CMAKE_PX4_ADD_MODULE = re.compile(
    r"\bpx4_add_module\s*\([^)]*?\bMODULE\s+(\w+)",
    re.DOTALL,
)
_CMAKE_TARGET_LINK = re.compile(
    r"\btarget_link_libraries\s*\(\s*(\w+)\s+(?:PUBLIC|PRIVATE|INTERFACE\s+)?([^)]+)\)",
    re.DOTALL,
)
# PX4 module DEPENDS clause inside px4_add_module(...)
_PX4_MODULE_DEPENDS = re.compile(
    r"\bDEPENDS\s+([^\n)]+)",
)

# STM32CubeMX .ioc — key=value, one per line. Most relevant keys:
_IOC_MCU_FAMILY = re.compile(r"^Mcu\.Family\s*=\s*(\S+)", re.MULTILINE)
_IOC_MCU_CPN = re.compile(r"^Mcu\.CPN\s*=\s*(\S+)", re.MULTILINE)
_IOC_RCC_TYPE = re.compile(r"^RCC\.AHB[\w.]*=", re.MULTILINE)
# Enabled peripheral: any line `<PERIPH>.IPParameters=...` or
# `<PERIPH>.Mode=...` where PERIPH is an uppercase identifier ≥3 chars
_IOC_PERIPHERAL = re.compile(r"^([A-Z][A-Z0-9_]{2,})\.(Mode|IPParameters)\s*=", re.MULTILINE)

# PX4 .px4board — Kconfig-style: CONFIG_<NAME>=<value>
_PX4BOARD_LINE = re.compile(r"^CONFIG_([A-Z][A-Z0-9_]+)\s*=\s*(.+?)\s*$", re.MULTILINE)
_PX4BOARD_DRIVER_CONFIG = re.compile(r"^CONFIG_(DRIVERS_[A-Z0-9_]+)\s*=\s*y\s*$", re.MULTILINE)
_PX4BOARD_MODULE_CONFIG = re.compile(r"^CONFIG_(MODULES_[A-Z0-9_]+)\s*=\s*y\s*$", re.MULTILINE)

# Linker script .ld — MEMORY block
_LINKER_MEMORY_REGION = re.compile(
    r"^\s*(\w+)\s*\([rwx!]+\)\s*:\s*ORIGIN\s*=\s*([\w]+|0x[0-9a-fA-F]+)\s*,\s*LENGTH\s*=\s*([\w]+)",
    re.MULTILINE | re.IGNORECASE,
)

# Arduino sketch — `void setup()` + `void loop()`
_ARDUINO_SETUP_LOOP = re.compile(r"^void\s+setup\s*\(\s*\)", re.MULTILINE)


# ─────────────────────────────────────────────────────────────────────
# Public API — per-format parsers
# ─────────────────────────────────────────────────────────────────────

def parse_cmakelists(
    rel_path: str,
    content: str,
) -> tuple[list[ModuleCandidate], list[InterconnectCandidate], list[CandidateEdge], Optional[DeploymentConfig]]:
    """Parse a CMakeLists.txt for firmware-target / px4-module candidates.

    Each `add_executable(<target>)` and `px4_add_module(MODULE <name>)`
    becomes a ModuleCandidate. `target_link_libraries` + PX4 `DEPENDS`
    clauses produce CandidateEdges between modules."""
    modules: list[ModuleCandidate] = []
    edges: list[CandidateEdge] = []

    # add_executable targets
    for m in _CMAKE_ADD_EXECUTABLE.finditer(content):
        name = m.group(1)
        cid = f"cmake-exec-{_slug(name)}"
        modules.append(ModuleCandidate(
            candidate_id=cid,
            kind_hint="firmware_target",
            name_hint=name,
            source_file=rel_path,
            evidence=[f"CMake add_executable({name})"],
        ))

    # PX4 modules
    for m in _CMAKE_PX4_ADD_MODULE.finditer(content):
        name = m.group(1)
        cid = f"px4-module-{_slug(name)}"
        # Look ahead in the same px4_add_module() call for DEPENDS
        call_start = m.start()
        call_end = _find_matching_paren(content, content.find("(", call_start))
        call_body = content[call_start:call_end] if call_end > call_start else content[call_start:call_start + 2000]
        deps_match = _PX4_MODULE_DEPENDS.search(call_body)
        deps: list[str] = []
        if deps_match:
            for dep in deps_match.group(1).split():
                dep = dep.strip()
                if dep and not dep.startswith("$"):
                    deps.append(dep)
                    edges.append(CandidateEdge(
                        kind="px4_module_depends_on",
                        source_candidate=cid,
                        target_candidate=f"px4-module-{_slug(dep)}",
                        evidence=f"px4_add_module({name}) DEPENDS {dep}",
                    ))
        ev = [f"px4_add_module(MODULE {name})"]
        if deps:
            ev.append(f"DEPENDS: {' '.join(deps[:5])}")
        modules.append(ModuleCandidate(
            candidate_id=cid,
            kind_hint="px4_module",
            name_hint=name,
            source_file=rel_path,
            evidence=ev,
        ))

    # target_link_libraries → edges between candidate modules
    for m in _CMAKE_TARGET_LINK.finditer(content):
        target = m.group(1)
        libs = [w for w in m.group(2).split() if w and not w.startswith("$") and w.upper() not in {"PUBLIC", "PRIVATE", "INTERFACE"}]
        target_cid = f"cmake-exec-{_slug(target)}"
        for lib in libs:
            edges.append(CandidateEdge(
                kind="cmake_target_link",
                source_candidate=target_cid,
                target_candidate=f"cmake-exec-{_slug(lib)}",
                evidence=f"target_link_libraries({target} {lib})",
            ))

    return modules, [], edges, None


def parse_stm32_ioc(
    rel_path: str,
    content: str,
) -> tuple[list[ModuleCandidate], list[InterconnectCandidate], list[CandidateEdge], Optional[DeploymentConfig]]:
    """Parse an STM32CubeMX `.ioc` file. One file = one MCU candidate.

    Captures MCU family + part number + the set of enabled peripherals.
    Each peripheral becomes evidence on the candidate (not its own
    module — peripherals are integrated, not deployment units)."""
    family_m = _IOC_MCU_FAMILY.search(content)
    cpn_m = _IOC_MCU_CPN.search(content)
    if not family_m and not cpn_m:
        return [], [], [], None

    family = family_m.group(1) if family_m else "STM32"
    cpn = cpn_m.group(1) if cpn_m else family
    peripherals = sorted({m.group(1) for m in _IOC_PERIPHERAL.finditer(content)})

    name = Path(rel_path).stem            # e.g. `leocore` from `leocore.ioc`
    cid = f"stm32-mcu-{_slug(name)}"
    ev = [f"STM32CubeMX: family={family}, CPN={cpn}"]
    if peripherals:
        ev.append(f"peripherals enabled: {', '.join(peripherals[:12])}")

    return [ModuleCandidate(
        candidate_id=cid,
        kind_hint="mcu",
        name_hint=f"{name} ({cpn})",
        source_file=rel_path,
        evidence=ev,
        image=cpn,                        # reuse `image` field for the MCU part number
    )], [], [], None


def parse_px4board(
    rel_path: str,
    content: str,
) -> tuple[list[ModuleCandidate], list[InterconnectCandidate], list[CandidateEdge], Optional[DeploymentConfig]]:
    """Parse a PX4 `.px4board` file. One file = one DeploymentConfig.

    Captures the set of CONFIG_DRIVERS_* + CONFIG_MODULES_* flags (which
    modules are included in this board config) + the toolchain /
    architecture metadata. The architect agent uses this to recognize
    that one logical px4_module appears in N board configs."""
    if not _PX4BOARD_LINE.search(content):
        return [], [], [], None

    # Board name from path: `boards/<vendor>/<board>/<variant>.px4board`
    parts = rel_path.split("/")
    board_name = ""
    if "boards" in parts:
        idx = parts.index("boards")
        if idx + 2 < len(parts):
            vendor = parts[idx + 1]
            board = parts[idx + 2]
            variant = Path(parts[-1]).stem
            board_name = f"{vendor}-{board}-{variant}" if variant != "default" else f"{vendor}-{board}"
    if not board_name:
        board_name = Path(rel_path).stem

    enabled_drivers = sorted({m.group(1) for m in _PX4BOARD_DRIVER_CONFIG.finditer(content)})
    enabled_modules = sorted({m.group(1) for m in _PX4BOARD_MODULE_CONFIG.finditer(content)})

    # Map each enabled module to its px4-module-<slug> candidate id, so the
    # architect can link the board to its module set
    candidate_ids = [f"px4-module-{_slug(m.replace('MODULES_', '').lower())}" for m in enabled_modules]

    return [], [], [], DeploymentConfig(
        name=_slug(board_name),
        source_file=rel_path,
        kind="px4_board",
        candidate_ids=candidate_ids,
    )


def parse_linker_script(
    rel_path: str,
    content: str,
) -> tuple[list[ModuleCandidate], list[InterconnectCandidate], list[CandidateEdge], Optional[DeploymentConfig]]:
    """Parse a linker script `.ld` for the MEMORY block.

    Doesn't produce its own ModuleCandidate (the linker script describes
    the deployment artifact's memory layout, not a module itself) — but
    we surface the memory map as a stand-alone candidate the architect
    can attach to the firmware target."""
    regions = list(_LINKER_MEMORY_REGION.finditer(content))
    if not regions:
        return [], [], [], None

    name = Path(rel_path).stem
    cid = f"ld-memory-{_slug(name)}"
    ev = [f"linker script: {len(regions)} memory regions"]
    for r in regions[:5]:
        ev.append(f"  {r.group(1)}: ORIGIN={r.group(2)}, LENGTH={r.group(3)}")

    return [ModuleCandidate(
        candidate_id=cid,
        kind_hint="memory_layout",
        name_hint=f"{name} memory map",
        source_file=rel_path,
        evidence=ev,
    )], [], [], None


def parse_arduino_sketch(
    rel_path: str,
    content: str,
) -> tuple[list[ModuleCandidate], list[InterconnectCandidate], list[CandidateEdge], Optional[DeploymentConfig]]:
    """Parse an Arduino `.ino` sketch. One sketch = one firmware target.

    Detected by `void setup()` presence; the sketch directory name is
    used as the module name."""
    if not _ARDUINO_SETUP_LOOP.search(content):
        return [], [], [], None

    sketch_name = Path(rel_path).stem
    cid = f"arduino-{_slug(sketch_name)}"

    return [ModuleCandidate(
        candidate_id=cid,
        kind_hint="arduino_sketch",
        name_hint=sketch_name,
        source_file=rel_path,
        evidence=[f"Arduino sketch: {rel_path}"],
    )], [], [], None


# ─────────────────────────────────────────────────────────────────────
# Dispatch helper — used by architecture_candidates._process_file
# ─────────────────────────────────────────────────────────────────────

def try_dispatch(
    rel_path: str,
    content: str,
) -> Optional[tuple[list[ModuleCandidate], list[InterconnectCandidate], list[CandidateEdge], Optional[DeploymentConfig]]]:
    """Return the per-format parser's output for `rel_path` if it matches
    one of the embedded formats, else None. Called from
    `architecture_candidates._process_file` after the existing
    compose / dockerfile / k8s / package-manifest checks fail to match."""
    name = Path(rel_path).name.lower()
    if name == "cmakelists.txt":
        return parse_cmakelists(rel_path, content)
    if name.endswith(".ioc"):
        return parse_stm32_ioc(rel_path, content)
    if name.endswith(".px4board"):
        return parse_px4board(rel_path, content)
    if name.endswith(".ld"):
        return parse_linker_script(rel_path, content)
    if name.endswith(".ino"):
        return parse_arduino_sketch(rel_path, content)
    return None


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

_SLUG_REPLACE = re.compile(r"[^a-z0-9-]+")


def _slug(s: str) -> str:
    s = s.lower().replace("_", "-")
    s = _SLUG_REPLACE.sub("-", s).strip("-")
    return s or "default"


def _find_matching_paren(text: str, open_idx: int) -> int:
    """Return the index *after* the closing paren that matches the open
    paren at `open_idx`. Returns -1 on failure (unmatched)."""
    if open_idx < 0 or open_idx >= len(text) or text[open_idx] != "(":
        return -1
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    return -1
