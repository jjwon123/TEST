#!/usr/bin/env python3
"""Measure evidence for repeated real-event operations and failure recovery."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json, write_text


TERMINAL_SUCCESS = {"archived", "archived_no_assets"}


def audit(runs_root: Path = ROOT / "runs", required_events: int = 3, required_recoveries: int = 1) -> dict[str, Any]:
    records = []
    for run_dir in sorted(runs_root.iterdir()) if runs_root.exists() else []:
        status_path = run_dir / "run-status.json"
        if not status_path.exists():
            continue
        status = read_json(status_path, default={})
        stages = status.get("stage_status", {})
        event_id = str(status.get("event_id") or run_dir.name)
        event_name = str(status.get("event_name") or status.get("eventName") or _event_name(run_dir) or event_id)
        automation_checkpoint = (
            stages.get("01_event_brief") == "approved"
            and stages.get("02_content_planning") == "approved"
            and (
                stages.get("03_reference_research") in {"done", "approved"}
                or stages.get("03_visual_candidates") in {"done", "approved"}
            )
        )
        terminal_success = status.get("run_state") in TERMINAL_SUCCESS
        failures = status.get("stage_failures", [])
        failure_count = len(failures) if isinstance(failures, (list, dict)) else 0
        recovered = failure_count > 0 and status.get("run_state") != "failed"
        progress_stages = sum(value in {"done", "approved", "review_pending", "done_no_assets"} for value in stages.values())
        records.append({
            "runId": run_dir.name,
            "eventId": event_id,
            "eventName": event_name,
            "runState": status.get("run_state", ""),
            "automationCheckpoint": automation_checkpoint,
            "terminalSuccess": terminal_success,
            "failureCount": failure_count,
            "recovered": recovered,
            "currentStage": str(status.get("current_stage") or ""),
            "progressStages": progress_stages,
        })

    checkpoint_events = _distinct_events(records, "automationCheckpoint")
    terminal_events = _distinct_events(records, "terminalSuccess")
    recovered_runs = [item["runId"] for item in records if item["recovered"]]
    terminal_event_ids = {item["eventId"] for item in terminal_events}
    next_terminal_candidates = _next_terminal_candidates(records, terminal_event_ids)
    requirements = {
        "threeDistinctAutomationCheckpoints": len(checkpoint_events) >= required_events,
        "threeDistinctTerminalEvents": len(terminal_events) >= required_events,
        "oneRecoveredRun": len(recovered_runs) >= required_recoveries,
    }
    return {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(requirements.values()) else "incomplete",
        "requirements": requirements,
        "summary": {
            "requiredDistinctEvents": required_events,
            "automationCheckpointEvents": len(checkpoint_events),
            "terminalSuccessEvents": len(terminal_events),
            "requiredRecoveries": required_recoveries,
            "recoveredRuns": len(recovered_runs),
        },
        "automationCheckpointEvents": checkpoint_events,
        "terminalSuccessEvents": terminal_events,
        "recoveredRunIds": recovered_runs,
        "nextTerminalCandidates": next_terminal_candidates,
        "runs": records,
    }


def _event_name(run_dir: Path) -> str:
    event = read_json(run_dir / "event-input.json", default={})
    if not event:
        event = read_json(run_dir / "input" / "event-input.json", default={})
    return str(event.get("eventName") or event.get("event_name") or "")


def _distinct_events(records: list[dict[str, Any]], flag: str) -> list[dict[str, str]]:
    events: dict[str, str] = {}
    for item in records:
        if item[flag]:
            events.setdefault(item["eventId"], item["eventName"])
    return [{"eventId": event_id, "eventName": events[event_id]} for event_id in sorted(events)]


def _next_terminal_candidates(records: list[dict[str, Any]], terminal_event_ids: set[str]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for item in records:
        if not item["automationCheckpoint"] or item["eventId"] in terminal_event_ids:
            continue
        previous = best.get(item["eventId"])
        if not previous or item["progressStages"] > previous["progressStages"]:
            best[item["eventId"]] = item
    return sorted(best.values(), key=lambda item: (-item["progressStages"], item["eventName"]))[:3]


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    requirements = report["requirements"]
    lines = [
        "# Repeated Operations Evidence",
        "",
        f"- Status: `{report['status']}`",
        f"- Automation checkpoints: `{summary['automationCheckpointEvents']}/{summary['requiredDistinctEvents']}` distinct events",
        f"- Terminal successes: `{summary['terminalSuccessEvents']}/{summary['requiredDistinctEvents']}` distinct events",
        f"- Recovered runs: `{summary['recoveredRuns']}/{summary['requiredRecoveries']}`",
        "",
        "## Requirements",
        "",
    ]
    lines.extend(f"- [{'x' if passed else ' '}] {name}" for name, passed in requirements.items())
    lines.extend(["", "## Terminal Success Events", ""])
    lines.extend(f"- {item['eventName']} (`{item['eventId']}`)" for item in report["terminalSuccessEvents"])
    lines.extend(["", "## Next Terminal Candidates", ""])
    lines.extend(
        f"- {item['eventName']} / `{item['runId']}` / `{item['currentStage']}`"
        for item in report["nextTerminalCandidates"]
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    report = audit()
    output = ROOT / ".tmp" / "repeated-operations"
    write_json(output / "latest-repeated-operations.json", report)
    write_text(output / "latest-repeated-operations.md", render_markdown(report))
    print(
        "REPEATED_OPERATIONS "
        f"{report['status']} checkpoints={report['summary']['automationCheckpointEvents']} "
        f"terminal={report['summary']['terminalSuccessEvents']} recovered={report['summary']['recoveredRuns']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
