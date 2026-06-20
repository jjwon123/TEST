#!/usr/bin/env python3
"""Run the fixed cosmetics planning benchmark and aggregate human-review results."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json
from services.ad_strategy.generation import generate_concepts, generate_copy
from services.ad_strategy.planning_engine import build_concept_candidates, build_copy_package, score_planning

DEFAULT_RESULTS = ROOT / ".tmp" / "model-benchmarks" / "cosmetics-external-results.json"
DEFAULT_REVIEWS = ROOT / ".tmp" / "model-benchmarks" / "cosmetics-human-reviews.json"
DEFAULT_REPORT = ROOT / ".tmp" / "model-benchmarks" / "cosmetics-planning-benchmark.json"
RUBRIC_KEYS = {
    "strategyClarity", "targetEmpathy", "productConnection", "distinctiveness",
    "channelFit", "koreanCopyQuality", "brandFit", "actionability",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json")
    parser.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--external-results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--run-external", action="store_true", help="Deprecated alias for --run-candidates --provider openai.")
    parser.add_argument("--run-candidates", action="store_true", help="Generate missing candidate results before reporting.")
    parser.add_argument("--provider", choices=["local", "openai"], default="local", help="Candidate generator to use. Default: local.")
    parser.add_argument("--limit", type=int, default=0, help="Limit candidate generation to the first N missing cases.")
    args = parser.parse_args()
    dataset = read_json(args.dataset.resolve())
    if args.run_external:
        run_external_cases(dataset, args.external_results.resolve(), limit=args.limit, provider="openai")
    elif args.run_candidates:
        run_external_cases(dataset, args.external_results.resolve(), limit=args.limit, provider=args.provider)
    reviews = {item["caseId"]: item for item in read_json(args.reviews.resolve(), default={"reviews": []}).get("reviews", [])}
    external = {item["caseId"]: item for item in read_json(args.external_results.resolve(), default={"results": []}).get("results", [])}
    cases = [evaluate_case(item, reviews.get(item["id"], {}), external.get(item["id"], {})) for item in dataset.get("cases", [])]
    report = aggregate(cases, dataset.get("target", {}))
    write_json(args.output.resolve(), report)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["summary"]["status"] == "pass" else 1


def build_brief(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": case["id"], "event_name": case["eventName"],
        "target": {"summary": case["target"]}, "offer": {"summary": case.get("offer", "")},
        "channels": ["instagram_cardnews", "instagram_feed", "blog_thumbnail", "blog_inline_image"],
        "constraints": {"required_phrases": [case["product"]], "banned_words": ["완치", "치료", "100% 개선"]},
    }


def build_deliverables(brief: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"deliverable_id": channel, "channel_id": channel, "purpose": "benchmark"} for channel in brief["channels"]]


def evaluate_case(case: dict[str, Any], review: dict[str, Any], external: dict[str, Any]) -> dict[str, Any]:
    brief = build_brief(case)
    concepts = build_concept_candidates(brief)
    deliverables = build_deliverables(brief)
    copy = build_copy_package(brief, concepts["candidates"][0], deliverables)
    scorecard = score_planning(brief, concepts, copy)
    scores = [value for value in review.get("scores", {}).values() if isinstance(value, (int, float))]
    blind_order = blind_order_for(case["id"])
    variants = {
        blind_order[0]: _benchmark_variant("A", blind_order[0], {"concepts": concepts, "copyPackage": copy, "scorecard": scorecard}, external),
        blind_order[1]: _benchmark_variant("B", blind_order[1], {"concepts": concepts, "copyPackage": copy, "scorecard": scorecard}, external),
    }
    return {
        "caseId": case["id"],
        "eventType": case["eventType"],
        "baseline": {"concepts": concepts, "copyPackage": copy, "scorecard": scorecard},
        "external": external,
        "blindComparison": {"A": variants[blind_order[0]], "B": variants[blind_order[1]]},
        "humanReview": review,
        "humanAverage": round(sum(scores) / len(scores), 2) if scores else 0,
    }


def aggregate(cases: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
    reviewed = [case for case in cases if case["humanReview"]]
    generated = [case for case in cases if case["external"].get("status") == "complete"]
    candidates = [case for case in cases if case["external"].get("status") in {"concept_review_pending", "complete"}]
    critical = sum(case["external"].get("scorecard", {}).get("criticalErrorCount", 0) for case in generated)
    average = round(sum(case["humanAverage"] for case in reviewed) / len(reviewed), 2) if reviewed else 0
    unchanged = sum(case["humanReview"].get("approved") and not case["humanReview"].get("edited") for case in reviewed)
    preference_rows = [case for case in reviewed if case["humanReview"].get("blindPreferred") in {"A", "B"}]
    external_wins = sum(
        case["humanReview"]["blindPreferred"] == ("A" if blind_order_for(case["caseId"])[0] == "external" else "B")
        for case in preference_rows
    )
    unchanged_rate = round(unchanged / len(reviewed), 3) if reviewed else 0
    preference_rate = round(external_wins / len(preference_rows), 3) if preference_rows else 0
    executions = [
        execution
        for case in generated
        for execution in case["external"].get("providerExecution", [])
        if isinstance(execution, dict)
    ]
    passed = len(generated) == target.get("cases", 20) and len(reviewed) == target.get("cases", 20) and critical == 0 and average >= target.get("averageHumanScore", 4) and unchanged_rate >= target.get("unchangedApprovalRate", .5) and preference_rate >= target.get("blindPreferenceRate", .7)
    return {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "status": "pass" if passed else "incomplete", "cases": len(cases), "externalGenerated": len(generated),
            "candidateGenerated": len(candidates),
            "reviewed": len(reviewed), "criticalErrors": critical, "averageHumanScore": average,
            "criticalErrorEvaluatedCases": len(generated),
            "unchangedApprovalRate": unchanged_rate, "blindPreferenceRate": preference_rate,
            "providerCalls": len(executions),
            "averageLatencyMs": round(sum(item.get("latencyMs", 0) for item in executions) / len(executions), 2) if executions else 0,
            "estimatedCostUsd": round(sum(item.get("estimatedCostUsd", 0) or 0 for item in executions), 6),
        },
        "target": target,
        "cases": cases,
    }


def run_external_cases(dataset: dict[str, Any], output_path: Path, *, limit: int = 0, provider: str = "local") -> dict[str, Any]:
    payload = read_json(output_path, default={"schemaVersion": "1.0.0", "results": []})
    existing = {item["caseId"]: item for item in payload.get("results", [])}
    actionable = [case for case in dataset.get("cases", []) if existing.get(case["id"], {}).get("status") != "complete"]
    for case in actionable[:limit or None]:
        brief = build_brief(case)
        run_dir = output_path.parent / "runs" / case["id"]
        current = existing.get(case["id"], {})
        if current.get("status") == "concept_review_pending" and current.get("selectedConceptId"):
            concepts = current.get("concepts", {})
            selected = next(
                (item for item in concepts.get("candidates", []) if item.get("conceptId") == current.get("selectedConceptId")),
                None,
            )
            if not selected:
                current["status"] = "invalid_concept_selection"
                existing[case["id"]] = current
                continue
            if current.get("provider") == "local" or provider == "local":
                copy_package = build_copy_package(brief, selected, build_deliverables(brief))
                copy_package["provider"] = "local"
                copy_package["providerExecution"] = [_local_execution("copywriter")]
            else:
                copy_package = generate_copy(brief, selected, build_deliverables(brief), run_dir)
            scorecard = score_planning(brief, concepts, copy_package)
            executions = current.get("providerExecution", []) + copy_package.get("providerExecution", [])
            existing[case["id"]] = {
                **current, "status": "complete" if copy_package.get("status") != "provider_unavailable" else "provider_unavailable",
                "copyPackage": copy_package, "scorecard": scorecard, "providerExecution": executions,
            }
        else:
            if provider == "local":
                concepts = build_concept_candidates(brief)
                concepts["provider"] = "local"
                concepts["providerExecution"] = [_local_execution("strategist")]
                concepts["criticReview"] = _local_critic_review(brief, concepts, {})
                concepts["repairHistory"] = []
            else:
                concepts = generate_concepts(brief, run_dir)
            if concepts.get("status") == "provider_unavailable" or not concepts.get("candidates"):
                existing[case["id"]] = {
                    "caseId": case["id"], "status": "provider_unavailable",
                    "provider": provider,
                    "providerExecution": concepts.get("providerExecution", []),
                }
            else:
                existing[case["id"]] = {
                    "caseId": case["id"], "status": "concept_review_pending", "selectedConceptId": "",
                    "provider": provider,
                    "concepts": concepts, "providerExecution": concepts.get("providerExecution", []),
                }
        payload["results"] = [existing[key] for key in sorted(existing)]
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        write_json(output_path, payload)
    return payload


def _local_execution(role: str) -> dict[str, Any]:
    return {
        "provider": "local",
        "model": "deterministic_planning_engine",
        "role": role,
        "status": "ok",
        "latencyMs": 0,
        "estimatedCostUsd": 0,
    }


def _local_critic_review(brief: dict[str, Any], concepts: dict[str, Any], copy_package: dict[str, Any]) -> dict[str, Any]:
    scorecard = score_planning(brief, concepts, copy_package or {"outputs": [], "status": "blocked_pending_concept_selection"})
    return {
        "status": "fail" if scorecard.get("criticalErrorCount") else "revise" if scorecard.get("issues") else "pass",
        "issues": scorecard.get("issues", []),
        "rubric": scorecard.get("rubric", {}),
    }


def select_external_concept(case_id: str, concept_id: str, output_path: Path = DEFAULT_RESULTS) -> dict[str, Any]:
    payload = read_json(output_path, default={"schemaVersion": "1.0.0", "results": []})
    result = next((item for item in payload.get("results", []) if item.get("caseId") == case_id), None)
    if not result or result.get("status") != "concept_review_pending":
        raise ValueError("Benchmark case is not waiting for concept selection.")
    if concept_id not in {item.get("conceptId") for item in result.get("concepts", {}).get("candidates", [])}:
        raise ValueError("Unknown benchmark concept.")
    result["selectedConceptId"] = concept_id
    result["selectedAt"] = datetime.now(timezone.utc).isoformat()
    payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
    write_json(output_path, payload)
    return result


def save_human_review(case_id: str, review: dict[str, Any], reviews_path: Path = DEFAULT_REVIEWS) -> dict[str, Any]:
    payload = read_json(reviews_path, default={"schemaVersion": "1.0.0", "reviews": []})
    records = {item["caseId"]: item for item in payload.get("reviews", [])}
    scores = {
        key: max(1, min(5, int(value)))
        for key, value in (review.get("scores") or {}).items()
        if isinstance(value, (int, float))
    }
    if set(scores) != RUBRIC_KEYS:
        raise ValueError("All eight benchmark rubric scores are required.")
    blind_preferred = str(review.get("blindPreferred") or "").strip().upper()
    if blind_preferred and blind_preferred not in {"A", "B"}:
        raise ValueError("blindPreferred must be A or B when A/B comparison is used.")
    records[case_id] = {
        "caseId": case_id, "scores": scores, "approved": bool(review.get("approved")),
        "edited": bool(review.get("edited")), "blindPreferred": blind_preferred,
        "reasonTags": list(dict.fromkeys(review.get("reasonTags") or [])),
        "reviewNote": str(review.get("reviewNote") or ""), "reviewedAt": datetime.now(timezone.utc).isoformat(),
    }
    payload["reviews"] = [records[key] for key in sorted(records)]
    payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
    write_json(reviews_path, payload)
    return records[case_id]


def blind_order_for(case_id: str) -> tuple[str, str]:
    return ("external", "baseline") if int(hashlib.sha256(case_id.encode()).hexdigest()[:2], 16) % 2 else ("baseline", "external")


def _benchmark_variant(label: str, source: str, baseline: dict[str, Any], external: dict[str, Any]) -> dict[str, Any]:
    value = external if source == "external" else baseline
    return {
        "label": label, "available": bool(value),
        "concepts": value.get("concepts", {}).get("candidates", []),
        "copyPackage": value.get("copyPackage", {}).get("outputs", []),
    }


if __name__ == "__main__":
    raise SystemExit(main())
