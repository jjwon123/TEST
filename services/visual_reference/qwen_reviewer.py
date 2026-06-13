"""Ollama Qwen-VL reviewer for shortlist image explanations."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import requests

from core.utils.rulebook import profile_negative_prompt_hints, profile_prompt_hints, profile_reject_terms, profile_selection_gates


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "qwen2.5vl:7b"
DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_CRITERIA_PATH = ROOT / "assets" / "references" / "review-criteria.json"


REVIEW_PROMPT = """You are a senior brand designer and performance marketer.

Evaluate this image as a reference for a premium gold/silver financial event banner.

Criteria:
- calm premium finance mood
- serious brand trust, not cute/kids/toy/kawaii
- metal texture quality
- negative space for Korean copy
- product/focal clarity
- gold/silver/investment/consultation relevance
- no fake text poster, no wine bottle, no random package box
- low stock-photo feeling
- usefulness as a ComfyUI visual reference

Return JSON only:
{
  "decision": "selected | shortlist | rejected",
  "role": "mood | layout | lighting | product | typography",
  "score": 1-100,
  "brand_fit": 1-100,
  "event_fit": 1-100,
  "seriousness_fit": 1-100,
  "product_relevance": 1-100,
  "risk_level": 1-100,
  "reason": "...",
  "risk": "..."
}
"""


def load_review_criteria(criteria_path: Path = DEFAULT_CRITERIA_PATH) -> dict[str, Any]:
    if not criteria_path.exists():
        return {}
    try:
        return json.loads(criteria_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def build_event_reference_prompt(
    event_context: dict[str, Any],
    *,
    criteria: dict[str, Any] | None = None,
) -> str:
    criteria = criteria if criteria is not None else load_review_criteria()
    references = event_context.get("event_references") or event_context.get("references") or []
    if isinstance(references, list):
        reference_text = "\n".join(f"- {item}" for item in references)
    else:
        reference_text = str(references)
    channels = event_context.get("channels") or []
    if isinstance(channels, list):
        channel_text = ", ".join(str(item) for item in channels)
    else:
        channel_text = str(channels)
    criteria_text = format_criteria_for_prompt(criteria)
    bullion_prompt_hints = "\n".join(f"- {item}" for item in profile_prompt_hints("bullion_investment"))
    bullion_reject_terms = ", ".join(profile_reject_terms("bullion_investment"))
    bullion_negative_hints = ", ".join(profile_negative_prompt_hints("bullion_investment"))
    gates = profile_selection_gates("bullion_investment")

    return f"""You are a senior brand designer and performance marketer.

Evaluate this image as a visual reference for the event below.

Event:
- Name: {event_context.get("event_name", "")}
- Objective: {event_context.get("objective", "")}
- Target: {event_context.get("target", "")}
- Channels: {channel_text}

Desired reference direction:
{reference_text}

Review rubric:
{criteria_text}

Bullion investment positive direction:
{bullion_prompt_hints}

Bullion investment hard reject terms:
{bullion_reject_terms}

Bullion investment negative prompt hints:
{bullion_negative_hints}

Return JSON only:
{{
  "decision": "selected | shortlist | rejected",
  "role": "choose exactly one: mood, layout, lighting, product, typography, color, or composition",
  "score": 1-100,
  "brand_fit": 1-100,
  "event_fit": 1-100,
  "copy_space": 1-100,
  "category_fit": 1-100,
  "seriousness_fit": 1-100,
  "product_relevance": 1-100,
  "risk_level": 1-100,
  "layout_idea": 1-100,
  "production_value": 1-100,
  "originality": 1-100,
  "risk_control": 1-100,
  "positive_tags": ["..."],
  "negative_tags": ["..."],
  "reason": "...",
  "risk": "..."
}}

Rules:
- Put exactly one value in "role"; do not copy the whole option list.
- Use only tags from the allowed tag lists.
- For gold/silver/investment/consultation events, reject anything matching the hard reject terms above.
- A selected reference must satisfy brand_fit >= {int(gates['brandFit'] * 10)}, event_fit >= {int(gates['eventFit'] * 10)}, product_relevance >= {int(gates['productRelevance'] * 10)}, seriousness_fit >= {int(gates['seriousnessFit'] * 10)}, and risk_level <= {int(gates['riskLevelMax'] * 10)}.
- Prefer premium finance, gold bar, bullion, asset management, consultation, editorial product photography, and clean empty headline areas.
- If decision is "selected", negative_tags should include only real remaining risks, not generic contradictions.
- Keep reason and risk short and specific to the visible image.
"""


def build_profile_reference_prompt(profile: str, event_context: dict[str, Any] | None = None) -> str:
    event_context = event_context or {}
    if profile == "cosmetics_skincare":
        return f"""You are a senior Korean H&B beauty campaign designer.

Evaluate this image as a reference for a Korean skincare sale banner/card-news campaign.

