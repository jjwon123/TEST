"""Manifest-first implementation for 03_visual_candidates.

This stage creates prompt records, candidate metadata, regeneration groups, and
materialized preview PNGs that `04_admin_selection` can inspect.
"""

from __future__ import annotations

import hashlib
import os
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json, write_json, write_text
from core.utils.rulebook import profile_negative_prompt_hints, profile_reject_terms
from core.utils.schema_validation import validate_json
from services.comfyui.client import ComfyUIClient, ComfyUIJob
from services.comfyui.brand_workflows import choose_brand_workflow, load_brand_workflow_config
from services.comfyui.prompt_builder import build_payload
from services.comfyui.workflow_registry import preset_path
from services.products.library import load_product_from_event


ROOT = Path(__file__).resolve().parents[3]
STAGE_ID = "03_visual_candidates"
DEFAULT_WORKFLOW_PRESET = "qwen_candidate_2511"
BULLION_BLOCKED_POSITIVE_TERMS = [
    "mascot",
    "character",
    "cute",
    "camping",
    "picnic",
    "tent",
    "toy",
    "diorama",
    "cartoon",
    "kawaii",
    "playful",
    "wine",
    "bottle",
    "package box",
]
BULLION_HARD_NEGATIVE_TERMS = [
    "mascot",
    "character",
    "camping",
    "picnic",
    "tent",
    "toy diorama",
    "toy-like",
    "cute 3d",
    "cartoon",
    "kawaii",
    "playful",
    "wine bottle",
    "random package box",
    "fake poster text",
    "fake text",
    "unreadable typography",
    "childlike 3d scene",
    "theme park mood",
    "cute mascot",
]
BULLION_BLOCKED_POSITIVE_TERMS = profile_reject_terms("bullion_investment") or BULLION_BLOCKED_POSITIVE_TERMS
BULLION_HARD_NEGATIVE_TERMS = profile_negative_prompt_hints("bullion_investment") or BULLION_HARD_NEGATIVE_TERMS


