from __future__ import annotations

import json
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.audit_full_pipeline_health import find_downstream_state_inconsistencies
from scripts.workflow import approve_stage, invalidate_downstream_stages, process_qa_failures
from services.comfyui.brand_workflows import choose_brand_workflow
from services.comfyui.workflow_registry import list_presets

archive_module = importlib.import_module("pipeline.07_asset_archive.handlers.run_asset_archive")
archive_completion_status = archive_module.archive_completion_status


class WorkflowQualityGateTests(unittest.TestCase):
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
