"""Evidence-aware deterministic critic for local concept and copy generation."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from services.ad_strategy.planning_engine import detect_industry
from services.ad_strategy.quality_gate import (
    INDUSTRY_TERMS,
    INTERNAL_MARKERS,
    copy_text_values,
    deterministic_quality_issues,
    unsupported_claims,
)
from services.ad_strategy.repository import load_examples_for_review
from services.ad_strategy.text_quality import has_blocking_text_artifacts, particle_mismatches


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


def review_local_concepts(brief: dict[str, Any], concepts: dict[str, Any]) -> dict[str, Any]:
    candidates = concepts.get("candidates") or []
    issues: list[dict[str, Any]] = []
    if len(candidates) != 3:
        issues.append(_issue("critical", "concept_count", "전략 축이 다른 콘셉트 3안이 필요합니다."))
    axes = [str(item.get("axis") or "") for item in candidates]
    if len(set(axes)) != len(axes):
        issues.append(_issue("critical", "concept_duplication", "콘셉트의 전략 축이 서로 겹칩니다."))
    if len(candidates) == 3 and not _differ_by_two_fields(candidates):
        issues.append(_issue("critical", "concept_insufficient_difference", "콘셉트 3안이 최소 두 가지 전략 항목에서 분리되지 않았습니다."))
    if concepts.get("marketingEvidenceStatus") != "ready":
        issues.append(_issue("warning", "marketing_signal_review_required", "이벤트 전용 마케팅 근거 검수가 아직 끝나지 않았습니다."))

    expected_type = str(brief.get("event_type") or brief.get("eventType") or "").strip()
    if expected_type and concepts.get("eventType") != expected_type:
        issues.append(_issue("critical", "event_type_mismatch", f"입력 이벤트 유형은 {expected_type}인데 기획 결과는 {concepts.get('eventType') or '미입력'}입니다."))

    expected_event_id = str(brief.get("event_id") or "")
    evidence_mismatch = [
        str(item.get("conceptId") or "")
        for item in candidates
        if expected_event_id and str((item.get("marketingEvidence") or {}).get("sourceEventId") or "") != expected_event_id
    ]
    if evidence_mismatch:
        issues.append(_issue("critical", "concept_evidence_event_mismatch", f"다른 이벤트 근거가 연결된 안이 있습니다: {', '.join(evidence_mismatch)}."))

    if concepts.get("marketingEvidenceStatus") == "ready":
        thin = [
            str(item.get("conceptId") or "")
            for item in candidates
            if len((item.get("marketingEvidence") or {}).get("signalIds") or []) < 3
            or not (item.get("marketingEvidence") or {}).get("primarySignalIds")
        ]
        if thin:
            issues.append(_issue("warning", "concept_evidence_thin", f"핵심 근거 1개와 전체 근거 3개를 채우지 못한 안이 있습니다: {', '.join(thin)}."))

    particle_errors = particle_mismatches(concepts)
    if particle_errors:
        issues.append(_issue("warning", "awkward_korean_particle", f"제품명 뒤 조사가 어색합니다: {particle_errors[0]}"))

    rubric, rubric_issues = _concept_rubric(brief, concepts)
    issues.extend(rubric_issues)
    return _review_result(issues, rubric)


def review_local_copy(
    brief: dict[str, Any],
    concepts: dict[str, Any],
    copy_package: dict[str, Any],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    outputs = copy_package.get("outputs") or []
    if not outputs:
        issues.append(_issue("critical", "copy_missing", "카피 패키지가 생성되지 않았습니다."))

    source_originals = [
        str(item.get("sourceOriginal", {}).get("copy") or "")
        for item in load_examples_for_review()
        if item.get("sourceOriginal", {}).get("copy")
    ]
    issues.extend(deterministic_quality_issues(
        brief,
        copy_package,
        industry=detect_industry(brief),
        source_originals=source_originals,
        issue=_issue,
    ))

    expected_event_id = str(brief.get("event_id") or "")
    if copy_package.get("marketingEvidenceStatus") != "ready":
        issues.append(_issue("warning", "copy_evidence_not_ready", "검수된 이벤트 전용 근거가 카피에 연결되지 않았습니다."))
    if expected_event_id and str(copy_package.get("marketingEvidenceEventId") or "") != expected_event_id:
        issues.append(_issue("critical", "copy_evidence_event_mismatch", "카피에 다른 이벤트의 마케팅 근거가 연결되었습니다."))
    missing_output_evidence = [
        str(item.get("channelId") or item.get("deliverableId") or "unknown")
        for item in outputs
        if not (item.get("planningEvidence") or {}).get("marketingSignalIds")
    ]
    if missing_output_evidence:
        issues.append(_issue("warning", "copy_channel_evidence_missing", f"채널별 근거가 비어 있습니다: {', '.join(missing_output_evidence)}."))

    selected_ids = {str(item.get("conceptId") or "") for item in concepts.get("candidates", [])}
    if copy_package.get("conceptId") and selected_ids and str(copy_package.get("conceptId")) not in selected_ids:
        issues.append(_issue("critical", "copy_concept_mismatch", "선택한 콘셉트와 카피 패키지의 전략 기준이 다릅니다."))

    repeated = _repeated_sentences(copy_package)
    if repeated:
        issues.append(_issue("warning", "repetitive_copy", f"같은 문장이 한 채널 안에서 반복됩니다: {repeated[0]}"))
    question_count = sum(value.count("?") for value in copy_text_values(copy_package))
    if question_count > max(2, len(outputs)):
        issues.append(_issue("warning", "excessive_questions", "질문형 문장이 채널 수보다 과도하게 많습니다."))

    rubric = _copy_rubric(brief, concepts, copy_package, issues)
    average = sum(rubric.values()) / len(rubric)
    if average < 4 and not any(item["id"] == "rubric_below_four" for item in issues):
        issues.append(_issue("warning", "rubric_below_four", f"평균 품질 점수가 4점 미만입니다: {average:.2f}."))
    return _review_result(issues, rubric)


def _concept_rubric(brief: dict[str, Any], concepts: dict[str, Any]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    candidates = concepts.get("candidates") or []
    issues: list[dict[str, Any]] = []
    texts = [_concept_text(item) for item in candidates]
    product = _brief_product(brief)
    offer = _brief_offer(brief)

    required = ("name", "targetInsight", "corePromise", "persuasionSequence", "cta", "differencePoint")
    complete = sum(all(item.get(field) for field in required) for item in candidates)
    strategy = 4 if len(candidates) == 3 and complete == 3 else 3 if complete >= 2 else 2

    generic = ("이번 제안이 필요한 고객", "피부 고민 고객", "고객 니즈", "좋은 선택", "자세히 알아보기")
    grounded = sum(
        len(str(item.get("targetInsight") or "").strip()) >= 35
        and bool((item.get("marketingEvidence") or {}).get("primaryInsight"))
        and not any(marker in str(item.get("targetInsight") or "") for marker in generic)
        for item in candidates
    )
    target = 4 if grounded == 3 else 3 if grounded >= 2 else 2 if grounded == 1 else 1
    if target < 4:
        issues.append(_issue("warning", "weak_target_insight", "구체적인 고객 상황과 핵심 근거가 연결되지 않은 타깃 인사이트가 있습니다."))

    product_hits = sum(bool(product) and product in str(item.get("corePromise") or "") for item in candidates)
    offer_hits = sum(not offer or _offer_connected(offer, text) for text in texts)
    product_score = 4 if product_hits == 3 and offer_hits == 3 else 3 if product_hits >= 2 else 2 if product_hits else 1
    if product_score < 4:
        issues.append(_issue("warning", "weak_product_connection", "제품과 입력 혜택이 세 콘셉트의 설득 논리에 충분히 연결되지 않았습니다."))

    primary_sets = [frozenset((item.get("marketingEvidence") or {}).get("primarySignalIds") or []) for item in candidates]
    strategy_distinct = len(candidates) == 3 and _differ_by_two_fields(candidates)
    evidence_distinct = len(primary_sets) == 3 and all(primary_sets) and len(set(primary_sets)) == 3
    distinct = 4 if strategy_distinct and evidence_distinct else 3 if strategy_distinct else 1
    if distinct < 4:
        issues.append(_issue("warning", "weak_evidence_distinction", "전략 문장은 다르지만 각 안을 만든 핵심 근거가 충분히 분리되지 않았습니다."))

    channel_ready = sum(len(item.get("headlineDirections") or []) >= 2 and bool(item.get("cta")) for item in candidates)
    channel = 4 if channel_ready == 3 else 3 if channel_ready >= 2 else 2
    blocking_text = has_blocking_text_artifacts({"candidates": [{key: item.get(key) for key in ("name", "targetInsight", "corePromise", "offerPresentation", "cta", "headlineDirections")} for item in candidates]})
    particles = particle_mismatches(concepts)
    korean = 1 if blocking_text else 3 if particles else 4
    if blocking_text:
        issues.append(_issue("critical", "broken_concept_text", "콘셉트 문장에 깨진 한글 또는 프로그래밍 구조가 섞였습니다."))

    concept_text = " ".join(texts)
    fact_text = _fact_text(brief)
    unsupported = unsupported_claims(concept_text, fact_text)
    mixed = next((term for term in INDUSTRY_TERMS.get(detect_industry(brief), set()) if term in concept_text), "")
    banned = next((term for term in brief.get("constraints", {}).get("banned_words", []) if term and term in concept_text), "")
    brand = 1 if unsupported or mixed or banned else 4
    if unsupported:
        issues.append(_issue("critical", "unsupported_concept_claim", f"입력 사실에서 확인되지 않은 주장이 있습니다: {unsupported[0]}."))
    if mixed:
        issues.append(_issue("critical", "concept_industry_mismatch", f"다른 업종 표현이 포함되었습니다: {mixed}."))
    if banned:
        issues.append(_issue("critical", "concept_banned_expression", f"브랜드 금지 표현이 포함되었습니다: {banned}."))

    ctas = [str(item.get("cta") or "").strip() for item in candidates]
    generic_ctas = {"자세히 보기", "더 알아보기", "확인하기", "구매하기", "보러 가기"}
    action = 4 if len(set(ctas)) == 3 and all(len(item) >= 6 and item not in generic_ctas for item in ctas) else 3 if all(ctas) else 2
    if action < 4:
        issues.append(_issue("warning", "weak_concept_cta", "각 콘셉트의 다음 행동이 구체적이지 않거나 서로 겹칩니다."))
    if any(marker.lower() in concept_text.lower() for marker in INTERNAL_MARKERS):
        issues.append(_issue("warning", "internal_concept_marker", "사용자에게 보여서는 안 되는 내부 작성 문구가 남아 있습니다."))

    return {
        "strategyClarity": strategy,
        "targetEmpathy": target,
        "productConnection": product_score,
        "distinctiveness": distinct,
        "channelFit": channel,
        "koreanCopyQuality": korean,
        "brandFit": brand,
        "actionability": action,
    }, issues


def _copy_rubric(
    brief: dict[str, Any],
    concepts: dict[str, Any],
    package: dict[str, Any],
    issues: list[dict[str, Any]],
) -> dict[str, int]:
    ids = {str(item.get("id") or "") for item in issues}
    critical_ids = {str(item.get("id") or "") for item in issues if item.get("severity") == "critical"}
    concept_rubric = (concepts.get("criticReview") or {}).get("rubric") or {}
    rubric = {key: min(4, int(concept_rubric.get(key, 4))) for key in RUBRIC_KEYS}

    persuasive_outputs = [
        item for item in package.get("outputs", [])
        if item.get("channelId") in {"instagram_cardnews", "instagram_feed", "blog_inline_image", "threads_image", "twitter_image"}
    ]
    grounded = all(
        (item.get("planningEvidence") or {}).get("target")
        and (item.get("planningEvidence") or {}).get("marketingSignalIds")
        for item in persuasive_outputs
    )
    rubric["targetEmpathy"] = min(rubric["targetEmpathy"], 4 if persuasive_outputs and grounded else 3)
    if not grounded and persuasive_outputs:
        issues.append(_issue("warning", "weak_copy_target_grounding", "고객 상황과 검수 근거가 연결되지 않은 채널 카피가 있습니다."))

    if "weak_product_connection" in ids:
        rubric["productConnection"] = min(rubric["productConnection"], 2)
    elif "weak_offer_connection" in ids:
        rubric["productConnection"] = min(rubric["productConnection"], 3)
    if {"channel_mismatch"} & critical_ids:
        rubric["channelFit"] = 1
    elif ids & {"channel_contract_missing", "channel_copy_reuse"}:
        rubric["channelFit"] = min(rubric["channelFit"], 2)
    elif ids & {"output_metadata_missing", "channel_character_limit"}:
        rubric["channelFit"] = min(rubric["channelFit"], 3)
    if ids & {"repetitive_copy", "channel_copy_reuse"}:
        rubric["distinctiveness"] = min(rubric["distinctiveness"], 2)
    if ids & {"broken_korean_text", "raw_structure_exposed"}:
        rubric["koreanCopyQuality"] = 1
    elif ids & {"awkward_korean_particle", "repetitive_copy", "excessive_questions"}:
        rubric["koreanCopyQuality"] = min(rubric["koreanCopyQuality"], 2)
    if critical_ids & {"unsupported_claim", "industry_mismatch", "copied_expression", "banned_expression"}:
        rubric["brandFit"] = 1
    if "weak_cta" in ids:
        rubric["actionability"] = min(rubric["actionability"], 2)
    return rubric


def _review_result(issues: list[dict[str, Any]], rubric: dict[str, int]) -> dict[str, Any]:
    has_critical = any(item.get("severity") == "critical" for item in issues)
    return {
        "status": "fail" if has_critical else "revise" if issues else "pass",
        "issues": issues,
        "rubric": rubric,
        "averageScore": round(sum(rubric.values()) / len(rubric), 2),
    }


def _issue(severity: str, issue_id: str, message: str) -> dict[str, Any]:
    return {"severity": severity, "id": issue_id, "message": message, "targetIds": []}


def _concept_text(concept: dict[str, Any]) -> str:
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
    terms = ("앰플", "세럼", "크림", "토너", "로션", "마스크", "에센스", "선크림", "목걸이", "반지", "귀걸이")
    phrases = [str(item or "").strip() for item in brief.get("constraints", {}).get("required_phrases", [])]
    candidates = [item for item in phrases if any(term in item for term in terms)]
    product_candidates = [
        item for item in candidates
        if not any(marker in item for marker in ("증정", "할인", "쿠폰", "사은", "혜택", "특가"))
    ]
    return (product_candidates or candidates or [""])[0]


def _brief_offer(brief: dict[str, Any]) -> str:
    offer = brief.get("offer", "")
    return str(offer.get("summary") or "").strip() if isinstance(offer, dict) else str(offer or "").strip()


def _offer_connected(offer: str, text: str) -> bool:
    tokens = [item for item in re.findall(r"[가-힣A-Za-z0-9%]+", offer) if len(item) >= 2]
    return not tokens or sum(item in text for item in tokens) >= max(1, len(tokens) // 2)


def _fact_text(brief: dict[str, Any]) -> str:
    return " ".join([
        str(brief.get("event_name") or ""),
        str(brief.get("target") or ""),
        str(brief.get("offer") or ""),
        " ".join(str(item) for item in brief.get("constraints", {}).get("required_phrases", [])),
    ])


def _differ_by_two_fields(candidates: list[dict[str, Any]]) -> bool:
    fields = ("targetInsight", "corePromise", "emotionalDirection", "persuasionSequence", "offerPresentation", "cta")
    for index, left in enumerate(candidates):
        for right in candidates[index + 1:]:
            differences = sum(_normalize_value(left.get(field)) != _normalize_value(right.get(field)) for field in fields)
            if differences < 2:
                return False
    return True


def _normalize_value(value: Any) -> str:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return " ".join(str(value or "").split()).lower()


def _repeated_sentences(copy_package: dict[str, Any]) -> list[str]:
    repeated: list[str] = []
    for output in copy_package.get("outputs", []):
        sentences: list[str] = []
        for text in copy_text_values({"outputs": [output]}):
            sentences.extend(
                value.strip()
                for value in re.split(r"(?<=[.!?])\s+|\n+", text)
                if len(value.strip()) >= 8
            )
        repeated.extend(value for value, count in Counter(sentences).most_common() if count >= 3)
    return repeated
