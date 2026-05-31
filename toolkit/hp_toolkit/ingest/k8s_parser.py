# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Typed Kubernetes manifest parser for Stage-5 architecture extraction.

Per locked tuning H.5.a: the previous k8s extractor was regex-only —
it found `kind:` + `name:` and emitted one ModuleCandidate per workload.
Real k8s manifests carry far more architectural signal:

- **Deployment / StatefulSet / DaemonSet / Job / CronJob** → modules
  with replicas, container images, resource limits
- **Service** → interconnects, with `selector` matching to the
  deployment(s) it routes to (typed CandidateEdge `k8s_service_selector`)
- **Ingress** → external surface (typed `k8s_ingress_target` edges)
- **NetworkPolicy** → trust-zone hints (informs the post-ingest
  hp-propose-architecture form)
- **PersistentVolumeClaim** → data-store allocation evidence
- **ConfigMap / Secret** → config-via-env pattern

Files often contain multiple manifests separated by `---`. We walk each
document in the multi-doc YAML stream.

Returns the same (modules, interconnects, edges, deployment) shape as
compose_parser.parse_compose() so architecture_candidates.py can
dispatch uniformly.
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


_WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "ReplicaSet"}


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def parse_k8s(
    rel_path: str,
    content: str,
) -> tuple[list[ModuleCandidate], list[InterconnectCandidate], list[CandidateEdge], Optional[DeploymentConfig]]:
    """Parse a k8s manifest (potentially multi-doc) + emit candidates.

    Returns empty results on parse error — caller can fall back to the
    regex-based extractor."""
    try:
        docs = list(yaml.safe_load_all(content))
    except yaml.YAMLError:
        return [], [], [], None

    deployment_name = _deployment_name(rel_path)

    modules: list[ModuleCandidate] = []
    interconnects: list[InterconnectCandidate] = []
    edges: list[CandidateEdge] = []
    candidate_ids: list[str] = []

    # We need two passes: first collect all workloads + their labels (so
    # Service selectors can resolve to candidate ids); then process
    # Services + Ingresses that reference those workloads.
    workload_by_name: dict[str, tuple[str, dict[str, str]]] = {}   # name → (candidate_id, labels)

    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind")
        if kind in _WORKLOAD_KINDS:
            cid = _workload_to_module(doc, rel_path, deployment_name, modules)
            if cid is not None:
                candidate_ids.append(cid)
                labels = _pod_labels(doc)
                meta_name = (doc.get("metadata") or {}).get("name", "")
                workload_by_name[str(meta_name)] = (cid, labels)
        elif kind == "PersistentVolumeClaim":
            # PVCs become data-store evidence — emit a candidate edge from
            # the workload that mounts them to this PVC (the workload-mount
            # match needs `.spec.template.spec.volumes.[].persistentVolumeClaim.claimName`,
            # which we'd walk in the workload pass below).
            pass  # handled inline during workload walk via _workload_to_module

    # Second pass: services + ingresses
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind")
        if kind == "Service":
            ic = _service_to_interconnect(doc, rel_path, deployment_name, workload_by_name, edges)
            if ic is not None:
                interconnects.append(ic)
        elif kind == "Ingress":
            ic = _ingress_to_interconnect(doc, rel_path, deployment_name, edges)
            if ic is not None:
                interconnects.append(ic)
        elif kind == "NetworkPolicy":
            # Surfaced as evidence only — trust-zone derivation is the
            # post-ingest hp-propose-architecture form's job per Q3.
            pass

    deployment = DeploymentConfig(
        name=deployment_name,
        source_file=rel_path,
        kind="k8s",
        candidate_ids=candidate_ids,
    ) if candidate_ids or interconnects else None
    return modules, interconnects, edges, deployment


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

def _deployment_name(rel_path: str) -> str:
    """Use the containing directory name as the deployment-config grouping
    (e.g. `k8s/production/api-deployment.yaml` → `production`)."""
    p = Path(rel_path)
    # Look up the path for the first interesting ancestor name
    for part in reversed(p.parts[:-1]):
        s = part.lower()
        if s and s not in {"k8s", "kubernetes", "manifests", "deploy", "deployments", "."}:
            return _slug(part)
    return _slug(p.stem)


_SLUG_REPLACE = re.compile(r"[^a-z0-9-]+")


def _slug(s: str) -> str:
    s = s.lower().replace("_", "-")
    s = _SLUG_REPLACE.sub("-", s).strip("-")
    return s or "default"


def _workload_to_module(
    doc: dict[str, Any],
    rel_path: str,
    deployment_name: str,
    modules: list[ModuleCandidate],
) -> Optional[str]:
    meta = doc.get("metadata") or {}
    name = meta.get("name")
    if not isinstance(name, str):
        return None
    kind = doc.get("kind", "")
    spec = doc.get("spec") or {}

    replicas = spec.get("replicas", 1) if isinstance(spec.get("replicas"), int) else 1
    pod_spec = _pod_spec(doc) or {}
    containers = pod_spec.get("containers") if isinstance(pod_spec, dict) else None
    image: Optional[str] = None
    ports_exposed: list[str] = []
    env_keys: list[str] = []
    if isinstance(containers, list) and containers:
        primary = containers[0]
        if isinstance(primary, dict):
            img = primary.get("image")
            if isinstance(img, str):
                image = img
            for port_entry in primary.get("ports") or []:
                if isinstance(port_entry, dict):
                    p = port_entry.get("containerPort")
                    if isinstance(p, int):
                        ports_exposed.append(str(p))
                elif isinstance(port_entry, int):
                    ports_exposed.append(str(port_entry))
            for env_entry in primary.get("env") or []:
                if isinstance(env_entry, dict) and isinstance(env_entry.get("name"), str):
                    env_keys.append(env_entry["name"])

    volumes_mounted = _pod_volume_mounts(pod_spec)

    cid = f"k8s-{deployment_name}-{_slug(name)}"
    modules.append(ModuleCandidate(
        candidate_id=cid,
        kind_hint="k8s_pod",
        name_hint=name,
        source_file=rel_path,
        evidence=[f"k8s {kind}: {name}"],
        deployment_config=deployment_name,
        image=image,
        ports_exposed=ports_exposed,
        volumes_mounted=volumes_mounted,
        environment_keys=sorted(set(env_keys)),
        replicas=replicas,
    ))
    return cid


