"""Deterministic critical-error and copy-quality checks for ad planning."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Callable

from core.utils import channel_registry
from services.ad_strategy.text_quality import text_artifact_summary


IssueFactory = Callable[[str, str, str], dict[str, str]]

CHANNEL_REQUIRED_FIELDS = {
    "instagram_cardnews": ("cover", "slides", "cta"),
    "instagram_feed": ("firstLine", "body", "cta"),
    "blog_thumbnail": ("headline", "subcopy", "cta"),
    "brunch_cover": ("headline", "subcopy", "cta"),
    "community_banner": ("headline", "subcopy", "cta"),
    "blog_inline_image": ("titleCandidates", "intro", "sections", "cta"),
    "threads_image": ("post", "followUp", "cta"),
    "twitter_image": ("post", "followUp", "cta"),
}

CLAIM_PATTERNS = (
    re.compile(r"\b\d+(?:\.\d+)?\s*%"),
    re.compile(r"\b\d{1,3}(?:,\d{3})*\s*원\b"),
    re.compile(r"\b\d+\s*(?:일|주|개월|시간)\b"),
    re.compile(r"\b\d{1,2}\s*/\s*\d{1,2}\b"),
)
OFFER_TERMS = {"할인", "증정", "무료", "쿠폰", "한정", "특가", "선착순"}
HIGH_RISK_CLAIMS = {
    "완치", "치료", "효과 보장", "부작용 없음", "즉시 개선", "100% 개선",
    "무조건 개선", "임상으로 증명", "올리브영 1위", "리뷰 폭발",
}
INTERNAL_MARKERS = {
    "placeholder", "tbd", "작성 필요", "여기에 입력", "입력하세요", "초안 메모",
    "집행 직전", "최신 단기 자료", "사람이 선택한 근거", "입력에 없는",
    "무작위 가설", "근거로 사용하지",
}
INDUSTRY_TERMS = {
    "cosmetics_skincare": {"다이아몬드", "목걸이", "귀걸이", "반지", "팔찌", "캐럿", "주얼리"},
    "jewelry_luxury": {"나이아신아마이드", "앰플", "세럼", "토너", "크림", "피부 장벽", "스킨케어"},
}
CHANNEL_CHARACTER_LIMITS = {
    "instagram_cardnews": 1800,
    "instagram_feed": 2200,
    "blog_thumbnail": 140,
    "brunch_cover": 140,
    "community_banner": 140,
    "blog_inline_image": 6000,
    "threads_image": 500,
    "twitter_image": 280,
}


def deterministic_quality_issues(
    brief: dict[str, Any],
    copy_package: dict[str, Any],
    *,
    industry: str,
    source_originals: list[str],
    issue: IssueFactory,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    outputs = copy_package.get("outputs", [])
    texts = copy_text_values(copy_package)
    full_text = " ".join(texts)
    fact_text = _verified_fact_text(brief)
    artifacts = text_artifact_summary(copy_package)

    if artifacts["brokenKoreanCount"]:
        issues.append(issue("critical", "broken_korean_text", "최종 카피에 깨진 한글 또는 인코딩 오류가 남아 있습니다."))
    if artifacts["rawJsonCount"] or artifacts["rawHtmlCount"] or artifacts["programmingArtifactCount"]:
        issues.append(issue("critical", "raw_structure_exposed", "최종 카피에 JSON/HTML/프로그래밍 구조가 노출되었습니다."))
    if artifacts.get("particleMismatchCount"):
        sample = artifacts.get("samples", {}).get("particleMismatch", ["조사 오류"])[0]
        issues.append(issue("warning", "awkward_korean_particle", f"제품명 뒤 조사가 어색합니다: {sample}"))

    unsupported = unsupported_claims(full_text, fact_text)
    if unsupported:
        issues.append(issue("critical", "unsupported_claim", f"입력 사실에서 확인되지 않은 주장입니다: {unsupported[0]}"))

    mixed_term = next((term for term in INDUSTRY_TERMS.get(industry, set()) if term in full_text), "")
    if mixed_term:
        issues.append(issue("critical", "industry_mismatch", f"다른 업종 표현이 포함되었습니다: {mixed_term}"))

    copied = copied_expression(texts, source_originals)
    if copied:
        issues.append(issue("critical", "copied_expression", f"경쟁사 원문과 지나치게 유사한 표현입니다: {copied}"))

    missing_contract = channel_contract_failure(outputs)
    if missing_contract:
        issues.append(issue("warning", "channel_contract_missing", missing_contract))
    requested_channels = {
        resolved
        for value in brief.get("channels", [])
        if str(value)
        for resolved in channel_registry.resolve_requested(str(value))
    }
    output_channels = {str(value.get("channelId") or "") for value in outputs if value.get("channelId")}
    if requested_channels and output_channels != requested_channels:
        issues.append(issue("critical", "channel_mismatch", f"요청 채널과 생성 채널이 다릅니다: 요청 {sorted(requested_channels)}, 생성 {sorted(output_channels)}"))

    metadata_failure = output_metadata_failure(outputs)
    if metadata_failure:
        issues.append(issue("warning", "output_metadata_missing", metadata_failure))

    length_failure = character_limit_failure(outputs)
    if length_failure:
        issues.append(issue("warning", "channel_character_limit", length_failure))

    if any(marker.lower() in full_text.lower() for marker in INTERNAL_MARKERS):
        issues.append(issue("warning", "internal_writing_marker", "내부 작성용 문구가 최종 카피에 남아 있습니다."))

    required_phrases = [str(value) for value in brief.get("constraints", {}).get("required_phrases", []) if str(value).strip()]
    product = _product_phrase(required_phrases)
    if product and product not in full_text:
        issues.append(issue("warning", "weak_product_connection", f"요청 제품이 완성 카피에 연결되지 않았습니다: {product}"))

    offer = str(_offer_summary(brief)).strip()
    if offer and not _offer_connected(offer, full_text):
        issues.append(issue("warning", "weak_offer_connection", "입력된 오퍼가 완성 카피에 충분히 연결되지 않았습니다."))

    if outputs and any(not _copy_has_cta(item.get("copy", {})) for item in outputs):
        issues.append(issue("warning", "weak_cta", "하나 이상의 채널 카피에 행동 유도 문구가 없습니다."))

    if reused_across_channels(outputs):
        issues.append(issue("warning", "channel_copy_reuse", "여러 채널에서 동일한 긴 문장을 재사용했습니다."))
    return issues


def copy_text_values(copy_package: dict[str, Any]) -> list[str]:
    values: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str) and value.strip():
            values.append(re.sub(r"\s+", " ", value).strip())

    for output in copy_package.get("outputs", []):
        collect(output.get("copy", {}))
    return values


def copy_character_count(copy: Any) -> int:
    """Count user-visible copy text without Python/JSON structure characters."""
    return len("\n".join(value.strip() for value in _copy_values(copy) if value.strip()))


def unsupported_claims(copy_text: str, fact_text: str) -> list[str]:
    claims = []
    for pattern in CLAIM_PATTERNS:
        claims.extend(match.group(0) for match in pattern.finditer(copy_text) if match.group(0) not in fact_text)
    for term in HIGH_RISK_CLAIMS:
        if term in copy_text and term not in fact_text:
            claims.append(term)
    for term in OFFER_TERMS:
        if _contains_korean_token(copy_text, term) and term not in fact_text:
            claims.append(term)
    return list(dict.fromkeys(claims))


def copied_expression(texts: list[str], source_originals: list[str]) -> str:
    generated_sentences = [value for text in texts for value in _sentences(text) if len(_normalize(value)) >= 18]
    source_sentences = [value for text in source_originals for value in _sentences(text) if len(_normalize(value)) >= 18]
    for generated in generated_sentences:
        normalized = _normalize(generated)
        for source in source_sentences:
            source_normalized = _normalize(source)
            if normalized == source_normalized or SequenceMatcher(None, normalized, source_normalized).ratio() >= 0.9:
                return generated[:80]
    return ""


def channel_contract_failure(outputs: list[dict[str, Any]]) -> str:
    for output in outputs:
        channel = str(output.get("channelId") or "")
        copy = output.get("copy")
        if not isinstance(copy, dict):
            return f"{channel or 'unknown'} 채널 카피가 객체가 아닙니다."
        required = CHANNEL_REQUIRED_FIELDS.get(channel, ("headline", "body", "cta"))
        missing = [field for field in required if not copy.get(field)]
        if missing:
            return f"{channel} 채널 필수 필드가 비었습니다: {', '.join(missing)}"
    return ""


def output_metadata_failure(outputs: list[dict[str, Any]]) -> str:
    for output in outputs:
        channel = str(output.get("channelId") or "unknown")
        missing = [field for field in ("purpose", "strategyBasis", "characterCount") if output.get(field) in (None, "")]
        if missing:
            return f"{channel} 결과 메타데이터가 비었습니다: {', '.join(missing)}"
        character_count = output.get("characterCount")
        if not isinstance(character_count, int) or character_count != copy_character_count(output.get("copy", {})):
            return f"{channel} 결과의 characterCount가 실제 카피 길이와 다릅니다."
    return ""


def character_limit_failure(outputs: list[dict[str, Any]]) -> str:
    for output in outputs:
        channel = str(output.get("channelId") or "")
        limit = CHANNEL_CHARACTER_LIMITS.get(channel)
        length = len(" ".join(_copy_values(output.get("copy", {}))))
        if limit and length > limit:
            return f"{channel} 카피가 권장 글자 수를 초과했습니다: {length}/{limit}"
    return ""


def reused_across_channels(outputs: list[dict[str, Any]]) -> bool:
    by_channel = {
        str(output.get("channelId") or ""): {
            _normalize(value) for value in _copy_values(output.get("copy", {})) if len(_normalize(value)) >= 20
        }
        for output in outputs
    }
    channels = list(by_channel)
    return any(by_channel[left] & by_channel[right] for index, left in enumerate(channels) for right in channels[index + 1:])


def _copy_has_cta(copy: dict[str, Any]) -> bool:
    return bool(copy.get("cta") or copy.get("followUp"))


def _offer_connected(offer: str, full_text: str) -> bool:
    tokens = [token for token in re.findall(r"[가-힣A-Za-z0-9%]+", offer) if len(token) >= 2]
    return not tokens or sum(token in full_text for token in tokens) >= max(1, len(tokens) // 2)


def _product_phrase(phrases: list[str]) -> str:
    product_terms = ("나이아신아마이드", "앰플", "세럼", "크림", "토너", "로션", "마스크", "에센스", "선크림", "목걸이", "반지", "귀걸이")
    scored = []
    for phrase in phrases:
        matched = [index for index, term in enumerate(product_terms) if term in phrase]
        if matched:
            scored.append((min(matched), -len(matched), phrase))
    if scored:
        return sorted(scored)[0][2]
    return phrases[-1] if phrases else ""


def _offer_summary(brief: dict[str, Any]) -> str:
    offer = brief.get("offer", "")
    if isinstance(offer, dict):
        return str(offer.get("summary") or "")
    return str(offer or "")


def _contains_korean_token(text: str, token: str) -> bool:
    if not token:
        return False
    return any(match.group(0) == token for match in re.finditer(r"[가-힣]+", text))


def _copy_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            values.extend(_copy_values(child))
    elif isinstance(value, list):
        for child in value:
            values.extend(_copy_values(child))
    elif isinstance(value, str):
        values.append(value)
    return values


def _sentences(text: str) -> list[str]:
    return [value.strip() for value in re.split(r"(?<=[.!?])\s+|\n+", text) if value.strip()]


def _normalize(text: str) -> str:
    return re.sub(r"[^가-힣a-z0-9]", "", text.lower())


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(child) for child in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(child) for child in value)
    return str(value or "")


def _verified_fact_text(brief: dict[str, Any]) -> str:
    verified = {
        "event_name": brief.get("event_name"),
        "brand": brief.get("brand"),
        "target": brief.get("target"),
        "offer": brief.get("offer"),
        "required_phrases": brief.get("constraints", {}).get("required_phrases", []),
        "verifiedFacts": brief.get("verifiedFacts", []),
    }
    return _flatten_text(verified)
