"""Map channel deliverables to Figma template metadata."""

from __future__ import annotations

from typing import Any


def find_template(deliverable: dict[str, Any], templates: list[dict[str, Any]]) -> dict[str, Any] | None:
    channel_id = deliverable.get("channel_id")
    ratio = deliverable.get("ratio")
    for template in templates:
        if template.get("channel_id") == channel_id and template.get("ratio") == ratio:
            return template
    return None
