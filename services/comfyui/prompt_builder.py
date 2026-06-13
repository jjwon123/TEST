"""Build ComfyUI prompt payloads from visual candidate records."""

from __future__ import annotations

from typing import Any


def build_payload(prompt_record: dict[str, Any]) -> dict[str, Any]:
    """Create a provider-neutral payload that a preset adapter can expand."""
    return {
        "positive_prompt": prompt_record.get("positive_prompt", ""),
        "negative_prompt": prompt_record.get("negative_prompt", ""),
        "ratio": prompt_record.get("ratio", "1:1"),
        "seed": prompt_record.get("seed"),
        "sampler": prompt_record.get("sampler"),
        "scheduler": prompt_record.get("scheduler"),
        "model": prompt_record.get("model"),
        "steps": prompt_record.get("steps"),
        "cfg_scale": prompt_record.get("cfg_scale"),
        "denoise": prompt_record.get("denoise"),
        "batch_size": prompt_record.get("batch_size", 1),
        "candidate_count": prompt_record.get("candidate_count", 1),
        "workflow_preset": prompt_record.get("workflow_preset"),
        "base_image": prompt_record.get("base_image", "qwen_image_edit_1024.png"),
        "product_image": prompt_record.get("product_image", prompt_record.get("base_image", "product_input.png")),
        "product_mask": prompt_record.get("product_mask", ""),
        "product_image_path": prompt_record.get("product_image_path", ""),
        "product_mask_path": prompt_record.get("product_mask_path", ""),
        "reference_images": prompt_record.get("reference_images", []),
        "reference_image_paths": prompt_record.get("reference_image_paths", []),
        "background_style": prompt_record.get("background_style", "cosmetic_studio"),
        "product_scale": prompt_record.get("product_scale"),
        "product_x_percent": prompt_record.get("product_x_percent"),
        "product_y_percent": prompt_record.get("product_y_percent"),
        "shadow_opacity": prompt_record.get("shadow_opacity", 0.34),
        "shadow_blur": prompt_record.get("shadow_blur", 46),
        "shadow_offset_y": prompt_record.get("shadow_offset_y", 26),
        "accent_color": prompt_record.get("accent_color", "#E8F0E8"),
        "headline": prompt_record.get("headline", ""),
        "subheadline": prompt_record.get("subheadline", ""),
        "cta": prompt_record.get("cta", ""),
        "footer_left": prompt_record.get("footer_left", ""),
        "footer_right": prompt_record.get("footer_right", ""),
        "filename_prefix": prompt_record.get("candidate_id") or prompt_record.get("prompt_id"),
        "text_safety": prompt_record.get("text_safety", {}),
        "metadata": {
            "prompt_id": prompt_record.get("prompt_id"),
            "candidate_id": prompt_record.get("candidate_id"),
            "deliverable_id": prompt_record.get("deliverable_id"),
            "visual_role": prompt_record.get("visual_role"),
            "channel_id": prompt_record.get("channel_id"),
            "candidate_index": prompt_record.get("candidate_index"),
            "regeneration_group": prompt_record.get("regeneration_group"),
            "reference_asset": prompt_record.get("reference_asset", {}),
            "reference_direction": prompt_record.get("reference_direction", {}),
            "product_id": prompt_record.get("product_id", ""),
            "product_source": prompt_record.get("product_source", {}),
            "workflow_id": prompt_record.get("workflow_preset"),
            "seed": prompt_record.get("seed"),
            "reference_images": prompt_record.get("reference_images", []),
        },
    }
