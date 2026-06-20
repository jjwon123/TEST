"""올리브영 랭킹·리뷰 키워드 CSV를 MarketingSignal로 변환.

CSV 포맷 (UTF-8, 헤더 필수):
    rank,brand,product,category,review_keywords
    1,브랜드A,수분세럼,세럼,"수분감, 흡수력, 끈적임 없음"
    2,브랜드B,진정크림,크림,"진정, 순함, 향"

- review_keywords는 쉼표/세미콜론/파이프로 구분.
- rank/brand/category는 선택(빈 값 허용), product 또는 review_keywords 중 하나는 있어야 한다.
- 생성 신호는 sourceType=oliveyoung_rank, decision=unreviewed(사람 검수 필요).
  순위·리뷰는 외부 주장이므로 riskFlags로 표시하고 카피 직접 인용을 막는다.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.marketing_intelligence.repository import normalize_signal

REQUIRED_HINT_COLUMNS = {"product", "review_keywords"}


def _split_keywords(value: str) -> list[str]:
    cleaned = str(value or "").replace(";", ",").replace("|", ",")
    return [token.strip() for token in cleaned.split(",") if token.strip()]


def parse_oliveyoung_ranking_csv(
    path: Path,
    *,
    industry: str = "cosmetics_skincare",
    topic: str = "oliveyoung_ranking",
    now: str | None = None,
) -> list[dict[str, Any]]:
    collected_at = now or datetime.now(timezone.utc).isoformat()
    signals: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            product = str(row.get("product") or "").strip()
            keywords = _split_keywords(row.get("review_keywords", ""))
            if not product and not keywords:
                continue  # 근거가 없는 빈 행은 건너뛴다
            rank = str(row.get("rank") or "").strip()
            brand = str(row.get("brand") or "").strip()
            category = str(row.get("category") or "").strip()

            label = " ".join(part for part in [category, f"{rank}위" if rank else "", brand, product] if part).strip()
            keyword_text = ", ".join(keywords) if keywords else "리뷰 키워드 미기재"
            signal_text = f"올리브영 {label or product}의 리뷰 키워드: {keyword_text}."
            insight = (
                f"{label or product} 리뷰에서 자주 나오는 기준({keyword_text})은 고객이 중시하는 "
                f"선택 포인트를 보여준다. 순위·리뷰 수치는 외부 주장이므로 카피에는 직접 인용하지 않고 "
                f"고객 선택 기준으로만 활용한다."
            )

            signals.append(normalize_signal({
                "industry": industry,
                "sourceType": "oliveyoung_rank",
                "sourceRef": {
                    "importer": "oliveyoung_csv.py",
                    "rank": rank,
                    "brand": brand,
                    "product": product,
                    "category": category,
                    "reviewKeywords": keywords,
                    "note": "외부 순위/리뷰 출처. 사람 검수 후 사용. 카피에 순위 직접 인용 금지.",
                },
                "collectedAt": collected_at,
                "topic": topic,
                "signalText": signal_text,
                "normalizedInsight": insight,
                "targetSegment": f"{category or '스킨케어'} 카테고리에서 리뷰를 보고 실패를 줄이려는 고객",
                "funnelStage": "consideration",
                "evidenceType": "trend",
                "strength": 3,
                "freshness": 3,
                "confidence": 3,
                "riskFlags": ["external_rank_claim", "needs_human_review", "no_copy_rank_quote"],
                "usableFor": ["concept", "copy"],
                "review": {"decision": "unreviewed", "reasonTags": [], "reviewNote": "올리브영 랭킹/리뷰 import. 사람 검수 후 selected 가능."},
            }))
    return signals
