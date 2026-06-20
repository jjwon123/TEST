"""Promote repeated human-review rules and apply them to future reference judgements."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json, write_json


ROOT = Path(__file__).resolve().parents[2]
TRAINING_ROOT = ROOT / "design_brain_wiki" / "training_sessions"
PROMOTED_RULES_PATH = ROOT / "assets" / "rules" / "promoted-reference-rules.json"
EXCLUDED_PROFILES = {"reference_learning", "meta_brand_review"}
HARD_REJECT_TAGS = {"low_resolution", "website_capture", "fake_text_risk", "wrong_category"}
RISK_TAG_ALIASES = {
    "too_small": "low_resolution",
    "wrong_product_category": "wrong_category",
    "ai_artifact": "fake_text_risk",
}


def build_promoted_rules(
    *,
    training_root: Path = TRAINING_ROOT,
    min_session_occurrences: int = 2,
    min_reviewed: int = 20,
    min_completion_ratio: float = 0.8,
) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    considered_sessions = 0
    for path in training_root.glob("**/learned_rules.json"):
        payload = read_json(path, default={})
        profile = str(payload.get("profile") or "").strip()
        summary = payload.get("summary", {})
        reviewed = int(summary.get("reviewed", 0) or 0)
        total = int(summary.get("total", 0) or 0)
        completion_ratio = reviewed / total if total else 0.0
        if (
            not profile
            or profile in EXCLUDED_PROFILES
            or reviewed < min_reviewed
            or completion_ratio < min_completion_ratio
        ):
            continue
        considered_sessions += 1
        for rule in payload.get("rules", []):
            rule_id = str(rule.get("id") or "").strip()
            if rule_id:
                grouped[(profile, rule_id)].append({
                    "session": relative(path.parent),
                    "reviewed": reviewed,
                    "total": total,
                    "accuracy": summary.get("accuracy", 0),
                    "rule": rule,
                })

    promoted: list[dict[str, Any]] = []
    for (profile, rule_id), evidence in sorted(grouped.items()):
        if len(evidence) < min_session_occurrences:
            continue
        canonical = dict(evidence[-1]["rule"])
        promoted.append({
            **canonical,
            "id": rule_id,
            "profile": profile,
            "status": "promoted",
            "sessionOccurrences": len(evidence),
            "evidenceSessions": [item["session"] for item in evidence],
            "totalReviewed": sum(item["reviewed"] for item in evidence),
        })
    return {
        "schemaVersion": "1.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "excludedProfiles": sorted(EXCLUDED_PROFILES),
            "minSessionOccurrences": min_session_occurrences,
            "minReviewed": min_reviewed,
            "minCompletionRatio": min_completion_ratio,
        },
        "summary": {
            "consideredSessions": considered_sessions,
            "promotedRules": len(promoted),
        },
        "rules": promoted,
    }


def write_promoted_rules(path: Path = PROMOTED_RULES_PATH) -> dict[str, Any]:
    payload = build_promoted_rules()
    write_json(path, payload)
    return payload


def load_promoted_rules(profile: str, path: Path = PROMOTED_RULES_PATH) -> list[dict[str, Any]]:
    payload = read_json(path, default={"rules": []})
    return [
        rule for rule in payload.get("rules", [])
        if rule.get("status") == "promoted" and rule.get("profile") == profile
    ]


def apply_promoted_rules(
    profile: str,
    decision: str,
    reason_tags: list[str],
    *,
    path: Path = PROMOTED_RULES_PATH,
) -> tuple[str, list[str]]:
    normalized_tags = {RISK_TAG_ALIASES.get(tag, tag) for tag in reason_tags}
    applied: list[str] = []
    final = decision
    for rule in load_promoted_rules(profile, path):
        rule_id = str(rule.get("id") or "")
        when_any = set(rule.get("whenAnyReasonTag", []) or [])
        unless_any = set(rule.get("unlessAnyReasonTag", []) or [])
        if when_any and when_any & normalized_tags:
            final = str(rule.get("decision") or final)
            applied.append(rule_id)
        elif rule_id == "soften_rejected_to_shortlist" and final == "rejected" and not (unless_any & normalized_tags):
            final = str(rule.get("decision") or "shortlist")
            applied.append(rule_id)
    return final, applied


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)
