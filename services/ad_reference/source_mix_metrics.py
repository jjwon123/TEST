"""Measure reviewed Meta search queries as fallback reference sources."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEARCH_ROOT = ROOT / "references" / "meta_ads" / "searches"


def source_mix_summary(search_root: Path = DEFAULT_SEARCH_ROOT) -> dict[str, Any]:
    queries: dict[str, dict[str, Any]] = {}
    for path in search_root.glob("*/collected-ads.json") if search_root.exists() else []:
        payload = _read_json(path)
        query = str(payload.get("query") or "").strip()
        if not query:
            continue
        item = queries.setdefault(query, {
            "query": query,
            "queryType": query_type(query),
            "collections": 0,
            "ads": 0,
            "media": 0,
            "reviewedMedia": 0,
            "cleanProductVisuals": 0,
        })
        item["collections"] += 1
        item["ads"] += int(payload.get("count") or 0)
        for ad in payload.get("items", []):
            for media in ad.get("media", []):
                item["media"] += 1
                review = media.get("qwenReview")
                if not isinstance(review, dict):
                    continue
                item["reviewedMedia"] += 1
                if review.get("creative_type") == "clean_product_visual" and review.get("decision") != "rejected":
                    item["cleanProductVisuals"] += 1
    results = []
    for item in queries.values():
        item["cleanProductRate"] = _ratio(item["cleanProductVisuals"], item["reviewedMedia"])
        results.append(item)
    results.sort(key=lambda item: (item["cleanProductRate"] or 0, item["cleanProductVisuals"], item["reviewedMedia"]), reverse=True)
    recommended = [
        item for item in results
        if item["queryType"] in {"product_or_ingredient", "category_plus_offer"}
        and item["reviewedMedia"] >= 5
        and (item["cleanProductRate"] or 0) >= 0.2
    ][:5]
    collection_plan = [
        item for item in sorted(
            (item for item in results if item["queryType"] == "product_or_ingredient" and item["reviewedMedia"] < 5),
            key=lambda item: (item["reviewedMedia"], -item["media"], item["query"]),
        )
    ][:3]
    total_reviewed = sum(item["reviewedMedia"] for item in results)
    total_clean = sum(item["cleanProductVisuals"] for item in results)
    summary = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "validated_fallback" if recommended else "insufficient_evidence",
        "queryCount": len(results),
        "reviewedMedia": total_reviewed,
        "cleanProductVisuals": total_clean,
        "cleanProductRate": _ratio(total_clean, total_reviewed),
        "recommendedQueries": recommended,
        "collectionPlan": collection_plan,
        "queries": results,
    }
    summary["regressionGate"] = source_mix_regression_gate(summary)
    return summary


def source_mix_regression_gate(
    summary: dict[str, Any],
    *,
    min_clean_rate: float = 0.2,
    min_reviewed: int = 10,
) -> dict[str, Any]:
    """공급 품질 회귀를 자동 판정한다.

    - insufficient_evidence: 검수 표본이 작아 회귀 판정 불가(공급 보류).
    - disable: 충분한 표본인데 추천 쿼리가 0개 → 공급하면 안 됨(자동 비활성화 권고).
    - warn: 전체 clean product rate가 기준 미만(추천 쿼리는 있으나 품질 저하 경고).
    - ok: 정상 공급 가능.
    """
    reviewed = int(summary.get("reviewedMedia") or 0)
    rate = summary.get("cleanProductRate")
    recommended = len(summary.get("recommendedQueries") or [])

    def result(status: str, reasons: list[str], allowed: bool) -> dict[str, Any]:
        return {
            "status": status,
            "reasons": reasons,
            "supplyAllowed": allowed,
            "reviewedMedia": reviewed,
            "cleanProductRate": rate,
            "recommendedQueries": recommended,
        }

    # 추천 쿼리가 있으면 per-query gate를 이미 통과한 것이므로 공급을 막지 않는다.
    # 회귀 gate는 전체 품질 저하를 경고/차단하는 역할만 한다.
    if recommended >= 1:
        if rate is not None and rate < min_clean_rate:
            return result("warn", [f"overall_clean_product_rate<{min_clean_rate}"], True)
        return result("ok", [], True)
    # 추천 쿼리 0개: 표본이 충분한데도 없으면 품질 회귀로 보고 비활성화 권고.
    if reviewed >= min_reviewed:
        return result("disable", ["no_recommended_queries_despite_evidence"], False)
    return result("insufficient_evidence", [f"reviewedMedia<{min_reviewed}"], False)


def query_type(query: str) -> str:
    normalized = query.casefold()
    if any(token in normalized for token in ("세일", "할인", "sale", "discount")):
        return "category_plus_offer"
    if any(token in normalized for token in ("세럼", "앰플", "크림", "제품", "serum", "cream", "niacinamide", "나이아신아마이드")):
        return "product_or_ingredient"
    return "brand_or_other"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError):
        return {}


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None
