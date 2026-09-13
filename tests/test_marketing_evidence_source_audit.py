from __future__ import annotations

import unittest

from services.marketing_intelligence.source_audit import PILOT_EVENT_IDS, audit_evidence_snapshot


class MarketingEvidenceSourceAuditTests(unittest.TestCase):
    def test_complete_unreviewed_snapshot_passes_with_missing_product_proof_warning(self) -> None:
        observations = []
        for event_id in sorted(PILOT_EVENT_IDS):
            for index, evidence_type in enumerate(("pain", "objection", "trend")):
                observations.append(observation(event_id, evidence_type, index))
        report = audit_evidence_snapshot({
            "policy": {"decision": "unreviewed"},
            "observations": observations,
        })

        self.assertEqual("pass", report["status"])
        self.assertEqual(15, report["summary"]["observations"])
        self.assertTrue(report["summary"]["unreviewedPolicy"])
        self.assertIn("product_proof_intentionally_missing", [item["code"] for item in report["warnings"]])

    def test_missing_provenance_and_raw_structure_fail(self) -> None:
        observations = []
        for event_id in sorted(PILOT_EVENT_IDS):
            for index, evidence_type in enumerate(("pain", "objection", "trend")):
                observations.append(observation(event_id, evidence_type, index))
        observations[0]["methodology"] = ""
        observations[0]["observedText"] = '{"headline":"bad"}'

        report = audit_evidence_snapshot({"policy": {"decision": "unreviewed"}, "observations": observations})

        self.assertEqual("fail", report["status"])
        self.assertIn("missing_provenance", [item["code"] for item in report["errors"]])
        self.assertIn("raw_structure_exposed", [item["code"] for item in report["errors"]])


def observation(event_id: str, evidence_type: str, index: int) -> dict:
    return {
        "eventId": event_id,
        "topic": f"{event_id}_topic",
        "sourceKind": "public_web",
        "sourceName": f"Source {index}",
        "url": f"https://source{index}.example/{event_id}",
        "title": f"Title {index}",
        "publishedAt": "2025-01-01",
        "observedAt": "2026-07-01",
        "methodology": "survey",
        "evidenceType": evidence_type,
        "targetSegment": "검수 대상 고객",
        "observedText": "검수 가능한 길이의 공개 관찰 요약 문장입니다.",
        "normalizedInsight": f"{event_id}에 사용할 수 있는 추상화된 기획 인사이트 {index}",
    }


if __name__ == "__main__":
    unittest.main()
