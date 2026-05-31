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

    lines.append("---")
    lines.append("")
    lines.append(
        "*Format: 2000 §4.2.5.4 — typical AMS contents. "
        "See [`../../ARCH_DESIGN.md`](../../ARCH_DESIGN.md).*"
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
