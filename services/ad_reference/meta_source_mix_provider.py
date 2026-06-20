"""Import Qwen-validated clean product visuals from Meta query collections."""

from __future__ import annotations

import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json
from services.ad_reference.source_mix_metrics import DEFAULT_SEARCH_ROOT, source_mix_summary


def add_meta_source_mix_references(
    run_dir: Path,
    manifest: dict[str, Any],
    context: dict[str, Any],
    *,
    limit: int = 6,
    search_root: Path = DEFAULT_SEARCH_ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Merge validated fallback product visuals into a cosmetics run."""
    if "cosmetics_skincare" not in context.get("categories", []):
        return manifest, _evidence("not_applicable", [], [], context)

    metrics = source_mix_summary(search_root)
    allowed_queries = {
        item["query"]: item
        for item in metrics.get("recommendedQueries", [])
        if item.get("queryType") == "product_or_ingredient"
    }
    ranked = _rank_candidates(search_root, allowed_queries)
    selected = _select_candidates(ranked, limit=limit)

    assets = list(manifest.get("assets", [])) if isinstance(manifest, dict) else []
    existing_keys = {key for asset in assets if isinstance(asset, dict) for key in _identity_keys(asset)}
    selected_dir = run_dir / "references" / "selected"
    selected_dir.mkdir(parents=True, exist_ok=True)
    imported: list[dict[str, Any]] = []
    for candidate in selected:
        source = candidate["sourcePath"]
        keys = _identity_keys(candidate["media"], source)
        if not source.is_file():
            candidate["importStatus"] = "missing_source"
            continue
        if keys & existing_keys:
            candidate["importStatus"] = "already_present"
            continue
        destination = selected_dir / f"meta_source_mix_{candidate['id']}{source.suffix.lower()}"
        shutil.copy2(source, destination)
        asset = _manifest_asset(candidate, run_dir, destination)
        assets.append(asset)
        imported.append(asset)
        existing_keys.update(keys)
        existing_keys.update(_identity_keys(asset, destination))
        candidate["importStatus"] = "imported"

    merged = dict(manifest or {})
    merged["assets"] = assets
    merged["asset_count"] = len(assets)
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    sources = dict(merged.get("sources", {}))
    sources["meta_source_mix"] = {
        "source_id": "meta_source_mix",
        "provider": "meta_source_mix",
        "status": "selected" if imported else "no_new_assets",
        "candidate_count": len(ranked),
        "selected_count": len(selected),
        "imported_count": len(imported),
        "validated_queries": sorted(allowed_queries),
    }
    merged["sources"] = sources
    return merged, _evidence("used" if selected else "no_matching_candidates", selected, imported, context)


def _rank_candidates(search_root: Path, allowed_queries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in search_root.glob("*/collected-ads.json") if search_root.exists() else []:
        payload = read_json(path, default={})
        query = str(payload.get("query") or "").strip()
        query_metrics = allowed_queries.get(query)
        if not query_metrics:
            continue
        for ad in payload.get("items", []):
            ad_id = str(ad.get("libraryId") or ad.get("id") or "")
            for media in ad.get("media", []):
                review = media.get("qwenReview")
                if not isinstance(review, dict):
                    continue
                if review.get("creative_type") != "clean_product_visual" or review.get("decision") == "rejected":
                    continue
                source = Path(str(media.get("savedPath") or review.get("file") or ""))
                candidate_id = str(review.get("candidate_id") or media.get("sha256") or source.stem)
                score = (
                    float(review.get("score") or 0)
                    + float(review.get("product_focus") or 0) * 0.25
                    + float(review.get("layout_usability") or 0) * 0.1
                    + float(query_metrics.get("cleanProductRate") or 0) * 20
                    + (8 if review.get("visible_cosmetic_container") else 0)
                    - float(review.get("text_density") or 0) * 0.1
                )
                candidates.append({
                    "id": candidate_id,
                    "query": query,
                    "queryMetrics": query_metrics,
                    "adId": ad_id,
                    "brand": ad.get("brand", ""),
                    "sourceUrl": ad.get("adLibraryUrl", ""),
                    "sourcePath": source,
                    "media": media,
                    "review": review,
                    "score": round(score, 2),
                    "importStatus": "not_imported",
                })
    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def _select_candidates(
    ranked: list[dict[str, Any]],
    *,
    limit: int,
    max_per_query: int = 2,
    max_per_ad: int = 1,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    query_counts: Counter[str] = Counter()
    ad_counts: Counter[str] = Counter()
    seen_sha: set[str] = set()
    for candidate in ranked:
        sha = str(candidate["media"].get("sha256") or "")
        if query_counts[candidate["query"]] >= max_per_query or ad_counts[candidate["adId"]] >= max_per_ad:
            continue
        if sha and sha in seen_sha:
            continue
        selected.append(candidate)
        query_counts[candidate["query"]] += 1
        ad_counts[candidate["adId"]] += 1
        if sha:
            seen_sha.add(sha)
        if len(selected) >= max(0, limit):
            break
    return selected


def _manifest_asset(candidate: dict[str, Any], run_dir: Path, destination: Path) -> dict[str, Any]:
    review = candidate["review"]
    media = candidate["media"]
    return {
        "asset_id": candidate["id"],
        "source": "meta_source_mix",
        "source_id": "meta_source_mix",
        "source_url": candidate["sourceUrl"],
        "original_path": str(candidate["sourcePath"]),
        "path": str(destination),
        "relative_path": str(destination.relative_to(run_dir)),
        "sha256": media.get("sha256", ""),
        "status": "selected",
        "review_decision": "selected",
        "score": candidate["score"],
        "query": candidate["query"],
        "brand": candidate["brand"],
        "ad_library_id": candidate["adId"],
        "role": ["product"],
        "reason": review.get("reason") or "Qwen-validated clean product visual from a proven fallback query.",
        "qwen_review": review,
        "provider_evidence": _candidate_evidence(candidate),
    }


def _evidence(
    status: str,
    selected: list[dict[str, Any]],
    imported: list[dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": status,
        "selectionPolicy": {
            "profile": "cosmetics_skincare_only",
            "queryEvidenceMinimum": "reviewedMedia >= 5 and cleanProductRate >= 0.2",
            "qwenCreativeType": "clean_product_visual",
            "humanFinalSelectionReplaced": False,
            "maxPerQuery": 2,
            "maxPerAd": 1,
        },
        "context": context,
        "selectedCount": len(selected),
        "importedCount": len(imported),
        "selected": [_candidate_evidence(candidate) for candidate in selected],
    }


def _candidate_evidence(candidate: dict[str, Any]) -> dict[str, Any]:
    review = candidate["review"]
    return {
        "id": candidate["id"],
        "query": candidate["query"],
        "adLibraryId": candidate["adId"],
        "brand": candidate["brand"],
        "score": candidate["score"],
        "queryCleanProductRate": candidate["queryMetrics"].get("cleanProductRate"),
        "qwenScore": review.get("score"),
        "productFocus": review.get("product_focus"),
        "visibleCosmeticContainer": review.get("visible_cosmetic_container"),
        "importStatus": candidate.get("importStatus", "not_imported"),
        "sourcePath": str(candidate["sourcePath"]),
    }


def _identity_keys(record: dict[str, Any], *paths: Path) -> set[str]:
    keys = {
        str(record.get(field) or "").strip()
        for field in ("sha256", "original_path", "path", "savedPath")
    }
    keys.update(str(path.resolve()) for path in paths)
    return {key for key in keys if key}
