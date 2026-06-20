#!/usr/bin/env python3
"""Collect strict advertiser-matched Meta images from the known-brand registry."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ad_reference.brand_registry import advertiser_match_type, load_brand_registry, profile_brands
from services.ad_reference.collection_strategy import order_brands
from services.ad_reference.meta_creative_classifier import classify_media
from services.ad_reference.meta_collector import MetaCollectorOptions, collect_meta_ads


OUTPUT_ROOT = ROOT / "references" / "meta_ads" / "brand_registry_runs"
MANIFEST_NAME = "brand-collection-manifest.json"
FAILED_BRANDS_NAME = "failed-brands.json"


def main() -> int:
    args = parse_args()
    manifest = run_collection(args)
    print(json.dumps({"output": relative(Path(manifest["batchDir"])), **manifest["summary"]}, ensure_ascii=False))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["cosmetics_skincare", "jewelry_luxury"], required=True)
    parser.add_argument("--brand-id", action="append", default=[], help="Collect only these brand ids.")
    parser.add_argument("--brand-limit", type=int, default=5)
    parser.add_argument("--strategy", choices=["adaptive", "registry"], default="adaptive")
    parser.add_argument("--ads-per-brand", type=int, default=5)
    parser.add_argument("--scrolls", type=int, default=5)
    parser.add_argument("--media-type", choices=["image", "all"], default="all")
    parser.add_argument("--skip-video", action="store_true", help="영상 광고 미디어를 받지 않음(취향 학습 노이즈 제거).")
    parser.add_argument("--country", default="")
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-creative-review",
        action="store_true",
        help="Skip Qwen-VL creative classification. Unclassified images remain review candidates.",
    )
    parser.add_argument("--review-limit", type=int, default=100, help="Maximum images classified per brand.")
    parser.add_argument("--review-model", default="qwen2.5vl:7b")
    parser.add_argument("--review-host", default="http://127.0.0.1:11434")
    parser.add_argument("--batch-id", help="Stable batch directory name. Required when resuming.")
    parser.add_argument("--resume", action="store_true", help="Resume an existing --batch-id and skip collected brands.")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Resume an existing --batch-id and retry only brands recorded in failed-brands.json.",
    )
    args = parser.parse_args(argv)
    if (args.resume or args.retry_failed) and not args.batch_id:
        parser.error("--resume/--retry-failed requires --batch-id")
    return args


def run_collection(
    args: argparse.Namespace,
    *,
    collector: Callable[[MetaCollectorOptions], dict[str, Any]] = collect_meta_ads,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    registry = load_brand_registry()
    profile_config = registry["profiles"][args.profile]
    default_country = profile_config.get("defaultCountry") or "KR"
    batch_dir, manifest = prepare_batch(args, args.country or default_country)
    country = args.country or manifest.get("country") or default_country
    manifest["country"] = country
    brands = selected_brands(args, manifest)
    results_by_id = {item["brandId"]: item for item in manifest.get("results", [])}

    for brand in brands:
        previous = results_by_id.get(brand["id"], {})
        if args.retry_failed and previous.get("status") != "error":
            continue
        if args.resume and not args.retry_failed and previous.get("status") == "collected":
            continue
        if args.dry_run:
            results_by_id[brand["id"]] = brand_result(brand, "planned")
            persist_batch(batch_dir, manifest, results_by_id)
            continue
        brand_dir = batch_dir / "brands" / brand["id"]
        results_by_id[brand["id"]] = brand_result(brand, "collecting")
        persist_batch(batch_dir, manifest, results_by_id)
        try:
            payload = collector(MetaCollectorOptions(
                query=brand["query"],
                output_dir=brand_dir,
                country=country,
                category="all",
                media_type=getattr(args, "media_type", "all"),
                limit=max(1, args.ads_per_brand),
                scrolls=max(0, args.scrolls),
                headless=not args.headful,
                skip_video=getattr(args, "skip_video", False),
            ))
            accepted_ads = []
            excluded_ads = []
            advertiser_matched_ads = 0
            excluded_media_count = 0
            review_media_count = 0
            classified_media_count = 0
            for ad in payload.get("items", []):
                match_type = advertiser_match_type(str(ad.get("brand") or ""), brand)
                if not match_type:
                    continue
                advertiser_matched_ads += 1
                accepted_media = []
                excluded_media = []
                for media in ad.get("media", []):
                    quality = media_quality(media)
                    if quality:
                        classified = {**media, "registryQuality": quality}
                        if (
                            not getattr(args, "no_creative_review", False)
                            and classified_media_count < max(0, getattr(args, "review_limit", 100))
                        ):
                            classified = classify_media(
                                classified,
                                profile=args.profile,
                                brand=brand,
                                model=getattr(args, "review_model", "qwen2.5vl:7b"),
                                host=getattr(args, "review_host", "http://127.0.0.1:11434"),
                            )
                            classified_media_count += 1
                        else:
                            classified.update({
                                "creativeType": "unclassified",
                                "creativeGate": "review",
                                "creativeExclusionReasons": [],
                                "needsCreativeReview": True,
                            })
                        if classified.get("creativeGate") == "excluded":
                            excluded_media.append(classified)
                            excluded_media_count += 1
                        else:
                            accepted_media.append(classified)
                            review_media_count += int(classified.get("creativeGate") == "review")
                classified_ad = {
                    **ad,
                    "media": accepted_media,
                    "excludedMedia": excluded_media,
                    "brandRegistry": {
                        "profile": args.profile,
                        "brandId": brand["id"],
                        "brandName": brand["name"],
                        "roles": brand.get("roles", []),
                        "advertiserMatched": True,
                        "advertiserMatchType": match_type,
                    },
                }
                if accepted_media:
                    accepted_ads.append(classified_ad)
                elif excluded_media:
                    excluded_ads.append(classified_ad)
            accepted_payload = {
                **payload,
                "registryProfile": args.profile,
                "registryBrand": brand,
                "strictAdvertiserMatch": True,
                "rawAdCount": payload.get("count", 0),
                "advertiserMatchedAdCount": advertiser_matched_ads,
                "count": len(accepted_ads),
                "downloadedImageCount": sum(len(ad.get("media", [])) for ad in accepted_ads),
                "excludedImageCount": excluded_media_count,
                "needsCreativeReviewCount": review_media_count,
                "items": accepted_ads,
                "excludedItems": excluded_ads,
            }
            atomic_write_json(brand_dir / "accepted-ads.json", accepted_payload)
            results_by_id[brand["id"]] = {
                "brandId": brand["id"],
                "brand": brand["name"],
                "query": brand["query"],
                "status": "collected",
                "rawAds": payload.get("count", 0),
                "advertiserMatchedAds": advertiser_matched_ads,
                "acceptedAds": len(accepted_ads),
                "acceptedImages": accepted_payload["downloadedImageCount"],
                "excludedImages": excluded_media_count,
                "needsCreativeReviewImages": review_media_count,
                "path": relative(brand_dir / "accepted-ads.json"),
            }
        except Exception as exc:
            results_by_id[brand["id"]] = {**brand_result(brand, "error"), "error": str(exc)}
        persist_batch(batch_dir, manifest, results_by_id)
        sleep_fn(max(0, args.delay))

    return persist_batch(batch_dir, manifest, results_by_id)


def prepare_batch(args: argparse.Namespace, country: str) -> tuple[Path, dict[str, Any]]:
    if args.resume or args.retry_failed:
        batch_dir = OUTPUT_ROOT / safe_batch_id(args.batch_id)
        manifest_path = batch_dir / MANIFEST_NAME
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Cannot resume missing batch manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("profile") != args.profile:
            raise ValueError(f"Batch profile is {manifest.get('profile')}, not {args.profile}")
        manifest["batchDir"] = str(batch_dir)
        return batch_dir, manifest

    requested_id = safe_batch_id(args.batch_id) if args.batch_id else f"{datetime.now():%Y-%m-%d_%H-%M-%S}_{args.profile}"
    batch_dir = reserve_batch_dir(requested_id)
    brands = choose_new_batch_brands(args)
    manifest = {
        "schemaVersion": 2,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "batchDir": str(batch_dir),
        "profile": args.profile,
        "country": country,
        "strictAdvertiserMatch": True,
        "collectionStrategy": getattr(args, "strategy", "adaptive"),
        "brandCount": len(brands),
        "summary": {},
        "results": [brand_result(brand, "planned") for brand in brands],
    }
    persist_batch(batch_dir, manifest, {item["brandId"]: item for item in manifest["results"]})
    return batch_dir, manifest


def choose_new_batch_brands(args: argparse.Namespace) -> list[dict[str, Any]]:
    brands = profile_brands(args.profile)
    if args.brand_id:
        requested = set(args.brand_id)
        return [brand for brand in brands if brand["id"] in requested]
    brands = order_brands(args.profile, brands, strategy=getattr(args, "strategy", "adaptive"))
    return brands[: max(1, args.brand_limit)]


def selected_brands(args: argparse.Namespace, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    brands_by_id = {brand["id"]: brand for brand in profile_brands(args.profile)}
    selected_ids = [item["brandId"] for item in manifest.get("results", [])]
    if args.brand_id:
        requested = set(args.brand_id)
        selected_ids = [brand_id for brand_id in selected_ids if brand_id in requested]
    return [brands_by_id[brand_id] for brand_id in selected_ids if brand_id in brands_by_id]


def reserve_batch_dir(batch_id: str) -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for index in range(1, 10_000):
        suffix = "" if index == 1 else f"-{index:02d}"
        candidate = OUTPUT_ROOT / f"{batch_id}{suffix}"
        try:
            candidate.mkdir(parents=False, exist_ok=False)
            return candidate
        except FileExistsError:
            continue
    raise RuntimeError(f"Could not reserve a unique batch directory for: {batch_id}")


def safe_batch_id(value: str | None) -> str:
    batch_id = str(value or "").strip()
    if not batch_id or batch_id in {".", ".."} or Path(batch_id).name != batch_id:
        raise ValueError(f"Invalid batch id: {value!r}")
    if not re.fullmatch(r"[\w.-]+", batch_id, flags=re.UNICODE):
        raise ValueError(f"Invalid batch id: {value!r}")
    return batch_id


def brand_result(brand: dict[str, Any], status: str) -> dict[str, Any]:
    return {"brandId": brand["id"], "brand": brand["name"], "query": brand["query"], "status": status}


def persist_batch(
    batch_dir: Path,
    manifest: dict[str, Any],
    results_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ordered_ids = [item["brandId"] for item in manifest.get("results", [])]
    results = [results_by_id[brand_id] for brand_id in ordered_ids if brand_id in results_by_id]
    manifest["updatedAt"] = datetime.now(timezone.utc).isoformat()
    manifest["results"] = results
    manifest["summary"] = summarize(results)
    failed = [item for item in results if item.get("status") == "error"]
    atomic_write_json(batch_dir / MANIFEST_NAME, manifest)
    atomic_write_json(batch_dir / FAILED_BRANDS_NAME, {
        "schemaVersion": 1,
        "updatedAt": manifest["updatedAt"],
        "profile": manifest["profile"],
        "count": len(failed),
        "brands": failed,
    })
    return manifest


def summarize(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "plannedBrands": sum(item.get("status") == "planned" for item in results),
        "collectingBrands": sum(item.get("status") == "collecting" for item in results),
        "collectedBrands": sum(item.get("status") == "collected" for item in results),
        "brandsWithAdvertiserMatches": sum(int(item.get("advertiserMatchedAds", 0)) > 0 for item in results),
        "brandsWithAcceptedImages": sum(int(item.get("acceptedImages", 0)) > 0 for item in results),
        "rawAds": sum(int(item.get("rawAds", 0)) for item in results),
        "advertiserMatchedAds": sum(int(item.get("advertiserMatchedAds", 0)) for item in results),
        "acceptedAds": sum(int(item.get("acceptedAds", 0)) for item in results),
        "acceptedImages": sum(int(item.get("acceptedImages", 0)) for item in results),
        "excludedImages": sum(int(item.get("excludedImages", 0)) for item in results),
        "needsCreativeReviewImages": sum(int(item.get("needsCreativeReviewImages", 0)) for item in results),
        "errors": sum(item.get("status") == "error" for item in results),
    }


def media_quality(media: dict[str, Any]) -> str:
    width = int(media.get("width") or 0)
    height = int(media.get("height") or 0)
    saved_path = Path(str(media.get("savedPath") or ""))
    if not saved_path.exists() or not saved_path.is_file():
        return ""
    if min(width, height) < 450 or max(width, height) < 600:
        return ""
    ratio = width / height if height else 0
    if not 0.55 <= ratio <= 1.9:
        return ""
    try:
        if len(saved_path.read_bytes()) < 10_000:
            return ""
    except OSError:
        return ""
    return "standard" if min(width, height) >= 500 else "review"


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


if __name__ == "__main__":
    raise SystemExit(main())
