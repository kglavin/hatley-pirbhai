# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Typed Dockerfile parser for Stage-5 architecture extraction.

Per locked tuning H.5.a: the previous Dockerfile extractor only captured
`FROM` lines. A Dockerfile carries substantial architectural signal we
should harvest:

- `FROM` — base image, hints `module_kind` (a `node:22-alpine` is
  software in-tree; `nginx:alpine` is software pre-built off-the-shelf)
- `EXPOSE` — external network surface (which ports this container offers)
- `ENV` — config-via-env pattern (architect rationale; H.2 "why")
- `CMD` / `ENTRYPOINT` — process role hint (server vs cli vs migration job)
- `HEALTHCHECK` — liveness behavior, hints at process kind
- `WORKDIR` — where build context lives in the image
- `LABEL` — author-provided rationale (`org.opencontainers.image.title` etc.)

Pure text/regex parse — Dockerfiles aren't YAML so no PyYAML; no new
deps. Returns enrichment fields applied onto the ModuleCandidate
produced by architecture_candidates.py for the matching Dockerfile.
"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field


class DockerfileEvidence(BaseModel):
    """Structural facts extracted from a single Dockerfile.

    The dispatcher in architecture_candidates.py overlays these onto the
    candidate's `image` / `ports_exposed` / `environment_keys` /
    `evidence` / `healthcheck` fields (so the architect agent reads them
    as part of the ModuleCandidate, not as a sidecar)."""

    from_image: Optional[str] = None
    exposed_ports: list[str] = Field(default_factory=list)
    env_keys: list[str] = Field(default_factory=list)
    cmd: Optional[str] = None
    entrypoint: Optional[str] = None
    workdir: Optional[str] = None
    healthcheck: bool = False
    labels: dict[str, str] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────
# Patterns
# ─────────────────────────────────────────────────────────────────────

# `FROM image[:tag] [AS stage]` — capture the image (the last FROM in a
# multi-stage build is what actually runs in production).
_FROM_LINE = re.compile(r"^\s*FROM\s+(\S+)(?:\s+AS\s+\S+)?\s*$", re.MULTILINE | re.IGNORECASE)
_EXPOSE_LINE = re.compile(r"^\s*EXPOSE\s+(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
# ENV supports `ENV KEY=value` or `ENV KEY value` or multi-line `ENV K1=v1 K2=v2`
_ENV_LINE = re.compile(r"^\s*ENV\s+(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
_CMD_LINE = re.compile(r"^\s*CMD\s+(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
_ENTRYPOINT_LINE = re.compile(r"^\s*ENTRYPOINT\s+(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
_HEALTHCHECK_LINE = re.compile(r"^\s*HEALTHCHECK\s+", re.MULTILINE | re.IGNORECASE)
_WORKDIR_LINE = re.compile(r"^\s*WORKDIR\s+(\S+)\s*$", re.MULTILINE | re.IGNORECASE)
_LABEL_LINE = re.compile(r"^\s*LABEL\s+(.+?)\s*$", re.MULTILINE | re.IGNORECASE)

# ENV key parsing — `KEY=value KEY2=value2` or `KEY value`
_ENV_KEY_EQUALS = re.compile(r"([A-Z_][A-Z0-9_]*)\s*=")
_ENV_KEY_SPACE = re.compile(r"^([A-Z_][A-Z0-9_]*)\s+")


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def parse_dockerfile(content: str) -> DockerfileEvidence:
    """Extract typed fields from a Dockerfile.

    Pure-text parse — tolerates malformed Dockerfiles (returns partial
    results rather than raising)."""
    ev = DockerfileEvidence()

    from_matches = _FROM_LINE.findall(content)
    if from_matches:
        # Last FROM wins (multi-stage builds — the production stage is last)
        ev.from_image = from_matches[-1]

    for raw in _EXPOSE_LINE.findall(content):
        # EXPOSE can list multiple ports on one line: "EXPOSE 80 443 8080/tcp"
        for token in raw.split():
            ev.exposed_ports.append(token)

    env_keys: list[str] = []
    for raw in _ENV_LINE.findall(content):
        # `ENV K=v K2=v2` — multiple keys on one line
        eq_keys = _ENV_KEY_EQUALS.findall(raw)
        if eq_keys:
            env_keys.extend(eq_keys)
        else:
            # `ENV KEY value` form
            m = _ENV_KEY_SPACE.match(raw)
            if m:
                env_keys.append(m.group(1))
    ev.env_keys = sorted(set(env_keys))

    cmd_matches = _CMD_LINE.findall(content)
    if cmd_matches:
        ev.cmd = cmd_matches[-1].strip()
    ent_matches = _ENTRYPOINT_LINE.findall(content)
    if ent_matches:
        ev.entrypoint = ent_matches[-1].strip()
    wd_matches = _WORKDIR_LINE.findall(content)
    if wd_matches:
        ev.workdir = wd_matches[-1]
    ev.healthcheck = bool(_HEALTHCHECK_LINE.search(content))

    for raw in _LABEL_LINE.findall(content):
        # `LABEL key=value key2=value2` — simple kv parse, skipping
        # quoted-multi-line cases we can't handle without a real
        # tokenizer.
        for match in re.finditer(r'([\w.-]+)\s*=\s*"([^"]*)"', raw):
            ev.labels[match.group(1)] = match.group(2)

    return ev
