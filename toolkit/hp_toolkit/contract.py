# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Project a dictionary.yaml into an EXECUTABLE DOMAIN CONTRACT (archi integration R1).

Backing code for the `hp-propose-contract` skill. The contract is a machine-consumable projection of the
completed HP model that an autonomous-control consumer (e.g. archi) ingests to run a loop against the
domain *without hand-coding the domain*. It is CONSUMER-NEUTRAL — plant / observation / action /
situation / objective / red-lines / seed — and a REGENERABLE projection (never hand-edited; fix the
model and re-emit).

What is mechanical (fully auto-projected here):
    plant            ← system + terminator entities + architecture modules
    observation      ← inbound level-0 data flows  (terminator → system)
    action           ← outbound level-0 flows       (system → terminator)
    situation vocab  ← CSPEC states + the level-0 signal labels
    objective.stated ← SLOs (cost-ish → cost, else proficiency) + PSPEC computational_constraints
    red_lines.machine_checkable ← TPM threshold+direction (already a don't-cross)
    red_lines.qualitative       ← AMS required_constraints.safety + STRIDE accepted/out_of_scope prose
    seed_skill       ← the PSPEC of the process that emits the action surface

What needs human confirmation (emitted with an explicit flag, NOT invented):
    objective.intended  — the gap to the stated objective is what a grown corpus games (hp-audit/R2 needs it)
    the red-line split  — auto-classified, but a human should confirm machine-checkable vs qualitative

    python -m hp_toolkit.contract examples/solar/dictionary.yaml      # writes examples/solar/<dir>.contract.yaml
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .model import EntityKind, FlowKind, Project, TPMDirection

_UNSET_INTENDED = ("<UNSET — confirm the INTENDED objective in prose. The gap between it and the stated "
                   "objective above is exactly what an autonomously-grown corpus games; hp-audit (R2) "
                   "needs it to detect objective-gaming.>")


def _system(project: Project):
    for e in project.all_entities():
        if e.kind == EntityKind.SYSTEM:
            return e
    return None


def _plant(project: Project) -> dict:
    sysent = _system(project)
    terms = [e for e in project.all_entities() if e.kind == EntityKind.TERMINATOR]
    return {
        "system": {"id": sysent.id, "label": sysent.label} if sysent else None,
        "terminators": [{"id": e.id, "label": e.label} for e in terms],
        "modules": [{"id": m.id, "name": m.name, "kind": m.kind.value}
                    for m in project.all_architecture_modules()],
    }


def _observation(project: Project, sys_id: str) -> list[dict]:
    """Inbound level-0 data flows — what the loop senses each tick (terminator → system)."""
    out = []
    for f in project.all_flows():
        if f.level == 0 and f.target == sys_id and f.kind in (FlowKind.DATA, FlowKind.DATA_AND_CONTROL):
            out.append({"flow": f.id, "label": f.label, "from": f.source,
                        "into": f.refined_target, "medium": f.medium})
    return out


def _action(project: Project, sys_id: str) -> list[dict]:
    """Outbound level-0 flows — what the loop emits each tick (system → terminator)."""
    out = []
    for f in project.all_flows():
        if f.level == 0 and f.source == sys_id:
            out.append({"flow": f.id, "label": f.label, "to": f.target,
                        "emitted_by": f.refined_source, "kind": f.kind.value, "medium": f.medium})
    return out


def _situation_vocabulary(project: Project, observation: list[dict], action: list[dict]) -> dict:
    """The features the consumer's supervisor / arbitrage reason over: CSPEC states + signal labels."""
    states = [{"id": e.id, "label": e.label, "machine": e.parent}
              for e in project.all_entities()
              if e.kind in (EntityKind.STATE, EntityKind.STATE_COMPOSITE)]
    signals = sorted({f["label"] for f in observation} | {f["label"] for f in action})
    return {"states": states, "signals": signals}


def _objective(project: Project) -> dict:
    """Stated objective from SLOs (cost-ish → cost, else proficiency) + PSPEC computational constraints.
    The intended objective is left for human confirmation (flagged), never invented."""
    proficiency, cost = [], []
    for s in project.all_slos():
        blob = f"{s.id} {s.name} {s.sli.query} {s.sli.unit or ''}".lower()
        entry = {"slo": s.id, "name": s.name, "target": s.target,
                 "unit": s.sli.unit, "window": s.window}
        (cost if any(w in blob for w in ("cost", "usd", "$", "dollar", "budget", "spend")) else
         proficiency).append(entry)
    constraints = []
    for p in project.all_pspecs():
        cc = p.computational_constraints
        if cc and (cc.accuracy or cc.timing or cc.frequency):
            constraints.append({"pspec": p.id, "process": p.parent_process,
                                 "accuracy": cc.accuracy, "timing": cc.timing, "frequency": cc.frequency})
    return {"stated": {"proficiency": proficiency, "cost": cost, "computational_constraints": constraints},
            "intended": _UNSET_INTENDED}


def _machine_checkable_red_lines(project: Project) -> list[dict]:
    """One per TPM: threshold + direction is already a per-tick don't-cross predicate."""
    out = []
    for t in project.all_tpms():
        op = "<=" if t.direction == TPMDirection.LESS_IS_BETTER else ">="
        out.append({"id": f"rl_{t.id}", "source": t.id, "metric": t.name,
                    "predicate": f"{op} {t.threshold}", "unit": t.unit,
                    "measured_by": t.measurement_method})
    return out


def _qualitative_red_lines(project: Project) -> list[dict]:
    """AMS safety constraints + STRIDE mitigations explicitly accepted / out-of-scope (residual risks)."""
    out = []
    for ams in project.all_architecture_module_specs():
        rc = ams.required_constraints
        if rc and rc.safety:
            out.append({"id": f"rl_safety_{ams.parent_module}", "source": ams.id, "kind": "safety",
                        "statement": rc.safety.strip()})
    for ic in project.all_architecture_interconnects():
        sm = ic.stride_mitigations
        if not sm:
            continue
        for cat in ("spoofing", "tampering", "repudiation", "info_disclosure",
                    "denial_of_service", "elev_of_privilege"):
            val = getattr(sm, cat, None)
            if val and any(w in val.lower() for w in ("accepted", "out_of_scope", "out of scope")):
                out.append({"id": f"rl_stride_{ic.id}_{cat}", "source": ic.id,
                            "kind": f"residual-{cat}", "statement": val.strip()})
    return out


def _seed_skill(project: Project, action: list[dict]) -> dict | None:
    """The PSPEC of a process that emits the action surface — a baseline policy for the consumer to beat."""
    actors = {f["emitted_by"] for f in action if f.get("emitted_by")}
    for p in project.all_pspecs():
        if p.parent_process in actors:
            return {"pspec": p.id, "process": p.parent_process,
                    "transformation_style": p.transformation.style.value,
                    "note": "baseline to beat (seed-and-grow); the consumer matures it"}
    pspecs = project.all_pspecs()
    if pspecs:
        p = pspecs[0]
        return {"pspec": p.id, "process": p.parent_process,
                "transformation_style": p.transformation.style.value,
                "note": "fallback seed — no PSPEC on the action surface; confirm this is the right baseline"}
    return None


def _underspecified(observation: list[dict], action: list[dict]) -> list[str]:
    """Honest gaps: an obs/action flow with no declared transport is underspecified for execution."""
    gaps = []
    for f in observation + action:
        if not f.get("medium"):
            gaps.append(f"{f['flow']} ({f['label']}) — transport/shape unspecified")
    return gaps


def project_contract(project: Project) -> dict:
    """Project a loaded Project into the consumer-neutral domain contract (a plain, YAML-friendly dict)."""
    sysent = _system(project)
    sys_id = sysent.id if sysent else None
    observation = _observation(project, sys_id) if sys_id else []
    action = _action(project, sys_id) if sys_id else []
    return {
        "contract": project.project,
        "version": project.version,                    # pinned to the dictionary version
        "source": "dictionary.yaml",
        "regenerable": True,
        "note": ("Projected by hp-propose-contract from the HP model. A regenerable projection — do NOT "
                 "hand-edit; fix dictionary.yaml and re-emit. Consumer-neutral; a consumer (e.g. archi) "
                 "binds its own constructs onto these fields."),
        "plant": _plant(project),
        "observation": observation,
        "action": action,
        "situation_vocabulary": _situation_vocabulary(project, observation, action),
        "objective": _objective(project),
        "red_lines": {
            "machine_checkable": _machine_checkable_red_lines(project),
            "qualitative": _qualitative_red_lines(project),
        },
        "seed_skill": _seed_skill(project, action),
        "underspecified": _underspecified(observation, action),
    }


def emit(dictionary_path: str | Path) -> Path:
    """Load a dictionary.yaml, project the contract, and write `<dir-name>.contract.yaml` beside it."""
    import yaml

    from .load import load

    dictionary_path = Path(dictionary_path)
    project = load(dictionary_path)
    contract = project_contract(project)
    out_path = dictionary_path.parent / f"{dictionary_path.parent.name}.contract.yaml"
    out_path.write_text(yaml.safe_dump(contract, sort_keys=False, default_flow_style=False, width=100))
    return out_path


def _main() -> int:
    import sys

    if len(sys.argv) < 2:
        print("usage: python -m hp_toolkit.contract <path/to/dictionary.yaml>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: {path} does not exist", file=sys.stderr)
        return 2

    from .load import load
    project = load(path)
    contract = project_contract(project)
    out_path = emit(path)

    # A light self-check (the proof that the projection is well-formed) — the full hp-validate
    # integration is future work; this surfaces the structural essentials.
    rl = contract["red_lines"]
    obj = contract["objective"]["stated"]
    seed = contract["seed_skill"]
    print(f"contract → {out_path}")
    print(f"  plant:        system={bool(contract['plant']['system'])}  "
          f"terminators={len(contract['plant']['terminators'])}  modules={len(contract['plant']['modules'])}")
    print(f"  observation:  {len(contract['observation'])} inbound flow(s)")
    print(f"  action:       {len(contract['action'])} outbound flow(s)")
    print(f"  objective:    {len(obj['proficiency'])} proficiency + {len(obj['cost'])} cost SLO(s); "
          f"intended={'SET' if not contract['objective']['intended'].startswith('<UNSET') else 'UNSET (confirm)'}")
    print(f"  red_lines:    {len(rl['machine_checkable'])} machine-checkable + {len(rl['qualitative'])} qualitative")
    print(f"  seed_skill:   {seed['pspec'] if seed else 'NONE (no PSPEC — supply a seed)'}")
    if contract["underspecified"]:
        print(f"  underspecified: {len(contract['underspecified'])} flow(s) — see contract (tighten the model)")

    problems = []
    if not contract["plant"]["system"]:
        problems.append("no system entity")
    if not contract["observation"] and not contract["action"]:
        problems.append("no boundary flows (observation/action empty)")
    if not (obj["proficiency"] or obj["cost"]):
        problems.append("no objective (no SLOs) — the consumer has nothing to be graded on")
    if not rl["machine_checkable"] and not rl["qualitative"]:
        problems.append("NO red lines — an autonomous consumer with an empty envelope is a governance risk")
    if seed is None:
        problems.append("no seed skill")
    if problems:
        print("  ⚠ findings: " + "; ".join(problems))
        return 1
    print("  ✓ contract is structurally complete")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