def run(
    run_dir: Path,
    mode: str = "run",
    outputs: list[str] | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    brief = read_json(run_dir / "01_event_brief" / "brief.json")
    content_plan = read_json(run_dir / "02_content_planning" / "content-plan.json")
    event_input = read_json(run_dir / "event-input.json", default={})
    reference_manifest = _load_reference_manifest(run_dir)
    reference_research = _load_reference_research(run_dir)
    product_profile = _load_product_profile(event_input)

    input_schema = read_json(ROOT / "pipeline" / STAGE_ID / "input.schema.json")
    output_schema = read_json(ROOT / "pipeline" / STAGE_ID / "output.schema.json")
    candidate_schema = read_json(ROOT / "core" / "schemas" / "candidate-manifest.schema.json")
    validate_json({"brief": brief, "content_plan": content_plan}, input_schema, data_label=f"{STAGE_ID} input", schema_label=f"pipeline/{STAGE_ID}/input.schema.json")

    stage_output = build_stage_output(
        brief,
        content_plan,
        reference_manifest=reference_manifest,
        reference_research=reference_research,
        requested_group=group,
        product_profile=product_profile,
    )
    materialized = materialize_previews(run_dir, stage_output, requested_group=group)
    stage_output["candidates"] = materialized["candidates"]
    stage_output["visual_plan"]["generation_mode"] = materialized["generation_mode"]
    stage_output["visual_plan"]["materialized_group"] = group or "all"
    stage_output["visual_plan"]["materialized_at"] = materialized["materialized_at"]

    validate_json(stage_output, output_schema, data_label=f"{STAGE_ID} outputs", schema_label=f"pipeline/{STAGE_ID}/output.schema.json")
    candidate_manifest = {
        "event_id": stage_output["event_id"],
        "regeneration_groups": stage_output["regeneration_groups"],
        "candidates": stage_output["candidates"],
    }
    validate_json(candidate_manifest, candidate_schema, data_label=f"{STAGE_ID}/candidate-manifest.json", schema_label="core/schemas/candidate-manifest.schema.json")

    stage_dir = run_dir / STAGE_ID
    visual_plan_path = stage_dir / "visual-plan.json"
    prompts_path = stage_dir / "image-prompts.json"
    manifest_path = stage_dir / "candidate-manifest.json"
    quality_path = stage_dir / "generation-quality.json"
    notes_path = stage_dir / "notes.md"

    write_json(visual_plan_path, stage_output["visual_plan"])
    write_json(prompts_path, {"engine": "comfyui", "prompts": stage_output["prompts"]})
    write_json(manifest_path, candidate_manifest)
    write_json(quality_path, build_generation_quality(run_dir, stage_output))
    write_text(notes_path, build_notes(stage_output, group=group))

    return {
        "stage_id": STAGE_ID,
        "status": "done",
        "outputs": [
            str(visual_plan_path.relative_to(run_dir)),
            str(prompts_path.relative_to(run_dir)),
            str(manifest_path.relative_to(run_dir)),
            str(quality_path.relative_to(run_dir)),
            str(notes_path.relative_to(run_dir)),
        ],
        "notes": [],
        "next_state": "selection_pending",
        "regeneration_groups": {
            item["group_id"]: item["candidate_ids"]
            for item in stage_output["regeneration_groups"]
            if not group or item["group_id"] == group
        },
    }


def build_stage_output(
    brief: dict[str, Any],
    content_plan: dict[str, Any],
    reference_manifest: dict[str, Any] | None = None,
    reference_research: dict[str, Any] | None = None,
    requested_group: str | None = None,
    product_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prompts = []
    candidates = []
    groups = []
    visual_requirements = []
    issues = []
    deliverable_by_id = {
        item.get("deliverable_id"): item
        for item in content_plan.get("deliverables", [])
    }
    reference_assets = _selected_reference_assets(reference_manifest or {})
    reference_research = reference_research or {}
    product_profile = product_profile or {}

    for image_need in content_plan.get("image_needs", []):
        group_id = _group_id(image_need)
        deliverable = deliverable_by_id.get(image_need["deliverable_id"], {})
        visual_requirements.append({
            "deliverable_id": image_need["deliverable_id"],
            "channel_id": image_need.get("channel_id", ""),
            "visual_role": image_need.get("visual_role", "key_visual"),
            "ratio": image_need.get("ratio", "1:1"),
            "message_priority": _message_priority(content_plan, deliverable),
            "channel_purpose": deliverable.get("purpose", ""),
            "copy_intent": deliverable.get("copy_intent", ""),
            "visual_need": deliverable.get("visual_need", ""),
            "candidate_count": 3,
            "regeneration_group": group_id,
        })
        if not deliverable:
            issues.append({
                "issue_type": "missing_deliverable_context",
                "deliverable_id": image_need["deliverable_id"],
                "severity": "warning",
                "message": "Image need has no matching deliverable metadata.",
            })

        candidate_ids = []
        for index in range(1, 4):
            candidate_id = f"{group_id}_c{index:02d}"
            prompt_id = f"{group_id}_p{index:02d}"
            workflow_preset = _workflow_preset(image_need, product_profile)
            workflow_config = _workflow_config(workflow_preset)
            reference_asset = _reference_for_variant(reference_assets, image_need, index)
            reference_trace = _reference_trace(reference_asset)
            product_trace = _product_trace(product_profile)
            input_image = _input_image_source(image_need, product_profile, reference_research)
            candidate_ids.append(candidate_id)
            prompts.append({
                "prompt_id": prompt_id,
                "candidate_id": candidate_id,
                "deliverable_id": image_need["deliverable_id"],
                "regeneration_group": group_id,
                "workflow_preset": workflow_preset,
                "workflow_source": workflow_config.get("workflow_path", "local"),
                "positive_prompt": _positive_prompt(brief, content_plan, deliverable, image_need, variant=index, reference_asset=reference_asset, reference_research=reference_research, product_profile=product_profile),
                "negative_prompt": _negative_prompt(product_profile, reference_research),
                "ratio": image_need.get("ratio", "1:1"),
                "aspect_ratio": image_need.get("ratio", "1:1"),
                "visual_role": image_need.get("visual_role", "key_visual"),
                "channel_id": image_need.get("channel_id", ""),
                "candidate_index": index,
                "candidate_count": 3,
                "batch_size": 1,
                "seed": _seed_for(prompt_id),
                "sampler": workflow_config.get("sampler", "dpmpp_2m"),
                "scheduler": workflow_config.get("scheduler", "beta"),
                "model": "campaign_default",
                "steps": int(workflow_config.get("steps") or 28),
                "cfg_scale": float(workflow_config.get("cfg_scale") or 6.5),
                "denoise": float(workflow_config.get("denoise") or 1.0),
                "base_image": input_image["base_image"],
                "product_id": product_profile.get("library_id", ""),
                "product_image": input_image["product_image"],
                "product_mask": product_profile.get("mask_image_asset", {}).get("comfyui_name") or image_need.get("product_mask", ""),
                "product_image_path": input_image["product_image_path"],
                "product_mask_path": product_profile.get("mask_image_asset", {}).get("absolute_path", ""),
                "reference_images": [ref.get("comfyui_name") for ref in product_profile.get("brand_style_refs", []) if ref.get("comfyui_name")],
                "reference_image_paths": [ref.get("absolute_path") for ref in product_profile.get("brand_style_refs", []) if ref.get("absolute_path")],
                "headline": _headline(brief, deliverable, variant=index),
                "subheadline": _subheadline(brief, deliverable),
                "cta": _cta(brief, deliverable),
                "footer_left": image_need.get("channel_id", ""),
                "footer_right": f"v{index:02d}",
                "reference_asset": reference_trace,
                "reference_direction": _reference_direction_trace(reference_research),
                "product_source": product_trace,
                "text_safety": {
                    "overlay_required": image_need.get("text_safe_area_required", True),
                    "safe_area_hint": "Korean text is composed by ComfyUI KoreanTextOverlay",
                    "assessment_mode": "rendered_overlay",
                },
            })
            candidates.append({
                "candidate_id": candidate_id,
                "deliverable_id": image_need["deliverable_id"],
                "regeneration_group": group_id,
                "visual_role": image_need.get("visual_role", "key_visual"),
                "channel_id": image_need.get("channel_id", ""),
                "ratio": image_need.get("ratio", "1:1"),
                "preview_path": f"03_visual_candidates/previews/{candidate_id}.png",
                "image_path": f"03_visual_candidates/previews/{candidate_id}.png",
                "source_prompt_id": prompt_id,
                "workflow_preset": workflow_preset,
                "workflow_source": workflow_config.get("workflow_path", "local"),
                "workflow_id": workflow_preset,
                "prompt_id": prompt_id,
                "seed": _seed_for(prompt_id),
                "product_id": product_profile.get("library_id", ""),
                "product_source": product_trace,
                "reference_images": [reference_trace] if reference_trace else [],
                "reject_reasons": [],
                "candidate_index": index,
                "candidate_count": 3,
                "generation_status": "planned",
                "generation_error": "",
                "text_safety": {
                    "overlay_required": image_need.get("text_safe_area_required", True),
                    "status": "required" if image_need.get("text_safe_area_required", True) else "not_required",
                },
                "review_metadata": {
                    "channel_purpose": deliverable.get("purpose", ""),
                    "copy_intent": deliverable.get("copy_intent", ""),
                    "visual_need": deliverable.get("visual_need", ""),
                    "reference_asset": reference_trace,
                    "reference_direction": _reference_direction_trace(reference_research),
                },
                "status": "planned",
            })

        groups.append({
            "group_id": group_id,
            "stage_id": STAGE_ID,
            "scope": "deliverable_visual_need",
            "deliverable_id": image_need["deliverable_id"],
            "visual_role": image_need.get("visual_role", "key_visual"),
            "candidate_ids": candidate_ids,
            "regenerate_command": f"python3 scripts/workflow.py --run <run-dir> --stage 04_visual_candidates --mode regenerate --group {group_id}",
        })

    return {
        "stage": STAGE_ID,
        "event_id": content_plan["event_id"],
        "visual_plan": {
            "event_id": content_plan["event_id"],
            "engine": "comfyui",
            "strategy": "Translate content-plan image needs into ComfyUI-ready candidate requests with deliverable-level traceability.",
            "source_strategy": content_plan.get("strategy_summary", {}),
            "reference_manifest": _reference_manifest_summary(reference_manifest or {}),
            "reference_research": _reference_research_summary(reference_research),
            "reference_assets": [_reference_trace(asset) for asset in reference_assets],
            "reference_direction": _reference_direction_trace(reference_research),
            "product_source": _product_trace(product_profile),
            "visual_requirements": visual_requirements,
            "issues": issues,
            "requested_group": requested_group,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "prompts": prompts,
        "regeneration_groups": groups,
        "candidates": candidates,
    }


def materialize_previews(
    run_dir: Path,
    stage_output: dict[str, Any],
    requested_group: str | None = None,
) -> dict[str, Any]:
    generation_mode = _generation_mode()
    materialized_at = datetime.now(timezone.utc).isoformat()
    prompt_by_id = {prompt["prompt_id"]: prompt for prompt in stage_output["prompts"]}
    existing_by_id = _existing_candidates_by_id(run_dir) if requested_group else {}
    candidates = []

    for candidate in stage_output["candidates"]:
        if requested_group and candidate["regeneration_group"] != requested_group:
            candidates.append(existing_by_id.get(candidate["candidate_id"], candidate))
            continue

        prompt = prompt_by_id.get(candidate["source_prompt_id"], {})
        output_path = run_dir / candidate["preview_path"]
        result = _materialize_candidate_preview(
            output_path=output_path,
            candidate=candidate,
            prompt=prompt,
            generation_mode=generation_mode,
        )
        updated = dict(candidate)
        updated.update(result)
        updated["selection_blockers"] = _selection_blockers(updated)
        updated["materialized_at"] = materialized_at
        candidates.append(updated)

    return {
        "generation_mode": generation_mode,
        "materialized_at": materialized_at,
        "candidates": candidates,
    }


def build_generation_quality(run_dir: Path, stage_output: dict[str, Any]) -> dict[str, Any]:
    prompts_by_candidate = {
        prompt.get("candidate_id"): prompt
        for prompt in stage_output.get("prompts", [])
        if prompt.get("candidate_id")
    }
    candidate_reports = []
    for candidate in stage_output.get("candidates", []):
        prompt = prompts_by_candidate.get(candidate.get("candidate_id"), {})
        output_rel = candidate.get("output_path") or candidate.get("image_path") or candidate.get("preview_path") or ""
        output_path = run_dir / output_rel if output_rel else None
        reference_direction = prompt.get("reference_direction") or candidate.get("review_metadata", {}).get("reference_direction") or {}
        reference_checks = _reference_direction_checks(prompt, reference_direction)
        image_info = _image_file_info(output_path) if output_path else {"exists": False}
        candidate_reports.append({
            "candidate_id": candidate.get("candidate_id", ""),
            "deliverable_id": candidate.get("deliverable_id", ""),
            "group_id": candidate.get("regeneration_group", ""),
            "regeneration_group": candidate.get("regeneration_group", ""),
            "workflow_preset": candidate.get("workflow_preset", ""),
            "generation_mode": candidate.get("generation_mode", stage_output.get("visual_plan", {}).get("generation_mode", "")),
            "generation_status": candidate.get("generation_status", ""),
            "generation_error": candidate.get("generation_error", ""),
            "output_path": output_rel,
            "image": image_info,
            "reference_direction": reference_direction,
            "reference_direction_checks": reference_checks,
            "comfyui_submission": _quality_submission_trace(candidate.get("comfyui_submission", {})),
        })

    generated = [item for item in candidate_reports if item["generation_status"] == "generated"]
    failed = [item for item in candidate_reports if item["generation_status"] == "failed"]
    reference_applied = [
        item for item in candidate_reports
        if item["reference_direction_checks"].get("has_reference_direction")
        and item["reference_direction_checks"].get("positive_prompt_has_reference_hints")
    ]
    return {
        "stage": STAGE_ID,
        "event_id": stage_output.get("event_id", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_mode": stage_output.get("visual_plan", {}).get("generation_mode", ""),
        "materialized_group": stage_output.get("visual_plan", {}).get("materialized_group", ""),
        "summary": {
            "candidate_count": len(candidate_reports),
            "generated_count": len(generated),
            "failed_count": len(failed),
            "reference_direction_applied_count": len(reference_applied),
            "all_generated": len(generated) == len(candidate_reports) if candidate_reports else False,
            "all_reference_direction_applied": len(reference_applied) == len(candidate_reports) if candidate_reports else False,
        },
        "candidates": candidate_reports,
    }


def _reference_direction_checks(prompt: dict[str, Any], reference_direction: dict[str, Any]) -> dict[str, Any]:
    positive = str(prompt.get("positive_prompt") or "")
    negative = str(prompt.get("negative_prompt") or "")
    prompt_hints = _as_text_list(reference_direction.get("promptHints"))
    negative_hints = _as_text_list(reference_direction.get("negativePromptHints"))
    avoid_keywords = _as_text_list(reference_direction.get("avoidKeywords"))
    return {
        "has_reference_direction": any(bool(reference_direction.get(key)) for key in [
            "moodKeywords",
            "compositionKeywords",
            "lightingKeywords",
            "colorPalette",
            "materialTexture",
            "promptHints",
            "selectedReferences",
        ]),
        "positive_prompt_has_reference_hints": (
            "reference prompt hints:" in positive
            or any(hint and hint in positive for hint in prompt_hints)
        ),
        "negative_prompt_has_avoid_keywords": any(item and item in negative for item in [*avoid_keywords, *negative_hints]),
        "prompt_hint_count": len(prompt_hints),
        "negative_hint_count": len(negative_hints),
    }


def _quality_submission_trace(submission: dict[str, Any]) -> dict[str, Any]:
    if not submission:
        return {}
    return {
        "status": submission.get("status", ""),
        "target": submission.get("target", ""),
        "prompt_id": submission.get("prompt_id", ""),
        "workflow_preset": submission.get("workflow_preset", ""),
        "comfyui_prompt_id": submission.get("comfyui_prompt_id", ""),
        "outputs": submission.get("outputs", []),
    }


def _image_file_info(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists() or not path.is_file():
        return {"exists": False}
    info = {
        "exists": True,
        "file_size": path.stat().st_size,
        "width": 0,
        "height": 0,
        "format": path.suffix.lower().lstrip("."),
    }
    if path.suffix.lower() == ".png":
        try:
            with path.open("rb") as f:
                header = f.read(24)
            if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
                info["width"], info["height"] = struct.unpack(">II", header[16:24])
        except OSError:
            pass
    return info


def _existing_candidates_by_id(run_dir: Path) -> dict[str, dict[str, Any]]:
    manifest_path = run_dir / STAGE_ID / "candidate-manifest.json"
    if not manifest_path.exists():
        return {}
    manifest = read_json(manifest_path, default={"candidates": []})
    return {
        candidate.get("candidate_id"): candidate
        for candidate in manifest.get("candidates", [])
        if candidate.get("candidate_id")
    }


def _materialize_candidate_preview(
    output_path: Path,
    candidate: dict[str, Any],
    prompt: dict[str, Any],
    generation_mode: str,
) -> dict[str, Any]:
    try:
        preset_path(prompt.get("workflow_preset", DEFAULT_WORKFLOW_PRESET))
        payload = build_payload(prompt)
        submission = ComfyUIClient().submit(ComfyUIJob(
            prompt_id=prompt.get("prompt_id", candidate["candidate_id"]),
            workflow_preset=prompt.get("workflow_preset", DEFAULT_WORKFLOW_PRESET),
            payload=payload,
        ))

        if generation_mode == "placeholder":
            _write_placeholder_png(output_path, candidate, prompt)
            generated = output_path.exists()
            return {
                "preview_path": str(output_path.relative_to(output_path.parents[2])),
                "image_path": str(output_path.relative_to(output_path.parents[2])),
                "output_path": str(output_path.relative_to(output_path.parents[2])),
                "generation_status": "placeholder" if generated else "failed",
                "generation_error": "" if generated else "placeholder writer did not create a file",
                "generation_mode": generation_mode,
                "comfyui_submission": submission,
                "status": "preview_placeholder" if generated else "failed",
            }

        if generation_mode == "live":
            result = ComfyUIClient().run_image_job(ComfyUIJob(
                prompt_id=prompt.get("prompt_id", candidate["candidate_id"]),
                workflow_preset=prompt.get("workflow_preset", DEFAULT_WORKFLOW_PRESET),
                payload=payload,
            ))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(result["image_bytes"])
            return {
                "preview_path": str(output_path.relative_to(output_path.parents[2])),
                "image_path": str(output_path.relative_to(output_path.parents[2])),
                "output_path": str(output_path.relative_to(output_path.parents[2])),
                "generation_status": "generated",
                "generation_error": "",
                "generation_mode": generation_mode,
                "comfyui_submission": {
                    "status": result["status"],
                    "target": result["target"],
                    "prompt_id": result["prompt_id"],
                    "workflow_preset": result["workflow_preset"],
                    "comfyui_prompt_id": result["comfyui_prompt_id"],
                    "outputs": result["outputs"],
                },
                "status": "generated",
            }

        return {
            "generation_status": "failed",
            "generation_error": f"Unsupported COMFYUI_GENERATION_MODE: {generation_mode}",
            "generation_mode": generation_mode,
            "comfyui_submission": submission,
            "status": "failed",
        }
    except Exception as exc:
        return {
            "generation_status": "failed",
            "generation_error": str(exc),
            "generation_mode": generation_mode,
            "status": "failed",
        }


def _write_placeholder_png(output_path: Path, candidate: dict[str, Any], prompt: dict[str, Any]) -> None:
    width, height = _preview_dimensions(candidate.get("ratio", "1:1"))
    digest = hashlib.sha256(candidate["candidate_id"].encode("utf-8")).digest()
    base = (digest[0], digest[1], digest[2])
    accent = (digest[3], digest[4], digest[5])
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            t = (x / max(width - 1, 1) + y / max(height - 1, 1)) / 2
            r = int(base[0] * (1 - t) + accent[0] * t)
            g = int(base[1] * (1 - t) + accent[1] * t)
            b = int(base[2] * (1 - t) + accent[2] * t)
            if _in_safe_area_frame(x, y, width, height):
                r = min(255, int(r * 0.75 + 255 * 0.25))
                g = min(255, int(g * 0.75 + 255 * 0.25))
                b = min(255, int(b * 0.75 + 255 * 0.25))
            row.extend([r, g, b])
        rows.append(b"\x00" + bytes(row))

    raw = b"".join(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_png_bytes(width, height, raw))


def _png_bytes(width: int, height: int, raw: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    return b"".join([
        b"\x89PNG\r\n\x1a\n",
        chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
        chunk(b"IDAT", zlib.compress(raw, 9)),
        chunk(b"IEND", b""),
    ])


def _preview_dimensions(ratio: str) -> tuple[int, int]:
    return {
        "1:1": (512, 512),
        "4:5": (512, 640),
        "4:3": (640, 480),
        "16:9": (640, 360),
    }.get(ratio, (512, 512))


def _in_safe_area_frame(x: int, y: int, width: int, height: int) -> bool:
    margin_x = max(24, width // 12)
    margin_y = max(24, height // 12)
    return margin_x <= x <= width - margin_x and margin_y <= y <= height - margin_y


def _generation_mode() -> str:
    mode = os.environ.get("COMFYUI_GENERATION_MODE", "placeholder").strip().lower()
    return mode if mode in {"placeholder", "live"} else "placeholder"


def _workflow_preset(image_need: dict[str, Any], product_profile: dict[str, Any] | None = None) -> str:
    product_profile = product_profile or {}
    recommended = product_profile.get("recommended_workflows") or []
    explicit = image_need.get("workflow_preset")
    if explicit and _is_supported_workflow(str(explicit)):
        return str(explicit)
    category_workflow = choose_brand_workflow(
        product_profile.get("category", ""),
        visual_role=image_need.get("visual_role", ""),
        channel_id=image_need.get("channel_id", ""),
    )
    if category_workflow:
        return category_workflow
    for workflow_id in recommended:
        if workflow_id and _is_supported_workflow(str(workflow_id)):
            return workflow_id
    return DEFAULT_WORKFLOW_PRESET


def _is_supported_workflow(workflow_id: str) -> bool:
    if workflow_id in {"product_locked_ad_background_v1", DEFAULT_WORKFLOW_PRESET, "campaign_keyvisual"}:
        return True
    try:
        preset_path(workflow_id)
        return True
    except Exception:
        return False


def _workflow_config(workflow_id: str) -> dict[str, Any]:
    if workflow_id == DEFAULT_WORKFLOW_PRESET:
        return {
            "sampler": "heun",
            "scheduler": "beta",
            "steps": 8,
            "cfg_scale": 1.0,
            "denoise": 1.0,
            "workflow_path": "local",
        }
    try:
        return load_brand_workflow_config(workflow_id)
    except Exception:
        return {}


def _selection_blockers(candidate: dict[str, Any]) -> list[str]:
    blockers = []
    if candidate.get("generation_status") != "generated":
        blockers.append("generation_failed")
    if candidate.get("generation_mode") != "live":
        blockers.append("not_live_generation")
    if candidate.get("text_safety", {}).get("overlay_required") and not candidate.get("preview_path"):
        blockers.append("missing_text_safe_preview")
    return blockers


def _load_reference_manifest(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "references" / "reference-manifest.json"
    if not path.exists():
        return {}
    return read_json(path, default={})


def _load_reference_research(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "03_reference_research" / "reference-research.json"
    if not path.exists():
        return {}
    return read_json(path, default={})


def _load_product_profile(event_input: dict[str, Any]) -> dict[str, Any]:
    try:
        return load_product_from_event(event_input) or {}
    except Exception as exc:
        return {
            "library_id": event_input.get("productLibraryId") or "",
            "load_error": str(exc),
        }


def _input_image_source(
    image_need: dict[str, Any],
    product_profile: dict[str, Any],
    reference_research: dict[str, Any],
) -> dict[str, str]:
    product_image = product_profile.get("main_image_asset", {}).get("comfyui_name") or image_need.get("product_image") or image_need.get("base_image") or ""
    product_image_path = product_profile.get("main_image_asset", {}).get("absolute_path", "")
    base_image = image_need.get("base_image") or product_image or "qwen_image_edit_1024.png"

    if _is_bullion_investment_profile(reference_research) and _is_contaminated_qwen_fallback(product_image or base_image):
        fallback_path = _bullion_fallback_product_path()
        if fallback_path:
            return {
                "base_image": fallback_path.name,
                "product_image": fallback_path.name,
                "product_image_path": str(fallback_path),
            }
        return {
            "base_image": "product_input.png",
            "product_image": "product_input.png",
            "product_image_path": "",
        }

    return {
        "base_image": base_image or "qwen_image_edit_1024.png",
        "product_image": product_image or base_image or "qwen_image_edit_1024.png",
        "product_image_path": product_image_path,
    }


def _is_contaminated_qwen_fallback(image_name: str) -> bool:
    return str(image_name or "").strip().lower() in {"", "qwen_image_edit_1024.png"}


def _bullion_fallback_product_path() -> Path | None:
    candidates = [
        ROOT / "0_자동화 샘플 이미지" / "금_은 누끼" / "eagle.png",
        ROOT / "0_자동화 샘플 이미지" / "금_은 누끼" / "1-oz-silver-austrian-philharmonic-coin-tubes-red-cap_151551_Obv.png",
        ROOT / "0_자동화 샘플 이미지" / "금_은 누끼" / "2025-austria-1-oz-silver-philharmonic-bu_302116_obv.jpg",
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def _product_trace(product_profile: dict[str, Any]) -> dict[str, Any]:
    if not product_profile or not product_profile.get("library_id"):
        return {}
    return {
        "product_id": product_profile.get("library_id", ""),
        "brand_name": product_profile.get("brand_name", ""),
        "product_name": product_profile.get("product_name", ""),
        "category": product_profile.get("category", ""),
        "main_image": product_profile.get("main_image_asset", {}),
        "mask_image": product_profile.get("mask_image_asset", {}),
        "recommended_workflows": product_profile.get("recommended_workflows", []),
        "safety_rule": "product_source_is_locked_original_asset",
    }


def _negative_prompt(product_profile: dict[str, Any], reference_research: dict[str, Any] | None = None) -> str:
    reference_research = reference_research or {}
    base = [
        "unsupported claims",
        "unreadable text",
        "cluttered layout",
        "distorted logo",
        "distorted product shape",
        "changed label placement",
        "changed package proportions",
        "fake label text",
        "fake text",
        "fake typography",
        "broken korean text",
        "readable text",
        "unreadable letters",
        "random product packaging",
    ]
    if _is_bullion_investment_profile(reference_research):
        base.extend(BULLION_HARD_NEGATIVE_TERMS)
    base.extend(str(item) for item in product_profile.get("forbidden", []) if item)
    base.extend(_as_text_list(reference_research.get("avoidKeywords")))
    base.extend(_as_text_list(reference_research.get("negativePromptHints")))
    return ", ".join(dict.fromkeys(base))


def _selected_reference_assets(reference_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    assets = [
        asset for asset in reference_manifest.get("assets", [])
        if asset.get("status") == "selected" and asset.get("relative_path")
    ]
    return sorted(
        assets,
        key=lambda asset: (
            -float(asset.get("score") or 0),
            str(asset.get("asset_id") or ""),
        ),
    )


def _reference_for_variant(
    reference_assets: list[dict[str, Any]],
    image_need: dict[str, Any],
    variant: int,
) -> dict[str, Any] | None:
    if not reference_assets:
        return None
    channel_id = str(image_need.get("channel_id") or "").lower()
    role = str(image_need.get("visual_role") or "").lower()
    scored = []
    for asset in reference_assets:
        text = " ".join([
            str(asset.get("query", "")),
            str(asset.get("source_id", "")),
            str(asset.get("relative_path", "")),
        ]).lower()
        fit = 0
        if channel_id and channel_id in text:
            fit += 2
        if role and role in text:
            fit += 1
        fit += float(asset.get("score") or 0) / 100
        scored.append((fit, asset))
    scored.sort(key=lambda item: item[0], reverse=True)
    ordered = [asset for _, asset in scored]
    return ordered[(variant - 1) % len(ordered)]


def _reference_trace(reference_asset: dict[str, Any] | None) -> dict[str, Any]:
    if not reference_asset:
        return {}
    return {
        "asset_id": reference_asset.get("asset_id", ""),
        "relative_path": reference_asset.get("relative_path", ""),
        "original_path": reference_asset.get("original_path", ""),
        "source_id": reference_asset.get("source_id", ""),
        "query": reference_asset.get("query", ""),
        "score": reference_asset.get("score", 0),
        "quality_score": reference_asset.get("quality_score", reference_asset.get("score", 0)),
        "text_relevance_score": reference_asset.get("text_relevance_score", 0),
        "review_decision": reference_asset.get("review_decision", ""),
        "review_score": reference_asset.get("review_score", 0),
    }


def _reference_manifest_summary(reference_manifest: dict[str, Any]) -> dict[str, Any]:
    if not reference_manifest:
        return {
            "status": "missing",
            "asset_count": 0,
            "selected_count": 0,
            "path": "references/reference-manifest.json",
        }
    selected_count = len(_selected_reference_assets(reference_manifest))
    return {
        "status": "loaded",
        "asset_count": reference_manifest.get("asset_count", 0),
        "selected_count": selected_count,
        "selection_method": (
            reference_manifest.get("selection", {}).get("selection_method")
            or reference_manifest.get("auto_collection", {}).get("selection_method")
            or ""
        ),
        "path": "references/reference-manifest.json",
        "updated_at": reference_manifest.get("updated_at", ""),
    }


def _reference_research_summary(reference_research: dict[str, Any]) -> dict[str, Any]:
    if not reference_research:
        return {
            "status": "missing",
            "path": "03_reference_research/reference-research.json",
        }
    return {
        "status": reference_research.get("status", "loaded"),
        "path": "03_reference_research/reference-research.json",
        "selected_reference_count": reference_research.get("selected_reference_count", 0),
        "eventProfile": reference_research.get("eventProfile", {}),
        "qualityFilter": reference_research.get("qualityFilter", {}),
        "prompt_hint_count": len(_as_text_list(reference_research.get("promptHints"))),
        "negative_prompt_hint_count": len(_as_text_list(reference_research.get("negativePromptHints"))),
        "moodKeywords": _as_text_list(reference_research.get("moodKeywords")),
        "compositionKeywords": _as_text_list(reference_research.get("compositionKeywords")),
        "lightingKeywords": _as_text_list(reference_research.get("lightingKeywords")),
        "colorPalette": _as_text_list(reference_research.get("colorPalette")),
        "materialTexture": _as_text_list(reference_research.get("materialTexture")),
    }


def _reference_direction_trace(reference_research: dict[str, Any]) -> dict[str, Any]:
    if not reference_research:
        return {}
    bullion_profile = _is_bullion_investment_profile(reference_research)
    prompt_hints = _as_text_list(reference_research.get("promptHints"))
    if bullion_profile:
        prompt_hints = [
            cleaned
            for hint in prompt_hints
            if (cleaned := _sanitize_bullion_positive_prompt(hint))
        ]
    return {
        "eventProfile": reference_research.get("eventProfile", {}),
        "qualityFilter": reference_research.get("qualityFilter", {}),
        "moodKeywords": _as_text_list(reference_research.get("moodKeywords")),
        "compositionKeywords": _as_text_list(reference_research.get("compositionKeywords")),
        "lightingKeywords": _as_text_list(reference_research.get("lightingKeywords")),
        "colorPalette": _as_text_list(reference_research.get("colorPalette")),
        "materialTexture": _as_text_list(reference_research.get("materialTexture")),
        "avoidKeywords": _as_text_list(reference_research.get("avoidKeywords")),
        "promptHints": prompt_hints,
        "negativePromptHints": _as_text_list(reference_research.get("negativePromptHints")),
        "selectedReferences": reference_research.get("selectedReferences", []),
    }


def build_notes(stage_output: dict[str, Any], group: str | None = None) -> str:
    lines = [
        "# Visual Candidate Notes",
        "",
        "This file summarizes planned ComfyUI candidate generation. `candidate-manifest.json` is the canonical source for selection and regeneration.",
        "",
        f"- Requested group: {group or 'all'}",
        f"- Regeneration groups: {len(stage_output['regeneration_groups'])}",
        f"- Candidates: {len(stage_output['candidates'])}",
        "",
        "## Regenerate",
    ]
    for item in stage_output["regeneration_groups"]:
        lines.append(f"- `{item['group_id']}`: `{item['regenerate_command']}`")
    lines.append("")
    return "\n".join(lines)


def _group_id(image_need: dict[str, Any]) -> str:
    return f"{image_need['deliverable_id']}__{image_need.get('visual_role', 'visual')}"


def _positive_prompt(
    brief: dict[str, Any],
    content_plan: dict[str, Any],
    deliverable: dict[str, Any],
    image_need: dict[str, Any],
    variant: int,
    reference_asset: dict[str, Any] | None = None,
    reference_research: dict[str, Any] | None = None,
    product_profile: dict[str, Any] | None = None,
) -> str:
    product_profile = product_profile or {}
    reference_research = reference_research or {}
    tone = brief.get("content_direction", {}).get("tone", "")
    product_tone = ", ".join(product_profile.get("tone", []))
    fragments = product_profile.get("prompt_fragments", {})
    product_name = product_profile.get("product_name") or brief.get("productOrService") or ""
    bullion_profile = _is_bullion_investment_profile(reference_research)
    if bullion_profile:
        product_lock = "Use only gold bullion, gold bars, coins, safe deposit, premium finance, or consultation desk cues as subject matter."
    else:
        product_lock = fragments.get(
            "product_lock",
            "Keep the original product shape, label placement, cap, package proportions, material, and color accents unchanged.",
        )
    reference_use = fragments.get(
        "reference_use",
        "Use reference images only for mood, lighting, background, color, and composition.",
    )
    message = deliverable.get("copy_intent") or (brief.get("core_messages") or [""])[0]
    purpose = deliverable.get("purpose", "")
    visual_need = deliverable.get("visual_need", "")
    strategy = content_plan.get("strategy_summary", {}).get("planning_thesis", "")
    reference_hint = _reference_prompt_hint(reference_asset)
    research_hint = _reference_research_prompt_hint(reference_research)
    prompt = (
        f"Event campaign visual, {image_need.get('visual_role', 'key visual')} for {image_need.get('channel_id', 'channel')}, "
        f"product source: {product_name}, {product_lock} "
        f"channel purpose: {purpose}, message priority: {message}, visual need: {visual_need}, "
        f"strategy context: {strategy}, brand tone: {tone}, product tone: {product_tone}, "
        f"{reference_use} variant {variant}, clean composition, text-safe negative space"
        f", poster layout with empty text area, blank space for Korean headline, no readable text, no fake typography"
        f"{research_hint}"
        f"{reference_hint}"
    )
    if bullion_profile:
        prompt = _sanitize_bullion_positive_prompt(prompt)
    return prompt


def _reference_prompt_hint(reference_asset: dict[str, Any] | None) -> str:
    if not reference_asset:
        return ""
    parts = []
    query = str(reference_asset.get("query") or "").strip()
    reason = str(reference_asset.get("text_relevance_reason") or reference_asset.get("reason") or "").strip()
    if query:
        parts.append(f"reference search intent: {query}")
    if reason:
        parts.append(f"reference selection evidence: {reason}")
    path = str(reference_asset.get("relative_path") or "").strip()
    if path:
        parts.append(f"selected reference asset: {path}")
    return ", " + ", ".join(parts) if parts else ""


def _reference_research_prompt_hint(reference_research: dict[str, Any]) -> str:
    if not reference_research:
        return ""
    parts = []
    bullion_profile = _is_bullion_investment_profile(reference_research)
    prompt_hints = _as_text_list(reference_research.get("promptHints"))
    if bullion_profile:
        prompt_hints = [
            cleaned
            for hint in prompt_hints
            if (cleaned := _sanitize_bullion_positive_prompt(hint))
        ]
    if prompt_hints:
        parts.append("reference prompt hints: " + " | ".join(prompt_hints))
        return ", " + ", ".join(parts)
    for label, key in [
        ("reference mood", "moodKeywords"),
        ("reference composition", "compositionKeywords"),
        ("reference lighting", "lightingKeywords"),
        ("reference color palette", "colorPalette"),
        ("reference material texture", "materialTexture"),
    ]:
        values = _as_text_list(reference_research.get(key))
        if values:
            parts.append(f"{label}: {', '.join(values)}")
    parts.extend(_as_text_list(reference_research.get("promptHints")))
    return ", " + ", ".join(parts) if parts else ""


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _is_bullion_investment_profile(reference_research: dict[str, Any]) -> bool:
    profile = reference_research.get("eventProfile") or {}
    quality = reference_research.get("qualityFilter") or {}
    return (
        profile.get("category") == "bullion_investment"
        or quality.get("profile") == "bullion_investment_strict_v1"
    )


def _sanitize_bullion_positive_prompt(text: str) -> str:
    cleaned = str(text or "")
    replacements = {
        "premium financial consultation campaign, not a cute event illustration": "premium financial consultation campaign",
        "not a cute event illustration": "premium financial consultation campaign",
        "random package box": "off-category object",
        "package box": "off-category object",
        "wine bottle": "off-category object",
    }
    for source, target in replacements.items():
        cleaned = _replace_case_insensitive(cleaned, source, target)
    for term in BULLION_BLOCKED_POSITIVE_TERMS:
        cleaned = _replace_case_insensitive(cleaned, term, "")
    cleaned = " ".join(cleaned.replace(" ,", ",").replace(",,", ",").split())
    return cleaned.strip(" ,")


def _replace_case_insensitive(text: str, source: str, target: str) -> str:
    lower = text.lower()
    source_lower = source.lower()
    start = 0
    chunks = []
    while True:
        index = lower.find(source_lower, start)
        if index == -1:
            chunks.append(text[start:])
            break
        chunks.append(text[start:index])
        chunks.append(target)
        start = index + len(source)
    return "".join(chunks)


def _headline(brief: dict[str, Any], deliverable: dict[str, Any], variant: int) -> str:
    phrases = brief.get("required_phrases") or brief.get("requiredPhrases") or []
    message = deliverable.get("copy_intent") or (brief.get("core_messages") or [""])[0]
    if phrases:
        return f"{phrases[0]}\n{_compact_korean(message, 10)}"
    return _compact_korean(message or brief.get("event_name") or brief.get("eventName") or "이벤트 안내", 12)


def _subheadline(brief: dict[str, Any], deliverable: dict[str, Any]) -> str:
    value = deliverable.get("purpose") or brief.get("purpose") or "지금 확인해 보세요"
    return _compact_korean(value, 18)


def _cta(brief: dict[str, Any], deliverable: dict[str, Any]) -> str:
    phrases = brief.get("required_phrases") or brief.get("requiredPhrases") or []
    if phrases:
        return phrases[0]
    return "자세히 보기"


def _compact_korean(value: str, max_chars: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip()


def _message_priority(content_plan: dict[str, Any], deliverable: dict[str, Any]) -> str:
    return deliverable.get("copy_intent") or (
        (content_plan.get("brief", {}).get("core_messages") or [""])[0]
    )


def _seed_for(prompt_id: str) -> int:
    return int(hashlib.sha256(prompt_id.encode("utf-8")).hexdigest()[:8], 16)
