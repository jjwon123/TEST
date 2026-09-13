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


def brand_api_template(workflow_id: str) -> dict[str, Any] | None:
    """Return the canonical API-format graph for a brand workflow, if one exists.

    Canonical API templates live in ``<WORKFLOW_ROOT>/api/<name>.api.json`` and are
    verified, ready-to-queue ComfyUI graphs. When present, the automation runs the
    template graph verbatim (only swapping product image, prompts, seed and save
    prefix) instead of rebuilding a graph in code. This guarantees live output matches
    the human-approved keeper cut for that workflow.
    """
    try:
        path = brand_workflow_path(workflow_id)
    except FileNotFoundError:
        return None
    api_path = WORKFLOW_ROOT / "api" / f"{path.stem}.api.json"
    if api_path.exists():
        return json.loads(api_path.read_text(encoding="utf-8"))
    return _runtime_api_template(path)


def _runtime_api_template(path: Path) -> dict[str, Any] | None:
    """Materialize the product-hero lane of a canonical UI workflow as an API graph.

    Some approved brand workflows (currently the cosmetics library) are saved as
    ComfyUI canvas JSON rather than queueable API JSON. Their product-hero lane is
    intentionally the same single-input Qwen graph as the jewelry keeper: product
    image -> scale -> positive/negative conditioning -> sample -> save.  Read the
    authored model, prompt, and sampling values from that workflow instead of
    falling back to the generic candidate preset. This preserves the brand's
    product-protection rules and visual personality while keeping the graph safe to
    submit to `/prompt`.
    """
    try:
        workflow = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    nodes = workflow.get("nodes") or []

    def first(node_type: str, title_contains: str = "") -> dict[str, Any] | None:
        title_contains = title_contains.lower()
        for node in nodes:
            if node.get("type") != node_type:
                continue
            if title_contains and title_contains not in str(node.get("title") or "").lower():
                continue
            return node
        return None

    unet = first("UnetLoaderGGUF")
    clip = first("CLIPLoader")
    vae = first("VAELoader")
    image = first("LoadImage")
    scale = first("ImageScaleToTotalPixels")
    positive = first("TextEncodeQwenImageEditPlus", "positive")
    negative = first("TextEncodeQwenImageEditPlus", "negative")
    sampler_model = first("ModelSamplingAuraFlow")
    cfg_norm = first("CFGNorm")
    sampler = first("KSampler")
    if not all((unet, clip, vae, image, scale, positive, negative, sampler_model, cfg_norm, sampler)):
        return None

    def widget(node: dict[str, Any], index: int, default: Any) -> Any:
        values = node.get("widgets_values") or []
        return values[index] if len(values) > index else default

    return {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": widget(unet, 0, "qwen-image-edit-2511-Q6_K.gguf")}},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": widget(clip, 0, "qwen_2.5_vl_7b_fp8_scaled.safetensors"),
            "type": widget(clip, 1, "qwen_image"),
            "device": widget(clip, 2, "default"),
        }},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": widget(vae, 0, "qwen_image_vae.safetensors")}},
        "4": {"class_type": "LoadImage", "inputs": {"image": widget(image, 0, "PRODUCT_INPUT.png")}},
        "5": {"class_type": "ImageScaleToTotalPixels", "inputs": {
            "image": ["4", 0],
            "upscale_method": widget(scale, 0, "lanczos"),
            "megapixels": float(widget(scale, 1, 1.6)),
            "resolution_steps": int(widget(scale, 2, 1)),
        }},
        "6": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "clip": ["2", 0], "vae": ["3", 0], "image1": ["5", 0],
            "prompt": widget(positive, 0, ""),
        }},
        "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "clip": ["2", 0], "vae": ["3", 0], "image1": ["5", 0],
            "prompt": widget(negative, 0, ""),
        }},
        "25": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
            "conditioning": ["6", 0], "reference_latents_method": "index_timestep_zero",
        }},
        "26": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
            "conditioning": ["7", 0], "reference_latents_method": "index_timestep_zero",
        }},
        "8": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": float(widget(sampler_model, 0, 3.1))}},
        "9": {"class_type": "CFGNorm", "inputs": {"model": ["8", 0], "strength": float(widget(cfg_norm, 0, 1.0))}},
        "19": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["3", 0]}},
        "20": {"class_type": "KSampler", "inputs": {
            "model": ["9", 0], "positive": ["25", 0], "negative": ["26", 0], "latent_image": ["19", 0],
            "steps": int(widget(sampler, 2, 20)), "cfg": float(widget(sampler, 3, 3.0)),
            "seed": int(widget(sampler, 0, 0)), "sampler_name": widget(sampler, 4, "euler"),
            "scheduler": widget(sampler, 5, "simple"), "denoise": float(widget(sampler, 6, 1.0)),
        }},
        "21": {"class_type": "VAEDecode", "inputs": {"samples": ["20", 0], "vae": ["3", 0]}},
        "23": {"class_type": "SaveImage", "inputs": {"images": ["21", 0], "filename_prefix": f"Automation/{path.parent.name}/{path.stem}"}},
    }


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
