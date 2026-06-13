#!/usr/bin/env python3
"""Verify reference collection outputs and their handoff into 03_visual_candidates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify run-scoped reference pipeline outputs.")
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--require-03", action="store_true", help="Require 03_visual_candidates outputs to carry reference traces.")
    parser.add_argument("--require-source", help="Require selected references to come from this source_id.")
    args = parser.parse_args()

    run_dir = args.run.resolve()
    checks = verify(run_dir, require_03=args.require_03, require_source=args.require_source)
    print(json.dumps({"run": str(run_dir), "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if all(item["ok"] for item in checks) else 1


def verify(run_dir: Path, *, require_03: bool, require_source: str | None = None) -> list[dict[str, Any]]:
    reference_dir = run_dir / "references"
    manifest_path = reference_dir / "reference-manifest.json"
    selected_path = reference_dir / "selected-references.json"

    manifest = read_json(manifest_path)
    selected = read_json(selected_path).get("selected", []) if selected_path.exists() else []
    selected_assets = [asset for asset in manifest.get("assets", []) if asset.get("status") == "selected"]

    checks = [
        check("reference_manifest_exists", manifest_path.exists(), str(manifest_path)),
        check("selected_references_exists", selected_path.exists(), str(selected_path)),
        check("manifest_has_selected_assets", bool(selected_assets), f"selected_assets={len(selected_assets)}"),
        check("selected_json_has_items", bool(selected), f"selected={len(selected)}"),
        check(
            "selected_files_exist",
            bool(selected) and all((run_dir / item.get("relative_path", "")).exists() for item in selected),
            "all selected relative_path files exist",
        ),
        check(
            "selected_assets_have_scores",
            bool(selected) and all("score" in item and "text_relevance_score" in item for item in selected),
            "requires score and text_relevance_score",
        ),
    ]

    if require_source:
        checks.append(check(
            "selected_assets_match_required_source",
            bool(selected) and all(item.get("source_id") == require_source for item in selected),
            f"required_source={require_source}",
        ))

    if require_03:
        visual_plan = read_json(run_dir / "03_visual_candidates" / "visual-plan.json")
        prompts = read_json(run_dir / "03_visual_candidates" / "image-prompts.json").get("prompts", [])
        candidates = read_json(run_dir / "03_visual_candidates" / "candidate-manifest.json").get("candidates", [])
        checks.extend([
            check(
                "visual_plan_loaded_reference_manifest",
                visual_plan.get("reference_manifest", {}).get("status") == "loaded",
                "visual_plan.reference_manifest.status",
            ),
            check(
                "visual_plan_has_reference_assets",
                bool(visual_plan.get("reference_assets")),
                f"reference_assets={len(visual_plan.get('reference_assets', []))}",
            ),
            check(
                "prompts_have_reference_asset",
                bool(prompts) and all(prompt.get("reference_asset", {}).get("relative_path") for prompt in prompts),
                f"prompts={len(prompts)}",
            ),
            check(
                "prompts_include_reference_hint",
                bool(prompts) and all("selected reference asset:" in prompt.get("positive_prompt", "") for prompt in prompts),
                "positive_prompt includes selected reference asset hint",
            ),
            check(
                "candidates_have_reference_trace",
                bool(candidates) and all(candidate.get("review_metadata", {}).get("reference_asset", {}).get("relative_path") for candidate in candidates),
                f"candidates={len(candidates)}",
            ),
        ])
        if require_source:
            checks.extend([
                check(
                    "prompts_reference_required_source",
                    bool(prompts) and all(prompt.get("reference_asset", {}).get("source_id") == require_source for prompt in prompts),
                    f"required_source={require_source}",
                ),
                check(
                    "candidates_reference_required_source",
                    bool(candidates) and all(candidate.get("review_metadata", {}).get("reference_asset", {}).get("source_id") == require_source for candidate in candidates),
                    f"required_source={require_source}",
                ),
            ])

    return checks


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": detail}


if __name__ == "__main__":
    raise SystemExit(main())
