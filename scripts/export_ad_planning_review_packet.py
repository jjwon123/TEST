#!/usr/bin/env python3
"""Export a human review packet for the cosmetics ad-planning quality goal."""

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

from core.utils.json_io import read_json, write_json, write_text
from services.ad_strategy.pilot_selection import select_pilot_cases
from services.ad_strategy.repository import load_examples_for_review, strategy_quality_metrics
from scripts.benchmark_ad_planning import is_final_human_review


DEFAULT_OUTPUT = ROOT / ".tmp" / "model-benchmarks" / "ad-planning-review-packet.json"
DEFAULT_MARKDOWN = ROOT / ".tmp" / "model-benchmarks" / "ad-planning-review-packet.md"
DEFAULT_STRATEGY_SHEET = ROOT / ".tmp" / "model-benchmarks" / "ad-strategy-review-sheet.csv"
DEFAULT_BENCHMARK_SHEET = ROOT / ".tmp" / "model-benchmarks" / "ad-planning-benchmark-review-sheet.csv"
DEFAULT_EVIDENCE_QUEUE = ROOT / ".tmp" / "model-benchmarks" / "cosmetics-evidence-queue.json"
RUBRIC_KEYS = [
    "strategyClarity",
    "targetEmpathy",
    "productConnection",
    "distinctiveness",
    "channelFit",
    "koreanCopyQuality",
    "brandFit",
    "actionability",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json")
    parser.add_argument("--benchmark", type=Path, default=ROOT / ".tmp" / "model-benchmarks" / "cosmetics-planning-benchmark.json")
    parser.add_argument("--external-results", type=Path, default=ROOT / ".tmp" / "model-benchmarks" / "cosmetics-external-results.json")
    parser.add_argument("--reviews", type=Path, default=ROOT / ".tmp" / "model-benchmarks" / "cosmetics-human-reviews.json")
    parser.add_argument("--evidence-queue", type=Path, default=DEFAULT_EVIDENCE_QUEUE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--pilot-limit", type=int, default=5)
    args = parser.parse_args()

    packet = build_packet(
        dataset=read_json(args.dataset.resolve(), default={"cases": []}),
        benchmark=read_json(args.benchmark.resolve(), default={}),
        external_results=read_json(args.external_results.resolve(), default={"results": []}),
        human_reviews=read_json(args.reviews.resolve(), default={"reviews": []}),
        strategy_examples=load_examples_for_review(),
        strategy_metrics=strategy_quality_metrics(),
        evidence_queue=read_json(args.evidence_queue.resolve(), default={"cases": []}),
        provider="local",
        pilot_limit=args.pilot_limit,
    )
    write_json(args.output.resolve(), packet)
    write_text(args.markdown.resolve(), render_markdown(packet))
    print(json.dumps(packet["summary"], ensure_ascii=False))
    return 0


def build_packet(
    *,
    dataset: dict[str, Any],
    benchmark: dict[str, Any],
    external_results: dict[str, Any],
    human_reviews: dict[str, Any],
    strategy_examples: list[dict[str, Any]],
    strategy_metrics: dict[str, Any],
    evidence_queue: dict[str, Any] | None = None,
    provider: str = "local",
    pilot_limit: int = 5,
) -> dict[str, Any]:
    external_by_id = {item.get("caseId"): item for item in external_results.get("results", []) if isinstance(item, dict)}
    reviews_by_id = {item.get("caseId"): item for item in human_reviews.get("reviews", []) if isinstance(item, dict)}
    evidence_by_id = {
        item.get("eventId"): item
        for item in (evidence_queue or {}).get("cases", [])
        if isinstance(item, dict)
    }
    all_cases = [item for item in dataset.get("cases", []) if isinstance(item, dict)]
    cases = select_pilot_cases(dataset, limit=pilot_limit)
    benchmark_queue = [
        build_case_review_item(
            case,
            external_by_id.get(case.get("id"), {}),
            reviews_by_id.get(case.get("id"), {}),
            evidence_by_id.get(case.get("id"), {}),
        )
        for case in cases
    ]
    strategy_queue = build_strategy_queue(strategy_examples)
    selected_or_shortlist = int(strategy_metrics.get("decisions", {}).get("selected", 0)) + int(strategy_metrics.get("decisions", {}).get("shortlist", 0))
    candidate_complete = sum(item["status"] in {"concept_selection_pending", "human_review_pending", "complete"} for item in benchmark_queue)
    human_reviewed = sum(item["humanReviewStatus"] == "reviewed" for item in benchmark_queue)
    blockers = []
    if selected_or_shortlist < 30:
        blockers.append("STRATEGY_REVIEW_BELOW_30")
    if candidate_complete < len(cases):
        blockers.append("PILOT_CANDIDATE_RESULTS_INCOMPLETE")
    if human_reviewed < len(cases):
        blockers.append("PILOT_HUMAN_REVIEWS_INCOMPLETE")
    return {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "status": "ready_for_human_review" if not blockers else "human_review_setup_incomplete",
            "provider": provider,
            "apiKeyAvailable": provider == "openai",
            "fixedEvaluationCases": len(all_cases),
            "pilotLimit": len(cases),
            "pilotCaseIds": [str(item.get("id") or "") for item in cases],
            "pilotExternalReady": candidate_complete,
            "pilotCandidateReady": candidate_complete,
            "pilotHumanReviewed": human_reviewed,
            "strategySelectedOrShortlist": selected_or_shortlist,
            "strategyTarget": 30,
            "blockers": blockers,
        },
        "benchmarkSummary": benchmark.get("summary", {}),
        "reviewArtifacts": {
            "strategyReviewSheet": str(DEFAULT_STRATEGY_SHEET.relative_to(ROOT)).replace("\\", "/"),
            "benchmarkReviewSheet": str(DEFAULT_BENCHMARK_SHEET.relative_to(ROOT)).replace("\\", "/"),
            "reviewPacketJson": str(DEFAULT_OUTPUT.relative_to(ROOT)).replace("\\", "/"),
            "reviewPacketMarkdown": str(DEFAULT_MARKDOWN.relative_to(ROOT)).replace("\\", "/"),
        },
        "reviewInstructions": {
            "strategyDecisions": ["selected", "shortlist", "rejected"],
            "rubricKeys": RUBRIC_KEYS,
            "reasonTags": [
                "generic",
                "weak_insight",
                "awkward_korean",
                "brand_mismatch",
                "unsupported_claim",
                "copied_expression",
                "weak_cta",
                "channel_mismatch",
                "good_hook",
                "good_structure",
                "strong_product_link",
            ],
            "pilotAcceptance": {
                "criticalErrors": 0,
                "averageHumanScoreAtLeast": 4.0,
                "qaWarnings": 0,
                "automaticApprovalAllowed": False,
            },
        },
        "strategyReviewQueue": strategy_queue[:30],
        "benchmarkReviewQueue": benchmark_queue,
    }


def build_case_review_item(
    case: dict[str, Any],
    external: dict[str, Any],
    review: dict[str, Any],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = evidence or {}
    final_human_review = is_final_human_review(review)
    status = "missing_external_result"
    next_action = "로컬 기획 후보를 생성하세요."
    if external.get("status") == "provider_unavailable":
        status = "provider_unavailable"
        next_action = "로컬 생성기로 전환하거나 생성기 오류를 확인하세요."
    elif external.get("status") == "evidence_review_required":
        status = "evidence_review_required"
        next_action = _evidence_next_action(evidence)
    elif external.get("status") == "quality_repair_required":
        status = "quality_repair_required"
        next_action = "콘셉트 선택 전에 실패한 품질 항목을 수정하세요."
    elif external.get("status") == "concept_review_pending":
        status = "concept_selection_pending"
        next_action = "콘셉트 1개를 선택하면 채널별 카피를 만들 수 있습니다."
    elif external.get("status") == "complete":
        if external.get("selectionSource") == "human":
            status = "human_review_pending"
            next_action = "채널별 카피를 검수하고 승인하거나 수정을 요청하세요."
        else:
            status = "concept_selection_pending"
            next_action = "연결 점검용 자동 선택은 최종 선택이 아닙니다. 콘셉트 3안을 비교해 사람이 1개를 선택하세요."
    if final_human_review:
        status = "complete"
        next_action = "검수가 완료되었습니다. 점수 수정이 필요할 때만 다시 여세요."
    return {
        "caseId": case.get("id", ""),
        "eventName": case.get("eventName", ""),
        "eventType": case.get("eventType", ""),
        "product": case.get("product", ""),
        "target": case.get("target", ""),
        "offer": case.get("offer", ""),
        "status": status,
        "nextAction": next_action,
        "providerStatus": _provider_status(external),
        "selectedConceptId": external.get("selectedConceptId", ""),
        "selectionSource": external.get("selectionSource", ""),
        "conceptCount": len(external.get("concepts", {}).get("candidates", [])),
        "copyOutputCount": len(external.get("copyPackage", {}).get("outputs", [])),
        "humanReviewStatus": "reviewed" if final_human_review else "pending",
        "excludedReviewReason": "connection_check_not_final_review" if review and not final_human_review else "",
        "requiredScores": RUBRIC_KEYS,
        "evidence": _evidence_summary(evidence),
    }


def _evidence_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    progress = evidence.get("progress", {}) if isinstance(evidence, dict) else {}
    gaps = evidence.get("gaps", {}) if isinstance(evidence, dict) else {}
    requirements = evidence.get("requirements", {}) if isinstance(evidence, dict) else {}
    return {
        "status": evidence.get("status", "") if isinstance(evidence, dict) else "",
        "selected": int(progress.get("selected") or 0),
        "reviewCandidates": int(progress.get("reviewCandidates") or 0),
        "requiredRoles": list(requirements.get("evidenceTypeLabels") or []),
        "missingRoles": list(gaps.get("evidenceTypeLabels") or []),
        "missingInputs": list(gaps.get("missingInputs") or []),
        "candidateSources": list(progress.get("candidateDistinctSources") or []),
    }


def _evidence_next_action(evidence: dict[str, Any]) -> str:
    summary = _evidence_summary(evidence)
    count = summary["reviewCandidates"]
    roles = " · ".join(summary["missingRoles"] or summary["requiredRoles"])
    parts = [f"후보 {count}개를 검수하세요." if count else "이벤트 전용 근거를 먼저 검수하세요."]
    if roles:
        parts.append(f"확인 역할: {roles}.")
    if summary["missingInputs"]:
        parts.append("추가 입력: " + "; ".join(summary["missingInputs"]))
    return " ".join(parts)


def build_strategy_queue(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]) -> tuple[int, str]:
        decision = item.get("review", {}).get("decision", "unreviewed")
        return (0 if decision == "unreviewed" else 1, str(item.get("id", "")))

    queue = []
    for item in sorted(examples, key=sort_key):
        review = item.get("review", {})
        source = item.get("sourceOriginal", {})
        queue.append({
            "id": item.get("id", ""),
            "industry": item.get("industry", ""),
            "currentDecision": review.get("decision", "unreviewed"),
            "sourceType": item.get("sourceType", ""),
            "sourceBrand": source.get("brand", ""),
            "sourceCopyPreview": _preview(source.get("copy", "")),
            "targetInsight": item.get("targetInsight", ""),
            "hookMechanism": item.get("hookMechanism", ""),
            "persuasionSequence": item.get("persuasionSequence", []),
            "offerMechanism": item.get("offerMechanism", ""),
            "ctaType": item.get("ctaType", ""),
            "missingForSelected": missing_selected_fields(item),
            "requiredScores": RUBRIC_KEYS,
        })
    return queue


def missing_selected_fields(item: dict[str, Any]) -> list[str]:
    return [field for field in ("targetInsight", "hookMechanism", "persuasionSequence", "ctaType") if not item.get(field)]


def render_markdown(packet: dict[str, Any]) -> str:
    summary = packet["summary"]
    lines = [
        "# Ad Planning Review Packet",
        "",
        f"- Status: {summary['status']}",
        f"- Provider: {summary.get('provider', 'local')}",
        f"- Pilot candidate ready: {summary.get('pilotCandidateReady', summary['pilotExternalReady'])}/{summary['pilotLimit']}",
        f"- Pilot human reviewed: {summary['pilotHumanReviewed']}/{summary['pilotLimit']}",
        f"- Strategy selected/shortlist: {summary['strategySelectedOrShortlist']}/{summary['strategyTarget']}",
        f"- Blockers: {', '.join(summary['blockers']) or '-'}",
        "",
        "## Pilot Queue",
        "",
    ]
    for item in packet["benchmarkReviewQueue"]:
        lines.extend([
            f"### {item['caseId']}",
            f"- Event: {item['eventName']} ({item['eventType']})",
            f"- Product: {item['product']}",
            f"- Status: {item['status']}",
            f"- Next action: {item['nextAction']}",
            f"- Provider: {item['providerStatus']}",
            f"- Selection source: {item['selectionSource'] or '-'}",
            f"- Evidence: selected {item['evidence']['selected']} / review candidates {item['evidence']['reviewCandidates']}",
            f"- Evidence roles: {', '.join(item['evidence']['requiredRoles']) or '-'}",
            f"- Missing input: {'; '.join(item['evidence']['missingInputs']) or '-'}",
            "",
        ])
    lines.extend(["## Strategy Queue", ""])
    for item in packet["strategyReviewQueue"]:
        lines.extend([
            f"### {item['id']}",
            f"- Industry: {item['industry']}",
            f"- Current decision: {item['currentDecision']}",
            f"- Source brand: {item['sourceBrand'] or '-'}",
            f"- Source copy preview: {item['sourceCopyPreview'] or '-'}",
            f"- Missing for selected: {', '.join(item['missingForSelected']) or '-'}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def _provider_status(external: dict[str, Any]) -> str:
    executions = external.get("providerExecution") or []
    if executions and isinstance(executions[0], dict):
        first = executions[0]
        return str(first.get("status") or external.get("status") or "")
    return str(external.get("status") or "")


def _preview(value: Any, limit: int = 160) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else f"{text[:limit - 1]}..."


if __name__ == "__main__":
    raise SystemExit(main())
