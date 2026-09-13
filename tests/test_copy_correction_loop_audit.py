from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.audit_copy_correction_loop import build_audit, verify_application


def correction(**overrides):
    value = {
        "id": "correction-1",
        "runId": "benchmark:case-1",
        "eventId": "case-1",
        "eventName": "테스트 이벤트",
        "brandName": "benchmark_cosmetics",
        "industry": "cosmetics_skincare",
        "channelId": "instagram_feed",
        "model": "local",
        "originalCopy": {"firstLine": "기존 문구"},
        "editedCopy": {"firstLine": "수정 문구"},
        "approved": True,
        "createdAt": "2026-06-28T00:00:00+00:00",
    }
    value.update(overrides)
    return value


class CopyCorrectionLoopAuditTests(unittest.TestCase):
    def test_requires_a_real_human_edit(self) -> None:
        report = build_audit(corrections={"records": []})
        self.assertEqual("needs_human_correction", report["status"])
        self.assertEqual(0, report["summary"]["approvedEditedCorrections"])

        unchanged = correction(editedCopy={"firstLine": "기존 문구"})
        report = build_audit(corrections={"records": [unchanged]})
        self.assertEqual("needs_human_correction", report["status"])

    def test_passes_only_when_active_correction_is_applied(self) -> None:
        item = correction()
        pending = build_audit(corrections={"records": [item]})
        self.assertEqual("ready_to_verify", pending["status"])

        failed = build_audit(
            corrections={"records": [item]},
            verification={"appliedIds": [], "cases": []},
            verification_requested=True,
        )
        self.assertEqual("fail", failed["status"])

        passed = build_audit(
            corrections={"records": [item]},
            verification={"appliedIds": ["correction-1"], "cases": []},
            verification_requested=True,
        )
        self.assertEqual("pass", passed["status"])
        self.assertEqual(1, passed["summary"]["verifiedAppliedCorrections"])

    def test_verification_freshly_generates_selected_case(self) -> None:
        dataset = {
            "cases": [{
                "id": "case-1",
                "eventName": "테스트 이벤트",
                "eventType": "promotion",
                "target": "테스트 고객",
                "product": "테스트 앰플",
                "offer": "",
            }]
        }
        results = {
            "results": [{
                "caseId": "case-1",
                "selectedConceptId": "concept_01",
                "concepts": {"candidates": [{"conceptId": "concept_01"}]},
            }]
        }
        package = {
            "correctionSearch": {"appliedIds": ["correction-1"]},
            "outputs": [],
        }
        with patch("scripts.audit_copy_correction_loop.build_copy_package", return_value=package):
            verification = verify_application(
                dataset=dataset,
                results=results,
                corrections={"records": [correction()]},
            )
        self.assertEqual(["correction-1"], verification["appliedIds"])
        self.assertEqual("pass", verification["cases"][0]["status"])
