from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import collect_meta_brand_registry as subject
from services.ad_reference import meta_collector


BRANDS = [
    {"id": "alpha", "name": "Alpha", "query": "Alpha", "advertiserAliases": ["Alpha"]},
    {"id": "beta", "name": "Beta", "query": "Beta", "advertiserAliases": ["Beta"]},
]


def args(**overrides: object) -> argparse.Namespace:
    values = {
        "profile": "cosmetics_skincare",
        "brand_id": [],
        "brand_limit": 2,
        "ads_per_brand": 3,
        "scrolls": 0,
        "country": "KR",
        "headful": False,
        "delay": 0,
        "dry_run": False,
        "batch_id": "batch",
        "resume": False,
        "retry_failed": False,
        "no_creative_review": False,
        "review_limit": 100,
        "review_model": "qwen2.5vl:7b",
        "review_host": "http://127.0.0.1:11434",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def payload(brand: str) -> dict[str, object]:
    return {
        "count": 1,
        "items": [{"brand": brand, "media": []}],
    }


class MetaBrandRegistryCollectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.output_root = Path(self.temporary.name) / "runs"
        self.patches = [
            patch.object(subject, "OUTPUT_ROOT", self.output_root),
            patch.object(subject, "ROOT", Path(self.temporary.name)),
            patch.object(subject, "load_brand_registry", return_value={
                "profiles": {"cosmetics_skincare": {"defaultCountry": "KR"}},
            }),
            patch.object(subject, "profile_brands", return_value=BRANDS),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.temporary.cleanup()

    def test_reserve_batch_dir_avoids_collisions(self) -> None:
        first = subject.reserve_batch_dir("same")
        second = subject.reserve_batch_dir("same")
        self.assertEqual("same", first.name)
        self.assertEqual("same-02", second.name)

    def test_persists_each_brand_and_failed_brand_list(self) -> None:
        calls = []

        def collector(options):
            calls.append(options.query)
            if options.query == "Beta":
                manifest = json.loads((options.output_dir.parents[1] / subject.MANIFEST_NAME).read_text(encoding="utf-8"))
                self.assertEqual("collected", manifest["results"][0]["status"])
                raise RuntimeError("temporary failure")
            manifest = json.loads((options.output_dir.parents[1] / subject.MANIFEST_NAME).read_text(encoding="utf-8"))
            self.assertEqual("collecting", manifest["results"][0]["status"])
            return payload(options.query)

        manifest = subject.run_collection(args(), collector=collector, sleep_fn=lambda _: None)
        batch_dir = Path(manifest["batchDir"])
        saved = json.loads((batch_dir / subject.MANIFEST_NAME).read_text(encoding="utf-8"))
        failed = json.loads((batch_dir / subject.FAILED_BRANDS_NAME).read_text(encoding="utf-8"))

        self.assertEqual(["Alpha", "Beta"], calls)
        self.assertEqual(["collected", "error"], [item["status"] for item in saved["results"]])
        self.assertEqual(1, failed["count"])
        self.assertEqual("beta", failed["brands"][0]["brandId"])

    def test_resume_skips_collected_and_retries_incomplete(self) -> None:
        first_calls = []

        def first_collector(options):
            first_calls.append(options.query)
            if options.query == "Beta":
                raise RuntimeError("temporary failure")
            return payload(options.query)

        subject.run_collection(args(), collector=first_collector, sleep_fn=lambda _: None)
        resumed_calls = []
        manifest = subject.run_collection(
            args(resume=True),
            collector=lambda options: resumed_calls.append(options.query) or payload(options.query),
            sleep_fn=lambda _: None,
        )

        self.assertEqual(["Beta"], resumed_calls)
        self.assertEqual(2, manifest["summary"]["collectedBrands"])
        self.assertEqual(0, manifest["summary"]["errors"])

    def test_retry_failed_only_retries_errors(self) -> None:
        subject.run_collection(
            args(),
            collector=lambda options: (_ for _ in ()).throw(RuntimeError("fail")) if options.query == "Beta" else payload(options.query),
            sleep_fn=lambda _: None,
        )
        calls = []
        subject.run_collection(
            args(retry_failed=True),
            collector=lambda options: calls.append(options.query) or payload(options.query),
            sleep_fn=lambda _: None,
        )
        self.assertEqual(["Beta"], calls)

    def test_meta_collector_atomic_json_replaces_existing_file(self) -> None:
        path = Path(self.temporary.name) / "collected-ads.json"
        path.write_text('{"old": true}\n', encoding="utf-8")

        meta_collector._atomic_write_json(path, {"new": True})

        self.assertEqual({"new": True}, json.loads(path.read_text(encoding="utf-8")))
        self.assertEqual([], list(path.parent.glob(".collected-ads.json.*.tmp")))

    def test_creative_gate_excludes_card_news_before_accepting_images(self) -> None:
        def collector(options):
            image = options.output_dir / "image.jpg"
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(b"x" * 20_000)
            return {
                "count": 1,
                "items": [{
                    "brand": "Alpha",
                    "media": [{"savedPath": str(image), "width": 1000, "height": 1000}],
                }],
            }

        with patch.object(subject, "classify_media", return_value={
            "savedPath": "image.jpg",
            "width": 1000,
            "height": 1000,
            "registryQuality": "standard",
            "creativeType": "card_news",
            "creativeGate": "excluded",
            "creativeExclusionReasons": ["card_news"],
        }):
            manifest = subject.run_collection(
                args(brand_id=["alpha"]),
                collector=collector,
                sleep_fn=lambda _: None,
            )

        self.assertEqual(1, manifest["summary"]["excludedImages"])
        self.assertEqual(0, manifest["summary"]["acceptedImages"])


if __name__ == "__main__":
    unittest.main()
