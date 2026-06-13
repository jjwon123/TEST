"""Figma client boundary.

This scaffold avoids direct API calls while defining the shape of future Figma
operations. Pipeline stages should request actions through this boundary so the
backend can later swap MCP, REST API, or plugin execution without changing stage
contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FigmaTarget:
    file_key: str
    node_id: str


class FigmaClient:
    def describe_target(self, target: FigmaTarget) -> dict[str, Any]:
        return {
            "file_key": target.file_key,
            "node_id": target.node_id,
            "status": "metadata_only",
        }
