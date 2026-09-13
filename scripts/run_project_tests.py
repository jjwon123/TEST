#!/usr/bin/env python3
"""Run the complete project-owned unittest suite from all test locations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXTERNAL_TEST_MODULES = [
    "pipeline.03_reference_research.tests.test_meta_brand_provider",
    "services.ad_reference.test_meta_creative_classifier",
    "ui.console.test_meta_brand_review_ui",
]


def build_suite(loader: unittest.TestLoader | None = None) -> unittest.TestSuite:
    loader = loader or unittest.defaultTestLoader
    root_tests = loader.discover(
        start_dir=str(ROOT / "tests"),
        pattern="test_*.py",
        top_level_dir=str(ROOT),
    )
    external_tests = loader.loadTestsFromNames(EXTERNAL_TEST_MODULES)
    return unittest.TestSuite([root_tests, external_tests])


def main() -> int:
    suite = build_suite()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
