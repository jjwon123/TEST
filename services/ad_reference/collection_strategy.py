"""Evidence-based brand ordering for the next Meta registry collection batch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.ad_reference.registry_metrics import DEFAULT_RUNS_ROOT, MANIFEST_NAME


def order_brands(
    profile: str,
    brands: list[dict[str, Any]],
    *,
    strategy: str = "adaptive",
    runs_root: Path = DEFAULT_RUNS_ROOT,
) -> list[dict[str, Any]]:
    if strategy == "registry":
        return brands
    diagnostics = {
        item["brandId"]: item
        for item in aggregate_brand_diagnostics(profile, runs_root)
        if item.get("action") in {"retain", "explore"}
    }
    if not diagnostics:
        return brands
    registry_position = {brand["id"]: index for index, brand in enumerate(brands)}
    recent_ids = _latest_eligible_brand_ids(profile, runs_root)
    retain = sorted(
        (brand for brand in brands if diagnostics.get(brand["id"], {}).get("action") == "retain"),
        key=lambda brand: (-diagnostics[brand["id"]]["priorityScore"], registry_position[brand["id"]]),
    )
    explore = sorted(
        (brand for brand in brands if diagnostics.get(brand["id"], {}).get("action") == "explore"),
        key=lambda brand: (-diagnostics[brand["id"]]["priorityScore"], registry_position[brand["id"]]),
    )
    retain = _cooldown(retain, recent_ids)
    explore = _cooldown(explore, recent_ids)
    # Keep one proven anchor, then spend the batch on coverage growth.
    recommended = retain[:1] + explore + retain[1:]
    remaining = [brand for brand in brands if brand["id"] not in diagnostics]
    return recommended + remaining


def strategy_summary(runs_root: Path = DEFAULT_RUNS_ROOT, limit: int = 8) -> dict[str, Any]:
    from services.ad_reference.brand_registry import load_brand_registry, profile_brands

    profiles = {}
    for profile in load_brand_registry().get("profiles", {}):
        diagnostics = {item["brandId"]: item for item in aggregate_brand_diagnostics(profile, runs_root)}
        ordered = order_brands(profile, profile_brands(profile), runs_root=runs_root)
        profiles[profile] = {
            "recommended": [
                {
                    "brandId": brand["id"],
                    "brand": brand["name"],
                    "action": diagnostics.get(brand["id"], {}).get("action", "unmeasured"),
                    "priorityScore": diagnostics.get(brand["id"], {}).get("priorityScore"),
                    "reason": _action_reason(diagnostics.get(brand["id"], {}).get("action", "unmeasured")),
                }
                for brand in ordered
                if diagnostics.get(brand["id"], {}).get("action") in {"retain", "explore"}
            ][:limit]
        }
    return {
        "strategy": "adaptive",
        "recommendedBatch": {"brandLimit": 5, "adsPerBrand": 5, "minimumRawAds": 20},
        "profiles": profiles,
    }


def aggregate_brand_diagnostics(profile: str, runs_root: Path = DEFAULT_RUNS_ROOT) -> list[dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    if not runs_root.exists():
        return []
    for path in runs_root.glob(f"*/{MANIFEST_NAME}"):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if manifest.get("profile") != profile:
            continue
        for result in manifest.get("results", []):
            if result.get("status") != "collected":
                continue
            if "needsCreativeReviewImages" not in result or _number(result.get("needsCreativeReviewImages")) > 0:
                continue
            brand_id = str(result.get("brandId") or "")
            if not brand_id:
                continue
            item = evidence.setdefault(brand_id, {
                "brandId": brand_id,
                "brand": str(result.get("brand") or brand_id),
                "advertiserMatchedAds": 0,
                "rawAds": 0,
                "acceptedImages": 0,
                "excludedImages": 0,
                "batches": 0,
            })
            item["advertiserMatchedAds"] += _number(result.get("advertiserMatchedAds"))
            item["rawAds"] += _number(result.get("rawAds"))
            item["acceptedImages"] += _number(result.get("acceptedImages"))
            item["excludedImages"] += _number(result.get("excludedImages"))
            item["batches"] += 1
    diagnostics = [_diagnose(item) for item in evidence.values()]
    return sorted(diagnostics, key=lambda item: (-item["priorityScore"], item["brandId"]))


def _diagnose(item: dict[str, Any]) -> dict[str, Any]:
    matched = item["advertiserMatchedAds"]
    raw = item["rawAds"]
    accepted = item["acceptedImages"]
    excluded = item["excludedImages"]
    match_rate = matched / raw if raw else 0.0
    if accepted:
        action, score = "retain", 100 + min(accepted, 20)
    elif raw >= 10 and match_rate < 0.15:
        action, score = "audit_alias", 10
    elif matched and 0 < excluded <= 6:
        action, score = "explore", 70 - excluded
    elif matched and not excluded:
        action, score = "media_gap", 45
    elif matched:
        action, score = "deprioritize_promotion_heavy", max(5, 35 - excluded)
    else:
        action, score = "audit_alias", 0
    return {**item, "action": action, "priorityScore": score, "advertiserMatchRate": round(match_rate, 4)}


def _latest_eligible_brand_ids(profile: str, runs_root: Path) -> set[str]:
    candidates = []
    for path in runs_root.glob(f"*/{MANIFEST_NAME}") if runs_root.exists() else []:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        results = [item for item in manifest.get("results", []) if item.get("status") == "collected"]
        if (
            manifest.get("profile") == profile
            and results
            and sum(_number(item.get("rawAds")) for item in results) > 0
            and all("needsCreativeReviewImages" in item and _number(item.get("needsCreativeReviewImages")) == 0 for item in results)
        ):
            candidates.append((path.stat().st_mtime, results))
    if not candidates:
        return set()
    return {str(item.get("brandId") or "") for item in max(candidates, key=lambda item: item[0])[1]}


def _cooldown(brands: list[dict[str, Any]], recent_ids: set[str]) -> list[dict[str, Any]]:
    return [brand for brand in brands if brand["id"] not in recent_ids] + [brand for brand in brands if brand["id"] in recent_ids]


def _number(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _action_reason(action: str) -> str:
    return {
        "retain": "검증된 통과 앵커",
        "explore": "브랜드 커버리지 확대 후보",
        "media_gap": "정지 이미지 부족 점검",
        "deprioritize_promotion_heavy": "프로모션 문구형 편중으로 후순위",
        "audit_alias": "쿼리·광고주 별칭 점검 필요",
        "unmeasured": "아직 측정되지 않은 브랜드",
    }.get(action, action)
