"""AMS + AIS markdown emitters.

Renders each Architecture Module Specification (AMS) and Architecture
Interconnect Specification (AIS) into a sidecar markdown file following
the 2000 §4.2.5.4 / §4.2.6.2 typical-content layout.

Output convention:
  ``architecture/specs/<module-id-short>.md``     (AMS)
  ``architecture/specs/interconnects/<interconnect-id-short>.md``  (AIS)

Where ``<id-short>`` strips the ``am_`` / ``ai_`` prefix and converts
``_`` → ``-`` (matches the existing PSPEC subdir convention).
"""

from __future__ import annotations

from ..model import (
    Project, ArchModule, ArchInterconnect, ArchModuleSpec, ArchInterconnectSpec,
    ArchModuleConstraints,
)


def ams_subdir_name(module_id: str) -> str:
    """`am_main_controller` → `main-controller`."""
    return module_id.replace("am_", "").replace("_", "-")


def ais_subdir_name(interconnect_id: str) -> str:
    """`ai_ble` → `ble`."""
    return interconnect_id.replace("ai_", "").replace("_", "-")


def _constraints_lines(c: ArchModuleConstraints | None) -> list[str]:
    if c is None:
        return []
    lines: list[str] = []
    fields = [
        ("Reliability", c.reliability),
        ("Maintainability", c.maintainability),
        ("Safety", c.safety),
        ("Physical", c.physical),
        ("Design", c.design),
        ("Manufacturability", c.manufacturability),
        ("Cost", c.cost),
        ("Schedule", c.schedule),
    ]
    for name, value in fields:
        if value:
            lines.append(f"- **{name}:** {value}")
    return lines


