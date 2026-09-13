"""ComfyUI API prompt builders for registered presets."""

from __future__ import annotations

import copy
from typing import Any

from services.comfyui.brand_workflows import (
    brand_api_template,
    has_brand_workflow,
    load_brand_workflow_config,
)


def build_api_prompt(workflow_preset: str, payload: dict[str, Any]) -> dict[str, Any]:
    if has_brand_workflow(workflow_preset):
        api_graph = brand_api_template(workflow_preset)
        if api_graph is not None:
            return _apply_brand_api_template(api_graph, payload)
        return _brand_workflow_qwen(payload, load_brand_workflow_config(workflow_preset))
    if workflow_preset in {"korean_poster_overlay_1024", "campaign_keyvisual"}:
        return _korean_poster_overlay_1024(payload)
    if workflow_preset == "product_locked_ad_background_v1":
        return _product_locked_ad_background_v1(payload)
    if workflow_preset == "qwen_candidate_2511":
        return _qwen_candidate_2511(payload)
    raise ValueError(f"No ComfyUI adapter registered for preset: {workflow_preset}")


def _apply_brand_api_template(graph: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Run a verified API-format brand graph, swapping only product image, prompts,
    seed and save prefix.

    Graph topology (unet/GGUF model, LoRA/Lightning toggle, ModelSampling shift,
    CFGNorm, reference method, sampler/steps/cfg/denoise) is left exactly as authored
    so live output matches the human-approved keeper cut for that workflow.
    """
    g = copy.deepcopy(graph)

    def node_of(ref: Any) -> tuple[str | None, dict[str, Any] | None]:
        if isinstance(ref, list) and ref and str(ref[0]) in g:
            return str(ref[0]), g[str(ref[0])]
        return None, None

    def trace_text_encode(start_ref: Any) -> dict[str, Any] | None:
        """Follow a conditioning link back to its TextEncode* source node."""
        seen: set[str] = set()
        nid, node = node_of(start_ref)
        while node is not None and nid not in seen:
            seen.add(str(nid))
            if str(node.get("class_type", "")).startswith("TextEncode"):
                return node
            nid, node = node_of(node.get("inputs", {}).get("conditioning"))
        return None

    ksampler = next((n for n in g.values() if n.get("class_type") == "KSampler"), None)
    pos_node = neg_node = None
    if ksampler is not None:
        pos_node = trace_text_encode(ksampler["inputs"].get("positive"))
        neg_node = trace_text_encode(ksampler["inputs"].get("negative"))
        if payload.get("seed") not in (None, ""):
            ksampler["inputs"]["seed"] = int(payload["seed"])

    # Keep the template base prompt; append campaign-specific direction from the brief.
    campaign_pos = str(payload.get("positive_prompt") or "").strip()
    campaign_neg = str(payload.get("negative_prompt") or "").strip()
    if pos_node is not None and campaign_pos:
        base = str(pos_node["inputs"].get("prompt") or "")
        pos_node["inputs"]["prompt"] = "\n\n".join(
            item for item in [base, "Campaign-specific direction:", campaign_pos] if item
        )
    if neg_node is not None and campaign_neg:
        base = str(neg_node["inputs"].get("prompt") or "")
        neg_node["inputs"]["prompt"] = ", ".join(item for item in [base, campaign_neg] if item)

    product_image = (
        payload.get("product_image")
        or payload.get("base_image")
        or "product_input.png"
    )
    for node in g.values():
        if node.get("class_type") == "LoadImage":
            node["inputs"]["image"] = product_image
            node.pop("is_changed", None)

    metadata = payload.get("metadata", {})
    prefix = (
        payload.get("filename_prefix")
        or metadata.get("candidate_id")
        or metadata.get("prompt_id")
    )
    if prefix:
        for node in g.values():
            if node.get("class_type") == "SaveImage":
                node["inputs"]["filename_prefix"] = _safe_prefix(prefix)

    return g


def _brand_workflow_qwen(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    base_positive = str(config.get("positive_prompt") or "")
    campaign_positive = str(payload.get("positive_prompt") or "")
    merged["positive_prompt"] = "\n\n".join(item for item in [
        base_positive,
        "Campaign-specific direction:",
        campaign_positive,
    ] if item)
    merged["negative_prompt"] = ", ".join(
        item for item in [str(config.get("negative_prompt") or ""), str(payload.get("negative_prompt") or "")]
        if item
    )
    merged["sampler"] = payload.get("sampler") or config.get("sampler") or "heun"
    merged["scheduler"] = payload.get("scheduler") or config.get("scheduler") or "beta"
    merged["steps"] = int(payload.get("steps") or config.get("steps") or 10)
    merged["cfg_scale"] = float(payload.get("cfg_scale") or config.get("cfg_scale") or 1.0)
    merged["denoise"] = float(payload.get("denoise") or config.get("denoise") or 1.0)
    if not payload.get("seed"):
        merged["seed"] = config.get("seed") or 0
    merged.setdefault("metadata", {})
    merged["metadata"] = {
        **merged.get("metadata", {}),
        "brand_workflow_id": config.get("workflow_id", ""),
        "brand_workflow_path": config.get("workflow_path", ""),
    }
    return _qwen_candidate_2511(merged)


def _korean_poster_overlay_1024(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata", {})
    width, height = _output_size(payload.get("ratio") or payload.get("aspect_ratio") or "1:1")
    filename_prefix = _safe_prefix(
        payload.get("filename_prefix")
        or metadata.get("candidate_id")
        or metadata.get("prompt_id")
        or "comfyui_candidate"
    )
    title = payload.get("headline") or _short_text(payload.get("positive_prompt", ""), "콘텐츠 이미지")
    subtitle = payload.get("subheadline") or payload.get("cta") or "자세히 보기"
    footer_left = _channel_label(payload.get("footer_left") or metadata.get("channel_id") or "campaign")
    footer_right = payload.get("footer_right") or metadata.get("deliverable_id") or "v01"
    layout = _layout(width, height)
    text_color = payload.get("text_color") or "#17324D"
    secondary_text_color = payload.get("secondary_text_color") or "#31546F"
    footer_text_color = payload.get("footer_text_color") or "#31546F"
    badge = str(payload.get("badge") or "")

    return {
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": payload.get("base_image", "qwen_image_edit_1024.png"),
                "upload": "image",
            },
        },
        "2": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["1", 0],
                "upscale_method": "lanczos",
                "width": width,
                "height": height,
                "crop": "center",
            },
        },
        "3": _overlay_node(["2", 0], badge, *layout["badge_box"], text_color=secondary_text_color),
        "4": _overlay_node(
            ["3", 0],
            title,
            *layout["title_box"],
            line_spacing=2,
            text_color=text_color,
            font_path="C:/Windows/Fonts/malgunbd.ttf",
        ),
        "5": _overlay_node(
            ["4", 0],
            subtitle,
            *layout["subtitle_box"],
            line_spacing=0,
            text_color=secondary_text_color,
        ),
        "6": _overlay_node(
            ["5", 0],
            footer_left,
            *layout["footer_left_box"],
            align="left",
            line_spacing=2,
            text_color=footer_text_color,
        ),
        "7": _overlay_node(
            ["6", 0],
            footer_right,
            *layout["footer_right_box"],
            align="right",
            line_spacing=2,
            text_color=footer_text_color,
        ),
        "8": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["7", 0],
                "filename_prefix": filename_prefix,
            },
        },
    }


def _product_locked_ad_background_v1(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata", {})
    width, height = _output_size(payload.get("ratio") or payload.get("aspect_ratio") or "1:1")
    filename_prefix = _safe_prefix(
        payload.get("filename_prefix")
        or metadata.get("candidate_id")
        or metadata.get("prompt_id")
        or "product_locked_ad"
    )
    layout = _product_layout(width, height, payload)

    mask_image = payload.get("product_mask") or ""
    prompt = {
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": payload.get("product_image") or payload.get("base_image") or "product_input.png",
                "upload": "image",
            },
        },
        "2": {
            "class_type": "ProductLockedAdComposite",
            "inputs": {
                "product_image": ["1", 0],
                "product_mask": ["1", 1],
                "width": width,
                "height": height,
                "background_style": payload.get("background_style", "cosmetic_studio"),
                "product_scale": layout["product_scale"],
                "x_percent": layout["x_percent"],
                "y_percent": layout["y_percent"],
                "shadow_opacity": payload.get("shadow_opacity", 0.34),
                "shadow_blur": payload.get("shadow_blur", 46),
                "shadow_offset_y": payload.get("shadow_offset_y", 26),
                "accent_color": payload.get("accent_color", "#E8F0E8"),
            },
        },
        "3": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["2", 0],
                "filename_prefix": filename_prefix,
            },
        },
    }
    if mask_image:
        prompt["4"] = {
            "class_type": "LoadImage",
            "inputs": {
                "image": mask_image,
                "upload": "image",
            },
        }
        prompt["2"]["inputs"]["product_mask"] = ["4", 1]
    return prompt


def _qwen_candidate_2511(payload: dict[str, Any]) -> dict[str, Any]:
    """Qwen Image Edit 2511 GGUF - first-pass product ad candidate.

    Runs the first KSampler pass only (no SAM/LaMa inpainting).
    All three image slots use the same product packshot so Qwen edits
    the product into a premium campaign scene.
    """
    metadata = payload.get("metadata", {})
    product_image = (
        payload.get("product_image")
        or payload.get("base_image")
        or "product_input.png"
    )
    positive_prompt = payload.get("positive_prompt", "")
    negative_prompt = payload.get("negative_prompt", "")
    seed = int(payload.get("seed") or 0)
    steps = int(payload.get("steps") or 8)
    cfg = float(payload.get("cfg_scale") or 1.0)
    sampler = payload.get("sampler") or "heun"
    scheduler = payload.get("scheduler") or "beta"
    denoise = float(payload.get("denoise") or 1.0)
    filename_prefix = _safe_prefix(
        payload.get("filename_prefix")
        or metadata.get("candidate_id")
        or metadata.get("prompt_id")
        or "qwen_candidate"
    )

    def load_image(img: str) -> dict[str, Any]:
        return {"class_type": "LoadImage", "inputs": {"image": img, "upload": "image"}}

    return {
        # Model loading
        "1": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
            "type": "qwen_image",
            "device": "default",
        }},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "qwen-image-edit-2511-Q3_K_M.gguf"}},
        "18": {"class_type": "LoraLoader", "inputs": {
            "model": ["4", 0],
            "clip": ["1", 0],
            "lora_name": "Qwen-Image-Edit-2511-Lightning-8steps-V1.0-bf16.safetensors",
            "strength_model": 1.0,
            "strength_clip": 1.0,
        }},
        "2": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["18", 0], "shift": 10.0}},
        "7": {"class_type": "CFGNorm", "inputs": {"model": ["2", 0], "strength": 1.0}},

        # Product images (all slots use the same packshot)
        "19": load_image(product_image),
        "20": load_image(product_image),
        "21": load_image(product_image),

        # Scale product to Kontext-optimal resolution
        "16": {"class_type": "FluxKontextImageScale", "inputs": {"image": ["19", 0]}},

        # Text encoding (positive=13, negative=9)
        "13": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "clip": ["18", 1],
            "prompt": positive_prompt,
            "vae": ["3", 0],
            "image1": ["16", 0],
            "image2": ["20", 0],
            "image3": ["21", 0],
        }},
        "9": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "clip": ["18", 1],
            "prompt": negative_prompt,
            "vae": ["3", 0],
            "image1": ["16", 0],
            "image2": ["20", 0],
            "image3": ["21", 0],
        }},

        # FluxKontext reference method wrappers
        "6": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
            "conditioning": ["13", 0],
            "reference_latents_method": "index_timestep_zero",
        }},
        "5": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
            "conditioning": ["9", 0],
            "reference_latents_method": "index_timestep_zero",
        }},

        # Encode product as starting latent
        "14": {"class_type": "VAEEncode", "inputs": {"pixels": ["16", 0], "vae": ["3", 0]}},

        # Sample
        "15": {"class_type": "KSampler", "inputs": {
            "model": ["7", 0],
            "positive": ["6", 0],
            "negative": ["5", 0],
            "latent_image": ["14", 0],
            "seed": seed,
            "control_after_generate": "randomize",
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": denoise,
        }},

        # Decode + save
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["15", 0], "vae": ["3", 0]}},
        "99": {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": filename_prefix}},
    }


def _overlay_node(
    image: list[Any],
    text: str,
    box_x: int,
    box_y: int,
    box_width: int,
    box_height: int,
    font_size: int,
    min_font_size: int,
    align: str = "center",
    line_spacing: int = 6,
    text_color: str = "#17324D",
    stroke_width: int = 0,
    stroke_color: str = "#FFFFFF",
    shadow_y: int = 0,
    shadow_blur: int = 0,
    shadow_color: str = "#FFFFFF",
    font_path: str = "C:/Windows/Fonts/NotoSansKR-VF.ttf",
) -> dict[str, Any]:
    return {
        "class_type": "KoreanTextOverlay",
        "inputs": {
            "image": image,
            "text": text,
            "font_path": font_path,
            "box_x": box_x,
            "box_y": box_y,
            "box_width": box_width,
            "box_height": box_height,
            "font_size": font_size,
            "min_font_size": min_font_size,
            "text_color": text_color,
            "opacity": 1.0,
            "align": align,
            "vertical_align": "middle",
            "line_spacing": line_spacing,
            "stroke_width": stroke_width,
            "stroke_color": stroke_color,
            "shadow_x": 0,
            "shadow_y": shadow_y,
            "shadow_blur": shadow_blur,
            "shadow_color": shadow_color,
            "draw_box": False,
        },
    }


def _short_text(value: str, fallback: str) -> str:
    words = str(value or "").replace(",", " ").split()
    if not words:
        return fallback
    text = " ".join(words[:6])
    return text if len(text) <= 28 else text[:28].rstrip()


def _safe_prefix(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in "-_/" else "_" for ch in str(value))
    return text.strip("_") or "comfyui_candidate"


def _output_size(ratio: str) -> tuple[int, int]:
    return {
        "1:1": (1024, 1024),
        "4:5": (1024, 1280),
        "4:3": (1024, 768),
        "16:9": (1280, 720),
    }.get(str(ratio), (1024, 1024))


def _layout(width: int, height: int) -> dict[str, Any]:
    scale = min(width, height) / 1024
    title_h = int(height * 0.17)
    title_y = int(height * 0.07)
    subtitle_y = title_y + title_h
    footer_y = int(height * 0.86)
    return {
        "badge": _badge_for_size(width, height),
        "badge_box": [
            int(width * 0.045),
            int(height * 0.035),
            int(width * 0.18),
            int(height * 0.06),
            max(18, int(32 * scale)),
            max(10, int(16 * scale)),
        ],
        "title_box": [
            int(width * 0.11),
            title_y,
            int(width * 0.78),
            title_h,
            max(32, int(64 * scale)),
            max(22, int(36 * scale)),
        ],
        "subtitle_box": [
            int(width * 0.16),
            subtitle_y,
            int(width * 0.68),
            int(height * 0.075),
            max(16, int(28 * scale)),
            max(10, int(14 * scale)),
        ],
        "footer_left_box": [
            int(width * 0.055),
            footer_y,
            int(width * 0.42),
            int(height * 0.085),
            max(14, int(24 * scale)),
            max(9, int(12 * scale)),
        ],
        "footer_right_box": [
            int(width * 0.68),
            footer_y,
            int(width * 0.27),
            int(height * 0.085),
            max(14, int(24 * scale)),
            max(9, int(12 * scale)),
        ],
    }


def _product_layout(width: int, height: int, payload: dict[str, Any]) -> dict[str, float]:
    ratio = width / max(height, 1)
    if ratio > 1.4:
        defaults = {"product_scale": 0.54, "x_percent": 0.5, "y_percent": 0.62}
    elif ratio < 0.9:
        defaults = {"product_scale": 0.58, "x_percent": 0.5, "y_percent": 0.60}
    else:
        defaults = {"product_scale": 0.60, "x_percent": 0.5, "y_percent": 0.60}
    return {
        "product_scale": float(payload.get("product_scale") or defaults["product_scale"]),
        "x_percent": float(payload.get("product_x_percent") or payload.get("x_percent") or defaults["x_percent"]),
        "y_percent": float(payload.get("product_y_percent") or payload.get("y_percent") or defaults["y_percent"]),
    }


def _badge_for_size(width: int, height: int) -> str:
    if width == height:
        return "1:1"
    if width < height:
        return "4:5"
    if width * 9 == height * 16:
        return "16:9"
    return "4:3"


def _channel_label(value: str) -> str:
    return {
        "instagram_cardnews": "카드뉴스",
        "instagram_feed": "인스타그램",
        "blog_thumbnail": "블로그 썸네일",
        "blog_inline_image": "블로그 본문",
        "community": "커뮤니티",
    }.get(str(value), str(value))
