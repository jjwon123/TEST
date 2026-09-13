#!/usr/bin/env python3
"""Run the fixed cosmetics planning benchmark and aggregate human-review results."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json
from services.ad_strategy.generation import generate_concepts, generate_copy
from services.ad_strategy.local_critic import review_local_concepts, review_local_copy
from services.ad_strategy.planning_engine import build_concept_candidates, build_copy_package, detect_industry, score_planning
from services.ad_strategy.quality_gate import INDUSTRY_TERMS, INTERNAL_MARKERS, unsupported_claims
from services.ad_strategy.text_quality import has_blocking_text_artifacts, particle_mismatches

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
    parser.add_argument("--select-pending-concepts", action="store_true", help="Connection-check mode: select a default concept for pending cases and generate copy without marking human review complete.")
    parser.add_argument("--default-concept-id", default="concept_01", help="Concept id to select in --select-pending-concepts mode. Falls back to the first candidate when missing.")
    parser.add_argument("--provider", choices=["local", "openai"], default="local", help="Candidate generator to use. Default: local.")
    parser.add_argument("--limit", type=int, default=0, help="Limit candidate generation to the first N missing cases.")
    args = parser.parse_args()
    dataset = read_json(args.dataset.resolve())
    if args.run_external:
        run_external_cases(dataset, args.external_results.resolve(), limit=args.limit, provider="openai")
    elif args.run_candidates:
        run_external_cases(dataset, args.external_results.resolve(), limit=args.limit, provider=args.provider)
    if args.select_pending_concepts:
        select_pending_concepts_for_connection_check(
            dataset,
            args.external_results.resolve(),
            limit=args.limit,
            provider=args.provider,
            default_concept_id=args.default_concept_id,
        )
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
        "event_type": str(case.get("eventType") or ""),
        "brand_name": str(case.get("brandName") or "benchmark_cosmetics"),
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
    review_eligible = is_final_human_review(review)
    scores = [
        value for value in review.get("scores", {}).values()
        if review_eligible and isinstance(value, (int, float))
    ]
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
        "humanReviewEligible": review_eligible,
        "humanAverage": round(sum(scores) / len(scores), 2) if scores else 0,
    }


def aggregate(cases: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
    reviewed = [case for case in cases if case.get("humanReviewEligible")]
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


def run_external_cases(
    dataset: dict[str, Any],
    output_path: Path,
    *,
    limit: int = 0,
    provider: str = "local",
    force_refresh: bool = False,
) -> dict[str, Any]:
    payload = read_json(output_path, default={"schemaVersion": "1.0.0", "results": []})
    existing = {item["caseId"]: item for item in payload.get("results", [])}
    actionable = [
        case for case in dataset.get("cases", [])
        if force_refresh
        or existing.get(case["id"], {}).get("status") != "complete"
        or result_needs_refresh(existing.get(case["id"], {}))
    ]
    for case in actionable[:limit or None]:
        brief = build_brief(case)
        run_dir = output_path.parent / "runs" / case["id"]
        current = existing.get(case["id"], {})
        if current.get("status") == "complete" and (force_refresh or result_needs_refresh(current)) and provider == "local":
            concepts = build_concept_candidates(brief)
            concepts["provider"] = "local"
            concepts["providerExecution"] = [_local_execution("strategist")]
            concepts["criticReview"] = _local_critic_review(brief, concepts, {})
            concepts["repairHistory"] = [{"reason": "stale_or_low_quality_cache_refresh", "at": datetime.now(timezone.utc).isoformat()}]
            existing[case["id"]] = {
                "caseId": case["id"],
                "status": _concept_result_status(concepts, case["id"]),
                "selectedConceptId": "",
                "provider": "local",
                "concepts": concepts,
                "providerExecution": concepts.get("providerExecution", []),
                "refreshedAt": datetime.now(timezone.utc).isoformat(),
                "refreshReason": "stale_or_low_quality_cache_requires_new_human_selection",
            }
        elif current.get("status") in {"concept_review_pending", "quality_repair_required"} and current.get("selectedConceptId"):
            concepts = current.get("concepts", {})
            if not _concept_evidence_ready(concepts, case["id"]):
                existing[case["id"]] = {
                    **current,
                    "status": "evidence_review_required",
                    "selectedConceptId": "",
                    "selectionSource": "",
                    "evidenceStatus": concepts.get("marketingEvidenceStatus", "needs_signal_review"),
                    "invalidationReason": "event_evidence_not_ready",
                }
                existing[case["id"]].pop("copyPackage", None)
                payload["results"] = [existing[key] for key in sorted(existing)]
                payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
                write_json(output_path, payload)
                continue
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
                copy_package["criticReview"] = review_local_copy(brief, concepts, copy_package)
                copy_package["repairHistory"] = []
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
                    "caseId": case["id"], "status": _concept_result_status(concepts, case["id"]), "selectedConceptId": "",
                    "provider": provider,
                    "concepts": concepts, "providerExecution": concepts.get("providerExecution", []),
                }
        payload["results"] = [existing[key] for key in sorted(existing)]
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        write_json(output_path, payload)
    return payload


def select_pending_concepts_for_connection_check(
    dataset: dict[str, Any],
    output_path: Path,
    *,
    limit: int = 0,
    provider: str = "local",
    default_concept_id: str = "concept_01",
) -> dict[str, Any]:
    """Select default concepts for pending cases so copy generation can be integration-tested.

    This intentionally does not create human reviews or final approvals.
    """
    payload = read_json(output_path, default={"schemaVersion": "1.0.0", "results": []})
    case_by_id = {case.get("id"): case for case in dataset.get("cases", [])}
    selected_case_ids: list[str] = []
    for result in payload.get("results", []):
        if result.get("status") != "concept_review_pending" or result.get("selectedConceptId"):
            continue
        candidates = (result.get("concepts") or {}).get("candidates") or []
        if not candidates:
            continue
        selected = next((item for item in candidates if item.get("conceptId") == default_concept_id), None) or candidates[0]
        result["selectedConceptId"] = selected.get("conceptId")
        result["selectedAt"] = datetime.now(timezone.utc).isoformat()
        result["selectionSource"] = "connection_check_default"
        result["selectionNote"] = "연결 확인용 기본 콘셉트 선택입니다. 사람의 최종 선호나 승인으로 보지 않습니다."
        if result.get("caseId") in case_by_id:
            selected_case_ids.append(result["caseId"])
        if limit and len(selected_case_ids) >= limit:
            break
    payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
    write_json(output_path, payload)
    selected_cases = [case_by_id[case_id] for case_id in selected_case_ids if case_id in case_by_id]
    if selected_cases:
        return run_external_cases({"cases": selected_cases}, output_path, provider=provider)
    return payload


def _concept_evidence_ready(concepts: dict[str, Any], case_id: str) -> bool:
    return (
        concepts.get("marketingEvidenceStatus") == "ready"
        and str(concepts.get("marketingEvidenceEventId") or "") == str(case_id or "")
    )


def _concept_result_status(concepts: dict[str, Any], case_id: str) -> str:
    if not _concept_evidence_ready(concepts, case_id):
        return "evidence_review_required"
    critic = concepts.get("criticReview") or {}
    issues = critic.get("issues") or []
    # Warnings are carried into the human concept/copy review. Only a failed
    # critic or an explicit error severity is allowed to close the journey.
    if critic.get("status") == "fail" or any(item.get("severity") == "error" for item in issues if isinstance(item, dict)):
        return "quality_repair_required"
    return "concept_review_pending"


def result_needs_refresh(result: dict[str, Any]) -> bool:
    if not result:
        return False
    if has_blocking_text_artifacts(result.get("concepts", {})) or has_blocking_text_artifacts(result.get("copyPackage", {})):
        return True
    scorecard = result.get("scorecard") if isinstance(result.get("scorecard"), dict) else {}
    if result.get("status") == "complete" and int(scorecard.get("criticalErrorCount") or 0) > 0:
        return True
    concepts_doc = result.get("concepts") if isinstance(result.get("concepts"), dict) else {}
    copy_doc = result.get("copyPackage") if isinstance(result.get("copyPackage"), dict) else {}
    event_id = str(result.get("caseId") or "")
    if event_id and (
        str(concepts_doc.get("marketingEvidenceEventId") or "") != event_id
        or (
            result.get("status") == "complete"
            and str(copy_doc.get("marketingEvidenceEventId") or "") != event_id
        )
    ):
        return True
    concepts = concepts_doc.get("candidates") or []
    if concepts and any(len(item.get("marketingSignalIds") or []) < 3 for item in concepts):
        return True
    if result.get("status") == "complete":
        outputs = (result.get("copyPackage") or {}).get("outputs") or []
        if not outputs:
            return True
        if any(not (item.get("planningEvidence") or {}).get("marketingSignalIds") for item in outputs):
            return True
    return False


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
    if not (copy_package or {}).get("outputs"):
        return review_local_concepts(brief, concepts)
    return review_local_copy(brief, concepts, copy_package)


def _local_concept_only_critic_review(brief: dict[str, Any], concepts: dict[str, Any]) -> dict[str, Any]:
    return review_local_concepts(brief, concepts)


def _concept_rubric(brief: dict[str, Any], concepts: dict[str, Any]) -> tuple[dict[str, int], list[dict[str, str]]]:
    candidates = concepts.get("candidates") or []
    issues: list[dict[str, str]] = []
    texts = [_concept_user_text(item) for item in candidates]
    product = _brief_product(brief)
    offer = _brief_offer(brief)

    required_fields = ("name", "targetInsight", "corePromise", "persuasionSequence", "cta", "differencePoint")
    complete_count = sum(all(item.get(field) for field in required_fields) for item in candidates)
    strategy_score = 4 if len(candidates) == 3 and complete_count == 3 else 3 if complete_count >= 2 else 2

    generic_markers = ("이번 제안이 필요한 고객", "피부 고민 고객", "고객 니즈", "좋은 선택", "자세히 알아보기")
    grounded_targets = sum(
        len(str(item.get("targetInsight") or "").strip()) >= 35
        and bool((item.get("marketingEvidence") or {}).get("primaryInsight"))
        and not any(marker in str(item.get("targetInsight") or "") for marker in generic_markers)
        for item in candidates
    )
    target_score = 4 if grounded_targets == 3 else 3 if grounded_targets >= 2 else 2 if grounded_targets == 1 else 1
    if target_score < 4:
        issues.append({"severity": "warning", "id": "weak_target_insight", "message": "구체적인 고객 상황과 핵심 근거가 연결되지 않은 타깃 인사이트가 있습니다."})

    product_connected = sum(
        bool(product)
        and product in str(item.get("corePromise") or "")
        and product in text
        for item, text in zip(candidates, texts)
    )
    offer_connected = sum(not offer or _offer_tokens_connected(offer, text) for text in texts)
    product_score = 4 if product_connected == 3 and offer_connected == 3 else 3 if product_connected >= 2 else 2 if product_connected else 1
    if product_score < 4:
        issues.append({"severity": "warning", "id": "weak_product_connection", "message": "제품과 입력 혜택이 세 콘셉트의 설득 논리에 충분히 연결되지 않았습니다."})

    primary_sets = [
        frozenset((item.get("marketingEvidence") or {}).get("primarySignalIds") or [])
        for item in candidates
    ]
    strategy_distinct = len(candidates) == 3 and _concept_candidates_differ_by_two_fields(candidates)
    evidence_distinct = len(primary_sets) == 3 and all(primary_sets) and len(set(primary_sets)) == 3
    distinctiveness_score = 4 if strategy_distinct and evidence_distinct else 3 if strategy_distinct else 1
    if distinctiveness_score < 4:
        issues.append({"severity": "warning", "id": "weak_evidence_distinction", "message": "전략 문장은 다르지만 각 안을 만든 핵심 근거가 충분히 분리되지 않았습니다."})

    channel_ready = sum(
        len(item.get("headlineDirections") or []) >= 2 and bool(item.get("cta"))
        for item in candidates
    )
    channel_score = 4 if channel_ready == 3 else 3 if channel_ready >= 2 else 2

    blocking_text = has_blocking_text_artifacts({
        "candidates": [
            {key: item.get(key) for key in ("name", "targetInsight", "corePromise", "offerPresentation", "cta", "headlineDirections")}
            for item in candidates
        ],
    })
    particle_errors = particle_mismatches(concepts)
    korean_score = 1 if blocking_text else 3 if particle_errors else 4
    if blocking_text:
        issues.append({"severity": "critical", "id": "broken_concept_text", "message": "콘셉트 문장에 깨진 한글 또는 프로그래밍 구조가 섞였습니다."})

    fact_text = " ".join([
        str(brief.get("event_name") or ""),
        str(brief.get("target") or ""),
        str(brief.get("offer") or ""),
        " ".join(str(item) for item in brief.get("constraints", {}).get("required_phrases", [])),
    ])
    concept_text = " ".join(texts)
    unsupported = unsupported_claims(concept_text, fact_text)
    mixed_term = next((term for term in INDUSTRY_TERMS.get(detect_industry(brief), set()) if term in concept_text), "")
    banned = next(
        (term for term in brief.get("constraints", {}).get("banned_words", []) if term and term in concept_text),
        "",
    )
    brand_score = 1 if unsupported or mixed_term or banned else 4
    if unsupported:
        issues.append({"severity": "critical", "id": "unsupported_concept_claim", "message": f"입력 사실에서 확인되지 않은 주장이 있습니다: {unsupported[0]}."})
    if mixed_term:
        issues.append({"severity": "critical", "id": "concept_industry_mismatch", "message": f"다른 업종 표현이 포함되었습니다: {mixed_term}."})
    if banned:
        issues.append({"severity": "critical", "id": "concept_banned_expression", "message": f"브랜드 금지 표현이 포함되었습니다: {banned}."})

    ctas = [str(item.get("cta") or "").strip() for item in candidates]
    generic_ctas = {"자세히 보기", "더 알아보기", "확인하기", "구매하기", "보러 가기"}
    actionability_score = 4 if len(set(ctas)) == 3 and all(len(item) >= 6 and item not in generic_ctas for item in ctas) else 3 if all(ctas) else 2
    if actionability_score < 4:
        issues.append({"severity": "warning", "id": "weak_concept_cta", "message": "각 콘셉트의 다음 행동이 구체적이지 않거나 서로 겹칩니다."})

    if any(marker.lower() in concept_text.lower() for marker in INTERNAL_MARKERS):
        issues.append({"severity": "warning", "id": "internal_concept_marker", "message": "사용자에게 보여서는 안 되는 내부 작성 문구가 남아 있습니다."})

    return {
        "strategyClarity": strategy_score,
        "targetEmpathy": target_score,
        "productConnection": product_score,
        "distinctiveness": distinctiveness_score,
        "channelFit": channel_score,
        "koreanCopyQuality": korean_score,
        "brandFit": brand_score,
        "actionability": actionability_score,
    }, issues


def _concept_user_text(concept: dict[str, Any]) -> str:
    values = [
        concept.get("name"),
        concept.get("targetInsight"),
        concept.get("corePromise"),
        concept.get("offerPresentation"),
        concept.get("cta"),
        concept.get("differencePoint"),
        *(concept.get("persuasionSequence") or []),
        *(concept.get("headlineDirections") or []),
    ]
    return " ".join(str(item or "").strip() for item in values if str(item or "").strip())


def _brief_product(brief: dict[str, Any]) -> str:
    product_terms = ("앰플", "세럼", "크림", "토너", "로션", "마스크", "에센스", "선크림", "목걸이", "반지", "귀걸이")
    phrases = [str(item or "").strip() for item in brief.get("constraints", {}).get("required_phrases", [])]
    candidates = [item for item in phrases if any(term in item for term in product_terms)]
    return candidates[-1] if candidates else ""


def _brief_offer(brief: dict[str, Any]) -> str:
    offer = brief.get("offer", "")
    if isinstance(offer, dict):
        return str(offer.get("summary") or "").strip()
    return str(offer or "").strip()


def _offer_tokens_connected(offer: str, text: str) -> bool:
    tokens = [item for item in re.findall(r"[가-힣A-Za-z0-9%]+", offer) if len(item) >= 2]
    return not tokens or sum(item in text for item in tokens) >= max(1, len(tokens) // 2)


def _concept_candidates_differ_by_two_fields(candidates: list[dict[str, Any]]) -> bool:
    fields = ("targetInsight", "corePromise", "emotionalDirection", "persuasionSequence", "offerPresentation", "cta")
    for left_index, left in enumerate(candidates):
        for right in candidates[left_index + 1:]:
            differences = 0
            for field in fields:
                if _normalized_value(left.get(field)) != _normalized_value(right.get(field)):
                    differences += 1
            if differences < 2:
                return False
    return True


def _normalized_value(value: Any) -> str:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return " ".join(str(value or "").split()).lower()


def select_external_concept(case_id: str, concept_id: str, output_path: Path = DEFAULT_RESULTS) -> dict[str, Any]:
    payload = read_json(output_path, default={"schemaVersion": "1.0.0", "results": []})
    result = next((item for item in payload.get("results", []) if item.get("caseId") == case_id), None)
    if not result or result.get("status") not in {"concept_review_pending", "quality_repair_required"}:
        raise ValueError("Benchmark case is not waiting for concept selection.")
    critic = result.get("concepts", {}).get("criticReview") or {}
    if critic.get("status") == "fail" or any(item.get("severity") == "error" for item in critic.get("issues", []) if isinstance(item, dict)):
        raise ValueError("Benchmark case has blocking planning quality errors.")
    if not _concept_evidence_ready(result.get("concepts") or {}, case_id):
        raise ValueError("Event-specific marketing evidence must be ready before concept selection.")
    if concept_id not in {item.get("conceptId") for item in result.get("concepts", {}).get("candidates", [])}:
        raise ValueError("Unknown benchmark concept.")
    result["selectedConceptId"] = concept_id
    result["selectedAt"] = datetime.now(timezone.utc).isoformat()
    result["selectionSource"] = "human"
    result["selectionNote"] = "사람이 콘셉트 3안을 비교한 뒤 선택했습니다."
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
        "reviewNote": str(review.get("reviewNote") or ""),
        "edits": review.get("edits", []) if isinstance(review.get("edits"), list) else [],
        "conceptSelectionSource": str(review.get("conceptSelectionSource") or ""),
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
    }
    payload["reviews"] = [records[key] for key in sorted(records)]
    payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
    write_json(reviews_path, payload)
    return records[case_id]


def is_final_human_review(review: dict[str, Any]) -> bool:
    if not isinstance(review, dict) or not review:
        return False
    reason_tags = {str(item).strip() for item in review.get("reasonTags", [])}
    selection_source = str(review.get("conceptSelectionSource") or "").strip()
    scores = review.get("scores") if isinstance(review.get("scores"), dict) else {}
    return (
        "connection_test" not in reason_tags
        and selection_source != "connection_check_default"
        and set(scores) == RUBRIC_KEYS
    )


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
