"""Brand workflow registry backed by the canonical ComfyUI workflow library."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_WORKFLOW_ROOT = Path(r"D:\CD\jewelry_ad_project\02_workflows")
WORKFLOW_ROOT = Path(os.environ.get("BRAND_WORKFLOW_ROOT", str(DEFAULT_WORKFLOW_ROOT)))


CATEGORY_ALIASES = {
    "cosmetic": "cosmetics",
    "cosmetics": "cosmetics",
    "skincare": "cosmetics",
    "beauty": "cosmetics",
    "jewelry": "jewelry",
    "jewellery": "jewelry",
    "diamond": "jewelry",
    "bullion": "bullion",
    "gold": "bullion",
    "silver": "bullion",
    "precious_metal": "bullion",
}


def list_brand_workflows() -> list[str]:
    if not WORKFLOW_ROOT.exists():
        return []
    return sorted(
        f"{path.parent.name}/{path.stem}"
        for path in WORKFLOW_ROOT.glob("*/*.json")
        if path.is_file()
    )


def brand_workflow_path(workflow_id: str) -> Path:
    normalized = _normalize_workflow_id(workflow_id)
    if "/" not in normalized:
        matches = [item for item in list_brand_workflows() if item.endswith(f"/{normalized}")]
        if len(matches) == 1:
            normalized = matches[0]
    if "/" not in normalized:
        raise FileNotFoundError(f"Unknown brand workflow: {workflow_id}")
    category, name = normalized.split("/", 1)
    path = WORKFLOW_ROOT / category / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown brand workflow: {workflow_id}")
    return path


def has_brand_workflow(workflow_id: str) -> bool:
    try:
        brand_workflow_path(workflow_id)
        return True
    except Exception:
        return False


def choose_brand_workflow(category: str, visual_role: str = "", channel_id: str = "") -> str:
    category_id = CATEGORY_ALIASES.get(str(category or "").strip().lower(), "")
    role = str(visual_role or "").lower()
    channel = str(channel_id or "").lower()

    if category_id == "cosmetics":
        if "banner" in channel or "promo" in role:
            return "cosmetics/cosmetic_promo_banner"
        if role in {"support", "texture"}:
            return "cosmetics/cosmetic_lifestyle_scene"
        return "cosmetics/cosmetic_product_hero_v2"

    if category_id == "jewelry":
        if "model" in role or "model" in channel:
            return "jewelry/jewelry_on_model_v2"
        if role in {"support", "scene"}:
            return "jewelry/jewelry_luxury_scene_v2"
        return "jewelry/jewelry_product_hero_v2"

    if category_id == "bullion":
        if "banner" in channel or "promo" in role:
            return "bullion/bullion_promo_banner"
        if role in {"support", "trust"}:
            return "bullion/bullion_trust_visual"
        return "bullion/bullion_product_hero"

    return ""


def load_brand_workflow_config(workflow_id: str) -> dict[str, Any]:
    path = brand_workflow_path(workflow_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = {int(node.get("id")): node for node in data.get("nodes", [])}
    positive = _widget_value(nodes, 11, 0, "")
    negative = _widget_value(nodes, 12, 0, "")
    sampler = _widget_value(nodes, 15, 4, "heun")
    scheduler = _widget_value(nodes, 15, 5, "beta")
    seed = _widget_value(nodes, 15, 0, 0)
    steps = _widget_value(nodes, 15, 2, 10)
    cfg = _widget_value(nodes, 15, 3, 1.0)
    denoise = _widget_value(nodes, 15, 6, 1.0)
    save_prefix = _widget_value(nodes, 17, 0, f"Automation/{path.parent.name}/{path.stem}")
    return {
        "workflow_id": f"{path.parent.name}/{path.stem}",
        "workflow_path": str(path),
        "positive_prompt": positive,
        "negative_prompt": negative,
        "sampler": sampler,
        "scheduler": scheduler,
        "seed": seed,
        "steps": steps,
        "cfg_scale": cfg,
        "denoise": denoise,
        "save_prefix": save_prefix,
    }


def _normalize_workflow_id(value: str) -> str:
    text = str(value or "").replace("\\", "/").strip("/")
    if text.startswith("brand:"):
        text = text.removeprefix("brand:")
    return text


def _widget_value(nodes: dict[int, dict[str, Any]], node_id: int, index: int, default: Any) -> Any:
    values = nodes.get(node_id, {}).get("widgets_values") or []
    return values[index] if len(values) > index else default
