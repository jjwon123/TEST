"""Scoped regeneration boundary.

Future implementation should regenerate outputs by stage, deliverable,
candidate, or output ID while preserving version history.
"""

from pathlib import Path


def planned_regeneration(run_dir: Path, stage_id: str, outputs: list[str]) -> dict[str, object]:
    return {
        "run_dir": str(run_dir),
        "stage_id": stage_id,
        "outputs": outputs,
        "mode": "regenerate"
    }
