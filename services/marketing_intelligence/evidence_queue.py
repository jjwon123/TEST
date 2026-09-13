"""Build an event-scoped evidence collection and review queue."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json, write_json
from services.marketing_intelligence.insight_brief import BLOCKED_RISK_FLAGS
from services.marketing_intelligence.repository import SIGNALS_PATH, load_signals


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json"
DEFAULT_PLAN = ROOT / "assets" / "rules" / "cosmetics-benchmark-evidence-plan.json"
DEFAULT_OUTPUT = ROOT / ".tmp" / "model-benchmarks" / "cosmetics-evidence-queue.json"

EVIDENCE_LABELS = {
    "pain": "고객 문제",
    "desire": "고객 욕구",
    "objection": "구매 저항",
    "timing": "시기 명분",
    "trend": "검색·시장 흐름",
    "proof": "제품 근거",
    "offer": "혜택 근거",
    "channel_pattern": "채널 반응 구조",
}
SOURCE_LABELS = {
    "brand_site": "브랜드·상품 페이지",
    "review": "고객 리뷰",
    "meta_ad": "경쟁 광고 관찰",
    "weather": "날씨 관찰",
    "google_trends": "Google 검색 흐름",
    "naver_datalab": "Naver 검색 흐름",
    "internal": "내부 검증 자료",
    "public_web": "공개 웹 자료",
}


def build_evidence_queue(
    *,
    dataset: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    signals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    dataset = dataset if dataset is not None else read_json(DEFAULT_DATASET, {"cases": []})
    plan = plan if plan is not None else read_json(DEFAULT_PLAN, {"events": []})
    signals = signals if signals is not None else load_signals(SIGNALS_PATH)
    plan_by_id = {item.get("id"): item for item in plan.get("events", []) if isinstance(item, dict)}
    requirements = plan.get("eventTypeRequirements", {})
    cases: list[dict[str, Any]] = []
    for case in dataset.get("cases", []):
        if not isinstance(case, dict):
            continue
        case_plan = plan_by_id.get(case.get("id"), {})
        event_type = str(case.get("eventType") or "")
        event_rules = requirements.get(event_type, {})
        cases.append(_build_case(
            case,
            case_plan,
            event_rules,
            signals,
            minimum_selected=int(plan.get("minimumSelectedSignals") or 3),
            minimum_sources=int(plan.get("minimumSourceTypes") or 2),
        ))
    cases.sort(key=lambda item: (int(item["priority"]), _status_rank(item["status"]), item["eventName"]))
    status_counts = Counter(item["status"] for item in cases)
    pilot_cases = [item for item in cases if item["priority"] == 1]
    return {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(cases),
            "ready": status_counts["ready"],
            "needsReview": status_counts["needs_review"],
            "needsCollection": status_counts["needs_collection"],
            "pilotTotal": len(pilot_cases),
            "pilotReady": sum(item["status"] == "ready" for item in pilot_cases),
        },
        "cases": cases,
    }


def build_and_save_evidence_queue(
    *,
    output: Path = DEFAULT_OUTPUT,
    dataset_path: Path = DEFAULT_DATASET,
    plan_path: Path = DEFAULT_PLAN,
    signals_path: Path = SIGNALS_PATH,
) -> dict[str, Any]:
    queue = build_evidence_queue(
        dataset=read_json(dataset_path, {"cases": []}),
        plan=read_json(plan_path, {"events": []}),
        signals=load_signals(signals_path),
    )
    write_json(output, queue)
    return queue


def load_or_build_evidence_queue(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    return build_and_save_evidence_queue(output=output)


def signals_for_event(
    signals: list[dict[str, Any]],
    *,
    event_id: str,
    topic: str,
) -> list[dict[str, Any]]:
    scoped: list[dict[str, Any]] = []
    for signal in signals:
        signal_event = str((signal.get("sourceRef") or {}).get("eventId") or signal.get("eventId") or "").strip()
        signal_topic = str(signal.get("topic") or "").strip()
        if signal_event == event_id or (topic and signal_topic == topic):
            scoped.append(signal)
    return scoped


def _build_case(
    case: dict[str, Any],
    case_plan: dict[str, Any],
    event_rules: dict[str, Any],
    signals: list[dict[str, Any]],
    *,
    minimum_selected: int,
    minimum_sources: int,
) -> dict[str, Any]:
    event_id = str(case.get("id") or "")
    topic = str(case_plan.get("topic") or event_id.replace("-", "_"))
    scoped = signals_for_event(signals, event_id=event_id, topic=topic)
    usable = [item for item in scoped if not BLOCKED_RISK_FLAGS.intersection(set(item.get("riskFlags") or []))]
    selected = [item for item in usable if (item.get("review") or {}).get("decision") == "selected"]
    review_candidates = [
        item for item in usable
        if (item.get("review") or {}).get("decision") in {"unreviewed", "shortlist"}
    ]
    candidate_sources = sorted({_source_key(item) for item in usable if _source_key(item)})
    required_types = [str(item) for item in event_rules.get("requiredEvidenceTypes", [])]
    recommended_sources = [str(item) for item in event_rules.get("recommendedSourceTypes", [])]
    selected_types = Counter(str(item.get("evidenceType") or "") for item in selected)
    candidate_types = Counter(str(item.get("evidenceType") or "") for item in usable)
    selected_sources = sorted({_source_key(item) for item in selected if _source_key(item)})
    missing_types = [item for item in required_types if selected_types[item] == 0]
    missing_candidate_types = [item for item in required_types if candidate_types[item] == 0]
    missing_source_count = max(0, minimum_sources - len(selected_sources))
    # If no official product page has been collected at all, do not strand a
    # completed review. Continue with the event input, but lock product efficacy
    # and ingredient claims until a human-reviewed proof candidate exists.
    has_reviewable_proof = any(str(item.get("evidenceType") or "") == "proof" for item in review_candidates)
    deferred_types = [item for item in missing_types if item == "proof" and not has_reviewable_proof]
    blocking_missing_types = [item for item in missing_types if item not in deferred_types]
    ready = len(selected) >= minimum_selected and not blocking_missing_types and not missing_source_count
    if ready:
        status = "ready"
        next_action = "이벤트 전용 근거 패킷을 만들고 기획안을 다시 생성하세요."
    elif review_candidates:
        status = "needs_review"
        next_action = f"후보 신호 {len(review_candidates)}개를 읽고 선택·보류·거절을 판정하세요."
    else:
        status = "needs_collection"
        next_action = "아래 조사 질문과 검색어로 공개 근거를 먼저 수집하세요."
    return {
        "eventId": event_id,
        "eventName": str(case.get("eventName") or event_id),
        "eventType": str(case.get("eventType") or ""),
        "target": str(case.get("target") or ""),
        "product": str(case.get("product") or ""),
        "offer": str(case.get("offer") or ""),
        "topic": topic,
        "priority": int(case_plan.get("priority") or 2),
        "status": status,
        "nextAction": next_action,
        "requirements": {
            "minimumSelectedSignals": minimum_selected,
            "minimumSourceTypes": minimum_sources,
            "evidenceTypes": required_types,
            "evidenceTypeLabels": [EVIDENCE_LABELS.get(item, item) for item in required_types],
            "recommendedSourceTypes": recommended_sources,
            "recommendedSourceLabels": [SOURCE_LABELS.get(item, item) for item in recommended_sources],
            "deferredEvidenceTypes": deferred_types,
            "claimPolicy": "no_unverified_product_claims" if deferred_types else "standard",
        },
        "progress": {
            "scopeMatched": len(scoped),
            "selected": len(selected),
            "reviewCandidates": len(review_candidates),
            "candidateDistinctSources": candidate_sources,
            "sourceTypes": selected_sources,
            "distinctSources": selected_sources,
            "evidenceTypeCounts": dict(selected_types),
            "candidateEvidenceTypeCounts": dict(candidate_types),
        },
        "gaps": {
            "evidenceTypes": blocking_missing_types,
            "evidenceTypeLabels": [EVIDENCE_LABELS.get(item, item) for item in blocking_missing_types],
            "deferredEvidenceTypes": deferred_types,
            "deferredEvidenceLabels": [EVIDENCE_LABELS.get(item, item) for item in deferred_types],
            "sourceTypesNeeded": missing_source_count,
            "missingInputs": [_missing_input_message(item, case) for item in missing_candidate_types],
        },
        "researchQuestions": [str(item) for item in case_plan.get("researchQuestions", [])],
        "collectionQueries": _collection_queries(case, required_types),
        "selectedSignalIds": [str(item.get("id") or "") for item in selected],
        "reviewCandidateIds": [str(item.get("id") or "") for item in review_candidates],
    }


def _collection_queries(case: dict[str, Any], required_types: list[str]) -> list[dict[str, str]]:
    product = str(case.get("product") or "스킨케어")
    target = str(case.get("target") or "고객")
    event_name = str(case.get("eventName") or "")
    templates = {
        "pain": ("고객 리뷰", f"{product} 불편 단점 후기 {target}"),
        "desire": ("고객 리뷰", f"{product} 원하는 변화 사용 상황 후기"),
        "objection": ("고객 리뷰", f"{product} 구매 고민 망설이는 이유"),
        "timing": ("날씨·계절", f"{event_name} 계절 날씨 피부 고민"),
        "trend": ("검색 흐름", f"{product} {event_name} 검색 트렌드"),
        "proof": ("상품 페이지", f"{product} 전성분 사용법 공식 제품 정보"),
        "offer": ("브랜드 페이지", f"{event_name} 공식 혜택 조건"),
        "channel_pattern": ("경쟁 광고", f"{product} 인스타그램 광고 콘텐츠 구조"),
    }
    return [
        {"evidenceType": evidence_type, "label": EVIDENCE_LABELS.get(evidence_type, evidence_type), "source": templates[evidence_type][0], "query": templates[evidence_type][1]}
        for evidence_type in required_types
        if evidence_type in templates
    ]


def _status_rank(status: str) -> int:
    return {"needs_review": 0, "needs_collection": 1, "ready": 2}.get(status, 9)


def _source_key(signal: dict[str, Any]) -> str:
    source_ref = signal.get("sourceRef") or {}
    host = str(source_ref.get("host") or "").strip().lower()
    if host:
        return host.removeprefix("www.")
    url = str(source_ref.get("url") or "").strip()
    if url:
        from urllib.parse import urlparse
        parsed_host = urlparse(url).netloc.lower().removeprefix("www.")
        if parsed_host:
            return parsed_host
    source_type = str(signal.get("sourceType") or "").strip()
    return source_type


def _missing_input_message(evidence_type: str, case: dict[str, Any]) -> str:
    product = str(case.get("product") or "제품")
    offer = str(case.get("offer") or "혜택")
    return {
        "proof": f"{product}의 공식 성분·사용법·시험 자료 또는 검증된 내부 제품 문서",
        "offer": f"{offer}의 공식 적용 조건·기간·대상 정보",
        "pain": "실제 고객 리뷰·상담 기록 또는 고객 조사에서 확인된 문제 표현",
        "desire": "고객 조사·검색 행동에서 확인된 기대 상황",
        "objection": "리뷰·상담·구매 조사에서 확인된 망설임",
        "timing": "공식 날씨·캘린더 자료로 확인된 지금의 시기 명분",
        "trend": "날짜와 조사 방법이 확인되는 검색·시장 흐름",
        "channel_pattern": "출처와 기간이 확인되는 채널 반응 또는 경쟁 콘텐츠 구조",
    }.get(evidence_type, f"{evidence_type} 근거 자료")
