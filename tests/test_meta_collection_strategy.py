from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from services.ad_reference.collection_strategy import aggregate_brand_diagnostics, order_brands
from services.ad_reference.registry_metrics import collection_metrics_summary


BRANDS = [{"id": item, "name": item} for item in ["heavy", "winner", "explore", "no-match", "media-gap"]]


class MetaCollectionStrategyTests(unittest.TestCase):
    def test_adaptive_strategy_prioritizes_proven_and_explorable_brands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_batch(root)
            ordered = order_brands("cosmetics_skincare", BRANDS, runs_root=root)
        self.assertEqual(["winner", "explore"], [item["id"] for item in ordered[:2]])

    def test_brand_diagnostics_explain_next_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_batch(root)
            report = collection_metrics_summary(root)
        diagnostics = {
            item["brandId"]: item["action"]
            for item in report["latestByProfile"]["cosmetics_skincare"]["brandDiagnostics"]
        }
        self.assertEqual("retain", diagnostics["winner"])
        self.assertEqual("explore", diagnostics["explore"])
        self.assertEqual("deprioritize_promotion_heavy", diagnostics["heavy"])
        self.assertEqual("media_gap", diagnostics["media-gap"])
        self.assertEqual("audit_alias", diagnostics["no-match"])

    def test_strategy_aggregates_evidence_across_batches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_batch(root)
            latest = root / "latest"
            latest.mkdir()
            (latest / "brand-collection-manifest.json").write_text(json.dumps({
                "profile": "cosmetics_skincare",
                "summary": {"collectedBrands": 1, "rawAds": 3},
                "results": [{"brandId": "winner", "brand": "winner", "status": "collected", "advertiserMatchedAds": 0, "acceptedImages": 0, "excludedImages": 0, "needsCreativeReviewImages": 0}],
            }), encoding="utf-8")

            diagnostics = {item["brandId"]: item for item in aggregate_brand_diagnostics("cosmetics_skincare", root)}

        self.assertEqual("retain", diagnostics["winner"]["action"])
        self.assertEqual(3, diagnostics["winner"]["acceptedImages"])

    @staticmethod
    def _write_batch(root: Path) -> None:
        batch = root / "batch"
        batch.mkdir()
        results = [
            {"brandId": "heavy", "brand": "heavy", "status": "collected", "advertiserMatchedAds": 10, "acceptedImages": 0, "excludedImages": 16, "needsCreativeReviewImages": 0},
            {"brandId": "winner", "brand": "winner", "status": "collected", "advertiserMatchedAds": 5, "acceptedImages": 3, "excludedImages": 2, "needsCreativeReviewImages": 0},
            {"brandId": "explore", "brand": "explore", "status": "collected", "advertiserMatchedAds": 2, "acceptedImages": 0, "excludedImages": 1, "needsCreativeReviewImages": 0},
            {"brandId": "no-match", "brand": "no-match", "status": "collected", "advertiserMatchedAds": 0, "acceptedImages": 0, "excludedImages": 0, "needsCreativeReviewImages": 0},
            {"brandId": "media-gap", "brand": "media-gap", "status": "collected", "advertiserMatchedAds": 4, "acceptedImages": 0, "excludedImages": 0, "needsCreativeReviewImages": 0},
        ]
        manifest = {
            "profile": "cosmetics_skincare",
            "summary": {
                "collectedBrands": 5,
                "brandsWithAdvertiserMatches": 4,
                "brandsWithAcceptedImages": 1,
                "rawAds": 50,
                "advertiserMatchedAds": 21,
                "acceptedImages": 3,
                "excludedImages": 19,
            },
            "results": results,
        }
        (batch / "brand-collection-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
