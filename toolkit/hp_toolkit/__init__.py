"""HP Toolkit — AI-augmented Hatley-Pirbhai methodology.

The toolkit reads a per-project dictionary.yaml (HP's Requirements Dictionary
in YAML form), validates it, and provides a programmatic model that
validators, renderers, and skills operate on.

Top-level exports:
    Project, Entity, Flow, Edge     — model classes
    EntityKind, FlowKind, EdgeKind  — enums
    load                            — read dictionary.yaml → Project
"""

from .model import (
    Project,
    Entity,
    Flow,
    Edge,
    Transition,
    EntityKind,
    FlowKind,
    EdgeKind,
)
from .load import load
from .validate import (
    validate,
    reference_integrity,
    hierarchy_consistency,
    coverage_metrics,
    find_orphans,
    ValidationIssue,
    ValidationReport,
)
from .status import status_report, StatusReport, StageStatus

__all__ = [
    "Project",
    "Entity",
    "Flow",
    "Edge",
    "Transition",
    "EntityKind",
    "FlowKind",
    "EdgeKind",
    "load",
    "validate",
    "reference_integrity",
    "hierarchy_consistency",
    "coverage_metrics",
    "find_orphans",
    "ValidationIssue",
    "ValidationReport",
    "status_report",
    "StatusReport",
    "StageStatus",
]

__version__ = "0.0.1"