def render_ams_markdown(project: Project, ams: ArchModuleSpec) -> str:
    """Produce the markdown body for one AMS (2000 §4.2.5.4 typical contents)."""
    module = project.architecture_modules.get(ams.parent_module)
    if module is None:
        raise ValueError(f"AMS {ams.id!r} references unknown module {ams.parent_module!r}")

    lines: list[str] = []
    title = module.name
    if module.module_number:
        title = f"{title} ({module.module_number})"
    lines.append(f"# AMS — {title}")
    lines.append("")
    lines.append(f"**Module:** [`{module.id}`](../../dictionary.yaml)")
    lines.append("*Generated from `dictionary.yaml`. Do not hand-edit.*")
    lines.append("")

    # DESCRIPTION (required)
    lines.append("## DESCRIPTION")
    lines.append("")
    lines.append(ams.description.rstrip())
    lines.append("")

    # CROSS-REFERENCE (allocation — derived from the module, not the spec)
    lines.append("## CROSS-REFERENCE (allocation)")
    lines.append("")
    rows: list[tuple[str, str]] = []
    for pid in module.allocated_processes:
        rows.append((pid, "process"))
    for pid in module.allocated_cspecs:
        rows.append((pid, "process (state-rich; CSPEC lives here)"))
    for sid in module.allocated_stores:
        rows.append((sid, "data store"))
    if rows:
        lines.append("| Requirements component | Kind |")
        lines.append("|---|---|")
        for rid, kind in rows:
            lines.append(f"| `{rid}` | {kind} |")
    else:
        lines.append("*(none — module has no allocations yet)*")
    lines.append("")

    # DESIGN RATIONALE (optional)
    if ams.design_rationale:
        lines.append("## DESIGN RATIONALE")
        lines.append("")
        lines.append(ams.design_rationale.rstrip())
        lines.append("")

    # DESIGN JUSTIFICATION (optional)
    if ams.design_justification:
        lines.append("## DESIGN JUSTIFICATION")
        lines.append("")
        lines.append(ams.design_justification.rstrip())
        lines.append("")

    # REQUIRED CONSTRAINTS (optional)
    cons = _constraints_lines(ams.required_constraints)
    if cons:
        lines.append("## REQUIRED CONSTRAINTS")
        lines.append("")
        lines.extend(cons)
        lines.append("")

    # INTERFACES (optional)
    if ams.interfaces:
        lines.append("## INTERFACES")
        lines.append("")
        lines.append(ams.interfaces.rstrip())
        lines.append("")

    # VERIFICATION (optional — modernization #25)
    v = ams.verification
    if v is not None:
        lines.append("## VERIFICATION")
        lines.append("")
        methods = ", ".join(m.value for m in v.methods)
        lines.append(f"- **Methods:** {methods}")
        if v.test_suite:
            lines.append(f"- **Test suite:** [`{v.test_suite}`](../../../{v.test_suite})")
        if v.coverage_target is not None:
            lines.append(f"- **Coverage target:** {v.coverage_target}%")
        if v.validation_scenarios:
            lines.append("- **Validation scenarios:**")
            for s in v.validation_scenarios:
                lines.append(f"  - {s}")
        lines.append("")

    # BUDGETS (optional — modernization #21)
    module_budgets = project.budgets_for_module(module.id)
    if module_budgets:
        lines.append("## BUDGETS (allocations to this module)")
        lines.append("")
        lines.append("| Budget | Unit | This module | System target | Reserve |")
        lines.append("|---|---|---:|---:|---:|")
        for b in module_budgets:
            allocation = b.allocations.get(module.id, 0)
            lines.append(
                f"| `{b.id}` — {b.name} | {b.unit} | {allocation} "
                f"| {b.system_target} | {b.system_reserve} |"
            )
        lines.append("")

    # TPMs (optional — modernization #22)
    module_tpms = []
    for b in module_budgets:
        module_tpms.extend(project.tpms_for_budget(b.id))
    if module_tpms:
        lines.append("## TPMs (tracking this module's budgets)")
        lines.append("")
        lines.append("| TPM | Unit | Current | Growth allowance | Threshold |")
        lines.append("|---|---|---:|---:|---:|")
        for t in module_tpms:
            lines.append(
                f"| `{t.id}` — {t.name} | {t.unit} | {t.current_estimate} "
                f"| {t.growth_allowance} | {t.threshold} |"
            )
        lines.append("")

    # OBSERVABILITY (optional — modernization #1 + #33)
    obs = module.observability
    if obs is not None:
        lines.append("## OBSERVABILITY")
        lines.append("")
        if obs.metrics:
            lines.append("**Metrics:**")
            lines.append("")
            for m in obs.metrics:
                unit = f" ({m.unit})" if m.unit else ""
                desc = f" — {m.description}" if m.description else ""
                lines.append(f"- `{m.name}` *{m.kind.value}*{unit}{desc}")
            lines.append("")
        if obs.traces:
            lines.append("**Traces:**")
            lines.append("")
            for t in obs.traces:
                desc = f" — {t.description}" if t.description else ""
                lines.append(f"- `{t.span}`{desc}")
            lines.append("")
        if obs.logs:
            lines.append("**Log categories:**")
            lines.append("")
            for log in obs.logs:
                lines.append(f"- `{log.category}` *(level: {log.level})*")
            lines.append("")
        if obs.alerts:
            lines.append("**Alerts:**")
            lines.append("")
            for a in obs.alerts:
                runbook_link = f" → [runbook](../../{a.runbook})" if a.runbook else ""
                lines.append(f"- `{a.name}` *({a.severity.value})* — when `{a.when}`{runbook_link}")
            lines.append("")

    # SLOs that apply to this module (modernization #32)
    module_slos = project.slos_for_module(module.id)
    if module_slos:
        lines.append("## SLOs (apply to this module)")
        lines.append("")
        lines.append("| SLO | Target | Window | Error budget |")
        lines.append("|---|---:|---|---:|")
        for slo in module_slos:
            lines.append(
                f"| [`{slo.id}`](../slos.md#{slo.id}) — {slo.name} "
                f"| {slo.target} {slo.sli.unit or ''} | {slo.window} | {slo.error_budget_pct}% |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "*Format: 2000 §4.2.5.4 — typical AMS contents. "
        "See [`../../ARCH_DESIGN.md`](../../ARCH_DESIGN.md).*"
    )
    return "\n".join(lines) + "\n"


