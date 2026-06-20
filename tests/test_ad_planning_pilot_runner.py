from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_ad_planning_pilot import run_pilot


class AdPlanningPilotRunnerTests(unittest.TestCase):
    def test_pilot_local_mode_exports_sheet_packet_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset.json"
            results = root / "results.json"
            reviews = root / "reviews.json"
            report = root / "report.json"
            packet = root / "packet.json"
            markdown = root / "packet.md"
            sheet = root / "sheet.csv"
            benchmark_sheet = root / "benchmark-sheet.csv"
            audit = root / "audit.json"
            summary = root / "summary.json"
            dataset.write_text(
                '{"cases":[{"id":"case-1","eventName":"Event","eventType":"seasonal","product":"Ampoule","target":"Target","offer":""}],"target":{"cases":1}}',
                encoding="utf-8",
            )
            patches = [
                patch("scripts.run_ad_planning_pilot.DATASET_PATH", dataset),
                patch("scripts.run_ad_planning_pilot.DEFAULT_RESULTS", results),
                patch("scripts.run_ad_planning_pilot.DEFAULT_REVIEWS", reviews),
                patch("scripts.run_ad_planning_pilot.DEFAULT_REPORT", report),
                patch("scripts.run_ad_planning_pilot.DEFAULT_OUTPUT", packet),
                patch("scripts.run_ad_planning_pilot.DEFAULT_MARKDOWN", markdown),
                patch("scripts.run_ad_planning_pilot.DEFAULT_SHEET", sheet),
                patch("scripts.run_ad_planning_pilot.DEFAULT_BENCHMARK_REVIEW_SHEET", benchmark_sheet),
                patch("scripts.run_ad_planning_pilot.GOAL_AUDIT_PATH", audit),
                patch("scripts.run_ad_planning_pilot.SUMMARY_PATH", summary),
                patch("scripts.run_ad_planning_pilot.load_examples_for_review", return_value=[]),
                patch("scripts.run_ad_planning_pilot.strategy_quality_metrics", return_value={"decisions": {"selected": 0, "shortlist": 0}}),
                patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            ]
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11]:
                result = run_pilot(limit=1)
            self.assertEqual("candidate_generation_attempted", result["status"])
            self.assertTrue(result["candidateGenerationAttempted"])
            self.assertTrue(packet.exists())
            self.assertTrue(markdown.exists())
            self.assertTrue(sheet.exists())
            self.assertTrue(benchmark_sheet.exists())
            self.assertTrue(audit.exists())
            self.assertTrue(summary.exists())

    def test_pilot_can_still_attempt_openai_generation_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset.json"
            results = root / "results.json"
            reviews = root / "reviews.json"
            report = root / "report.json"
            packet = root / "packet.json"
            markdown = root / "packet.md"
            sheet = root / "sheet.csv"
            benchmark_sheet = root / "benchmark-sheet.csv"
            audit = root / "audit.json"
            summary = root / "summary.json"
            dataset.write_text('{"cases":[],"target":{"cases":0}}', encoding="utf-8")
            with patch("scripts.run_ad_planning_pilot.DATASET_PATH", dataset), patch("scripts.run_ad_planning_pilot.DEFAULT_RESULTS", results), patch("scripts.run_ad_planning_pilot.DEFAULT_REVIEWS", reviews), patch("scripts.run_ad_planning_pilot.DEFAULT_REPORT", report), patch("scripts.run_ad_planning_pilot.DEFAULT_OUTPUT", packet), patch("scripts.run_ad_planning_pilot.DEFAULT_MARKDOWN", markdown), patch("scripts.run_ad_planning_pilot.DEFAULT_SHEET", sheet), patch("scripts.run_ad_planning_pilot.DEFAULT_BENCHMARK_REVIEW_SHEET", benchmark_sheet), patch("scripts.run_ad_planning_pilot.GOAL_AUDIT_PATH", audit), patch("scripts.run_ad_planning_pilot.SUMMARY_PATH", summary), patch("scripts.run_ad_planning_pilot.load_examples_for_review", return_value=[]), patch("scripts.run_ad_planning_pilot.strategy_quality_metrics", return_value={"decisions": {"selected": 0, "shortlist": 0}}), patch("scripts.run_ad_planning_pilot.run_external_cases") as external_mock, patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
                result = run_pilot(limit=5, provider="openai")
        self.assertEqual("candidate_generation_attempted", result["status"])
        external_mock.assert_called_once()

    def test_console_job_starts_planning_pilot_script(self) -> None:
        from scripts.console_server import ROOT, run_planning_pilot_job

        with patch("scripts.console_server.start_process", return_value={"job_id": "job", "status": "running"}) as start_mock:
            job = run_planning_pilot_job({"limit": 5})
        self.assertEqual("job", job["job_id"])
        command, cwd, label = start_mock.call_args.args
        self.assertEqual(ROOT, cwd)
        self.assertIn("scripts/run_ad_planning_pilot.py", command)
        self.assertIn("--limit", command)
        self.assertIn("5", command)
        self.assertEqual("ad planning pilot 5", label)

    def test_console_job_starts_strategy_review_sheet_export(self) -> None:
        from scripts.console_server import ROOT, run_ad_strategy_review_sheet_job

        with patch("scripts.console_server.start_process", return_value={"job_id": "job", "status": "running"}) as start_mock:
            job = run_ad_strategy_review_sheet_job({"mode": "export", "limit": 30})
        self.assertEqual("job", job["job_id"])
        command, cwd, label = start_mock.call_args.args
        self.assertEqual(ROOT, cwd)
        self.assertIn("scripts/manage_ad_strategy_review_sheet.py", command)
        self.assertIn("--limit", command)
        self.assertIn("30", command)
        self.assertEqual("ad strategy review sheet export 30", label)

    def test_console_job_starts_strategy_review_sheet_import_modes(self) -> None:
        from scripts.console_server import ROOT, run_ad_strategy_review_sheet_job

        with patch("scripts.console_server.start_process", return_value={"job_id": "dry", "status": "running"}) as start_mock:
            dry = run_ad_strategy_review_sheet_job({"mode": "import_dry_run"})
        self.assertEqual("dry", dry["job_id"])
        command, cwd, label = start_mock.call_args.args
        self.assertEqual(ROOT, cwd)
        self.assertIn("--import-sheet", command)
        self.assertNotIn("--apply", command)
        self.assertEqual("ad strategy review sheet import dry-run", label)

        with patch("scripts.console_server.start_process", return_value={"job_id": "apply", "status": "running"}) as start_mock:
            applied = run_ad_strategy_review_sheet_job({"mode": "import_apply"})
        self.assertEqual("apply", applied["job_id"])
        command, cwd, label = start_mock.call_args.args
        self.assertEqual(ROOT, cwd)
        self.assertIn("--import-sheet", command)
        self.assertIn("--apply", command)
        self.assertEqual("ad strategy review sheet import apply", label)

    def test_console_job_rejects_unknown_strategy_review_sheet_mode(self) -> None:
        from scripts.console_server import run_ad_strategy_review_sheet_job

        with self.assertRaises(ValueError):
            run_ad_strategy_review_sheet_job({"mode": "surprise"})

    def test_console_job_starts_benchmark_review_sheet_export(self) -> None:
        from scripts.console_server import ROOT, run_ad_planning_benchmark_review_sheet_job

        with patch("scripts.console_server.start_process", return_value={"job_id": "job", "status": "running"}) as start_mock:
            job = run_ad_planning_benchmark_review_sheet_job({"mode": "export", "limit": 5})
        self.assertEqual("job", job["job_id"])
        command, cwd, label = start_mock.call_args.args
        self.assertEqual(ROOT, cwd)
        self.assertIn("scripts/manage_ad_planning_benchmark_review_sheet.py", command)
        self.assertIn("--limit", command)
        self.assertIn("5", command)
        self.assertEqual("ad planning benchmark review sheet export 5", label)

    def test_console_job_starts_benchmark_review_sheet_import_modes(self) -> None:
        from scripts.console_server import ROOT, run_ad_planning_benchmark_review_sheet_job

        with patch("scripts.console_server.start_process", return_value={"job_id": "dry", "status": "running"}) as start_mock:
            dry = run_ad_planning_benchmark_review_sheet_job({"mode": "import_dry_run"})
        self.assertEqual("dry", dry["job_id"])
        command, cwd, label = start_mock.call_args.args
        self.assertEqual(ROOT, cwd)
        self.assertIn("--import-sheet", command)
        self.assertNotIn("--apply", command)
        self.assertEqual("ad planning benchmark review sheet import dry-run", label)

        with patch("scripts.console_server.start_process", return_value={"job_id": "apply", "status": "running"}) as start_mock:
            applied = run_ad_planning_benchmark_review_sheet_job({"mode": "import_apply"})
        self.assertEqual("apply", applied["job_id"])
        command, cwd, label = start_mock.call_args.args
        self.assertEqual(ROOT, cwd)
        self.assertIn("--import-sheet", command)
        self.assertIn("--apply", command)
        self.assertEqual("ad planning benchmark review sheet import apply", label)


if __name__ == "__main__":
    unittest.main()
