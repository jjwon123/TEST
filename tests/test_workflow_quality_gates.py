from __future__ import annotations

import json
import importlib
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.audit_full_pipeline_health import find_downstream_state_inconsistencies
from scripts import workflow as workflow_module
from scripts.console_server import create_package, recover_persisted_jobs
from scripts.reconcile_run_states import reconcile_status
from scripts.workflow import (
    approve_stage,
    invalidate_downstream_stages,
    mark_stage,
    process_qa_failures,
    setup_run,
)
from services.comfyui.brand_workflows import brand_api_template, choose_brand_workflow
from services.comfyui.preset_adapters import build_api_prompt
from services.comfyui.workflow_registry import list_presets

archive_module = importlib.import_module("pipeline.07_asset_archive.handlers.run_asset_archive")
archive_completion_status = archive_module.archive_completion_status


class WorkflowQualityGateTests(unittest.TestCase):
    def test_brief_input_required_is_registered_run_state(self) -> None:
        states = self._read(Path(__file__).resolve().parents[1] / "core" / "states" / "run-states.json")
        self.assertIn("brief_input_required", states["states"])

    def test_expired_brief_propagates_needs_input_and_blocks_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            event = root / "event"
            event.mkdir()
            source = Path(__file__).resolve().parents[1] / "events" / "june-monsoon-barrier-care"
            shutil.copy2(source / "event-input.json", event / "event-input.json")
            shutil.copy2(source / "brand-guide.json", event / "brand-guide.json")
            runs = root / "runs"
            runs.mkdir()

            with patch.object(workflow_module, "RUNS_DIR", runs):
                run = setup_run(event)
                mark_stage(run, "01_event_brief")

            status = self._read(run / "run-status.json")
            brief = self._read(run / "01_event_brief" / "brief.json")
            self.assertEqual("needs_input", status["stage_status"]["01_event_brief"])
            self.assertEqual("brief_input_required", status["run_state"])
            self.assertEqual("needs_input", brief["approval_status"])
            with self.assertRaisesRegex(SystemExit, "unresolved input"):
                approve_stage(run, "01_event_brief", approver="test")

    def test_failed_qa_cannot_be_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run = self._run(Path(temp))
            with self.assertRaises(SystemExit):
                approve_stage(run, "06_qa_packaging", approver="test")

    def test_error_severity_routes_to_fix_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run = self._run(Path(temp))
            process_qa_failures(run)
            status = self._read(run / "run-status.json")
            self.assertEqual("04_visual_candidates", status["current_stage"])
            self.assertEqual("needs_regeneration", status["stage_status"]["04_visual_candidates"])

    def test_warning_qa_requires_approval_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run = self._run(Path(temp), qa_status="warn", issues=[{
                "issue_id": "generation_warning",
                "severity": "warning",
                "suggested_fix_stage": "04_visual_candidates",
            }])
            with self.assertRaises(SystemExit):
                approve_stage(run, "06_qa_packaging", approver="test")
            approve_stage(run, "06_qa_packaging", approver="test", note="Reviewed placeholder warning.")
            status = self._read(run / "run-status.json")
            self.assertEqual("approved", status["stage_status"]["06_qa_packaging"])

    def test_empty_archive_has_distinct_completion_state(self) -> None:
        self.assertEqual(("done_no_assets", "archived_no_assets"), archive_completion_status([]))
        self.assertEqual(("done", "archived"), archive_completion_status([{"asset_id": "asset"}]))

    def test_archive_handler_records_empty_completion_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            (run / "06_qa_packaging").mkdir(parents=True)
            self._write(run / "06_qa_packaging" / "final-package-manifest.json", [])
            self._write(run / "06_qa_packaging" / "qa-report.json", {
                "summary": {"status": "pass", "frames": 0, "issues": 0, "blocking": 0},
                "issues": [],
            })
            self._write(run / "run-status.json", {"run_id": "test-run", "event_id": "test-event"})
            self._write(run / "event-input.json", {"eventName": "Test Event"})
            with (
                patch.object(archive_module, "_copy_to_assets"),
                patch.object(archive_module, "_upsert_global_index"),
                patch.object(archive_module, "_write_event_index"),
            ):
                result = archive_module.run(run)
            archive = self._read(run / "07_asset_archive" / "asset-archive.json")
            self.assertEqual("done_no_assets", result["status"])
            self.assertEqual("archived_no_assets", result["next_state"])
            self.assertEqual("done_no_assets", archive["summary"]["completion_status"])

    def test_archive_accepts_human_approved_qa_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            (run / "06_qa_packaging").mkdir(parents=True)
            self._write(run / "06_qa_packaging" / "final-package-manifest.json", [{
                "frameId": "instagram_feed_01__key_visual_c01",
                "frameName": "Instagram feed",
                "channel": "instagram_feed",
                "deliverableId": "instagram_feed_01",
                "exportFileName": "feed.png",
                "sourceExportPath": "03_visual_candidates/previews/feed.png",
                "finalPackagePath": "package/final/feed.png",
            }])
            self._write(run / "06_qa_packaging" / "qa-report.json", {
                "summary": {"status": "warn", "frames": 1, "issues": 1, "blocking": 0},
                "issues": [{"severity": "warning", "message": "Human review required."}],
            })
            self._write(run / "approvals.json", {"approvals": [{
                "stage_id": "06_qa_packaging",
                "status": "approved",
                "note": "Reviewed the non-blocking reference warning.",
            }]})
            self._write(run / "run-status.json", {"run_id": "test-run", "event_id": "test-event"})
            self._write(run / "event-input.json", {"eventName": "Test Event"})
            self._write(run / "brand-guide.json", {})
            with (
                patch.object(archive_module, "_copy_to_assets"),
                patch.object(archive_module, "_upsert_global_index"),
                patch.object(archive_module, "_write_event_index"),
            ):
                result = archive_module.run(run)

            archive = self._read(run / "07_asset_archive" / "asset-archive.json")
            self.assertEqual("done", result["status"])
            self.assertEqual(1, archive["summary"]["total_assets"])
            self.assertEqual("warn", archive["assets"][0]["qa_status"])

    def test_archive_rejects_unapproved_qa_warnings(self) -> None:
        self.assertFalse(archive_module._qa_status_allows_archive("warn", False))
        self.assertFalse(archive_module._qa_status_allows_archive("fail", True))

    def test_archive_copy_is_idempotent_and_returns_actual_versioned_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src = root / "source.png"
            dest = root / "approved" / "asset.png"
            src.write_bytes(b"one")
            first = archive_module._safe_copy(src, dest)
            second = archive_module._safe_copy(src, dest)
            src.write_bytes(b"two")
            third = archive_module._safe_copy(src, dest)
            self.assertEqual(dest, first)
            self.assertEqual(dest, second)
            self.assertEqual(dest.with_name("asset_v2.png"), third)

    def test_selected_brand_workflows_exist(self) -> None:
        presets = set(list_presets())
        expected = [
            choose_brand_workflow("cosmetics", "key_visual", "instagram_feed"),
            choose_brand_workflow("cosmetics", "support", "blog_inline_image"),
            choose_brand_workflow("jewelry", "key_visual", "instagram_feed"),
            choose_brand_workflow("jewelry", "support", "blog_inline_image"),
            choose_brand_workflow("bullion", "key_visual", "instagram_feed"),
        ]
        self.assertTrue(all(item in presets for item in expected))

    def test_cosmetics_product_hero_uses_its_authored_brand_graph_at_runtime(self) -> None:
        template = brand_api_template("cosmetics/cosmetic_product_hero_v2")
        self.assertIsNotNone(template)
        self.assertEqual("qwen-image-edit-2511-Q6_K.gguf", template["1"]["inputs"]["unet_name"])
        self.assertIn("exact skincare product source", template["6"]["inputs"]["prompt"])
        self.assertIn("distorted label", template["7"]["inputs"]["prompt"])

        graph = build_api_prompt("cosmetics/cosmetic_product_hero_v2", {
            "product_image": "niacinamide_packshot.png",
            "positive_prompt": "Campaign-specific direction: calm clinical confidence.",
            "negative_prompt": "no neon trend props",
            "seed": 42,
            "filename_prefix": "cosmetics_test",
        })
        self.assertEqual("niacinamide_packshot.png", graph["4"]["inputs"]["image"])
        self.assertIn("exact skincare product source", graph["6"]["inputs"]["prompt"])
        self.assertIn("calm clinical confidence", graph["6"]["inputs"]["prompt"])
        self.assertIn("distorted label", graph["7"]["inputs"]["prompt"])
        self.assertIn("no neon trend props", graph["7"]["inputs"]["prompt"])
        self.assertEqual(42, graph["20"]["inputs"]["seed"])

    def test_reset_upstream_with_completed_downstream_is_inconsistent(self) -> None:
        inconsistent = find_downstream_state_inconsistencies({
            "01_event_brief": "approved",
            "02_content_planning": "approved",
            "03_reference_research": "done",
            "04_visual_candidates": "done",
            "05_admin_selection": "not_started",
            "06_qa_packaging": "approved",
            "07_asset_archive": "done",
        })
        self.assertEqual(2, len(inconsistent))
        self.assertEqual("05_admin_selection", inconsistent[0]["upstream"])

    def test_rerun_invalidates_downstream_stage_states(self) -> None:
        status = {
            "stage_status": {
                "01_event_brief": "approved",
                "02_content_planning": "approved",
                "03_reference_research": "done",
                "04_visual_candidates": "done",
                "05_admin_selection": "done",
                "06_qa_packaging": "approved",
                "07_asset_archive": "done",
            },
        }
        invalidated = invalidate_downstream_stages(status, "04_visual_candidates")
        self.assertEqual(
            ["05_admin_selection", "06_qa_packaging", "07_asset_archive"],
            invalidated,
        )
        self.assertEqual("locked", status["stage_status"]["06_qa_packaging"])
        self.assertEqual("04_visual_candidates", status["stale_stages"]["07_asset_archive"]["invalidated_by"])

    def test_unexpected_stage_error_is_recorded_and_does_not_leave_in_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run = self._run(Path(temp))
            with patch("scripts.workflow.run_stage_handler", side_effect=RuntimeError("provider unavailable")):
                with self.assertRaises(SystemExit):
                    mark_stage(run, "06_qa_packaging")
            status = self._read(run / "run-status.json")
            self.assertEqual("blocked", status["stage_status"]["06_qa_packaging"])
            self.assertEqual("failed", status["run_state"])
            self.assertEqual("RuntimeError", status["stage_failures"]["06_qa_packaging"]["error_type"])
            self.assertIn("provider unavailable", (run / "logs" / "stage-errors.log").read_text(encoding="utf-8"))

    def test_setup_accepts_legacy_purpose_as_objective(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            event = root / "events" / "legacy"
            event.mkdir(parents=True)
            self._write(event / "event-input.json", {"eventName": "Legacy Event", "purpose": "Drive signups"})
            self._write(event / "brand-guide.json", {"brandName": "Legacy Brand"})
            with patch("scripts.workflow.RUNS_DIR", root / "runs"):
                run = setup_run(event)
            self.assertTrue((run / "run-status.json").exists())

    def test_setup_rejects_event_without_objective_or_purpose(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            event = root / "events" / "invalid"
            event.mkdir(parents=True)
            self._write(event / "event-input.json", {"eventName": "Invalid Event"})
            self._write(event / "brand-guide.json", {"brandName": "Brand"})
            with patch("scripts.workflow.RUNS_DIR", root / "runs"):
                with self.assertRaises(ValueError):
                    setup_run(event)

    def test_console_restart_marks_running_jobs_interrupted(self) -> None:
        recovered = recover_persisted_jobs([
            {"job_id": "running-job", "status": "running", "started_at": "2026-06-14T00:00:00Z"},
            {"job_id": "done-job", "status": "done", "started_at": "2026-06-14T00:00:01Z"},
        ])
        self.assertEqual("interrupted", recovered["running-job"]["status"])
        self.assertIn("recovery_note", recovered["running-job"])
        self.assertEqual("done", recovered["done-job"]["status"])

    def test_reconcile_stale_and_legacy_run_states(self) -> None:
        stale = {
            "run_state": "briefing",
            "current_stage": "01_event_brief",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "stage_status": {"01_event_brief": "in_progress"},
            "history": [],
        }
        changes = reconcile_status(stale, cutoff=datetime.now(timezone.utc))
        self.assertEqual("failed", stale["run_state"])
        self.assertEqual("blocked", stale["stage_status"]["01_event_brief"])
        self.assertEqual("StaleInProgress", stale["stage_failures"]["01_event_brief"]["error_type"])
        self.assertEqual("stale_in_progress_to_blocked", changes[0]["type"])

        legacy = {
            "run_state": "done",
            "current_stage": "07_asset_archive",
            "stage_status": {"07_asset_archive": "done_no_assets"},
            "history": [],
        }
        reconcile_status(legacy, cutoff=datetime.now(timezone.utc))
        self.assertEqual("archived_no_assets", legacy["run_state"])

    def test_final_package_requires_qa_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            run.mkdir()
            self._write(run / "run-status.json", {
                "stage_status": {"06_qa_packaging": "review_pending"},
            })
            with patch("scripts.console_server.run_dir_from_id", return_value=run):
                with self.assertRaises(ValueError):
                    create_package("run")
            self.assertFalse((run / "production-package").exists())

    def _run(self, root: Path, qa_status: str = "fail", issues: list[dict] | None = None) -> Path:
        run = root / "run"
        (run / "06_qa_packaging").mkdir(parents=True)
        self._write(run / "run-status.json", {
            "run_state": "review_pending",
            "current_stage": "06_qa_packaging",
            "stage_status": {
                "01_event_brief": "approved",
                "02_content_planning": "approved",
                "03_reference_research": "done",
                "04_visual_candidates": "done",
                "05_admin_selection": "done",
                "06_qa_packaging": "review_pending",
                "07_asset_archive": "locked",
            },
            "history": [],
        })
        self._write(run / "approvals.json", {"approvals": []})
        self._write(run / "06_qa_packaging" / "qa-report.json", {
            "summary": {"status": qa_status},
            "issues": issues if issues is not None else [{
                "issue_id": "generation_failed",
                "severity": "error",
                "suggested_fix_stage": "04_visual_candidates",
                "affected_item_id": "generation_quality",
            }],
        })
        return run

    @staticmethod
    def _write(path: Path, data: dict) -> None:
        path.write_text(json.dumps(data), encoding="utf-8")

    @staticmethod
    def _read(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
