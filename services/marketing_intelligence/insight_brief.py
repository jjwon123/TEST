"""Build InsightBrief packets from reviewed MarketingSignal records."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re

from core.utils.json_io import read_json, write_json
from core.utils.schema_validation import validate_json
from services.marketing_intelligence.repository import SIGNALS_PATH, load_signals


ROOT = Path(__file__).resolve().parents[2]
INSIGHT_BRIEF_PATH = ROOT / "design_brain_wiki" / "marketing_signals" / "insight-brief.json"
INSIGHT_BRIEF_DIR = INSIGHT_BRIEF_PATH.parent / "insight-briefs"
INSIGHT_BRIEF_SCHEMA_PATH = ROOT / "core" / "schemas" / "insight-brief.schema.json"
MINIMUM_SELECTED_SIGNALS = 3
BLOCKED_RISK_FLAGS = {
    "capture_quality_blocked",
    "raw_html_detected",
    "raw_json_detected",
    "broken_text_suspected",
}


def build_insight_brief(
    *,
    event_id: str = "general",
    industry: str = "cosmetics_skincare",
    topic: str = "",
    minimum_selected: int = MINIMUM_SELECTED_SIGNALS,
    additional_do_not_claim: list[str] | None = None,
    signals_path: Path = SIGNALS_PATH,
) -> dict[str, Any]:
    selected = [
        signal for signal in load_signals(signals_path)
        if signal.get("industry") == industry
        and signal.get("review", {}).get("decision") == "selected"
        and _matches_event_scope(signal, event_id=event_id, topic=topic)
        and not _has_blocked_risk(signal)
    ]
    selected.sort(key=lambda item: (
        -int(item.get("strength") or 0),
        -int(item.get("freshness") or 0),
        -int(item.get("confidence") or 0),
        str(item.get("id") or ""),
    ))
    brief = {
        "schemaVersion": "1.0.0",
        "eventId": event_id,
        "topic": topic,
        "scopePolicy": "exact_event_or_explicit_topic",
        "industry": industry,
        "status": "ready" if len(selected) >= minimum_selected else "needs_signal_review",
        "minimumSelectedSignals": minimum_selected,
        "selectedSignalCount": len(selected),
        "targetHypotheses": _unique(signal.get("targetSegment") for signal in selected),
        "customerPains": _by_type(selected, "pain"),
        "customerDesires": _by_type(selected, "desire"),
        "purchaseObjections": _by_type(selected, "objection"),
        "trendHooks": _by_type(selected, "trend"),
        "seasonalHooks": _by_type(selected, "timing"),
        "productProofs": _by_type(selected, "proof"),
        "offerAngles": _by_type(selected, "offer"),
        "channelPatterns": _by_type(selected, "channel_pattern"),
        "evidenceDetails": [_evidence_detail(signal) for signal in selected],
        "doNotClaim": [
            "사람이 선택한 근거에 없는 순위, 가격, 효능, 기간 수치를 만들지 않는다.",
            "무작위 가설은 사람이 검수하기 전까지 사실 근거로 사용하지 않는다.",
            "공식 출처가 없는 유행, 날씨, 판매 순위 주장을 단정하지 않는다.",
        ] + [str(item).strip() for item in (additional_do_not_claim or []) if str(item).strip()],
        "evidenceSignalIds": [str(signal.get("id") or "") for signal in selected],
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    validate_json(brief, read_json(INSIGHT_BRIEF_SCHEMA_PATH), data_label="insight brief", schema_label="insight-brief.schema.json")
    return brief


def save_insight_brief(brief: dict[str, Any], path: Path = INSIGHT_BRIEF_PATH) -> None:
    validate_json(brief, read_json(INSIGHT_BRIEF_SCHEMA_PATH), data_label="insight brief", schema_label="insight-brief.schema.json")
    write_json(path, brief)
    if path.resolve() == INSIGHT_BRIEF_PATH.resolve() and str(brief.get("eventId") or "").strip():
        write_json(event_insight_brief_path(str(brief["eventId"]), root=path.parent / "insight-briefs"), brief)


def build_and_save_insight_brief(
    *,
    event_id: str = "general",
    industry: str = "cosmetics_skincare",
    topic: str = "",
    minimum_selected: int = MINIMUM_SELECTED_SIGNALS,
    additional_do_not_claim: list[str] | None = None,
    output: Path = INSIGHT_BRIEF_PATH,
    signals_path: Path = SIGNALS_PATH,
) -> dict[str, Any]:
    brief = build_insight_brief(
        event_id=event_id,
        industry=industry,
        topic=topic,
        minimum_selected=minimum_selected,
        additional_do_not_claim=additional_do_not_claim,
        signals_path=signals_path,
    )
    save_insight_brief(brief, output)
    return brief


def _by_type(signals: list[dict[str, Any]], evidence_type: str) -> list[str]:
    return _unique(
        signal.get("normalizedInsight") or signal.get("signalText")
        for signal in signals
        if signal.get("evidenceType") == evidence_type
    )


def _evidence_detail(signal: dict[str, Any]) -> dict[str, Any]:
    source = signal.get("sourceRef") if isinstance(signal.get("sourceRef"), dict) else {}
    return {
        "signalId": str(signal.get("id") or ""),
        "evidenceType": str(signal.get("evidenceType") or ""),
        "targetSegment": str(signal.get("targetSegment") or ""),
        "insight": str(signal.get("normalizedInsight") or signal.get("signalText") or ""),
        "sourceType": str(signal.get("sourceType") or ""),
        "sourceName": str(source.get("sourceName") or source.get("title") or ""),
        "observedAt": str(source.get("observedAt") or signal.get("collectedAt") or ""),
        "claimBoundary": str(source.get("claimBoundary") or ""),
    }


def _has_blocked_risk(signal: dict[str, Any]) -> bool:
    return bool(BLOCKED_RISK_FLAGS.intersection(set(signal.get("riskFlags") or [])))


def _matches_event_scope(signal: dict[str, Any], *, event_id: str, topic: str) -> bool:
    requested_event = str(event_id or "general").strip()
    requested_topic = str(topic or "").strip()
    signal_event = str((signal.get("sourceRef") or {}).get("eventId") or signal.get("eventId") or "").strip()
    signal_topic = str(signal.get("topic") or "").strip()
    if requested_event == "general" and not requested_topic:
        return True
    if signal_event and signal_event == requested_event:
        return True
    return bool(requested_topic and signal_topic == requested_topic)


def _unique(values: Any) -> list[str]:
    return [value for value in dict.fromkeys(str(item or "").strip() for item in values) if value]


def event_insight_brief_path(event_id: str, root: Path = INSIGHT_BRIEF_DIR) -> Path:
    slug = re.sub(r"[^\w가-힣-]+", "-", str(event_id or "general").strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-") or "general"
    return root / f"{slug}.json"
