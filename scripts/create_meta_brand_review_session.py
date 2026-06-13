#!/usr/bin/env python3
"""Create a balanced console review session from known-brand Meta images."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "references" / "meta_ads" / "brand_registry_runs"
META_ROOT = ROOT / "references" / "meta_ads"
TRAINING_ROOT = ROOT / "design_brain_wiki" / "training_sessions" / "meta_brand_review"
WIKI_SOURCES = [
    "knowledge/META_BRAND_REGISTRY.md",
    "design_brain_wiki/00_JUDGE_SCHEMA.md",
    "design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json",
    "design_brain_wiki/05_industry_playbooks/deep/cosmetics_skincare_v0_2.md",
    "design_brain_wiki/05_industry_playbooks/deep/jewelry_luxury_v0_2.md",
]

if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from services.ad_reference.brand_registry import advertiser_match_type, load_brand_registry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", default="meta_brand_review_001")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-per-brand", type=int, default=20)
    parser.add_argument("--max-per-ad", type=int, default=5)
    parser.add_argument("--partner-limit", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    session_dir = TRAINING_ROOT / args.session_id
    if session_dir.exists() and args.force:
        shutil.rmtree(session_dir)
    references_dir = session_dir / "references"
    references_dir.mkdir(parents=True, exist_ok=True)

    records = collect_records()
    chosen = balanced_records(
        records,
        max(1, args.limit),
        max_per_brand=max(1, args.max_per_brand),
        max_per_ad=max(1, args.max_per_ad),
        partner_limit=max(0, args.partner_limit),
    )
    items = []
    for index, record in enumerate(chosen, start=1):
        source = Path(record["savedPath"])
        target = references_dir / f"{index:03d}_{record['brandId']}_{record['sha256'][:10]}{source.suffix.lower()}"
        shutil.copy2(source, target)
        items.append(build_item(record, target, index))

    report = {
        "sessionId": args.session_id,
        "sessionType": "meta_brand_registry_review",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "profile": "meta_brand_review",
        "purpose": "Review balanced, advertiser-matched Meta brand images before connecting them to briefs.",
        "sourceRun": "references/meta_ads/brand_registry_runs",
        "localModelUsed": False,
        "judgementMethod": "Direct advertiser first, balanced by brand and ad; partner ads are explicitly labeled.",
        "selectionPolicy": {
            "requestedLimit": args.limit,
            "maxPerBrand": args.max_per_brand,
            "maxPerAd": args.max_per_ad,
            "partnerLimit": args.partner_limit,
        },
        "wikiSources": WIKI_SOURCES,
        "summary": summary(items),
        "items": items,
    }
    write_json(session_dir / "ai_judgement.json", report)
    (session_dir / "README.md").write_text(render_readme(report), encoding="utf-8")
    print(json.dumps({"session": relative(session_dir), **report["summary"]}, ensure_ascii=False))
    return 0


def registry_brands() -> list[dict[str, Any]]:
    registry = load_brand_registry()
    return [
        {**brand, "profile": profile}
        for profile, config in registry.get("profiles", {}).items()
        for brand in config.get("brands", [])
        if brand.get("active", True)
    ]


def collect_records() -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    brands = registry_brands()
    brands_by_id = {brand["id"]: brand for brand in brands}

    for path in sorted(SOURCE_ROOT.rglob("accepted-ads.json")):
        payload = read_json(path, {})
        registry_brand = payload.get("registryBrand", {})
        profile = str(payload.get("registryProfile") or "")
        for ad in payload.get("items", []):
            brand_meta = ad.get("brandRegistry") or {}
            brand_id = brand_meta.get("brandId") or registry_brand.get("id") or "brand"
            brand = brands_by_id.get(brand_id, registry_brand)
            match_type = brand_meta.get("advertiserMatchType") or advertiser_match_type(
                str(ad.get("brand") or ""), brand
            )
            if not match_type:
                continue
            for media in ad.get("media", []):
                source = Path(str(media.get("savedPath") or ""))
                quality = media.get("registryQuality") or review_media_quality(media, source)
                if not quality:
                    continue
                digest = str(media.get("sha256") or "") or hashlib.sha256(source.read_bytes()).hexdigest()
                incoming = build_record(
                    media,
                    digest=digest,
                    profile=profile or brand_meta.get("profile", ""),
                    brand=brand,
                    advertiser=str(ad.get("brand") or ""),
                    match_type=match_type,
                    ad=ad,
                    quality=str(quality),
                )
                keep_higher_priority(records, digest, incoming)

    for path in sorted(META_ROOT.rglob("collected-ads.json")):
        if "brand_registry_runs" in path.parts:
            continue
        payload = read_json(path, {})
        for ad in payload.get("items", []):
            brand, match_type = match_registry_brand(str(ad.get("brand") or ""), brands)
            if not brand:
                continue
            for media in ad.get("media", []):
                source = Path(str(media.get("savedPath") or ""))
                quality = review_media_quality(media, source)
                if not quality:
                    continue
                digest = str(media.get("sha256") or "") or hashlib.sha256(source.read_bytes()).hexdigest()
                incoming = build_record(
                    media,
                    digest=digest,
                    profile=brand["profile"],
                    brand=brand,
                    advertiser=str(ad.get("brand") or ""),
                    match_type=match_type,
                    ad=ad,
                    quality=quality,
                )
                keep_higher_priority(records, digest, incoming)
    return list(records.values())


def build_record(
    media: dict[str, Any],
    *,
    digest: str,
    profile: str,
    brand: dict[str, Any],
    advertiser: str,
    match_type: str,
    ad: dict[str, Any],
    quality: str,
) -> dict[str, Any]:
    return {
        **media,
        "sha256": digest,
        "registryQuality": quality,
        "profile": profile,
        "brandId": brand.get("id", ""),
        "brandName": brand.get("name") or advertiser,
        "advertiser": advertiser,
        "roles": brand.get("roles", []),
        "libraryId": ad.get("libraryId", ""),
        "sourceUrl": ad.get("adLibraryUrl", ""),
        "copy": ad.get("copy", ""),
        "advertiserMatchType": match_type,
    }


def keep_higher_priority(records: dict[str, dict[str, Any]], digest: str, incoming: dict[str, Any]) -> None:
    previous = records.get(digest)
    if previous is None or record_priority(incoming) > record_priority(previous):
        records[digest] = incoming


def match_registry_brand(advertiser: str, brands: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    partner: dict[str, Any] | None = None
    for brand in brands:
        match_type = advertiser_match_type(advertiser, brand)
        if match_type == "direct":
            return brand, "direct"
        if match_type == "partner":
            partner = partner or brand
    return (partner, "partner") if partner else (None, "")


def review_media_quality(media: dict[str, Any], source: Path) -> str:
    if not source.exists() or not source.is_file():
        return ""
    width = int(media.get("width") or 0)
    height = int(media.get("height") or 0)
    if min(width, height) < 300 or max(width, height) < 500:
        return ""
    ratio = width / height if height else 0
    if not 0.45 <= ratio <= 2.2:
        return ""
    try:
        if source.stat().st_size < 10_000:
            return ""
    except OSError:
        return ""
    return "standard" if min(width, height) >= 500 and max(width, height) >= 600 else "review_low_resolution"


def record_priority(record: dict[str, Any]) -> tuple[int, int, int]:
    return (
        1 if record.get("advertiserMatchType") == "direct" else 0,
        1 if record.get("registryQuality") == "standard" else 0,
        int(record.get("width") or 0) * int(record.get("height") or 0),
    )


def balanced_records(
    records: list[dict[str, Any]],
    limit: int,
    *,
    max_per_brand: int,
    max_per_ad: int,
    partner_limit: int,
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        buckets[(record.get("profile", ""), record.get("brandId", ""))].append(record)
    for bucket in buckets.values():
        bucket.sort(key=record_priority, reverse=True)

    chosen = []
    brand_counts: Counter[str] = Counter()
    ad_counts: Counter[str] = Counter()
    partner_count = 0
    keys = sorted(buckets)
    while keys and len(chosen) < limit:
        remaining = []
        for key in keys:
            while buckets[key] and len(chosen) < limit:
                candidate = buckets[key].pop(0)
                brand_id = str(candidate.get("brandId") or "")
                ad_id = str(candidate.get("libraryId") or candidate.get("sha256") or "")
                is_partner = candidate.get("advertiserMatchType") == "partner"
                if brand_counts[brand_id] >= max_per_brand or ad_counts[ad_id] >= max_per_ad:
                    continue
                if is_partner and partner_count >= partner_limit:
                    continue
                chosen.append(candidate)
                brand_counts[brand_id] += 1
                ad_counts[ad_id] += 1
                partner_count += int(is_partner)
                break
            if buckets[key]:
                remaining.append(key)
        keys = remaining
    return chosen


def build_item(record: dict[str, Any], target: Path, index: int) -> dict[str, Any]:
    quality = record.get("registryQuality", "standard")
    match_type = record.get("advertiserMatchType", "")
    roles = record.get("roles", [])
    risks = ["review_low_resolution"] if quality != "standard" else []
    if match_type == "partner":
        risks.append("partner_advertiser")
    reason = (
        "공식 브랜드 광고주와 기본 이미지 품질 기준을 통과했습니다. 브리프 적합성은 사람 검수가 필요합니다."
        if match_type == "direct"
        else "브랜드 협업 광고로 확인되었습니다. 공식 광고와 분리해 활용 가치를 검수해야 합니다."
    )
    confidence = 0.84 if match_type == "direct" and quality == "standard" else 0.68
    return {
        "id": f"meta_brand_ref_{index:03d}",
        "file": relative(target),
        "sourcePath": str(record.get("savedPath", "")).replace("\\", "/"),
        "sourceUrl": record.get("sourceUrl", ""),
        "sourceType": "meta_ad_library",
        "sourceIsPinterest": False,
        "sourceIsMeta": True,
        "sourceSplit": "meta_brand_registry",
        "category": record.get("profile", ""),
        "brandId": record.get("brandId", ""),
        "brandName": record.get("brandName", ""),
        "advertiser": record.get("advertiser", ""),
        "advertiserMatchType": match_type,
        "adLibraryId": record.get("libraryId", ""),
        "decision": "shortlist",
        "confidence": confidence,
        "reason": reason,
        "referenceRole": roles or ["brand_campaign"],
        "usableElements": ["브랜드 광고 레퍼런스", *roles],
        "riskSignals": risks,
        "registryQuality": quality,
        "wikiSources": WIKI_SOURCES,
        "seniorDesignerFeedback": "광고주 유형과 이미지 상태를 확인했습니다. 현재 브리프에 필요한 역할인지 판단합니다.",
        "kiwonReview": {
            "agree": "",
            "disagree": "",
            "unsure": "",
            "correctDecision": "",
            "kiwonReason": "",
            "ruleToUpdate": "",
        },
    }


def summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(items),
        "decisionCounts": {"shortlist": len(items)},
        "sourceCounts": {"meta_ad_library": len(items)},
        "profileCounts": dict(Counter(item["category"] for item in items)),
        "brandCounts": dict(Counter(item["brandName"] for item in items)),
        "qualityCounts": dict(Counter(item["registryQuality"] for item in items)),
        "advertiserMatchCounts": dict(Counter(item["advertiserMatchType"] for item in items)),
        "riskCounts": dict(Counter(risk for item in items for risk in item["riskSignals"])),
        "needsKiwonReview": len(items),
    }


def render_readme(report: dict[str, Any]) -> str:
    return "\n".join([
        "# Meta Brand Review",
        "",
        "광고주 유형을 검증하고 브랜드별 편중과 한 광고의 캐러셀 편중을 제한한 Meta 광고 이미지 검수 세션입니다.",
        "",
        f"- Total: {report['summary']['total']}",
        f"- Profiles: {report['summary']['profileCounts']}",
        f"- Brands: {report['summary']['brandCounts']}",
        f"- Quality: {report['summary']['qualityCounts']}",
        f"- Advertiser matches: {report['summary']['advertiserMatchCounts']}",
        f"- Selection policy: {report['selectionPolicy']}",
        "",
    ])


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


if __name__ == "__main__":
    raise SystemExit(main())
