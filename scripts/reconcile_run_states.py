#!/usr/bin/env python3
"""Reconcile stale and legacy run states while preserving an audit history."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--stale-hours", type=int, default=24)
    parser.add_argument("--apply", action="store_true", help="Write repairs. Default is dry-run.")
    args = parser.parse_args()
    if not args.run and not args.all:
        parser.error("Use --run or --all")
    run_dirs = [args.run.resolve()] if args.run else sorted(path for path in (ROOT / "runs").iterdir() if path.is_dir())
    report = reconcile_runs(run_dirs, stale_hours=args.stale_hours, apply=args.apply)
    write_json(ROOT / ".tmp" / "run-reconcile" / "latest-run-reconcile.json", report)
    print(f"RUN_RECONCILE {'applied' if args.apply else 'dry-run'} changes={report['summary']['changedRuns']}")
    return 0


def reconcile_runs(run_dirs: list[Path], *, stale_hours: int, apply: bool) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=stale_hours)
    records: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        status_path = run_dir / "run-status.json"
        if not status_path.exists():
            continue
        status = read_json(status_path)
        changes = reconcile_status(status, cutoff=cutoff)
        if changes and apply:
            write_json(status_path, status)
        records.append({"run": str(run_dir), "changes": changes, "applied": bool(changes and apply)})
    return {
        "createdAt": now(),
        "mode": "apply" if apply else "dry-run",
        "staleHours": stale_hours,
        "summary": {
            "inspectedRuns": len(records),
            "changedRuns": sum(bool(record["changes"]) for record in records),
            "changes": sum(len(record["changes"]) for record in records),
        },
        "runs": records,
    }


def reconcile_status(status: dict[str, Any], *, cutoff: datetime) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    stage_status = status.setdefault("stage_status", {})
    updated_at = parse_time(status.get("updated_at"))
    stale_stages = [
        stage for stage, value in stage_status.items()
        if value == "in_progress" and updated_at and updated_at < cutoff
    ]
    for stage in stale_stages:
        stage_status[stage] = "blocked"
        status.setdefault("stage_failures", {})[stage] = {
            "failed_at": now(),
            "error_type": "StaleInProgress",
            "message": "Reconciled after exceeding the stale in-progress threshold.",
        }
        changes.append({"type": "stale_in_progress_to_blocked", "stage": stage})
    if stale_stages:
        status["run_state"] = "failed"
        status["current_stage"] = stale_stages[0]

    archive_stage = stage_status.get("07_asset_archive")
    if status.get("run_state") == "done" and archive_stage in {"done", "done_no_assets"}:
        target = "archived_no_assets" if archive_stage == "done_no_assets" else "archived"
        status["run_state"] = target
        status["current_stage"] = "07_asset_archive"
        changes.append({"type": "legacy_done_to_terminal", "stage": "07_asset_archive", "target": target})

    if changes:
        status.setdefault("history", []).append({
            "at": now(),
            "event": "run_state_reconciled",
            "stage": status.get("current_stage"),
            "note": "; ".join(change["type"] for change in changes),
        })
        status["updated_at"] = now()
    return changes


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
