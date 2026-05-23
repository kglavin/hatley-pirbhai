"""Load and validate dictionary.yaml into a Project model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .model import Project


def load(path: str | Path) -> Project:
    """Load a dictionary.yaml file into a validated Project model.

    The dictionary.yaml schema uses entity/flow/edge IDs as dict keys
    (idiomatic YAML); the loader injects each key as the `id` field of
    the corresponding object so Pydantic models carry the stable ID.

    Raises:
        FileNotFoundError: path does not exist
        yaml.YAMLError: invalid YAML
        pydantic.ValidationError: schema mismatch (missing required field,
            wrong type, unknown enum value, etc.)
    """
    path = Path(path)
    raw: dict[str, Any] = yaml.safe_load(path.read_text())

    # Inject the key as `id` on every entity/flow/edge/transition before
    # Pydantic validation — the schema requires `id`, but in YAML it's the
    # dict key.
    for section in (
        "entities", "flows", "edges", "transitions", "pspecs",
        "architecture_modules", "architecture_flows",
        "architecture_interconnects", "architecture_module_specs",
        "architecture_interconnect_specs",
        "adrs",
        "budgets", "tpms",
        "service_level_objectives",
    ):
        items = raw.get(section, {})
        if items is None:
            raw[section] = {}
            continue
        for key, value in items.items():
            if isinstance(value, dict):
                value["id"] = key

    return Project.model_validate(raw)
