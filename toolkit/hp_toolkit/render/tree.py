# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Project artifact tree — the single source for portal navigation + PDF TOC.

A `TreeNode` is one entry in the tree; `build_project_tree(project, project_dir)`
walks the loaded Project model and returns a root node whose children are the
stage sections (1–5) plus a Modernization section plus a Reference section.

Both the HTML sidebar renderer (render/sidebar.py — Commit 2) and the PDF
renderer (render/pdf.py — Commit 3) consume the same tree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal, Optional

from ..model import Project, EntityKind
from .adr import adr_filename
from .architecture import ams_subdir_name, ais_subdir_name
from .pspec import pspec_subdir_name


NodeKind = Literal["root", "section", "subsection", "artifact", "external", "note"]


@dataclass
class TreeNode:
    """One entry in the project tree.

    `href` is a path relative to the project root (the directory containing
    `dictionary.yaml`). `kind` is a UI hint — sections get headings, artifacts
    get list items, externals get a marker, notes are unlinked descriptive lines.
    """
    label: str
    kind: NodeKind = "section"
    href: Optional[str] = None
    badge: Optional[str] = None
    children: list["TreeNode"] = field(default_factory=list)
    pdf_section_intro: Optional[str] = None

    def add(self, child: "TreeNode") -> "TreeNode":
        self.children.append(child)
        return child

    def walk(self) -> Iterator["TreeNode"]:
        """Depth-first iterator over all nodes including self."""
        yield self
        for c in self.children:
            yield from c.walk()


# ─────────────────────────────────────────────────────────────────────
# Builder
# ─────────────────────────────────────────────────────────────────────

def build_project_tree(project: Project, project_dir: Path) -> TreeNode:
    """Build the project tree from the loaded Project model + project directory.

    Stages 1–5 always appear (with an empty-state note when nothing is locked).
    Modernization + Reference appear conditionally based on what's declared."""
    root = TreeNode(label=project.project, kind="root")

    # Home — links back to the index page
    root.add(TreeNode(
        label="Home",
        kind="artifact",
        href="project_index.generated.html",
    ))

    root.add(_build_stage1(project))
    root.add(_build_stage2(project))
    root.add(_build_stage3(project))
    root.add(_build_stage4(project))
    root.add(_build_stage5(project))

    modern = _build_modernization(project, project_dir)
    if modern.children:
        root.add(modern)

    root.add(_build_reference(project))

    return root


# ─── Stage builders ──────────────────────────────────────────────────

def _build_stage1(project: Project) -> TreeNode:
    n_terms = sum(1 for e in project.all_entities() if e.kind == EntityKind.TERMINATOR)
    s = TreeNode(label="Stage 1 — Context Diagram", kind="section")
    if n_terms > 0:
        s.badge = f"{n_terms} terminator(s)"
        s.add(TreeNode(
            label="Context Diagram",
            kind="artifact",
            href="00-context/context.generated.html",
        ))
    return s


def _build_stage2(project: Project) -> TreeNode:
    n_procs = sum(1 for e in project.all_entities()
                  if e.kind == EntityKind.PROCESS and e.level == 1)
    s = TreeNode(label="Stage 2 — Level-1 DFD", kind="section")
    if n_procs > 0:
        s.badge = f"{n_procs} process(es)"
        s.add(TreeNode(
            label="Level-1 DFD",
            kind="artifact",
            href="01-level1/dfd.generated.html",
        ))
        # HIERARCHICAL_INGEST_DESIGN.md: surface per-parent level-N DFDs
        # for every non-leaf process so the sidebar walks the hierarchy.
        for parent_proc in _non_leaf_processes(project):
            slug = parent_proc.id.replace("proc_", "").replace("_", "-")
            s.add(TreeNode(
                label=f"{parent_proc.label} (decomp)",
                kind="artifact",
                href=f"02-decomp/{slug}/dfd.generated.html",
            ))
    return s


def _non_leaf_processes(project: Project) -> list:
    """Processes that have child processes (mirrors render_project's helper).

    Used by the sidebar tree builder to expose per-parent level-N DFD
    pages under Stage 2."""
    parents: set[str] = set()
    for e in project.all_entities():
        if e.kind == EntityKind.PROCESS and e.parent and e.parent != "sys_root":
            target = project.entities.get(e.parent)
            if target and target.kind == EntityKind.PROCESS:
                parents.add(target.id)
    return [project.entity(pid) for pid in parents]


def _build_stage3(project: Project) -> TreeNode:
    cspec_procs = [e for e in project.all_entities()
                   if e.kind == EntityKind.PROCESS and e.needs_cspec]
    s = TreeNode(label="Stage 3 — CSPECs", kind="section")
    if cspec_procs:
        s.badge = f"{len(cspec_procs)} CSPEC(s)"
        for proc in cspec_procs:
            subdir = proc.id.replace("proc_", "").replace("_", "-")
            s.add(TreeNode(
                label=proc.label,
                kind="artifact",
                href=f"01-level1/cspecs/{subdir}/cspec.generated.html",
            ))
    return s


