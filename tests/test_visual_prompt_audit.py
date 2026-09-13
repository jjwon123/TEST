from __future__ import annotations

import unittest

from scripts.audit_visual_prompts import audit_prompt


class VisualPromptAuditTests(unittest.TestCase):
    def test_seasonal_cosmetics_prompt_does_not_require_h_and_b_sale(self) -> None:
        result = audit_prompt(
            {
                "prompt_id": "seasonal-01",
                "candidate_id": "seasonal-c01",
                "visual_role": "key_visual",
                "channel_id": "instagram_feed",
                "positive_prompt": (
                    "skincare product, benefit hierarchy, clean layout, "
                    "blank space for Korean headline, no readable text"
                ),
                "negative_prompt": (
                    "website screenshot, url bar, homepage capture, fake text, "
                    "broken korean text, wrong product category"
                ),
            },
            "cosmetics_skincare",
        )

        self.assertEqual("pass", result["status"])
        self.assertNotIn("korean h&b sale", result["missingRequired"])

    def test_general_profile_minimum_never_exceeds_available_directions(self) -> None:
        result = audit_prompt(
            {
                "prompt_id": "general-01",
                "candidate_id": "general-c01",
                "visual_role": "key_visual",
                "channel_id": "instagram_feed",
                "positive_prompt": (
                    "campaign layout, product focus, copy space, "
                    "blank space for Korean headline, no readable text"
                ),
                "negative_prompt": "fake text, broken text, website screenshot",
            },
            "general",
        )

        self.assertEqual("pass", result["status"])


if __name__ == "__main__":
    unittest.main()
