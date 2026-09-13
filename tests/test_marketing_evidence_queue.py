from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.marketing_intelligence.evidence_queue import build_evidence_queue, build_and_save_evidence_queue


class MarketingEvidenceQueueTests(unittest.TestCase):
    def test_empty_repository_creates_collection_queue_with_five_pilot_cases(self) -> None:
        queue = build_evidence_queue(dataset=dataset(), plan=plan(), signals=[])

        self.assertEqual(2, queue["summary"]["total"])
        self.assertEqual(1, queue["summary"]["pilotTotal"])
        self.assertEqual(0, queue["summary"]["pilotReady"])
        self.assertEqual("needs_collection", queue["cases"][0]["status"])
        self.assertEqual(["고객 문제", "시기 명분", "검색·시장 흐름"], queue["cases"][0]["gaps"]["evidenceTypeLabels"])
        self.assertTrue(queue["cases"][0]["collectionQueries"])

    def test_unreviewed_scoped_signals_move_event_to_review(self) -> None:
        signals = [
            signal("one", "pilot_topic", "pain", "review", "unreviewed"),
            signal("two", "other_topic", "timing", "weather", "unreviewed"),
        ]

        queue = build_evidence_queue(dataset=dataset(), plan=plan(), signals=signals)
        pilot = queue["cases"][0]

        self.assertEqual("needs_review", pilot["status"])
        self.assertEqual(1, pilot["progress"]["reviewCandidates"])
        self.assertEqual(["one"], pilot["reviewCandidateIds"])
        self.assertEqual(2, len(pilot["gaps"]["missingInputs"]))

    def test_ready_requires_type_coverage_and_source_diversity(self) -> None:
        signals = [
            signal("pain", "pilot_topic", "pain", "review", "selected"),
            signal("timing", "pilot_topic", "timing", "weather", "selected"),
            signal("trend", "pilot_topic", "trend", "google_trends", "selected"),
        ]

        queue = build_evidence_queue(dataset=dataset(), plan=plan(), signals=signals)
        pilot = queue["cases"][0]

        self.assertEqual("ready", pilot["status"])
        self.assertEqual(3, pilot["progress"]["selected"])
        self.assertEqual([], pilot["gaps"]["evidenceTypes"])
        self.assertGreaterEqual(len(pilot["progress"]["sourceTypes"]), 2)

    def test_three_selected_of_one_type_do_not_pass(self) -> None:
        signals = [
            signal("one", "pilot_topic", "pain", "review", "selected"),
            signal("two", "pilot_topic", "pain", "review", "selected"),
            signal("three", "pilot_topic", "pain", "review", "selected"),
        ]

        queue = build_evidence_queue(dataset=dataset(), plan=plan(), signals=signals)
        pilot = queue["cases"][0]

        self.assertNotEqual("ready", pilot["status"])
        self.assertEqual(["timing", "trend"], pilot["gaps"]["evidenceTypes"])
        self.assertEqual(1, pilot["gaps"]["sourceTypesNeeded"])

    def test_distinct_hosts_count_as_independent_sources(self) -> None:
        signals = [
            signal("pain", "pilot_topic", "pain", "public_web", "selected", host="aad.org"),
            signal("timing", "pilot_topic", "timing", "public_web", "selected", host="kma.go.kr"),
            signal("trend", "pilot_topic", "trend", "public_web", "selected", host="euromonitor.com"),
        ]

        queue = build_evidence_queue(dataset=dataset(), plan=plan(), signals=signals)
        pilot = queue["cases"][0]

        self.assertEqual("ready", pilot["status"])
        self.assertEqual(["aad.org", "euromonitor.com", "kma.go.kr"], pilot["progress"]["distinctSources"])

    def test_queue_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset_path = root / "dataset.json"
            plan_path = root / "plan.json"
            signals_path = root / "signals.json"
            output = root / "queue.json"
            import json
            dataset_path.write_text(json.dumps(dataset(), ensure_ascii=False), encoding="utf-8")
            plan_path.write_text(json.dumps(plan(), ensure_ascii=False), encoding="utf-8")
            signals_path.write_text(json.dumps({"signals": []}, ensure_ascii=False), encoding="utf-8")
            result = build_and_save_evidence_queue(
                output=output,
                dataset_path=dataset_path,
                plan_path=plan_path,
                signals_path=signals_path,
            )
            output_exists = output.exists()

        self.assertEqual(2, result["summary"]["total"])
        self.assertTrue(output_exists)


def dataset() -> dict:
    return {
        "cases": [
            {"id": "pilot", "eventName": "장마 이벤트", "eventType": "seasonal", "target": "속당김 고객", "product": "앰플", "offer": ""},
            {"id": "later", "eventName": "나중 이벤트", "eventType": "branding", "target": "미니멀 고객", "product": "크림", "offer": ""},
        ]
    }


def plan() -> dict:
    return {
        "minimumSelectedSignals": 3,
        "minimumSourceTypes": 2,
        "eventTypeRequirements": {
            "seasonal": {"requiredEvidenceTypes": ["pain", "timing", "trend"], "recommendedSourceTypes": ["review", "weather"]},
            "branding": {"requiredEvidenceTypes": ["desire", "objection", "channel_pattern"], "recommendedSourceTypes": ["review", "meta_ad"]},
        },
        "events": [
            {"id": "pilot", "topic": "pilot_topic", "priority": 1, "researchQuestions": ["실제 문제는?"]},
            {"id": "later", "topic": "later_topic", "priority": 2, "researchQuestions": ["실제 욕구는?"]},
        ],
    }


def signal(signal_id: str, topic: str, evidence_type: str, source_type: str, decision: str, *, host: str = "") -> dict:
    return {
        "id": signal_id,
        "industry": "cosmetics_skincare",
        "sourceType": source_type,
        "sourceRef": {"host": host} if host else {},
        "topic": topic,
        "signalText": f"{signal_id} 관찰",
        "normalizedInsight": f"{signal_id} 인사이트",
        "targetSegment": "테스트 고객",
        "evidenceType": evidence_type,
        "strength": 4,
        "freshness": 4,
        "confidence": 4,
        "riskFlags": [],
        "usableFor": ["concept", "copy"],
        "review": {"decision": decision, "reasonTags": [], "reviewNote": ""},
    }


if __name__ == "__main__":
    unittest.main()
