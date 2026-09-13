"""Reviewed advertising strategy examples and correction records."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json, write_json
from services.ad_strategy.text_quality import has_broken_korean


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_PATH = ROOT / "design_brain_wiki" / "ad_strategy" / "reviewed-strategy-examples.json"
CORRECTIONS_PATH = ROOT / "design_brain_wiki" / "ad_strategy" / "copy-corrections.json"
LEGACY_PATH = ROOT / "design_brain_wiki" / "ad_strategy" / "meta-ad-strategy-library.json"

REASON_TAGS = {
    "generic", "weak_insight", "awkward_korean", "brand_mismatch",
    "unsupported_claim", "copied_expression", "weak_cta", "channel_mismatch",
    "good_hook", "good_structure", "strong_product_link",
}
RUBRIC_KEYS = {
    "strategyClarity", "targetEmpathy", "productConnection", "distinctiveness",
    "channelFit", "koreanCopyQuality", "brandFit", "actionability",
}
EDITABLE_STRATEGY_FIELDS = {
    "targetInsight", "hookMechanism", "persuasionSequence", "offerMechanism",
    "proofMechanism", "ctaType", "toneTraits", "channelFit",
}

STRATEGY_TOKEN_LABELS = {
    "hook": "후킹",
    "cta": "행동 유도",
    "offer": "혜택 제시",
    "reason_to_believe": "선택 근거",
    "usage_or_routine": "사용 루틴",
    "problem_recognition": "문제 인식",
    "brand_statement": "브랜드 선언",
    "problem_empathy": "문제 공감",
    "offer_first": "오퍼 선제시",
    "specific_value": "구체 가치",
    "question_or_challenge": "질문형 후킹",
    "news_announcement": "신규 소식",
    "learn_more": "자세히 보기",
    "soft_action": "부드러운 행동 유도",
    "purchase": "구매 유도",
}


def load_examples() -> list[dict[str, Any]]:
    payload = read_json(EXAMPLES_PATH, default={"examples": []})
    return [item for item in payload.get("examples", []) if isinstance(item, dict)]


def load_examples_for_review() -> list[dict[str, Any]]:
    source_cache: dict[Path, dict[str, Any]] = {}
    enriched = []
    for item in load_examples():
        source_ref = item.get("sourceRef", {})
        source_file = _safe_source_path(source_ref.get("sourceFile"))
        original = {}
        if source_file:
            payload = source_cache.setdefault(source_file, read_json(source_file, default={}))
            library_id = str(source_ref.get("libraryId") or "")
            source_item = next(
                (candidate for candidate in payload.get("items", []) if str(candidate.get("libraryId") or "") == library_id),
                {},
            )
            original = {
                "brand": source_item.get("brand", ""),
                "copy": source_item.get("copy", ""),
                "cta": source_item.get("cta", ""),
                "adLibraryUrl": source_item.get("adLibraryUrl", ""),
                "landingUrl": source_item.get("landingUrl", ""),
            }
        enriched_item = {
            **item,
            "sourceOriginal": original,
            "sourceBrand": original.get("brand", ""),
            "sourceCopyPreview": _preview(original.get("copy", "")),
        }
        enriched_item["reviewRecommendation"] = strategy_review_recommendation(enriched_item)
        enriched.append(enriched_item)
    return enriched


def save_examples(examples: list[dict[str, Any]]) -> None:
    write_json(EXAMPLES_PATH, {
        "schemaVersion": "1.0.0",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "examples": examples,
    })


def import_legacy_as_unreviewed() -> int:
    existing = load_examples()
    existing_ids = {item.get("id") for item in existing}
    legacy = read_json(LEGACY_PATH, default={})
    added = 0
    for record in legacy.get("records", []):
        item = legacy_to_example(record)
        if item["id"] in existing_ids:
            continue
        existing.append(item)
        existing_ids.add(item["id"])
        added += 1
    if added:
        save_examples(existing)
    return added


def legacy_to_example(record: dict[str, Any]) -> dict[str, Any]:
    strategy = record.get("strategy", {})
    profile = record.get("profile")
    industry = profile if profile in {"cosmetics_skincare", "jewelry_luxury"} else "cosmetics_skincare"
    return {
        "id": record.get("patternId") or f"legacy-{record.get('source', {}).get('copyHash', '')[:12]}",
        "industry": industry,
        "sourceType": "meta_ad",
        "sourceRef": record.get("source", {}),
        "eventType": "promotion" if strategy.get("offerMechanics") else "branding",
        "funnelStage": "conversion" if strategy.get("offerMechanics") else "awareness",
        "targetInsight": "",
        "hookMechanism": strategy.get("hookType", "brand_statement"),
        "persuasionSequence": strategy.get("persuasionSequence", []),
        "offerMechanism": ", ".join(strategy.get("offerMechanics", [])),
        "proofMechanism": "",
        "ctaType": strategy.get("ctaType", "soft_action"),
        "toneTraits": strategy.get("toneTraits", []),
        "channelFit": [],
        "review": {"decision": "unreviewed", "scores": {}, "reasonTags": [], "reviewNote": "Legacy pattern; human review required."},
    }


def retrieve_selected(*, industry: str, event_type: str, channels: list[str], limit: int = 6) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in load_examples():
        review = item.get("review", {})
        if review.get("decision") != "selected" or item.get("industry") != industry:
            continue
        score = 5
        score += 3 if item.get("eventType") == event_type else 0
        score += len(set(channels) & set(item.get("channelFit", [])))
        scores = [value for value in review.get("scores", {}).values() if isinstance(value, (int, float))]
        score += int(sum(scores) / len(scores)) if scores else 0
        scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("id"))))
    return [item for _, item in scored[:limit]]


def retrieve_examples(brief: dict[str, Any], *, decision: str, limit: int = 6) -> list[dict[str, Any]]:
    industry = "jewelry_luxury" if any(token in str(brief).lower() for token in ("주얼리", "jewelry", "반지", "목걸이")) else "cosmetics_skincare"
    event_type = "promotion" if brief.get("offer", {}).get("summary") else "branding"
    channels = brief.get("channels", [])
    ranked = retrieve_selected(industry=industry, event_type=event_type, channels=channels, limit=limit) if decision == "selected" else [
        item for item in load_examples()
        if item.get("industry") == industry and item.get("review", {}).get("decision") == decision
    ][:limit]
    return ranked


def strategy_review_recommendation(example: dict[str, Any]) -> dict[str, Any]:
    """Return a non-authoritative review draft for faster human strategy review."""
    copy_text = str((example.get("sourceOriginal") or {}).get("copy") or "")
    hook = str(example.get("hookMechanism") or "")
    sequence = [str(item) for item in example.get("persuasionSequence") or [] if str(item)]
    offer = str(example.get("offerMechanism") or "")
    cta = str(example.get("ctaType") or "")
    tone_traits = [str(item) for item in example.get("toneTraits") or [] if str(item)]
    reasons: list[str] = []
    risk_flags: list[str] = []
    score = 4

    if len(copy_text.strip()) >= 80:
        score += 1
        reasons.append("원문 길이가 충분해 전략 추상이 가능합니다.")
    else:
        risk_flags.append("원문이 짧아 전략 근거가 약합니다.")
        score -= 1
    if has_broken_korean(copy_text):
        risk_flags.append("원문 또는 수집 텍스트에 깨진 문자가 있습니다.")
        score -= 3
    if not re.search(r"[가-힣]", copy_text):
        risk_flags.append("한국어 화장품 카피 학습용으로 바로 쓰기 어렵습니다.")
        score -= 2
    if any(token in copy_text.lower() for token in ("library id", "라이브러리 id", "드롭다운 열기", "광고 상세 정보 보기")):
        risk_flags.append("Meta UI 수집 문구가 섞여 있어 원문 정제가 필요합니다.")
        score -= 1
    if hook in {"problem_empathy", "specific_value", "question_or_challenge", "offer_first"}:
        score += 2
        reasons.append("후킹 방식이 비교적 선명합니다.")
    elif hook == "brand_statement":
        reasons.append("브랜드 선언형이라 참고는 가능하지만 차별성 검수가 필요합니다.")
    if "reason_to_believe" in sequence or "usage_or_routine" in sequence:
        score += 1
        reasons.append("설득 순서에 근거 또는 사용 맥락이 포함됩니다.")
    if offer:
        score += 1
        reasons.append("오퍼 연결 방식이 있어 전환 캠페인 참고에 좋습니다.")
    if cta in {"purchase", "learn_more", "soft_action"}:
        score += 1
    score = max(0, min(10, score))

    if score >= 8 and not risk_flags:
        suggested_decision = "selected"
    elif score >= 5:
        suggested_decision = "shortlist"
    else:
        suggested_decision = "rejected"

    suggested_scores = _suggested_strategy_scores(score, hook, sequence, offer, risk_flags)
    strategy = {
        "targetInsight": example.get("targetInsight") or _suggested_target_insight(hook, sequence, offer),
        "hookMechanism": hook,
        "persuasionSequence": sequence,
        "offerMechanism": offer,
        "proofMechanism": example.get("proofMechanism") or _suggested_proof_mechanism(sequence, copy_text),
        "ctaType": cta,
        "toneTraits": tone_traits,
        "channelFit": example.get("channelFit") or _suggested_channel_fit(hook, sequence, offer),
    }
    reason_tags = _suggested_reason_tags(suggested_decision, hook, sequence, offer, risk_flags)
    return {
        "suggestedDecision": suggested_decision,
        "score": score,
        "confidence": "high" if score >= 8 or score <= 3 else "medium",
        "reasons": reasons,
        "riskFlags": risk_flags,
        "suggestedScores": suggested_scores,
        "suggestedReasonTags": reason_tags,
        "suggestedStrategy": strategy,
        "reviewNote": _suggested_review_note(suggested_decision, reasons, risk_flags),
    }


def _suggested_strategy_scores(
    score: int,
    hook: str,
    sequence: list[str],
    offer: str,
    risk_flags: list[str],
) -> dict[str, int]:
    base = 4 if score >= 6 else 3
    scores = {
        "strategyClarity": base,
        "targetEmpathy": 4 if hook in {"problem_empathy", "question_or_challenge"} else base,
        "productConnection": 4 if "usage_or_routine" in sequence or "reason_to_believe" in sequence else base,
        "distinctiveness": 4 if hook in {"specific_value", "question_or_challenge", "offer_first"} else 3,
        "channelFit": 4,
        "koreanCopyQuality": 3 if risk_flags else 4,
        "brandFit": base,
        "actionability": 4 if offer or hook == "offer_first" else base,
    }
    if score >= 8 and not risk_flags:
        return {key: max(value, 4) for key, value in scores.items()}
    if score <= 3:
        return {key: min(value, 2 if key in {"koreanCopyQuality", "brandFit"} else 3) for key, value in scores.items()}
    return scores


def _suggested_target_insight(hook: str, sequence: list[str], offer: str) -> str:
    if hook == "problem_empathy" or "problem_recognition" in sequence:
        return "문제를 느끼고 있지만 어떤 기준으로 제품을 골라야 할지 확신이 부족한 고객"
    if hook == "specific_value" or "reason_to_believe" in sequence:
        return "성분, 사용감, 루틴 근거를 보고 납득한 뒤 구매를 결정하려는 고객"
    if hook == "question_or_challenge":
        return "익숙한 선택 기준을 다시 확인하고 더 나은 대안을 찾고 싶은 고객"
    if hook == "offer_first" or offer:
        return "혜택이 명확할 때 체험이나 구매를 빠르게 결정하는 고객"
    if hook == "news_announcement":
        return "신제품이나 새로운 소식에 반응하지만 사용 이유를 함께 확인하고 싶은 고객"
    return "브랜드와 제품 메시지를 훑어본 뒤 나에게 맞는 이유를 짧게 확인하고 싶은 고객"


def _suggested_proof_mechanism(sequence: list[str], copy_text: str) -> str:
    if "reason_to_believe" in sequence:
        return "성분, 기술, 순위, 전문가 관점처럼 선택 이유를 제시하는 구조"
    if "usage_or_routine" in sequence:
        return "사용 장면과 루틴 변화를 보여줘 제품 필요성을 납득시키는 구조"
    if re.search(r"(랭킹|1위|TOP|성분|기술|전문가|약사|피부)", copy_text, re.I):
        return "원문에 포함된 선택 근거를 추상화해 제품 신뢰를 만드는 구조"
    return "직접적인 효능 단정보다 브랜드 메시지와 행동 유도를 연결하는 구조"


def _suggested_channel_fit(hook: str, sequence: list[str], offer: str) -> list[str]:
    channels = ["instagram_feed"]
    if "usage_or_routine" in sequence or "problem_recognition" in sequence:
        channels.append("instagram_cardnews")
    if "reason_to_believe" in sequence:
        channels.append("blog_inline_image")
    if offer or hook == "offer_first":
        channels.append("blog_thumbnail")
    return list(dict.fromkeys(channels))


def _suggested_reason_tags(
    decision: str,
    hook: str,
    sequence: list[str],
    offer: str,
    risk_flags: list[str],
) -> list[str]:
    tags: list[str] = []
    if decision == "rejected":
        tags.append("awkward_korean" if risk_flags else "generic")
    if hook in {"problem_empathy", "question_or_challenge", "specific_value"}:
        tags.append("good_hook")
    if "reason_to_believe" in sequence or "usage_or_routine" in sequence:
        tags.append("good_structure")
    if offer:
        tags.append("strong_product_link")
    if not tags:
        tags.append("generic")
    return [tag for tag in dict.fromkeys(tags) if tag in REASON_TAGS]


def _suggested_review_note(decision: str, reasons: list[str], risk_flags: list[str]) -> str:
    if decision == "rejected":
        return "추천 거절: " + (" ".join(risk_flags) if risk_flags else "전략 차별성 또는 학습 가치가 약합니다.")
    if decision == "selected":
        return "추천 선택: " + (" ".join(reasons) if reasons else "전략 구조가 선명하고 생성 예시로 사용할 수 있습니다.")
    return "추천 참고: " + (" ".join(reasons + risk_flags) if reasons or risk_flags else "일부 보완 후 참고 근거로 사용할 수 있습니다.")


def _preview(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else f"{text[:limit - 1]}..."


def update_example_review(example_id: str, review: dict[str, Any]) -> dict[str, Any]:
    examples = load_examples()
    item = next((example for example in examples if example.get("id") == example_id), None)
    if not item:
        raise ValueError(f"Unknown strategy example: {example_id}")
    decision = str(review.get("decision") or "").strip()
    if decision not in {"selected", "shortlist", "rejected", "unreviewed"}:
        raise ValueError("Invalid strategy review decision.")
    scores = {
        key: max(1, min(5, int(value)))
        for key, value in (review.get("scores") or {}).items()
        if isinstance(value, (int, float))
    }
    if decision != "unreviewed" and set(scores) != RUBRIC_KEYS:
        raise ValueError("All eight strategy rubric scores are required.")
    reason_tags = [tag for tag in dict.fromkeys(review.get("reasonTags", [])) if tag in REASON_TAGS]
    review_note = str(review.get("reviewNote") or "").strip()
    strategy_updates = review.get("strategy") or {}
    for field in EDITABLE_STRATEGY_FIELDS:
        if field not in strategy_updates:
            continue
        value = strategy_updates[field]
        if field in {"persuasionSequence", "toneTraits", "channelFit"}:
            item[field] = [str(entry).strip() for entry in value if str(entry).strip()] if isinstance(value, list) else []
        else:
            item[field] = str(value or "").strip()
    if decision == "selected":
        missing_strategy = [field for field in ("targetInsight", "hookMechanism", "persuasionSequence", "ctaType") if not item.get(field)]
        if missing_strategy:
            raise ValueError(f"Selected strategy is incomplete: {', '.join(missing_strategy)}")
        if sum(scores.values()) / len(scores) < 4:
            raise ValueError("Selected strategy requires an average rubric score of at least 4.")
    if decision != "unreviewed" and not reason_tags:
        raise ValueError("Strategy review requires at least one reason tag.")
    if decision != "unreviewed" and len(review_note) < 5:
        raise ValueError("Strategy review requires a specific review note.")
    item["review"] = {
        "decision": decision,
        "scores": scores,
        "reasonTags": reason_tags,
        "reviewNote": review_note,
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
    }
    save_examples(examples)
    return item


def load_corrections() -> list[dict[str, Any]]:
    return read_json(CORRECTIONS_PATH, default={"records": []}).get("records", [])


def retrieve_corrections(*, industry: str, brand_name: str = "", approved_only: bool = True, limit: int = 6) -> list[dict[str, Any]]:
    normalized_brand = brand_name.strip().lower()
    records = [
        item for item in load_corrections()
        if item.get("industry") == industry
        and (not approved_only or item.get("approved") is True)
        and (
            (
                normalized_brand
                and (
                    not str(item.get("brandName") or "").strip()
                    or str(item.get("brandName") or "").strip().lower() == normalized_brand
                )
            )
            or (
                not normalized_brand
                and not str(item.get("brandName") or "").strip()
            )
        )
    ]
    records.sort(key=lambda item: (
        str(item.get("brandName") or "").strip().lower() == normalized_brand,
        str(item.get("createdAt") or ""),
    ))
    return records[-limit:]


def strategy_quality_metrics() -> dict[str, Any]:
    examples = load_examples()
    corrections = load_corrections()
    decisions = {decision: sum(item.get("review", {}).get("decision") == decision for item in examples) for decision in ("selected", "shortlist", "rejected", "unreviewed")}
    reviewed = len(examples) - decisions["unreviewed"]
    approved = [item for item in corrections if item.get("approved") is True]
    unedited = [item for item in approved if item.get("originalCopy") == item.get("editedCopy")]
    scores = [
        value for item in examples for value in item.get("review", {}).get("scores", {}).values()
        if isinstance(value, (int, float))
    ]
    return {
        "examples": len(examples),
        "reviewed": reviewed,
        "reviewProgress": round(reviewed / len(examples), 3) if examples else 0,
        "decisions": decisions,
        "corrections": len(corrections),
        "approvedCorrections": len(approved),
        "averageHumanScore": round(sum(scores) / len(scores), 2) if scores else 0,
        "unchangedApprovalRate": round(len(unedited) / len(approved), 3) if approved else 0,
        "benchmark": read_json(ROOT / ".tmp" / "model-benchmarks" / "cosmetics-planning-benchmark.json", default={}).get("summary", {}),
        "goalAudit": read_json(ROOT / ".tmp" / "model-benchmarks" / "ad-planning-goal-audit.json", default={}),
    }


def append_correction(record: dict[str, Any]) -> dict[str, Any]:
    _validate_correction(record)
    payload = read_json(CORRECTIONS_PATH, default={"records": []})
    records = payload.setdefault("records", [])
    created = datetime.now(timezone.utc).isoformat()
    normalized = {
        **record,
        "id": record.get("id") or hashlib.sha256(f"{record.get('runId')}|{record.get('channelId')}|{created}".encode()).hexdigest()[:16],
        "eventId": str(record.get("eventId") or ""),
        "eventName": str(record.get("eventName") or ""),
        "brandName": str(record.get("brandName") or ""),
        "reasonTags": [tag for tag in dict.fromkeys(record.get("reasonTags", [])) if tag in REASON_TAGS],
        "originalCopy": record.get("originalCopy", {}),
        "editedCopy": record.get("editedCopy", {}),
        "model": record.get("model", ""),
        "approved": bool(record.get("approved")),
        "createdAt": created,
    }
    existing_index = next((index for index, item in enumerate(records) if item.get("id") == normalized["id"]), None)
    if existing_index is None:
        records.append(normalized)
    else:
        normalized["createdAt"] = records[existing_index].get("createdAt") or created
        normalized["updatedAt"] = created
        records[existing_index] = normalized
    payload["schemaVersion"] = "1.0.0"
    payload["updatedAt"] = created
    write_json(CORRECTIONS_PATH, payload)
    return normalized


def _safe_source_path(value: Any) -> Path | None:
    if not value:
        return None
    candidate = (ROOT / str(value)).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _validate_correction(record: dict[str, Any]) -> None:
    required_text = ("runId", "eventId", "eventName", "brandName", "industry", "channelId", "model")
    missing = [field for field in required_text if not str(record.get(field) or "").strip()]
    required_values = ("originalCopy", "editedCopy", "reasonTags", "qaResult", "strategyExampleIds", "approved")
    missing.extend(field for field in required_values if field not in record)
    if missing:
        raise ValueError(f"Incomplete copy correction record: {', '.join(missing)}")
    if record.get("industry") not in {"cosmetics_skincare", "jewelry_luxury"}:
        raise ValueError("Invalid correction industry.")
    if not isinstance(record.get("originalCopy"), dict) or not isinstance(record.get("editedCopy"), dict):
        raise ValueError("Correction originalCopy and editedCopy must be objects.")
