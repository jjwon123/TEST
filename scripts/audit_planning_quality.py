#!/usr/bin/env python3
"""Audit 01 brief and 02 content planning outputs before reference/prompt work."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json, write_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run.resolve()
    audit = build_audit(run_dir)
    output_dir = run_dir / "planning-quality"
    write_json(output_dir / "planning-quality-audit.json", audit)
    write_text(output_dir / "planning-quality-audit.md", render_markdown(audit))
    print(f"OK planning audit {output_dir / 'planning-quality-audit.json'}")
    return 0


def build_audit(run_dir: Path) -> dict[str, Any]:
    event_input = read_json(run_dir / "event-input.json", default={})
    brand_guide = read_json(run_dir / "brand-guide.json", default={})
    brief = read_json(run_dir / "01_event_brief" / "brief.json", default={})
    plan = read_json(run_dir / "02_content_planning" / "content-plan.json", default={})
    candidates = read_json(run_dir / "02_content_planning" / "concept-candidates.json", default={})
    concept_review = read_json(run_dir / "02_content_planning" / "concept-review.json", default={})
    copy_package = read_json(run_dir / "02_content_planning" / "copy-package.json", default={})
    copy_review = read_json(run_dir / "02_content_planning" / "copy-review.json", default={})
    scorecard = read_json(run_dir / "02_content_planning" / "planning-scorecard.json", default={})
    issues = []
    issues.extend(audit_brief(event_input, brand_guide, brief))
    issues.extend(audit_plan(brief, plan))
    issues.extend(audit_campaign_package(brief, candidates, concept_review, copy_package, copy_review, scorecard))
    blockers = [item for item in issues if item["severity"] == "blocker"]
    warnings = [item for item in issues if item["severity"] == "warning"]
    status = "fail" if blockers else "warning" if warnings else "pass"
    return {
        "runId": run_dir.name,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "summary": {
            "issues": len(issues),
            "blockers": len(blockers),
            "warnings": len(warnings),
        },
        "checks": [
            "brief_core_inputs",
            "brand_safety_constraints",
            "content_plan_channel_coverage",
            "visual_need_handoff",
            "message_diversity",
            "three_distinct_concepts",
            "concept_and_copy_approval",
            "critical_planning_qa",
        ],
        "issues": issues,
    }


def audit_brief(event_input: dict[str, Any], brand_guide: dict[str, Any], brief: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    required = {
        "eventName": event_input.get("eventName") or brief.get("event_name"),
        "target": event_input.get("target") or brief.get("target", {}).get("summary"),
        "offer": event_input.get("offer") or brief.get("offer", {}).get("summary"),
        "brandName": brand_guide.get("brandName") or brief.get("brand", {}).get("name"),
    }
    for field, value in required.items():
        if not value:
            issues.append(issue("blocker", "brief_missing_core_input", f"{field} is empty.", "01_event_brief"))
    banned_words = brief.get("constraints", {}).get("banned_words", []) or event_input.get("bannedWords", [])
    if not banned_words:
        issues.append(issue("warning", "brief_missing_banned_words", "금지 표현/모방 방지 기준이 비어 있습니다.", "01_event_brief"))
    quality = brief.get("quality_assessment", {})
    if quality.get("category_risk", {}).get("blocking"):
        issues.append(issue("blocker", "brief_category_risk_blocking", "카테고리 리스크 blocking 항목이 남아 있습니다.", "01_event_brief"))
    core_messages = brief.get("core_messages", [])
    copied_inputs = {
        event_input.get("objective", ""),
        event_input.get("offer", ""),
    }
    generic_messages = [
        item for item in core_messages
        if item in copied_inputs or item.endswith("중심으로 안내한다.")
    ]
    if core_messages and len(generic_messages) >= max(2, len(core_messages) // 2):
        issues.append(issue(
            "warning",
            "brief_low_strategic_enrichment",
            "핵심 메시지가 입력 문장 복사 또는 범용 안내 문구에 치우쳐 있습니다.",
            "01_event_brief",
        ))
    return issues


def audit_campaign_package(
    brief: dict[str, Any],
    candidates: dict[str, Any],
    concept_review: dict[str, Any],
    copy_package: dict[str, Any],
    copy_review: dict[str, Any],
    scorecard: dict[str, Any],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    concepts = candidates.get("candidates", [])
    if len(concepts) != 3:
        issues.append(issue("blocker", "planning_requires_three_concepts", "서로 다른 캠페인 콘셉트 3안이 필요합니다.", "02_content_planning"))
    axes = [item.get("axis") for item in concepts]
    if concepts and len(set(axes)) != len(axes):
        issues.append(issue("blocker", "planning_duplicate_concept_axes", "콘셉트 전략 축이 중복됩니다.", "02_content_planning"))
    if concept_review.get("status") != "approved":
        issues.append(issue("warning", "planning_concept_not_approved", "사람이 캠페인 콘셉트를 선택해야 합니다.", "02_content_planning"))
    if copy_package.get("status") != "review_pending" and concept_review.get("status") == "approved":
        issues.append(issue("blocker", "planning_copy_package_missing", "선택된 콘셉트의 완성 카피 패키지가 없습니다.", "02_content_planning"))
    if copy_review.get("status") != "approved":
        issues.append(issue("warning", "planning_copy_not_approved", "최종 카피 승인이 필요합니다.", "02_content_planning"))
    if int(scorecard.get("criticalErrorCount") or 0) > 0:
        issues.append(issue("blocker", "planning_critical_qa_failure", "기획 점수표에 치명 오류가 남아 있습니다.", "02_content_planning"))
    quality_issue_ids = [item.get("id") for item in scorecard.get("issues", []) if item.get("severity") == "warning"]
    if quality_issue_ids:
        issues.append(issue("warning", "planning_quality_warning", f"기획 품질 수정이 필요합니다: {', '.join(quality_issue_ids)}", "02_content_planning"))
    text = str(copy_package)
    for banned in brief.get("constraints", {}).get("banned_words", []):
        if banned and banned in text:
            issues.append(issue("blocker", "planning_banned_word", f"금지 표현이 포함되었습니다: {banned}", "02_content_planning"))
    return issues


def audit_plan(brief: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    deliverables = plan.get("deliverables", [])
    image_needs = plan.get("image_needs", [])
    if not deliverables:
        issues.append(issue("blocker", "plan_missing_deliverables", "산출물 정의가 없습니다.", "02_content_planning"))
    if len(deliverables) != len(image_needs):
        issues.append(issue("warning", "plan_image_need_mismatch", "산출물 수와 image_needs 수가 다릅니다.", "02_content_planning"))
    for item in deliverables:
        if not item.get("copy_intent"):
            issues.append(issue("warning", "plan_missing_copy_intent", f"{item.get('deliverable_id', '-')}: copy_intent가 비어 있습니다.", "02_content_planning"))
        if not item.get("visual_need"):
            issues.append(issue("warning", "plan_missing_visual_need", f"{item.get('deliverable_id', '-')}: visual_need가 비어 있습니다.", "02_content_planning"))
    copy_intents = {item.get("copy_intent") for item in deliverables if item.get("copy_intent")}
    if len(deliverables) >= 3 and len(copy_intents) <= 1:
        issues.append(issue("warning", "plan_low_message_diversity", "여러 채널 산출물이 거의 같은 메시지에만 의존합니다.", "02_content_planning"))
    generic_purpose = "이벤트 핵심 내용을 빠르게 이해시키고 참여 행동으로 연결한다."
    generic_purposes = sum(
        1 for item in deliverables
        if item.get("purpose") in {generic_purpose, brief.get("objective", {}).get("primary")}
    )
    if len(deliverables) >= 3 and generic_purposes >= len(deliverables) // 2:
        issues.append(issue("warning", "plan_generic_channel_roles", "채널별 목적이 범용 문장에 머물러 역할 분리가 약합니다.", "02_content_planning"))
    slide_plans = [item for item in deliverables if item.get("slides")]
    if slide_plans and any(
        any(not slide.get("message_intent") for slide in item.get("slides", []))
        for item in slide_plans
    ):
        issues.append(issue("warning", "plan_missing_slide_messages", "다중 슬라이드 산출물의 장별 메시지 의도가 비어 있습니다.", "02_content_planning"))
    strategy_thesis = plan.get("strategy_summary", {}).get("planning_thesis", "")
    objective = brief.get("objective", {}).get("primary", "")
    if objective and strategy_thesis.count(objective) >= 2:
        issues.append(issue("warning", "plan_repetitive_strategy_thesis", "전략 논지가 목표 문장을 반복하며 별도 판단을 제공하지 않습니다.", "02_content_planning"))
    core_messages = brief.get("core_messages", [])
    if not core_messages:
        issues.append(issue("blocker", "plan_no_brief_core_messages", "브리프 핵심 메시지가 없어 기획 품질을 판단하기 어렵습니다.", "01_event_brief"))
    return issues


def issue(severity: str, issue_id: str, message: str, stage: str) -> dict[str, str]:
    return {
        "id": issue_id,
        "severity": severity,
        "message": message,
        "suggestedStage": stage,
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Planning Quality Audit",
        "",
        f"- Run: `{audit['runId']}`",
        f"- Status: `{audit['status']}`",
        f"- Issues: {audit['summary']['issues']} (blockers {audit['summary']['blockers']}, warnings {audit['summary']['warnings']})",
        "",
        "## Issues",
        "",
    ]
    if audit["issues"]:
        for item in audit["issues"]:
            lines.append(f"- `{item['severity']}` `{item['id']}` [{item['suggestedStage']}]: {item['message']}")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
