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


class CandidateEdge(BaseModel):
    """A typed relationship between two candidate modules — extracted from
    compose `depends_on`, k8s Service selector matching, or terraform
    resource dependency. Per locked tuning H.5.a.

    The architect agent turns these into architecture flows (or `refines:`
    deployment-order edges, for asymmetric init-only relationships)."""

    kind: str                                    # "compose_depends_on" | "compose_port_exposed" | "compose_volume_mount" | "k8s_service_selector" | "k8s_ingress_target" | "tf_resource_dependency" | "dockerfile_exposes"
    source_candidate: str                        # candidate_id of one end
    target_candidate: Optional[str] = None       # candidate_id of the other end (None for "port exposed to outside world")
    evidence: Optional[str] = None               # raw extracted string


class ModuleCandidate(BaseModel):
    """One deployment-unit candidate. The LLM decides if this becomes a
    Stage-5 module + what kind (hardware / software / organizational).

    Per locked tuning H.5: rich structural fields are populated by the
    format-specific parsers (compose_parser, dockerfile_parser, k8s_parser)
    so the architect agent can read deployment relationships rather than
    inferring them. `deployment_config` groups candidates by source
    configuration (bluerockccpd / agate-test / aws-basic on cloudctlplane);
    the same logical service can appear in multiple deployments."""

    candidate_id: str                            # synthetic short id
    kind_hint: str                               # "container" | "k8s_pod" | "package" | "infra_resource"
    name_hint: Optional[str] = None              # extracted name, e.g., from compose service or k8s deployment
    source_file: str                             # which infra file surfaced this
    related_files: list[str] = Field(default_factory=list)  # related infra files
    evidence: list[str] = Field(default_factory=list)

    # H.5.a — typed structural fields populated by format-specific parsers
    deployment_config: Optional[str] = None      # which deployment configuration (compose file basename / k8s namespace) this lives in
    image: Optional[str] = None                  # `image:` from compose / `FROM` in Dockerfile
    build_context: Optional[str] = None          # `build:` in compose (in-tree build vs pre-built image)
    ports_exposed: list[str] = Field(default_factory=list)
    volumes_mounted: list[str] = Field(default_factory=list)
    environment_keys: list[str] = Field(default_factory=list)   # env-var NAMES only (values can be secrets)
    replicas: int = 1
    profiles: list[str] = Field(default_factory=list)
    healthcheck: bool = False


class InterconnectCandidate(BaseModel):
    """One interconnect candidate — typically a docker-compose network, k8s
    Service, or implicit network between containers.

    Per H.5.a: scoped by `deployment_config` so the architect can produce
    per-deployment interconnect topologies when multiple configurations
    exist."""

    candidate_id: str
    kind_hint: str                               # "compose_network" | "k8s_service" | "network_policy" | "k8s_ingress"
    name_hint: Optional[str] = None
    source_file: str
    endpoints_hinted: list[str] = Field(default_factory=list)  # module candidate ids it connects
    evidence: list[str] = Field(default_factory=list)

    # H.5.a
    deployment_config: Optional[str] = None
    external: bool = False                       # exposes to outside world (Ingress / LoadBalancer / compose port-publish)


class DeploymentConfig(BaseModel):
    """One deployment configuration — a compose file or k8s namespace.

    Per H.5.b: when multiple compose / k8s configs exist (cloudctlplane has
    bluerockccpd / agate-test-deployment / aws-basic), each is one
    DeploymentConfig. Modules appear in N of them; interconnect topologies
    are per-config; the architect produces a union module set + per-config
    interconnects."""

    name: str                                    # short id ("bluerockccpd")
    source_file: str                             # the compose / k8s manifest file
    kind: str                                    # "compose" | "k8s"
    candidate_ids: list[str] = Field(default_factory=list)


