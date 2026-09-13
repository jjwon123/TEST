#!/usr/bin/env python3
"""Run an isolated 01→07 workflow smoke test with a real local image file.

The smoke test proves orchestration, gates, file selection, QA approval, and
archive copying without writing to production ``runs/`` or ``assets/``.
Human approvals are explicitly tagged ``smoke_test`` and are valid only inside
the generated ``.tmp/full-pipeline-smoke/<session>`` directory.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json
from core.utils.module_loader import load_callable_from_path
from scripts import workflow
from scripts.audit_planning_quality import build_audit as build_planning_audit
from scripts.audit_visual_prompts import build_markdown as build_prompt_audit_markdown
from scripts.audit_visual_prompts import build_prompt_audit
from services.ad_strategy import planning_engine
from services.ad_strategy.generation import generate_copy


DEFAULT_EVENT = ROOT / "events" / "june-monsoon-barrier-care"
DEFAULT_INSIGHT = ROOT / "design_brain_wiki" / "marketing_signals" / "insight-briefs" / "season-monsoon-barrier.json"
DEFAULT_IMAGE = ROOT / "products" / "cosmetic" / "hsgn_niacinamide" / "niacinamide_packshot.png"
DEFAULT_OUTPUT_ROOT = ROOT / ".tmp" / "full-pipeline-smoke"
SMOKE_EVENT_ID = "full-pipeline-smoke"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path, default=DEFAULT_EVENT)
    parser.add_argument("--insight", type=Path, default=DEFAULT_INSIGHT)
    parser.add_argument("--fixture-image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--concept-id", default="concept_03")
    args = parser.parse_args()

    output_root = _safe_output_root(args.output_root)
    session_root = output_root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    session_root.mkdir(parents=True, exist_ok=False)
    report_path = session_root / "report.json"
    latest_path = output_root / "latest-report.json"

    report: dict[str, Any]
    try:
        report = run_smoke(
            session_root=session_root,
            source_event=args.event.resolve(),
            insight_source=args.insight.resolve(),
            fixture_image=args.fixture_image.resolve(),
            concept_id=args.concept_id,
        )
    except Exception as exc:
        report = {
            "schemaVersion": "1.0.0",
            "createdAt": _now(),
            "status": "fail",
            "sessionRoot": str(session_root),
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc().splitlines()[-12:],
        }

    write_json(report_path, report)
    write_json(latest_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "pass" else 1


def run_smoke(
    *,
    session_root: Path,
    source_event: Path,
    insight_source: Path,
    fixture_image: Path,
    concept_id: str,
) -> dict[str, Any]:
    _require_file(source_event / "event-input.json")
    _require_file(source_event / "brand-guide.json")
    _require_file(insight_source)
    _require_file(fixture_image)

    event_dir = session_root / "event" / SMOKE_EVENT_ID
    event_dir.mkdir(parents=True)
    shutil.copy2(source_event / "event-input.json", event_dir / "event-input.json")
    shutil.copy2(source_event / "brand-guide.json", event_dir / "brand-guide.json")
    if (source_event / "research-evidence.json").exists():
        shutil.copy2(source_event / "research-evidence.json", event_dir / "research-evidence.json")

    event_input = read_json(event_dir / "event-input.json")
    start = date.today() + timedelta(days=2)
    event_input["eventType"] = "seasonal"
    event_input["schedule"] = {
        "startDate": start.isoformat(),
        "publishDate": start.isoformat(),
        "endDate": (start + timedelta(days=21)).isoformat(),
    }
    write_json(event_dir / "event-input.json", event_input)

    insight_root = session_root / "marketing-signals"
    insight = read_json(insight_source)
    insight["eventId"] = SMOKE_EVENT_ID
    insight["status"] = "ready"
    write_json(insight_root / "insight-brief.json", insight)
    write_json(insight_root / "insight-briefs" / f"{SMOKE_EVENT_ID}.json", insight)

    runs_root = session_root / "runs"
    archive_root = session_root / "archive-root"
    runs_root.mkdir()
    _prepare_archive_root(archive_root)

    original_runs_dir = workflow.RUNS_DIR
    original_insight_path = planning_engine.INSIGHT_BRIEF_PATH
    original_handler = workflow.run_stage_handler
    original_generation_mode = os.environ.get("COMFYUI_GENERATION_MODE")
    run_dir: Path | None = None

    try:
        workflow.RUNS_DIR = runs_root
        planning_engine.INSIGHT_BRIEF_PATH = insight_root / "insight-brief.json"
        workflow.run_stage_handler = _isolated_handler(original_handler, archive_root)
        os.environ["COMFYUI_GENERATION_MODE"] = "stub"

        run_dir = workflow.setup_run(event_dir)
        _run_and_approve_brief(run_dir)
        planning_score = _run_and_approve_planning(run_dir, concept_id)
        _write_planning_audit(run_dir)

        workflow.mark_stage(run_dir, "03_reference_research")
        workflow.mark_stage(run_dir, "04_visual_candidates")
        prompt_audit = _write_prompt_audit(run_dir)
        _assert_prompt_audit_clean(prompt_audit)

        _materialize_real_fixture(run_dir, fixture_image)
        _select_first_candidate_per_group(run_dir)
        workflow.mark_stage(run_dir, "05_admin_selection")
        workflow.mark_stage(run_dir, "06_qa_packaging")

        qa_report = read_json(run_dir / "06_qa_packaging" / "qa-report.json")
        failed_issues = _failed_qa_issues(qa_report)
        if failed_issues:
            raise RuntimeError(f"QA contains blocking issues: {failed_issues}")
        qa_status = str(qa_report.get("summary", {}).get("status") or "")
        approval_note = "Smoke test reviewed non-blocking QA warnings." if qa_status == "warn" else "Smoke test QA pass."
        workflow.approve_stage(run_dir, "06_qa_packaging", "smoke_test", approval_note)
        workflow.mark_stage(run_dir, "07_asset_archive")

        status = read_json(run_dir / "run-status.json")
        archive = read_json(run_dir / "07_asset_archive" / "asset-archive.json")
        selected = read_json(run_dir / "04_admin_selection" / "selected-assets.json")
        assets = archive.get("assets", [])
        copied_files = list((archive_root / "assets" / "approved").rglob("*.png"))
        checks = {
            "allStagesTerminal": all(
                status.get("stage_status", {}).get(stage_id) in {"approved", "done"}
                for stage_id in [
                    "01_event_brief", "02_content_planning", "03_reference_research",
                    "04_visual_candidates", "05_admin_selection", "06_qa_packaging",
                    "07_asset_archive",
                ]
            ),
            "planningScoreAtLeastFour": float(planning_score.get("averageScore") or 0) >= 4,
            "promptAuditClean": prompt_audit.get("failed") == 0 and prompt_audit.get("warning") == 0,
            "qaHasNoBlockingIssues": not failed_issues,
            "selectedAssetsPresent": len(selected.get("selectedAssets", [])) > 0,
            "archiveAssetsPresent": len(assets) > 0,
            "approvedFilesCopied": len(copied_files) == len(assets),
            "archiveIsIsolated": all(_is_relative_to(path.resolve(), archive_root.resolve()) for path in copied_files),
        }
        passed = all(checks.values())
        return {
            "schemaVersion": "1.0.0",
            "createdAt": _now(),
            "status": "pass" if passed else "fail",
            "scope": "orchestration_and_filesystem_smoke_only",
            "contentAcceptance": False,
            "sessionRoot": str(session_root),
            "run": str(run_dir),
            "archiveRoot": str(archive_root),
            "runState": status.get("run_state"),
            "stageStatus": status.get("stage_status", {}),
            "planningScore": planning_score.get("averageScore"),
            "promptAudit": {
                "total": prompt_audit.get("totalPrompts"),
                "passed": prompt_audit.get("passed"),
                "warning": prompt_audit.get("warning"),
                "failed": prompt_audit.get("failed"),
            },
            "qaStatus": qa_status,
            "qaWarningsApprovedForSmoke": qa_status == "warn",
            "selectedAssets": len(selected.get("selectedAssets", [])),
            "archiveAssets": len(assets),
            "archivedQaStatuses": sorted({str(item.get("qa_status") or "") for item in assets}),
            "copiedApprovedFiles": len(copied_files),
            "checks": checks,
        }
    finally:
        workflow.RUNS_DIR = original_runs_dir
        planning_engine.INSIGHT_BRIEF_PATH = original_insight_path
        workflow.run_stage_handler = original_handler
        if original_generation_mode is None:
            os.environ.pop("COMFYUI_GENERATION_MODE", None)
        else:
            os.environ["COMFYUI_GENERATION_MODE"] = original_generation_mode


def _isolated_handler(original_handler: Any, archive_root: Path) -> Any:
    def handler(
        run_dir: Path,
        stage: workflow.Stage,
        mode: str,
        outputs: list[str] | None,
        group: str | None = None,
    ) -> workflow.StageResult | None:
        if stage.id == "02_content_planning":
            fn = load_callable_from_path(workflow.STAGE_HANDLERS[stage.id], "run")
            fn.__globals__["import_legacy_as_unreviewed"] = lambda: 0
            result = fn(run_dir=run_dir, mode=mode, outputs=outputs, group=group)
            return workflow.StageResult.from_handler_output(stage.id, result, stage.pending_state)
        if stage.id == "07_asset_archive":
            fn = load_callable_from_path(workflow.STAGE_HANDLERS[stage.id], "run")
            fn.__globals__["ROOT"] = archive_root
            result = fn(run_dir=run_dir, mode=mode, outputs=outputs, group=group)
            return workflow.StageResult.from_handler_output(stage.id, result, stage.pending_state)
        return original_handler(run_dir, stage, mode, outputs, group=group)

    return handler


def _run_and_approve_brief(run_dir: Path) -> None:
    workflow.mark_stage(run_dir, "01_event_brief")
    brief = read_json(run_dir / "01_event_brief" / "brief.json")
    if brief.get("open_questions"):
        raise RuntimeError(f"Brief has unresolved questions: {brief['open_questions']}")
    workflow.approve_stage(run_dir, "01_event_brief", "smoke_test", "Isolated future-date smoke approval.")


def _run_and_approve_planning(run_dir: Path, concept_id: str) -> dict[str, Any]:
    workflow.mark_stage(run_dir, "02_content_planning")
    stage_dir = run_dir / "02_content_planning"
    candidates = read_json(stage_dir / "concept-candidates.json")
    selected = next(
        (item for item in candidates.get("candidates", []) if item.get("conceptId") == concept_id),
        None,
    )
    if selected is None:
        raise RuntimeError(f"Concept not found: {concept_id}")

    rejected = [
        item.get("conceptId")
        for item in candidates.get("candidates", [])
        if item.get("conceptId") != concept_id
    ]
    brief = read_json(run_dir / "01_event_brief" / "brief.json")
    content_plan = read_json(stage_dir / "content-plan.json")
    copy_package = generate_copy(brief, selected, content_plan.get("deliverables", []), run_dir)
    score = planning_engine.score_planning(brief, candidates, copy_package)
    if score.get("status") != "pass" or score.get("issues") or score.get("criticalErrorCount"):
        raise RuntimeError(f"Planning gate is not clean: {score}")

    write_json(stage_dir / "concept-review.json", {
        "schemaVersion": "1.0.0",
        "status": "approved",
        "selectedConceptId": concept_id,
        "rejectedConceptIds": rejected,
        "reasonTags": ["smoke_test"],
        "reviewNote": "Isolated smoke approval; not production human review.",
        "approvedAt": _now(),
    })
    write_json(stage_dir / "selected-concept.json", {
        "schemaVersion": "1.0.0",
        "status": "approved",
        "concept": selected,
    })
    write_json(stage_dir / "copy-package.json", copy_package)
    write_json(stage_dir / "copy-review.json", {
        "schemaVersion": "1.0.0",
        "status": "approved",
        "approved": True,
        "edits": [],
        "reasonTags": ["smoke_test"],
        "reviewNote": "Isolated smoke approval; not production human review.",
        "reviewedAt": _now(),
    })
    write_json(stage_dir / "planning-scorecard.json", score)
    workflow.approve_stage(run_dir, "02_content_planning", "smoke_test", "Isolated concept/copy smoke approval.")
    return score


def _write_planning_audit(run_dir: Path) -> None:
    audit = build_planning_audit(run_dir)
    if audit.get("status") != "pass":
        raise RuntimeError(f"Planning audit failed: {audit.get('issues', [])}")
    write_json(run_dir / "planning-quality" / "planning-quality-audit.json", audit)


def _write_prompt_audit(run_dir: Path) -> dict[str, Any]:
    audit = build_prompt_audit(run_dir)
    output_dir = run_dir / "03_visual_candidates"
    write_json(output_dir / "prompt-audit.json", audit)
    (output_dir / "prompt-audit.md").write_text(build_prompt_audit_markdown(audit), encoding="utf-8")
    return audit


def _assert_prompt_audit_clean(audit: dict[str, Any]) -> None:
    if int(audit.get("failed") or 0) or int(audit.get("warning") or 0):
        sample = [
            {"candidateId": item.get("candidateId"), "status": item.get("status"), "notes": item.get("notes")}
            for item in audit.get("items", [])
            if item.get("status") != "pass"
        ][:3]
        raise RuntimeError(f"Prompt audit is not clean: {sample}")


def _materialize_real_fixture(run_dir: Path, fixture_image: Path) -> None:
    manifest_path = run_dir / "03_visual_candidates" / "candidate-manifest.json"
    quality_path = run_dir / "03_visual_candidates" / "generation-quality.json"
    manifest = read_json(manifest_path)
    quality = read_json(quality_path)
    previews_dir = run_dir / "03_visual_candidates" / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    selected_ids = {
        str(group["candidate_ids"][0])
        for group in manifest.get("regeneration_groups", [])
        if group.get("candidate_ids")
    }
    shared_target = previews_dir / "smoke-fixture-unselected.png"
    shutil.copy2(fixture_image, shared_target)
    paths_by_candidate: dict[str, str] = {}

    for candidate in manifest.get("candidates", []):
        candidate_id = str(candidate.get("candidate_id") or "")
        target = shared_target
        if candidate_id in selected_ids:
            target = previews_dir / f"{candidate_id}.png"
            shutil.copy2(fixture_image, target)
        relative = target.relative_to(run_dir).as_posix()
        paths_by_candidate[candidate_id] = relative
        candidate.update({
            "image_path": relative,
            "preview_path": relative,
            "generation_status": "generated",
            "generation_mode": "smoke_fixture",
            "status": "generated",
        })
    write_json(manifest_path, manifest)

    quality_candidates = quality.get("candidates", [])
    for candidate in quality_candidates:
        relative = paths_by_candidate[str(candidate.get("candidate_id") or "")]
        target = run_dir / relative
        candidate.update({
            "generation_status": "generated",
            "generation_mode": "smoke_fixture",
            "output_path": relative,
            "image": {
                "path": relative,
                "exists": True,
                "file_size_bytes": target.stat().st_size,
            },
        })
    quality["generation_mode"] = "smoke_fixture"
    quality.setdefault("summary", {}).update({
        "generated_count": len(quality_candidates),
        "failed_count": 0,
        "all_generated": True,
    })
    write_json(quality_path, quality)


def _select_first_candidate_per_group(run_dir: Path) -> None:
    manifest = read_json(run_dir / "03_visual_candidates" / "candidate-manifest.json")
    decisions = [
        {
            "candidate_id": group["candidate_ids"][0],
            "decision": "selected",
            "manager_note": "Isolated filesystem smoke selection.",
        }
        for group in manifest.get("regeneration_groups", [])
        if group.get("candidate_ids")
    ]
    if not decisions:
        raise RuntimeError("No candidate groups are available for selection.")
    write_json(run_dir / "selection.json", {"reviewer": "smoke_test", "decisions": decisions})


def _failed_qa_issues(qa_report: dict[str, Any]) -> list[str]:
    return [
        str(item.get("issue_id") or item.get("message") or "unknown")
        for item in qa_report.get("issues", [])
        if item.get("status") == "fail"
        or item.get("qa_failed") is True
        or item.get("severity") in {"error", "blocker"}
    ]


def _prepare_archive_root(archive_root: Path) -> None:
    for relative in [
        Path("core/policies/archive-reuse-policy.json"),
        Path("pipeline/07_asset_archive/input.schema.json"),
        Path("pipeline/07_asset_archive/output.schema.json"),
    ]:
        destination = archive_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)


def _safe_output_root(value: Path) -> Path:
    path = value.resolve() if value.is_absolute() else (ROOT / value).resolve()
    allowed = (ROOT / ".tmp").resolve()
    if not _is_relative_to(path, allowed) or path == allowed:
        raise SystemExit(f"Smoke output must be a child of {allowed}: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
