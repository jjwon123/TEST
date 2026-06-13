"""Classify newly collected Meta images into reusable creative-reference types."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from services.visual_reference.qwen_reviewer import DEFAULT_HOST, DEFAULT_MODEL, review_image


EXCLUDED_CREATIVE_TYPES = {"promotion_text_heavy", "card_news", "reject_noise"}
KNOWN_CREATIVE_TYPES = {
    "promotion_text_heavy",
    "card_news",
    "product_clean",
    "brand_campaign",
    "device",
    "model_lifestyle",
    "jewelry_product",
    "jewelry_craft",
    "reject_noise",
}

CLASSIFICATION_PROMPT = """You are classifying a competitor Meta advertisement image for a visual reference library.
Judge only the visible image. Return JSON only:
{
  "creative_type": "promotion_text_heavy | card_news | product_clean | brand_campaign | device | model_lifestyle | jewelry_product | jewelry_craft | reject_noise",
  "category_fit": 1-100,
  "reference_usability": 1-100,
  "text_density": 1-100,
  "card_news_style": false,
  "promotion_text_dominant": false,
  "screen_capture_risk": 1-100,
  "broken_or_unusable": false,
  "reason": "short visible-image reason"
}

Classification rules:
- promotion_text_heavy: price, discount, giveaway, limited-time offer, CTA, or large sales copy dominates.
- card_news: explainer panels, numbered points, comparisons, before/after, charts, reviews, or multi-block educational slides.
- product_clean: product/container is the hero and text or sales structure does not dominate.
- brand_campaign: editorial campaign image or brand storytelling.
- device: beauty device or screen/device is the hero.
- model_lifestyle: model, portrait, wearing, or lifestyle scene is the hero.
- jewelry_product: jewelry product or macro display is the hero.
- jewelry_craft: making, setting, artisan, or jewelry process is the hero.
- reject_noise: broken, unrelated, screenshot-like, severe artifact, or unusable image.
"""


def classify_media(
    media: dict[str, Any],
    *,
    profile: str,
    brand: dict[str, Any],
    reviewer: Callable[..., dict[str, Any]] = review_image,
    model: str = DEFAULT_MODEL,
    host: str = DEFAULT_HOST,
    timeout: int = 240,
) -> dict[str, Any]:
    """Attach normalized creative classification and collection-gate fields."""
    source = Path(str(media.get("savedPath") or ""))
    prompt = (
        CLASSIFICATION_PROMPT
        + f"\nExpected industry profile: {profile}."
        + f"\nKnown competitor brand: {brand.get('name', '')}."
        + f"\nUseful brand roles: {', '.join(str(role) for role in brand.get('roles', []))}."
    )
    result = dict(media)
    try:
        review = reviewer(source, prompt=prompt, model=model, host=host, timeout=timeout)
        creative_type = normalize_creative_type(review)
        reasons = exclusion_reasons(review, creative_type)
        result.update({
            "qwenReview": review,
            "creativeType": creative_type,
            "creativeGate": "excluded" if reasons else "accepted",
            "creativeExclusionReasons": reasons,
            "needsCreativeReview": creative_type == "unclassified",
        })
    except Exception as exc:
        result.update({
            "creativeType": "unclassified",
            "creativeGate": "review",
            "creativeExclusionReasons": [],
            "needsCreativeReview": True,
            "qwenError": str(exc),
        })
    return result


def normalize_creative_type(review: dict[str, Any]) -> str:
    creative_type = str(review.get("creative_type") or review.get("creativeType") or "").strip().lower()
    aliases = {
        "clean_product_visual": "product_clean",
        "single_image_ad": "brand_campaign",
        "promotion_structure": "promotion_text_heavy",
    }
    creative_type = aliases.get(creative_type, creative_type)
    if creative_type in KNOWN_CREATIVE_TYPES:
        return creative_type
    if review.get("card_news_style") is True:
        return "card_news"
    if review.get("promotion_text_dominant") is True:
        return "promotion_text_heavy"
    if review.get("broken_or_unusable") is True:
        return "reject_noise"
    return "unclassified"


def exclusion_reasons(review: dict[str, Any], creative_type: str) -> list[str]:
    reasons: list[str] = []
    if creative_type in EXCLUDED_CREATIVE_TYPES:
        reasons.append(creative_type)
    if review.get("card_news_style") is True and "card_news" not in reasons:
        reasons.append("card_news")
    if review.get("promotion_text_dominant") is True and "promotion_text_heavy" not in reasons:
        reasons.append("promotion_text_heavy")
    if review.get("broken_or_unusable") is True and "reject_noise" not in reasons:
        reasons.append("reject_noise")
    if _score(review.get("screen_capture_risk")) >= 70:
        reasons.append("screen_capture")
    return reasons


def _score(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