def render_slos_summary(project: Project) -> str:
    """Project-level SLO summary (modernization #32).

    One markdown page listing every SLO with its cross-references to
    TPMs (#22), modules, and the runbook to follow when the error
    budget burns."""
    if not project.service_level_objectives:
        return ""

    lines: list[str] = []
    lines.append(f"# {project.project} — Service Level Objectives")
    lines.append("")
    lines.append("*Generated from `dictionary.yaml`. Do not hand-edit.*")
    lines.append("")
    lines.append(
        "SLOs commit external promises about the runtime behavior of the "
        "architecture model. Each declares the SLI being measured, the "
        "target value, the rolling window, and the error budget that gates "
        "release decisions (Google SRE Book 2016)."
    )
    lines.append("")

    for slo in project.all_slos():
        lines.append(f"## {slo.id}")
        lines.append("")
        lines.append(f"**{slo.name}**")
        lines.append("")
        lines.append(f"- **Target:** {slo.target} {slo.sli.unit or ''}")
        lines.append(f"- **Window:** {slo.window}")
        lines.append(f"- **Error budget:** {slo.error_budget_pct}%")
        if slo.sla:
            lines.append(f"- **SLA (customer-facing):** {slo.sla}")
        lines.append("")
        lines.append("### SLI")
        lines.append("")
        if slo.sli.description:
            lines.append(slo.sli.description.rstrip())
            lines.append("")
        lines.append("```")
        lines.append(slo.sli.query)
        lines.append("```")
        lines.append("")
        if slo.applies_to:
            lines.append("### Applies to")
            lines.append("")
            for kind, ids in slo.applies_to.items():
                if not ids:
                    continue
                label = kind.replace("_", " ").title()
                lines.append(f"- **{label}:** " + ", ".join(f"`{i}`" for i in ids))
            lines.append("")
        if slo.derives_from_tpm:
            lines.append(f"### Derived from TPM")
            lines.append("")
            tpm = project.tpms.get(slo.derives_from_tpm)
            if tpm is not None:
                lines.append(f"[`{slo.derives_from_tpm}`](../dictionary.yaml) — "
                             f"{tpm.name} (current {tpm.current_estimate} {tpm.unit})")
            else:
                lines.append(f"`{slo.derives_from_tpm}` *(not in dictionary)*")
            lines.append("")
        if slo.runbook_on_burn:
            lines.append(f"### Runbook on budget burn")
            lines.append("")
            lines.append(f"[`{slo.runbook_on_burn}`](../{slo.runbook_on_burn})")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(
        "*See [`../toolkit/MODERNIZATION_DESIGN.md`](../toolkit/MODERNIZATION_DESIGN.md) §4.3 — SLI/SLO/SLA chain.*"
    )
    return "\n".join(lines) + "\n"


def render_ais_markdown(project: Project, ais: ArchInterconnectSpec) -> str:
    """Produce the markdown body for one AIS (2000 §4.2.6.2)."""
    ic = project.architecture_interconnects.get(ais.parent_interconnect)
    if ic is None:
        raise ValueError(f"AIS {ais.id!r} references unknown interconnect {ais.parent_interconnect!r}")

    lines: list[str] = []
    lines.append(f"# AIS — {ic.name}")
    lines.append("")
    lines.append(f"**Interconnect:** [`{ic.id}`](../../../dictionary.yaml)")
    lines.append(f"**Endpoints:** {', '.join(f'`{e}`' for e in ic.endpoints)}")
    lines.append("*Generated from `dictionary.yaml`. Do not hand-edit.*")
    lines.append("")

    # DESCRIPTION
    lines.append("## DESCRIPTION")
    lines.append("")
    lines.append(ais.description.rstrip())
    lines.append("")

    # CARRIES (architecture flows on this channel)
    if ic.carries:
        lines.append("## CARRIES")
        lines.append("")
        lines.append("Architecture flows allocated to this channel:")
        lines.append("")
        for af_id in ic.carries:
            af = project.architecture_flows.get(af_id)
            if af is not None:
                lines.append(f"- `{af.id}` — {af.name} ({af.kind.value})")
            else:
                lines.append(f"- `{af_id}` *(not in dictionary)*")
        lines.append("")

    # PROTOCOL STANDARD (optional)
    if ais.protocol_standard:
        lines.append("## PROTOCOL STANDARD")
        lines.append("")
        lines.append(ais.protocol_standard.rstrip())
        lines.append("")

    # DESIGN RATIONALE
    if ais.design_rationale:
        lines.append("## DESIGN RATIONALE")
        lines.append("")
        lines.append(ais.design_rationale.rstrip())
        lines.append("")

    # DESIGN JUSTIFICATION
    if ais.design_justification:
        lines.append("## DESIGN JUSTIFICATION")
        lines.append("")
        lines.append(ais.design_justification.rstrip())
        lines.append("")

    # REQUIRED CONSTRAINTS
    cons = _constraints_lines(ais.required_constraints)
    if cons:
        lines.append("## REQUIRED CONSTRAINTS")
        lines.append("")
        lines.extend(cons)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "*Format: 2000 §4.2.6.2 — typical AIS contents. "
        "See [`../../../ARCH_DESIGN.md`](../../../ARCH_DESIGN.md).*"
    )
    return "\n".join(lines) + "\n"
