# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Typed docker-compose parser for Stage-5 architecture extraction.

Per locked tuning H.5.a: the previous regex-only compose extractor saw
service *names* and inferred "one shared default network" — it missed
the depends_on graph, port exposures, volume mounts, environment
references, and image-vs-build distinction. Those are the actual
deployment topology the architect agent should arrive at Stage 5
having already decoded.

This parser uses PyYAML to walk compose's typed structure + emits:

- One ModuleCandidate per service (with `image` / `build_context` /
  `ports_exposed` / `volumes_mounted` / `environment_keys` / `replicas` /
  `profiles` / `healthcheck`)
- One InterconnectCandidate per `networks:` block (or one default
  "implicit" interconnect when services share the file's default network)
- CandidateEdges for `depends_on` relationships (typed as
  `compose_depends_on`)
- CandidateEdges for outward port publishes (`compose_port_exposed`, no
  target — external surface)
- CandidateEdges for volume mounts (`compose_volume_mount`)

All candidates carry `deployment_config = Path(source_file).parent.name`
(or the file basename when it lives at the repo root) so the architect
can group per-config when multiple compose files exist.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

import yaml

from .architecture_candidates import (
    CandidateEdge,
    DeploymentConfig,
    InterconnectCandidate,
    ModuleCandidate,
)


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def parse_compose(
    rel_path: str,
    content: str,
) -> tuple[list[ModuleCandidate], list[InterconnectCandidate], list[CandidateEdge], Optional[DeploymentConfig]]:
    """Parse one compose file. Returns (modules, interconnects, edges, deployment_config).

    Falls back to empty results on YAML parse errors — the regex-based
    extractor in architecture_candidates.py is the safety net for malformed
    files."""
    try:
        doc = yaml.safe_load(content)
    except yaml.YAMLError:
        return [], [], [], None
    if not isinstance(doc, dict):
        return [], [], [], None

    deployment_name = _deployment_name(rel_path)
    services_dict = doc.get("services") or {}
    if not isinstance(services_dict, dict):
        return [], [], [], None

    networks_dict = doc.get("networks") or {}

    modules: list[ModuleCandidate] = []
    edges: list[CandidateEdge] = []
    candidate_ids: list[str] = []
    # Track which services live on which networks so we can compute
    # the network → endpoints map for InterconnectCandidates.
    service_networks: dict[str, list[str]] = {}

    for svc_name, raw_svc in services_dict.items():
        if not isinstance(raw_svc, dict):
            continue
        cid = _service_candidate_id(deployment_name, svc_name)
        candidate_ids.append(cid)
        modules.append(_service_to_module(cid, svc_name, raw_svc, rel_path, deployment_name))

        # depends_on → edges
        for dep in _normalize_depends_on(raw_svc.get("depends_on")):
            edges.append(CandidateEdge(
                kind="compose_depends_on",
                source_candidate=cid,
                target_candidate=_service_candidate_id(deployment_name, dep),
                evidence=f"compose {rel_path}: {svc_name} depends_on {dep}",
            ))

        # Outward port publishes → external-surface edge (no target)
        for port_spec in _normalize_ports(raw_svc.get("ports")):
            edges.append(CandidateEdge(
                kind="compose_port_exposed",
                source_candidate=cid,
                target_candidate=None,
                evidence=f"compose {rel_path}: {svc_name} publishes {port_spec}",
            ))

        # Volume mounts → edge per mount
        for vol_spec in _normalize_volumes(raw_svc.get("volumes")):
            edges.append(CandidateEdge(
                kind="compose_volume_mount",
                source_candidate=cid,
                target_candidate=None,
                evidence=f"compose {rel_path}: {svc_name} mounts {vol_spec}",
            ))

        service_networks[cid] = _normalize_networks(raw_svc.get("networks"))

    # Build interconnect candidates:
    #   - If networks: block defines named networks → one per network with
    #     endpoints = services on that network
    #   - Else → one "implicit default" network with all services
    interconnects: list[InterconnectCandidate] = []
    if networks_dict:
        for net_name, net_spec in networks_dict.items():
            if not isinstance(net_spec, (dict, type(None))):
                continue
            endpoints = [
                cid for cid, nets in service_networks.items()
                # default treatment: service joins this network if it lists
                # it explicitly OR if it lists no networks (compose default
                # behavior) AND this is the only / first network
                if net_name in nets
            ]
            if not endpoints and len(networks_dict) == 1:
                # Single network + services don't list networks → all
                # services join the implicit default
                endpoints = list(service_networks.keys())
            internal = bool((net_spec or {}).get("internal"))
            interconnects.append(InterconnectCandidate(
                candidate_id=f"compose-net-{deployment_name}-{net_name}",
                kind_hint="compose_network",
                name_hint=net_name,
                source_file=rel_path,
                endpoints_hinted=endpoints,
                evidence=[f"compose network: {net_name} (deployment={deployment_name})"],
                deployment_config=deployment_name,
                external=not internal,
            ))
    elif len(candidate_ids) >= 2:
        interconnects.append(InterconnectCandidate(
            candidate_id=f"compose-net-{deployment_name}-default",
            kind_hint="compose_network",
            name_hint="default compose network",
            source_file=rel_path,
            endpoints_hinted=candidate_ids,
            evidence=[f"implicit default network between {len(candidate_ids)} services "
                      f"(deployment={deployment_name})"],
            deployment_config=deployment_name,
            external=True,
        ))

    deployment = DeploymentConfig(
        name=deployment_name,
        source_file=rel_path,
        kind="compose",
        candidate_ids=candidate_ids,
    )
    return modules, interconnects, edges, deployment


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

def _deployment_name(rel_path: str) -> str:
    """Short, stable name for the deployment configuration this compose
    file defines.

    Conventions: prefer the immediate parent directory name when it's
    informative (e.g., `deployments/deploy-test/compose.yml` →
    `deploy-test`); fall back to the file's stem at the repo root (e.g.,
    `compose.yml` → `compose`)."""
    p = Path(rel_path)
    parent = p.parent.name
    if parent and parent not in {".", "compose", "docker", "deploy"}:
        return _slug(parent)
    return _slug(p.stem)


_SLUG_REPLACE = re.compile(r"[^a-z0-9-]+")


def _slug(s: str) -> str:
    s = s.lower().replace("_", "-")
    s = _SLUG_REPLACE.sub("-", s).strip("-")
    return s or "default"


def _service_candidate_id(deployment_name: str, service_name: str) -> str:
    return f"compose-{deployment_name}-{_slug(service_name)}"


def _service_to_module(
    cid: str,
    svc_name: str,
    raw_svc: dict[str, Any],
    rel_path: str,
    deployment_name: str,
) -> ModuleCandidate:
    image = raw_svc.get("image")
    if not isinstance(image, str):
        image = None
    build = raw_svc.get("build")
    build_context: Optional[str] = None
    if isinstance(build, str):
        build_context = build
    elif isinstance(build, dict):
        build_context = build.get("context") if isinstance(build.get("context"), str) else None

    ports_norm = _normalize_ports(raw_svc.get("ports"))
    volumes_norm = _normalize_volumes(raw_svc.get("volumes"))
    env_keys = _normalize_environment_keys(raw_svc.get("environment"))
    healthcheck = isinstance(raw_svc.get("healthcheck"), dict)
    profiles = _normalize_profiles(raw_svc.get("profiles"))
    replicas = _extract_replicas(raw_svc)

    evidence: list[str] = [f"compose service: {svc_name}"]
    if image:
        evidence.append(f"image: {image}")
    if build_context:
        evidence.append(f"build: {build_context}")

    return ModuleCandidate(
        candidate_id=cid,
        kind_hint="container",
        name_hint=svc_name,
        source_file=rel_path,
        evidence=evidence,
        deployment_config=deployment_name,
        image=image,
        build_context=build_context,
        ports_exposed=ports_norm,
        volumes_mounted=volumes_norm,
        environment_keys=env_keys,
        replicas=replicas,
        profiles=profiles,
        healthcheck=healthcheck,
    )


def _normalize_depends_on(raw: Any) -> list[str]:
    """Compose accepts depends_on as a list or as a dict (with condition).
    Normalize to a flat list of service names."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if isinstance(x, str)]
    if isinstance(raw, dict):
        return [str(k) for k in raw.keys()]
    return []


def _normalize_ports(raw: Any) -> list[str]:
    """Ports can be a list of strings (`"8080:80"`) or list of dicts
    (target/published/protocol). Normalize to display strings."""
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for entry in raw:
        if isinstance(entry, str):
            out.append(entry)
        elif isinstance(entry, dict):
            target = entry.get("target")
            published = entry.get("published")
            if published and target:
                out.append(f"{published}:{target}")
            elif target:
                out.append(str(target))
    return out


def _normalize_volumes(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for entry in raw:
        if isinstance(entry, str):
            out.append(entry)
        elif isinstance(entry, dict):
            src = entry.get("source")
            tgt = entry.get("target")
            if src and tgt:
                out.append(f"{src}:{tgt}")
            elif tgt:
                out.append(str(tgt))
    return out


def _normalize_environment_keys(raw: Any) -> list[str]:
    """Compose environment can be a list (`["FOO=bar", "BAZ"]`) or a dict
    (`{FOO: bar, BAZ: ""}`). Return just the keys (values often contain
    secrets / config we don't want to surface here)."""
    if isinstance(raw, dict):
        return sorted(str(k) for k in raw.keys())
    if isinstance(raw, list):
        out: list[str] = []
        for entry in raw:
            if isinstance(entry, str):
                name = entry.split("=", 1)[0]
                if name:
                    out.append(name)
        return sorted(set(out))
    return []


def _normalize_networks(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(n) for n in raw if isinstance(n, str)]
    if isinstance(raw, dict):
        return [str(k) for k in raw.keys()]
    return []


def _normalize_profiles(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(p) for p in raw if isinstance(p, str)]


def _extract_replicas(raw_svc: dict[str, Any]) -> int:
    deploy = raw_svc.get("deploy")
    if not isinstance(deploy, dict):
        return 1
    r = deploy.get("replicas")
    if isinstance(r, int) and r > 0:
        return r
    return 1
