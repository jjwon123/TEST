#!/usr/bin/env python3
"""Audit end-to-end pipeline health without mutating a run."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json, write_text
from services.comfyui.workflow_registry import list_presets


SERVICE_URLS = {
    "console": "http://127.0.0.1:5177/api/runs",
    "comfyui": "http://127.0.0.1:8188/system_stats",
    "ollama": "http://127.0.0.1:11434/api/tags",
}
STAGE_ORDER = [
    "01_event_brief",
    "02_content_planning",
    "03_reference_research",
    "04_visual_candidates",
    "05_admin_selection",
    "06_qa_packaging",
    "07_asset_archive",
]
COMPLETED_STAGE_STATUSES = {"done", "approved"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, help="Run directory. Defaults to the newest run.")
    args = parser.parse_args()
    run_dir = (args.run or newest_run()).resolve()
    report = audit(run_dir)
    output_dir = ROOT / ".tmp" / "pipeline-health"
    write_json(output_dir / "latest-pipeline-health.json", report)
    write_text(output_dir / "latest-pipeline-health.md", render_markdown(report))
    print(f"PIPELINE_HEALTH {report['status']} {output_dir / 'latest-pipeline-health.json'}")
    return 0 if report["status"] == "pass" else 1


def newest_run() -> Path:
    runs = [path for path in (ROOT / "runs").iterdir() if path.is_dir()]
    if not runs:
        raise SystemExit("No runs found.")
    return max(runs, key=lambda path: path.stat().st_ctime)


def audit(run_dir: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    services = audit_services(findings)
    status = read_json(run_dir / "run-status.json", default={})
    candidate_manifest = read_json(run_dir / "03_visual_candidates" / "candidate-manifest.json", default={})
    selected_assets = read_json(run_dir / "04_admin_selection" / "selected-assets.json", default={})
    qa_report = read_json(run_dir / "06_qa_packaging" / "qa-report.json", default={})
    archive = read_json(run_dir / "07_asset_archive" / "asset-archive.json", default={})
    reference_manifest = read_json(run_dir / "references" / "reference-manifest.json", default={})

    candidates = {
        item.get("candidate_id"): item
        for item in candidate_manifest.get("candidates", [])
        if item.get("candidate_id")
    }
    candidate_statuses = Counter(item.get("generation_status", "unknown") for item in candidates.values())
    selected = [
        item for item in selected_assets.get("selectedAssets", [])
        if item.get("status") == "selected"
    ]
    selected_failed = [
        item.get("id") for item in selected
        if candidates.get(item.get("id"), {}).get("generation_status") in {"failed", "error"}
    ]
    if selected_failed:
        add(findings, "P0", "failed_candidates_selected", f"{len(selected_failed)} failed candidates are selected.", selected_failed)

    qa_status = str(qa_report.get("summary", {}).get("status") or "")
    qa_stage_status = status.get("stage_status", {}).get("06_qa_packaging")
    qa_is_current = qa_stage_status != "locked"
    if qa_status == "fail" and qa_stage_status == "approved":
        add(findings, "P0", "failed_qa_approved", "QA status is fail but 06_qa_packaging is approved.")
    unroutable_errors = [
        issue.get("issue_id")
        for issue in qa_report.get("issues", [])
        if issue.get("severity") in {"error", "blocker"}
        and issue.get("status") != "fail"
        and issue.get("qa_failed") is not True
    ]
    if unroutable_errors and qa_is_current:
        add(findings, "P0", "qa_errors_not_routable", "QA error/blocker issues are invisible to --process-qa-failures.", unroutable_errors)

    referenced_presets = sorted({
        str(item.get("workflow_preset") or "")
        for item in candidates.values()
        if item.get("workflow_preset")
    })
    available_presets = set(list_presets())
    missing_presets = [item for item in referenced_presets if item not in available_presets]
    if missing_presets:
        add(findings, "P0", "missing_comfyui_presets", "Candidate generation references unavailable ComfyUI presets.", missing_presets)

    expected_prompt_audit = run_dir / "03_visual_candidates" / "prompt-audit.json"
    alternate_prompt_audit = run_dir / "04_visual_candidates" / "prompt-audit.json"
    if not expected_prompt_audit.exists() and alternate_prompt_audit.exists():
        add(findings, "P1", "prompt_audit_path_mismatch", "Prompt audit exists under 04_visual_candidates but QA expects 03_visual_candidates.")

    text_sources = [
        run_dir / "event-input.json",
        run_dir / "brand-guide.json",
        run_dir / "01_event_brief" / "brief.json",
        run_dir / "02_content_planning" / "content-plan.json",
    ]
    broken_text_files = [relative(path) for path in text_sources if path.exists() and looks_mojibake(path.read_text(encoding="utf-8"))]
    if broken_text_files:
        add(findings, "P0", "korean_text_mojibake", "Korean input/output text contains strong mojibake signals.", broken_text_files)

    if candidate_statuses.get("failed", 0):
        add(findings, "P1", "candidate_generation_failures", f"{candidate_statuses['failed']} visual candidates failed generation.")
    if qa_status == "fail" and qa_is_current:
        add(findings, "P1", "qa_failed", f"QA report status is fail with {qa_report.get('summary', {}).get('issues', 0)} issues.")
    elif qa_status in {"warn", "warning"} and qa_is_current:
        add(findings, "P1", "qa_warning", f"QA report has {qa_report.get('summary', {}).get('warnings', 0)} warnings.")
    if status.get("stage_status", {}).get("07_asset_archive") == "done" and not archive.get("assets"):
        add(findings, "P1", "empty_completed_archive", "07_asset_archive is done but contains zero reusable assets.")
    if (
        status.get("stage_status", {}).get("07_asset_archive") in {"done", "done_no_assets"}
        and status.get("stage_status", {}).get("06_qa_packaging") != "approved"
    ):
        add(findings, "P1", "downstream_stage_state_inconsistent", "07_asset_archive is done while 06_qa_packaging is not approved.")
    inconsistent_pairs = find_downstream_state_inconsistencies(status.get("stage_status", {}))
    if inconsistent_pairs:
        add(
            findings,
            "P1",
            "downstream_stage_state_stale",
            "A downstream stage remains complete after an upstream stage was reset.",
            inconsistent_pairs,
        )
    if not selected_assets.get("selectedAssets"):
        add(findings, "P1", "no_selected_assets", "No selected assets recorded.")

    severity_counts = Counter(item["severity"] for item in findings)
    overall = "fail" if severity_counts["P0"] else "warning" if findings else "pass"
    return {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": overall,
        "run": relative(run_dir),
        "services": services,
        "summary": {
            "stageStatus": status.get("stage_status", {}),
            "runState": status.get("run_state", ""),
            "referenceCount": len(reference_manifest.get("assets", [])),
            "candidateStatuses": dict(candidate_statuses),
            "selectedCount": len(selected),
            "selectedFailedCount": len(selected_failed),
            "qaStatus": qa_status if qa_is_current else f"stale:{qa_status}" if qa_status else "",
            "archiveAssetCount": len(archive.get("assets", [])),
            "severityCounts": dict(severity_counts),
        },
        "findings": findings,
    }


def audit_services(findings: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, url in SERVICE_URLS.items():
        try:
            response = requests.get(url, timeout=5)
            result[name] = {"status": "up" if response.ok else "error", "httpStatus": response.status_code}
            if not response.ok:
                add(findings, "P1", f"{name}_service_error", f"{name} returned HTTP {response.status_code}.")
        except requests.RequestException as exc:
            result[name] = {"status": "down", "error": str(exc)}
            add(findings, "P1", f"{name}_service_down", f"{name} service is unavailable.")
    return result


def looks_mojibake(text: str) -> bool:
    compatibility_count = sum(0xF900 <= ord(char) <= 0xFAFF for char in text)
    suspicious = sum(text.count(token) for token in ("?붿", "?대", "?쒗", "?몄", "硫", "寃", "湲"))
    # U+FFFD 치환문자는 디코딩 실패의 진짜 신호. 과거의 ASCII "?" 카운트는
    # 정상 한글 카피의 "~하시겠어요?" 물음표를 mojibake로 오탐했다.
    return compatibility_count >= 3 or suspicious >= 5 or text.count("�") >= 3


def find_downstream_state_inconsistencies(stage_status: dict[str, Any]) -> list[dict[str, str]]:
    inconsistent: list[dict[str, str]] = []
    for upstream_index, upstream in enumerate(STAGE_ORDER[:-1]):
        upstream_status = str(stage_status.get(upstream, "not_started"))
        if upstream_status in COMPLETED_STAGE_STATUSES:
            continue
        for downstream in STAGE_ORDER[upstream_index + 1:]:
            downstream_status = str(stage_status.get(downstream, "not_started"))
            if downstream_status in COMPLETED_STAGE_STATUSES:
                inconsistent.append({
                    "upstream": upstream,
                    "upstreamStatus": upstream_status,
                    "downstream": downstream,
                    "downstreamStatus": downstream_status,
                })
    return inconsistent


def add(findings: list[dict[str, Any]], severity: str, code: str, message: str, evidence: Any = None) -> None:
    findings.append({"severity": severity, "code": code, "message": message, "evidence": evidence})


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Full Pipeline Health",
        "",
        f"- Status: `{report['status']}`",
        f"- Run: `{report['run']}`",
        f"- Run state: `{summary['runState']}`",
        f"- QA: `{summary['qaStatus']}`",
        f"- Candidates: `{summary['candidateStatuses']}`",
        f"- Selected failed: `{summary['selectedFailedCount']}`",
        f"- Archive assets: `{summary['archiveAssetCount']}`",
        "",
        "## Services",
        "",
    ]
    lines.extend(f"- {name}: `{value['status']}`" for name, value in report["services"].items())
    lines.extend(["", "## Findings", ""])
    lines.extend(
        f"- **{item['severity']} {item['code']}**: {item['message']}"
        for item in report["findings"]
    )
    if not report["findings"]:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
