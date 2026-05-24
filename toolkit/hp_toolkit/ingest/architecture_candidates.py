"""Stage 5 candidate extractor — surfaces deployment-unit candidates from
infrastructure files (Dockerfile, docker-compose, k8s manifests, terraform,
package manifests) for the LLM architect agent.

Pure Python, no LLM. Reads `intermediate/scan.json`, focuses on files
classified `infra` (and a few config files like `package.json` / `Cargo.toml`
that announce a deployable unit). Emits `intermediate/architecture-candidates.json`.

The LLM agent (`hp-ingest-architect`) takes these candidates and decides
which become HP Stage-5 modules / interconnects, names them, and draws
the allocation graph against the processes in `hp-graph.json`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .schema import HpRoleHint, ProjectScan


class ModuleCandidate(BaseModel):
    """One deployment-unit candidate. The LLM decides if this becomes a
    Stage-5 module + what kind (hardware / software / organizational)."""

    candidate_id: str                            # synthetic short id
    kind_hint: str                               # "container" | "k8s_pod" | "package" | "infra_resource"
    name_hint: Optional[str] = None              # extracted name, e.g., from compose service or k8s deployment
    source_file: str                             # which infra file surfaced this
    related_files: list[str] = Field(default_factory=list)  # related infra files
    evidence: list[str] = Field(default_factory=list)


class InterconnectCandidate(BaseModel):
    """One interconnect candidate — typically a docker-compose network, k8s
    Service, or implicit network between containers."""

    candidate_id: str
    kind_hint: str                               # "compose_network" | "k8s_service" | "network_policy"
    name_hint: Optional[str] = None
    source_file: str
    endpoints_hinted: list[str] = Field(default_factory=list)  # module candidate ids it connects
    evidence: list[str] = Field(default_factory=list)


class ArchitectureCandidates(BaseModel):
    """`intermediate/architecture-candidates.json` shape."""

    modules: list[ModuleCandidate] = Field(default_factory=list)
    interconnects: list[InterconnectCandidate] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Extractors per infra file type
# ─────────────────────────────────────────────────────────────────────

_COMPOSE_SERVICE_PATTERN = re.compile(
    r"^\s{2}(\w[\w-]*):\s*$",                    # YAML key one indent in (compose v2/v3 services:)
    re.MULTILINE,
)
_K8S_KIND_PATTERN = re.compile(r"^kind:\s*(\w+)", re.MULTILINE)
_K8S_NAME_PATTERN = re.compile(r"^\s*name:\s*(\S+)", re.MULTILINE)
_TERRAFORM_RESOURCE_PATTERN = re.compile(r'^resource\s+"([^"]+)"\s+"([^"]+)"', re.MULTILINE)
_PACKAGE_NAME_JSON   = re.compile(r'"name"\s*:\s*"([^"]+)"')
_PACKAGE_NAME_CARGO  = re.compile(r'\[package\][^\[]*?name\s*=\s*"([^"]+)"', re.DOTALL)
_PACKAGE_NAME_PYPRJ  = re.compile(r'(?:^|\n)\[(?:tool\.poetry|project)\][^\[]*?name\s*=\s*"([^"]+)"', re.DOTALL)


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def extract_candidates(scan: ProjectScan, codebase_root: Path) -> ArchitectureCandidates:
    """Walk the scan output, pull deployment-unit candidates from infra/config
    files."""
    modules: list[ModuleCandidate] = []
    interconnects: list[InterconnectCandidate] = []

    for f in scan.files:
        if not f.is_significant:
            continue
        # We focus on infra files + package manifests
        if f.hp_role_hint not in (HpRoleHint.INFRA, HpRoleHint.CONFIG):
            continue
        abs_path = codebase_root / f.path
        content = _read_head(abs_path)
        if content is None:
            continue
        _process_file(f.path, content, modules, interconnects)

    return ArchitectureCandidates(modules=modules, interconnects=interconnects)


def write_candidates(c: ArchitectureCandidates, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(c.model_dump_json(indent=2))


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

_MAX_HEAD = 32 * 1024


def _read_head(path: Path) -> Optional[str]:
    try:
        with path.open("rb") as fh:
            head = fh.read(_MAX_HEAD)
        if b"\x00" in head:
            return None
        return head.decode("utf-8", errors="replace")
    except (OSError, PermissionError):
        return None


def _process_file(
    rel_path: str,
    content: str,
    modules: list[ModuleCandidate],
    interconnects: list[InterconnectCandidate],
) -> None:
    name = Path(rel_path).name.lower()

    # Dockerfile → one module per Dockerfile (the container image)
    if name == "dockerfile" or name.startswith("dockerfile."):
        from_lines = [l.strip() for l in content.splitlines() if l.strip().startswith("FROM ")]
        modules.append(ModuleCandidate(
            candidate_id=_candidate_id_from_path(rel_path),
            kind_hint="container",
            name_hint=_infer_container_name(rel_path),
            source_file=rel_path,
            evidence=from_lines[:3],
        ))
        return

    # docker-compose → multiple modules + a network interconnect
    if name in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}:
        # Extract services block — heuristic: find `services:` and then top-level keys
        services_match = re.search(r"^services:\s*\n((?:[^\n]*\n)*?)(?:^\w|\Z)", content, re.MULTILINE)
        services_block = services_match.group(1) if services_match else content
        service_names = _COMPOSE_SERVICE_PATTERN.findall(services_block)
        service_ids: list[str] = []
        for svc in service_names:
            sid = f"compose-{svc}"
            service_ids.append(sid)
            modules.append(ModuleCandidate(
                candidate_id=sid,
                kind_hint="container",
                name_hint=svc,
                source_file=rel_path,
                evidence=[f"compose service: {svc}"],
            ))
        if len(service_ids) >= 2:
            interconnects.append(InterconnectCandidate(
                candidate_id=f"compose-network-{Path(rel_path).stem}",
                kind_hint="compose_network",
                name_hint="default compose network",
                source_file=rel_path,
                endpoints_hinted=service_ids,
                evidence=[f"implicit network between {len(service_ids)} compose services"],
            ))
        return

    # k8s manifests
    if rel_path.endswith((".yaml", ".yml")) and re.search(r"^apiVersion:", content, re.MULTILINE):
        for kind_match in _K8S_KIND_PATTERN.finditer(content):
            kind = kind_match.group(1)
            # Find the closest name after the kind line
            name_search_window = content[kind_match.start():kind_match.start() + 600]
            name_match = _K8S_NAME_PATTERN.search(name_search_window)
            resource_name = name_match.group(1) if name_match else "unnamed"

            if kind in {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"}:
                modules.append(ModuleCandidate(
                    candidate_id=f"k8s-{resource_name}",
                    kind_hint="k8s_pod",
                    name_hint=resource_name,
                    source_file=rel_path,
                    evidence=[f"k8s {kind}: {resource_name}"],
                ))
            elif kind == "Service":
                interconnects.append(InterconnectCandidate(
                    candidate_id=f"k8s-svc-{resource_name}",
                    kind_hint="k8s_service",
                    name_hint=resource_name,
                    source_file=rel_path,
                    evidence=[f"k8s Service: {resource_name}"],
                ))
        return

    # Terraform
    if rel_path.endswith(".tf"):
        for m in _TERRAFORM_RESOURCE_PATTERN.finditer(content):
            resource_kind, resource_name = m.group(1), m.group(2)
            modules.append(ModuleCandidate(
                candidate_id=f"tf-{resource_kind}-{resource_name}",
                kind_hint="infra_resource",
                name_hint=f"{resource_kind}.{resource_name}",
                source_file=rel_path,
                evidence=[f"terraform: resource \"{resource_kind}\" \"{resource_name}\""],
            ))
        return

    # Package manifests = one deployable unit per package
    if name == "package.json":
        m = _PACKAGE_NAME_JSON.search(content)
        if m:
            pkg = m.group(1)
            modules.append(ModuleCandidate(
                candidate_id=f"npm-{pkg}",
                kind_hint="package",
                name_hint=pkg,
                source_file=rel_path,
                evidence=[f"npm package: {pkg}"],
            ))
        return

    if name == "cargo.toml":
        m = _PACKAGE_NAME_CARGO.search(content)
        if m:
            pkg = m.group(1)
            modules.append(ModuleCandidate(
                candidate_id=f"cargo-{pkg}",
                kind_hint="package",
                name_hint=pkg,
                source_file=rel_path,
                evidence=[f"cargo package: {pkg}"],
            ))
        return

    if name == "pyproject.toml":
        m = _PACKAGE_NAME_PYPRJ.search(content)
        if m:
            pkg = m.group(1)
            modules.append(ModuleCandidate(
                candidate_id=f"py-{pkg}",
                kind_hint="package",
                name_hint=pkg,
                source_file=rel_path,
                evidence=[f"python package: {pkg}"],
            ))
        return

    if name == "go.mod":
        first_line = content.splitlines()[0] if content else ""
        if first_line.startswith("module "):
            pkg = first_line.split(None, 1)[1].strip()
            modules.append(ModuleCandidate(
                candidate_id=f"go-{Path(pkg).name}",
                kind_hint="package",
                name_hint=pkg,
                source_file=rel_path,
                evidence=[first_line],
            ))


def _candidate_id_from_path(rel_path: str) -> str:
    """Derive a short candidate id from a Dockerfile / etc. path."""
    parent = Path(rel_path).parent.as_posix()
    if parent == ".":
        return "container-root"
    return f"container-{parent.replace('/', '-')}"


def _infer_container_name(rel_path: str) -> str:
    """Best-effort guess at a container name from its Dockerfile path."""
    parent = Path(rel_path).parent.as_posix()
    if parent == ".":
        return "root"
    return parent.split("/")[-1]


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def _main(argv: Optional[list[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="hp_architecture_candidates",
        description="Extract Stage-5 architecture-module candidates from scan.json.",
    )
    parser.add_argument("--scan",   required=True, help="Path to intermediate/scan.json")
    parser.add_argument("--codebase", required=True, help="Codebase root (for re-reading file content)")
    parser.add_argument("--output", required=True, help="Output path for architecture-candidates.json")
    args = parser.parse_args(argv)

    scan_data = json.loads(Path(args.scan).read_text())
    scan = ProjectScan.model_validate(scan_data)
    candidates = extract_candidates(scan, Path(args.codebase))
    write_candidates(candidates, Path(args.output))
    print(f"wrote {args.output} "
          f"({len(candidates.modules)} module candidates, "
          f"{len(candidates.interconnects)} interconnect candidates)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
