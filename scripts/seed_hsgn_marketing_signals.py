"""Seed reviewed HSGN marketing signals and build an event InsightBrief."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.marketing_intelligence.insight_brief import INSIGHT_BRIEF_PATH, build_and_save_insight_brief
from services.marketing_intelligence.repository import SIGNALS_PATH, append_signals, normalize_signal


EVENT_ID = "hsgn-summer-tone-care-2026"
TOPIC = "hsgn_summer_tone_care"


def hsgn_signals() -> list[dict[str, Any]]:
    rows = [
        (
            "pain",
            "여름에는 강한 자외선과 실내외 온도 차 이후 피부가 칙칙해 보인다는 인상을 빠르게 자각한다.",
            "여름 외출 후 피부 인상이 칙칙해 보인다고 느끼는 고객은 강한 효능 주장보다 오늘 루틴을 조정할 이유에 반응한다.",
            "여름 외출 후 피부 인상이 신경 쓰이는 20~40대 스킨케어 고객",
            ["concept", "copy"],
        ),
        (
            "pain",
            "덥고 습한 계절에는 여러 단계를 바르는 루틴보다 가볍게 이해되는 핵심 제품 제안이 더 설득력 있다.",
            "여름 고객은 무거운 루틴보다 핵심 제품 하나의 역할이 분명한 제안을 선호할 수 있다.",
            "복잡한 스킨케어 단계를 줄이고 싶은 고객",
            ["concept", "copy"],
        ),
        (
            "objection",
            "나이아신아마이드는 익숙한 성분이지만 농도 표기만으로는 왜 지금 사야 하는지 부족하게 느껴질 수 있다.",
            "성분명에 익숙한 고객일수록 농도보다 사용 맥락과 선택 기준을 함께 확인하려 한다.",
            "성분명은 알지만 구매 이유가 더 필요한 고객",
            ["concept", "qa"],
        ),
        (
            "objection",
            "화장품 광고에서 순위, 리뷰, 임상 표현이 많을수록 확인되지 않은 과장으로 받아들여질 위험이 있다.",
            "HSGN 카피는 순위나 임상 주장 대신 입력된 성분명, 시즌 맥락, 오퍼만으로 설득해야 한다.",
            "과장 표현에 피로감을 느끼는 고객",
            ["qa", "copy"],
        ),
        (
            "desire",
            "고객은 즉각적인 변화 약속보다 매일 반복 가능한 여름 톤 케어 루틴의 명분을 원한다.",
            "데일리 루틴으로 부담 없이 이어갈 수 있다는 메시지는 여름 스킨케어 구매 저항을 낮춘다.",
            "가벼운 데일리 루틴을 찾는 고객",
            ["concept", "copy"],
        ),
        (
            "desire",
            "미니 크림 증정은 큰 할인보다 루틴을 함께 시작해볼 수 있다는 보조 제품 경험으로 설명할 때 자연스럽다.",
            "증정 오퍼는 가격 혜택보다 루틴 확장 경험으로 연결하면 제품과 더 잘 붙는다.",
            "구매 전 사용 경험의 명분을 원하는 고객",
            ["offer", "copy"],
        ),
        (
            "timing",
            "6월 말은 장마, 습도, 자외선, 냉방 환경이 겹쳐 여름 스킨케어 루틴을 다시 정리하기 좋은 시점이다.",
            "6월 말 여름 루틴 재정비 맥락은 HSGN 톤 케어 이벤트의 시즌 명분으로 사용할 수 있다.",
            "계절 변화에 맞춰 루틴을 바꾸려는 고객",
            ["concept", "copy"],
        ),
        (
            "trend",
            "최근 스킨케어 카피는 성분을 크게 외치기보다 고객 상황, 선택 기준, 루틴 이유를 함께 보여줄 때 신뢰감을 얻는다.",
            "성분 중심 제품도 고객 상황과 선택 기준을 같이 제시해야 광고 문구가 덜 공허해진다.",
            "성분 기반 스킨케어를 비교하는 고객",
            ["concept", "copy"],
        ),
        (
            "proof",
            "HSGN은 'skincare about science, skincare about life'라는 브랜드 문장과 나이아신아마이드 100,000ppm 제품명을 확인된 사실로 사용할 수 있다.",
            "HSGN 카피의 근거는 브랜드의 과학적 태도와 제품명에 명시된 성분 농도 표기에서 출발한다.",
            "브랜드 태도와 제품명을 함께 확인하는 고객",
            ["concept", "copy", "qa"],
        ),
        (
            "offer",
            "입력된 혜택은 HSGN 나이아신아마이드 100,000ppm 구매 시 미니 크림 증정이며, 할인율이나 재고 수량은 확인되지 않았다.",
            "오퍼는 미니 크림 증정까지만 말하고 할인율, 한정 수량, 인기 순위는 만들지 않는다.",
            "혜택 조건을 확인하고 구매하려는 고객",
            ["offer", "qa", "copy"],
        ),
        (
            "channel_pattern",
            "인스타그램 피드는 첫 문장에서 계절 상황을 바로 말하고, 본문에서 제품 역할과 오퍼를 짧게 연결해야 저장과 클릭이 쉽다.",
            "인스타그램 피드는 여름 피부 인상 상황을 먼저 열고 제품 역할과 증정 오퍼를 짧게 연결한다.",
            "모바일에서 빠르게 판단하는 고객",
            ["channel", "copy"],
        ),
        (
            "channel_pattern",
            "블로그형 콘텐츠는 제품명보다 고객 질문으로 시작한 뒤 성분, 사용 맥락, 오퍼를 순서대로 설명할 때 이탈이 줄어든다.",
            "블로그 카피는 고객 질문에서 시작해 성분과 사용 맥락을 설명하고 마지막에 오퍼를 배치한다.",
            "검색 후 비교하며 읽는 고객",
            ["channel", "copy"],
        ),
        (
            "channel_pattern",
            "배너와 썸네일은 성분 농도와 혜택을 모두 넣으려 하기보다 하나의 선택 이유와 하나의 행동만 남겨야 읽힌다.",
            "배너는 여름 톤 케어라는 선택 이유와 미니 크림 증정 확인 행동만 남긴다.",
            "짧은 노출에서 빠르게 판단하는 고객",
            ["channel", "copy"],
        ),
    ]
    now = datetime.now(timezone.utc).isoformat()
    signals: list[dict[str, Any]] = []
    for index, (evidence_type, raw, insight, target, usable_for) in enumerate(rows, start=1):
        signals.append(normalize_signal({
            "id": f"hsgn-summer-tone-care-{index:02d}",
            "industry": "cosmetics_skincare",
            "sourceType": "internal",
            "sourceRef": {
                "eventId": EVENT_ID,
                "source": "manual_marketing_intelligence_seed",
                "note": "HSGN 연결 검증용 1차 근거 신호. 외부 순위, 리뷰, 임상 주장은 포함하지 않음.",
            },
            "collectedAt": now,
            "topic": TOPIC,
            "signalText": raw,
            "normalizedInsight": insight,
            "targetSegment": target,
            "funnelStage": "conversion" if evidence_type in {"offer", "proof"} else "consideration",
            "evidenceType": evidence_type,
            "strength": 4,
            "freshness": 4,
            "confidence": 4,
            "riskFlags": ["no_external_rank_claim", "manual_reviewed_seed"],
            "usableFor": usable_for,
            "review": {
                "decision": "selected",
                "reasonTags": ["useful_target", "useful_season", "strong_product_link"],
                "reviewNote": "HSGN 여름 톤 케어 이벤트 1차 품질 업그레이드용으로 선별한 근거.",
                "reviewedAt": now,
            },
        }))
    return signals


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed HSGN reviewed marketing signals and build InsightBrief.")
    parser.add_argument("--signals-path", type=Path, default=SIGNALS_PATH)
    parser.add_argument("--insight-path", type=Path, default=INSIGHT_BRIEF_PATH)
    args = parser.parse_args()

    append_result = append_signals(hsgn_signals(), args.signals_path)
    brief = build_and_save_insight_brief(
        event_id=EVENT_ID,
        industry="cosmetics_skincare",
        topic=TOPIC,
        minimum_selected=5,
        output=args.insight_path,
        signals_path=args.signals_path,
    )
    print({
        "signals": append_result,
        "insightBrief": {
            "path": str(args.insight_path),
            "status": brief["status"],
            "selectedSignalCount": brief["selectedSignalCount"],
            "eventId": brief["eventId"],
        },
    })


if __name__ == "__main__":
    main()
