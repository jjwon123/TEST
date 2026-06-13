"""Export manifest helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def expected_export_record(output_id: str, export_path: Path, dimensions: dict[str, int]) -> dict[str, Any]:
    return {
        "output_id": output_id,
        "expected_export_path": str(export_path),
        "expected_dimensions": dimensions,
        "exists": export_path.exists(),
    }
