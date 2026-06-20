from __future__ import annotations

import unittest

from scripts.pretag_session_with_taste import taste_decision


class TasteDecisionTests(unittest.TestCase):
    def test_thresholds_map_score_to_decision(self) -> None:
        self.assertEqual("selected", taste_decision(80))
        self.assertEqual("selected", taste_decision(55))
        self.assertEqual("shortlist", taste_decision(40))
        self.assertEqual("shortlist", taste_decision(25))
        self.assertEqual("rejected", taste_decision(10))
        self.assertEqual("rejected", taste_decision(0))

    def test_custom_thresholds(self) -> None:
        self.assertEqual("selected", taste_decision(40, selected_min=35, shortlist_min=15))
        self.assertEqual("rejected", taste_decision(10, selected_min=35, shortlist_min=15))


if __name__ == "__main__":
    unittest.main()
