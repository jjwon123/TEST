from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.manage_ad_planning_benchmark_review_sheet import export_sheet, import_sheet


class AdPlanningBenchmarkReviewSheetTests(unittest.TestCase):
    def test_export_writes_blind_variants_without_revealing_source_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset.json"
            external = root / "external.json"
            reviews = root / "reviews.json"
            sheet = root / "sheet.csv"
            dataset.write_text(json.dumps({"cases": [case_payload()]}), encoding="utf-8")
            external.write_text(json.dumps({"results": [external_payload()]}), encoding="utf-8")
            reviews.write_text('{"reviews":[]}', encoding="utf-8")
            summary = export_sheet(sheet, dataset_path=dataset, external_path=external, reviews_path=reviews, limit=1)
            with sheet.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(1, summary["rows"])
        self.assertEqual("case-1", rows[0]["caseId"])
        self.assertIn("External concept", rows[0]["variantA"] + rows[0]["variantB"])
        self.assertNotIn("external", rows[0]["variantA"].lower())
        self.assertNotIn("baseline", rows[0]["variantA"].lower())

    def test_import_validates_without_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sheet = root / "sheet.csv"
            reviews = root / "reviews.json"
            write_sheet(sheet)
            summary = import_sheet(sheet, reviews_path=reviews, apply=False)
        self.assertEqual(0, summary["applied"])
        self.assertEqual([], summary["errors"])
        self.assertFalse(reviews.exists())

    def test_import_apply_saves_human_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sheet = root / "sheet.csv"
            reviews = root / "reviews.json"
            write_sheet(sheet)
            summary = import_sheet(sheet, reviews_path=reviews, apply=True)
            saved = json.loads(reviews.read_text(encoding="utf-8"))["reviews"][0]
        self.assertEqual(1, summary["applied"])
        self.assertEqual("case-1", saved["caseId"])
        self.assertEqual("A", saved["blindPreferred"])
        self.assertTrue(saved["approved"])

    def test_import_reports_errors_for_partial_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sheet = Path(tmp) / "sheet.csv"
            write_sheet(sheet, score_strategyClarity="")
            summary = import_sheet(sheet, reviews_path=Path(tmp) / "reviews.json", apply=False)
        self.assertEqual(1, len(summary["errors"]))
        self.assertIn("eight", summary["errors"][0]["error"])


def case_payload() -> dict[str, str]:
    return {
        "id": "case-1",
        "eventType": "seasonal",
        "eventName": "June Event",
        "target": "Sensitive skin",
        "product": "Ampoule",
        "offer": "Gift",
    }


def external_payload() -> dict:
    return {
        "caseId": "case-1",
        "status": "complete",
        "concepts": {"candidates": [{"conceptId": "concept_01", "name": "External concept", "targetInsight": "Insight", "corePromise": "Promise"}]},
        "copyPackage": {"outputs": [{"copy": {"headline": "External copy"}}]},
        "scorecard": {"criticalErrorCount": 0},
        "providerExecution": [],
    }


def write_sheet(path: Path, **overrides: str) -> None:
    fields = [
        "caseId", "eventType", "eventName", "product", "target", "offer", "externalStatus", "selectedConceptId",
        "variantA", "variantB", "blindPreferred", "approved", "edited",
        "score_actionability", "score_brandFit", "score_channelFit", "score_distinctiveness",
        "score_koreanCopyQuality", "score_productConnection", "score_strategyClarity", "score_targetEmpathy",
        "reasonTags", "reviewNote",
    ]
    row = {
        "caseId": "case-1",
        "blindPreferred": "A",
        "approved": "true",
        "edited": "false",
        "score_actionability": "4",
        "score_brandFit": "4",
        "score_channelFit": "4",
        "score_distinctiveness": "4",
        "score_koreanCopyQuality": "4",
        "score_productConnection": "4",
        "score_strategyClarity": "4",
        "score_targetEmpathy": "4",
        "reasonTags": "good_structure",
        "reviewNote": "ok",
    }
    row.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)


if __name__ == "__main__":
    unittest.main()
