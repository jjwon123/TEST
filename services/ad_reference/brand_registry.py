"""Known-brand registry helpers for stable Meta Ad Library collection."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "assets" / "rules" / "meta-brand-registry.json"


def load_brand_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def profile_brands(profile: str, *, active_only: bool = True) -> list[dict[str, Any]]:
    registry = load_brand_registry()
    brands = list(registry.get("profiles", {}).get(profile, {}).get("brands", []))
    if active_only:
        brands = [brand for brand in brands if brand.get("active", True)]
    return brands


def registry_summary() -> dict[str, Any]:
    registry = load_brand_registry()
    profiles = {}
    for profile, config in registry.get("profiles", {}).items():
        brands = [brand for brand in config.get("brands", []) if brand.get("active", True)]
        profiles[profile] = {
            "label": config.get("label", profile),
            "defaultCountry": config.get("defaultCountry", "KR"),
            "defaultCreativeProfile": config.get("defaultCreativeProfile", "brand_campaign"),
            "brandCount": len(brands),
            "brands": brands,
        }
    return {"version": registry.get("version", ""), "profiles": profiles}


def advertiser_matches_brand(advertiser: str, brand: dict[str, Any]) -> bool:
    return bool(advertiser_match_type(advertiser, brand))


def advertiser_match_type(advertiser: str, brand: dict[str, Any]) -> str:
    """Return direct for the brand account and partner for collaboration ads."""
    normalized_advertiser = normalize_name(advertiser)
    if not normalized_advertiser:
        return ""
    aliases = sorted(
        {normalize_name(value) for value in brand.get("advertiserAliases", []) if normalize_name(value)},
        key=len,
        reverse=True,
    )
    if any(normalized_advertiser == alias or normalized_advertiser.startswith(alias) for alias in aliases):
        return "direct"
    if any(alias in normalized_advertiser for alias in aliases):
        return "partner"
    return ""


def normalize_name(value: Any) -> str:
    return re.sub(r"[\W_]+", "", str(value or "").casefold())
