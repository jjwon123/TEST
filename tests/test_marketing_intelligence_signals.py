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
    signal_metrics,
    update_signal_content,
    update_signal_review,
    update_signal_reviews,
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

    def test_blocked_capture_signal_cannot_be_saved_as_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signals_path = Path(tmp) / "signals.json"
            append_signals([blocked_signal("blocked-1")], signals_path)

            updated = update_signal_review(
                "blocked-1",
                {"decision": "selected", "reasonTags": ["useful_target"], "reviewNote": "좋아 보임"},
                signals_path,
            )
            metrics = signal_metrics(load_signals(signals_path))

        self.assertEqual("shortlist", updated["review"]["decision"])
        self.assertIn("capture_quality_blocked", updated["review"]["reasonTags"])
        self.assertIn("selected 대신 보류", updated["review"]["reviewNote"])
        self.assertEqual(0, metrics["selectedUsable"])
        self.assertEqual(1, metrics["qualityBlocked"])

    def test_review_sheet_import_downgrades_blocked_capture_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            signals_path = root / "signals.json"
            sheet = root / "review.csv"
            append_signals([blocked_signal("blocked-2")], signals_path)
            export_review_sheet(sheet, signals_path=signals_path)
            rows = read_rows(sheet)
            rows[0]["decision"] = "selected"
            rows[0]["reasonTags"] = "useful_target"
            write_rows(sheet, rows)

            summary = import_review_sheet(sheet, apply=True, signals_path=signals_path)
            saved = load_signals(signals_path)[0]

        self.assertEqual(1, summary["applied"])
        self.assertEqual("shortlist", saved["review"]["decision"])
        self.assertIn("capture_quality_blocked", saved["review"]["reasonTags"])

    def test_human_cleaned_signal_can_become_selected_usable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signals_path = Path(tmp) / "signals.json"
            append_signals([blocked_signal("blocked-3")], signals_path)

            cleaned = update_signal_content("blocked-3", {
                "signalText": "여름 톤 케어 제품 상세에서 확인한 사용 상황과 제품 설명 요약",
                "targetSegment": "여름철 칙칙함과 루틴 부담을 함께 줄이고 싶은 고객",
                "normalizedInsight": "여름철 톤 케어 고객은 강한 효능 주장보다 지금 계절의 사용 상황과 제품 선택 이유가 함께 정리된 메시지에 반응한다.",
            }, signals_path)
            selected = update_signal_review("blocked-3", {"decision": "selected", "reasonTags": ["useful_target"]}, signals_path)
            metrics = signal_metrics(load_signals(signals_path))

        self.assertNotIn("capture_quality_blocked", cleaned["riskFlags"])
        self.assertIn("human_cleaned_public_signal", cleaned["riskFlags"])
        self.assertEqual("selected", selected["review"]["decision"])
        self.assertEqual(1, metrics["selectedUsable"])
        self.assertEqual(0, metrics["qualityBlocked"])

    def test_batch_reviews_are_saved_once_and_reject_duplicates_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signals_path = Path(tmp) / "signals.json"
            items = generate_random_seed_signals(count=2, seed=99, topic="pilot")
            append_signals(items, signals_path)
            updated = update_signal_reviews([
                {
                    "signalId": items[0]["id"],
                    "decision": "selected",
                    "reasonTags": ["useful_target"],
                    "reviewNote": "첫 번째 후보를 고객 문제 근거로 확인했습니다.",
                },
                {
                    "signalId": items[1]["id"],
                    "decision": "shortlist",
                    "reasonTags": ["needs_source"],
                    "reviewNote": "중복 역할 후보라 참고 근거로만 보류했습니다.",
                },
            ], signals_path)
            before_duplicate = signals_path.read_text(encoding="utf-8")
            with self.assertRaises(ValueError):
                update_signal_reviews([
                    {"signalId": items[0]["id"], "decision": "rejected"},
                    {"signalId": items[0]["id"], "decision": "selected"},
                ], signals_path)
            after_duplicate = signals_path.read_text(encoding="utf-8")

        self.assertEqual(["selected", "shortlist"], [item["review"]["decision"] for item in updated])
        self.assertEqual(before_duplicate, after_duplicate)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def blocked_signal(signal_id: str) -> dict:
    return {
        "id": signal_id,
        "industry": "cosmetics_skincare",
        "sourceType": "brand_site",
        "sourceRef": {},
        "topic": "hsgn_summer_tone_care",
        "signalText": "HTML 조각이 섞인 공개 캡처",
        "normalizedInsight": "정리 전에는 생성 근거로 쓰면 안 되는 공개 캡처",
        "targetSegment": "검수 대기 고객",
        "funnelStage": "awareness",
        "evidenceType": "trend",
        "strength": 4,
        "freshness": 4,
        "confidence": 3,
        "riskFlags": ["capture_quality_blocked", "raw_html_detected"],
        "usableFor": ["concept", "copy"],
        "review": {"decision": "unreviewed", "reasonTags": [], "reviewNote": ""},
    }


if __name__ == "__main__":
    unittest.main()
