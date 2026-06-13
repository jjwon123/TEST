"""Run validation boundary.

Future implementation should validate `run-status.json`, approvals, stage
schemas, and required files before expensive service calls.
"""

from pathlib import Path


def validate_run(run_dir: Path) -> list[str]:
    issues: list[str] = []
    if not (run_dir / "run-status.json").exists():
        issues.append("missing run-status.json")
    if not (run_dir / "approvals.json").exists():
        issues.append("missing approvals.json")
    return issues
