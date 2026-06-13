from __future__ import annotations

import unittest
from pathlib import Path

from services.ad_reference.meta_creative_classifier import classify_media, normalize_creative_type


class MetaCreativeClassifierTest(unittest.TestCase):
    def test_excludes_card_news(self) -> None:
        result = classify_media(
            {"savedPath": str(Path("image.jpg"))},
            profile="cosmetics_skincare",
            brand={"name": "Medicube", "roles": ["product"]},
            reviewer=lambda *args, **kwargs: {
                "creative_type": "card_news",
                "card_news_style": True,
            },
        )
        self.assertEqual("card_news", result["creativeType"])
        self.assertEqual("excluded", result["creativeGate"])

    def test_keeps_product_clean(self) -> None:
        result = classify_media(
            {"savedPath": str(Path("image.jpg"))},
            profile="cosmetics_skincare",
            brand={"name": "Anua", "roles": ["product"]},
            reviewer=lambda *args, **kwargs: {"creative_type": "product_clean"},
        )
        self.assertEqual("accepted", result["creativeGate"])

    def test_failed_review_is_preserved_for_manual_review(self) -> None:
        def failed(*args, **kwargs):
            raise RuntimeError("offline")

        result = classify_media(
            {"savedPath": str(Path("image.jpg"))},
            profile="jewelry_luxury",
            brand={"name": "Cartier"},
            reviewer=failed,
        )
        self.assertEqual("review", result["creativeGate"])
        self.assertTrue(result["needsCreativeReview"])

    def test_normalizes_existing_clean_product_type(self) -> None:
        self.assertEqual("product_clean", normalize_creative_type({"creative_type": "clean_product_visual"}))


if __name__ == "__main__":
    unittest.main()
