from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from services.ad_reference.registry_metrics import collection_metrics_summary


class MetaBrandMetricsTests(unittest.TestCase):
    def test_calculates_rates_concentration_creative_types_and_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch = root / "batch-1"
            brand = batch / "brands" / "alpha"
            brand.mkdir(parents=True)
            manifest = {
                "profile": "cosmetics_skincare",
                "summary": {
                    "collectedBrands": 10,
                    "brandsWithAdvertiserMatches": 3,
                    "brandsWithAcceptedImages": 1,
                    "rawAds": 100,
                    "advertiserMatchedAds": 20,
                    "acceptedImages": 12,
                    "excludedImages": 108,
                    "needsCreativeReviewImages": 0,
                    "errors": 0,
                },
                "results": [
                    {"brandId": "alpha", "brand": "Alpha", "advertiserMatchedAds": 20, "acceptedImages": 12},
                    *[{"brandId": f"zero-{index}", "advertiserMatchedAds": 0, "acceptedImages": 0} for index in range(9)],
                ],
            }
            (batch / "brand-collection-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            accepted = {
                "items": [{"media": [{"creativeType": "product_clean"} for _ in range(12)]}],
                "excludedItems": [{"excludedMedia": [{"creativeType": "promotion_text_heavy"} for _ in range(108)]}],
            }
            (brand / "accepted-ads.json").write_text(json.dumps(accepted), encoding="utf-8")

            report = collection_metrics_summary(root)
            metric = report["latestByProfile"]["cosmetics_skincare"]

            self.assertEqual(0.2, metric["rates"]["advertiserMatchRate"])
            self.assertEqual(0.1, metric["rates"]["creativeAcceptanceRate"])
            self.assertEqual(0.1, metric["rates"]["brandCoverageRate"])
            self.assertEqual(1.0, metric["rates"]["topBrandShare"])
            self.assertEqual(12, metric["creativeTypeCounts"]["product_clean"])
            self.assertEqual(108, metric["creativeTypeCounts"]["promotion_text_heavy"])
            self.assertEqual(
                {"low_advertiser_match", "low_brand_coverage", "high_brand_concentration"},
                {item["code"] for item in metric["warnings"]},
            )

    def test_empty_root_reports_no_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = collection_metrics_summary(Path(temporary))
        self.assertEqual("no_data", report["status"])
        self.assertEqual(0, report["batchCount"])

    def test_planned_only_batch_does_not_hide_latest_collected_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            collected = root / "collected"
            planned = root / "planned"
            collected.mkdir()
            planned.mkdir()
            (collected / "brand-collection-manifest.json").write_text(json.dumps({
                "profile": "cosmetics_skincare",
                "summary": {"collectedBrands": 1, "rawAds": 1, "advertiserMatchedAds": 1, "acceptedImages": 1},
                "results": [{"brandId": "alpha", "status": "collected", "acceptedImages": 1}],
            }), encoding="utf-8")
            (planned / "brand-collection-manifest.json").write_text(json.dumps({
                "profile": "cosmetics_skincare",
                "summary": {"plannedBrands": 3, "collectedBrands": 0},
                "results": [{"brandId": "beta", "status": "planned"}],
            }), encoding="utf-8")

            report = collection_metrics_summary(root)

        self.assertEqual("collected", report["latestByProfile"]["cosmetics_skincare"]["batchId"])

    def test_small_sample_is_warned_and_benchmark_prefers_broader_batch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            broad = root / "broad"
            small = root / "small"
            broad.mkdir()
            small.mkdir()
            (broad / "brand-collection-manifest.json").write_text(json.dumps({
                "profile": "cosmetics_skincare",
                "summary": {"collectedBrands": 10, "rawAds": 100, "advertiserMatchedAds": 50, "acceptedImages": 10, "excludedImages": 20},
                "results": [],
            }), encoding="utf-8")
            (small / "brand-collection-manifest.json").write_text(json.dumps({
                "profile": "cosmetics_skincare",
                "summary": {"collectedBrands": 3, "rawAds": 9, "advertiserMatchedAds": 1, "acceptedImages": 1, "excludedImages": 0},
                "results": [],
            }), encoding="utf-8")

            report = collection_metrics_summary(root)

        self.assertEqual("broad", report["benchmarkByProfile"]["cosmetics_skincare"]["batchId"])
        self.assertIn("small_sample", {item["code"] for item in report["latestByProfile"]["cosmetics_skincare"]["warnings"]})

    def test_adaptive_performance_compares_against_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, strategy, accepted, excluded, collected_brands in [
                ("benchmark", "legacy", 1, 9, 10),
                ("adaptive", "adaptive", 4, 6, 5),
            ]:
                batch = root / name
                batch.mkdir()
                (batch / "brand-collection-manifest.json").write_text(json.dumps({
                    "profile": "cosmetics_skincare",
                    "collectionStrategy": strategy,
                    "summary": {
                        "collectedBrands": collected_brands,
                        "brandsWithAcceptedImages": 1,
                        "rawAds": 25,
                        "advertiserMatchedAds": 10,
                        "acceptedImages": accepted,
                        "excludedImages": excluded,
                    },
                    "results": [{
                        "brandId": name,
                        "brand": name,
                        "status": "collected",
                        "rawAds": 25,
                        "advertiserMatchedAds": 10,
                        "acceptedImages": accepted,
                        "excludedImages": excluded,
                        "needsCreativeReviewImages": 0,
                    }],
                }), encoding="utf-8")

            report = collection_metrics_summary(root)

        adaptive = report["adaptivePerformanceByProfile"]["cosmetics_skincare"]
        self.assertEqual(0.4, adaptive["rates"]["creativeAcceptanceRate"])
        self.assertEqual(0.3, adaptive["deltaVsBenchmark"]["creativeAcceptanceRate"])
        self.assertEqual("insufficient_evidence", adaptive["operatingDecision"]["status"])


if __name__ == "__main__":
    unittest.main()
