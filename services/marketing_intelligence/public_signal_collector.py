"""Convert public marketing observations into reviewable MarketingSignal records.

The collector is intentionally conservative: captured page text or trend notes
are stored as source observations, while generation consumes only reviewed
`normalizedInsight` records.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from core.utils.json_io import read_json, write_json
from services.marketing_intelligence.repository import normalize_signal


SOURCE_KIND_TO_SOURCE_TYPE = {
    "brand_site": "brand_site",
    "public_web": "public_web",
    "google_trends": "google_trends",
    "naver_datalab": "naver_datalab",
    "oliveyoung_rank": "oliveyoung_rank",
    "weather": "weather",
    "calendar": "calendar",
    "meta_ad": "meta_ad",
    "review": "review",
    "event_brief": "internal",
}

EVIDENCE_TYPE_BY_SOURCE = {
    "brand_site": "proof",
    "public_web": "trend",
    "google_trends": "trend",
    "naver_datalab": "trend",
    "oliveyoung_rank": "proof",
    "weather": "timing",
    "calendar": "timing",
    "meta_ad": "channel_pattern",
    "review": "objection",
    "event_brief": "offer",
}

USABLE_FOR_BY_EVIDENCE = {
    "trend": ["concept", "copy"],
    "pain": ["concept", "copy"],
    "desire": ["concept", "copy"],
    "objection": ["concept", "copy", "qa"],
    "proof": ["concept", "copy", "qa"],
    "offer": ["offer", "copy", "qa"],
    "channel_pattern": ["channel", "copy"],
    "timing": ["concept", "offer", "copy"],
}


@dataclass(frozen=True)
class PublicObservation:
    source_kind: str
    observed_text: str
    topic: str
    event_id: str = ""
    url: str = ""
    title: str = ""
    evidence_type: str = ""
    target_segment: str = ""
    normalized_insight: str = ""
    published_at: str = ""
    observed_at: str = ""
    source_name: str = ""
    section: str = ""
    query: str = ""
    methodology: str = ""
    strength: int = 3
    freshness: int = 3
    confidence: int = 2


def load_public_signal_snapshot(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if isinstance(payload, list):
        return {"observations": payload}
    if not isinstance(payload, dict):
        raise ValueError("public signal snapshot must be a JSON object or array")
    return payload


def collect_public_signals_from_snapshot(
    snapshot: dict[str, Any],
    *,
    industry: str = "cosmetics_skincare",
    default_topic: str = "public_marketing_signals",
    default_event_id: str = "",
    auto_select: bool = False,
) -> list[dict[str, Any]]:
    observations = [
        _normalize_observation(
            item,
            default_topic=default_topic,
            default_event_id=default_event_id or str(snapshot.get("eventId") or ""),
        )
        for item in snapshot.get("observations", [])
        if isinstance(item, dict)
    ]
    return [
        public_observation_to_signal(observation, industry=industry, auto_select=auto_select)
        for observation in observations
        if observation.observed_text.strip()
    ]


def public_observation_to_signal(
    observation: PublicObservation,
    *,
    industry: str = "cosmetics_skincare",
    auto_select: bool = False,
) -> dict[str, Any]:
    source_type = SOURCE_KIND_TO_SOURCE_TYPE.get(observation.source_kind, "public_web")
    evidence_type = observation.evidence_type or EVIDENCE_TYPE_BY_SOURCE.get(observation.source_kind, "trend")
    insight = observation.normalized_insight or infer_normalized_insight(observation)
    now = datetime.now(timezone.utc).isoformat()
    signal_text = sanitize_public_observation_text(observation.observed_text)
    risk_flags = (
        ["needs_human_review", "verified_brief_fact"]
        if observation.source_kind == "event_brief"
        else ["needs_human_review", "public_observation_not_copy_source"]
    )
    if source_type in {"meta_ad", "public_web"}:
        risk_flags.append("do_not_copy_original_expression")
    if source_type in {"google_trends", "naver_datalab", "oliveyoung_rank"}:
        risk_flags.append("ranking_or_trend_requires_source_date")
    risk_flags.extend(public_observation_quality_flags(observation, signal_text))
    return normalize_signal({
        "id": _public_signal_id(observation, industry, insight),
        "industry": industry,
        "sourceType": source_type,
        "sourceRef": {
            "collector": "public_signal_collector",
            "sourceKind": observation.source_kind,
            "eventId": observation.event_id,
            "url": observation.url,
            "title": observation.title,
            "host": urlparse(observation.url).netloc if observation.url else "",
            "sourceName": observation.source_name,
            "publishedAt": observation.published_at,
            "observedAt": observation.observed_at,
            "section": observation.section,
            "query": observation.query,
            "methodology": observation.methodology,
        },
        "collectedAt": now,
        "topic": observation.topic,
        "signalText": _compact(signal_text, 260),
        "normalizedInsight": insight,
        "targetSegment": observation.target_segment or infer_target_segment(observation),
        "funnelStage": _funnel_stage_for(evidence_type),
        "evidenceType": evidence_type,
        "strength": observation.strength,
        "freshness": observation.freshness,
        "confidence": observation.confidence,
        "riskFlags": risk_flags,
        "usableFor": USABLE_FOR_BY_EVIDENCE.get(evidence_type, ["concept", "copy"]),
        "review": {
            "decision": "selected" if auto_select and "capture_quality_blocked" not in risk_flags else "unreviewed",
            "reasonTags": ["useful_trend"] if auto_select else [],
            "reviewNote": "공개 관찰 신호. 원문 복사 금지, 추상화된 인사이트만 생성 근거로 사용.",
            "reviewNote": public_review_note(risk_flags, source_kind=observation.source_kind),
            "reviewedAt": now if auto_select else "",
        },
    })


def sanitize_public_observation_text(text: str) -> str:
    value = _clean_text(text)
    value = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\{[\"'][A-Za-z0-9_\-]+[\"']\s*:", " ", value)
    value = re.sub(r"[{}\[\]]", " ", value)
    return _clean_text(value)


def public_observation_quality_flags(observation: PublicObservation, sanitized_text: str | None = None) -> list[str]:
    raw_text = str(observation.observed_text or "")
    text = sanitized_text if sanitized_text is not None else sanitize_public_observation_text(raw_text)
    flags: list[str] = []
    if re.search(r"<(html|body|div|span|script|style|meta|section|article)\b", raw_text, re.IGNORECASE):
        flags.append("raw_html_detected")
    if re.search(r"\{[\"'][A-Za-z0-9_\-]+[\"']\s*:|[\"']slides[\"']\s*:|[\"']headline[\"']\s*:", raw_text):
        flags.append("raw_json_detected")
    if "�" in raw_text or re.search(r"(ì|ë|í|ê|ð|Ã|Â|爰|愿|怨|諛|섏|쒕|좏|留)", raw_text):
        flags.append("broken_text_suspected")
    if len(raw_text) > 1800:
        flags.append("source_text_too_long")
    if len(text) < 35:
        flags.append("thin_public_observation")
    if any(flag in flags for flag in ("raw_html_detected", "raw_json_detected", "broken_text_suspected", "thin_public_observation")):
        flags.append("capture_quality_blocked")
    return list(dict.fromkeys(flags))


def public_review_note(risk_flags: list[str], *, source_kind: str = "") -> str:
    if source_kind == "event_brief":
        return "이벤트 입력에서 확인된 사실 후보. 원본 이벤트 조건과 대조한 뒤 selected로 승격합니다."
    if "capture_quality_blocked" in risk_flags:
        return "공개 관찰 신호지만 캡처 품질 문제가 있어 selected 승격 전 원문/요약을 반드시 정리해야 합니다."
    return "공개 관찰 신호. 원문 복사 금지, 추상화된 인사이트만 생성 근거로 사용."


def infer_normalized_insight(observation: PublicObservation) -> str:
    text = _clean_text(observation.observed_text)
    source_kind = observation.source_kind
    if source_kind == "weather":
        return f"날씨와 계절 변화가 {observation.topic} 이벤트의 지금 행동 명분을 만들 수 있다."
    if source_kind == "calendar":
        return f"캘린더 시점은 고객이 루틴을 다시 정리할 이유를 제공한다."
    if source_kind in {"google_trends", "naver_datalab"}:
        keyword = _keyword_from_text(text)
        return f"검색 흐름에서 '{keyword}' 관심 신호가 보이면 카피는 성분명보다 고객 상황과 선택 이유를 함께 설명해야 한다."
    if source_kind == "oliveyoung_rank":
        keyword = _keyword_from_text(text)
        return f"H&B 인기 맥락에서 '{keyword}' 관련 선택 기준을 확인하려는 고객에게 제품 역할을 구체적으로 설명해야 한다."
    if source_kind == "meta_ad":
        return "경쟁 광고 관찰은 원문을 복사하지 않고 훅 방식, 설득 순서, CTA 구조만 추상화해 참고한다."
    if source_kind == "brand_site":
        keyword = _keyword_from_text(text)
        return f"브랜드/제품 페이지에서 확인된 '{keyword}' 정보는 과장 주장 없이 제품 역할을 설명하는 근거로 사용할 수 있다."
    keyword = _keyword_from_text(text)
    return f"공개 관찰에서 '{keyword}' 맥락이 확인되면 고객 상황과 제품 선택 이유를 함께 연결한다."


def infer_target_segment(observation: PublicObservation) -> str:
    text = observation.observed_text
    if any(token in text for token in ("민감", "자극", "진정")):
        return "자극과 민감 반응을 걱정해 구매 전 기준을 확인하려는 고객"
    if any(token in text for token in ("여름", "자외선", "습도", "장마", "냉방")):
        return "계절 변화 이후 피부 인상과 루틴을 다시 점검하려는 고객"
    if any(token in text for token in ("성분", "나이아신아마이드", "비타민", "PDRN")):
        return "성분명은 알지만 구매 이유를 더 확인하려는 스킨케어 고객"
    return "구매 전 제품 역할과 선택 이유를 확인하려는 고객"


def capture_public_page_snapshot(
    url: str,
    *,
    topic: str,
    event_id: str = "",
    source_kind: str = "public_web",
    output_path: Path | None = None,
    timeout_ms: int = 15000,
    browser_channel: str = "",
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("Playwright is not installed or not available in this environment.") from exc

    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, browser_channel=browser_channel)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 1100})
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            title = page.title()
            body_text = page.locator("body").inner_text(timeout=timeout_ms)
        finally:
            browser.close()
    snapshot = {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "observations": [{
            "sourceKind": source_kind,
            "url": url,
            "title": title,
            "topic": topic,
            "eventId": event_id,
            "observedText": _compact(body_text, 1200),
        }],
    }
    if output_path:
        write_json(output_path, snapshot)
    return snapshot


def _launch_browser(playwright: Any, *, browser_channel: str = "") -> Any:
    channels = [browser_channel] if browser_channel else [None, "chrome", "msedge"]
    errors: list[str] = []
    for channel in channels:
        try:
            if channel:
                return playwright.chromium.launch(channel=channel, headless=True)
            return playwright.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover - environment dependent
            errors.append(f"{channel or 'bundled chromium'}: {exc}")
    raise RuntimeError("No Playwright browser could be launched. " + " | ".join(errors[-3:]))


def _normalize_observation(item: dict[str, Any], *, default_topic: str, default_event_id: str = "") -> PublicObservation:
    return PublicObservation(
        source_kind=str(item.get("sourceKind") or item.get("source_type") or "public_web").strip(),
        observed_text=str(item.get("observedText") or item.get("text") or item.get("summary") or "").strip(),
        topic=str(item.get("topic") or default_topic).strip() or default_topic,
        event_id=str(item.get("eventId") or default_event_id).strip(),
        url=str(item.get("url") or "").strip(),
        title=str(item.get("title") or "").strip(),
        evidence_type=str(item.get("evidenceType") or "").strip(),
        target_segment=str(item.get("targetSegment") or "").strip(),
        normalized_insight=str(item.get("normalizedInsight") or "").strip(),
        published_at=str(item.get("publishedAt") or "").strip(),
        observed_at=str(item.get("observedAt") or "").strip(),
        source_name=str(item.get("sourceName") or "").strip(),
        section=str(item.get("section") or "").strip(),
        query=str(item.get("query") or "").strip(),
        methodology=str(item.get("methodology") or "").strip(),
        strength=_score(item.get("strength"), 3),
        freshness=_score(item.get("freshness"), 3),
        confidence=_score(item.get("confidence"), 2),
    )


def _public_signal_id(observation: PublicObservation, industry: str, insight: str) -> str:
    key = "|".join([
        industry,
        observation.source_kind,
        observation.event_id,
        observation.topic,
        observation.url,
        observation.title,
        insight,
    ])
    return f"public_signal_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"


def _funnel_stage_for(evidence_type: str) -> str:
    return {
        "pain": "awareness",
        "desire": "consideration",
        "objection": "consideration",
        "proof": "consideration",
        "offer": "conversion",
        "channel_pattern": "awareness",
        "timing": "conversion",
        "trend": "awareness",
    }.get(evidence_type, "awareness")


def _keyword_from_text(text: str) -> str:
    tokens = [
        token for token in re.findall(r"[가-힣A-Za-z0-9]+", text)
        if len(token) >= 2 and token not in {"그리고", "하지만", "대한", "있는", "없는", "관련"}
    ]
    return tokens[0] if tokens else "고객 관심"


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _compact(text: str, limit: int) -> str:
    value = _clean_text(text)
    return value if len(value) <= limit else value[: max(0, limit - 1)].rstrip() + "…"


def _score(value: Any, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(1, min(5, number))
