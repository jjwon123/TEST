from __future__ import annotations

import os
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from scripts.run_ad_planning_pilot import run_pilot


class AdPlanningPilotRunnerTests(unittest.TestCase):
    def test_scorecard_warnings_do_not_block_human_approval(self) -> None:
        from scripts.console_server import scorecard_has_blocking_issue

        self.assertFalse(scorecard_has_blocking_issue({
            "criticalErrorCount": 0,
            "issues": [{"severity": "warning", "id": "copy_critic_revision_unresolved"}],
        }))
        self.assertTrue(scorecard_has_blocking_issue({
            "criticalErrorCount": 1,
            "issues": [],
        }))
        self.assertTrue(scorecard_has_blocking_issue({
            "criticalErrorCount": 0,
            "issues": [{"severity": "error", "id": "missing_required_evidence"}],
        }))

    def test_benchmark_copy_review_persists_edits_and_correction_records(self) -> None:
        from scripts.benchmark_ad_planning import build_brief, build_deliverables
        from scripts.console_server import review_planning_benchmark
        from services.ad_strategy.planning_engine import build_concept_candidates, build_copy_package, score_planning

        case = {
            "id": "case-1",
            "eventType": "seasonal",
            "eventName": "장마철 앰플",
            "product": "세라마이드 앰플",
            "target": "속당김을 느끼는 직장인",
            "offer": "",
        }
        brief = build_brief(case)
        concepts = build_concept_candidates(brief)
        package = build_copy_package(brief, concepts["candidates"][0], build_deliverables(brief))
        result = {
            "caseId": "case-1",
            "status": "complete",
            "provider": "local",
            "selectedConceptId": "concept_01",
            "selectionSource": "human",
            "concepts": concepts,
            "copyPackage": package,
            "scorecard": score_planning(brief, concepts, package),
            "providerExecution": [],
        }
        result["concepts"]["marketingEvidenceStatus"] = "ready"
        result["concepts"]["marketingEvidenceEventId"] = "case-1"
        result["copyPackage"]["marketingEvidenceStatus"] = "ready"
        result["copyPackage"]["marketingEvidenceEventId"] = "case-1"
        for candidate in result["concepts"]["candidates"]:
            candidate["marketingSignalIds"] = ["case-1-s1", "case-1-s2", "case-1-s3"]
        for output in result["copyPackage"]["outputs"]:
            output.setdefault("planningEvidence", {})["marketingSignalIds"] = ["case-1-s1"]
        feed = next(item for item in package["outputs"] if item["channelId"] == "instagram_feed")
        original = json.loads(json.dumps(feed["copy"], ensure_ascii=False))
        edited = {**original, "firstLine": "장마철 속당김, 루틴의 기준부터 다시 봅니다."}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "assets" / "rules" / "cosmetics-planning-benchmark.json"
            results = root / "results.json"
            reviews = root / "reviews.json"
            report = root / "report.json"
            dataset.parent.mkdir(parents=True)
            dataset.write_text(json.dumps({"cases": [case], "target": {"cases": 1}}, ensure_ascii=False), encoding="utf-8")
            results.write_text(json.dumps({"results": [result]}, ensure_ascii=False), encoding="utf-8")
            with patch("scripts.console_server.ROOT", root), patch("scripts.console_server.DEFAULT_RESULTS", results), patch("scripts.console_server.DEFAULT_REVIEWS", reviews), patch("scripts.console_server.DEFAULT_REPORT", report), patch("scripts.console_server.append_correction") as correction_mock, patch("scripts.console_server.strategy_quality_metrics", return_value={}), patch("scripts.console_server.ad_planning_review_packet", return_value={}):
                response = review_planning_benchmark({
                    "caseId": "case-1",
                    "approved": False,
                    "scores": benchmark_rubric(4),
                    "reasonTags": ["good_hook"],
                    "reviewNote": "첫 문장 수정",
                    "edits": [{"channelId": "instagram_feed", "originalCopy": original, "editedCopy": edited}],
                })
                with self.assertRaisesRegex(ValueError, "average human rubric score"):
                    review_planning_benchmark({
                        "caseId": "case-1",
                        "approved": True,
                        "scores": benchmark_rubric(3),
                        "reasonTags": ["weak_insight"],
                        "reviewNote": "평균 점수가 승인 기준에 미달합니다.",
                        "edits": [],
                    })
                before_missing_rationale = results.read_text(encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "reason tag"):
                    review_planning_benchmark({
                        "caseId": "case-1",
                        "approved": False,
                        "scores": benchmark_rubric(4),
                        "reasonTags": [],
                        "reviewNote": "",
                        "edits": [{"channelId": "instagram_feed", "editedCopy": {"firstLine": "저장되면 안 됨"}}],
                    })
                self.assertEqual(before_missing_rationale, results.read_text(encoding="utf-8"))

                invalid_result = json.loads(results.read_text(encoding="utf-8"))
                invalid_result["results"][0]["concepts"]["marketingEvidenceEventId"] = "other-event"
                results.write_text(json.dumps(invalid_result, ensure_ascii=False), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Event-specific"):
                    review_planning_benchmark({
                        "caseId": "case-1",
                        "approved": False,
                        "scores": benchmark_rubric(4),
                        "reasonTags": ["weak_insight"],
                        "reviewNote": "이벤트 전용 근거가 없어 검수를 보류합니다.",
                        "edits": [],
                    })
                results.write_text(before_missing_rationale, encoding="utf-8")

            saved_result = json.loads(results.read_text(encoding="utf-8"))["results"][0]
            saved_feed = next(item for item in saved_result["copyPackage"]["outputs"] if item["channelId"] == "instagram_feed")
            saved_review = json.loads(reviews.read_text(encoding="utf-8"))["reviews"][0]

        self.assertTrue(response["ok"])
        self.assertEqual(original, saved_feed["generatedCopy"])
        self.assertEqual(edited, saved_feed["copy"])
        self.assertTrue(saved_review["edited"])
        self.assertEqual("human", saved_review["conceptSelectionSource"])
        self.assertEqual(4, correction_mock.call_count)
        feed_record = next(
            call.args[0] for call in correction_mock.call_args_list
            if call.args[0]["channelId"] == "instagram_feed"
        )
        self.assertEqual(original, feed_record["originalCopy"])
        self.assertEqual(edited, feed_record["editedCopy"])

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
            pilot_goal_audit = root / "pilot-goal-audit.json"
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
                patch("scripts.run_ad_planning_pilot.PILOT_GOAL_AUDIT_PATH", pilot_goal_audit),
                patch("scripts.run_ad_planning_pilot.SUMMARY_PATH", summary),
                patch("scripts.run_ad_planning_pilot.load_examples_for_review", return_value=[]),
                patch("scripts.run_ad_planning_pilot.strategy_quality_metrics", return_value={"decisions": {"selected": 0, "shortlist": 0}}),
                patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            ]
            with ExitStack() as stack:
                for item in patches:
                    stack.enter_context(item)
                result = run_pilot(limit=1)
            self.assertEqual("candidate_generation_attempted", result["status"])
            self.assertTrue(result["candidateGenerationAttempted"])
            self.assertTrue(packet.exists())
            self.assertTrue(markdown.exists())
            self.assertTrue(sheet.exists())
            self.assertTrue(benchmark_sheet.exists())
            self.assertTrue(audit.exists())
            self.assertTrue(pilot_goal_audit.exists())
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
            pilot_goal_audit = root / "pilot-goal-audit.json"
            summary = root / "summary.json"
            dataset.write_text('{"cases":[],"target":{"cases":0}}', encoding="utf-8")
            with patch("scripts.run_ad_planning_pilot.DATASET_PATH", dataset), patch("scripts.run_ad_planning_pilot.DEFAULT_RESULTS", results), patch("scripts.run_ad_planning_pilot.DEFAULT_REVIEWS", reviews), patch("scripts.run_ad_planning_pilot.DEFAULT_REPORT", report), patch("scripts.run_ad_planning_pilot.DEFAULT_OUTPUT", packet), patch("scripts.run_ad_planning_pilot.DEFAULT_MARKDOWN", markdown), patch("scripts.run_ad_planning_pilot.DEFAULT_SHEET", sheet), patch("scripts.run_ad_planning_pilot.DEFAULT_BENCHMARK_REVIEW_SHEET", benchmark_sheet), patch("scripts.run_ad_planning_pilot.GOAL_AUDIT_PATH", audit), patch("scripts.run_ad_planning_pilot.PILOT_GOAL_AUDIT_PATH", pilot_goal_audit), patch("scripts.run_ad_planning_pilot.SUMMARY_PATH", summary), patch("scripts.run_ad_planning_pilot.load_examples_for_review", return_value=[]), patch("scripts.run_ad_planning_pilot.strategy_quality_metrics", return_value={"decisions": {"selected": 0, "shortlist": 0}}), patch("scripts.run_ad_planning_pilot.run_external_cases") as external_mock, patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
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

    def test_console_job_starts_planning_pilot_connection_copy_mode(self) -> None:
        from scripts.console_server import ROOT, run_planning_pilot_job

        with patch("scripts.console_server.start_process", return_value={"job_id": "job", "status": "running"}) as start_mock:
            job = run_planning_pilot_job({"limit": 20, "selectPendingConcepts": True})
        self.assertEqual("job", job["job_id"])
        command, cwd, label = start_mock.call_args.args
        self.assertEqual(ROOT, cwd)
        self.assertIn("scripts/run_ad_planning_pilot.py", command)
        self.assertIn("--limit", command)
        self.assertIn("20", command)
        self.assertIn("--select-pending-concepts", command)
        self.assertEqual("ad planning pilot connection copy 20", label)

    def test_console_job_starts_marketing_planning_loop_audit_script(self) -> None:
        from scripts.console_server import ROOT, run_marketing_planning_loop_audit_job

        with patch("scripts.console_server.start_process", return_value={"job_id": "audit", "status": "running"}) as start_mock:
            job = run_marketing_planning_loop_audit_job({"run": "runs/example", "minimumSignals": 5})

        self.assertEqual("audit", job["job_id"])
        command, cwd, label = start_mock.call_args.args
        self.assertEqual(ROOT, cwd)
        self.assertIn("scripts/audit_marketing_planning_loop.py", command)
        self.assertIn("--run", command)
        self.assertIn("runs/example", command)
        self.assertIn("--minimum-signals", command)
        self.assertIn("5", command)
        self.assertEqual("marketing planning loop audit 5", label)

    def test_marketing_planning_loop_audit_report_reads_latest_file(self) -> None:
        from scripts.console_server import marketing_planning_loop_audit_report

        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "audit.json"
            report.write_text('{"status":"pass","checks":{"selectedUsableEnough":{"selectedUsable":5}}}', encoding="utf-8")
            with patch("scripts.console_server.MARKETING_PLANNING_LOOP_AUDIT_PATH", report):
                data = marketing_planning_loop_audit_report()

        self.assertEqual("pass", data["status"])
        self.assertEqual(5, data["checks"]["selectedUsableEnough"]["selectedUsable"])

    def test_console_job_starts_cosmetics_pilot_goal_audit_script(self) -> None:
        from scripts.console_server import ROOT, run_cosmetics_pilot_goal_audit_job

        with patch("scripts.console_server.start_process", return_value={"job_id": "pilot-audit", "status": "running"}) as start_mock:
            job = run_cosmetics_pilot_goal_audit_job({"limit": 5})

        self.assertEqual("pilot-audit", job["job_id"])
        command, cwd, label = start_mock.call_args.args
        self.assertEqual(ROOT, cwd)
        self.assertIn("scripts/audit_cosmetics_pilot_goal.py", command)
        self.assertIn("--limit", command)
        self.assertIn("5", command)
        self.assertEqual("cosmetics pilot goal audit 5", label)

    def test_cosmetics_pilot_goal_audit_report_reads_latest_file(self) -> None:
        from scripts.console_server import cosmetics_pilot_goal_audit_report

        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "audit.json"
            report.write_text('{"status":"fail","summary":{"criticalErrorCount":2}}', encoding="utf-8")
            with patch("scripts.console_server.COSMETICS_PILOT_GOAL_AUDIT_PATH", report):
                data = cosmetics_pilot_goal_audit_report()

        self.assertEqual("fail", data["status"])
        self.assertEqual(2, data["summary"]["criticalErrorCount"])

    def test_console_job_starts_copy_correction_loop_audit(self) -> None:
        from scripts.console_server import ROOT, run_copy_correction_loop_audit_job

        with patch("scripts.console_server.start_process", return_value={"job_id": "correction-audit", "status": "running"}) as start_mock:
            job = run_copy_correction_loop_audit_job({"verifyApplication": True})

        self.assertEqual("correction-audit", job["job_id"])
        command, cwd, label = start_mock.call_args.args
        self.assertEqual(ROOT, cwd)
        self.assertIn("scripts/audit_copy_correction_loop.py", command)
        self.assertIn("--verify-application", command)
        self.assertEqual("copy correction learning audit", label)

    def test_copy_correction_loop_audit_report_reads_latest_file(self) -> None:
        from scripts.console_server import copy_correction_loop_audit_report

        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "audit.json"
            report.write_text('{"status":"pass","summary":{"verifiedAppliedCorrections":1}}', encoding="utf-8")
            with patch("scripts.console_server.COPY_CORRECTION_LOOP_AUDIT_PATH", report):
                data = copy_correction_loop_audit_report()

        self.assertEqual("pass", data["status"])
        self.assertEqual(1, data["summary"]["verifiedAppliedCorrections"])

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


def benchmark_rubric(value: int) -> dict[str, int]:
    return {
        key: value
        for key in (
            "strategyClarity",
            "targetEmpathy",
            "productConnection",
            "distinctiveness",
            "channelFit",
            "koreanCopyQuality",
            "brandFit",
            "actionability",
        )
    }


if __name__ == "__main__":
    unittest.main()
