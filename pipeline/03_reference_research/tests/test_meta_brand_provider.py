from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from services.ad_reference.meta_brand_provider import add_meta_brand_references, build_brief_context, rank_candidates


class MetaBrandProviderTest(unittest.TestCase):
    def test_direct_is_prioritized_and_partner_review_are_penalized(self) -> None:
        context = {"brand": "", "categories": ["cosmetics_skincare"], "roles": ["promotion", "product"]}
        items = [
            self._item("partner", match="partner", quality="standard", roles=["promotion", "product"]),
            self._item("review", match="direct", quality="review", roles=["promotion", "product"]),
            self._item("direct", match="direct", quality="standard", roles=["product"]),
        ]
        ranked = rank_candidates(items, context)

        self.assertEqual("direct", ranked[0]["item"]["id"])
        scores = {candidate["item"]["id"]: candidate["score"] for candidate in ranked}
        self.assertGreater(scores["direct"], scores["partner"])
        self.assertGreater(scores["direct"], scores["review"])

    def test_brief_context_matches_industry_brand_and_roles(self) -> None:
        context = build_brief_context(
            {
                "event_name": "여름 스킨케어 세일",
                "brand": {"name": "hsgn"},
                "offer": {"summary": "제품 20% 할인과 증정"},
            },
            {},
        )
        self.assertIn("cosmetics_skincare", context["categories"])
        self.assertIn("promotion", context["roles"])
        self.assertIn("product", context["roles"])
        self.assertEqual("hsgn", context["brand"])

    def test_empty_candidate_brand_does_not_receive_brand_match_score(self) -> None:
        item = self._item("empty-brand")
        item["brandName"] = ""

        ranked = rank_candidates(
            [item],
            {"brand": "Target Brand", "categories": ["cosmetics_skincare"], "roles": []},
        )

        self.assertEqual(0, ranked[0]["brandScore"])

    def test_excludes_card_news_and_promotion_text_heavy_from_ranked_candidates(self) -> None:
        items = [
            self._item("clean", file_name="001_clean.jpg"),
            self._item("card", file_name="002_card.jpg"),
            self._item("promo", file_name="003_promo.jpg"),
        ]

        ranked = rank_candidates(
            items,
            {"brand": "", "categories": ["cosmetics_skincare"], "roles": ["product"]},
            creative_types={
                "001_clean.jpg": "product_clean",
                "002_card.jpg": "card_news",
                "003_promo.jpg": "promotion_text_heavy",
            },
        )

        self.assertEqual(["clean"], [candidate["item"]["id"] for candidate in ranked])

    def test_merges_with_existing_pinterest_and_records_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "source.jpg"
            source.write_bytes(b"meta-image")
            session = temp_path / "ai_judgement.json"
            session.write_text(json.dumps({"items": [self._item("direct", source=source)]}), encoding="utf-8")
            run_dir = temp_path / "run"
            manifest = {"assets": [{"asset_id": "pin_1", "source": "pinterest", "status": "selected"}]}

            merged, evidence = add_meta_brand_references(
                run_dir,
                manifest,
                {"event_name": "스킨케어 제품 세일", "brand": {"name": "hsgn"}},
                {},
                limit=1,
                session_path=session,
            )

            self.assertEqual(2, len(merged["assets"]))
            self.assertEqual("pinterest", merged["assets"][0]["source"])
            self.assertEqual("meta_brand_review", merged["assets"][1]["source"])
            self.assertEqual(1, evidence["providers"]["meta_brand_review"]["importedCount"])

    def test_does_not_duplicate_existing_asset_when_sha_and_original_path_are_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "source.jpg"
            source.write_bytes(b"meta-image")
            session = temp_path / "ai_judgement.json"
            session.write_text(json.dumps({"items": [self._item("direct", source=source)]}), encoding="utf-8")
            manifest = {
                "assets": [{
                    "asset_id": "existing",
                    "sha256": "existing-sha",
                    "original_path": str(source),
                    "status": "selected",
                }],
            }

            merged, evidence = add_meta_brand_references(
                temp_path / "run",
                manifest,
                {"event_name": "스킨케어 제품 세일"},
                {},
                limit=1,
                session_path=session,
            )

            self.assertEqual(1, len(merged["assets"]))
            self.assertEqual(0, evidence["providers"]["meta_brand_review"]["importedCount"])
            self.assertEqual("already_present", evidence["providers"]["meta_brand_review"]["selected"][0]["importStatus"])

    @staticmethod
    def _item(
        item_id: str,
        *,
        match: str = "direct",
        quality: str = "standard",
        roles: list[str] | None = None,
        source: Path | None = None,
        file_name: str = "",
    ) -> dict:
        return {
            "id": item_id,
            "sourcePath": str(source or ""),
            "file": file_name,
            "category": "cosmetics_skincare",
            "brandId": item_id,
            "brandName": item_id,
            "advertiserMatchType": match,
            "registryQuality": quality,
            "referenceRole": roles or ["promotion", "product"],
            "adLibraryId": item_id,
        }


if __name__ == "__main__":
    unittest.main()
