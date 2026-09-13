from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.marketing_intelligence.insight_brief import build_insight_brief, save_insight_brief
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
        self.assertEqual(
            "사람이 선택한 근거에 없는 순위, 가격, 효능, 기간 수치를 만들지 않는다.",
            brief["doNotClaim"][0],
        )
        self.assertTrue(all("selected" not in item and "seed_random" not in item for item in brief["doNotClaim"]))

    def test_ready_brief_uses_only_selected_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signals_path = Path(tmp) / "signals.json"
            append_signals(generate_random_seed_signals(count=6, seed=42, topic="pilot_topic"), signals_path)
            from services.marketing_intelligence.repository import load_signals
            for item in load_signals(signals_path)[:3]:
                update_signal_review(item["id"], {"decision": "selected", "reasonTags": ["useful_target"]}, signals_path)

            brief = build_insight_brief(event_id="pilot", topic="pilot_topic", signals_path=signals_path)

        self.assertEqual("ready", brief["status"])
        self.assertEqual(3, brief["selectedSignalCount"])
        self.assertEqual(3, len(brief["evidenceSignalIds"]))
        self.assertGreaterEqual(len(brief["targetHypotheses"]), 1)
        self.assertEqual(3, len(brief["evidenceDetails"]))
        self.assertEqual(
            {"signalId", "evidenceType", "targetSegment", "insight", "sourceType", "sourceName", "observedAt", "claimBoundary"},
            set(brief["evidenceDetails"][0]),
        )

    def test_brief_excludes_selected_signals_with_blocked_capture_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signals_path = Path(tmp) / "signals.json"
            append_signals([
                _signal("good-1", "trend", []),
                _signal("good-2", "pain", []),
                _signal("good-3", "proof", []),
                _signal("bad-raw-json", "trend", ["capture_quality_blocked", "raw_json_detected"]),
            ], signals_path)

            brief = build_insight_brief(event_id="pilot", signals_path=signals_path)

        self.assertEqual("ready", brief["status"])
        self.assertEqual(3, brief["selectedSignalCount"])
        self.assertNotIn("bad-raw-json", brief["evidenceSignalIds"])

    def test_brief_excludes_selected_signals_from_another_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signals_path = Path(tmp) / "signals.json"
            append_signals([
                _signal("pilot-1", "trend", [], event_id="pilot"),
                _signal("pilot-2", "pain", [], event_id="pilot"),
                _signal("pilot-3", "proof", [], event_id="pilot"),
                _signal("other-1", "trend", [], event_id="other-event"),
                _signal("other-2", "pain", [], event_id="other-event"),
                _signal("other-3", "proof", [], event_id="other-event"),
            ], signals_path)

            brief = build_insight_brief(event_id="pilot", signals_path=signals_path)

        self.assertEqual("ready", brief["status"])
        self.assertEqual(["pilot-1", "pilot-2", "pilot-3"], brief["evidenceSignalIds"])

    def test_default_save_also_writes_event_scoped_brief(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            latest = root / "insight-brief.json"
            brief = {
                "schemaVersion": "1.0.0",
                "eventId": "Launch Serum",
                "industry": "cosmetics_skincare",
                "status": "needs_signal_review",
                "minimumSelectedSignals": 3,
                "selectedSignalCount": 0,
                "targetHypotheses": [],
                "customerPains": [],
                "customerDesires": [],
                "purchaseObjections": [],
                "trendHooks": [],
                "seasonalHooks": [],
                "productProofs": [],
                "offerAngles": [],
                "channelPatterns": [],
                "doNotClaim": [],
                "evidenceSignalIds": [],
                "createdAt": "2026-06-30T00:00:00+00:00",
            }
            from unittest.mock import patch
            with patch("services.marketing_intelligence.insight_brief.INSIGHT_BRIEF_PATH", latest):
                save_insight_brief(brief, latest)
            scoped = root / "insight-briefs" / "launch-serum.json"
            scoped_exists = scoped.exists()

        self.assertTrue(scoped_exists)

    def test_event_scoped_filename_preserves_readable_korean(self) -> None:
        from services.marketing_intelligence.insight_brief import event_insight_brief_path

        path = event_insight_brief_path("장마철 수분 장벽", root=Path("briefs"))

        self.assertEqual("장마철-수분-장벽.json", path.name)


def _signal(signal_id: str, evidence_type: str, risk_flags: list[str], *, event_id: str = "pilot") -> dict:
    return {
        "id": signal_id,
        "industry": "cosmetics_skincare",
        "sourceType": "brand_site",
        "sourceRef": {"eventId": event_id},
        "topic": "general_cosmetics",
        "signalText": f"{signal_id} observed text",
        "normalizedInsight": f"{signal_id} normalized insight",
        "targetSegment": f"{signal_id} target",
        "funnelStage": "awareness",
        "evidenceType": evidence_type,
        "strength": 4,
        "freshness": 4,
        "confidence": 4,
        "riskFlags": risk_flags,
        "usableFor": ["concept", "copy"],
        "review": {"decision": "selected", "reasonTags": ["useful_target"], "reviewNote": ""},
    }


if __name__ == "__main__":
    unittest.main()
