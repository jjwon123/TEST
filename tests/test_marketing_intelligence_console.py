from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.console_server import build_marketing_insight_brief, marketing_signal_packet, review_marketing_signal, run_marketing_signal_job


class MarketingIntelligenceConsoleTests(unittest.TestCase):
    def test_packet_prioritizes_unreviewed_signals(self) -> None:
        signals = [
            signal("selected-one", "selected", "desire"),
            signal("waiting-one", "unreviewed", "pain"),
            signal("waiting-two", "unreviewed", "timing"),
        ]
        with patch("scripts.console_server.load_signals", return_value=signals):
            packet = marketing_signal_packet(limit=2)

        self.assertEqual(2, len(packet["signals"]))
        self.assertEqual(["waiting-one", "waiting-two"], [item["id"] for item in packet["reviewQueue"]])
        self.assertEqual(3, packet["metrics"]["total"])
        self.assertEqual(2, packet["metrics"]["decisions"]["unreviewed"])
        self.assertEqual("우선 검토", packet["reviewQueue"][0]["reviewRecommendation"]["label"])
        self.assertGreaterEqual(packet["reviewQueue"][0]["reviewRecommendation"]["score"], packet["reviewQueue"][1]["reviewRecommendation"]["score"])

    def test_packet_recommends_high_score_signals_first(self) -> None:
        low = signal("low", "unreviewed", "channel_pattern")
        low["strength"] = 2
        high = signal("high", "unreviewed", "pain")
        high["strength"] = 5
        high["confidence"] = 3
        with patch("scripts.console_server.load_signals", return_value=[low, high]):
            packet = marketing_signal_packet(limit=2)

        self.assertEqual(["high", "low"], [item["id"] for item in packet["reviewQueue"]])
        self.assertIn("타깃", packet["reviewQueue"][0]["reviewRecommendation"]["reasons"][0])

    def test_review_signal_returns_updated_packet(self) -> None:
        updated = signal("waiting-one", "selected", "pain")
        with patch("scripts.console_server.update_signal_review", return_value=updated) as update, patch(
            "scripts.console_server.marketing_signal_packet",
            return_value={"signals": [updated], "metrics": {"total": 1}, "reviewQueue": []},
        ):
            result = review_marketing_signal({
                "signalId": "waiting-one",
                "decision": "selected",
                "reasonTags": ["useful_target"],
                "reviewNote": "쓸만한 타깃 가설",
            })

        update.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual("selected", result["signal"]["review"]["decision"])
        self.assertEqual(1, result["marketingSignals"]["metrics"]["total"])

    def test_build_insight_brief_returns_marketing_packet(self) -> None:
        ready = {"status": "needs_signal_review", "selectedSignalCount": 0}
        with patch("scripts.console_server.build_and_save_insight_brief", return_value=ready) as build, patch(
            "scripts.console_server.marketing_signal_packet",
            return_value={"signals": [], "metrics": {"total": 0}, "reviewQueue": [], "insightBrief": ready},
        ):
            result = build_marketing_insight_brief({"minimumSelected": 3})

        build.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual("needs_signal_review", result["insightBrief"]["status"])
        self.assertEqual(0, result["marketingSignals"]["metrics"]["total"])

    def test_console_job_starts_random_signal_collection(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "job", "status": "running"}) as start_mock:
            result = run_marketing_signal_job({"mode": "random_seed", "count": 50, "topic": "daily_random_seed"})

        self.assertEqual("running", result["status"])
        command = start_mock.call_args.args[0]
        self.assertIn("scripts/collect_marketing_signals.py", command)
        self.assertIn("--random-seed", command)
        self.assertIn("--export-review", command)
        self.assertIn("--count", command)
        self.assertIn("50", command)

    def test_console_job_starts_marketing_signal_csv_import_modes(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "dry", "status": "running"}) as start_mock:
            run_marketing_signal_job({"mode": "import_dry_run"})
        self.assertEqual(["--import-review"], start_mock.call_args.args[0][-1:])

        with patch("scripts.console_server.start_process", return_value={"job_id": "apply", "status": "running"}) as start_mock:
            run_marketing_signal_job({"mode": "import_apply"})
        self.assertEqual(["--import-review", "--apply"], start_mock.call_args.args[0][-2:])

    def test_console_job_starts_public_snapshot_import(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "public", "status": "running"}) as start_mock:
            result = run_marketing_signal_job({
                "mode": "public_snapshot",
                "snapshot": ".tmp/public-signals/hsgn.json",
                "topic": "hsgn_summer_tone_care",
            })

        command = start_mock.call_args.args[0]
        self.assertEqual("running", result["status"])
        self.assertIn("--public-snapshot", command)
        self.assertIn(".tmp/public-signals/hsgn.json", command)
        self.assertIn("--export-review", command)

    def test_console_job_starts_public_url_capture(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "capture", "status": "running"}) as start_mock:
            result = run_marketing_signal_job({
                "mode": "public_capture",
                "url": "https://example.test/hsgn",
                "sourceKind": "brand_site",
                "topic": "hsgn_summer_tone_care",
            })

        command = start_mock.call_args.args[0]
        self.assertEqual("running", result["status"])
        self.assertIn("--capture-url", command)
        self.assertIn("https://example.test/hsgn", command)
        self.assertIn("--source-kind", command)
        self.assertIn("brand_site", command)

    def test_console_job_rejects_unknown_marketing_signal_mode(self) -> None:
        with self.assertRaises(ValueError):
            run_marketing_signal_job({"mode": "mystery"})


def signal(signal_id: str, decision: str, evidence_type: str) -> dict:
    return {
        "id": signal_id,
        "industry": "cosmetics_skincare",
        "sourceType": "seed_random",
        "sourceRef": {},
        "collectedAt": "2026-06-18T00:00:00+09:00",
        "topic": "daily_random_seed",
        "signalText": "가설 후보",
        "normalizedInsight": "타깃이 반응할 수 있는 가설",
        "targetSegment": "장마철 속당김 고객",
        "funnelStage": "awareness",
        "evidenceType": evidence_type,
        "strength": 3,
        "freshness": 2,
        "confidence": 1,
        "riskFlags": ["needs_external_validation"],
        "usableFor": ["concept", "copy"],
        "review": {"decision": decision, "reasonTags": [], "reviewNote": ""},
    }


if __name__ == "__main__":
    unittest.main()
