from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.export_ad_planning_review_packet import build_packet, main


class AdPlanningReviewPacketTests(unittest.TestCase):
    def test_packet_surfaces_candidate_and_human_review_blockers(self) -> None:
        dataset = {
            "cases": [
                {"id": "case-1", "eventName": "June Event", "eventType": "seasonal", "product": "Ampoule", "target": "Sensitive skin", "offer": "Gift"},
                {"id": "case-2", "eventName": "Launch", "eventType": "launch", "product": "Cream", "target": "Dry skin", "offer": ""},
            ]
        }
        external = {"results": [{"caseId": "case-1", "status": "provider_unavailable", "providerExecution": [{"status": "missing_api_key"}]}]}
        packet = build_packet(
            dataset=dataset,
            benchmark={"summary": {"status": "incomplete"}},
            external_results=external,
            human_reviews={"reviews": []},
            strategy_examples=[],
            strategy_metrics={"decisions": {"selected": 0, "shortlist": 0}},
            provider="local",
            pilot_limit=2,
        )
        self.assertEqual("human_review_setup_incomplete", packet["summary"]["status"])
        self.assertNotIn("OPENAI_API_KEY_MISSING", packet["summary"]["blockers"])
        self.assertIn("PILOT_CANDIDATE_RESULTS_INCOMPLETE", packet["summary"]["blockers"])
        self.assertEqual("provider_unavailable", packet["benchmarkReviewQueue"][0]["status"])
        self.assertEqual("missing_external_result", packet["benchmarkReviewQueue"][1]["status"])
        self.assertEqual(".tmp/model-benchmarks/ad-strategy-review-sheet.csv", packet["reviewArtifacts"]["strategyReviewSheet"])
        self.assertEqual(".tmp/model-benchmarks/ad-planning-benchmark-review-sheet.csv", packet["reviewArtifacts"]["benchmarkReviewSheet"])

    def test_packet_prioritizes_unreviewed_strategy_examples(self) -> None:
        packet = build_packet(
            dataset={"cases": []},
            benchmark={},
            external_results={"results": []},
            human_reviews={"reviews": []},
            strategy_examples=[
                {"id": "selected", "industry": "cosmetics_skincare", "review": {"decision": "selected"}},
                {"id": "unreviewed", "industry": "cosmetics_skincare", "review": {"decision": "unreviewed"}, "sourceOriginal": {"brand": "Brand", "copy": "Copy"}},
            ],
            strategy_metrics={"decisions": {"selected": 1, "shortlist": 0}},
            provider="local",
            pilot_limit=5,
        )
        self.assertEqual("unreviewed", packet["strategyReviewQueue"][0]["id"])
        self.assertEqual("Brand", packet["strategyReviewQueue"][0]["sourceBrand"])
        self.assertIn("targetInsight", packet["strategyReviewQueue"][0]["missingForSelected"])

    def test_main_writes_json_and_markdown_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset.json"
            benchmark = root / "benchmark.json"
            external = root / "external.json"
            reviews = root / "reviews.json"
            output = root / "packet.json"
            markdown = root / "packet.md"
            dataset.write_text(json.dumps({"cases": [{"id": "case-1", "eventName": "Event", "eventType": "seasonal", "product": "Ampoule", "target": "Target", "offer": ""}]}), encoding="utf-8")
            benchmark.write_text('{"summary":{"status":"incomplete"}}', encoding="utf-8")
            external.write_text('{"results":[]}', encoding="utf-8")
            reviews.write_text('{"reviews":[]}', encoding="utf-8")
            argv = [
                "export_ad_planning_review_packet.py",
                "--dataset", str(dataset),
                "--benchmark", str(benchmark),
                "--external-results", str(external),
                "--reviews", str(reviews),
                "--output", str(output),
                "--markdown", str(markdown),
            ]
            with patch("sys.argv", argv), patch("scripts.export_ad_planning_review_packet.load_examples_for_review", return_value=[]), patch("scripts.export_ad_planning_review_packet.strategy_quality_metrics", return_value={"decisions": {"selected": 0, "shortlist": 0}}):
                self.assertEqual(0, main())
            self.assertTrue(output.exists())
            self.assertTrue(markdown.exists())
            self.assertEqual("case-1", json.loads(output.read_text(encoding="utf-8"))["benchmarkReviewQueue"][0]["caseId"])

    def test_console_review_packet_helper_matches_current_goal_shape(self) -> None:
        from scripts.console_server import ad_planning_review_packet

        packet = ad_planning_review_packet()
        self.assertEqual(20, packet["summary"]["fixedEvaluationCases"])
        self.assertEqual(5, packet["summary"]["pilotLimit"])
        self.assertLessEqual(len(packet["benchmarkReviewQueue"]), 5)
        self.assertIn("strategySelectedOrShortlist", packet["summary"])


if __name__ == "__main__":
    unittest.main()
