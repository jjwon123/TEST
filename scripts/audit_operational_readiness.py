#!/usr/bin/env python3
"""Audit automation-side operational readiness without ComfyUI or human-review gates."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json, write_text
from core.utils.schema_validation import SchemaValidationError, validate_json


TERMINAL_STATES = {"archived", "archived_no_assets", "failed"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stale-hours", type=int, default=24)
    args = parser.parse_args()
    report = audit(stale_hours=args.stale_hours)
    output_dir = ROOT / ".tmp" / "operations-readiness"
    write_json(output_dir / "latest-operations-readiness.json", report)
    write_text(output_dir / "latest-operations-readiness.md", render_markdown(report))
    print(f"OPERATIONS_READINESS {report['status']} {output_dir / 'latest-operations-readiness.json'}")
    return 0 if report["status"] == "pass" else 1


def audit(stale_hours: int = 24) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    run_states = read_json(ROOT / "core" / "states" / "run-states.json", default={})
    known_states = set(run_states.get("states", []))
    event_schema = read_json(ROOT / "core" / "schemas" / "event-input.schema.json")
    brand_schema = read_json(ROOT / "core" / "schemas" / "brand-guide.schema.json")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=stale_hours)

    runs: list[dict[str, Any]] = []
    for run_dir in sorted((ROOT / "runs").iterdir()) if (ROOT / "runs").exists() else []:
        status_path = run_dir / "run-status.json"
        if not status_path.exists():
            continue
        status = read_json(status_path, default={})
        stage_status = status.get("stage_status", {})
        updated_at = parse_time(status.get("updated_at")) or datetime.fromtimestamp(status_path.stat().st_mtime, timezone.utc)
        in_progress = [stage for stage, value in stage_status.items() if value == "in_progress"]
        if in_progress and updated_at < cutoff:
            add(findings, "P0", "stale_in_progress", f"{run_dir.name} has stale in-progress stages.", in_progress)
        run_state = str(status.get("run_state") or "")
        if run_state and run_state not in known_states:
            add(findings, "P1", "unknown_run_state", f"{run_dir.name} uses undefined run state '{run_state}'.")
        archive = read_json(run_dir / "07_asset_archive" / "asset-archive.json", default={})
        archive_count = len(archive.get("assets", []))
        archive_stage = stage_status.get("07_asset_archive")
        if archive_stage in {"done", "done_no_assets"} and run_state not in {"archived", "archived_no_assets"}:
            add(findings, "P1", "archive_not_terminal", f"{run_dir.name} completed archive but is not in a terminal archive state.")
        if (run_dir / "production-package").exists() and stage_status.get("06_qa_packaging") != "approved":
            add(findings, "P1", "package_before_qa_approval", f"{run_dir.name} has a production package before QA approval.")
        runs.append({
            "run": run_dir.name,
            "runState": run_state,
            "updatedAt": updated_at.isoformat(),
            "inProgress": in_progress,
            "archiveAssets": archive_count,
        })

    invalid_events: list[dict[str, str]] = []
    for event_dir in sorted((ROOT / "events").iterdir()) if (ROOT / "events").exists() else []:
        if not event_dir.is_dir() or not (event_dir / "event-input.json").exists():
            continue
        try:
            validate_json(read_json(event_dir / "event-input.json"), event_schema)
            validate_json(read_json(event_dir / "brand-guide.json"), brand_schema)
        except (SchemaValidationError, FileNotFoundError, ValueError) as exc:
            invalid_events.append({"event": event_dir.name, "error": str(exc)})
    if invalid_events:
        add(findings, "P0", "invalid_event_sources", "Event source files fail the canonical input contract.", invalid_events)

    jobs = read_json(ROOT / ".tmp" / "console-jobs" / "jobs.json", default={"jobs": []}).get("jobs", [])
    interrupted_jobs = [job.get("job_id") for job in jobs if job.get("status") == "interrupted"]
    if interrupted_jobs:
        add(findings, "P1", "interrupted_console_jobs", "Console jobs were interrupted and may require a retry.", interrupted_jobs)

    learned_rules = list((ROOT / "design_brain_wiki" / "training_sessions").glob("**/learned_rules.json"))
    consumer_files = learned_rule_consumers()
    promoted_rules = read_json(ROOT / "assets" / "rules" / "promoted-reference-rules.json", default={"rules": []}).get("rules", [])
    if learned_rules and not consumer_files:
        add(
            findings,
            "P1",
            "learned_rules_not_consumed",
            "Training learned_rules.json files are generated but no pipeline/service consumer is connected.",
            {"learnedRuleFiles": len(learned_rules)},
        )
    if learned_rules and not promoted_rules:
        add(findings, "P1", "no_promoted_learned_rules", "Learned rules exist but none passed the runtime promotion policy.")

    terminal_runs = [run for run in runs if run["runState"] in TERMINAL_STATES]
    if runs and not terminal_runs:
        add(findings, "P1", "no_terminal_runs", "No run currently proves a terminal archived/failed lifecycle state.")

    severity_counts = Counter(item["severity"] for item in findings)
    status = "fail" if severity_counts["P0"] else "warning" if findings else "pass"
    return {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "scope": "Automation operations only; excludes ComfyUI quality and required human review work.",
        "summary": {
            "runs": len(runs),
            "terminalRuns": len(terminal_runs),
            "events": len([path for path in (ROOT / "events").iterdir() if path.is_dir()]) if (ROOT / "events").exists() else 0,
            "invalidEvents": len(invalid_events),
            "persistedJobs": len(jobs),
            "learnedRuleFiles": len(learned_rules),
            "learnedRuleConsumers": len(consumer_files),
            "promotedLearnedRules": len(promoted_rules),
            "severityCounts": dict(severity_counts),
        },
        "runs": runs,
        "findings": findings,
    }


def learned_rule_consumers() -> list[str]:
    consumers: list[str] = []
    roots = [ROOT / "pipeline", ROOT / "services", ROOT / "core"]
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if "learned_rules.json" in path.read_text(encoding="utf-8", errors="ignore"):
                consumers.append(relative(path))
    return consumers


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def add(findings: list[dict[str, Any]], severity: str, code: str, message: str, evidence: Any = None) -> None:
    findings.append({"severity": severity, "code": code, "message": message, "evidence": evidence})


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Operations Readiness",
        "",
        f"- Status: `{report['status']}`",
        f"- Scope: {report['scope']}",
        f"- Runs: {summary['runs']} / terminal: {summary['terminalRuns']}",
        f"- Events: {summary['events']} / invalid: {summary['invalidEvents']}",
        f"- Learned rules: {summary['learnedRuleFiles']} / consumers: {summary['learnedRuleConsumers']}",
        "",
        "## Findings",
        "",
    ]
    lines.extend(f"- **{item['severity']} {item['code']}**: {item['message']}" for item in report["findings"])
    if not report["findings"]:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
