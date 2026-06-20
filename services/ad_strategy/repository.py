"""Reviewed advertising strategy examples and correction records."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json, write_json


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_PATH = ROOT / "design_brain_wiki" / "ad_strategy" / "reviewed-strategy-examples.json"
CORRECTIONS_PATH = ROOT / "design_brain_wiki" / "ad_strategy" / "copy-corrections.json"
LEGACY_PATH = ROOT / "design_brain_wiki" / "ad_strategy" / "meta-ad-strategy-library.json"

REASON_TAGS = {
    "generic", "weak_insight", "awkward_korean", "brand_mismatch",
    "unsupported_claim", "copied_expression", "weak_cta", "channel_mismatch",
    "good_hook", "good_structure", "strong_product_link",
}
RUBRIC_KEYS = {
    "strategyClarity", "targetEmpathy", "productConnection", "distinctiveness",
    "channelFit", "koreanCopyQuality", "brandFit", "actionability",
}
EDITABLE_STRATEGY_FIELDS = {
    "targetInsight", "hookMechanism", "persuasionSequence", "offerMechanism",
    "proofMechanism", "ctaType", "toneTraits", "channelFit",
}


def load_examples() -> list[dict[str, Any]]:
    payload = read_json(EXAMPLES_PATH, default={"examples": []})
    return [item for item in payload.get("examples", []) if isinstance(item, dict)]


def load_examples_for_review() -> list[dict[str, Any]]:
    source_cache: dict[Path, dict[str, Any]] = {}
    enriched = []
    for item in load_examples():
        source_ref = item.get("sourceRef", {})
        source_file = _safe_source_path(source_ref.get("sourceFile"))
        original = {}
        if source_file:
            payload = source_cache.setdefault(source_file, read_json(source_file, default={}))
            library_id = str(source_ref.get("libraryId") or "")
            source_item = next(
                (candidate for candidate in payload.get("items", []) if str(candidate.get("libraryId") or "") == library_id),
                {},
            )
            original = {
                "brand": source_item.get("brand", ""),
                "copy": source_item.get("copy", ""),
                "cta": source_item.get("cta", ""),
                "adLibraryUrl": source_item.get("adLibraryUrl", ""),
                "landingUrl": source_item.get("landingUrl", ""),
            }
        enriched.append({**item, "sourceOriginal": original})
    return enriched


def save_examples(examples: list[dict[str, Any]]) -> None:
    write_json(EXAMPLES_PATH, {
        "schemaVersion": "1.0.0",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "examples": examples,
    })


def import_legacy_as_unreviewed() -> int:
    existing = load_examples()
    existing_ids = {item.get("id") for item in existing}
    legacy = read_json(LEGACY_PATH, default={})
    added = 0
    for record in legacy.get("records", []):
        item = legacy_to_example(record)
        if item["id"] in existing_ids:
            continue
        existing.append(item)
        existing_ids.add(item["id"])
        added += 1
    if added:
        save_examples(existing)
    return added


def legacy_to_example(record: dict[str, Any]) -> dict[str, Any]:
    strategy = record.get("strategy", {})
    profile = record.get("profile")
    industry = profile if profile in {"cosmetics_skincare", "jewelry_luxury"} else "cosmetics_skincare"
    return {
        "id": record.get("patternId") or f"legacy-{record.get('source', {}).get('copyHash', '')[:12]}",
        "industry": industry,
        "sourceType": "meta_ad",
        "sourceRef": record.get("source", {}),
        "eventType": "promotion" if strategy.get("offerMechanics") else "branding",
        "funnelStage": "conversion" if strategy.get("offerMechanics") else "awareness",
        "targetInsight": "",
        "hookMechanism": strategy.get("hookType", "brand_statement"),
        "persuasionSequence": strategy.get("persuasionSequence", []),
        "offerMechanism": ", ".join(strategy.get("offerMechanics", [])),
        "proofMechanism": "",
        "ctaType": strategy.get("ctaType", "soft_action"),
        "toneTraits": strategy.get("toneTraits", []),
        "channelFit": [],
        "review": {"decision": "unreviewed", "scores": {}, "reasonTags": [], "reviewNote": "Legacy pattern; human review required."},
    }


def retrieve_selected(*, industry: str, event_type: str, channels: list[str], limit: int = 6) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in load_examples():
        review = item.get("review", {})
        if review.get("decision") != "selected" or item.get("industry") != industry:
            continue
        score = 5
        score += 3 if item.get("eventType") == event_type else 0
        score += len(set(channels) & set(item.get("channelFit", [])))
        scores = [value for value in review.get("scores", {}).values() if isinstance(value, (int, float))]
        score += int(sum(scores) / len(scores)) if scores else 0
        scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("id"))))
    return [item for _, item in scored[:limit]]


def retrieve_examples(brief: dict[str, Any], *, decision: str, limit: int = 6) -> list[dict[str, Any]]:
    industry = "jewelry_luxury" if any(token in str(brief).lower() for token in ("주얼리", "jewelry", "반지", "목걸이")) else "cosmetics_skincare"
    event_type = "promotion" if brief.get("offer", {}).get("summary") else "branding"
    channels = brief.get("channels", [])
    ranked = retrieve_selected(industry=industry, event_type=event_type, channels=channels, limit=limit) if decision == "selected" else [
        item for item in load_examples()
        if item.get("industry") == industry and item.get("review", {}).get("decision") == decision
    ][:limit]
    return ranked


def update_example_review(example_id: str, review: dict[str, Any]) -> dict[str, Any]:
    examples = load_examples()
    item = next((example for example in examples if example.get("id") == example_id), None)
    if not item:
        raise ValueError(f"Unknown strategy example: {example_id}")
    decision = str(review.get("decision") or "").strip()
    if decision not in {"selected", "shortlist", "rejected", "unreviewed"}:
        raise ValueError("Invalid strategy review decision.")
    scores = {
        key: max(1, min(5, int(value)))
        for key, value in (review.get("scores") or {}).items()
        if isinstance(value, (int, float))
    }
    if decision != "unreviewed" and set(scores) != RUBRIC_KEYS:
        raise ValueError("All eight strategy rubric scores are required.")
    strategy_updates = review.get("strategy") or {}
    for field in EDITABLE_STRATEGY_FIELDS:
        if field not in strategy_updates:
            continue
        value = strategy_updates[field]
        if field in {"persuasionSequence", "toneTraits", "channelFit"}:
            item[field] = [str(entry).strip() for entry in value if str(entry).strip()] if isinstance(value, list) else []
        else:
            item[field] = str(value or "").strip()
    if decision == "selected":
        missing_strategy = [field for field in ("targetInsight", "hookMechanism", "persuasionSequence", "ctaType") if not item.get(field)]
        if missing_strategy:
            raise ValueError(f"Selected strategy is incomplete: {', '.join(missing_strategy)}")
        if sum(scores.values()) / len(scores) < 4:
            raise ValueError("Selected strategy requires an average rubric score of at least 4.")
    item["review"] = {
        "decision": decision,
        "scores": scores,
        "reasonTags": [tag for tag in dict.fromkeys(review.get("reasonTags", [])) if tag in REASON_TAGS],
        "reviewNote": str(review.get("reviewNote") or ""),
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
    }
    save_examples(examples)
    return item


def load_corrections() -> list[dict[str, Any]]:
    return read_json(CORRECTIONS_PATH, default={"records": []}).get("records", [])


def retrieve_corrections(*, industry: str, brand_name: str = "", approved_only: bool = True, limit: int = 6) -> list[dict[str, Any]]:
    normalized_brand = brand_name.strip().lower()
    records = [
        item for item in load_corrections()
        if item.get("industry") == industry
        and (not approved_only or item.get("approved") is True)
        and (
            not normalized_brand
            or not str(item.get("brandName") or "").strip()
            or str(item.get("brandName") or "").strip().lower() == normalized_brand
        )
    ]
    records.sort(key=lambda item: (
        str(item.get("brandName") or "").strip().lower() == normalized_brand,
        str(item.get("createdAt") or ""),
    ))
    return records[-limit:]


def strategy_quality_metrics() -> dict[str, Any]:
    examples = load_examples()
    corrections = load_corrections()
    decisions = {decision: sum(item.get("review", {}).get("decision") == decision for item in examples) for decision in ("selected", "shortlist", "rejected", "unreviewed")}
    reviewed = len(examples) - decisions["unreviewed"]
    approved = [item for item in corrections if item.get("approved") is True]
    unedited = [item for item in approved if item.get("originalCopy") == item.get("editedCopy")]
    scores = [
        value for item in examples for value in item.get("review", {}).get("scores", {}).values()
        if isinstance(value, (int, float))
    ]
    return {
        "examples": len(examples),
        "reviewed": reviewed,
        "reviewProgress": round(reviewed / len(examples), 3) if examples else 0,
        "decisions": decisions,
        "corrections": len(corrections),
        "approvedCorrections": len(approved),
        "averageHumanScore": round(sum(scores) / len(scores), 2) if scores else 0,
        "unchangedApprovalRate": round(len(unedited) / len(approved), 3) if approved else 0,
        "benchmark": read_json(ROOT / ".tmp" / "model-benchmarks" / "cosmetics-planning-benchmark.json", default={}).get("summary", {}),
        "goalAudit": read_json(ROOT / ".tmp" / "model-benchmarks" / "ad-planning-goal-audit.json", default={}),
    }


def append_correction(record: dict[str, Any]) -> dict[str, Any]:
    _validate_correction(record)
    payload = read_json(CORRECTIONS_PATH, default={"records": []})
    records = payload.setdefault("records", [])
    created = datetime.now(timezone.utc).isoformat()
    normalized = {
        **record,
        "id": record.get("id") or hashlib.sha256(f"{record.get('runId')}|{record.get('channelId')}|{created}".encode()).hexdigest()[:16],
        "eventId": str(record.get("eventId") or ""),
        "eventName": str(record.get("eventName") or ""),
        "brandName": str(record.get("brandName") or ""),
        "reasonTags": [tag for tag in dict.fromkeys(record.get("reasonTags", [])) if tag in REASON_TAGS],
        "originalCopy": record.get("originalCopy", {}),
        "editedCopy": record.get("editedCopy", {}),
        "model": record.get("model", ""),
        "approved": bool(record.get("approved")),
        "createdAt": created,
    }
    records.append(normalized)
    payload["schemaVersion"] = "1.0.0"
    payload["updatedAt"] = created
    write_json(CORRECTIONS_PATH, payload)
    return normalized


def _safe_source_path(value: Any) -> Path | None:
    if not value:
        return None
    candidate = (ROOT / str(value)).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _validate_correction(record: dict[str, Any]) -> None:
    required_text = ("runId", "eventId", "eventName", "brandName", "industry", "channelId", "model")
    missing = [field for field in required_text if not str(record.get(field) or "").strip()]
    required_values = ("originalCopy", "editedCopy", "reasonTags", "qaResult", "strategyExampleIds", "approved")
    missing.extend(field for field in required_values if field not in record)
    if missing:
        raise ValueError(f"Incomplete copy correction record: {', '.join(missing)}")
    if record.get("industry") not in {"cosmetics_skincare", "jewelry_luxury"}:
        raise ValueError("Invalid correction industry.")
    if not isinstance(record.get("originalCopy"), dict) or not isinstance(record.get("editedCopy"), dict):
        raise ValueError("Correction originalCopy and editedCopy must be objects.")
