"""Use reviewed Meta brand images as brief-aware reference candidates."""

from __future__ import annotations

import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json
from services.ad_reference.meta_creative_classifier import EXCLUDED_CREATIVE_TYPES


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SESSION = (
    ROOT
    / "design_brain_wiki"
    / "training_sessions"
    / "meta_brand_review"
    / "meta_brand_review_001"
    / "ai_judgement.json"
)
DEFAULT_CHARACTER_AUDIT = DEFAULT_SESSION.with_name("manual_meta_character_audit.json")
DEFAULT_EXCLUDED_CREATIVE_TYPES = EXCLUDED_CREATIVE_TYPES

CATEGORY_TERMS = {
    "cosmetics_skincare": (
        "cosmetic", "skincare", "beauty", "serum", "ampoule", "skin", "화장품", "스킨케어",
        "뷰티", "세럼", "앰플", "피부", "미백", "나이아신아마이드",
    ),
    "jewelry_luxury": (
        "jewelry", "jewellery", "diamond", "ring", "necklace", "luxury", "주얼리", "쥬얼리",
        "다이아", "반지", "목걸이", "럭셔리",
    ),
}

ROLE_ALIASES = {
    "campaign": ("campaign", "event", "이벤트", "캠페인"),
    "promotion": ("promotion", "sale", "discount", "gift", "프로모션", "세일", "할인", "증정", "혜택"),
    "product": ("product", "제품", "상품"),
    "ingredient": ("ingredient", "성분", "나이아신아마이드", "pdrn", "세럼", "앰플"),
    "clean": ("clean", "minimal", "클린", "미니멀", "화이트"),
    "premium": ("premium", "luxury", "프리미엄", "고급", "럭셔리"),
    "performance": ("performance", "benefit", "conversion", "효능", "기능성", "구매", "전환"),
    "derma": ("derma", "clinical", "science", "더마", "기능성", "과학"),
    "global": ("global", "글로벌"),
}


