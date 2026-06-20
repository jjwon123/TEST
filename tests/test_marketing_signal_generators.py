from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.marketing_intelligence.calendar_signals import generate_calendar_signals
from services.marketing_intelligence.oliveyoung_csv import parse_oliveyoung_ranking_csv
from services.marketing_intelligence.repository import append_signals, load_signals


class CalendarSignalTests(unittest.TestCase):
    def test_generates_unreviewed_calendar_signals_for_month(self) -> None:
        signals = generate_calendar_signals(6, now="2026-06-20T00:00:00+00:00")
        self.assertGreaterEqual(len(signals), 2)
        for signal in signals:
            self.assertEqual("calendar", signal["sourceType"])
            self.assertEqual("unreviewed", signal["review"]["decision"])
            self.assertIn("deterministic_calendar_fact", signal["riskFlags"])
        self.assertEqual("summer_tone_care", signals[0]["topic"])

    def test_rejects_invalid_month(self) -> None:
        with self.assertRaises(ValueError):
            generate_calendar_signals(13)

    def test_calendar_signals_pass_schema_on_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.json"
            result = append_signals(generate_calendar_signals(1), path)
            self.assertEqual(result["added"], len(load_signals(path)))
            self.assertGreater(result["added"], 0)


class OliveyoungCsvTests(unittest.TestCase):
    def _write_csv(self, tmp: str) -> Path:
        path = Path(tmp) / "ranking.csv"
        path.write_text(
            "rank,brand,product,category,review_keywords\n"
            "1,브랜드A,수분세럼,세럼,\"수분감, 흡수력, 끈적임 없음\"\n"
            "2,브랜드B,진정크림,크림,진정;순함;향\n"
            ",,,, \n",  # 빈 행은 건너뛴다
            encoding="utf-8",
        )
        return path

    def test_parses_rows_into_unreviewed_rank_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signals = parse_oliveyoung_ranking_csv(self._write_csv(tmp), now="2026-06-20T00:00:00+00:00")
        self.assertEqual(2, len(signals))  # 빈 행 제외
        for signal in signals:
            self.assertEqual("oliveyoung_rank", signal["sourceType"])
            self.assertEqual("unreviewed", signal["review"]["decision"])
            self.assertIn("external_rank_claim", signal["riskFlags"])
        self.assertEqual(["수분감", "흡수력", "끈적임 없음"], signals[0]["sourceRef"]["reviewKeywords"])

    def test_parsed_signals_pass_schema_on_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = self._write_csv(tmp)
            store = Path(tmp) / "signals.json"
            result = append_signals(parse_oliveyoung_ranking_csv(csv_path), store)
            self.assertEqual(2, result["added"])


if __name__ == "__main__":
    unittest.main()
