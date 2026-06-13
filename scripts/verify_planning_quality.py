#!/usr/bin/env python3
"""Focused verifier for planning-stage strategy completeness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json


def verify(run_dir: Path) -> list[str]:
    issues: list[str] = []
    brief = read_json(run_dir / "01_event_brief" / "brief.json", default={})
    plan = read_json(run_dir / "02_content_planning" / "content-plan.json", default={})
    approvals = read_json(run_dir / "approvals.json", default={"approvals": []})
    run_evidence = read_json(run_dir / "research-evidence.json", default={})

    if not brief:
        issues.append("missing brief.json")
        return issues
    if not plan:
        issues.append("missing content-plan.json")
        return issues

    _require_object(brief, "research_context", issues, "brief")
    _require_object(brief, "reasoning_trace", issues, "brief")
    _require_object(brief, "quality_assessment", issues, "brief")
    _require_object(plan, "strategy_summary", issues, "content-plan")
    _require_object(plan, "research_context", issues, "content-plan")
    _require_object(plan, "reasoning_trace", issues, "content-plan")
    _require_object(plan, "quality_assessment", issues, "content-plan")
    if not isinstance(brief.get("quality_assessment", {}).get("repair_history"), dict):
        issues.append("brief.quality_assessment.repair_history must be an object")
    if not isinstance(plan.get("quality_assessment", {}).get("repair_history"), dict):
        issues.append("content-plan.quality_assessment.repair_history must be an object")
    if not isinstance(brief.get("reasoning_trace", {}).get("generation_execution"), dict):
        issues.append("brief.reasoning_trace.generation_execution must be an object")
    if not isinstance(plan.get("reasoning_trace", {}).get("generation_execution"), dict):
        issues.append("content-plan.reasoning_trace.generation_execution must be an object")
    if not isinstance(brief.get("research_context", {}).get("provider_execution"), dict):
        issues.append("brief.research_context.provider_execution must be an object")
    if not isinstance(plan.get("research_context", {}).get("provider_execution"), dict):
        issues.append("content-plan.research_context.provider_execution must be an object")

    if not brief.get("core_messages"):
        issues.append("brief.core_messages must not be empty")
    if not plan.get("deliverables"):
        issues.append("content-plan.deliverables must not be empty")
    if len(plan.get("deliverables", [])) != len(plan.get("image_needs", [])):
        issues.append("deliverable/image_need counts must match")

    distinct_copy_intents = {
        item.get("copy_intent", "")
        for item in plan.get("deliverables", [])
        if item.get("copy_intent", "")
    }
    if len(plan.get("deliverables", [])) >= 3 and len(distinct_copy_intents) < 2:
        issues.append("multi-deliverable plan needs differentiated copy_intent")

    if not any(
        item.get("stage_id") == "01_event_brief" and item.get("status") == "approved"
        for item in approvals.get("approvals", [])
    ):
        issues.append("01_event_brief approval missing before content planning")

    evidence_items = run_evidence.get("items", []) if isinstance(run_evidence, dict) else []
    if evidence_items:
        if brief.get("research_context", {}).get("status") != "evidence_attached":
            issues.append("brief did not attach available research evidence")
        if plan.get("research_context", {}).get("status") != "evidence_attached":
            issues.append("content-plan did not attach available research evidence")

    if not isinstance(plan.get("strategy_summary", {}).get("handoff_focus"), list):
        issues.append("strategy_summary.handoff_focus must be a list")
    category_risk = plan.get("quality_assessment", {}).get("category_risk")
    if category_risk:
        if not isinstance(category_risk, dict):
            issues.append("content-plan.quality_assessment.category_risk must be an object")
        elif category_risk.get("blocking") and plan.get("quality_assessment", {}).get("handoff_ready") is not False:
            issues.append("blocking category_risk must stop content-plan handoff")
        elif category_risk.get("detected") and not category_risk.get("reference_path"):
            issues.append("detected category_risk must include reference_path")

    return issues


def _require_object(payload: dict, key: str, issues: list[str], label: str) -> None:
    if not isinstance(payload.get(key), dict):
        issues.append(f"{label}.{key} must be an object")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify planning-stage strategy quality contracts.")
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()

    issues = verify(args.run_dir.resolve())
    if issues:
        for issue in issues:
            print(f"FAIL {issue}")
        raise SystemExit(1)
    print("OK planning quality verified")


if __name__ == "__main__":
    main()