def add_meta_brand_references(
    run_dir: Path,
    manifest: dict[str, Any],
    brief: dict[str, Any],
    content_plan: dict[str, Any],
    *,
    limit: int = 8,
    session_path: Path = DEFAULT_SESSION,
    character_audit_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Select brief-fit Meta references, copy them into the run, and merge the manifest."""
    context = build_brief_context(brief, content_plan)
    session = read_json(session_path, default={})
    audit_path = character_audit_path or session_path.with_name(DEFAULT_CHARACTER_AUDIT.name)
    creative_types = load_creative_types(audit_path)
    excluded_counts = Counter(
        value for value in creative_types.values() if value in DEFAULT_EXCLUDED_CREATIVE_TYPES
    )
    ranked = rank_candidates(session.get("items", []), context, creative_types=creative_types)
    selected = select_candidates(ranked, limit=limit)

    assets = list(manifest.get("assets", [])) if isinstance(manifest, dict) else []
    existing_keys: set[str] = set()
    for asset in assets:
        if isinstance(asset, dict):
            existing_keys.update(_identity_keys(asset))
    selected_dir = run_dir / "references" / "selected"
    selected_dir.mkdir(parents=True, exist_ok=True)
    imported: list[dict[str, Any]] = []
    for candidate in selected:
        source = _resolve_source_path(candidate["item"], session_path)
        if not source.is_file():
            candidate["importStatus"] = "missing_source"
            continue
        candidate_keys = _identity_keys(candidate["item"], source)
        if candidate_keys & existing_keys:
            candidate["importStatus"] = "already_present"
            continue
        destination = selected_dir / f"meta_brand_{candidate['item']['id']}{source.suffix.lower()}"
        shutil.copy2(source, destination)
        asset = _manifest_asset(candidate, run_dir, destination)
        assets.append(asset)
        imported.append(asset)
        existing_keys.update(candidate_keys)
        existing_keys.update(_identity_keys(asset, destination))
        candidate["importStatus"] = "imported"

    merged = dict(manifest or {})
    merged["assets"] = assets
    merged["asset_count"] = len(assets)
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    sources = dict(merged.get("sources", {}))
    sources["meta_brand_review"] = {
        "source_id": "meta_brand_review",
        "provider": "meta_brand_review",
        "status": "selected" if imported else "no_new_assets",
        "session_path": _relative_to_root(session_path),
        "candidate_count": len(ranked),
        "selected_count": len(selected),
        "imported_count": len(imported),
    }
    merged["sources"] = sources
    evidence = build_evidence(
        session_path,
        context,
        ranked,
        selected,
        imported,
        audit_path=audit_path,
        excluded_counts=excluded_counts,
    )
    return merged, evidence


def build_brief_context(brief: dict[str, Any], content_plan: dict[str, Any]) -> dict[str, Any]:
    text = _flatten_text({"brief": brief, "contentPlan": content_plan}).casefold()
    categories = [
        category for category, terms in CATEGORY_TERMS.items()
        if any(term.casefold() in text for term in terms)
    ]
    roles = [
        role for role, terms in ROLE_ALIASES.items()
        if any(term.casefold() in text for term in terms)
    ]
    brand = str((brief.get("brand") or {}).get("name") or brief.get("brand_name") or "").strip()
    return {
        "brand": brand,
        "categories": categories,
        "roles": roles,
        "eventName": brief.get("event_name") or content_plan.get("event_name") or "",
    }


def rank_candidates(
    items: list[dict[str, Any]],
    context: dict[str, Any],
    *,
    creative_types: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    creative_types = creative_types or {}
    ranked = [
        _score_candidate(item, context, creative_types.get(Path(str(item.get("file") or "")).name, ""))
        for item in items
        if isinstance(item, dict)
    ]
    ranked = [
        candidate
        for candidate in ranked
        if candidate["categoryScore"] > 0
        and candidate["creativeType"] not in DEFAULT_EXCLUDED_CREATIVE_TYPES
    ]
    return sorted(
        ranked,
        key=lambda candidate: (
            candidate["advertiserMatchType"] == "direct",
            candidate["score"],
            candidate["roleScore"],
        ),
        reverse=True,
    )


def select_candidates(
    ranked: list[dict[str, Any]],
    *,
    limit: int,
    max_per_brand: int = 2,
    max_per_ad: int = 2,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    brand_counts: Counter[str] = Counter()
    ad_counts: Counter[str] = Counter()
    for candidate in ranked:
        brand = str(candidate["item"].get("brandId") or candidate["item"].get("brandName") or "")
        ad_id = str(candidate["item"].get("adLibraryId") or candidate["item"].get("id") or "")
        if brand_counts[brand] >= max_per_brand or ad_counts[ad_id] >= max_per_ad:
            continue
        selected.append(candidate)
        brand_counts[brand] += 1
        ad_counts[ad_id] += 1
        if len(selected) >= max(0, limit):
            break
    return selected


def build_evidence(
    session_path: Path,
    context: dict[str, Any],
    ranked: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    imported: list[dict[str, Any]],
    *,
    audit_path: Path,
    excluded_counts: Counter[str],
) -> dict[str, Any]:
    selected_ids = {candidate["item"].get("id") for candidate in selected}
    return {
        "stage": "03_reference_research",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "providers": {
            "pinterest": {"status": "preserved_in_reference_manifest"},
            "meta_brand_review": {
                "status": "used" if selected else "no_matching_candidates",
                "sessionPath": _relative_to_root(session_path),
                "selectionPolicy": {
                    "matchBasis": ["event brief industry", "brand", "reference role"],
                    "directAdvertiserPriority": True,
                    "partnerPenalty": 10,
                    "reviewQualityPenalty": 12,
                    "excludedCreativeTypes": sorted(DEFAULT_EXCLUDED_CREATIVE_TYPES),
                },
                "characterAuditPath": _relative_to_root(audit_path),
                "excludedByCreativeType": dict(excluded_counts),
                "context": context,
                "candidateCount": len(ranked),
                "selectedCount": len(selected),
                "importedCount": len(imported),
                "selected": [_evidence_candidate(candidate) for candidate in selected],
                "candidates": [
                    {**_evidence_candidate(candidate), "selected": candidate["item"].get("id") in selected_ids}
                    for candidate in ranked
                ],
            },
        },
    }


def _score_candidate(item: dict[str, Any], context: dict[str, Any], creative_type: str = "") -> dict[str, Any]:
    creative_type = creative_type or str(item.get("creativeType") or "")
    category_score = 45 if item.get("category") in context.get("categories", []) else 0
    brand = str(context.get("brand") or "").casefold()
    brand_name = str(item.get("brandName") or "").casefold()
    brand_score = 25 if brand and brand_name and (brand in brand_name or brand_name in brand) else 0
    matched_roles = sorted(set(context.get("roles", [])) & set(item.get("referenceRole", [])))
    role_score = min(24, len(matched_roles) * 6)
    advertiser_type = str(item.get("advertiserMatchType") or "")
    advertiser_adjustment = 12 if advertiser_type == "direct" else -10 if advertiser_type == "partner" else -15
    quality_adjustment = -12 if item.get("registryQuality") == "review" else 4
    score = category_score + brand_score + role_score + advertiser_adjustment + quality_adjustment
    return {
        "item": item,
        "score": score,
        "categoryScore": category_score,
        "brandScore": brand_score,
        "roleScore": role_score,
        "matchedRoles": matched_roles,
        "advertiserMatchType": advertiser_type,
        "advertiserAdjustment": advertiser_adjustment,
        "qualityAdjustment": quality_adjustment,
        "creativeType": creative_type,
    }


def _manifest_asset(candidate: dict[str, Any], run_dir: Path, destination: Path) -> dict[str, Any]:
    item = candidate["item"]
    return {
        "asset_id": item.get("id"),
        "source": "meta_brand_review",
        "source_id": "meta_brand_review",
        "source_url": item.get("sourceUrl", ""),
        "original_path": item.get("sourcePath", ""),
        "path": str(destination),
        "relative_path": str(destination.relative_to(run_dir)),
        "status": "selected",
        "review_decision": "selected",
        "score": candidate["score"],
        "brand": item.get("brandName", ""),
        "advertiser": item.get("advertiser", ""),
        "advertiser_match_type": item.get("advertiserMatchType", ""),
        "registry_quality": item.get("registryQuality", ""),
        "ad_library_id": item.get("adLibraryId", ""),
        "role": item.get("referenceRole", []),
        "reason": "Selected from Meta brand review by brief industry, brand, and role fit.",
        "provider_evidence": _evidence_candidate(candidate),
    }


def _evidence_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    item = candidate["item"]
    return {
        "id": item.get("id", ""),
        "brandName": item.get("brandName", ""),
        "category": item.get("category", ""),
        "referenceRole": item.get("referenceRole", []),
        "matchedRoles": candidate["matchedRoles"],
        "advertiserMatchType": candidate["advertiserMatchType"],
        "registryQuality": item.get("registryQuality", ""),
        "creativeType": candidate.get("creativeType", ""),
        "score": candidate["score"],
        "scoreBreakdown": {
            "category": candidate["categoryScore"],
            "brand": candidate["brandScore"],
            "role": candidate["roleScore"],
            "advertiser": candidate["advertiserAdjustment"],
            "quality": candidate["qualityAdjustment"],
        },
        "importStatus": candidate.get("importStatus", "not_imported"),
        "sourcePath": item.get("sourcePath", ""),
    }


def load_creative_types(path: Path) -> dict[str, str]:
    audit = read_json(path, default={})
    creative_types: dict[str, str] = {}
    for creative_type, filenames in audit.get("classifications", {}).items():
        if isinstance(filenames, list):
            creative_types.update({Path(str(filename)).name: str(creative_type) for filename in filenames})
    return creative_types


def _resolve_source_path(item: dict[str, Any], session_path: Path) -> Path:
    source_path = Path(str(item.get("sourcePath") or ""))
    if source_path.is_file():
        return source_path
    file_path = Path(str(item.get("file") or ""))
    if file_path.is_absolute():
        return file_path
    root_candidate = ROOT / file_path
    if root_candidate.is_file():
        return root_candidate
    return session_path.parent / file_path.name


def _identity_keys(record: dict[str, Any], *extra_paths: Path) -> set[str]:
    keys = {
        str(record.get(field) or "").strip()
        for field in ("sha256", "original_path", "path", "sourcePath", "file")
    }
    keys.update(str(path).strip() for path in extra_paths)
    for field in ("original_path", "path", "sourcePath", "file"):
        value = str(record.get(field) or "").strip()
        if value:
            keys.add(str(Path(value).resolve()))
    keys.update(str(path.resolve()) for path in extra_paths)
    return {key for key in keys if key}


def _relative_to_root(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)
