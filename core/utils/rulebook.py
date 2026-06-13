"""Shared rulebook loader for brand/event/reference policy files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils.json_io import read_json


ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = ROOT / "assets" / "rules"


def load_rulebook() -> dict[str, Any]:
    return {
        "brand_persona": _load_profiles("brand-persona.json"),
        "event_rules": _load_profiles("event-rules.json"),
        "reference_rules": _load_profiles("reference-rules.json"),
        "visual_avoid_rules": _load_profiles("visual-avoid-rules.json"),
    }


def profile_rules(profile: str) -> dict[str, Any]:
    rulebook = load_rulebook()
    return {
        "profile": profile,
        "brand_persona": rulebook["brand_persona"].get(profile, {}),
        "event_rules": rulebook["event_rules"].get(profile, {}),
        "reference_rules": rulebook["reference_rules"].get(profile, {}),
        "visual_avoid_rules": rulebook["visual_avoid_rules"].get(profile, {}),
    }


def detect_event_profile(event_input: dict[str, Any], brand_guide: dict[str, Any] | None = None) -> str:
    text = _flatten_text({"event_input": event_input, "brand_guide": brand_guide or {}}).lower()
    event_rules = load_rulebook()["event_rules"]
    for profile, rules in event_rules.items():
        keywords = [str(item).lower() for item in rules.get("detectKeywords", [])]
        if any(keyword and keyword in text for keyword in keywords):
            return profile
    return "general"


def profile_search_queries(profile: str, channels: list[str] | None = None) -> list[str]:
    rules = profile_rules(profile)["reference_rules"]
    queries = _string_list(rules.get("searchQueries"))
    channel_text = " ".join(channels or []).lower()
    if profile == "bullion_investment":
        if "blog" not in channel_text and "naver" not in channel_text:
            queries = [query for query in queries if "blog cover" not in query]
        if "community" not in channel_text and "notice" not in channel_text:
            queries = [query for query in queries if "notice banner" not in query]
    return _dedupe(queries)


def profile_fallback_directions(profile: str) -> list[str]:
    return _string_list(profile_rules(profile)["reference_rules"].get("fallbackDirections"))


def profile_prompt_hints(profile: str) -> list[str]:
    return _string_list(profile_rules(profile)["reference_rules"].get("promptHints"))


def profile_avoid_keywords(profile: str) -> list[str]:
    return _string_list(profile_rules(profile)["visual_avoid_rules"].get("avoidKeywords"))


def profile_negative_prompt_hints(profile: str) -> list[str]:
    return _string_list(profile_rules(profile)["visual_avoid_rules"].get("negativePromptHints"))


def profile_reject_terms(profile: str) -> list[str]:
    return _string_list(profile_rules(profile)["visual_avoid_rules"].get("rejectTerms"))


def profile_selection_gates(profile: str) -> dict[str, float]:
    gates = profile_rules(profile)["reference_rules"].get("selectionGates") or {}
    return {
        "brandFit": float(gates.get("brandFit", 7)),
        "eventFit": float(gates.get("eventFit", 7)),
        "productRelevance": float(gates.get("productRelevance", 7)),
        "seriousnessFit": float(gates.get("seriousnessFit", 6)),
        "riskLevelMax": float(gates.get("riskLevelMax", 4)),
    }


def profile_reference_direction(profile: str) -> dict[str, list[str]]:
    rules = profile_rules(profile)["reference_rules"]
    avoid = profile_avoid_keywords(profile)
    negative = profile_negative_prompt_hints(profile)
    return {
        "moodKeywords": _string_list(rules.get("moodKeywords")),
        "compositionKeywords": _string_list(rules.get("compositionKeywords")),
        "lightingKeywords": _string_list(rules.get("lightingKeywords")),
        "colorPalette": _string_list(rules.get("colorPalette")),
        "materialTexture": _string_list(rules.get("materialTexture")),
        "avoidKeywords": avoid,
        "promptHints": profile_prompt_hints(profile),
        "negativePromptHints": negative,
    }


def _load_profiles(filename: str) -> dict[str, Any]:
    data = read_json(RULES_DIR / filename, default={})
    profiles = data.get("profiles", {}) if isinstance(data, dict) else {}
    return profiles if isinstance(profiles, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result
