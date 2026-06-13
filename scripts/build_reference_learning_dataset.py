#!/usr/bin/env python3
"""Build the deduplicated 1,000-image reference learning dataset index."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "design_brain_wiki" / "reference_learning_1000"
TRAINING_ROOT = ROOT / "design_brain_wiki" / "training_sessions"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SOURCE_ROOTS = [
    ROOT / "runs",
    ROOT / "references" / "meta_ads",
    ROOT / "assets" / "reference_training",
    ROOT / "assets" / "references" / "inbox",
    ROOT / "0_자동화 샘플 이미지",
]
POLICY_PATH = ROOT / "assets" / "rules" / "reference-learning-brief.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--near-distance", type=int, default=4)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed = load_review_history()
    run_profiles = load_run_profiles()
    metadata = load_source_metadata()
    policy = read_json(POLICY_PATH, {})
    paths = discover_images()
    exact_groups = group_exact_duplicates(paths)
    records = [
        build_record(paths_for_hash, digest, reviewed, run_profiles, metadata, policy)
        for digest, paths_for_hash in exact_groups.items()
    ]
    records.sort(key=record_priority, reverse=True)
    attach_near_duplicates(records, max_distance=max(0, args.near_distance))
    batches = build_review_batches(records, max(1, args.batch_size), str(policy.get("batchPrefix") or "learning_batch"))
    summary = build_summary(records, batches, args.target, len(paths))
    payload = {
        "schemaVersion": 1,
        "createdAt": now(),
        "target": args.target,
        "policy": relative(POLICY_PATH),
        "summary": summary,
        "batches": batches,
        "items": records,
    }
    write_json(OUTPUT_DIR / "dataset-index.json", payload)
    write_json(OUTPUT_DIR / "summary.json", summary)
    write_json(OUTPUT_DIR / "review-batches.json", {"createdAt": now(), "batches": batches})
    (OUTPUT_DIR / "SUMMARY.md").write_text(render_summary(summary, batches), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def discover_images() -> list[Path]:
    paths: list[Path] = []
    for root in SOURCE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS and ".tmp" not in path.parts:
                paths.append(path.resolve())
    return sorted(set(paths))


def group_exact_duplicates(paths: list[Path]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        try:
            groups[hashlib.sha256(path.read_bytes()).hexdigest()].append(path)
        except OSError:
            continue
    return groups


def build_record(
    paths: list[Path],
    digest: str,
    reviewed: dict[str, dict[str, Any]],
    run_profiles: dict[str, str],
    metadata: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    primary = choose_primary_path(paths)
    width, height, dhash, image_error = image_info(primary)
    meta = metadata.get(digest, {})
    review = reviewed.get(digest, {})
    source_types = sorted({source_type(path) for path in paths})
    profiles = [infer_profile(path, run_profiles, meta) for path in paths]
    profile = Counter(profiles).most_common(1)[0][0] if profiles else "general"
    hard_reject_reasons = quality_reject_reasons(primary, width, height, image_error, profile, source_types, meta, policy)
    eligible = not hard_reject_reasons
    return {
        "id": f"ref_{digest[:12]}",
        "sha256": digest,
        "dhash": dhash,
        "path": relative(primary),
        "duplicatePaths": [relative(path) for path in paths if path != primary],
        "exactDuplicateCount": len(paths) - 1,
        "nearDuplicateOf": "",
        "sourceTypes": source_types,
        "source": preferred_source(source_types),
        "profile": profile,
        "width": width,
        "height": height,
        "aspectRatio": round(width / height, 4) if height else 0,
        "imageError": image_error,
        "sourceUrl": meta.get("sourceUrl", ""),
        "brand": meta.get("brand", ""),
        "query": meta.get("query", ""),
        "aiDecision": review.get("aiDecision") or meta.get("decision") or "",
        "finalDecision": review.get("finalDecision") or "",
        "reviewed": bool(review.get("reviewed")),
        "reasonTags": review.get("reasonTags", []),
        "lowResolution": "low_resolution" in hard_reject_reasons,
        "hardRejectReasons": hard_reject_reasons,
        "eligible": eligible,
        "referencePool": "rejection_example" if hard_reject_reasons else "creative_candidate",
    }


def quality_reject_reasons(
    path: Path,
    width: int,
    height: int,
    image_error: str,
    profile: str,
    source_types: list[str],
    meta: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    normalized = str(path).replace("\\", "/").lower()
    reasons = []
    name_text = normalized.replace("-", " ").replace("_", " ")
    if (
        ("/references/meta_ads/" in normalized and "/captures/" in normalized)
        or any(term in name_text for term in ("website screenshot", "browser screenshot", "homepage", "web page", "url bar"))
    ):
        reasons.append("website_capture")
    if any(term in name_text for term in (
        "hair dryer", "hair styling", "jewelry", "necklace", "earring", "gold bar",
        "bullion", "finance", "investment", "food menu", "restaurant", "fashion outfit",
    )):
        reasons.append("wrong_category")
    meta_text = f"{meta.get('brand', '')} {meta.get('copy', '')}".lower()
    if any(term in meta_text for term in ("dental", "dentist", "치과", "임플란트", "tattoo", "타투", "부동산", "보험")):
        reasons.append("wrong_category")
    if policy.get("excludeDenseCardNews") and any(term in name_text for term in ("카드뉴스", "infographic", "인포그래픽")):
        reasons.append("dense_card_news")
    if image_error or not width or not height:
        reasons.append("broken_image")
    minimum_short = int(policy.get("minimumShortSide") or 500)
    minimum_long = int(policy.get("minimumLongSide") or 600)
    if width and height and (min(width, height) < minimum_short or max(width, height) < minimum_long):
        reasons.append("low_resolution")
    aspect_range = policy.get("aspectRatioRange") or [0.55, 1.9]
    ratio = width / height if height else 0
    if ratio and not (float(aspect_range[0]) <= ratio <= float(aspect_range[1])):
        reasons.append("extreme_aspect_ratio")
    allowed_sources = set(policy.get("allowedSources") or [])
    if allowed_sources and not any(source in allowed_sources for source in source_types):
        reasons.append("disallowed_source")
    required_profile = str(policy.get("profile") or "")
    if required_profile and profile != required_profile:
        reasons.append("wrong_profile")
    if policy.get("excludeForeignMetaAds") and "meta_ad_library" in source_types and meta.get("foreignMarket"):
        reasons.append("foreign_market")
    return reasons


def choose_primary_path(paths: list[Path]) -> Path:
    priorities = {
        "meta_ad_library": 5,
        "pinterest_search": 4,
        "training_seed": 3,
        "sample_asset": 2,
        "other": 1,
    }
    return max(paths, key=lambda path: (priorities.get(source_type(path), 0), -len(str(path))))


def image_info(path: Path) -> tuple[int, int, str, str]:
    try:
        with Image.open(path) as image:
            image = image.convert("L")
            width, height = image.size
            resized = image.resize((9, 8))
            pixels = list(resized.getdata())
            bits = []
            for row in range(8):
                start = row * 9
                bits.extend(pixels[start + col] > pixels[start + col + 1] for col in range(8))
            value = sum((1 << index) for index, bit in enumerate(bits) if bit)
            return width, height, f"{value:016x}", ""
    except (OSError, UnidentifiedImageError) as exc:
        return 0, 0, "", f"{type(exc).__name__}: {exc}"


def attach_near_duplicates(records: list[dict[str, Any]], max_distance: int) -> None:
    representatives: list[dict[str, Any]] = []
    for record in records:
        if not record["dhash"]:
            continue
        match = next(
            (
                representative
                for representative in representatives
                if hamming(record["dhash"], representative["dhash"]) <= max_distance
                and similar_aspect(record, representative)
            ),
            None,
        )
        if match:
            record["nearDuplicateOf"] = match["id"]
        else:
            representatives.append(record)


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def similar_aspect(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_ratio = float(left.get("aspectRatio") or 0)
    right_ratio = float(right.get("aspectRatio") or 0)
    if not left_ratio or not right_ratio:
        return False
    return abs(left_ratio - right_ratio) / max(left_ratio, right_ratio) <= 0.08


def build_review_batches(records: list[dict[str, Any]], batch_size: int, batch_prefix: str) -> list[dict[str, Any]]:
    queue = [
        item for item in records
        if item.get("eligible") and not item["nearDuplicateOf"] and not item["imageError"]
    ]
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in queue:
        buckets[(item["profile"], item["source"])].append(item)
    for bucket in buckets.values():
        bucket.sort(key=lambda item: item["id"])
    queue = []
    keys = sorted(buckets)
    while keys:
        next_keys = []
        for key in keys:
            if buckets[key]:
                queue.append(buckets[key].pop(0))
            if buckets[key]:
                next_keys.append(key)
        keys = next_keys
    batches = []
    for start in range(0, len(queue), batch_size):
        items = queue[start:start + batch_size]
        batches.append({
            "id": f"{batch_prefix}_{len(batches) + 1:03d}",
            "status": "ready",
            "itemCount": len(items),
            "sourceCounts": dict(Counter(item["source"] for item in items)),
            "profileCounts": dict(Counter(item["profile"] for item in items)),
            "itemIds": [item["id"] for item in items],
        })
    return batches


def load_review_history() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not TRAINING_ROOT.exists():
        return result
    for judgement_path in TRAINING_ROOT.glob("*/*/ai_judgement.json"):
        judgement = read_json(judgement_path, {})
        review_state = read_json(judgement_path.parent / "kiwon_review_state.json", {})
        reviews = review_state.get("reviews", {}) if isinstance(review_state, dict) else {}
        for item in judgement.get("items", []):
            path = resolve_project_path(item.get("file") or item.get("sourcePath"))
            digest = file_hash(path)
            if not digest:
                continue
            review = reviews.get(item.get("id", ""), {})
            result[digest] = {
                "reviewed": bool(review.get("status")),
                "aiDecision": item.get("decision", ""),
                "finalDecision": review.get("correctDecision") or (item.get("decision", "") if review.get("status") else ""),
                "reasonTags": review.get("reasonTags", []) or [],
            }
    return result


def load_run_profiles() -> dict[str, str]:
    result = {}
    runs_dir = ROOT / "runs"
    if not runs_dir.exists():
        return result
    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue
        research = read_json(run_dir / "03_reference_research" / "reference-research.json", {})
        plan = read_json(run_dir / "references" / "reference-collection-plan.json", {})
        event_profile = research.get("eventProfile", {}) if isinstance(research, dict) else {}
        profile = event_profile.get("category") or plan.get("intent", {}).get("event_profile") or "general"
        result[run_dir.name] = profile
    return result


def load_source_metadata() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    searches = ROOT / "references" / "meta_ads" / "searches"
    if searches.exists():
        for payload_path in searches.glob("*/collected-ads.json"):
            payload = read_json(payload_path, {})
            for ad in payload.get("items", []):
                for media in ad.get("media", []):
                    digest = str(media.get("sha256") or "")
                    if digest:
                        incoming = {
                            "sourceUrl": ad.get("adLibraryUrl", ""),
                            "brand": ad.get("brand", ""),
                            "query": payload.get("query", ""),
                            "country": payload.get("country", ""),
                            "copy": ad.get("copy", ""),
                            "foreignMarket": is_foreign_market_ad(ad),
                            "decision": (media.get("qwenReview") or {}).get("decision", ""),
                        }
                        existing = result.get(digest, {})
                        result[digest] = {
                            **existing,
                            **{key: value for key, value in incoming.items() if value not in ("", None)},
                            "foreignMarket": bool(existing.get("foreignMarket") or incoming["foreignMarket"]),
                        }
    return result


def is_foreign_market_ad(ad: dict[str, Any]) -> bool:
    text = f"{ad.get('brand', '')} {ad.get('copy', '')}"
    meaningful = [char for char in text if char.isalpha()]
    if not meaningful:
        return False
    korean = sum("\uac00" <= char <= "\ud7a3" for char in meaningful)
    foreign_scripts = sum(
        ("\u0e00" <= char <= "\u0e7f")
        or ("\u0400" <= char <= "\u04ff")
        or ("\u0600" <= char <= "\u06ff")
        or ("\u4e00" <= char <= "\u9fff")
        for char in meaningful
    )
    return foreign_scripts >= 8 and foreign_scripts >= korean


def source_type(path: Path) -> str:
    normalized = str(path).replace("\\", "/").lower()
    if "/references/meta_ads/" in normalized or "meta_ad_" in path.name.lower():
        return "meta_ad_library"
    if "/assets/references/inbox/" in normalized:
        return "imported_learning_inbox"
    if (
        "pinterest" in normalized
        or "pinimg" in normalized
        or "/references/candidates/" in normalized
    ):
        return "pinterest_search"
    if "/assets/reference_training/" in normalized:
        return "training_seed"
    if "0_자동화 샘플 이미지" in str(path):
        return "sample_asset"
    return "other"


def preferred_source(sources: list[str]) -> str:
    for name in ("meta_ad_library", "pinterest_search", "imported_learning_inbox", "training_seed", "sample_asset", "other"):
        if name in sources:
            return name
    return "other"


def infer_profile(path: Path, run_profiles: dict[str, str], meta: dict[str, Any]) -> str:
    normalized = str(path).replace("\\", "/").lower()
    for profile in ("cosmetics_skincare", "bullion_investment", "jewelry_luxury"):
        if profile in normalized:
            return profile
    if "meta_ads" in normalized or "meta_ad_" in path.name.lower():
        return "cosmetics_skincare"
    if "/runs/" in normalized:
        parts = path.parts
        try:
            run_name = parts[parts.index("runs") + 1]
            return run_profiles.get(run_name, "general")
        except (ValueError, IndexError):
            pass
    text = f"{path.name} {meta.get('brand', '')} {meta.get('query', '')}".lower()
    if any(term in text for term in ("cosmetic", "skincare", "serum", "화장품", "스킨케어", "세럼")):
        return "cosmetics_skincare"
    if any(term in text for term in ("gold", "bullion", "coin", "금", "은화")):
        return "bullion_investment"
    return "general"


def record_priority(record: dict[str, Any]) -> tuple[int, int, int]:
    return (
        1 if record["reviewed"] else 0,
        1 if record["source"] in {"meta_ad_library", "pinterest_search"} else 0,
        int(record.get("width") or 0) * int(record.get("height") or 0),
    )


def build_summary(records: list[dict[str, Any]], batches: list[dict[str, Any]], target: int, discovered: int) -> dict[str, Any]:
    reviewable = [item for item in records if item.get("eligible") and not item["nearDuplicateOf"] and not item["imageError"]]
    excluded = [item for item in records if not item.get("eligible")]
    reviewed = [item for item in reviewable if item["reviewed"]]
    return {
        "target": target,
        "discoveredFiles": discovered,
        "exactUniqueImages": len(records),
        "exactDuplicatesRemoved": discovered - len(records),
        "nearDuplicatesFlagged": sum(bool(item["nearDuplicateOf"]) for item in records),
        "reviewableUniqueImages": len(reviewable),
        "excludedByBriefGate": len(excluded),
        "remainingToTarget": max(0, target - len(reviewable)),
        "reviewedImages": len(reviewed),
        "unreviewedImages": len(reviewable) - len(reviewed),
        "reviewProgress": round(len(reviewed) / len(reviewable), 4) if reviewable else 0,
        "sourceCounts": dict(Counter(item["source"] for item in reviewable)),
        "profileCounts": dict(Counter(item["profile"] for item in reviewable)),
        "poolCounts": dict(Counter(item.get("referencePool", "creative_candidate") for item in reviewable)),
        "hardRejectReasonCounts": dict(Counter(reason for item in excluded for reason in item.get("hardRejectReasons", []))),
        "decisionCounts": dict(Counter(item["finalDecision"] or item["aiDecision"] or "unjudged" for item in reviewable)),
        "batchCount": len(batches),
    }


def render_summary(summary: dict[str, Any], batches: list[dict[str, Any]]) -> str:
    lines = [
        "# Reference Learning 1000",
        "",
        f"- Target: {summary['target']}",
        f"- Discovered files: {summary['discoveredFiles']}",
        f"- Exact unique images: {summary['exactUniqueImages']}",
        f"- Exact duplicates removed: {summary['exactDuplicatesRemoved']}",
        f"- Near duplicates flagged: {summary['nearDuplicatesFlagged']}",
        f"- Reviewable unique images: {summary['reviewableUniqueImages']}",
        f"- Remaining to target: {summary['remainingToTarget']}",
        f"- Reviewed: {summary['reviewedImages']}",
        f"- Unreviewed: {summary['unreviewedImages']}",
        f"- Review batches: {summary['batchCount']}",
        "",
        "## Sources",
        *[f"- {key}: {value}" for key, value in summary["sourceCounts"].items()],
        "",
        "## Profiles",
        *[f"- {key}: {value}" for key, value in summary["profileCounts"].items()],
        "",
        "## Review Batches",
        *[f"- {batch['id']}: {batch['itemCount']} items / {batch['sourceCounts']}" for batch in batches],
        "",
    ]
    return "\n".join(lines)


def resolve_project_path(value: Any) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = ROOT / path
    return path if path.exists() and path.is_file() else None


def file_hash(path: Path | None) -> str:
    if not path:
        return ""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
