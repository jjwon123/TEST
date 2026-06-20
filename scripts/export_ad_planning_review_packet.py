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
from services.ad_strategy.repository import load_examples_for_review, strategy_quality_metrics


DEFAULT_OUTPUT = ROOT / ".tmp" / "model-benchmarks" / "ad-planning-review-packet.json"
DEFAULT_MARKDOWN = ROOT / ".tmp" / "model-benchmarks" / "ad-planning-review-packet.md"
DEFAULT_STRATEGY_SHEET = ROOT / ".tmp" / "model-benchmarks" / "ad-strategy-review-sheet.csv"
DEFAULT_BENCHMARK_SHEET = ROOT / ".tmp" / "model-benchmarks" / "ad-planning-benchmark-review-sheet.csv"
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
    provider: str = "local",
    pilot_limit: int = 5,
) -> dict[str, Any]:
    external_by_id = {item.get("caseId"): item for item in external_results.get("results", []) if isinstance(item, dict)}
    reviews_by_id = {item.get("caseId"): item for item in human_reviews.get("reviews", []) if isinstance(item, dict)}
    cases = dataset.get("cases", [])
    benchmark_queue = [
        build_case_review_item(case, external_by_id.get(case.get("id"), {}), reviews_by_id.get(case.get("id"), {}))
        for case in cases
    ]
    strategy_queue = build_strategy_queue(strategy_examples)
    selected_or_shortlist = int(strategy_metrics.get("decisions", {}).get("selected", 0)) + int(strategy_metrics.get("decisions", {}).get("shortlist", 0))
    candidate_complete = sum(item["status"] in {"concept_selection_pending", "human_review_pending", "complete"} for item in benchmark_queue)
    human_reviewed = sum(item["humanReviewStatus"] == "reviewed" for item in benchmark_queue)
    blockers = []
    if selected_or_shortlist < 30:
        blockers.append("STRATEGY_REVIEW_BELOW_30")
    if candidate_complete < min(pilot_limit, len(cases)):
        blockers.append("PILOT_CANDIDATE_RESULTS_INCOMPLETE")
    if human_reviewed < min(pilot_limit, len(cases)):
        blockers.append("PILOT_HUMAN_REVIEWS_INCOMPLETE")
    return {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "status": "ready_for_human_review" if not blockers else "human_review_setup_incomplete",
            "provider": provider,
            "apiKeyAvailable": provider == "openai",
            "fixedEvaluationCases": len(cases),
            "pilotLimit": min(pilot_limit, len(cases)),
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
        "benchmarkReviewQueue": benchmark_queue[:pilot_limit],
    }


def build_case_review_item(case: dict[str, Any], external: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    status = "missing_external_result"
    next_action = "Run local candidate generation."
    if external.get("status") == "provider_unavailable":
        status = "provider_unavailable"
        next_action = "Switch to local provider or inspect provider failure."
    elif external.get("status") == "concept_review_pending":
        status = "concept_selection_pending"
        next_action = "Select one concept before copy generation."
    elif external.get("status") == "complete":
        status = "human_review_pending"
        next_action = "Complete blind A/B copy review."
    if review:
        status = "complete"
        next_action = "No action required unless scores need correction."
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
        "conceptCount": len(external.get("concepts", {}).get("candidates", [])),
        "copyOutputCount": len(external.get("copyPackage", {}).get("outputs", [])),
        "humanReviewStatus": "reviewed" if review else "pending",
        "requiredScores": RUBRIC_KEYS,
    }


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