def _build_stage4(project: Project) -> TreeNode:
    s = TreeNode(label="Stage 4 — PSPECs", kind="section")
    if project.pspecs:
        s.badge = f"{len(project.pspecs)} PSPEC(s)"
        for ps in project.all_pspecs():
            proc = project.entities.get(ps.parent_process)
            label = proc.label if proc else ps.parent_process
            s.add(TreeNode(
                label=label,
                kind="artifact",
                href=f"01-level1/pspecs/{pspec_subdir_name(ps.parent_process)}.generated.html",
            ))
    return s


def _build_stage5(project: Project) -> TreeNode:
    s = TreeNode(label="Stage 5 — Architecture", kind="section")
    if not project.architecture_modules:
        return s

    n_modules = len(project.architecture_modules)
    n_ic = len(project.architecture_interconnects)
    s.badge = f"{n_modules} module(s), {n_ic} interconnect(s)"

    s.add(TreeNode(label="AFD (Flow Diagram)", kind="artifact",
                   href="architecture/afd.generated.html"))
    if project.architecture_interconnects:
        s.add(TreeNode(label="AID (Interconnect Diagram)", kind="artifact",
                       href="architecture/aid.generated.html"))

    if project.architecture_module_specs:
        modules_sub = s.add(TreeNode(label="Modules", kind="subsection"))
        for ams in project.all_architecture_module_specs():
            m = project.architecture_modules.get(ams.parent_module)
            label = m.name if m else ams.parent_module
            modules_sub.add(TreeNode(
                label=label,
                kind="artifact",
                href=f"architecture/specs/{ams_subdir_name(ams.parent_module)}.generated.html",
            ))

    if project.architecture_interconnect_specs:
        ic_sub = s.add(TreeNode(label="Interconnects", kind="subsection"))
        for ais in project.all_architecture_interconnect_specs():
            ic = project.architecture_interconnects.get(ais.parent_interconnect)
            label = ic.name if ic else ais.parent_interconnect
            ic_sub.add(TreeNode(
                label=label,
                kind="artifact",
                href=f"architecture/specs/interconnects/{ais_subdir_name(ais.parent_interconnect)}.generated.html",
            ))

    return s


# ─── Modernization + Reference ──────────────────────────────────────

def _build_modernization(project: Project, project_dir: Path) -> TreeNode:
    s = TreeNode(label="Modernization", kind="section")

    if project.adrs:
        adrs_sub = s.add(TreeNode(
            label="ADRs",
            kind="subsection",
            badge=str(len(project.adrs)),
        ))
        for adr in project.all_adrs():
            adrs_sub.add(TreeNode(
                label=adr.title,
                kind="artifact",
                href=f"adrs/{adr_filename(adr.id).replace('.md', '.generated.html')}",
            ))

    if project.service_level_objectives:
        s.add(TreeNode(
            label="SLOs Summary",
            kind="artifact",
            href="architecture/slos.generated.html",
            badge=f"{len(project.service_level_objectives)} SLO(s)",
        ))

    if project.bounded_contexts:
        bc_sub = s.add(TreeNode(
            label="Bounded Contexts",
            kind="subsection",
            badge=f"{len(project.bounded_contexts)} contexts, "
                  f"{len(project.all_translations())} ACL(s)",
        ))
        bc_sub.add(TreeNode(
            label="Context Map",
            kind="artifact",
            href="context-map.generated-d2.svg",
        ))

    runbook_dir = project_dir / "runbooks"
    if runbook_dir.is_dir():
        runbook_files = sorted(runbook_dir.glob("*.md"))
        if runbook_files:
            rb_sub = s.add(TreeNode(
                label="Runbooks",
                kind="subsection",
                badge=str(len(runbook_files)),
            ))
            for rb in runbook_files:
                label = rb.stem.replace("-", " ").replace("_", " ")
                rb_sub.add(TreeNode(
                    label=label,
                    kind="artifact",
                    href=f"runbooks/{rb.stem}.generated.html",
                ))

    return s


def _build_reference(project: Project) -> TreeNode:
    s = TreeNode(label="Reference", kind="section")
    # Default link → HTML viewer; the page itself has a "Download raw" button
    # for users who want the .yaml verbatim. Prevents the browser-downloads-
    # the-file UX hiccup from clicking the sidebar entry.
    s.add(TreeNode(
        label="Dictionary (browse)",
        kind="artifact",
        href="dictionary.generated.html",
    ))
    s.add(TreeNode(
        label="Dictionary (raw YAML, download)",
        kind="external",
        href="dictionary.yaml",
    ))
    s.add(TreeNode(
        label="HP Quick Reference",
        kind="external",
        href="../../toolkit/reference/HP_QUICK_REF.md",
    ))
    return s
