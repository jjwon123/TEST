"""Campaign concept, copy-package, and deterministic planning QA engine."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from core.utils.json_io import read_json
from services.ad_strategy.quality_gate import deterministic_quality_issues
from services.ad_strategy.repository import load_examples_for_review, retrieve_selected
from services.marketing_intelligence.insight_brief import INSIGHT_BRIEF_PATH


CONCEPT_AXES = [
    {
        "axis": "problem_reframe",
        "name": "불편을 새 기준으로 바꾸는 캠페인",
        "emotion": "공감과 안도",
        "sequence": ["상황 공감", "문제 재정의", "제품 역할", "가벼운 행동 제안"],
        "cta": "내 루틴에 맞는지 확인하기",
    },
    {
        "axis": "proof_and_choice",
        "name": "선택 근거를 분명히 보여주는 캠페인",
        "emotion": "납득과 신뢰",
        "sequence": ["선택 기준 제시", "제품 역할 설명", "사용 맥락 연결", "오퍼 확인"],
        "cta": "선택 기준 확인하기",
    },
    {
        "axis": "identity_and_moment",
        "name": "지금의 나에게 맞는 순간으로 연결하는 캠페인",
        "emotion": "기대와 자기관리",
        "sequence": ["원하는 피부 인상", "시즌 루틴 제안", "브랜드 태도 연결", "구매 행동 제안"],
        "cta": "여름 루틴 시작하기",
    },
]

COSMETIC_PRODUCT_TOKENS = (
    "나이아신아마이드", "앰플", "세럼", "크림", "토너", "로션", "마스크", "에센스", "선크림",
    "스킨케어", "수분", "장벽", "톤",
)
JEWELRY_PRODUCT_TOKENS = ("반지", "목걸이", "귀걸이", "팔찌", "다이아", "주얼리", "골드", "실버")


def detect_industry(brief: dict[str, Any]) -> str:
    text = str(brief).lower()
    if any(token.lower() in text for token in JEWELRY_PRODUCT_TOKENS):
        return "jewelry_luxury"
    return "cosmetics_skincare"


def detect_event_type(brief: dict[str, Any]) -> str:
    text = str(brief)
    if any(token in text for token in ("할인", "증정", "쿠폰", "%", "세일", "프로모션")):
        return "promotion"
    if any(token in text for token in ("출시", "신제품", "런칭", "론칭")):
        return "launch"
    if any(token in text for token in ("가이드", "방법", "교육", "알아보기", "사용법")):
        return "education"
    if any(token in text for token in ("여름", "겨울", "장마", "환절기", "봄", "가을")):
        return "seasonal"
    return "branding"


def build_strategic_brief(brief: dict[str, Any]) -> dict[str, Any]:
    target = _target_summary(brief)
    offer = _offer_summary(brief)
    open_questions = brief.get("open_questions", [])
    facts = [value for value in [brief.get("event_name"), target, offer] if value]
    facts.extend(brief.get("constraints", {}).get("required_phrases", []))
    industry = detect_industry(brief)
    return {
        "schemaVersion": "1.0.0",
        "eventId": brief.get("event_id"),
        "industry": industry,
        "eventType": detect_event_type(brief),
        "funnelStage": "conversion" if offer else "consideration",
        "verifiedFacts": list(dict.fromkeys(str(item).strip() for item in facts if str(item).strip())),
        "unverifiedClaims": open_questions,
        "audience": {
            "situation": target,
            "desire": _desire_for(industry),
            "resistance": "과장된 효능보다 지금 상황에 맞는 선택 이유를 먼저 확인하려는 상태",
        },
        "constraints": brief.get("constraints", {}),
        "channelRoles": [{"channel": channel, "role": _channel_role(channel)} for channel in brief.get("channels", [])],
        "status": "needs_input" if open_questions else "ready_for_concepts",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


def build_concept_candidates(brief: dict[str, Any]) -> dict[str, Any]:
    industry = detect_industry(brief)
    event_type = detect_event_type(brief)
    examples = retrieve_selected(industry=industry, event_type=event_type, channels=brief.get("channels", []))
    insight_brief = _ready_insight_brief(industry=industry, event_id=str(brief.get("event_id") or ""))
    target = _target_summary(brief) or "이번 제안이 필요한 고객"
    product = _product_phrase(brief)
    offer = _offer_summary(brief)
    candidates = []
    for index, axis in enumerate(CONCEPT_AXES, start=1):
        evidence = _concept_marketing_evidence(insight_brief, axis["axis"], index)
        promise = _promise(industry, axis["axis"], product, evidence)
        candidates.append({
            "conceptId": f"concept_{index:02d}",
            "axis": axis["axis"],
            "name": axis["name"],
            "targetInsight": _insight(_target_from_evidence(target, evidence), axis["axis"], evidence),
            "corePromise": promise,
            "emotionalDirection": axis["emotion"],
            "persuasionSequence": axis["sequence"],
            "offerPresentation": _offer_presentation(offer, axis["axis"]),
            "cta": axis["cta"],
            "headlineDirections": _headlines(product, evidence, axis["axis"]),
            "expectedEffect": _expected_effect(axis["axis"]),
            "risks": [
                "입력에 없는 효능, 가격, 기간, 순위, 리뷰 주장은 추가하지 않는다.",
                *insight_brief.get("doNotClaim", [])[:2],
            ],
            "strategyExampleIds": [item["id"] for item in examples[index - 1::3][:2]],
            "marketingSignalIds": evidence.get("signalIds", []),
            "marketingEvidence": evidence,
            "differencePoint": _difference_point(axis["axis"], evidence),
            "status": "candidate",
        })
    return {
        "schemaVersion": "1.0.0",
        "industry": industry,
        "eventType": event_type,
        "sourcePolicy": "selected_examples_only",
        "reviewedExampleCount": len(examples),
        "marketingEvidenceStatus": insight_brief.get("status", "needs_signal_review"),
        "selectedMarketingSignalCount": insight_brief.get("selectedSignalCount", 0),
        "marketingSignalIds": insight_brief.get("evidenceSignalIds", []),
        "candidates": candidates,
        "status": "review_pending",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


def build_copy_package(brief: dict[str, Any], concept: dict[str, Any], deliverables: list[dict[str, Any]]) -> dict[str, Any]:
    event_name = str(brief.get("event_name") or "")
    offer = _offer_summary(brief)
    product = _product_phrase(brief)
    target = _target_summary(brief)
    insight_brief = _ready_insight_brief(industry=detect_industry(brief), event_id=str(brief.get("event_id") or ""))
    outputs = []
    for deliverable in deliverables:
        channel = str(deliverable.get("channel_id") or "")
        marketing_evidence = _copy_marketing_evidence(insight_brief, concept, channel)
        copy = _channel_copy(channel, concept, event_name, product, offer, deliverable, marketing_evidence)
        outputs.append({
            "deliverableId": deliverable.get("deliverable_id"),
            "channelId": channel,
            "purpose": deliverable.get("purpose", ""),
            "strategyBasis": _strategy_basis(brief, concept, channel, product, offer, marketing_evidence),
            "planningEvidence": {
                "target": target or concept.get("targetInsight", ""),
                "productRole": _product_role(concept, product),
                "offerRole": _offer_role(offer, concept.get("axis", "")),
                "channelRole": _channel_role(channel),
                "verifiedFacts": _verified_facts(brief),
                "marketingSignals": marketing_evidence.get("signals", []),
                "marketingSignalIds": marketing_evidence.get("signalIds", []),
                "marketingEvidenceStatus": insight_brief.get("status", "needs_signal_review"),
            },
            "copy": copy,
            "characterCount": len(str(copy)),
        })
    return {
        "schemaVersion": "1.0.0",
        "conceptId": concept.get("conceptId"),
        "model": "deterministic_planning_engine",
        "marketingEvidenceStatus": insight_brief.get("status", "needs_signal_review"),
        "marketingSignalIds": insight_brief.get("evidenceSignalIds", []),
        "outputs": outputs,
        "status": "review_pending",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


def score_planning(brief: dict[str, Any], candidates: dict[str, Any], copy_package: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    concepts = candidates.get("candidates", [])
    if len(concepts) != 3:
        issues.append(_issue("critical", "concept_count", "전략 축이 다른 콘셉트 3안이 필요합니다."))
    axes = {item.get("axis") for item in concepts}
    if len(axes) != len(concepts):
        issues.append(_issue("critical", "concept_duplication", "콘셉트의 전략 축이 중복됩니다."))
    if len(concepts) == 3 and not _concepts_differ_by_two_fields(concepts):
        issues.append(_issue("critical", "concept_insufficient_difference", "콘셉트 3안이 최소 두 가지 전략 항목에서 분리되지 않았습니다."))
    if candidates.get("marketingEvidenceStatus") != "ready":
        issues.append(_issue("warning", "marketing_signal_review_required", "선택된 마케팅 신호가 부족해 기획 근거 패킷이 아직 준비되지 않았습니다."))

    text = str(copy_package)
    for word in brief.get("constraints", {}).get("banned_words", []):
        if word and word in text:
            issues.append(_issue("critical", "banned_expression", f"금지 표현이 포함되었습니다: {word}"))

    questions = len(re.findall(r"\?", text))
    if questions > max(2, len(copy_package.get("outputs", []))):
        issues.append(_issue("warning", "excessive_questions", "질문형 문장이 과도하게 반복됩니다."))
    if _has_broken_korean(text):
        issues.append(_issue("warning", "awkward_korean", "깨진 한글, 번역투, 내부 작성용 문구가 최종 카피에 포함되었습니다."))

    repeated = _repeated_copy_sentences(copy_package)
    if repeated:
        issues.append(_issue("warning", "repetitive_copy", f"동일 문장이 과도하게 반복됩니다: {repeated[0]}"))
        if not any(item["id"] == "awkward_korean" for item in issues):
            issues.append(_issue("warning", "awkward_korean", "반복된 문장 때문에 한국어 카피 품질 확인이 필요합니다."))

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
    if copy_package.get("status") == "blocked_pending_concept_selection":
        issues.append(_issue("warning", "copy_waiting_for_concept", "콘셉트 선택 후 카피 패키지를 생성해야 합니다."))

    provider_executions = candidates.get("providerExecution", []) + copy_package.get("providerExecution", [])
    if any(item.get("status") != "ok" for item in provider_executions):
        issues.append(_issue("critical", "provider_unavailable", "기획 provider를 사용할 수 없어 승인 가능한 결과를 만들지 못했습니다."))

    critics = [
        ("concept", candidates.get("criticReview") or {}),
        ("copy", copy_package.get("criticReview") or {}),
    ]
    for critic_target, critic in critics:
        if critic.get("status") == "fail":
            issues.append(_issue("critical", f"{critic_target}_critic_failed", f"{critic_target} 비평 결과가 실패입니다."))
        elif critic.get("status") == "revise":
            issues.append(_issue("warning", f"{critic_target}_critic_revision_unresolved", f"{critic_target} 비평의 수정 요청이 남아 있습니다."))
        for item in critic.get("issues", []):
            severity = "critical" if item.get("severity") == "critical" else "warning"
            issues.append(_issue(severity, f"{critic_target}_critic_{item.get('id', 'quality')}", str(item.get("message") or "비평 품질 이슈")))

    korean_quality = 1 if any(item["id"] == "awkward_korean" for item in issues) else 2 if repeated else 4
    rubric = {
        "strategyClarity": 4 if len(axes) == 3 else 2,
        "targetEmpathy": 4,
        "productConnection": 4,
        "distinctiveness": 4 if len(axes) == 3 else 1,
        "channelFit": 2 if repeated else 4 if copy_package.get("outputs") else 1,
        "koreanCopyQuality": korean_quality,
        "brandFit": 4,
        "actionability": 4,
    }
    critic_rubrics = [critic.get("rubric", {}) for _, critic in critics if critic.get("rubric")]
    for key in rubric:
        values = [value[key] for value in critic_rubrics if isinstance(value.get(key), (int, float))]
        if values:
            rubric[key] = max(1, min(5, min(values)))
    average_score = sum(rubric.values()) / len(rubric)
    if average_score < 4:
        issues.append(_issue("warning", "rubric_below_four", f"평균 루브릭 점수가 4점 미만입니다: {average_score:.2f}"))
    critical = [item for item in issues if item["severity"] == "critical"]
    return {
        "schemaVersion": "1.0.0",
        "status": "fail" if critical else "warning" if issues else "pass",
        "criticalErrorCount": len(critical),
        "issues": issues,
        "rubric": rubric,
        "averageScore": round(average_score, 2),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


def _channel_copy(
    channel: str,
    concept: dict[str, Any],
    event: str,
    product: str,
    offer: str,
    deliverable: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    headline = concept.get("headlineDirections", [""])[0]
    cta = concept.get("cta", "자세히 보기")
    primary_signal = _user_facing_signal(_first(evidence.get("signals")) or concept.get("targetInsight", ""))
    offer_line = offer or "상세 내용은 이벤트 페이지에서 확인하세요."
    if channel == "instagram_cardnews":
        roles = [item.get("role", "support") for item in deliverable.get("slides", [])] or ["hook", "problem", "benefit", "offer", "cta"]
        slide_lines = [
            (headline, primary_signal),
            ("왜 지금 이 루틴인가요?", concept.get("corePromise", "")),
            ("제품은 어떤 역할인가요?", _product_role(concept, product)),
            ("참여 이유", offer_line),
            ("다음 행동", cta),
        ]
        slides = []
        for index, role in enumerate(roles):
            title, body = slide_lines[min(index, len(slide_lines) - 1)]
            slides.append({
                "slide": index + 1,
                "role": role,
                "headline": title,
                "body": body,
                "transition": "다음 장에서 선택 기준을 더 구체적으로 보여줍니다." if index < len(roles) - 1 else "",
            })
        return {"cover": headline, "slides": slides, "cta": cta}
    if channel == "instagram_feed":
        body_parts = [
            primary_signal,
            concept.get("corePromise", ""),
            f"{product}를 중심으로 지금 필요한 선택 기준을 정리했습니다.",
            offer_line,
        ]
        return {
            "firstLine": headline,
            "body": "\n".join(part for part in body_parts if part),
            "cta": cta,
            "hashtagDirection": _hashtag_direction(event, product),
        }
    if channel in {"blog_thumbnail", "brunch_cover"}:
        return {"headline": _compact(_channel_headline(channel, concept, product), 48), "subcopy": _compact(concept.get("corePromise", ""), 54), "offer": _offer_badge(offer_line), "cta": cta}
    if channel == "community_banner":
        return {
            "headline": _compact(_channel_headline(channel, concept, product), 34),
            "subcopy": _compact(f"{product}와 함께 여름 루틴 기준을 확인하세요.", 56),
            "offer": _offer_badge(offer_line),
            "cta": cta,
        }
    if channel == "blog_inline_image":
        section_sentences = [
            _user_facing_signal(concept.get("targetInsight", "")),
            concept.get("corePromise", ""),
            _product_role(concept, product),
            offer_line,
        ]
        return {
            "titleCandidates": _blog_title_candidates(concept, product),
            "intro": _blog_intro(evidence, concept),
            "sections": [
                {"heading": step, "keySentence": section_sentences[min(index, len(section_sentences) - 1)]}
                for index, step in enumerate(concept.get("persuasionSequence", []))
            ],
            "cta": cta,
        }
    if channel in {"threads_image", "twitter_image"}:
        return {"post": _compact(f"{headline} {concept.get('corePromise', '')}", 180), "followUp": offer_line, "cta": cta}
    return {"headline": headline, "body": concept.get("corePromise", ""), "cta": cta}


def _target_summary(brief: dict[str, Any]) -> str:
    target = brief.get("target", "")
    if isinstance(target, dict):
        return str(target.get("summary") or "").strip()
    return str(target or "").strip()


def _offer_summary(brief: dict[str, Any]) -> str:
    offer = brief.get("offer", "")
    if isinstance(offer, dict):
        return str(offer.get("summary") or "").strip()
    return str(offer or "").strip()


def _product_phrase(brief: dict[str, Any]) -> str:
    phrases = [str(item).strip() for item in brief.get("constraints", {}).get("required_phrases", []) if str(item).strip()]
    scored = []
    product_tokens = COSMETIC_PRODUCT_TOKENS + JEWELRY_PRODUCT_TOKENS
    for phrase in phrases:
        matched = [index for index, token in enumerate(product_tokens) if token in phrase]
        if matched:
            scored.append((min(matched), -len(matched), phrase))
    if scored:
        return sorted(scored)[0][2]
    return phrases[-1] if phrases else "제품"


def _promise(industry: str, axis: str, product: str, evidence: dict[str, Any]) -> str:
    if industry == "jewelry_luxury":
        values = {
            "problem_reframe": f"{product}를 단순 장식이 아니라 취향을 정리하는 선택 기준으로 제안합니다.",
            "proof_and_choice": f"{product}를 골라야 하는 이유를 소재, 형태, 착용 장면 기준으로 보여줍니다.",
            "identity_and_moment": f"{product}를 나를 표현하는 순간과 연결합니다.",
        }
    else:
        values = {
            "problem_reframe": f"{product}를 여름철 피부 인상 고민을 정리하는 데일리 루틴의 시작점으로 제안합니다.",
            "proof_and_choice": f"{product}를 선택해야 하는 이유를 성분명, 사용 맥락, 구매 전 확인 포인트로 설명합니다.",
            "identity_and_moment": f"{product}를 지금 계절에 맞는 자기관리 루틴으로 연결합니다.",
        }
    return values[axis]


def _insight(target: str, axis: str, evidence: dict[str, Any] | None = None) -> str:
    endings = {
        "problem_reframe": "이 고객은 문제를 참으라는 말보다 불편을 줄이는 현실적인 기준에 반응합니다.",
        "proof_and_choice": "이 고객은 광고 문구보다 스스로 납득할 수 있는 선택 근거를 원합니다.",
        "identity_and_moment": "이 고객은 구매 자체보다 지금의 나에게 맞는 관리 경험을 원합니다.",
    }
    evidence_line = (evidence or {}).get("primaryInsight", "")
    if evidence_line and (_normalize_for_compare(evidence_line) in _normalize_for_compare(target)):
        evidence_line = ""
    return " ".join(part for part in [target, evidence_line, endings[axis]] if part).strip()


def _headlines(product: str, evidence: dict[str, Any], axis: str) -> list[str]:
    signal = _first(evidence.get("signals"))
    if axis == "problem_reframe":
        return [f"불편을 참기보다, 여름 루틴의 기준을 바꿀 때", f"{product}로 시작하는 여름 피부 루틴"]
    if axis == "proof_and_choice":
        return [f"좋아 보이는 말보다, 선택 이유가 분명한 {product}", "구매 전 확인할 기준을 먼저 보여드립니다"]
    return [f"오늘 피부 인상에 맞춘 {product} 루틴", signal or "여름 피부 인상을 다시 정리하는 시간"]


def _offer_presentation(offer: str, axis: str) -> str:
    if not offer:
        return "입력에 없는 가격, 기간, 수량 혜택을 만들지 않고 제품 이해와 행동 유도 중심으로 마무리합니다."
    return {
        "problem_reframe": f"불편을 줄이는 루틴을 시작하는 계기로 제시: {offer}",
        "proof_and_choice": f"선택을 마무리할 추가 이유로 제시: {offer}",
        "identity_and_moment": f"지금 루틴을 시작할 명분으로 제시: {offer}",
    }[axis]


def _expected_effect(axis: str) -> str:
    return {
        "problem_reframe": "초기 공감과 저장 반응",
        "proof_and_choice": "구매 고려 단계의 납득 전환",
        "identity_and_moment": "브랜드 선호와 루틴 기억",
    }[axis]


def _difference_point(axis: str, evidence: dict[str, Any]) -> str:
    signal = _first(evidence.get("signals"))
    return {
        "problem_reframe": f"고객 불편을 먼저 잡고 제품을 해결 루틴으로 배치합니다. {signal}",
        "proof_and_choice": f"성분과 선택 기준을 먼저 보여주고 오퍼를 마지막 근거로 배치합니다. {signal}",
        "identity_and_moment": f"계절감과 자기관리 감정을 먼저 열고 브랜드 경험으로 연결합니다. {signal}",
    }[axis].strip()


def _desire_for(industry: str) -> str:
    return "나에게 어울리는 의미 있는 선택" if industry == "jewelry_luxury" else "과장 없이 이해되고 지속 가능한 관리 방법"


def _channel_role(channel: str) -> str:
    return {
        "instagram_cardnews": "공감에서 이해와 행동까지 순차 설득",
        "instagram_feed": "첫 문장으로 관심을 만들고 저장 또는 클릭 유도",
        "blog_thumbnail": "검색 진입과 클릭 유도",
        "brunch_cover": "콘텐츠 진입과 클릭 유도",
        "blog_inline_image": "근거와 사용 맥락을 설명",
        "community_banner": "짧은 문장으로 이벤트 행동 유도",
        "threads_image": "짧은 문제 제기로 반응 유도",
        "twitter_image": "짧은 문제 제기로 반응 유도",
    }.get(channel, "핵심 메시지 전달")


def _strategy_basis(brief: dict[str, Any], concept: dict[str, Any], channel: str, product: str, offer: str, marketing_evidence: dict[str, Any] | None = None) -> str:
    target = _target_summary(brief) or concept.get("targetInsight", "")
    channel_role = _channel_role(channel)
    parts = [
        f"타깃은 {target}입니다." if target else "",
        _marketing_basis(marketing_evidence or {}),
        _product_role(concept, product),
        _offer_role(offer, concept.get("axis", "")),
        f"{channel_role} 역할에 맞춰 문장 길이와 CTA를 조정했습니다.",
    ]
    return " ".join(part for part in parts if part)


def _product_role(concept: dict[str, Any], product: str) -> str:
    axis = concept.get("axis", "")
    if axis == "problem_reframe":
        return f"{product}는 고객의 불편을 루틴 문제로 다시 보게 만드는 연결 장치입니다."
    if axis == "proof_and_choice":
        return f"{product}는 막연한 기대가 아니라 선택 기준과 사용 맥락을 설명하는 근거입니다."
    if axis == "identity_and_moment":
        return f"{product}는 기능 설명보다 지금 계절의 자기관리 순간을 만드는 매개입니다."
    return f"{product}를 이번 이벤트의 핵심 제품으로 연결했습니다."


def _offer_role(offer: str, axis: str) -> str:
    if not offer:
        return "입력에 없는 가격, 기간, 수량 혜택을 만들지 않고 제품 이해와 행동 유도 중심으로 마무리했습니다."
    if axis == "problem_reframe":
        return f"{offer}{_particle(offer, '은', '는')} 루틴을 시작하는 부담을 낮추는 계기로 제시했습니다."
    if axis == "proof_and_choice":
        return f"{offer}{_particle(offer, '은', '는')} 선택을 마무리할 추가 근거로 제시했습니다."
    if axis == "identity_and_moment":
        return f"{offer}{_particle(offer, '은', '는')} 지금 루틴을 시작할 명분으로 제시했습니다."
    return f"{offer}를 입력된 혜택 범위 안에서만 사용했습니다."


def _verified_facts(brief: dict[str, Any]) -> list[str]:
    values = [
        brief.get("event_name", ""),
        _target_summary(brief),
        _offer_summary(brief),
        *brief.get("constraints", {}).get("required_phrases", []),
    ]
    return [value for value in dict.fromkeys(str(item).strip() for item in values) if value]


def _ready_insight_brief(*, industry: str, event_id: str = "") -> dict[str, Any]:
    payload = read_json(INSIGHT_BRIEF_PATH, default={})
    payload_event_id = str(payload.get("eventId") or "")
    event_matches = not event_id or not payload_event_id or payload_event_id in {event_id, "general"}
    if payload.get("status") != "ready" or payload.get("industry") != industry or not event_matches:
        return {
            "status": "needs_signal_review",
            "selectedSignalCount": int(payload.get("selectedSignalCount") or 0),
            "minimumSelectedSignals": int(payload.get("minimumSelectedSignals") or 3),
            "evidenceSignalIds": [],
            "doNotClaim": payload.get("doNotClaim", []),
        }
    return payload


def _concept_marketing_evidence(insight_brief: dict[str, Any], axis: str, index: int) -> dict[str, Any]:
    if insight_brief.get("status") != "ready":
        return {"status": "needs_signal_review", "signals": [], "signalIds": []}
    if axis == "problem_reframe":
        signals = insight_brief.get("customerPains", []) + insight_brief.get("purchaseObjections", [])
    elif axis == "proof_and_choice":
        signals = insight_brief.get("purchaseObjections", []) + insight_brief.get("productProofs", []) + insight_brief.get("customerDesires", [])
    else:
        signals = insight_brief.get("seasonalHooks", []) + insight_brief.get("trendHooks", []) + insight_brief.get("customerDesires", [])
    selected = _rotate_signals(signals, index, limit=3)
    return {
        "status": "ready",
        "primaryInsight": selected[0] if selected else "",
        "signals": selected,
        "signalIds": insight_brief.get("evidenceSignalIds", [])[:5],
    }


def _copy_marketing_evidence(insight_brief: dict[str, Any], concept: dict[str, Any], channel: str) -> dict[str, Any]:
    if insight_brief.get("status") != "ready":
        return {"status": "needs_signal_review", "signals": [], "signalIds": []}
    channel_signals = insight_brief.get("channelPatterns", []) if channel in {"instagram_cardnews", "instagram_feed", "blog_thumbnail", "blog_inline_image", "community_banner"} else []
    concept_signals = concept.get("marketingEvidence", {}).get("signals", [])
    offer_signals = insight_brief.get("offerAngles", [])
    signals = _unique_texts([*channel_signals[:1], *concept_signals[:2], *offer_signals[:1]])
    return {
        "status": "ready",
        "signals": signals,
        "signalIds": concept.get("marketingSignalIds") or insight_brief.get("evidenceSignalIds", [])[:5],
    }


def _target_from_evidence(default_target: str, evidence: dict[str, Any]) -> str:
    primary = evidence.get("primaryInsight", "")
    if not primary:
        return default_target
    first_sentence = str(primary).split(".")[0].strip()
    return first_sentence if 4 <= len(first_sentence) <= 100 else default_target


def _marketing_basis(evidence: dict[str, Any]) -> str:
    signals = evidence.get("signals", [])
    if not signals:
        return ""
    return f"검수된 마케팅 신호 {len(signals)}개를 근거로 고객 반응 가능성을 보강했습니다."


def _hashtag_direction(event: str, product: str) -> list[str]:
    values = []
    for text in [event, product, "여름스킨케어", "톤케어"]:
        cleaned = re.sub(r"[^가-힣A-Za-z0-9]", "", str(text))
        if cleaned:
            values.append(cleaned[:24])
    return list(dict.fromkeys(values))[:5]


def _repeated_copy_sentences(copy_package: dict[str, Any]) -> list[str]:
    values: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str) and len(value.strip()) >= 16:
            values.append(value.strip())

    for output in copy_package.get("outputs", []):
        collect(output.get("copy", {}))
    counts = {value: values.count(value) for value in set(values)}
    return sorted((value for value, count in counts.items() if count >= 3), key=lambda value: (-counts[value], value))


def _concepts_differ_by_two_fields(concepts: list[dict[str, Any]]) -> bool:
    fields = ("targetInsight", "corePromise", "emotionalDirection", "persuasionSequence", "offerPresentation", "cta")
    for left_index, left in enumerate(concepts):
        for right in concepts[left_index + 1:]:
            differences = sum(left.get(field) != right.get(field) for field in fields)
            if differences < 2:
                return False
    return True


def _rotate_signals(values: list[Any], index: int, limit: int = 2) -> list[str]:
    items = _unique_texts(values)
    if not items:
        return []
    start = (index - 1) % len(items)
    rotated = items[start:] + items[:start]
    return rotated[:limit]


def _unique_texts(values: list[Any]) -> list[str]:
    return [value for value in dict.fromkeys(str(item or "").strip() for item in values) if value]


def _first(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    return str(values[0]).strip() if values else ""


def _compact(text: str, limit: int) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    return value if len(value) <= limit else value[: max(0, limit - 1)].rstrip() + "…"


def _channel_headline(channel: str, concept: dict[str, Any], product: str) -> str:
    axis = concept.get("axis")
    if channel == "blog_thumbnail":
        return "구매 전 확인할 기준을 먼저 보여드립니다" if axis == "proof_and_choice" else f"{product} 루틴을 다시 볼 시간"
    if channel == "community_banner":
        return "여름 톤 케어 선택 기준"
    return concept.get("headlineDirections", [""])[0]


def _blog_title_candidates(concept: dict[str, Any], product: str) -> list[str]:
    axis = concept.get("axis")
    if axis == "proof_and_choice":
        return [
            f"{product}, 구매 전 무엇을 확인해야 할까",
            "여름 톤 케어를 고를 때 필요한 선택 기준",
        ]
    return [value for value in concept.get("headlineDirections", []) if value]


def _blog_intro(evidence: dict[str, Any], concept: dict[str, Any]) -> str:
    signals = evidence.get("signals", [])
    if signals:
        return _user_facing_signal(signals[1] if len(signals) > 1 else signals[0])
    return _user_facing_signal(concept.get("targetInsight", ""))


def _user_facing_signal(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    internal_markers = ("카피", "광고", "주장", "순위", "임상", "입력된", "만들지 않는다", "인스타그램 피드", "블로그", "배너")
    if any(marker in value for marker in internal_markers):
        return "여름 피부 인상과 성분 선택 기준을 함께 확인하려는 고객에게, 과장보다 납득 가능한 루틴 이유를 먼저 보여줍니다."
    return value


def _normalize_for_compare(text: str) -> str:
    return re.sub(r"[^가-힣A-Za-z0-9]", "", str(text or "")).lower()


def _offer_badge(offer: str) -> str:
    if "미니 크림" in offer and "증정" in offer:
        return "미니 크림 증정"
    if "증정" in offer:
        return _compact(offer, 24)
    return _compact(offer, 32)


def _particle(text: str, consonant: str, vowel: str) -> str:
    stripped = re.sub(r"[\s.。!?]+$", "", str(text or "").strip())
    if not stripped:
        return vowel
    if stripped[-1].isdigit():
        return consonant
    code = ord(stripped[-1])
    if not 0xAC00 <= code <= 0xD7A3:
        return vowel
    return consonant if (code - 0xAC00) % 28 else vowel


def _has_broken_korean(text: str) -> bool:
    markers = ("�", "占", "筌", "揶", "甕", "媛", "吏", "怨", "??", "?낅젰", "placeholder", "tbd")
    return any(marker in text for marker in markers) or bool(re.search(r"\?{3,}", text))


def _issue(severity: str, issue_id: str, message: str) -> dict[str, str]:
    return {"severity": severity, "id": issue_id, "message": message}
