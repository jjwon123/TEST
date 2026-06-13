#!/usr/bin/env python3
"""Verify 03_visual_candidates -> 04_admin_selection operational contracts."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json


PROMPT_FIELDS = {
    "positive_prompt",
    "negative_prompt",
    "ratio",
    "workflow_preset",
    "seed",
    "sampler",
    "model",
    "batch_size",
    "candidate_count",
}


def verify(run_dir: Path) -> list[str]:
    issues: list[str] = []
    content_plan = read_json(run_dir / "02_content_planning" / "content-plan.json", default={})
    visual_plan = read_json(run_dir / "03_visual_candidates" / "visual-plan.json", default={})
    prompts = read_json(run_dir / "03_visual_candidates" / "image-prompts.json", default={}).get("prompts", [])
    manifest = read_json(run_dir / "03_visual_candidates" / "candidate-manifest.json", default={})
    selected_assets = read_json(run_dir / "04_admin_selection" / "selected-assets.json", default={})

    if not content_plan:
        return ["missing content-plan.json"]
    if not visual_plan:
        return ["missing visual-plan.json"]
    if not manifest:
        return ["missing candidate-manifest.json"]
    if not selected_assets:
        return ["missing selected-assets.json"]

    image_needs = content_plan.get("image_needs", [])
    requirements = visual_plan.get("visual_requirements", [])
    if len(requirements) != len(image_needs):
        issues.append("visual_requirements count must match content-plan image_needs")

    for prompt in prompts:
        missing = sorted(field for field in PROMPT_FIELDS if field not in prompt)
        if missing:
            issues.append(f"prompt {prompt.get('prompt_id')} missing fields: {', '.join(missing)}")

    candidate_counts = Counter(item.get("deliverable_id") for item in manifest.get("candidates", []))
    for need in image_needs:
        deliverable_id = need.get("deliverable_id")
        if candidate_counts.get(deliverable_id, 0) < 3:
            issues.append(f"{deliverable_id} has fewer than 3 candidates")

    group_ids = {item.get("group_id") for item in manifest.get("regeneration_groups", [])}
    if not group_ids:
        issues.append("no regeneration groups recorded")
    for candidate in manifest.get("candidates", []):
        if candidate.get("regeneration_group") not in group_ids:
            issues.append(f"candidate {candidate.get('candidate_id')} has unknown regeneration_group")
        if "selection_blockers" not in candidate:
            issues.append(f"candidate {candidate.get('candidate_id')} missing selection_blockers")

    valid_decisions = {"selected", "rejected", "regenerate", "hold"}
    for item in selected_assets.get("selections", []):
        if item.get("decision") not in valid_decisions:
            issues.append(f"invalid selection decision: {item.get('decision')}")

    for request in selected_assets.get("regeneration_requests", []):
        if request.get("group_id") not in group_ids:
            issues.append(f"regeneration request references unknown group {request.get('group_id')}")
        if not request.get("workflow_command"):
            issues.append(f"regeneration request {request.get('group_id')} missing workflow_command")

    selected_by_deliverable = {
        item.get("deliverable_id"): item
        for item in selected_assets.get("selections", [])
        if item.get("decision") == "selected"
    }
    for deliverable in content_plan.get("deliverables", []):
        if deliverable.get("deliverable_id") not in selected_by_deliverable:
            issues.append(f"no selected asset for deliverable {deliverable.get('deliverable_id')}")

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify visual decision pipeline artifacts.")
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    issues = verify(args.run_dir.resolve())
    if issues:
        for issue in issues:
            print(f"FAIL {issue}")
        raise SystemExit(1)
    print("OK visual decision pipeline verified")


if __name__ == "__main__":
    main()
