from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.marketing_intelligence.insight_brief import build_insight_brief
from services.marketing_intelligence.repository import append_signals, generate_random_seed_signals, update_signal_review


class MarketingInsightBriefTests(unittest.TestCase):
    def test_blocks_when_selected_signals_are_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signals_path = Path(tmp) / "signals.json"
            append_signals(generate_random_seed_signals(count=5, seed=41), signals_path)

            brief = build_insight_brief(event_id="pilot", signals_path=signals_path)

        self.assertEqual("needs_signal_review", brief["status"])
        self.assertEqual(0, brief["selectedSignalCount"])
        self.assertEqual([], brief["evidenceSignalIds"])
        self.assertIn("selected 신호에 없는", brief["doNotClaim"][0])

    def test_ready_brief_uses_only_selected_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signals_path = Path(tmp) / "signals.json"
            append_signals(generate_random_seed_signals(count=6, seed=42), signals_path)
            from services.marketing_intelligence.repository import load_signals
            for item in load_signals(signals_path)[:3]:
                update_signal_review(item["id"], {"decision": "selected", "reasonTags": ["useful_target"]}, signals_path)

            brief = build_insight_brief(event_id="pilot", signals_path=signals_path)

        self.assertEqual("ready", brief["status"])
        self.assertEqual(3, brief["selectedSignalCount"])
        self.assertEqual(3, len(brief["evidenceSignalIds"]))
        self.assertGreaterEqual(len(brief["targetHypotheses"]), 1)


if __name__ == "__main__":
    unittest.main()
