"""계절/캘린더 기반 MarketingSignal 자동 생성.

날씨·계절·캘린더는 결정적(deterministic) 사실이므로 외부 수집 없이 월 기준으로 생성한다.
생성된 신호는 항상 `unreviewed`로 시작해 사람 검수 큐에 들어간다(자동 selected 금지).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.marketing_intelligence.repository import normalize_signal

# 한국 화장품/스킨케어 관점의 월별 계절 맥락.
MONTH_CONTEXT: dict[int, dict[str, Any]] = {
    1: {"season": "한겨울", "topic": "winter_barrier_care", "skin": "난방으로 인한 건조와 각질, 당김", "timing": "신년 루틴 재정비"},
    2: {"season": "늦겨울", "topic": "winter_barrier_care", "skin": "찬바람과 실내 건조로 인한 피부 장벽 저하", "timing": "환절기 진입 전 보습 강화"},
    3: {"season": "초봄", "topic": "spring_transition_care", "skin": "환절기 민감과 미세먼지 자극", "timing": "봄 환절기 진정 루틴"},
    4: {"season": "봄", "topic": "spring_transition_care", "skin": "황사·미세먼지와 일교차로 인한 트러블", "timing": "봄 나들이 전 피부 정돈"},
    5: {"season": "늦봄", "topic": "uv_defense_intro", "skin": "자외선 강해지며 색소·톤 고민 시작", "timing": "초여름 자외선 대비 시작"},
    6: {"season": "초여름·장마", "topic": "summer_tone_care", "skin": "장마철 습도와 실내 냉방의 간극, 칙칙해 보이는 인상", "timing": "여름 루틴 재정비 적기"},
    7: {"season": "한여름", "topic": "summer_sebum_care", "skin": "고온다습으로 인한 유분·모공·번들거림", "timing": "휴가철 피부 컨디션 관리"},
    8: {"season": "늦여름", "topic": "summer_recovery_care", "skin": "자외선 누적 후 진정·수분·톤 회복 수요", "timing": "휴가 후 피부 회복 루틴"},
    9: {"season": "초가을", "topic": "autumn_transition_care", "skin": "여름 손상 회복과 환절기 민감 전환", "timing": "가을 환절기 장벽 정비"},
    10: {"season": "가을", "topic": "autumn_barrier_care", "skin": "건조 시작과 일교차로 인한 속건조", "timing": "겨울 대비 보습 루틴 준비"},
    11: {"season": "늦가을", "topic": "winter_prep_care", "skin": "기온 급강하로 인한 장벽 약화", "timing": "겨울 진입 전 집중 보습"},
    12: {"season": "초겨울", "topic": "winter_barrier_care", "skin": "한파와 난방 건조로 인한 당김·각질", "timing": "연말 선물·자기관리 시즌"},
}


def generate_calendar_signals(
    month: int,
    *,
    industry: str = "cosmetics_skincare",
    now: str | None = None,
) -> list[dict[str, Any]]:
    if month not in MONTH_CONTEXT:
        raise ValueError(f"month must be 1-12, got {month}")
    context = MONTH_CONTEXT[month]
    collected_at = now or datetime.now(timezone.utc).isoformat()
    topic = context["topic"]
    season = context["season"]
    skin = context["skin"]
    timing = context["timing"]
    target = f"{season} 피부 변화에 맞춰 루틴을 조정하려는 스킨케어 고객"

    rows = [
        {
            "evidenceType": "timing",
            "funnelStage": "conversion",
            "signalText": f"{month}월({season})은 {skin} 때문에 {timing} 시점이다.",
            "normalizedInsight": f"{month}월 {season} 맥락({skin})은 지금 루틴을 조정할 시즌 명분으로 쓸 수 있다.",
            "usableFor": ["concept", "offer", "copy"],
        },
        {
            "evidenceType": "trend",
            "funnelStage": "awareness",
            "signalText": f"{season}에는 {skin}이 자주 언급되어 관련 스킨케어 관심이 올라간다.",
            "normalizedInsight": f"{season} 피부 고민({skin})을 먼저 짚으면 제품 역할 설명이 덜 공허해진다.",
            "usableFor": ["concept", "copy"],
        },
    ]

    signals: list[dict[str, Any]] = []
    for row in rows:
        signals.append(normalize_signal({
            "industry": industry,
            "sourceType": "calendar",
            "sourceRef": {
                "generator": "calendar_signals.py",
                "month": month,
                "season": season,
                "note": "결정적 계절/캘린더 맥락. 외부 순위·임상 주장 없음. 사람 검수 후 사용.",
            },
            "collectedAt": collected_at,
            "topic": topic,
            "signalText": row["signalText"],
            "normalizedInsight": row["normalizedInsight"],
            "targetSegment": target,
            "funnelStage": row["funnelStage"],
            "evidenceType": row["evidenceType"],
            "strength": 3,
            "freshness": 5,
            "confidence": 4,
            "riskFlags": ["deterministic_calendar_fact", "no_external_rank_claim"],
            "usableFor": row["usableFor"],
            "review": {"decision": "unreviewed", "reasonTags": [], "reviewNote": "계절 캘린더 자동 신호. 사람 검수 후 selected 가능."},
        }))
    return signals
