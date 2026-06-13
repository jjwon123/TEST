"""Good/bad reference seed dataset helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils.json_io import read_json


ROOT = Path(__file__).resolve().parents[2]
TRAINING_DIR = ROOT / "assets" / "reference_training"


def load_reference_training(profile: str) -> dict[str, Any]:
    base = TRAINING_DIR / profile
    good = _load_split(base / "good")
    bad = _load_split(base / "bad")
    return {
        "profile": profile,
        "path": str(base.relative_to(ROOT)) if base.exists() else str(base),
        "good": good,
        "bad": bad,
        "good_count": len(good.get("items", [])),
        "bad_count": len(bad.get("items", [])),
        "good_terms": _terms_from_items(good.get("items", [])),
        "bad_terms": _terms_from_items(bad.get("items", [])),
        "good_seed_coverage": _category_counts(good.get("items", [])),
        "good_useful_for_coverage": _useful_for_counts(good.get("items", [])),
    }


def score_record_against_training(record: dict[str, Any], profile: str) -> dict[str, Any]:
    training = load_reference_training(profile)
    text = _record_text(record).lower()
    good_hits = _hits(text, training["good_terms"])
    bad_hits = _hits(text, training["bad_terms"])
    matched_good_items = _matched_items(record, training["good"].get("items", []))
    good_score = min(10.0, len(good_hits) * 1.35)
    bad_score = min(10.0, len(bad_hits) * 1.75)
    return {
        "profile": profile,
        "goodScore": round(good_score, 2),
        "badScore": round(bad_score, 2),
        "scoreDelta": round(good_score - bad_score, 2),
        "goodHits": good_hits[:12],
        "badHits": bad_hits[:12],
        "goodSeedCount": training["good_count"],
        "badSeedCount": training["bad_count"],
        "matchedCategories": sorted({str(item.get("category", "")).strip() for item in matched_good_items if item.get("category")}),
        "matchedUsefulFor": sorted({
            str(value).strip()
            for item in matched_good_items
            for value in (item.get("usefulFor", []) if isinstance(item.get("usefulFor"), list) else [])
            if str(value).strip()
        }),
    }


def training_summary(profile: str) -> dict[str, Any]:
    training = load_reference_training(profile)
    return {
        "profile": profile,
        "path": training["path"],
        "good_count": training["good_count"],
        "bad_count": training["bad_count"],
        "goodSeedCoverage": training["good_seed_coverage"],
        "goodUsefulForCoverage": training["good_useful_for_coverage"],
        "good_terms": training["good_terms"][:40],
        "bad_terms": training["bad_terms"][:40],
    }


def _load_split(path: Path) -> dict[str, Any]:
    metadata = read_json(path / "metadata.json", default={})
    items = metadata.get("items")
    if not isinstance(items, list):
        files = metadata.get("files") if isinstance(metadata.get("files"), list) else []
        items = [
            {
                "filename": item.get("file", ""),
                "tags": metadata.get("tags", []),
                "whyGood": item.get("reason", ""),
                "usefulFor": [],
            }
            for item in files
            if isinstance(item, dict)
        ]
    image_files = [
        str(item.relative_to(path))
        for item in sorted(path.rglob("*"))
        if item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]
    return {
        "metadata_path": str((path / "metadata.json").relative_to(ROOT)) if (path / "metadata.json").exists() else "",
        "items": items if isinstance(items, list) else [],
        "image_files": image_files,
    }


def _terms_from_items(items: list[dict[str, Any]]) -> list[str]:
    terms: list[str] = []
    for item in items:
        filename = str(item.get("filename", ""))
        terms.extend(_tokens(filename.replace("_", " ").replace("-", " ")))
        tags = item.get("tags", [])
        if isinstance(tags, list):
            terms.extend(str(tag).strip().lower() for tag in tags if str(tag).strip())
        useful = item.get("usefulFor", [])
        if isinstance(useful, list):
            terms.extend(str(value).replace("_", " ").strip().lower() for value in useful if str(value).strip())
        terms.extend(_tokens(str(item.get("whyGood", ""))))
    return _dedupe([term for term in terms if len(term) >= 3])


def _matched_items(record: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = _record_text(record).lower().replace("\\", "/")
    matched: list[dict[str, Any]] = []
    for item in items:
        filename = str(item.get("filename", "")).lower().replace("\\", "/")
        basename = Path(filename).name
        category = str(item.get("category", "")).lower()
        if (filename and filename in text) or (basename and basename in text):
            matched.append(item)
            continue
        if category and category in text:
            matched.append(item)
    return matched


def _category_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        category = str(item.get("category", "")).strip() or "uncategorized"
        counts[category] = counts.get(category, 0) + 1
    return counts


def _useful_for_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        useful = item.get("usefulFor", [])
        if not isinstance(useful, list):
            continue
        for value in useful:
            key = str(value).strip()
            if key:
                counts[key] = counts.get(key, 0) + 1
    return counts


def _record_text(record: dict[str, Any]) -> str:
    review = record.get("qwen_review") or {}
    parts = [
        record.get("asset_id", ""),
        record.get("query", ""),
        record.get("source_id", ""),
        record.get("relative_path", ""),
        record.get("path", ""),
        record.get("text_relevance_reason", ""),
        record.get("reason", ""),
        " ".join(str(tag) for tag in record.get("positive_tags", []) or []),
        " ".join(str(tag) for tag in record.get("negative_tags", []) or []),
        review.get("reason", ""),
        review.get("risk", ""),
        " ".join(str(tag) for tag in review.get("positive_tags", []) or []),
        " ".join(str(tag) for tag in review.get("negative_tags", []) or []),
    ]
    return " ".join(str(part) for part in parts)


def _tokens(text: str) -> list[str]:
    raw = str(text or "").lower().replace(".", " ").replace(",", " ").split()
    stop = {
        "the", "and", "with", "from", "that", "this", "into", "only", "suitable",
        "jpg", "jpeg", "png", "webp", "reference", "visual", "no", "not",
        "playful", "character-driven", "style;", "for", "premium", "financial",
        "poster", "text", "object",
    }
    return [token.strip() for token in raw if token.strip() and token.strip() not in stop]


def _hits(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term in text]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.lower()
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result
