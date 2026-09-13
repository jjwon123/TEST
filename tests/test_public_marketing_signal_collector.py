from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from services.marketing_intelligence.public_signal_collector import (
    collect_public_signals_from_snapshot,
    infer_normalized_insight,
    public_observation_to_signal,
    public_observation_quality_flags,
    sanitize_public_observation_text,
    PublicObservation,
)
from services.marketing_intelligence.repository import load_signals
from scripts.collect_marketing_signals import load_capture_urls


class PublicMarketingSignalCollectorTests(unittest.TestCase):
    def test_public_observations_become_unreviewed_marketing_signals(self) -> None:
        snapshot = {
            "eventId": "season-monsoon-barrier",
            "observations": [
                {
                    "sourceKind": "brand_site",
                    "url": "https://example.test/hsgn",
                    "title": "HSGN Niacinamide",
                    "topic": "hsgn_summer_tone_care",
                    "observedText": "HSGN 나이아신아마이드 100,000ppm 제품 소개와 여름 톤 케어 루틴 안내",
                    "strength": 4,
                    "freshness": 4,
                    "confidence": 3,
                },
                {
                    "sourceKind": "weather",
                    "topic": "hsgn_summer_tone_care",
                    "observedText": "6월 말 장마와 냉방 환경으로 피부 루틴 점검 수요가 생긴다.",
                },
            ]
        }

        signals = collect_public_signals_from_snapshot(snapshot, default_topic="fallback")

        self.assertEqual(2, len(signals))
        self.assertEqual("brand_site", signals[0]["sourceType"])
        self.assertEqual("season-monsoon-barrier", signals[0]["sourceRef"]["eventId"])
        self.assertEqual("proof", signals[0]["evidenceType"])
        self.assertEqual("unreviewed", signals[0]["review"]["decision"])
        self.assertIn("public_observation_not_copy_source", signals[0]["riskFlags"])
        self.assertEqual("weather", signals[1]["sourceType"])
        self.assertEqual("timing", signals[1]["evidenceType"])

    def test_public_collector_does_not_copy_meta_ad_expression_as_insight(self) -> None:
        observation = PublicObservation(
            source_kind="meta_ad",
            observed_text="경쟁 광고 원문: 여름 피부를 단번에 환하게 만드는 특별한 선택",
            topic="summer_tone_care",
        )

        signal = public_observation_to_signal(observation)

        self.assertEqual("meta_ad", signal["sourceType"])
        self.assertEqual("channel_pattern", signal["evidenceType"])
        self.assertNotEqual(signal["signalText"], signal["normalizedInsight"])
        self.assertIn("원문을 복사하지 않고", signal["normalizedInsight"])
        self.assertIn("do_not_copy_original_expression", signal["riskFlags"])

    def test_public_collector_preserves_research_provenance(self) -> None:
        signal = collect_public_signals_from_snapshot({
            "eventId": "education-barrier",
            "observations": [{
                "sourceKind": "public_web",
                "url": "https://www.aad.org/public/diseases/a-z/dry-skin-overview",
                "sourceName": "American Academy of Dermatology",
                "publishedAt": "2025-01-01",
                "observedAt": "2026-07-01",
                "methodology": "professional guidance",
                "topic": "skin_barrier_education",
                "observedText": "낮은 습도에서는 피부 수분 손실과 건조함이 흔하다는 전문기관 안내다.",
                "normalizedInsight": "환경과 생활 습관을 먼저 설명하고 제품 역할은 보습 유지로 제한한다.",
                "evidenceType": "pain",
            }],
        })[0]

        self.assertEqual("education-barrier", signal["sourceRef"]["eventId"])
        self.assertEqual("American Academy of Dermatology", signal["sourceRef"]["sourceName"])
        self.assertEqual("2026-07-01", signal["sourceRef"]["observedAt"])
        self.assertEqual("professional guidance", signal["sourceRef"]["methodology"])

    def test_public_capture_flags_raw_html_and_blocks_auto_select(self) -> None:
        observation = PublicObservation(
            source_kind="brand_site",
            observed_text="<html><body><script>window.__DATA__={\"headline\":\"copy me\"}</script><div>HSGN 여름 톤 케어 제품 설명</div></body></html>",
            topic="hsgn_summer_tone_care",
        )

        signal = public_observation_to_signal(observation, auto_select=True)

        self.assertEqual("unreviewed", signal["review"]["decision"])
        self.assertIn("raw_html_detected", signal["riskFlags"])
        self.assertIn("raw_json_detected", signal["riskFlags"])
        self.assertIn("capture_quality_blocked", signal["riskFlags"])
        self.assertNotIn("<html>", signal["signalText"])
        self.assertNotIn("script", signal["signalText"].lower())

    def test_public_capture_quality_flags_detect_thin_or_broken_text(self) -> None:
        self.assertIn("thin_public_observation", public_observation_quality_flags(PublicObservation(
            source_kind="public_web",
            observed_text="짧음",
            topic="hsgn",
        )))
        self.assertIn("broken_text_suspected", public_observation_quality_flags(PublicObservation(
            source_kind="public_web",
            observed_text="ì—¬ë¦„ í†¤ ì¼€ì–´",
            topic="hsgn",
        )))
        self.assertEqual("HSGN 여름 톤 케어", sanitize_public_observation_text("<div>HSGN 여름 톤 케어</div>"))

    def test_infer_search_trend_mentions_customer_context_and_choice_reason(self) -> None:
        insight = infer_normalized_insight(PublicObservation(
            source_kind="google_trends",
            observed_text="나이아신아마이드 세럼 검색 관심 상승",
            topic="hsgn",
        ))

        self.assertIn("고객 상황", insight)
        self.assertIn("선택 이유", insight)

    def test_collect_script_imports_public_snapshot_and_exports_review_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "snapshot.json"
            signals_path = root / "signals.json"
            sheet = root / "review.csv"
            snapshot.write_text(json.dumps({
                "observations": [{
                    "sourceKind": "naver_datalab",
                    "topic": "summer_tone_care",
                    "observedText": "여름 톤 케어 검색 관심이 계절 전환기에 증가한다.",
                }]
            }, ensure_ascii=False), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/collect_marketing_signals.py",
                    "--public-snapshot",
                    str(snapshot),
                    "--signals",
                    str(signals_path),
                    "--review-sheet",
                    str(sheet),
                    "--topic",
                    "summer_tone_care",
                    "--event-id",
                    "season-monsoon-barrier",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=True,
            )
            output = json.loads(completed.stdout)

            saved = load_signals(signals_path)
            exported_sheet = Path(output["reviewExport"]["sheet"])
            exported_sheet_exists = exported_sheet.exists()

        self.assertEqual(1, output["publicSignalCount"])
        self.assertTrue(exported_sheet_exists)
        self.assertEqual(1, len(saved))
        self.assertEqual("naver_datalab", saved[0]["sourceType"])
        self.assertEqual("unreviewed", saved[0]["review"]["decision"])
        self.assertEqual("season-monsoon-barrier", saved[0]["sourceRef"]["eventId"])

    def test_load_capture_urls_ignores_blank_lines_and_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            urls_path = Path(tmp) / "urls.txt"
            urls_path.write_text(
                "\n# HSGN public URLs\nhttps://example.test/product\n  https://example.test/review  \n",
                encoding="utf-8",
            )

            urls = load_capture_urls(urls_path)

        self.assertEqual(["https://example.test/product", "https://example.test/review"], urls)


if __name__ == "__main__":
    unittest.main()
