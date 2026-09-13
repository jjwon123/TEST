#!/usr/bin/env python3
"""Validate a review-ready advertising planning JSON document."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json  # noqa: E402
from core.utils.schema_validation import SchemaValidationError, validate_json  # noqa: E402
from core.utils import channel_registry  # noqa: E402
from services.ad_strategy.quality_gate import copy_character_count  # noqa: E402
from services.ad_strategy.text_quality import text_artifact_summary  # noqa: E402


SCHEMA_PATH = ROOT / "core" / "schemas" / "ad-planning-output.schema.json"
DISTINCT_FIELDS = (
    "targetInsight",
    "corePromise",
    "emotionalDirection",
    "persuasionSequence",
    "offerPresentation",
    "cta",
)
FINAL_COPY_STATUSES = {"copy_review_pending", "approved"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_file", type=Path, nargs="?")
    parser.add_argument("--run-dir", type=Path, help="Validate the canonical 01/02 planning artifacts in a run directory.")
    args = parser.parse_args()
    if bool(args.json_file) == bool(args.run_dir):
        parser.error("provide either json_file or --run-dir")
    path = (args.run_dir or args.json_file).resolve()
    try:
        payload = build_planning_output_from_run(path) if args.run_dir else read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "file": str(path), "issues": [{"path": "$", "message": str(exc)}]}, ensure_ascii=False))
        return 1

    issues = validate_planning_output(payload)
    status = "pass" if not issues else "fail"
    print(json.dumps({"status": status, "file": str(path), "issues": issues}, ensure_ascii=False))
    return 0 if not issues else 1


def build_planning_output_from_run(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    brief = read_json(run_dir / "01_event_brief" / "brief.json")
    strategic = read_json(run_dir / "01_event_brief" / "strategic-brief.json", default={})
    stage = run_dir / "02_content_planning"
    concepts_doc = read_json(stage / "concept-candidates.json", default={})
    concept_review = read_json(stage / "concept-review.json", default={})
    copy_package = read_json(stage / "copy-package.json", default={})
    copy_review = read_json(stage / "copy-review.json", default={})
    scorecard = read_json(stage / "planning-scorecard.json", default={})

    concept_approved = concept_review.get("status") == "approved" and bool(concept_review.get("selectedConceptId"))
    copy_approved = copy_review.get("status") == "approved" and copy_review.get("approved") is True
    if strategic.get("missingInputs") or brief.get("open_questions"):
        status = "needs_input"
    elif concept_review.get("status") == "rejected" or copy_review.get("status") == "rejected":
        status = "rejected"
    elif copy_approved:
        status = "approved"
    elif concept_approved:
        status = "copy_review_pending"
    else:
        status = "concept_review_pending"

    resolved_channels: list[str] = []
    for requested in brief.get("channels", []):
        for channel_id in channel_registry.resolve_requested(requested):
            if channel_id not in resolved_channels:
                resolved_channels.append(channel_id)

    selected_id = str(concept_review.get("selectedConceptId") or "")
    outputs = [_copy_output(item) for item in copy_package.get("outputs", []) if isinstance(item, dict)]
    generated_original = {
        str(item.get("channelId") or item.get("deliverableId") or index): item.get("copy", {})
        for index, item in enumerate(outputs)
    }
    user_edited_final = dict(generated_original)
    for edit in copy_review.get("edits", []):
        if not isinstance(edit, dict):
            continue
        channel_id = str(edit.get("channelId") or "")
        if not channel_id:
            continue
        if isinstance(edit.get("originalCopy"), dict):
            generated_original[channel_id] = edit["originalCopy"]
        if isinstance(edit.get("editedCopy"), dict):
            user_edited_final[channel_id] = edit["editedCopy"]
    return {
        "schemaVersion": "1.0.0",
        "status": status,
        "brief": {
            "industry": str(strategic.get("industry") or "cosmetics_skincare"),
            "eventName": str(brief.get("event_name") or ""),
            "verifiedFacts": [str(item) for item in strategic.get("verifiedFacts", [])],
            "unverifiedClaims": [str(item) for item in strategic.get("unverifiedClaims", [])],
            "missingInputs": [str(item) for item in (strategic.get("missingInputs") or brief.get("open_questions") or [])],
            "constraints": {
                "requiredPhrases": [str(item) for item in brief.get("constraints", {}).get("required_phrases", [])],
                "bannedWords": [str(item) for item in brief.get("constraints", {}).get("banned_words", [])],
                "channels": resolved_channels,
            },
        },
        "conceptCandidates": [_concept_candidate(item) for item in concepts_doc.get("candidates", []) if isinstance(item, dict)],
        "conceptReview": {
            "selectedConceptId": selected_id,
            "rejectedConceptIds": [str(item) for item in concept_review.get("rejectedConceptIds", [])],
            "reasonTags": [str(item) for item in concept_review.get("reasonTags", [])],
            "reviewNote": str(concept_review.get("reviewNote") or ""),
        },
        "copyPackage": {
            "selectedConceptId": str(copy_package.get("conceptId") or ""),
            "outputs": outputs,
        },
        "scorecard": {
            "status": str(scorecard.get("status") or "fail"),
            "criticalErrorCount": int(scorecard.get("criticalErrorCount") or 0),
            "issues": scorecard.get("issues", []) if isinstance(scorecard.get("issues"), list) else [],
            "rubric": {
                key: float((scorecard.get("rubric") or {}).get(key) or 0)
                for key in (
                    "strategyClarity", "targetEmpathy", "productConnection", "distinctiveness",
                    "channelFit", "koreanCopyQuality", "brandFit", "actionability",
                )
            },
            "averageScore": float(scorecard.get("averageScore") or 0),
        },
        "correctionRecord": {
            "generatedOriginal": generated_original,
            "userEditedFinal": user_edited_final,
            "reasonTags": [str(item) for item in copy_review.get("reasonTags", [])],
            "approved": copy_approved,
        },
    }


def _concept_candidate(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "conceptId": str(item.get("conceptId") or ""),
        "axis": str(item.get("axis") or ""),
        "name": str(item.get("name") or ""),
        "targetInsight": str(item.get("targetInsight") or ""),
        "corePromise": str(item.get("corePromise") or ""),
        "emotionalDirection": str(item.get("emotionalDirection") or ""),
        "persuasionSequence": [str(value) for value in item.get("persuasionSequence", [])],
        "offerPresentation": str(item.get("offerPresentation") or ""),
        "cta": str(item.get("cta") or ""),
        "headlineDirections": [str(value) for value in item.get("headlineDirections", [])],
        "expectedEffect": str(item.get("expectedEffect") or ""),
        "risks": [str(value) for value in item.get("risks", [])],
    }


def _copy_output(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "deliverableId": str(item.get("deliverableId") or ""),
        "channelId": str(item.get("channelId") or ""),
        "purpose": str(item.get("purpose") or ""),
        "strategyBasis": str(item.get("strategyBasis") or ""),
        "copy": item.get("copy", {}) if isinstance(item.get("copy"), dict) else {},
        "characterCount": item.get("characterCount") if isinstance(item.get("characterCount"), int) else -1,
    }


def validate_planning_output(payload: Any) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    schema = read_json(SCHEMA_PATH)
    try:
        validate_json(payload, schema, data_label="ad planning output", schema_label=SCHEMA_PATH.name)
    except SchemaValidationError as exc:
        issues.extend({"path": item.path, "message": item.message} for item in exc.issues)
        return issues

    status = str(payload.get("status") or "")
    brief = payload["brief"]
    concepts = payload["conceptCandidates"]
    review = payload["conceptReview"]
    package = payload["copyPackage"]
    scorecard = payload["scorecard"]
    correction = payload["correctionRecord"]
    selected_id = str(review.get("selectedConceptId") or "")
    package_selected_id = str(package.get("selectedConceptId") or "")
    outputs = package.get("outputs") or []

    if status == "needs_input":
        if not brief.get("missingInputs"):
            _add(issues, "brief.missingInputs", "needs_input 상태에는 누락 입력이 한 개 이상 필요합니다.")
        if concepts or selected_id or outputs:
            _add(issues, "$", "needs_input 상태에서는 콘셉트 선택이나 카피를 생성할 수 없습니다.")
        return issues

    if len(concepts) != 3:
        _add(issues, "conceptCandidates", "검수 가능한 결과에는 콘셉트가 정확히 3개 있어야 합니다.")
    else:
        _validate_concept_distinction(concepts, issues)

    concept_ids = [str(item.get("conceptId") or "") for item in concepts]
    if len(set(concept_ids)) != len(concept_ids):
        _add(issues, "conceptCandidates", "conceptId는 서로 달라야 합니다.")

    if status == "concept_review_pending":
        if selected_id or package_selected_id or outputs:
            _add(issues, "$", "콘셉트 선택 전에는 선택 ID와 채널 카피가 비어 있어야 합니다.")
    elif status in FINAL_COPY_STATUSES:
        if not selected_id or selected_id not in concept_ids:
            _add(issues, "conceptReview.selectedConceptId", "생성된 3안 중 사람이 선택한 콘셉트 ID가 필요합니다.")
        if package_selected_id != selected_id:
            _add(issues, "copyPackage.selectedConceptId", "카피 패키지는 사람이 선택한 콘셉트와 일치해야 합니다.")
        if not outputs:
            _add(issues, "copyPackage.outputs", "선택된 콘셉트의 채널별 카피가 필요합니다.")

    requested_channels = set(brief.get("constraints", {}).get("channels") or [])
    output_channels = [str(item.get("channelId") or "") for item in outputs]
    unexpected = sorted(set(output_channels) - requested_channels)
    if unexpected:
        _add(issues, "copyPackage.outputs", f"요청하지 않은 채널이 포함되었습니다: {', '.join(unexpected)}")
    if len(output_channels) != len(set(output_channels)):
        _add(issues, "copyPackage.outputs", "같은 채널 결과가 중복되었습니다.")

    for index, output in enumerate(outputs):
        actual = copy_character_count(output.get("copy", {}))
        if output.get("characterCount") != actual:
            _add(issues, f"copyPackage.outputs[{index}].characterCount", f"실제 표시 문장 길이 {actual}와 일치하지 않습니다.")

    artifacts = text_artifact_summary({"conceptCandidates": concepts, "copyPackage": package})
    if any(artifacts.get(key) for key in ("brokenKoreanCount", "rawJsonCount", "rawHtmlCount", "programmingArtifactCount")):
        _add(issues, "$", "깨진 한글, JSON/HTML 또는 프로그래밍 구조가 사용자 문장에 포함되었습니다.")

    rubric = scorecard.get("rubric") or {}
    calculated_average = sum(float(value) for value in rubric.values()) / len(rubric) if rubric else 0.0
    if abs(float(scorecard.get("averageScore") or 0) - calculated_average) > 0.01:
        _add(issues, "scorecard.averageScore", f"루브릭 실제 평균 {calculated_average:.2f}와 일치하지 않습니다.")

    if status == "approved":
        if int(scorecard.get("criticalErrorCount") or 0) != 0:
            _add(issues, "scorecard", "승인 결과에는 치명 오류가 남아 있으면 안 됩니다.")
        blocking_issues = [
            item for item in (scorecard.get("issues") or [])
            if isinstance(item, dict) and item.get("severity") in {"error", "critical"}
        ]
        if blocking_issues:
            _add(issues, "scorecard.issues", "승인 전 차단 등급의 품질 오류를 해결해야 합니다.")
        if calculated_average < 4.0:
            _add(issues, "scorecard.rubric", "승인 결과의 평균 루브릭 점수는 4.0 이상이어야 합니다.")
        if correction.get("approved") is not True:
            _add(issues, "correctionRecord.approved", "최종 사람 승인이 기록되어야 합니다.")
        if not correction.get("reasonTags"):
            _add(issues, "correctionRecord.reasonTags", "최종 카피 승인 또는 수정 사유 태그가 필요합니다.")
        if not review.get("reasonTags") or not str(review.get("reviewNote") or "").strip():
            _add(issues, "conceptReview", "사람 선택 사유 태그와 검수 메모가 필요합니다.")

    return issues


def _validate_concept_distinction(concepts: list[dict[str, Any]], issues: list[dict[str, str]]) -> None:
    for left_index, left in enumerate(concepts):
        for right in concepts[left_index + 1:]:
            changed = [field for field in DISTINCT_FIELDS if _normalize(left.get(field)) != _normalize(right.get(field))]
            if len(changed) < 2:
                _add(
                    issues,
                    "conceptCandidates",
                    f"{left.get('conceptId')}와 {right.get('conceptId')}는 전략 항목이 두 개 이상 달라야 합니다.",
                )


def _normalize(value: Any) -> str:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return " ".join(str(value or "").split()).lower()


def _add(issues: list[dict[str, str]], path: str, message: str) -> None:
    issues.append({"path": path, "message": message})


if __name__ == "__main__":
    raise SystemExit(main())
