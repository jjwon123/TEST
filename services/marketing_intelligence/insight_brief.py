"""Build InsightBrief packets from reviewed MarketingSignal records."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json, write_json
from core.utils.schema_validation import validate_json
from services.marketing_intelligence.repository import SIGNALS_PATH, load_signals


ROOT = Path(__file__).resolve().parents[2]
INSIGHT_BRIEF_PATH = ROOT / "design_brain_wiki" / "marketing_signals" / "insight-brief.json"
INSIGHT_BRIEF_SCHEMA_PATH = ROOT / "core" / "schemas" / "insight-brief.schema.json"
MINIMUM_SELECTED_SIGNALS = 3


def build_insight_brief(
    *,
    event_id: str = "general",
    industry: str = "cosmetics_skincare",
    topic: str = "",
    minimum_selected: int = MINIMUM_SELECTED_SIGNALS,
    signals_path: Path = SIGNALS_PATH,
) -> dict[str, Any]:
    selected = [
        signal for signal in load_signals(signals_path)
        if signal.get("industry") == industry
        and signal.get("review", {}).get("decision") == "selected"
        and (not topic or signal.get("topic") == topic)
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
        "doNotClaim": [
            "selected 신호에 없는 순위, 가격, 효능, 후기 수를 생성하지 않는다.",
            "seed_random 신호는 selected 검수 전까지 사실 근거로 쓰지 않는다.",
            "외부 출처가 없는 유행/날씨/랭킹 주장을 단정하지 않는다.",
        ],
        "evidenceSignalIds": [str(signal.get("id") or "") for signal in selected],
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    validate_json(brief, read_json(INSIGHT_BRIEF_SCHEMA_PATH), data_label="insight brief", schema_label="insight-brief.schema.json")
    return brief


def save_insight_brief(brief: dict[str, Any], path: Path = INSIGHT_BRIEF_PATH) -> None:
    validate_json(brief, read_json(INSIGHT_BRIEF_SCHEMA_PATH), data_label="insight brief", schema_label="insight-brief.schema.json")
    write_json(path, brief)


def build_and_save_insight_brief(
    *,
    event_id: str = "general",
    industry: str = "cosmetics_skincare",
    topic: str = "",
    minimum_selected: int = MINIMUM_SELECTED_SIGNALS,
    output: Path = INSIGHT_BRIEF_PATH,
    signals_path: Path = SIGNALS_PATH,
) -> dict[str, Any]:
    brief = build_insight_brief(
        event_id=event_id,
        industry=industry,
        topic=topic,
        minimum_selected=minimum_selected,
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


def _unique(values: Any) -> list[str]:
    return [value for value in dict.fromkeys(str(item or "").strip() for item in values) if value]