Event:
- Name: {event_context.get("event_name", "")}
- Product/category: {event_context.get("product", "niacinamide serum / skincare")}
- Offer: {event_context.get("offer", "")}

Score the visible image only. Do not reward search query, file name, or Pinterest metadata.

Return JSON only:
{{
  "decision": "selected | shortlist | rejected",
  "role": "choose exactly one: mood, layout, lighting, product, typography, color, or composition",
  "score": 1-100,
  "local_hb_sale_fit": 1-100,
  "benefit_hierarchy": 1-100,
  "product_trust": 1-100,
  "layout_usability": 1-100,
  "copy_space": 1-100,
  "risk_level": 1-100,
  "website_capture_risk": 1-100,
  "text_artifact_risk": 1-100,
  "foreign_sale_risk": 1-100,
  "positive_tags": ["..."],
  "negative_tags": ["..."],
  "reason": "...",
  "risk": "..."
}}

Decision rules:
- Hard reject if the image is low quality, wrong product category, website/browser screenshot, visible URL/address bar, severe fake text, or mainly a homepage capture.
- Select only if it has usable Korean beauty sale/event layout, product or skincare trust, readable benefit hierarchy, and enough adaptable composition.
- If it has some useful mood/layout but lacks product or benefit hierarchy, choose shortlist.
- Keep reason and risk specific to the visible image.
"""
    if profile == "bullion_investment":
        return build_event_reference_prompt(event_context)
    return """You are a senior brand designer.

Evaluate this image as a visual reference for a brand event campaign.
Return strict JSON with decision, role, score, brand_fit, event_fit, copy_space, product_relevance, risk_level, positive_tags, negative_tags, reason, and risk.
Prefer shortlist unless the image is clearly usable or clearly unsafe.
"""


def format_criteria_for_prompt(criteria: dict[str, Any]) -> str:
    if not criteria:
        return "\n".join([
            "- visual relevance to the event and product/category",
            "- usefulness as a campaign or content design reference",
            "- clear focal subject or layout idea",
            "- negative space or adaptable composition for Korean copy",
            "- premium enough for brand use",
            "- low risk of random unrelated objects, stock-photo feeling, clutter, or off-category imagery",
        ])
    lines: list[str] = []
    for item in criteria.get("weighted_dimensions", []):
        field = item.get("field", "")
        weight = item.get("weight", "")
        question = item.get("question", "")
        lines.append(f"- {field} ({weight}): {question}")
    if criteria.get("hard_reject_rules"):
        lines.append("")
        lines.append("Hard reject rules:")
        lines.extend(f"- {rule}" for rule in criteria.get("hard_reject_rules", []))
    if criteria.get("positive_tags"):
        lines.append("")
        lines.append("Allowed positive tags: " + ", ".join(criteria.get("positive_tags", [])))
    if criteria.get("negative_tags"):
        lines.append("Allowed negative tags: " + ", ".join(criteria.get("negative_tags", [])))
    return "\n".join(lines)


def review_image(
    image_path: Path,
    *,
    model: str = DEFAULT_MODEL,
    host: str = DEFAULT_HOST,
    prompt: str = REVIEW_PROMPT,
    timeout: int = 240,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [_image_b64(image_path)],
            }
        ],
        "options": {"temperature": 0.1},
    }
    response = requests.post(f"{host}/api/chat", json=payload, timeout=timeout)
    response.raise_for_status()
    content = response.json()["message"]["content"].strip()
    return _parse_jsonish(content, image_path=image_path, model=model)


def _image_b64(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode("ascii")


def _parse_jsonish(content: str, *, image_path: Path, model: str) -> dict[str, Any]:
    cleaned = content
    if "```" in cleaned:
        cleaned = cleaned.replace("```json", "```")
        cleaned = cleaned.split("```", 2)[1].strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {
            "decision": "shortlist",
            "role": "mood",
            "score": 50,
            "reason": content,
            "risk": "Model did not return strict JSON.",
        }
    data = sanitize_review(data)
    data["file"] = str(image_path)
    data["candidate_id"] = image_path.stem
    data["review_model"] = model
    return data


def sanitize_review(data: dict[str, Any]) -> dict[str, Any]:
    role = str(data.get("role", "")).strip().lower()
    allowed_roles = {"mood", "layout", "lighting", "product", "typography", "color", "composition"}
    if role not in allowed_roles:
        data["role"] = "composition"
    else:
        data["role"] = role

    negative_tags = _string_list(data.get("negative_tags"))
    if _score(data.get("copy_space")) >= 70:
        negative_tags = [tag for tag in negative_tags if tag != "no-copy-space"]
    if _score(data.get("risk_control")) >= 70:
        negative_tags = [tag for tag in negative_tags if tag != "brand-risk"]
    data["positive_tags"] = _string_list(data.get("positive_tags"))
    data["negative_tags"] = negative_tags
    return data


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _score(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
