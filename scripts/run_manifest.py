#!/usr/bin/env python3
"""Build console-friendly run manifests from existing pipeline artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"


STAGE_LABELS = {
    "01_event_brief": "01 Brief",
    "02_content_planning": "02 Plan",
    "03_reference_research": "03 Reference",
    "04_visual_candidates": "04 Visual",
    "05_admin_selection": "05 Select",
    "reference_collection": "03 Reference",
    "qwen_vl_review": "Qwen Review",
    "03_visual_candidates": "04 Visual",
    "04_admin_selection": "05 Select",
    "06_qa_packaging": "06 QA",
    "07_asset_archive": "07 Archive",
}


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def count_stage_errors(run_dir: Path) -> int:
    error_log = run_dir / "logs" / "stage-errors.log"
    if not error_log.exists():
        return 0
    return len([line for line in error_log.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()])


def image_url(run_dir: Path, relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    return f"/assets/{run_dir.name}/{normalized}"


def find_preview_images(run_dir: Path, limit: int = 8) -> list[dict[str, str]]:
    preview_dir = run_dir / "03_visual_candidates" / "previews"
    if not preview_dir.exists():
        return []
    images = []
    for path in sorted(preview_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            relative_path = rel(path, run_dir)
            images.append({"name": path.name, "relative_path": relative_path, "url": image_url(run_dir, relative_path)})
        if len(images) >= limit:
            break
    return images


def folder_payload(run_dir: Path, relative_path: str) -> dict[str, str]:
    path = (run_dir / relative_path).resolve()
    return {
        "label": relative_path.replace("/", "\\"),
        "relative_path": relative_path,
        "absolute_path": str(path),
    }


def normalize_reference(run_dir: Path, item: dict[str, Any]) -> dict[str, Any]:
    relative_path = str(item.get("relative_path") or "")
    original_path = str(item.get("original_path") or "")
    if relative_path and not (run_dir / relative_path).exists() and original_path:
        relative_path = original_path
    if not relative_path:
        relative_path = original_path
    qwen = item.get("qwen_review") or {}
    return {
        "asset_id": item.get("asset_id") or item.get("candidate_id") or item.get("path") or "reference",
        "status": item.get("review_decision") or qwen.get("decision") or item.get("status") or "unknown",
        "score": item.get("review_score") or qwen.get("score") or item.get("score"),
        "brand_fit": item.get("category_fit") or qwen.get("category_fit"),
        "event_fit": item.get("event_fit") or qwen.get("event_fit"),
        "copy_space": item.get("copy_space") or qwen.get("copy_space"),
        "reason": qwen.get("reason") or item.get("reason") or item.get("text_relevance_reason") or "",
        "risk": qwen.get("risk") or "",
        "positive_tags": qwen.get("positive_tags") or [],
        "negative_tags": qwen.get("negative_tags") or [],
        "query": item.get("query") or "",
        "relative_path": relative_path,
        "url": image_url(run_dir, relative_path) if relative_path else "",
    }


def normalize_candidate(run_dir: Path, item: dict[str, Any]) -> dict[str, Any]:
    preview_path = str(item.get("preview_path") or item.get("image_path") or "")
    image_path = str(item.get("image_path") or preview_path)
    return {
        "candidate_id": item.get("candidate_id") or "candidate",
        "deliverable_id": item.get("deliverable_id") or "",
        "regeneration_group": item.get("regeneration_group") or "",
        "visual_role": item.get("visual_role") or "",
        "channel_id": item.get("channel_id") or "",
        "ratio": item.get("ratio") or "",
        "generation_status": item.get("generation_status") or item.get("status") or "unknown",
        "generation_mode": item.get("generation_mode") or "",
        "generation_error": item.get("generation_error") or "",
        "selection_blockers": item.get("selection_blockers") or [],
        "preview_path": preview_path,
        "image_path": image_path,
        "output_path": item.get("output_path") or image_path,
        "product_id": item.get("product_id") or "",
        "workflow_id": item.get("workflow_id") or item.get("workflow_preset") or "",
        "prompt_id": item.get("prompt_id") or item.get("source_prompt_id") or "",
        "seed": item.get("seed"),
        "reference_images": item.get("reference_images") or [],
        "product_source": item.get("product_source") or {},
        "url": image_url(run_dir, preview_path) if preview_path else "",
        "comfyui_submission": item.get("comfyui_submission") or {},
        "materialized_at": item.get("materialized_at") or "",
    }


def load_references(run_dir: Path) -> list[dict[str, Any]]:
    reviewed = read_json(run_dir / "references" / "qwen-reviewed-candidates.json", {"reviewed": []}).get("reviewed", [])
    manifest_assets = read_json(run_dir / "references" / "reference-manifest.json", {"assets": []}).get("assets", [])
    by_id: dict[str, dict[str, Any]] = {}
    for item in reviewed + manifest_assets:
        normalized = normalize_reference(run_dir, item)
        by_id[str(normalized["asset_id"])] = normalized
    return list(by_id.values())


def load_candidates(run_dir: Path) -> list[dict[str, Any]]:
    manifest = read_json(run_dir / "03_visual_candidates" / "candidate-manifest.json", {"candidates": []})
    return [normalize_candidate(run_dir, item) for item in manifest.get("candidates", [])]


def load_prompts(run_dir: Path) -> list[dict[str, Any]]:
    prompts = read_json(run_dir / "03_visual_candidates" / "image-prompts.json", {"prompts": []}).get("prompts", [])
    normalized = []
    for item in prompts:
        normalized.append({
            "prompt_id": item.get("prompt_id") or item.get("candidate_id") or "prompt",
            "candidate_id": item.get("candidate_id") or "",
            "deliverable_id": item.get("deliverable_id") or "",
            "channel_id": item.get("channel_id") or "",
            "purpose": item.get("visual_role") or item.get("deliverable_id") or "",
            "model": item.get("model") or item.get("workflow_preset") or "",
            "ratio": item.get("aspect_ratio") or item.get("ratio") or "",
            "reference_asset": item.get("reference_asset") or {},
            "positive_prompt": item.get("positive_prompt") or "",
            "negative_prompt": item.get("negative_prompt") or "",
            "product_id": item.get("product_id") or "",
            "product_source": item.get("product_source") or {},
            "reference_images": item.get("reference_images") or [],
        })
    return normalized


def derive_status(run_status: dict[str, Any], reference_count: int, prompt_count: int) -> tuple[str, str]:
    stage_status = run_status.get("stage_status", {})
    if stage_status.get("07_asset_archive") == "done_no_assets":
        return "archived_no_assets", "Archive complete, no approved assets"
    if stage_status.get("07_asset_archive") in {"done", "approved"}:
        return "archived", "Archive complete"
    if stage_status.get("06_qa_packaging") in {"done", "approved", "review_pending"}:
        return "qa_ready", "Review QA and package"
    if stage_status.get("05_admin_selection") in {"done", "approved", "review_pending"} or stage_status.get("04_admin_selection") in {"done", "approved", "review_pending"}:
        return "assets_selected", "Build output package"
    if prompt_count:
        return "prompt_ready", "Generate image candidates / human selection"
    if reference_count:
        return "reference_ready", "Review selected references"
    current = run_status.get("current_stage") or "01_event_brief"
    return str(run_status.get("run_state") or "created"), f"Continue {current}"


def completed_steps(run_status: dict[str, Any], reference_count: int, reviewed_count: int, prompt_count: int) -> list[str]:
    completed = [
        stage
        for stage, state in (run_status.get("stage_status") or {}).items()
        if state in {"done", "approved", "review_pending", "qa_pending"}
    ]
    if reference_count and "03_reference_research" not in completed:
        completed.append("03_reference_research")
    if reviewed_count:
        completed.append("qwen_vl_review")
    if prompt_count and "04_visual_candidates" not in completed and "03_visual_candidates" not in completed:
        completed.append("04_visual_candidates")
    return completed


def build_manifest(run_dir: Path) -> dict[str, Any]:
    event_input = read_json(run_dir / "event-input.json", {})
    brand_guide = read_json(run_dir / "brand-guide.json", {})
    run_status = read_json(run_dir / "run-status.json", {})
    reference_manifest = read_json(run_dir / "references" / "reference-manifest.json", {"assets": []})
    references = load_references(run_dir)
    candidates = load_candidates(run_dir)
    prompts = load_prompts(run_dir)

    selected_count = len([item for item in reference_manifest.get("assets", []) if item.get("status") == "selected"])
    rejected_count = len([item for item in references if item.get("status") == "rejected"])
    status, next_action = derive_status(run_status, selected_count or len(references), len(prompts))
    completed = completed_steps(run_status, selected_count or len(references), len(references), len(prompts))

    manifest = {
        "run_id": run_status.get("run_id") or run_dir.name,
        "run_dir": str(run_dir),
        "event_name": event_input.get("eventName") or event_input.get("name") or run_dir.name,
        "brand_name": brand_guide.get("brandName") or event_input.get("brandName") or "",
        "status": status,
        "current_step": run_status.get("current_stage") or run_status.get("run_state") or "created",
        "completed_steps": completed,
        "completed_step_labels": [STAGE_LABELS.get(step, step) for step in completed],
        "selected_reference_count": selected_count,
        "rejected_reference_count": rejected_count,
        "reference_count": len(references),
        "prompt_count": len(prompts),
        "candidate_count": len(candidates),
        "generated_image_count": len([item for item in candidates if item.get("generation_status") == "generated"]),
        "placeholder_image_count": len([item for item in candidates if item.get("generation_status") == "placeholder"]),
        "next_action": next_action,
        "has_errors": count_stage_errors(run_dir) > 0,
        "error_count": count_stage_errors(run_dir),
        "updated_at": run_status.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        "stage_status": run_status.get("stage_status") or {},
        "previews": find_preview_images(run_dir),
        "folders": {
            "run": folder_payload(run_dir, "."),
            "references": folder_payload(run_dir, "references"),
            "reference_candidates": folder_payload(run_dir, "references/candidates"),
            "selected_references": folder_payload(run_dir, "references/selected"),
            "generated_images": folder_payload(run_dir, "03_visual_candidates/previews"),
            "package": folder_payload(run_dir, "production-package"),
        },
        "paths": {
            "event_input": "event-input.json",
            "brand_guide": "brand-guide.json",
            "run_status": "run-status.json",
            "references": "references/qwen-reviewed-candidates.json",
            "prompts": "03_visual_candidates/image-prompts.json",
            "package": "production-package",
        },
    }
    return manifest


def write_manifest(run_dir: Path) -> dict[str, Any]:
    manifest = build_manifest(run_dir)
    write_json(run_dir / "run-manifest.json", manifest)
    return manifest


def build_all(write: bool = False) -> list[dict[str, Any]]:
    manifests = []
    if not RUNS_DIR.exists():
        return manifests
    for run_dir in sorted([path for path in RUNS_DIR.iterdir() if path.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True):
        if not (run_dir / "run-status.json").exists() and not (run_dir / "run-manifest.json").exists():
            continue
        manifests.append(write_manifest(run_dir) if write else build_manifest(run_dir))
    return manifests


def main() -> int:
    parser = argparse.ArgumentParser(description="Create run-manifest.json files for the local console.")
    parser.add_argument("--run", type=Path, help="One run directory to update.")
    parser.add_argument("--all", action="store_true", help="Update every run under runs/.")
    args = parser.parse_args()

    if args.run:
        print(json.dumps(write_manifest(args.run.resolve()), ensure_ascii=False, indent=2))
        return 0
    if args.all:
        print(json.dumps(build_all(write=True), ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
