#!/usr/bin/env python3
"""Audit whether approved human copy edits are reused by local generation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json  # noqa: E402
from scripts.benchmark_ad_planning import build_brief, build_deliverables  # noqa: E402
from services.ad_strategy.planning_engine import build_copy_package  # noqa: E402


DEFAULT_DATASET = ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json"
DEFAULT_RESULTS = ROOT / ".tmp" / "model-benchmarks" / "cosmetics-external-results.json"
DEFAULT_CORRECTIONS = ROOT / "design_brain_wiki" / "ad_strategy" / "copy-corrections.json"
DEFAULT_OUTPUT = ROOT / ".tmp" / "model-benchmarks" / "copy-correction-loop-audit.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--corrections", type=Path, default=DEFAULT_CORRECTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--verify-application",
        action="store_true",
        help="Freshly generate matching benchmark copy and verify applied correction IDs.",
    )
    args = parser.parse_args()

    dataset = read_json(args.dataset.resolve(), {"cases": []})
    results = read_json(args.results.resolve(), {"results": []})
    corrections = read_json(args.corrections.resolve(), {"records": []})
    verification = (
        verify_application(dataset=dataset, results=results, corrections=corrections)
        if args.verify_application
        else {}
    )
    report = build_audit(
        corrections=corrections,
        verification=verification,
        verification_requested=args.verify_application,
    )
    write_json(args.output.resolve(), report)
    print(json.dumps({"status": report["status"], **report["summary"]}, ensure_ascii=False))
    return 0


def build_audit(
    *,
    corrections: dict[str, Any],
    verification: dict[str, Any] | None = None,
    verification_requested: bool = False,
) -> dict[str, Any]:
    records = [item for item in corrections.get("records", []) if isinstance(item, dict)]
    approved = [item for item in records if item.get("approved") is True]
    active = active_edited_corrections(approved)
    incomplete_ids = [
        str(item.get("id") or "")
        for item in active
        if not correction_is_complete(item)
    ]
    verification = verification or {}
    applied_ids = set(verification.get("appliedIds") or [])
    active_ids = {str(item.get("id") or "") for item in active if item.get("id")}
    missing_ids = sorted(active_ids - applied_ids) if verification_requested else sorted(active_ids)
    verified = bool(active) and verification_requested and not missing_ids and not incomplete_ids

    if not active:
        status = "needs_human_correction"
    elif not verification_requested:
        status = "ready_to_verify"
    elif verified:
        status = "pass"
    else:
        status = "fail"

    checks = {
        "humanCorrectionExists": {
            "pass": bool(active),
            "approvedEditedCount": len(active),
        },
        "recordsComplete": {
            "pass": bool(active) and not incomplete_ids,
            "incompleteIds": incomplete_ids,
        },
        "applicationVerified": {
            "pass": verified,
            "requested": verification_requested,
            "activeIds": sorted(active_ids),
            "appliedIds": sorted(applied_ids),
            "missingIds": missing_ids,
            "cases": verification.get("cases", []),
        },
    }
    return {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "summary": {
            "totalCorrections": len(records),
            "approvedCorrections": len(approved),
            "approvedEditedCorrections": len(active),
            "verifiedAppliedCorrections": len(active_ids & applied_ids),
            "pendingVerification": len(missing_ids),
        },
        "checks": checks,
        "nextAction": next_action(status),
    }


def active_edited_corrections(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in records:
        if item.get("industry") != "cosmetics_skincare":
            continue
        if item.get("originalCopy") == item.get("editedCopy"):
            continue
        key = (
            str(item.get("brandName") or "").strip().lower(),
            str(item.get("eventId") or ""),
            str(item.get("channelId") or ""),
        )
        current = latest.get(key)
        item_stamp = str(item.get("updatedAt") or item.get("createdAt") or "")
        current_stamp = str((current or {}).get("updatedAt") or (current or {}).get("createdAt") or "")
        if current is None or item_stamp >= current_stamp:
            latest[key] = item
    return list(latest.values())


def correction_is_complete(item: dict[str, Any]) -> bool:
    required = ("id", "eventId", "eventName", "brandName", "industry", "channelId", "model")
    return (
        all(str(item.get(field) or "").strip() for field in required)
        and isinstance(item.get("originalCopy"), dict)
        and isinstance(item.get("editedCopy"), dict)
    )


def verify_application(
    *,
    dataset: dict[str, Any],
    results: dict[str, Any],
    corrections: dict[str, Any],
) -> dict[str, Any]:
    active = active_edited_corrections([
        item for item in corrections.get("records", [])
        if isinstance(item, dict) and item.get("approved") is True
    ])
    active_by_event: dict[str, list[dict[str, Any]]] = {}
    for item in active:
        active_by_event.setdefault(str(item.get("eventId") or ""), []).append(item)

    cases_by_id = {str(item.get("id") or ""): item for item in dataset.get("cases", [])}
    results_by_id = {str(item.get("caseId") or ""): item for item in results.get("results", [])}
    applied_ids: set[str] = set()
    case_reports: list[dict[str, Any]] = []

    for event_id, event_corrections in sorted(active_by_event.items()):
        case = cases_by_id.get(event_id)
        result = results_by_id.get(event_id, {})
        expected_ids = sorted(str(item.get("id") or "") for item in event_corrections if item.get("id"))
        if not case:
            case_reports.append({
                "eventId": event_id,
                "status": "dataset_case_missing",
                "expectedIds": expected_ids,
                "appliedIds": [],
            })
            continue
        concepts = (result.get("concepts") or {}).get("candidates") or []
        selected_id = str(result.get("selectedConceptId") or "")
        selected = next((item for item in concepts if item.get("conceptId") == selected_id), None)
        if not selected:
            case_reports.append({
                "eventId": event_id,
                "status": "selected_concept_missing",
                "expectedIds": expected_ids,
                "appliedIds": [],
            })
            continue
        package = build_copy_package(build_brief(case), selected, build_deliverables(build_brief(case)))
        event_applied = sorted(set((package.get("correctionSearch") or {}).get("appliedIds") or []))
        applied_ids.update(event_applied)
        case_reports.append({
            "eventId": event_id,
            "status": "pass" if set(expected_ids).issubset(event_applied) else "correction_not_applied",
            "expectedIds": expected_ids,
            "appliedIds": event_applied,
        })
    return {"appliedIds": sorted(applied_ids), "cases": case_reports}


def next_action(status: str) -> str:
    return {
        "needs_human_correction": "카피 한 건을 실제로 수정하고 검수 저장을 눌러 교정 데이터를 만드세요.",
        "ready_to_verify": "교정 학습 확인을 실행해 같은 이벤트 재생성에 수정문이 반영되는지 확인하세요.",
        "pass": "사람이 수정한 문구가 같은 이벤트의 다음 생성에 반영됩니다.",
        "fail": "적용되지 않은 교정의 이벤트·채널·생성 원문 일치 여부를 확인하세요.",
    }[status]


if __name__ == "__main__":
    raise SystemExit(main())
