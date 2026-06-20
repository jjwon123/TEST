"""Operational metrics for Meta known-brand collection batches."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_ROOT = ROOT / "references" / "meta_ads" / "brand_registry_runs"
MANIFEST_NAME = "brand-collection-manifest.json"


def collection_metrics_summary(runs_root: Path = DEFAULT_RUNS_ROOT) -> dict[str, Any]:
    batches = []
    if runs_root.exists():
        for manifest_path in runs_root.glob(f"*/{MANIFEST_NAME}"):
            metric = batch_metrics(manifest_path)
            if metric:
                batches.append(metric)
    batches.sort(key=lambda item: (item["modifiedAt"], item["batchId"]), reverse=True)

    latest_by_profile: dict[str, dict[str, Any]] = {}
    for batch in batches:
        profile = batch["profile"]
        if profile and profile not in latest_by_profile and batch["summary"]["collectedBrands"] > 0 and batch["summary"]["rawAds"] > 0:
            latest_by_profile[profile] = batch

    warnings = [warning for batch in latest_by_profile.values() for warning in batch["warnings"]]
    benchmark_by_profile: dict[str, dict[str, Any]] = {}
    for batch in batches:
        profile = batch["profile"]
        current = benchmark_by_profile.get(profile)
        if profile and batch["summary"]["collectedBrands"] > 0 and batch["summary"]["rawAds"] > 0 and (
            not current or batch["summary"]["collectedBrands"] > current["summary"]["collectedBrands"]
        ):
            benchmark_by_profile[profile] = batch
    aggregate_recommendations = _aggregate_recommendations(batches)
    adaptive_performance = _aggregate_strategy_performance(batches, benchmark_by_profile)
    return {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "warning" if warnings else "pass" if batches else "no_data",
        "batchCount": len(batches),
        "latestByProfile": latest_by_profile,
        "benchmarkByProfile": benchmark_by_profile,
        "recommendedNextBrandsByProfile": aggregate_recommendations,
        "adaptivePerformanceByProfile": adaptive_performance,
        "recentBatches": batches[:10],
        "warnings": warnings,
    }


def batch_metrics(manifest_path: Path) -> dict[str, Any] | None:
    manifest = _read_json(manifest_path)
    if not manifest:
        return None
    summary = manifest.get("summary", {})
    results = manifest.get("results", [])
    collected = _number(summary.get("collectedBrands"))
    raw_ads = _number(summary.get("rawAds"))
    matched_ads = _number(summary.get("advertiserMatchedAds"))
    accepted_images = _number(summary.get("acceptedImages"))
    excluded_images = _number(summary.get("excludedImages"))
    reviewed_images = accepted_images + excluded_images
    brands_with_images = _number(summary.get("brandsWithAcceptedImages"))
    brand_counts = sorted(
        (
            {"brandId": item.get("brandId", ""), "brand": item.get("brand", ""), "acceptedImages": _number(item.get("acceptedImages"))}
            for item in results
            if _number(item.get("acceptedImages"))
        ),
        key=lambda item: item["acceptedImages"],
        reverse=True,
    )
    top_count = brand_counts[0]["acceptedImages"] if brand_counts else 0
    creative_types = _creative_type_counts(manifest_path.parent)
    brand_diagnostics = sorted(
        (_brand_diagnostic(item) for item in results if item.get("status") == "collected"),
        key=lambda item: (-item["priorityScore"], item["brandId"]),
    )

    metric = {
        "batchId": manifest_path.parent.name,
        "profile": str(manifest.get("profile") or ""),
        "collectionStrategy": str(manifest.get("collectionStrategy") or "legacy"),
        "modifiedAt": datetime.fromtimestamp(manifest_path.stat().st_mtime, timezone.utc).isoformat(),
        "summary": {
            "collectedBrands": collected,
            "brandsWithAdvertiserMatches": _number(summary.get("brandsWithAdvertiserMatches")),
            "brandsWithAcceptedImages": brands_with_images,
            "rawAds": raw_ads,
            "advertiserMatchedAds": matched_ads,
            "acceptedImages": accepted_images,
            "excludedImages": excluded_images,
            "needsCreativeReviewImages": _number(summary.get("needsCreativeReviewImages")),
            "errors": _number(summary.get("errors")),
        },
        "rates": {
            "advertiserMatchRate": _ratio(matched_ads, raw_ads),
            "creativeAcceptanceRate": _ratio(accepted_images, reviewed_images),
            "brandCoverageRate": _ratio(brands_with_images, collected),
            "topBrandShare": _ratio(top_count, accepted_images),
        },
        "zeroMatchBrands": sum(1 for item in results if not _number(item.get("advertiserMatchedAds"))),
        "zeroAcceptedBrands": sum(1 for item in results if not _number(item.get("acceptedImages"))),
        "strategyEligible": bool(results) and all(
            item.get("status") != "collected"
            or ("needsCreativeReviewImages" in item and _number(item.get("needsCreativeReviewImages")) == 0)
            for item in results
        ),
        "topBrands": brand_counts[:5],
        "creativeTypeCounts": dict(creative_types.most_common()),
        "brandDiagnostics": brand_diagnostics,
        "recommendedNextBrands": [item for item in brand_diagnostics if item["action"] in {"retain", "explore"}][:8],
    }
    metric["warnings"] = _warnings(metric)
    metric["status"] = "warning" if metric["warnings"] else "pass"
    return metric


def _creative_type_counts(batch_dir: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in batch_dir.glob("brands/*/accepted-ads.json"):
        payload = _read_json(path)
        for media in _iter_media(payload.get("items", []), "media"):
            counts[str(media.get("creativeType") or "unclassified")] += 1
        for media in _iter_media(payload.get("excludedItems", []), "excludedMedia"):
            counts[str(media.get("creativeType") or "unclassified")] += 1
    return counts


def _aggregate_recommendations(batches: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    evidence: dict[str, dict[str, dict[str, Any]]] = {}
    for batch in batches:
        if not batch.get("strategyEligible"):
            continue
        profile_evidence = evidence.setdefault(batch["profile"], {})
        for item in batch.get("brandDiagnostics", []):
            target = profile_evidence.setdefault(item["brandId"], {
                "brandId": item["brandId"],
                "brand": item["brand"],
                "status": "collected",
                "advertiserMatchedAds": 0,
                "acceptedImages": 0,
                "excludedImages": 0,
            })
            for key in ("advertiserMatchedAds", "acceptedImages", "excludedImages"):
                target[key] += _number(item.get(key))
    return {
        profile: [
            item for item in sorted(
                (_brand_diagnostic(item) for item in items.values()),
                key=lambda item: (-item["priorityScore"], item["brandId"]),
            )
            if item["action"] in {"retain", "explore"}
        ][:8]
        for profile, items in evidence.items()
    }


def _aggregate_strategy_performance(
    batches: list[dict[str, Any]],
    benchmarks: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}
    for batch in batches:
        if batch.get("collectionStrategy") != "adaptive" or not batch.get("strategyEligible") or batch["summary"]["rawAds"] <= 0:
            continue
        item = totals.setdefault(batch["profile"], {
            "batchCount": 0,
            "brandIds": set(),
            "acceptedBrandIds": set(),
            "rawAds": 0,
            "advertiserMatchedAds": 0,
            "acceptedImages": 0,
            "excludedImages": 0,
        })
        item["batchCount"] += 1
        for brand in batch.get("brandDiagnostics", []):
            item["brandIds"].add(brand["brandId"])
            if brand["acceptedImages"] > 0:
                item["acceptedBrandIds"].add(brand["brandId"])
        for key in ("rawAds", "advertiserMatchedAds", "acceptedImages", "excludedImages"):
            item[key] += batch["summary"][key]

    output = {}
    for profile, item in totals.items():
        reviewed = item["acceptedImages"] + item["excludedImages"]
        rates = {
            "advertiserMatchRate": _ratio(item["advertiserMatchedAds"], item["rawAds"]),
            "creativeAcceptanceRate": _ratio(item["acceptedImages"], reviewed),
            "brandCoverageRate": _ratio(len(item["acceptedBrandIds"]), len(item["brandIds"])),
        }
        benchmark_rates = benchmarks.get(profile, {}).get("rates", {})
        output[profile] = {
            "batchCount": item["batchCount"],
            "uniqueBrands": len(item["brandIds"]),
            "brandsWithAcceptedImages": len(item["acceptedBrandIds"]),
            "rawAds": item["rawAds"],
            "advertiserMatchedAds": item["advertiserMatchedAds"],
            "acceptedImages": item["acceptedImages"],
            "excludedImages": item["excludedImages"],
            "rates": rates,
            "deltaVsBenchmark": {
                "creativeAcceptanceRate": _delta(rates["creativeAcceptanceRate"], benchmark_rates.get("creativeAcceptanceRate")),
                "brandCoverageRate": _delta(rates["brandCoverageRate"], benchmark_rates.get("brandCoverageRate")),
            },
            "operatingDecision": _strategy_decision(item["rawAds"], rates),
        }
    return output


def _iter_media(items: Any, key: str) -> Iterable[dict[str, Any]]:
    for item in items if isinstance(items, list) else []:
        for media in item.get(key, []) if isinstance(item, dict) else []:
            if isinstance(media, dict):
                yield media


def _warnings(metric: dict[str, Any]) -> list[dict[str, Any]]:
    rates = metric["rates"]
    summary = metric["summary"]
    warnings = []
    checks = [
        (rates["advertiserMatchRate"] is not None and rates["advertiserMatchRate"] < 0.3, "low_advertiser_match", "광고주 일치율이 30% 미만입니다."),
        (rates["creativeAcceptanceRate"] is not None and rates["creativeAcceptanceRate"] < 0.1, "low_creative_acceptance", "성격 검수 통과율이 10% 미만입니다."),
        (rates["brandCoverageRate"] is not None and rates["brandCoverageRate"] < 0.3, "low_brand_coverage", "통과 이미지가 있는 브랜드가 30% 미만입니다."),
        (summary["acceptedImages"] >= 10 and rates["topBrandShare"] is not None and rates["topBrandShare"] > 0.4, "high_brand_concentration", "한 브랜드가 통과 이미지의 40%를 초과합니다."),
        (summary["errors"] > 0, "collection_errors", "수집 오류가 남아 있습니다."),
        (summary["needsCreativeReviewImages"] > 0, "creative_review_pending", "성격 검수 대기 이미지가 남아 있습니다."),
        (
            summary["advertiserMatchedAds"] > 0 and (summary["acceptedImages"] + summary["excludedImages"]) == 0,
            "no_reviewable_images",
            "광고주는 일치하지만 판정 가능한 정지 이미지가 없습니다.",
        ),
        (
            summary["collectedBrands"] < 5 or summary["rawAds"] < 20 or (summary["acceptedImages"] + summary["excludedImages"]) < 10,
            "small_sample",
            "표본이 작아 수집 전략 개선 여부를 확정할 수 없습니다.",
        ),
    ]
    for triggered, code, message in checks:
        if triggered:
            warnings.append({"batchId": metric["batchId"], "profile": metric["profile"], "code": code, "message": message})
    return warnings


def _brand_diagnostic(item: dict[str, Any]) -> dict[str, Any]:
    matched = _number(item.get("advertiserMatchedAds"))
    accepted = _number(item.get("acceptedImages"))
    excluded = _number(item.get("excludedImages"))
    evaluated = accepted + excluded
    if accepted:
        action, score, reason = "retain", 100 + min(accepted, 20), "실제 통과 이미지를 만든 브랜드입니다."
    elif matched and 0 < excluded <= 6:
        action, score, reason = "explore", 70 - excluded, "일치 광고와 정지 이미지가 있어 추가 탐색 가치가 있습니다."
    elif matched and not evaluated:
        action, score, reason = "media_gap", 45, "광고주는 일치하지만 판정 가능한 정지 이미지가 없습니다."
    elif matched and excluded > 6:
        action, score, reason = "deprioritize_promotion_heavy", max(5, 35 - excluded), "탈락 이미지가 많아 같은 검색 반복 효율이 낮습니다."
    else:
        action, score, reason = "audit_alias", 0, "광고주 일치 결과가 없어 쿼리·별칭·국가 점검이 필요합니다."
    return {
        "brandId": str(item.get("brandId") or ""),
        "brand": str(item.get("brand") or item.get("brandId") or ""),
        "action": action,
        "priorityScore": score,
        "reason": reason,
        "advertiserMatchedAds": matched,
        "acceptedImages": accepted,
        "excludedImages": excluded,
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError):
        return {}


def _number(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _delta(value: float | None, baseline: float | None) -> float | None:
    return round(value - baseline, 4) if value is not None and baseline is not None else None


def _strategy_decision(raw_ads: int, rates: dict[str, float | None]) -> dict[str, str]:
    coverage = rates.get("brandCoverageRate")
    if raw_ads < 50:
        return {
            "status": "insufficient_evidence",
            "role": "under_evaluation",
            "message": "원본 광고 50개 이상 누적 후 공급원 적합성을 판정합니다.",
        }
    if coverage is not None and coverage < 0.3:
        return {
            "status": "source_limited",
            "role": "secondary_campaign_reference",
            "message": "검증 브랜드 Meta 수집은 클린 제품 비주얼의 단독 공급원으로 부족합니다. 캠페인·프로모션 구조 참고용으로 사용하고 상품·성분 쿼리와 다른 출처를 병행합니다.",
        }
    return {
        "status": "validated",
        "role": "primary_candidate_source",
        "message": "현재 커버리지 기준을 충족해 주요 후보 공급원으로 사용할 수 있습니다.",
    }
