"""Template metadata registry.

Templates live under `core/templates/**/{template}.json`. Handlers use this
registry to resolve template metadata by `template_id` without knowing folder
layout details.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils.json_io import read_json


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "core" / "templates"


class TemplateRegistryError(LookupError):
    pass


def get(template_id: str) -> dict[str, Any]:
    for template in list_all():
        if template.get("template_id") == template_id:
            return template
    available = ", ".join(sorted(template["template_id"] for template in list_all()))
    raise TemplateRegistryError(
        f"Template metadata not found for '{template_id}'. Available template ids: {available}"
    )


def list_all() -> list[dict[str, Any]]:
    templates = []
    for path in sorted(TEMPLATE_DIR.glob("**/*.json")):
        templates.append(read_json(path))
    return templates