class ArchitectureCandidates(BaseModel):
    """`intermediate/architecture-candidates.json` shape."""

    modules: list[ModuleCandidate] = Field(default_factory=list)
    interconnects: list[InterconnectCandidate] = Field(default_factory=list)
    edges: list[CandidateEdge] = Field(default_factory=list)
    deployments: list[DeploymentConfig] = Field(default_factory=list)


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
    files.

    Per locked tuning H.5: dispatches to format-specific parsers
    (`compose_parser`, `dockerfile_parser`, `k8s_parser`) for the rich
    structural fields the architect agent needs. Falls back to the
    regex-based local extractor for package manifests + terraform (the
    latter is regex-only by design until a `python-hcl2` dep makes sense)."""
    modules: list[ModuleCandidate] = []
    interconnects: list[InterconnectCandidate] = []
    edges: list[CandidateEdge] = []
    deployments: list[DeploymentConfig] = []

    for f in scan.files:
        if not f.is_significant:
            continue
        if f.hp_role_hint not in (HpRoleHint.INFRA, HpRoleHint.CONFIG):
            continue
        abs_path = codebase_root / f.path
        content = _read_head(abs_path)
        if content is None:
            continue
        _process_file(f.path, content, modules, interconnects, edges, deployments)

    return ArchitectureCandidates(
        modules=modules,
        interconnects=interconnects,
        edges=edges,
        deployments=deployments,
    )


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
    edges: list[CandidateEdge],
    deployments: list[DeploymentConfig],
) -> None:
    # Lazy imports so the new parsers' YAML dependency doesn't fire for
    # the package-manifest / terraform paths.
    from .compose_parser import parse_compose
    from .dockerfile_parser import parse_dockerfile
    from .embedded_arch_extractor import try_dispatch as try_embedded_dispatch
    from .k8s_parser import parse_k8s

    name = Path(rel_path).name.lower()

    # Embedded firmware artifacts (per EMBEDDED_FIRMWARE_TUNING_DESIGN.md
    # finding C — CMakeLists / .ioc / .px4board / .ld / .ino). Checked first
    # because some embedded files (notably CMakeLists.txt) might otherwise
    # fall through to the generic "no match" path.
    embedded_result = try_embedded_dispatch(rel_path, content)
    if embedded_result is not None:
        mods, ics, eds, deployment = embedded_result
        modules.extend(mods)
        interconnects.extend(ics)
        edges.extend(eds)
        if deployment:
            deployments.append(deployment)
        # Don't `return` here — CMakeLists.txt classifies as infra but we
        # still want it to pass through other extractors if nothing
        # matched. The current downstream extractors all check filename;
        # falling through is safe.
        if mods or ics or eds or deployment:
            return

    # Dockerfile → typed Dockerfile parse (H.5.a)
    if name == "dockerfile" or name.startswith("dockerfile."):
        df = parse_dockerfile(content)
        module = ModuleCandidate(
            candidate_id=_candidate_id_from_path(rel_path),
            kind_hint="container",
            name_hint=_infer_container_name(rel_path),
            source_file=rel_path,
            evidence=[
                f"FROM: {df.from_image}" if df.from_image else "Dockerfile (no FROM extracted)",
                *([f"CMD: {df.cmd}"] if df.cmd else []),
                *([f"ENTRYPOINT: {df.entrypoint}"] if df.entrypoint else []),
                *([f"LABEL.{k}: {v}" for k, v in list(df.labels.items())[:3]]),
            ],
            image=df.from_image,
            ports_exposed=df.exposed_ports,
            environment_keys=df.env_keys,
            healthcheck=df.healthcheck,
        )
        modules.append(module)
        # Outward port → external surface edge per port
        for port in df.exposed_ports:
            edges.append(CandidateEdge(
                kind="dockerfile_exposes",
                source_candidate=module.candidate_id,
                target_candidate=None,
                evidence=f"Dockerfile {rel_path}: EXPOSE {port}",
            ))
        return

    # docker-compose → typed parser dispatch
    if name in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"} \
            or _is_compose_named(name):
        mods, ics, eds, deployment = parse_compose(rel_path, content)
        modules.extend(mods)
        interconnects.extend(ics)
        edges.extend(eds)
        if deployment:
            deployments.append(deployment)
        return

    # k8s manifests — typed parser dispatch
    if rel_path.endswith((".yaml", ".yml")) and re.search(r"^apiVersion:", content, re.MULTILINE):
        mods, ics, eds, deployment = parse_k8s(rel_path, content)
        modules.extend(mods)
        interconnects.extend(ics)
        edges.extend(eds)
        if deployment:
            deployments.append(deployment)
        return

    # Terraform — regex extraction only. Locked tuning H.5.a lists
    # `terraform_parser.py` (HCL2 via `python-hcl2`) as a sibling of
    # compose/dockerfile/k8s parsers; deferred to a follow-up commit
    # because (a) it adds a new dep and (b) tf resources are typically
    # infra (S3 buckets, IAM roles) rather than process-allocation
    # targets, so typed `tf_resource_dependency` edges don't help the
    # architect much in the common case. Re-evaluate after a re-ingest
    # confirms (or refutes) the gap.
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


_COMPOSE_NAME_VARIANT = re.compile(r"^(docker-)?compose(\.[a-zA-Z0-9_-]+)?\.ya?ml$", re.IGNORECASE)


def _is_compose_named(filename: str) -> bool:
    """Recognize compose-file variants like `compose.prod.yml` /
    `docker-compose.override.yml`."""
    return bool(_COMPOSE_NAME_VARIANT.match(filename))


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
    from .progress_log import log_done, log_start
    parser = argparse.ArgumentParser(
        prog="hp_architecture_candidates",
        description="Extract Stage-5 architecture-module candidates from scan.json.",
    )
    parser.add_argument("--scan",   required=True, help="Path to intermediate/scan.json")
    parser.add_argument("--codebase", required=True, help="Codebase root (for re-reading file content)")
    parser.add_argument("--output", required=True, help="Output path for architecture-candidates.json")
    args = parser.parse_args(argv)

    intermediate = Path(args.output).parent
    log_start(intermediate, stage="5-prep", agent="architecture_candidates")

    scan_data = json.loads(Path(args.scan).read_text())
    scan = ProjectScan.model_validate(scan_data)
    candidates = extract_candidates(scan, Path(args.codebase))
    write_candidates(candidates, Path(args.output))
    print(f"wrote {args.output} "
          f"({len(candidates.modules)} module candidates, "
          f"{len(candidates.interconnects)} interconnect candidates)")

    log_done(intermediate, stage="5-prep", agent="architecture_candidates",
             modules=len(candidates.modules),
             interconnects=len(candidates.interconnects))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
