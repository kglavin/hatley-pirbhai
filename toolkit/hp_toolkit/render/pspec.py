"""PSPEC markdown emitter.

Renders each PSPEC into a sidecar markdown file following 2000 Fig 4.46
(INPUTS / OUTPUTS / TRANSFORMATION) plus optional COMPUTATIONAL CONSTRAINTS
(2000 §4.3.3.9) and COMMENTS (1988 §13.5).

Output convention: ``01-level1/pspecs/<process-id-short>.md`` where
``<process-id-short>`` strips the ``proc_`` prefix and converts ``_`` → ``-``
(matching the existing CSPEC subdir convention).
"""

from __future__ import annotations

from ..model import Project, PSpec, Flow, PSpecStyle


def _process_inputs(project: Project, process_id: str) -> list[Flow]:
    result: list[Flow] = []
    for f in project.all_flows():
        if f.refined_target == process_id:
            result.append(f)
        elif f.target == process_id and not f.refined_target:
            result.append(f)
    return result


def _process_outputs(project: Project, process_id: str) -> list[Flow]:
    result: list[Flow] = []
    for f in project.all_flows():
        if f.refined_source == process_id:
            result.append(f)
        elif f.source == process_id and not f.refined_source:
            result.append(f)
    return result


def pspec_subdir_name(process_id: str) -> str:
    """`proc_acquire_tension` → `acquire-tension`."""
    return process_id.replace("proc_", "").replace("_", "-")


def render_pspec_markdown(project: Project, pspec: PSpec) -> str:
    """Produce the markdown body for one PSPEC."""
    parent = project.entity(pspec.parent_process)
    inputs = _process_inputs(project, pspec.parent_process)
    outputs = _process_outputs(project, pspec.parent_process)

    lines: list[str] = []
    lines.append(f"# PSPEC — {parent.label}")
    lines.append("")
    lines.append(
        f"**Process:** [`{parent.id}`](../../dictionary.yaml) "
        f"(level-{int(parent.level)} DFD)"
    )
    lines.append("*Generated from `dictionary.yaml`. Do not hand-edit.*")
    lines.append("")

    # INPUTS
    lines.append("## INPUTS")
    lines.append("")
    if inputs:
        lines.append("| Flow | From | Medium |")
        lines.append("|---|---|---|")
        for f in inputs:
            # Effective source after refinement
            src = f.refined_source or f.source if f.refined_target == parent.id else f.source
            lines.append(f"| `{f.id}` — {f.label} | `{src}` | {f.medium or '—'} |")
    else:
        lines.append("*(none — process has no incoming flows)*")
    lines.append("")

    # OUTPUTS
    lines.append("## OUTPUTS")
    lines.append("")
    if outputs:
        lines.append("| Flow | To |")
        lines.append("|---|---|")
        for f in outputs:
            tgt = f.refined_target or f.target if f.refined_source == parent.id else f.target
            lines.append(f"| `{f.id}` — {f.label} | `{tgt}` |")
    else:
        lines.append("*(none — process has no outgoing flows)*")
    lines.append("")

    # TRANSFORMATION
    style_label = pspec.transformation.style.value
    lines.append(f"## TRANSFORMATION ({style_label})")
    lines.append("")
    if pspec.transformation.style == PSpecStyle.TEXTUAL:
        # Render as a fenced block to preserve indentation.
        lines.append("```")
        lines.append(pspec.transformation.body.rstrip())
        lines.append("```")
    else:
        # Equation / table / diagram / mixed — render the body as-is
        # (author is responsible for valid markdown in those cases;
        # diagram bodies typically link or embed a sidecar SVG).
        lines.append(pspec.transformation.body.rstrip())
    lines.append("")

    # COMPUTATIONAL CONSTRAINTS (optional)
    cc = pspec.computational_constraints
    if cc and (cc.frequency or cc.accuracy or cc.timing):
        lines.append("## COMPUTATIONAL CONSTRAINTS")
        lines.append("")
        if cc.frequency:
            lines.append(f"- **Frequency:** {cc.frequency}")
        if cc.accuracy:
            lines.append(f"- **Accuracy:** {cc.accuracy}")
        if cc.timing:
            lines.append(f"- **Timing:** {cc.timing}")
        lines.append("")

    # VERIFICATION (optional — modernization #25)
    v = pspec.verification
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

    # OBSERVABILITY (optional — modernization #1 + #33)
    obs = pspec.observability
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
                runbook_link = f" → [runbook](../../../{a.runbook})" if a.runbook else ""
                lines.append(f"- `{a.name}` *({a.severity.value})* — when `{a.when}`{runbook_link}")
            lines.append("")

    # COMMENTS (optional)
    if pspec.comments:
        lines.append("## COMMENTS")
        lines.append("")
        lines.append(pspec.comments.rstrip())
        lines.append("")
        lines.append("*Not a formal part of the specification (1988 §13.5).*")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(
        "*Format: 2000 Fig 4.46 — INPUTS / OUTPUTS / TRANSFORMATION. "
        "See [`../../../toolkit/PSPEC_DESIGN.md`](../../../toolkit/PSPEC_DESIGN.md).*"
    )

    return "\n".join(lines) + "\n"
