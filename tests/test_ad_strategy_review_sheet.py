from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.manage_ad_strategy_review_sheet import export_sheet, import_sheet


class AdStrategyReviewSheetTests(unittest.TestCase):
    def test_export_writes_unreviewed_rows_with_source_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sheet = Path(tmp) / "sheet.csv"
            with patch("scripts.manage_ad_strategy_review_sheet.load_examples_for_review", return_value=[
                {
                    "id": "one",
                    "industry": "cosmetics_skincare",
                    "targetInsight": "",
                    "hookMechanism": "offer_first",
                    "persuasionSequence": ["hook", "offer"],
                    "review": {"decision": "unreviewed", "scores": {}, "reasonTags": []},
                    "sourceOriginal": {"brand": "Brand", "copy": "A strong source ad copy."},
                }
            ]), patch("scripts.manage_ad_strategy_review_sheet.strategy_quality_metrics", return_value={}):
                summary = export_sheet(sheet)
            with sheet.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(1, summary["rows"])
        self.assertEqual("one", rows[0]["id"])
        self.assertEqual("", rows[0]["decision"])
        self.assertEqual("Brand", rows[0]["sourceBrand"])

    def test_import_validates_selected_rows_without_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sheet = Path(tmp) / "sheet.csv"
            write_sheet(sheet, decision="selected")
            with patch("scripts.manage_ad_strategy_review_sheet.strategy_quality_metrics", return_value={}):
                summary = import_sheet(sheet, apply=False)
        self.assertEqual(0, summary["applied"])
        self.assertEqual([], summary["errors"])

    def test_import_apply_updates_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sheet = root / "sheet.csv"
            examples = root / "examples.json"
            examples.write_text(json.dumps({
                "examples": [{
                    "id": "one",
                    "industry": "cosmetics_skincare",
                    "targetInsight": "",
                    "hookMechanism": "",
                    "persuasionSequence": [],
                    "ctaType": "",
                    "review": {"decision": "unreviewed", "scores": {}, "reasonTags": []},
                }]
            }), encoding="utf-8")
            write_sheet(sheet, decision="selected")
            with patch("services.ad_strategy.repository.EXAMPLES_PATH", examples):
                summary = import_sheet(sheet, apply=True)
            saved = json.loads(examples.read_text(encoding="utf-8"))["examples"][0]
        self.assertEqual(1, summary["applied"])
        self.assertEqual("selected", saved["review"]["decision"])
        self.assertEqual("고객 인사이트", saved["targetInsight"])

    def test_import_reports_errors_for_incomplete_selected_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sheet = Path(tmp) / "sheet.csv"
            write_sheet(sheet, decision="selected", targetInsight="")
            with patch("scripts.manage_ad_strategy_review_sheet.strategy_quality_metrics", return_value={}):
                summary = import_sheet(sheet, apply=False)
        self.assertEqual(1, len(summary["errors"]))
        self.assertIn("missing strategy fields", summary["errors"][0]["error"])


def write_sheet(path: Path, *, decision: str, targetInsight: str = "고객 인사이트") -> None:
    fields = [
        "id", "industry", "sourceBrand", "sourceCopyPreview", "decision",
        "targetInsight", "hookMechanism", "persuasionSequence", "offerMechanism", "proofMechanism", "ctaType", "toneTraits", "channelFit",
        "score_actionability", "score_brandFit", "score_channelFit", "score_distinctiveness", "score_koreanCopyQuality", "score_productConnection", "score_strategyClarity", "score_targetEmpathy",
        "reasonTags", "reviewNote",
    ]
    row = {
        "id": "one",
        "industry": "cosmetics_skincare",
        "decision": decision,
        "targetInsight": targetInsight,
        "hookMechanism": "공감 후킹",
        "persuasionSequence": "공감, 근거, 제안",
        "offerMechanism": "증정",
        "proofMechanism": "사용 맥락",
        "ctaType": "자세히 보기",
        "toneTraits": "차분함",
        "channelFit": "instagram_feed",
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)


if __name__ == "__main__":
    unittest.main()
