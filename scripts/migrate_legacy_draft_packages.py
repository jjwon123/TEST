#!/usr/bin/env python3
"""Move pre-QA production packages to an explicitly labeled legacy draft folder."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = ROOT / "runs"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Move packages. Default is dry-run.")
    args = parser.parse_args()
    report = migrate_legacy_packages(RUNS_ROOT, apply=args.apply)
    write_json(ROOT / ".tmp" / "legacy-package-migration" / "latest.json", report)
    print(f"LEGACY_PACKAGE_MIGRATION {'applied' if args.apply else 'dry-run'} candidates={report['summary']['candidates']}")
    return 0


def migrate_legacy_packages(runs_root: Path, *, apply: bool) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for package_dir in runs_root.glob("*/production-package"):
        run_dir = package_dir.parent
        status = read_json(run_dir / "run-status.json", default={})
        qa_status = status.get("stage_status", {}).get("06_qa_packaging")
        if qa_status == "approved":
            continue
        destination = next_destination(run_dir / "production-package-legacy-draft")
        record = {
            "run": run_dir.name,
            "qaStageStatus": qa_status,
            "source": str(package_dir),
            "destination": str(destination),
            "applied": False,
        }
        if apply:
            resolved_runs = runs_root.resolve()
            if resolved_runs not in [package_dir.resolve(), *package_dir.resolve().parents]:
                raise ValueError(f"Package path escapes runs root: {package_dir}")
            package_dir.rename(destination)
            write_json(destination / "legacy-draft-migration.json", {
                "migratedAt": datetime.now(timezone.utc).isoformat(),
                "reason": "Package existed before 06_qa_packaging approval.",
                "originalPath": "production-package",
                "qaStageStatus": qa_status,
            })
            record["applied"] = True
        records.append(record)
    return {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if apply else "dry-run",
        "summary": {"candidates": len(records), "applied": sum(item["applied"] for item in records)},
        "packages": records,
    }


def next_destination(path: Path) -> Path:
    if not path.exists():
        return path
    version = 2
    while True:
        candidate = path.with_name(f"{path.name}-v{version}")
        if not candidate.exists():
            return candidate
        version += 1


if __name__ == "__main__":
    raise SystemExit(main())
