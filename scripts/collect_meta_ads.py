#!/usr/bin/env python3
"""Collect Meta Ad Library cards into local JSON and optional Qwen tags."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ad_reference.meta_collector import MetaCollectorOptions, collect_meta_ads
from services.visual_reference.qwen_reviewer import review_image


QWEN_PROMPT = """You are reviewing a Meta advertisement image as a creative reference.
Return JSON only:
{
  "decision": "selected | shortlist | rejected",
  "role": "product | mood | layout | typography | composition",
  "creative_type": "clean_product_visual | single_image_ad | brand_campaign | promotion_structure | card_news",
  "score": 1-100,
  "product_focus": 1-100,
  "category_fit": 1-100,
  "visible_cosmetic_container": true,
  "package_box_only": false,
  "card_news_style": false,
  "large_headline_or_dense_copy": false,
  "text_density": 1-100,
  "layout_usability": 1-100,
  "screen_capture_risk": 1-100,
  "positive_tags": ["..."],
  "negative_tags": ["..."],
  "reason": "...",
  "risk": "..."
}
Clean product visual means an actual skincare/cosmetic container such as a bottle, jar, tube, dropper, pump, or compact is visibly the hero.
Reject package-box-only images, lifestyle props without a visible cosmetic container, low text density, adaptable composition,
and not a price flyer, card-news panel, app/device screen, website capture, or unrelated beauty platform promotion.
Set card_news_style=true for explainer panels, review slides, comparison panels, illustrated information cards, or step-by-step content.
Set large_headline_or_dense_copy=true when large promotional text or multiple text blocks dominate the image.
Do not recommend directly copying the competitor ad."""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--country", default="KR")
    parser.add_argument("--category", default="all")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--scrolls", type=int, default=12)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--qwen", action="store_true")
    parser.add_argument("--qwen-limit", type=int, default=20)
    parser.add_argument("--run", default="")
    parser.add_argument("--advertiser-match", action="store_true")
    parser.add_argument("--skip-video", action="store_true", help="영상 광고(포스터/캡처 프레임)는 이미지로 받지 않음.")
    parser.add_argument(
        "--creative-profile",
        choices=["product_visual", "single_image_ad", "brand_campaign", "promotion_structure", "all"],
        default="product_visual",
    )
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    slug = re.sub(r"[^\w가-힣]+", "-", args.query).strip("-") or "search"
    output_dir = ROOT / "references" / "meta_ads" / "searches" / f"{stamp}_{slug}"
    payload = collect_meta_ads(MetaCollectorOptions(
        query=args.query,
        output_dir=output_dir,
        country=args.country,
        category=args.category,
        limit=max(1, args.limit),
        scrolls=max(0, args.scrolls),
        headless=args.headless,
        skip_video=args.skip_video,
    ))
    if args.qwen:
        reviewed_media = 0
        for item in payload["items"]:
            media = item.get("media") or []
            for media_item in media:
                if reviewed_media >= max(0, args.qwen_limit):
                    break
                try:
                    review = review_image(Path(media_item["savedPath"]), prompt=QWEN_PROMPT)
                    media_item["qwenReview"] = review
                    reviewed_media += 1
                except Exception as exc:
                    media_item["qwenError"] = str(exc)
            if media and media[0].get("qwenReview"):
                review = media[0]["qwenReview"]
                item["qwenReview"] = review
                item["score"] = review.get("score")
                item["visualTags"] = review.get("visualTags") or review.get("positive_tags") or []
                item["copyTags"] = review.get("copyTags") or []
                item["layoutHint"] = review.get("layoutHint") or review.get("reason") or ""
            if reviewed_media >= max(0, args.qwen_limit):
                break
        (output_dir / "collected-ads.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    imported = import_into_run(
        payload,
        Path(args.run),
        creative_profile=args.creative_profile,
        advertiser_match=args.advertiser_match,
    ) if args.run else []
    print(json.dumps({
        "output": str(output_dir),
        "count": payload["count"],
        "downloaded_images": payload.get("downloadedImageCount", 0),
        "imported_references": len(imported),
        "creative_profile": args.creative_profile,
        "advertiser_match": args.advertiser_match,
    }, ensure_ascii=False))
    return 0


def import_into_run(
    payload: dict,
    run_dir: Path,
    *,
    creative_profile: str = "product_visual",
    advertiser_match: bool = False,
) -> list[dict]:
    run_dir = run_dir.resolve()
    if ROOT.resolve() not in [run_dir, *run_dir.parents] or not run_dir.exists():
        raise ValueError(f"Invalid run path: {run_dir}")
    references_dir = run_dir / "references"
    selected_dir = references_dir / "selected"
    selected_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = references_dir / "reference-manifest.json"
    manifest = _read_json(manifest_path, {"assets": [], "sources": {}})
    assets = manifest.setdefault("assets", [])
    existing_hashes = {str(item.get("sha256") or "") for item in assets if item.get("sha256")}
    imported: list[dict] = []
    for ad in payload.get("items", []):
        if advertiser_match and not advertiser_matches_query(ad, str(payload.get("query") or "")):
            continue
        for media_index, media in enumerate(media_for_profile(ad, creative_profile), 1):
            digest = str(media.get("sha256") or "")
            if digest and digest in existing_hashes:
                continue
            source_path = Path(media["savedPath"])
            target_path = selected_dir / f"meta_{ad['libraryId']}_{media_index:02d}{source_path.suffix.lower()}"
            shutil.copy2(source_path, target_path)
            asset = {
                "asset_id": f"meta_{ad['libraryId']}_{media_index:02d}",
                "source": "meta_ad_library",
                "creative_profile": creative_profile,
                "source_id": "meta_ad_library",
                "source_url": ad.get("adLibraryUrl", ""),
                "ad_library_id": ad.get("libraryId", ""),
                "brand": ad.get("brand", ""),
                "query": payload.get("query", ""),
                "title": media.get("alt") or ad.get("brand", ""),
                "copy": ad.get("copy", ""),
                "cta": ad.get("cta", ""),
                "image_url": media.get("imageUrl", ""),
                "downloaded_url": media.get("imageUrl", ""),
                "sha256": digest or hashlib.sha256(source_path.read_bytes()).hexdigest(),
                "width": media.get("width", 0),
                "height": media.get("height", 0),
                "path": str(target_path),
                "relative_path": str(target_path.relative_to(run_dir)),
                "original_path": str(source_path),
                "status": "selected",
                "selected_at": datetime.now(timezone.utc).isoformat(),
                "review_decision": "selected",
                "reason": "Imported from Meta Ad Library for reference review.",
                "qwen_review": ad.get("qwenReview") or {},
            }
            assets.append(asset)
            imported.append(asset)
            existing_hashes.add(asset["sha256"])
    manifest.setdefault("sources", {})["meta_ad_library"] = {
        "source_id": "meta_ad_library",
        "query": payload.get("query", ""),
        "url": payload.get("sourceUrl", ""),
        "collector": "playwright_meta_ad_library",
        "status": "collected",
        "downloaded_count": len(imported),
        "creative_profile": creative_profile,
        "advertiser_match": advertiser_match,
        "collected_at": payload.get("collectedAt", ""),
    }
    manifest["asset_count"] = len(assets)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(manifest_path, manifest)
    selected = [item for item in assets if item.get("status") == "selected"]
    _write_json(references_dir / "selected-references.json", {"selected": selected})
    return imported


def advertiser_matches_query(ad: dict, query: str) -> bool:
    brand = re.sub(r"[\W_]+", "", str(ad.get("brand") or "").lower())
    normalized_query = re.sub(r"[\W_]+", "", query.lower())
    return bool(normalized_query and normalized_query in brand)


def media_for_profile(ad: dict, creative_profile: str) -> list[dict]:
    media = list(ad.get("media") or [])
    copy_text = str(ad.get("copy") or "").lower()
    has_video = bool(re.search(r"\b0:\d{2}\s*/\s*\d+:\d{2}\b", copy_text))
    if creative_profile == "all":
        return media
    if creative_profile == "single_image_ad":
        return [] if has_video or len(media) > 3 else media[:1]
    if creative_profile == "promotion_structure":
        return media[:5]
    if creative_profile == "brand_campaign":
        return media[:3]
    # Clean product visual is judged per image, including images inside carousels.
    selected = []
    for media_item in media:
        review = media_item.get("qwenReview") or {}
        if (
            review.get("creative_type") == "clean_product_visual"
            and float(review.get("product_focus") or 0) >= 70
            and float(review.get("category_fit") or 0) >= 70
            and review.get("visible_cosmetic_container") is True
            and review.get("package_box_only") is not True
            and review.get("card_news_style") is not True
            and review.get("large_headline_or_dense_copy") is not True
            and float(review.get("text_density") or 100) <= 40
            and float(review.get("screen_capture_risk") or 100) <= 30
            and review.get("decision") != "rejected"
        ):
            selected.append(media_item)
    return selected[:3]


def _read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