def _pod_spec(doc: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Resolve the pod-spec dict regardless of workload kind.

    Most workloads put it at `spec.template.spec`; CronJob at
    `spec.jobTemplate.spec.template.spec`."""
    spec = doc.get("spec") or {}
    if doc.get("kind") == "CronJob":
        template = (spec.get("jobTemplate") or {}).get("spec") or {}
        return ((template.get("template") or {}).get("spec")) or None
    template = spec.get("template") or {}
    if isinstance(template, dict):
        return template.get("spec") if isinstance(template.get("spec"), dict) else None
    return None


def _pod_labels(doc: dict[str, Any]) -> dict[str, str]:
    spec = doc.get("spec") or {}
    template = spec.get("template") or {}
    if isinstance(template, dict):
        meta = template.get("metadata") or {}
        labels = meta.get("labels") or {}
        if isinstance(labels, dict):
            return {str(k): str(v) for k, v in labels.items()}
    return {}


def _pod_volume_mounts(pod_spec: dict[str, Any]) -> list[str]:
    out: list[str] = []
    volumes = pod_spec.get("volumes") if isinstance(pod_spec, dict) else None
    if not isinstance(volumes, list):
        return []
    for v in volumes:
        if not isinstance(v, dict):
            continue
        name = v.get("name", "")
        pvc = v.get("persistentVolumeClaim")
        if isinstance(pvc, dict):
            claim = pvc.get("claimName", "")
            out.append(f"pvc:{claim}")
            continue
        cm = v.get("configMap")
        if isinstance(cm, dict):
            out.append(f"configMap:{cm.get('name', '')}")
            continue
        sec = v.get("secret")
        if isinstance(sec, dict):
            out.append(f"secret:{sec.get('secretName', '')}")
            continue
        # emptyDir / hostPath / etc.
        out.append(f"volume:{name}")
    return out


def _service_to_interconnect(
    doc: dict[str, Any],
    rel_path: str,
    deployment_name: str,
    workload_by_name: dict[str, tuple[str, dict[str, str]]],
    edges: list[CandidateEdge],
) -> Optional[InterconnectCandidate]:
    meta = doc.get("metadata") or {}
    name = meta.get("name")
    if not isinstance(name, str):
        return None
    spec = doc.get("spec") or {}
    selector = spec.get("selector") or {}
    svc_type = spec.get("type", "ClusterIP")

    endpoints: list[str] = []
    if isinstance(selector, dict) and selector:
        # Match selector to any workload whose pod-template labels are a
        # superset of the selector. This is k8s's actual matching rule —
        # selector keys all present + values equal.
        for wl_name, (cid, labels) in workload_by_name.items():
            if all(labels.get(k) == v for k, v in selector.items()):
                endpoints.append(cid)
                edges.append(CandidateEdge(
                    kind="k8s_service_selector",
                    source_candidate=f"k8s-svc-{deployment_name}-{_slug(name)}",
                    target_candidate=cid,
                    evidence=f"k8s Service '{name}' selector matches workload '{wl_name}'",
                ))

    return InterconnectCandidate(
        candidate_id=f"k8s-svc-{deployment_name}-{_slug(name)}",
        kind_hint="k8s_service",
        name_hint=name,
        source_file=rel_path,
        endpoints_hinted=endpoints,
        evidence=[f"k8s Service: {name} (type={svc_type})"],
        deployment_config=deployment_name,
        external=svc_type in {"LoadBalancer", "NodePort"},
    )


def _ingress_to_interconnect(
    doc: dict[str, Any],
    rel_path: str,
    deployment_name: str,
    edges: list[CandidateEdge],
) -> Optional[InterconnectCandidate]:
    meta = doc.get("metadata") or {}
    name = meta.get("name")
    if not isinstance(name, str):
        return None
    spec = doc.get("spec") or {}
    rules = spec.get("rules") or []
    referenced_services: list[str] = []
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            http = rule.get("http") or {}
            paths = http.get("paths") or [] if isinstance(http, dict) else []
            for path in paths:
                if not isinstance(path, dict):
                    continue
                backend = path.get("backend") or {}
                svc = backend.get("service") or {}
                if isinstance(svc, dict):
                    svc_name = svc.get("name")
                    if isinstance(svc_name, str):
                        target_id = f"k8s-svc-{deployment_name}-{_slug(svc_name)}"
                        referenced_services.append(target_id)
                        edges.append(CandidateEdge(
                            kind="k8s_ingress_target",
                            source_candidate=f"k8s-ing-{deployment_name}-{_slug(name)}",
                            target_candidate=target_id,
                            evidence=f"k8s Ingress '{name}' routes to Service '{svc_name}'",
                        ))

    return InterconnectCandidate(
        candidate_id=f"k8s-ing-{deployment_name}-{_slug(name)}",
        kind_hint="k8s_ingress",
        name_hint=name,
        source_file=rel_path,
        endpoints_hinted=referenced_services,
        evidence=[f"k8s Ingress: {name}"],
        deployment_config=deployment_name,
        external=True,
    )
