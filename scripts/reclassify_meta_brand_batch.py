#!/usr/bin/env python3
"""Reapply Qwen creative classification to an existing Meta brand batch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.collect_meta_brand_registry import atomic_write_json, media_quality, persist_batch
from services.ad_reference.brand_registry import advertiser_match_type, load_brand_registry
from services.ad_reference.meta_creative_classifier import classify_media


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--review-model", default="qwen2.5vl:7b")
    parser.add_argument("--review-host", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    batch_dir = ROOT / "references" / "meta_ads" / "brand_registry_runs" / args.batch_id
    manifest_path = batch_dir / "brand-collection-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    profile = manifest["profile"]
    registry = load_brand_registry()
    brands = {
        brand["id"]: brand
        for brand in registry["profiles"][profile]["brands"]
    }
    results_by_id: dict[str, dict[str, Any]] = {}

    for previous in manifest.get("results", []):
        brand_id = previous["brandId"]
        brand = brands[brand_id]
        brand_dir = batch_dir / "brands" / brand_id
        source_path = brand_dir / "collected-ads.json"
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        accepted_ads = []
        excluded_ads = []
        advertiser_matched_ads = 0
        excluded_count = 0
        review_count = 0

        for ad in payload.get("items", []):
            match_type = advertiser_match_type(str(ad.get("brand") or ""), brand)
            if not match_type:
                continue
            advertiser_matched_ads += 1
            accepted_media = []
            excluded_media = []
            for media in ad.get("media", []):
                quality = media_quality(media)
                if not quality:
                    continue
                classified = classify_media(
                    {**media, "registryQuality": quality},
                    profile=profile,
                    brand=brand,
                    model=args.review_model,
                    host=args.review_host,
                )
                if classified.get("creativeGate") == "excluded":
                    excluded_media.append(classified)
                    excluded_count += 1
                else:
                    accepted_media.append(classified)
                    review_count += int(classified.get("creativeGate") == "review")
            classified_ad = {
                **ad,
                "media": accepted_media,
                "excludedMedia": excluded_media,
                "brandRegistry": {
                    "profile": profile,
                    "brandId": brand_id,
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
            "registryProfile": profile,
            "registryBrand": brand,
            "strictAdvertiserMatch": True,
            "rawAdCount": payload.get("count", 0),
            "advertiserMatchedAdCount": advertiser_matched_ads,
            "count": len(accepted_ads),
            "downloadedImageCount": sum(len(ad["media"]) for ad in accepted_ads),
            "excludedImageCount": excluded_count,
            "needsCreativeReviewCount": review_count,
            "items": accepted_ads,
            "excludedItems": excluded_ads,
        }
        atomic_write_json(brand_dir / "accepted-ads.json", accepted_payload)
        results_by_id[brand_id] = {
            "brandId": brand_id,
            "brand": brand["name"],
            "query": brand["query"],
            "status": "collected",
            "rawAds": payload.get("count", 0),
            "advertiserMatchedAds": advertiser_matched_ads,
            "acceptedAds": len(accepted_ads),
            "acceptedImages": accepted_payload["downloadedImageCount"],
            "excludedImages": excluded_count,
            "needsCreativeReviewImages": review_count,
            "path": str((brand_dir / "accepted-ads.json").relative_to(ROOT)).replace("\\", "/"),
        }

    result = persist_batch(batch_dir, manifest, results_by_id)
    print(json.dumps({"batch": args.batch_id, **result["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
