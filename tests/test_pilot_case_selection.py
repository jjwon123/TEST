from __future__ import annotations

import unittest

from core.utils.json_io import read_json
from services.ad_strategy.pilot_selection import DEFAULT_EVIDENCE_PLAN, ROOT, pilot_dataset, select_pilot_cases


class PilotCaseSelectionTests(unittest.TestCase):
    def test_real_dataset_uses_the_five_priority_one_events(self) -> None:
        dataset = read_json(
            ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json",
            {"cases": []},
        )

        selected = select_pilot_cases(dataset, limit=5)

        self.assertEqual(
            [
                "season-monsoon-barrier",
                "promotion-gift",
                "launch-serum",
                "education-barrier",
                "branding-minimal",
            ],
            [item["id"] for item in selected],
        )

    def test_custom_dataset_keeps_order_when_plan_ids_are_absent(self) -> None:
        dataset = {"cases": [{"id": "case-2"}, {"id": "case-1"}]}

        selected = select_pilot_cases(dataset, limit=2)

        self.assertEqual(["case-2", "case-1"], [item["id"] for item in selected])

    def test_larger_limit_appends_remaining_cases_without_duplicates(self) -> None:
        plan = read_json(DEFAULT_EVIDENCE_PLAN, {"events": []})
        dataset = {
            "target": {"cases": 3},
            "cases": [
                {"id": "season-summer-brightening"},
                {"id": "promotion-gift"},
                {"id": "season-monsoon-barrier"},
            ],
        }

        selected = pilot_dataset(dataset, limit=3, evidence_plan=plan)

        self.assertEqual({"cases": 3}, selected["target"])
        self.assertEqual(
            ["season-monsoon-barrier", "promotion-gift", "season-summer-brightening"],
            [item["id"] for item in selected["cases"]],
        )

    def test_duplicate_case_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate benchmark case id"):
            select_pilot_cases({"cases": [{"id": "same"}, {"id": "same"}]}, limit=2)


if __name__ == "__main__":
    unittest.main()
