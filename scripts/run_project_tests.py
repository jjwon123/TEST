#!/usr/bin/env python3
"""Run the complete project-owned unittest suite from all test locations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_MODULES = [
    "tests.test_collect_meta_brand_registry",
    "tests.test_workflow_quality_gates",
    "pipeline.03_reference_research.tests.test_meta_brand_provider",
    "services.ad_reference.test_meta_creative_classifier",
    "ui.console.test_meta_brand_review_ui",
]


def main() -> int:
    loader = unittest.defaultTestLoader
    suite = loader.loadTestsFromNames(TEST_MODULES)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
