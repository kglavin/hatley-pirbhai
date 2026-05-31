# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""ADR markdown emitter.

Renders each Architecture Decision Record into a sidecar markdown file
following Michael Nygard's 2011 format: Context / Decision / Consequences /
Alternatives, plus cross-references to affected model elements.

Output convention: ``adrs/<id-short>.md`` at the project root.
"""

from __future__ import annotations

from ..model import Project, ADR


def adr_filename(adr_id: str) -> str:
    """`adr_001_ble_choice` → `001-ble-choice.md`."""
    short = adr_id.replace("adr_", "").replace("_", "-")
    return f"{short}.md"


def render_adr_markdown(project: Project, adr: ADR) -> str:
    """Produce the markdown body for one ADR (Nygard 2011 format)."""
    lines: list[str] = []
    lines.append(f"# ADR — {adr.title}")
    lines.append("")
    lines.append(f"**ID:** `{adr.id}`")
    lines.append(f"**Status:** {adr.status.value.title()}")
    lines.append(f"**Date:** {adr.date}")
    if adr.author:
        lines.append(f"**Author:** {adr.author}")
    if adr.supersedes:
        lines.append(f"**Supersedes:** [`{adr.supersedes}`](./{adr_filename(adr.supersedes)})")
    lines.append("")
    lines.append("*Generated from `dictionary.yaml`. Do not hand-edit.*")
    lines.append("")

    # CONTEXT (required)
    lines.append("## CONTEXT")
    lines.append("")
    lines.append(adr.context.rstrip())
    lines.append("")

    # DECISION (required)
    lines.append("## DECISION")
    lines.append("")
    lines.append(adr.decision.rstrip())
    lines.append("")

    # CONSEQUENCES (required)
    lines.append("## CONSEQUENCES")
    lines.append("")
    lines.append(adr.consequences.rstrip())
    lines.append("")

    # ALTERNATIVES CONSIDERED (optional)
    if adr.alternatives:
        lines.append("## ALTERNATIVES CONSIDERED")
        lines.append("")
        for alt in adr.alternatives:
            lines.append(f"- {alt}")
        lines.append("")

    # AFFECTS (optional cross-references)
    if adr.affects:
        lines.append("## AFFECTS")
        lines.append("")
        for kind, ids in adr.affects.items():
            if not ids:
                continue
            label = kind.replace("_", " ").title()
            lines.append(f"- **{label}:** " + ", ".join(f"`{i}`" for i in ids))
        lines.append("")

    # CATALOG REFERENCES (modernization #8.3)
    mitre = adr.references_mitre_attack
    cwe   = adr.references_cwe
    compl = adr.references_compliance
    if mitre or cwe or compl:
        lines.append("## CATALOG REFERENCES")
        lines.append("")
        if mitre:
            lines.append("**MITRE ATT&CK:** " + ", ".join(
                f"[`{t}`](https://attack.mitre.org/techniques/{t.replace('.', '/')}/)" for t in mitre))
            lines.append("")
        if cwe:
            lines.append("**CWE:** " + ", ".join(
                f"[`{c}`](https://cwe.mitre.org/data/definitions/{c.split('-')[1]}.html)" for c in cwe))
            lines.append("")
        if compl:
            lines.append("**Compliance:** " + ", ".join(f"`{c}`" for c in compl))
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "*Format: Michael Nygard 2011 — Context / Decision / Consequences / Alternatives. "
        "See [`../toolkit/MODERNIZATION_DESIGN.md`](../toolkit/MODERNIZATION_DESIGN.md).*"
    )
    return "\n".join(lines) + "\n"
