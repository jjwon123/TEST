#!/usr/bin/env python3
"""Audit the 5-case cosmetics pilot against the current quality target."""

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
from services.ad_strategy.pilot_selection import select_pilot_cases  # noqa: E402
from services.ad_strategy.text_quality import text_artifact_summary  # noqa: E402
from scripts.benchmark_ad_planning import is_final_human_review  # noqa: E402


DEFAULT_DATASET = ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json"
DEFAULT_RESULTS = ROOT / ".tmp" / "model-benchmarks" / "cosmetics-external-results.json"
DEFAULT_REVIEWS = ROOT / ".tmp" / "model-benchmarks" / "cosmetics-human-reviews.json"
DEFAULT_OUTPUT = ROOT / ".tmp" / "model-benchmarks" / "cosmetics-pilot-goal-audit.json"
RUBRIC_KEYS = (
    "strategyClarity",
    "targetEmpathy",
    "productConnection",
    "distinctiveness",
    "channelFit",
    "koreanCopyQuality",
    "brandFit",
    "actionability",
)
DISTINCT_FIELDS = (
    "targetInsight",
    "corePromise",
    "emotionalDirection",
    "persuasionSequence",
    "offerPresentation",
    "cta",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    report = build_audit(
        dataset=read_json(args.dataset.resolve(), {"cases": []}),
        results=read_json(args.results.resolve(), {"results": []}),
        reviews=read_json(args.reviews.resolve(), {"reviews": []}),
        limit=max(1, args.limit),
    )
    write_json(args.output.resolve(), report)
    print(json.dumps({"status": report["status"], **report["summary"]}, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


def build_audit(*, dataset: dict[str, Any], results: dict[str, Any], reviews: dict[str, Any], limit: int = 5) -> dict[str, Any]:
    cases = select_pilot_cases(dataset, limit=limit)
    result_by_id = {item.get("caseId"): item for item in results.get("results", []) if isinstance(item, dict)}
    review_by_id = {item.get("caseId"): item for item in reviews.get("reviews", []) if isinstance(item, dict)}
    case_reports = [audit_case(case, result_by_id.get(case.get("id"), {}), review_by_id.get(case.get("id"), {})) for case in cases]

    reviewed = [item for item in case_reports if item["checks"]["humanReviewed"]["pass"]]
    unchanged_approved = [item for item in reviewed if item["review"].get("approved") is True and item["review"].get("edited") is False]
    average_score = average([item["review"].get("averageScore", 0) for item in reviewed])
    critical_error_count = sum(1 for item in case_reports if not item["checks"]["criticalErrorsZero"]["pass"])
    pass_count = sum(1 for item in case_reports if item["status"] == "pass")
    checks = {
        "pilotCaseCount": {"pass": len(cases) == limit, "value": len(cases), "target": limit},
        "candidateReady": {"pass": all(item["checks"]["candidateReady"]["pass"] for item in case_reports), "value": sum(item["checks"]["candidateReady"]["pass"] for item in case_reports), "target": len(cases)},
        "copyReady": {"pass": all(item["checks"]["copyReady"]["pass"] for item in case_reports), "value": sum(item["checks"]["copyReady"]["pass"] for item in case_reports), "target": len(cases)},
        "humanReviewed": {"pass": len(reviewed) == len(cases) and bool(cases), "value": len(reviewed), "target": len(cases)},
        "criticalErrorsZero": {"pass": critical_error_count == 0 and bool(cases), "value": critical_error_count, "target": 0},
        "averageHumanScore": {"pass": len(reviewed) == len(cases) and average_score >= 4.0, "value": round(average_score, 2), "target": 4.0},
        "unchangedApprovalRate": {
            "pass": len(reviewed) == len(cases) and rate(len(unchanged_approved), len(reviewed)) >= 0.5,
            "value": round(rate(len(unchanged_approved), len(reviewed)), 3),
            "target": 0.5,
        },
        "conceptsDistinct": {"pass": all(item["checks"]["conceptsDistinct"]["pass"] for item in case_reports), "value": sum(item["checks"]["conceptsDistinct"]["pass"] for item in case_reports), "target": len(cases)},
        "evidenceConnected": {"pass": all(item["checks"]["evidenceConnected"]["pass"] for item in case_reports), "value": sum(item["checks"]["evidenceConnected"]["pass"] for item in case_reports), "target": len(cases)},
    }
    errors = [name for name, item in checks.items() if not item["pass"]]
    return {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not errors else "fail",
        "summary": {
            "pilotLimit": limit,
            "caseCount": len(cases),
            "pilotCaseIds": [str(item.get("id") or "") for item in cases],
            "passedCases": pass_count,
            "candidateReady": checks["candidateReady"]["value"],
            "copyReady": checks["copyReady"]["value"],
            "humanReviewed": len(reviewed),
            "criticalErrorCount": critical_error_count,
            "averageHumanScore": round(average_score, 2),
            "unchangedApprovalRate": round(rate(len(unchanged_approved), len(reviewed)), 3),
            "eventEvidenceMatched": checks["evidenceConnected"]["value"],
            "eventEvidenceTarget": checks["evidenceConnected"]["target"],
        },
        "errors": errors,
        "checks": checks,
        "cases": case_reports,
        "nextActions": next_actions(errors, case_reports),
    }


def audit_case(case: dict[str, Any], result: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    concepts_doc = result.get("concepts") or {}
    copy_package = result.get("copyPackage") or {}
    concepts = concepts_doc.get("candidates") or []
    copy_outputs = copy_package.get("outputs") or []
    scorecard = result.get("scorecard") if isinstance(result.get("scorecard"), dict) else {}
    scorecard_critical_count = int(scorecard.get("criticalErrorCount") or 0)
    concept_artifacts = text_artifact_summary(result.get("concepts") or {})
    copy_artifacts = text_artifact_summary(result.get("copyPackage") or {})
    visible_artifacts = text_artifact_summary({
        "case": case,
        "reviewNote": review.get("reviewNote", ""),
    })
    all_artifacts = {
        "brokenKoreanCount": concept_artifacts["brokenKoreanCount"] + copy_artifacts["brokenKoreanCount"] + visible_artifacts["brokenKoreanCount"],
        "rawJsonCount": concept_artifacts["rawJsonCount"] + copy_artifacts["rawJsonCount"] + visible_artifacts["rawJsonCount"],
        "rawHtmlCount": concept_artifacts["rawHtmlCount"] + copy_artifacts["rawHtmlCount"] + visible_artifacts["rawHtmlCount"],
        "programmingArtifactCount": concept_artifacts["programmingArtifactCount"] + copy_artifacts["programmingArtifactCount"] + visible_artifacts["programmingArtifactCount"],
        "samples": {
            "brokenKorean": concept_artifacts["samples"]["brokenKorean"] + copy_artifacts["samples"]["brokenKorean"] + visible_artifacts["samples"]["brokenKorean"],
            "rawJson": concept_artifacts["samples"]["rawJson"] + copy_artifacts["samples"]["rawJson"] + visible_artifacts["samples"]["rawJson"],
            "rawHtml": concept_artifacts["samples"]["rawHtml"] + copy_artifacts["samples"]["rawHtml"] + visible_artifacts["samples"]["rawHtml"],
            "programmingArtifact": concept_artifacts["samples"]["programmingArtifact"] + copy_artifacts["samples"]["programmingArtifact"] + visible_artifacts["samples"]["programmingArtifact"],
        },
    }
    review_scores = review.get("scores") if isinstance(review.get("scores"), dict) else {}
    average_review_score = average([float(review_scores.get(key) or 0) for key in RUBRIC_KEYS if review_scores.get(key) is not None])
    final_human_review = is_final_human_review(review)
    case_id = str(case.get("id") or "")
    concept_evidence_ready = (
        concepts_doc.get("marketingEvidenceStatus") == "ready"
        and str(concepts_doc.get("marketingEvidenceEventId") or "") == case_id
    )
    checks = {
        "candidateReady": {
            "pass": len(concepts) == 3 and concept_evidence_ready,
            "conceptCount": len(concepts),
            "evidenceReady": concept_evidence_ready,
        },
        "copyReady": {"pass": result.get("status") == "complete" and len(copy_outputs) > 0, "status": result.get("status"), "copyOutputCount": len(copy_outputs)},
        "humanReviewed": {
            "pass": final_human_review,
            "approved": review.get("approved") if final_human_review else None,
            "edited": review.get("edited") if final_human_review else None,
            "averageScore": round(average_review_score, 2) if final_human_review else 0,
            "excludedReason": "connection_check_not_final_review" if review and not final_human_review else "",
        },
        "noCriticalArtifacts": {
            "pass": not any(int(all_artifacts.get(key) or 0) for key in ("brokenKoreanCount", "rawJsonCount", "rawHtmlCount", "programmingArtifactCount")),
            "artifacts": all_artifacts,
        },
        "scorecardCriticalErrorsZero": {
            "pass": scorecard_critical_count == 0,
            "criticalErrorCount": scorecard_critical_count,
            "issues": [
                item for item in scorecard.get("issues", [])
                if isinstance(item, dict) and item.get("severity") == "critical"
            ],
        },
        "conceptsDistinct": concept_distinct_check(concepts),
        "evidenceConnected": evidence_check(str(case.get("id") or ""), concepts_doc, copy_package),
    }
    checks["criticalErrorsZero"] = {
        "pass": checks["noCriticalArtifacts"]["pass"] and checks["scorecardCriticalErrorsZero"]["pass"],
        "artifactPass": checks["noCriticalArtifacts"]["pass"],
        "scorecardPass": checks["scorecardCriticalErrorsZero"]["pass"],
    }
    errors = [name for name, item in checks.items() if not item["pass"]]
    return {
        "caseId": case.get("id", ""),
        "eventName": case.get("eventName", ""),
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "checks": checks,
        "review": {
            "approved": review.get("approved") if final_human_review else None,
            "edited": review.get("edited") if final_human_review else None,
            "averageScore": round(average_review_score, 2) if final_human_review else 0,
        },
    }


def concept_distinct_check(concepts: list[dict[str, Any]]) -> dict[str, Any]:
    if len(concepts) != 3:
        return {"pass": False, "reason": "concept_count_not_three", "pairDifferences": []}
    pair_diffs: list[dict[str, Any]] = []
    for left_index, left in enumerate(concepts):
        for right in concepts[left_index + 1:]:
            changed = [field for field in DISTINCT_FIELDS if normalize(left.get(field)) != normalize(right.get(field))]
            pair_diffs.append({
                "left": left.get("conceptId"),
                "right": right.get("conceptId"),
                "differentFields": changed,
                "differentFieldCount": len(changed),
            })
    return {
        "pass": all(item["differentFieldCount"] >= 2 for item in pair_diffs),
        "pairDifferences": pair_diffs,
    }


def evidence_check(case_id: str, concepts_doc: dict[str, Any], copy_package: dict[str, Any]) -> dict[str, Any]:
    concepts = concepts_doc.get("candidates") or []
    copy_outputs = copy_package.get("outputs") or []
    concept_event_id = str(concepts_doc.get("marketingEvidenceEventId") or "")
    copy_event_id = str(copy_package.get("marketingEvidenceEventId") or "")
    event_match = bool(case_id) and concept_event_id == case_id and copy_event_id == case_id
    ready = (
        concepts_doc.get("marketingEvidenceStatus") == "ready"
        and copy_package.get("marketingEvidenceStatus") == "ready"
    )
    concept_ok = len(concepts) == 3 and all(len(item.get("marketingSignalIds") or []) >= 3 for item in concepts)
    copy_ok = bool(copy_outputs) and all(len((item.get("planningEvidence") or {}).get("marketingSignalIds") or []) > 0 for item in copy_outputs)
    return {
        "pass": event_match and ready and concept_ok and copy_ok,
        "expectedEventId": case_id,
        "conceptEvidenceEventId": concept_event_id,
        "copyEvidenceEventId": copy_event_id,
        "eventMatch": event_match,
        "evidenceReady": ready,
        "conceptsWithEvidence": sum(len(item.get("marketingSignalIds") or []) >= 3 for item in concepts),
        "copyOutputsWithEvidence": sum(len((item.get("planningEvidence") or {}).get("marketingSignalIds") or []) > 0 for item in copy_outputs),
        "copyOutputCount": len(copy_outputs),
    }


def next_actions(errors: list[str], case_reports: list[dict[str, Any]] | None = None) -> list[str]:
    case_reports = case_reports or []
    actions: list[str] = []
    if "candidateReady" in errors:
        evidence_blocked = [
            item["eventName"] or item["caseId"]
            for item in case_reports
            if not item["checks"]["candidateReady"]["pass"]
            and not item["checks"]["candidateReady"].get("evidenceReady")
        ]
        concept_missing = [
            item["eventName"] or item["caseId"]
            for item in case_reports
            if int(item["checks"]["candidateReady"].get("conceptCount") or 0) != 3
        ]
        if evidence_blocked:
            actions.append(f"{', '.join(evidence_blocked)}의 이벤트 전용 근거를 먼저 검수한다.")
        if concept_missing:
            actions.append(f"{', '.join(concept_missing)}의 콘셉트 3안을 다시 생성한다.")
    if "copyReady" in errors:
        selection_ready = [
            item["eventName"] or item["caseId"]
            for item in case_reports
            if item["checks"]["candidateReady"]["pass"] and not item["checks"]["copyReady"]["pass"]
        ]
        if selection_ready:
            actions.append(f"{', '.join(selection_ready)}에서 콘셉트 1개를 사람이 선택해 채널별 카피를 생성한다.")
    mapping = {
        "humanReviewed": "파일럿 5건의 최종 카피를 사람이 채점하고 수정 여부를 저장한다.",
        "criticalErrorsZero": "깨진 한글, JSON 노출, 프로그래밍 구조가 섞인 결과를 폐기하고 재생성한다.",
        "averageHumanScore": "평균 4.0 미만 케이스의 훅, 타깃, 제품 연결을 보강한다.",
        "unchangedApprovalRate": "수정 없이 승인되지 못한 케이스의 수정문을 교정 데이터로 저장한다.",
        "conceptsDistinct": "콘셉트 3안의 타깃 인사이트, 약속, 설득 구조, CTA가 실제로 갈라지게 재작성한다.",
        "evidenceConnected": "최종 카피까지 생성된 뒤 콘셉트와 카피가 같은 이벤트 근거를 사용하는지 확인한다.",
    }
    has_human_reviews = any(item["checks"]["humanReviewed"]["pass"] for item in case_reports)
    actions.extend(
        mapping[item]
        for item in errors
        if item in mapping
        and (has_human_reviews or item not in {"averageHumanScore", "unchangedApprovalRate"})
    )
    return actions


def normalize(value: Any) -> str:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return " ".join(str(value or "").split()).lower()


def average(values: list[float]) -> float:
    filtered = [float(item) for item in values if item is not None]
    return sum(filtered) / len(filtered) if filtered else 0.0


def rate(part: int, whole: int) -> float:
    return float(part) / float(whole) if whole else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
