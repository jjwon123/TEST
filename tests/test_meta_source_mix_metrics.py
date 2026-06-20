from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from services.ad_reference.source_mix_metrics import source_mix_summary


class MetaSourceMixMetricsTests(unittest.TestCase):
    def test_recommends_reviewed_product_query_with_clean_visual_yield(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            search = root / "search"
            search.mkdir()
            media = [
                {"qwenReview": {"creative_type": "clean_product_visual", "decision": "selected"}}
                for _ in range(3)
            ] + [
                {"qwenReview": {"creative_type": "promotion_structure", "decision": "rejected"}}
                for _ in range(3)
            ]
            (search / "collected-ads.json").write_text(json.dumps({
                "query": "스킨케어 세럼",
                "count": 2,
                "items": [{"media": media}],
            }), encoding="utf-8")

            report = source_mix_summary(root)

        self.assertEqual("validated_fallback", report["status"])
        self.assertEqual("스킨케어 세럼", report["recommendedQueries"][0]["query"])
        self.assertEqual(0.5, report["recommendedQueries"][0]["cleanProductRate"])

    def test_collection_plan_prioritizes_under_reviewed_product_queries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for query, reviewed in [("스킨케어 크림", 0), ("스킨케어 세럼", 6), ("스킨케어 세일", 0)]:
                search = root / query
                search.mkdir()
                media = [{"qwenReview": {"creative_type": "other"}} for _ in range(reviewed)] or [{} for _ in range(8)]
                (search / "collected-ads.json").write_text(json.dumps({
                    "query": query,
                    "count": 2,
                    "items": [{"media": media}],
                }), encoding="utf-8")

            report = source_mix_summary(root)

        self.assertEqual(["스킨케어 크림"], [item["query"] for item in report["collectionPlan"]])


if __name__ == "__main__":
    unittest.main()
