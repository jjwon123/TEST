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
    return {
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
