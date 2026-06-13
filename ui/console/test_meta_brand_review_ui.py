import unittest
from pathlib import Path

from scripts.console_server import training_session_detail


APP_JS = Path(__file__).with_name("app.js")


class MetaBrandReviewUiContractTest(unittest.TestCase):
    def test_meta_brand_review_exposes_filter_and_card_fields(self):
        detail = training_session_detail("meta_brand_review", "meta_brand_review_001")
        self.assertEqual(detail["sessionType"], "meta_brand_registry_review")
        self.assertEqual(len(detail["judgement"]["items"]), 100)

        required = {
            "brandName",
            "category",
            "advertiserMatchType",
            "registryQuality",
            "riskSignals",
            "kiwonReview",
            "imageUrl",
        }
        for item in detail["judgement"]["items"]:
            self.assertTrue(required.issubset(item), item["id"])
            self.assertIn(item["category"], {"cosmetics_skincare", "jewelry_luxury"})
            self.assertIn(item["advertiserMatchType"], {"direct", "partner"})
            self.assertIn(item["registryQuality"], {"standard", "review"})

    def test_pinterest_session_contract_is_unchanged(self):
        detail = training_session_detail("cosmetics_skincare", "pinterest_holdout_003")
        self.assertNotEqual(detail["sessionType"], "meta_brand_registry_review")
        self.assertTrue(detail["judgement"]["items"])
        self.assertTrue(all("imageUrl" in item and "kiwonReview" in item for item in detail["judgement"]["items"]))

    def test_meta_status_tabs_and_reset_synchronize_review_status_filter(self):
        source = APP_JS.read_text(encoding="utf-8")

        self.assertIn("syncTrainingReviewStatusFilter(state.trainingStatusFilter, isMetaBrandReview);", source)
        self.assertIn('statusFilter === "completed"', source)
        self.assertIn('? "reviewed"', source)
        self.assertIn('statusFilter === "pending"', source)
        self.assertIn('? "unreviewed"', source)
        self.assertIn('state.trainingStatusFilter = "all";', source)


if __name__ == "__main__":
    unittest.main()
