"""06_qa_packaging handler.

Runs structural QA against selected assets or assembled outputs and writes the
QA/package files consumed by 07_asset_archive.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils import channel_registry
from core.utils import template_registry
from core.utils.json_io import read_json, write_json, write_text
from core.utils.schema_validation import validate_json


ROOT = Path(__file__).resolve().parents[3]
STAGE_ID = "06_qa_packaging"


QUALITY_ARTIFACT_SPECS = [
    {
        "id": "planning_quality_audit",
        "label": "Planning quality audit",
        "path": Path("planning-quality") / "planning-quality-audit.json",
        "stage": "02_content_planning",
        "required": True,
        "missing_severity": "warning",
    },
    {
        "id": "reference_quality_report",
        "label": "Reference quality report",
        "path": Path("03_reference_research") / "reference-quality-report.json",
        "stage": "03_reference_research",
        "required": True,
        "missing_severity": "warning",
    },
    {
        "id": "prompt_audit",
        "label": "Prompt audit",
        "path": Path("03_visual_candidates") / "prompt-audit.json",
        "stage": "03_visual_candidates",
        "required": True,
        "missing_severity": "warning",
    },
    {
        "id": "generation_quality",
        "label": "Generation quality",
        "path": Path("03_visual_candidates") / "generation-quality.json",
        "stage": "03_visual_candidates",
        "required": True,
        "missing_severity": "warning",
    },
    {
        "id": "selected_assets",
        "label": "Selected assets",
        "path": Path("04_admin_selection") / "selected-assets.json",
        "stage": "04_admin_selection",
        "required": True,
        "missing_severity": "blocker",
    },
]


def run(
    run_dir: Path,
    mode: str = "run",
    outputs: list[str] | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    stage_dir = run_dir / STAGE_ID

    brief = read_json(run_dir / "01_event_brief" / "brief.json")
    selected_assets = read_json(run_dir / "04_admin_selection" / "selected-assets.json")
    figma_outputs_path = run_dir / "05_figma_assembly" / "channel-outputs.json"
    if not figma_outputs_path.exists():
        return _run_selected_assets_packaging(run_dir, stage_dir, brief, selected_assets)

    channel_outputs = read_json(run_dir / "05_figma_assembly" / "channel-outputs.json")
    copy_map = read_json(run_dir / "05_figma_assembly" / "copy-map.json")
    qa_rules = read_json(ROOT / "core" / "policies" / "qa-rules.json")
    export_rules = read_json(ROOT / "core" / "policies" / "export-rules.json")
    forbidden_policy = read_json(ROOT / "core" / "policies" / "forbidden-phrases.json")

    input_schema = read_json(ROOT / "pipeline" / STAGE_ID / "input.schema.json")
    validate_json(
        {"channel_outputs": channel_outputs, "qa_rules": qa_rules},
        input_schema,
        data_label=f"{STAGE_ID} input",
        schema_label=f"pipeline/{STAGE_ID}/input.schema.json",
    )

    context = {
        "run_dir": run_dir,
        "brief": brief,
        "channel_outputs": channel_outputs,
        "copy_map": copy_map,
        "qa_rules": qa_rules,
        "export_rules": export_rules,
        "forbidden_policy": forbidden_policy,
    }

    quality_artifacts = _collect_quality_artifacts(run_dir, selected_assets)
    issues: list[dict[str, Any]] = []
    issues.extend(_check_quality_artifacts(quality_artifacts))
    issues.extend(_check_exports(context))
    issues.extend(_check_copy_source_trace(context))
    issues.extend(_check_copy_fit_status(context))
    issues.extend(_check_forbidden_phrases(context))
    issues.extend(_check_required_phrases(context))

    package_manifest, package_copy = _copy_package_files(context, issues)
    _attach_quality_trace(package_manifest, selected_assets, quality_artifacts)
    qa_report = _build_qa_report(brief, channel_outputs, issues, package_manifest, package_copy, quality_artifacts)
    qa_packaging = _build_schema_summary(brief, qa_report, package_manifest, quality_artifacts)

    qa_report_path = stage_dir / "qa-report.json"
    manifest_path = stage_dir / "final-package-manifest.json"
    summary_path = stage_dir / "qa-packaging.json"
    notes_path = stage_dir / "notes.md"

    write_json(qa_report_path, qa_report)
    write_json(manifest_path, package_manifest)
    write_json(summary_path, qa_packaging)
    write_text(notes_path, _build_notes(qa_report, package_manifest))

    return {
        "stage_id": STAGE_ID,
        "status": "review_pending",
        "outputs": [
            str(qa_report_path.relative_to(run_dir)),
            str(manifest_path.relative_to(run_dir)),
            str(summary_path.relative_to(run_dir)),
            str(notes_path.relative_to(run_dir)),
        ],
        "notes": [f"QA status: {qa_report['summary']['status']} ({len(issues)} issues)."],
        "next_state": "review_pending",
        "regeneration_groups": {},
    }


def _run_selected_assets_packaging(
    run_dir: Path,
    stage_dir: Path,
    brief: dict[str, Any],
    selected_assets: dict[str, Any],
) -> dict[str, Any]:
    selections = [
        item for item in selected_assets.get("selectedAssets", selected_assets.get("selections", []))
        if item.get("status", item.get("decision")) == "selected"
    ]
    quality_artifacts = _collect_quality_artifacts(run_dir, selected_assets)
    issues = []
    issues.extend(_check_quality_artifacts(quality_artifacts))
    if not selections:
        issues.append(_issue(
            code="selected_assets_missing",
            severity="blocker",
            frame_id="",
            output_id="",
            message="No selected assets were recorded in 04_admin_selection/selected-assets.json.",
            suggested_fix_stage="04_admin_selection",
            source_stage="04_admin_selection",
            source_field="selected-assets.json.selectedAssets",
        ))

    package_manifest = []
    for item in selections:
        asset_id = item.get("id") or item.get("candidate_id", "")
        source_file = item.get("sourceFile") or item.get("selected_file", "")
        deliverable_id = item.get("deliverableId") or item.get("deliverable_id", "")
        filename = Path(source_file or f"{asset_id or 'candidate'}.png").name
        channel = _package_channel(item.get("channel") or item.get("channel_id", "unknown"))
        package_manifest.append({
            "frameId": asset_id,
            "frameName": f"{channel} / {deliverable_id}",
            "channel": channel,
            "channelName": _channel_name(channel),
            "deliverableId": deliverable_id,
            "template_id": "",
            "width": 0,
            "height": 0,
            "exportFileName": filename,
            "sourceExportPath": source_file,
            "finalPackagePath": str(Path("package") / "final" / filename),
            "channelPackagePath": str(Path("package") / "by-channel" / channel / filename),
        })

    _attach_quality_trace(package_manifest, selected_assets, quality_artifacts)
    qa_report = _build_qa_report(
        brief,
        {"outputs": []},
        issues,
        package_manifest,
        {"copiedFiles": [], "missingFiles": []},
        quality_artifacts,
    )
    qa_packaging = _build_schema_summary(brief, qa_report, package_manifest, quality_artifacts)
    notes = _build_notes(qa_report, package_manifest)

    qa_report_path = stage_dir / "qa-report.json"
    manifest_path = stage_dir / "final-package-manifest.json"
    summary_path = stage_dir / "qa-packaging.json"
    notes_path = stage_dir / "notes.md"
    write_json(qa_report_path, qa_report)
    write_json(manifest_path, package_manifest)
    write_json(summary_path, qa_packaging)
    write_text(notes_path, notes)

    return {
        "stage_id": STAGE_ID,
        "status": "review_pending",
        "outputs": [
            str(qa_report_path.relative_to(run_dir)),
            str(manifest_path.relative_to(run_dir)),
            str(summary_path.relative_to(run_dir)),
            str(notes_path.relative_to(run_dir)),
        ],
        "notes": [f"QA status: {qa_report['summary']['status']} ({len(issues)} issues)."],
        "next_state": "review_pending",
        "regeneration_groups": {},
    }


def _check_exports(context: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    allowed = set(context["export_rules"].get("allowed_formats", ["png", "jpg"]))
    for output in context["channel_outputs"].get("outputs", []):
        expected = output.get("expected_export_path", "")
        output_id = output.get("output_id", "")
        export_path = context["run_dir"] / expected
        suffix = export_path.suffix.lower().lstrip(".")

        if suffix and suffix not in allowed:
            issues.append(_issue(
                code="export_format",
                severity="error",
                frame_id=_frame_id(output),
                output_id=output_id,
                message=f"Export format .{suffix} is not allowed.",
                suggested_fix_stage="05_figma_assembly",
                source_stage="05_figma_assembly",
                source_field="channel_outputs.outputs[].expected_export_path",
            ))

        if not export_path.exists():
            issues.append(_issue(
                code="export_missing",
                severity="blocker",
                frame_id=_frame_id(output),
                output_id=output_id,
                message=f"Expected export file is missing: {expected}",
                suggested_fix_stage="05_figma_assembly",
                source_stage="05_figma_assembly",
                source_field="channel_outputs.outputs[].expected_export_path",
            ))
    return issues


def _check_copy_source_trace(context: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    for item in context["copy_map"].get("items", []):
        missing = [field for field in ["source_stage", "source_field", "fit_status"] if not item.get(field)]
        if missing:
            issues.append(_issue(
                code="copy_trace_missing",
                severity="error",
                frame_id=item.get("frame_id", ""),
                output_id=item.get("output_id", ""),
                text_slot=item.get("text_slot", ""),
                message=f"Copy item is missing trace fields: {', '.join(missing)}",
                suggested_fix_stage="05_figma_assembly",
                source_stage=item.get("source_stage") or "05_figma_assembly",
                source_field=item.get("source_field") or "copy_map.items[]",
            ))
    return issues


def _check_copy_fit_status(context: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    for item in context["copy_map"].get("items", []):
        if item.get("fit_status") != "too_long":
            continue
        source_stage = item.get("source_stage", "05_figma_assembly")
        text = item.get("text_value", "")
        suggested = source_stage if source_stage in {"01_event_brief", "02_content_planning"} and len(text) > 60 else "05_figma_assembly"
        issues.append(_issue(
            code="copy_too_long",
            severity="warning",
            frame_id=item.get("frame_id", ""),
            output_id=item.get("output_id", ""),
            text_slot=item.get("text_slot", ""),
            message=f"Copy does not fit the template slot: {item.get('text_slot', '')}",
            suggested_fix_stage=suggested,
            source_stage=source_stage,
            source_field=item.get("source_field", "copy_map.items[].text_value"),
        ))
    return issues


def _check_forbidden_phrases(context: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    forbidden = _forbidden_phrases(context)
    if not forbidden:
        return issues

    for item in context["copy_map"].get("items", []):
        text = item.get("text_value", "")
        for phrase in forbidden:
            if phrase and phrase in text:
                source_stage = item.get("source_stage") or "05_figma_assembly"
                issues.append(_issue(
                    code="banned_word",
                    severity="error",
                    frame_id=item.get("frame_id", ""),
                    output_id=item.get("output_id", ""),
                    text_slot=item.get("text_slot", ""),
                    message=f"Banned phrase found in copy: {phrase}",
                    suggested_fix_stage=_suggest_from_source(source_stage, fallback="05_figma_assembly"),
                    source_stage=source_stage,
                    source_field=item.get("source_field", "copy_map.items[].text_value"),
                ))
    return issues


def _check_required_phrases(context: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    required = context["brief"].get("constraints", {}).get("required_phrases", [])
    if not required:
        return issues

    copy_items = context["copy_map"].get("items", [])
    all_text = "\n".join(item.get("text_value", "") for item in copy_items)
    cta_text = "\n".join(
        item.get("text_value", "")
        for item in copy_items
        if item.get("text_slot") in {"cta", "button", "button_label"}
    )

    for phrase in required:
        if phrase not in all_text:
            issues.append(_issue(
                code=f"required_phrase_missing_{_slug(phrase)}",
                severity="error",
                frame_id="",
                output_id="",
                message=f"Required phrase is missing from final copy: {phrase}",
                suggested_fix_stage="02_content_planning",
                source_stage="01_event_brief",
                source_field="constraints.required_phrases",
            ))

    cta_phrases = [phrase for phrase in required if any(token in phrase for token in ["신청", "예약", "구매", "문의", "보기"])]
    for phrase in cta_phrases:
        if phrase in all_text and phrase not in cta_text:
            issues.append(_issue(
                code="required_cta_phrase_not_in_cta",
                severity="warning",
                frame_id="",
                output_id="",
                text_slot="cta",
                message=f"CTA-oriented required phrase is present but not assigned to a CTA slot: {phrase}",
                suggested_fix_stage="05_figma_assembly",
                source_stage="01_event_brief",
                source_field="constraints.required_phrases",
            ))
    return issues


def _collect_quality_artifacts(run_dir: Path, selected_assets: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    selected_candidate_ids = _selected_candidate_ids(selected_assets or {})
    artifacts: list[dict[str, Any]] = []
    for spec in QUALITY_ARTIFACT_SPECS:
        rel_path = spec["path"]
        path = run_dir / rel_path
        exists = path.exists()
        data = read_json(path, default={}) if exists else {}
        artifacts.append({
            "id": spec["id"],
            "label": spec["label"],
            "stage": spec["stage"],
            "path": str(rel_path),
            "exists": exists,
            "required": bool(spec["required"]),
            "status": _quality_artifact_status(spec["id"], data, exists, selected_candidate_ids),
            "summary": _quality_artifact_summary(spec["id"], data, exists, selected_candidate_ids),
            "missingSeverity": spec["missing_severity"],
        })
    return artifacts


def _quality_artifact_status(
    artifact_id: str,
    data: dict[str, Any],
    exists: bool,
    selected_candidate_ids: set[str] | None = None,
) -> str:
    if not exists:
        return "missing"
    selected_candidate_ids = selected_candidate_ids or set()
    if artifact_id == "selected_assets":
        selections = data.get("selectedAssets", data.get("selections", [])) if isinstance(data, dict) else []
        selected_count = sum(1 for item in selections if item.get("status", item.get("decision")) == "selected")
        return "pass" if selected_count else "fail"
    if artifact_id == "prompt_audit":
        selected_items = _selected_prompt_audit_items(data, selected_candidate_ids)
        if selected_items:
            if any(item.get("status") == "fail" for item in selected_items):
                return "fail"
            if any(item.get("status") == "warning" for item in selected_items):
                return "warning"
            return "pass"
        failed = int(data.get("failed", 0) or 0)
        warnings = int(data.get("warning", 0) or 0)
        return "fail" if failed else ("warning" if warnings else "pass")
    if artifact_id == "generation_quality":
        selected_items = _selected_generation_quality_items(data, selected_candidate_ids)
        if selected_items:
            statuses = {str(item.get("generation_status") or "").lower() for item in selected_items}
            if "failed" in statuses or "error" in statuses:
                return "fail"
            if "placeholder" in statuses or "prompt_only" in statuses:
                return "warning"
            if any(item.get("reference_direction") is None for item in selected_items):
                return "warning"
            return "pass"
        summary = data.get("summary", {})
        failed = int(summary.get("failed_count", 0) or 0)
        if failed:
            return "fail"
        if summary.get("all_reference_direction_applied") is False:
            return "warning"
        return "pass"
    status = str(data.get("status") or data.get("qa_status") or data.get("summary", {}).get("status") or "").lower()
    if status in {"pass", "passed", "ok"}:
        return "pass"
    if status in {"warning", "warn", "pass_with_warnings"}:
        return "warning"
    if status in {"fail", "failed", "revision_required", "error"}:
        return "fail"
    return "present"


def _quality_artifact_summary(
    artifact_id: str,
    data: dict[str, Any],
    exists: bool,
    selected_candidate_ids: set[str] | None = None,
) -> dict[str, Any]:
    if not exists:
        return {}
    selected_candidate_ids = selected_candidate_ids or set()
    if artifact_id == "selected_assets":
        selections = data.get("selectedAssets", data.get("selections", [])) if isinstance(data, dict) else []
        return {
            "selected": sum(1 for item in selections if item.get("status", item.get("decision")) == "selected"),
            "total": len(selections),
            "approvalStatus": data.get("approvalStatus", ""),
        }
    if artifact_id == "prompt_audit":
        selected_items = _selected_prompt_audit_items(data, selected_candidate_ids)
        return {
            "totalPrompts": data.get("totalPrompts", 0),
            "passed": data.get("passed", 0),
            "warning": data.get("warning", 0),
            "failed": data.get("failed", 0),
            "profile": data.get("profile", ""),
            "selectedPromptCount": len(selected_items),
            "selectedFailed": sum(1 for item in selected_items if item.get("status") == "fail"),
            "selectedWarnings": sum(1 for item in selected_items if item.get("status") == "warning"),
        }
    if artifact_id == "generation_quality":
        summary = data.get("summary", {})
        selected_items = _selected_generation_quality_items(data, selected_candidate_ids)
        return {
            "generationMode": data.get("generation_mode", ""),
            "candidateCount": summary.get("candidate_count", 0),
            "generatedCount": summary.get("generated_count", 0),
            "failedCount": summary.get("failed_count", 0),
            "referenceDirectionAppliedCount": summary.get("reference_direction_applied_count", 0),
            "allReferenceDirectionApplied": summary.get("all_reference_direction_applied"),
            "selectedCandidateCount": len(selected_items),
            "selectedGenerated": sum(1 for item in selected_items if item.get("generation_status") == "generated"),
            "selectedPlaceholder": sum(1 for item in selected_items if item.get("generation_status") == "placeholder"),
            "selectedFailed": sum(1 for item in selected_items if item.get("generation_status") in {"failed", "error"}),
        }
    if artifact_id == "reference_quality_report":
        summary = data.get("summary", {})
        return {
            "status": data.get("status", summary.get("status", "")),
            "selected": summary.get("selected", summary.get("selected_count", data.get("selected_count", 0))),
            "rejected": summary.get("rejected", summary.get("rejected_count", data.get("rejected_count", 0))),
            "selectedBadSignal": summary.get("selected_bad_signal", summary.get("selectedBadSignal", 0)),
        }
    if artifact_id == "planning_quality_audit":
        summary = data.get("summary", {})
        return {
            "status": data.get("status", ""),
            "issues": summary.get("issues", 0),
            "blockers": summary.get("blockers", 0),
            "warnings": summary.get("warnings", 0),
        }
    return {"status": data.get("status", "")}


def _selected_candidate_ids(selected_assets: dict[str, Any]) -> set[str]:
    selections = selected_assets.get("selectedAssets", selected_assets.get("selections", [])) if isinstance(selected_assets, dict) else []
    ids: set[str] = set()
    for item in selections:
        if item.get("status", item.get("decision")) != "selected":
            continue
        candidate_id = item.get("id") or item.get("candidateId") or item.get("candidate_id")
        if candidate_id:
            ids.add(str(candidate_id))
    return ids


def _selected_prompt_audit_items(data: dict[str, Any], selected_candidate_ids: set[str]) -> list[dict[str, Any]]:
    if not selected_candidate_ids:
        return []
    return [
        item for item in data.get("items", [])
        if str(item.get("candidateId") or item.get("candidate_id") or "") in selected_candidate_ids
    ]


def _selected_generation_quality_items(data: dict[str, Any], selected_candidate_ids: set[str]) -> list[dict[str, Any]]:
    if not selected_candidate_ids:
        return []
    return [
        item for item in data.get("candidates", [])
        if str(item.get("candidate_id") or item.get("candidateId") or "") in selected_candidate_ids
    ]


def _check_quality_artifacts(quality_artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for artifact in quality_artifacts:
        if not artifact["exists"] and artifact["required"]:
            issues.append(_issue(
                code=f"{artifact['id']}_missing",
                severity=artifact.get("missingSeverity", "warning"),
                frame_id="",
                output_id="",
                message=f"Required QA evidence file is missing: {artifact['path']}.",
                suggested_fix_stage=artifact["stage"],
                source_stage=artifact["stage"],
                source_field=Path(artifact["path"]).name,
            ))
            continue

        status = artifact.get("status")
        if status == "fail":
            summary = artifact.get("summary", {})
            selected_failed = int(summary.get("selectedFailed", 0) or 0)
            issues.append(_issue(
                code=f"{artifact['id']}_failed",
                severity="error" if artifact["id"] in {"planning_quality_audit", "prompt_audit", "selected_assets"} or selected_failed else "warning",
                frame_id="",
                output_id="",
                message=f"QA evidence file reports a failed status: {artifact['path']}.",
                suggested_fix_stage=artifact["stage"],
                source_stage=artifact["stage"],
                source_field=Path(artifact["path"]).name,
            ))
        elif status == "warning":
            issues.append(_issue(
                code=f"{artifact['id']}_warning",
                severity="warning",
                frame_id="",
                output_id="",
                message=f"QA evidence file reports warnings: {artifact['path']}.",
                suggested_fix_stage=artifact["stage"],
                source_stage=artifact["stage"],
                source_field=Path(artifact["path"]).name,
            ))
    return issues


def _attach_quality_trace(
    package_manifest: list[dict[str, Any]],
    selected_assets: dict[str, Any],
    quality_artifacts: list[dict[str, Any]],
) -> None:
    artifact_refs = [
        {
            "id": artifact["id"],
            "path": artifact["path"],
            "status": artifact["status"],
            "exists": artifact["exists"],
            "summary": artifact.get("summary", {}),
        }
        for artifact in quality_artifacts
    ]
    selection_map = _selection_map(selected_assets)
    for record in package_manifest:
        deliverable_id = record.get("deliverableId") or record.get("deliverable_id", "")
        candidate_id = record.get("frameId", "")
        selection = selection_map.get(candidate_id) or selection_map.get(deliverable_id) or {}
        record["qualityEvidence"] = {
            "artifacts": artifact_refs,
            "selection": {
                "candidateId": selection.get("candidateId") or selection.get("candidate_id") or selection.get("id") or candidate_id,
                "deliverableId": deliverable_id,
                "decision": selection.get("status") or selection.get("decision") or "selected",
                "managerNote": selection.get("managerNote") or selection.get("manager_note") or selection.get("notes", ""),
                "sourceFile": selection.get("sourceFile") or selection.get("selected_file") or record.get("sourceExportPath", ""),
            },
        }


def _selection_map(selected_assets: dict[str, Any]) -> dict[str, dict[str, Any]]:
    selections = selected_assets.get("selectedAssets", selected_assets.get("selections", [])) if isinstance(selected_assets, dict) else []
    mapped: dict[str, dict[str, Any]] = {}
    for item in selections:
        for key in [
            item.get("id"),
            item.get("candidateId"),
            item.get("candidate_id"),
            item.get("deliverableId"),
            item.get("deliverable_id"),
        ]:
            if key:
                mapped[str(key)] = item
    return mapped


def _copy_package_files(
    context: dict[str, Any],
    issues: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    run_dir = context["run_dir"]
    blocked_frames = {
        issue.get("frameId")
        for issue in issues
        if issue.get("severity") in {"blocker", "error"} and issue.get("frameId")
    }
    copied_files: list[dict[str, Any]] = []
    missing_files: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []

    for output in context["channel_outputs"].get("outputs", []):
        frame_id = _frame_id(output)
        expected = output.get("expected_export_path", "")
        src = run_dir / expected
        filename = Path(expected).name or f"{output.get('output_id', frame_id)}.png"
        channel = _package_channel(output.get("channel_id", "unknown"))

        final_rel = Path("package") / "final" / filename
        channel_rel = Path("package") / "by-channel" / channel / filename
        final_dest = run_dir / STAGE_ID / final_rel
        channel_dest = run_dir / STAGE_ID / channel_rel

        record = _manifest_record(output, filename, final_rel, channel_rel)
        if not src.exists():
            missing_files.append({
                "frameId": frame_id,
                "sourcePath": _source_export_path(expected),
                "finalPackagePath": str(final_rel),
                "channelPackagePath": str(channel_rel),
            })
            continue

        if frame_id in blocked_frames:
            continue

        final_dest.parent.mkdir(parents=True, exist_ok=True)
        channel_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, final_dest)
        shutil.copy2(src, channel_dest)
        manifest.append(record)
        copied_files.append({
            "frameId": frame_id,
            "sourcePath": _source_export_path(expected),
            "finalPackagePath": str(final_rel),
            "channelPackagePath": str(channel_rel),
        })

    return manifest, {"copiedFiles": copied_files, "missingFiles": missing_files}


def _build_qa_report(
    brief: dict[str, Any],
    channel_outputs: dict[str, Any],
    issues: list[dict[str, Any]],
    package_manifest: list[dict[str, Any]],
    package_copy: dict[str, list[dict[str, Any]]],
    quality_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    blocking = sum(1 for issue in issues if issue.get("severity") == "blocker")
    errors = sum(1 for issue in issues if issue.get("severity") == "error")
    warnings = sum(1 for issue in issues if issue.get("severity") == "warning")
    status = "fail" if blocking or errors else ("warn" if warnings else "pass")

    return {
        "projectStage": "6단계. QA 및 패키징",
        "createdAt": _now(),
        "summary": {
            "frames": len(channel_outputs.get("outputs", [])),
            "issues": len(issues),
            "blocking": blocking,
            "errors": errors,
            "warnings": warnings,
            "status": status,
            "copiedFiles": len(package_copy["copiedFiles"]),
            "missingFiles": len(package_copy["missingFiles"]),
            "qualityArtifacts": {
                "total": len(quality_artifacts),
                "present": sum(1 for item in quality_artifacts if item.get("exists")),
                "missing": sum(1 for item in quality_artifacts if not item.get("exists")),
                "failed": sum(1 for item in quality_artifacts if item.get("status") == "fail"),
                "warnings": sum(1 for item in quality_artifacts if item.get("status") == "warning"),
            },
        },
        "issues": issues,
        "packageManifest": package_manifest,
        "qualityArtifacts": quality_artifacts,
        "revisionNeeded": [
            issue for issue in issues if issue.get("severity") in {"blocker", "error"}
        ],
        "packageCopy": package_copy,
    }


def _build_schema_summary(
    brief: dict[str, Any],
    qa_report: dict[str, Any],
    package_manifest: list[dict[str, Any]],
    quality_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    status_map = {
        "pass": "pass",
        "warn": "pass_with_warnings",
        "fail": "revision_required",
    }
    schema_issues = [_schema_issue(issue) for issue in qa_report.get("issues", [])]
    return {
        "stage": STAGE_ID,
        "event_id": brief["event_id"],
        "qa_status": status_map.get(qa_report["summary"]["status"], "failed"),
        "issues": schema_issues,
        "package_manifest": {
            "event_id": brief["event_id"],
            "package_id": f"{brief['event_id']}-final",
            "files": package_manifest,
            "quality_artifacts": quality_artifacts,
        },
        "quality_artifacts": quality_artifacts,
        "revision_needed": [
            issue for issue in schema_issues if issue.get("status") == "fail"
        ],
        "approval_status": "review_pending",
    }


def _schema_issue(issue: dict[str, Any]) -> dict[str, Any]:
    severity_map = {"blocker": "blocker", "error": "major", "warning": "minor"}
    return {
        "issue_id": issue["issue_id"],
        "status": "fail" if issue.get("severity") in {"blocker", "error"} else "warning",
        "qa_failed": issue.get("severity") in {"blocker", "error"},
        "severity": severity_map.get(issue.get("severity"), "info"),
        "message": issue.get("message", ""),
        "suggested_fix_stage": issue.get("suggested_fix_stage", "06_qa_packaging"),
        "affected_item_id": issue.get("affected_item_id", ""),
        "source_trace": issue.get("source_trace", {"source_stage": "06_qa_packaging", "source_field": "unknown"}),
    }


def _build_notes(qa_report: dict[str, Any], package_manifest: list[dict[str, Any]]) -> str:
    summary = qa_report["summary"]
    quality = summary.get("qualityArtifacts", {})
    lines = [
        "# QA Packaging Notes",
        "",
        f"- Status: {summary['status']}",
        f"- Issues: {summary['issues']} (blocker {summary['blocking']}, error {summary['errors']}, warning {summary['warnings']})",
        f"- Packaged files: {len(package_manifest)}",
        f"- Quality evidence: {quality.get('present', 0)}/{quality.get('total', 0)} present, {quality.get('failed', 0)} failed, {quality.get('warnings', 0)} warning",
        "",
        "## Quality Evidence",
    ]
    for artifact in qa_report.get("qualityArtifacts", []):
        marker = "present" if artifact.get("exists") else "missing"
        lines.append(f"- [{artifact.get('status')}] {artifact.get('path')} ({marker})")
    lines.extend([
        "",
        "## Issues",
    ])
    if qa_report["issues"]:
        lines.extend(
            f"- [{issue['severity']}] {issue['issue_id']}: {issue['message']} -> {issue['suggested_fix_stage']}"
            for issue in qa_report["issues"]
        )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _issue(
    code: str,
    severity: str,
    frame_id: str,
    output_id: str,
    message: str,
    suggested_fix_stage: str,
    source_stage: str,
    source_field: str,
    text_slot: str = "",
) -> dict[str, Any]:
    affected = output_id or frame_id or text_slot or code
    trace = {
        "source_stage": source_stage,
        "source_field": source_field,
    }
    if frame_id:
        trace["frame_id"] = frame_id
    if output_id:
        trace["output_id"] = output_id
    if text_slot:
        trace["text_slot"] = text_slot

    parts = [code, output_id or frame_id or "global", text_slot]
    issue_id = "__".join(_slug(part) for part in parts if part)
    return {
        "issue_id": issue_id,
        "severity": severity,
        "frameId": frame_id,
        "output_id": output_id,
        "text_slot": text_slot,
        "message": message,
        "suggested_fix_stage": suggested_fix_stage,
        "affected_item_id": affected,
        "source_trace": trace,
    }


def _manifest_record(
    output: dict[str, Any],
    filename: str,
    final_rel: Path,
    channel_rel: Path,
) -> dict[str, Any]:
    dimensions = _dimensions(output)
    channel = _package_channel(output.get("channel_id", "unknown"))
    frame_id = _frame_id(output)
    return {
        "frameId": frame_id,
        "frameName": _frame_name(output),
        "channel": channel,
        "channelName": _channel_name(channel),
        "deliverableId": output.get("deliverable_id", ""),
        "template_id": output.get("template_id", ""),
        "width": dimensions["width"],
        "height": dimensions["height"],
        "exportFileName": filename,
        "sourceExportPath": _source_export_path(output.get("expected_export_path", "")),
        "finalPackagePath": str(final_rel),
        "channelPackagePath": str(channel_rel),
    }


def _dimensions(output: dict[str, Any]) -> dict[str, int]:
    expected = output.get("expected_dimensions") or {}
    if expected.get("width") and expected.get("height"):
        return {"width": int(expected["width"]), "height": int(expected["height"])}

    ratio = ""
    template_id = output.get("template_id")
    if template_id:
        try:
            ratio = template_registry.get(template_id).get("ratio", "")
        except Exception:
            ratio = ""
    return _ratio_dimensions(ratio)


def _ratio_dimensions(ratio: str) -> dict[str, int]:
    return {
        "1:1": {"width": 1080, "height": 1080},
        "4:5": {"width": 1080, "height": 1350},
        "4:3": {"width": 1200, "height": 900},
        "16:9": {"width": 1280, "height": 720},
    }.get(ratio, {"width": 0, "height": 0})


def _forbidden_phrases(context: dict[str, Any]) -> list[str]:
    event_banned = context["brief"].get("constraints", {}).get("banned_words", [])
    policy_global = context["forbidden_policy"].get("global", [])
    return sorted({str(item) for item in [*event_banned, *policy_global] if str(item).strip()})


def _suggest_from_source(source_stage: str, fallback: str) -> str:
    return source_stage if source_stage in {
        "01_event_brief",
        "02_content_planning",
        "03_visual_candidates",
        "04_admin_selection",
        "05_figma_assembly",
        "06_qa_packaging",
    } else fallback


def _frame_id(output: dict[str, Any]) -> str:
    output_id = output.get("output_id", "")
    return output_id or output.get("deliverable_id", "")


def _frame_name(output: dict[str, Any]) -> str:
    channel = _channel_name(_package_channel(output.get("channel_id", "unknown")))
    template = output.get("template_id") or output.get("deliverable_id", "")
    return f"{channel} / {template}"


def _package_channel(channel_id: str) -> str:
    try:
        return channel_registry.canonicalize(channel_id)
    except Exception:
        return channel_registry.normalize_token(channel_id) or "unknown"


def _channel_name(channel: str) -> str:
    try:
        return channel_registry.get(channel).get("name", channel)
    except Exception:
        return channel


def _source_export_path(expected_export_path: str) -> str:
    return f"../{expected_export_path}" if expected_export_path else ""


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_") or "issue"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
