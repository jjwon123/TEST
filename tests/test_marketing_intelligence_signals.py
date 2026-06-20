from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from services.marketing_intelligence.repository import (
    append_signals,
    export_review_sheet,
    generate_random_seed_signals,
    import_review_sheet,
    load_signals,
)


class MarketingIntelligenceSignalTests(unittest.TestCase):
    def test_random_seed_signals_are_unreviewed_hypotheses(self) -> None:
        signals = generate_random_seed_signals(count=5, seed=7, topic="monsoon_hydration")

        self.assertEqual(5, len(signals))
        self.assertTrue(all(signal["sourceType"] == "seed_random" for signal in signals))
        self.assertTrue(all(signal["review"]["decision"] == "unreviewed" for signal in signals))
        self.assertTrue(all("needs_external_validation" in signal["riskFlags"] for signal in signals))
        self.assertTrue(all(signal["topic"] == "monsoon_hydration" for signal in signals))

    def test_append_dedupes_repeatable_random_seed_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.json"
            first = generate_random_seed_signals(count=10, seed=11)
            second = generate_random_seed_signals(count=10, seed=11)

            first_summary = append_signals(first, path)
            second_summary = append_signals(second, path)

            self.assertEqual(10, first_summary["added"])
            self.assertEqual(0, second_summary["added"])
            self.assertEqual(10, second_summary["skipped"])
            self.assertEqual(10, len(load_signals(path)))

    def test_export_and_import_review_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            signals_path = root / "signals.json"
            sheet = root / "review.csv"
            append_signals(generate_random_seed_signals(count=2, seed=3), signals_path)

            export_summary = export_review_sheet(sheet, signals_path=signals_path)
            rows = read_rows(sheet)
            rows[0]["decision"] = "selected"
            rows[0]["reasonTags"] = "useful_target"
            rows[0]["reviewNote"] = "검수 후 파일럿에 사용"
            write_rows(sheet, rows)

            dry_run = import_review_sheet(sheet, apply=False, signals_path=signals_path)
            apply_summary = import_review_sheet(sheet, apply=True, signals_path=signals_path)
            saved = json.loads(signals_path.read_text(encoding="utf-8"))["signals"]

        selected = next(item for item in saved if item["id"] == rows[0]["id"])
        self.assertEqual(2, export_summary["rows"])
        self.assertEqual(0, dry_run["applied"])
        self.assertEqual(1, apply_summary["applied"])
        self.assertEqual("selected", selected["review"]["decision"])
        self.assertEqual(["useful_target"], selected["review"]["reasonTags"])


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
