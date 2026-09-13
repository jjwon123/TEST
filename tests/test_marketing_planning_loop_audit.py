from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.utils.json_io import write_json
from scripts.audit_marketing_planning_loop import build_audit


class MarketingPlanningLoopAuditTests(unittest.TestCase):
    def test_passes_when_signals_insight_scorecard_and_outputs_are_connected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            stage_dir = run_dir / "02_content_planning"
            stage_dir.mkdir(parents=True)
            insight = root / "insight.json"
            write_json(insight, insight_brief())
            write_json(stage_dir / "concept-candidates.json", concepts())
            write_json(stage_dir / "copy-package.json", copy_package())
            write_json(stage_dir / "planning-scorecard.json", scorecard("pass"))

            with patch("scripts.audit_marketing_planning_loop.INSIGHT_BRIEF_PATH", insight), patch(
                "scripts.audit_marketing_planning_loop.signal_metrics",
                return_value={"selectedUsable": 3, "qualityBlocked": 0},
            ):
                report = build_audit(run_dir, minimum_signals=3)

        self.assertEqual("pass", report["status"])
        self.assertEqual([], report["errors"])
        self.assertTrue(report["checks"]["conceptsUseMarketingEvidence"]["pass"])
        self.assertTrue(report["checks"]["copyUsesMarketingEvidence"]["pass"])

    def test_fails_when_scorecard_has_critical_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            stage_dir = run_dir / "02_content_planning"
            stage_dir.mkdir(parents=True)
            insight = root / "insight.json"
            write_json(insight, insight_brief())
            write_json(stage_dir / "concept-candidates.json", concepts())
            write_json(stage_dir / "copy-package.json", copy_package())
            write_json(stage_dir / "planning-scorecard.json", scorecard("fail", critical=1))

            with patch("scripts.audit_marketing_planning_loop.INSIGHT_BRIEF_PATH", insight), patch(
                "scripts.audit_marketing_planning_loop.signal_metrics",
                return_value={"selectedUsable": 3, "qualityBlocked": 0},
            ):
                report = build_audit(run_dir, minimum_signals=3)

        self.assertEqual("fail", report["status"])
        self.assertIn("scorecardPasses", report["errors"])


def insight_brief() -> dict:
    return {"status": "ready", "selectedSignalCount": 3, "evidenceSignalIds": ["s1", "s2", "s3"]}


def concepts() -> dict:
    return {
        "marketingEvidenceStatus": "ready",
        "candidates": [
            {"conceptId": "c1", "marketingSignalIds": ["s1", "s2", "s3"]},
            {"conceptId": "c2", "marketingSignalIds": ["s1", "s2", "s3"]},
            {"conceptId": "c3", "marketingSignalIds": ["s1", "s2", "s3"]},
        ],
    }


def copy_package() -> dict:
    return {
        "marketingEvidenceStatus": "ready",
        "outputs": [
            {"deliverableId": "feed", "planningEvidence": {"marketingSignalIds": ["s1"]}},
            {"deliverableId": "blog", "planningEvidence": {"marketingSignalIds": ["s2"]}},
        ],
    }


def scorecard(status: str, *, critical: int = 0) -> dict:
    return {"status": status, "criticalErrorCount": critical, "averageScore": 4.0}


if __name__ == "__main__":
    unittest.main()
