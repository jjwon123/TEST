from __future__ import annotations

import unittest

from scripts.audit_console_ui_playwright import evaluate_console_snapshot


class ConsoleUiPlaywrightAuditTests(unittest.TestCase):
    def test_clean_console_snapshot_passes(self) -> None:
        report = evaluate_console_snapshot(snapshot("광고 기획 검수 데스크\n마케팅 신호 검수", planning_cases=5))

        self.assertEqual("pass", report["status"])
        self.assertTrue(report["checks"]["developerTermsHidden"]["pass"])
        self.assertTrue(report["checks"]["noHorizontalOverflow"]["pass"])

    def test_developer_terms_and_raw_json_fail(self) -> None:
        report = evaluate_console_snapshot(snapshot('provider meta_strategy_123 {"copy":"bad"}', planning_cases=1))

        self.assertEqual("fail", report["status"])
        self.assertIn("developerTermsHidden", report["errors"])
        self.assertIn("rawJsonHidden", report["errors"])

    def test_ab_and_overflow_fail(self) -> None:
        data = snapshot("안 A\n안 B", planning_cases=1)
        data["metrics"]["overflowing"] = [{"tag": "article", "text": "long card"}]

        report = evaluate_console_snapshot(data)

        self.assertEqual("fail", report["status"])
        self.assertIn("abComparisonHidden", report["errors"])
        self.assertIn("noHorizontalOverflow", report["errors"])


def snapshot(body: str, *, planning_cases: int = 0) -> dict:
    return {
        "createdAt": "2026-06-18T00:00:00+00:00",
        "url": "http://127.0.0.1:5177/",
        "viewport": {"width": 1280, "height": 1100},
        "bodyText": body,
        "metrics": {
            "viewportWidth": 1280,
            "bodyScrollWidth": 1280,
            "documentScrollWidth": 1280,
            "planningCases": planning_cases,
            "conceptCards": 15 if planning_cases else 0,
            "copyCards": 12 if planning_cases else 0,
            "signalCards": 0,
            "signalJobButtons": 4,
            "signalRecommendations": 0,
            "overflowing": [],
        },
    }


if __name__ == "__main__":
    unittest.main()
