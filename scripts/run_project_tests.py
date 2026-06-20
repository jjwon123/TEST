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
    "tests.test_ad_planning_engine",
    "tests.test_ad_planning_upgrade",
    "tests.test_ad_planning_quality_gate",
    "tests.test_ad_planning_review_packet",
    "tests.test_ad_planning_pilot_runner",
    "tests.test_ad_planning_benchmark_review_sheet",
    "tests.test_ad_strategy_review_sheet",
    "tests.test_planning_strategy_quality",
    "tests.test_collect_meta_brand_registry",
    "tests.test_asset_integrity",
    "tests.test_workflow_quality_gates",
    "tests.test_comfyui_preset_adapters",
    "tests.test_learned_reference_rules",
    "tests.test_legacy_package_migration",
    "tests.test_meta_brand_metrics",
    "tests.test_meta_collection_strategy",
    "tests.test_meta_source_mix_metrics",
    "tests.test_marketing_intelligence_signals",
    "tests.test_marketing_intelligence_console",
    "tests.test_marketing_insight_brief",
    "tests.test_console_ui_playwright_audit",
    "tests.test_repeated_operations",
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
