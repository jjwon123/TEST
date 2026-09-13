from __future__ import annotations

import unittest
from datetime import date
from importlib import import_module
from pathlib import Path

from scripts.audit_planning_quality import audit_brief, audit_plan
from services.ad_strategy.library import adapt_patterns, extract_strategy_record

_core_messages = import_module("pipeline.01_event_brief.handlers.generate_brief")._core_messages
_build_brief = import_module("pipeline.01_event_brief.handlers.generate_brief").build_brief
_open_questions = import_module("pipeline.01_event_brief.handlers.generate_brief")._open_questions
_slides = import_module("pipeline.02_content_planning.handlers.generate_content_plan")._slides
_build_reference_direction = import_module(
    "pipeline.03_reference_research.handlers.run_reference_research"
)._build_reference_direction


class PlanningStrategyQualityTests(unittest.TestCase):
    def test_expired_event_schedule_requires_review_update(self) -> None:
        questions = _open_questions(
            {
                "eventName": "지난 이벤트",
                "target": "고객",
                "channels": ["instagram"],
                "offer": "샘플 증정",
                "schedule": {
                    "startDate": "2026-06-01",
                    "endDate": "2026-06-30",
                },
            },
            {"brandName": "테스트", "styleRules": ["과장하지 않는다."]},
            today=date(2026, 7, 18),
        )

        self.assertIn("이벤트 종료일이 이미 지났습니다. 현재 집행 일정으로 갱신해야 합니다.", questions)

    def test_event_brief_preserves_explicit_event_type(self) -> None:
        brief = _build_brief(
            "seasonal-event",
            {
                "eventName": "장마철 루틴",
                "eventType": "seasonal",
                "objective": "장마철 루틴을 제안한다.",
                "target": "냉방 속 속당김을 느끼는 고객",
                "offer": "앰플 구매 시 크림 증정",
                "channels": ["instagram"],
                "schedule": {
                    "startDate": "2026-06-01",
                    "endDate": "2026-06-30",
                },
            },
            {"brandName": "테스트", "styleRules": ["과장하지 않는다."]},
        )

        self.assertEqual("seasonal", brief["event_type"])

    def test_event_brief_persists_inferred_seasonal_type_with_gift_offer(self) -> None:
        brief = _build_brief(
            "seasonal-event",
            {
                "eventName": "6월 장마철 수분 장벽 리셋 위크",
                "objective": "장마철 습도와 냉방 환경에 맞는 루틴을 제안한다.",
                "target": "냉방 속 속당김을 느끼는 고객",
                "offer": "앰플 구매 시 크림 증정",
                "channels": ["instagram"],
                "schedule": {
                    "startDate": "2026-06-01",
                    "endDate": "2026-06-30",
                },
            },
            {"brandName": "테스트", "styleRules": ["과장하지 않는다."]},
        )

        self.assertEqual("seasonal", brief["event_type"])

    def test_core_messages_turn_inputs_into_strategy_roles(self) -> None:
        objective = "제품 구매 전환을 유도한다."
        offer = "구매 시 미니 크림을 증정한다."

        messages = _core_messages(
            objective,
            offer,
            ["장마철 수분 장벽 케어", "세라마이드 앰플"],
            target="냉방 공간에서 속당김을 느끼는 직장인",
            notes="할인보다 루틴 제안을 먼저 전달한다.",
        )

        self.assertTrue(messages[0].startswith("공감 진입:"))
        self.assertTrue(messages[1].startswith("핵심 제안 방향:"))
        self.assertTrue(messages[2].startswith("제품 역할 정의:"))
        self.assertNotIn(objective, messages)
        self.assertNotIn("케어을", " ".join(messages))
        self.assertNotIn("앰플가", " ".join(messages))

    def test_cardnews_slides_receive_message_intents(self) -> None:
        slides = _slides(
            {
                "typical_slides": [5],
                "content_roles": ["hook", "problem", "benefit", "how_to_join", "cta"],
            },
            {"core_messages": ["공감", "해결", "제품", "혜택"]},
        )

        self.assertEqual(5, len(slides))
        self.assertTrue(all(item["message_intent"] for item in slides))
        self.assertEqual("공감", slides[0]["message_intent"])
        self.assertEqual("혜택", slides[-1]["message_intent"])

    def test_audit_warns_on_unenriched_brief_and_generic_plan(self) -> None:
        objective = "인지도와 구매 전환을 유도한다."
        brief = {
            "objective": {"primary": objective},
            "core_messages": [objective, "혜택", "제품 중심으로 안내한다."],
            "constraints": {"banned_words": ["기적"]},
            "quality_assessment": {},
        }
        event_input = {
            "eventName": "테스트",
            "target": "타깃",
            "offer": "혜택",
            "objective": objective,
        }
        plan = {
            "deliverables": [
                {"deliverable_id": f"d{index}", "purpose": objective, "copy_intent": objective, "visual_need": "visual"}
                for index in range(3)
            ],
            "image_needs": [{}, {}, {}],
            "strategy_summary": {"planning_thesis": f"{objective} {objective}"},
        }

        brief_issue_ids = {item["id"] for item in audit_brief(event_input, {"brandName": "브랜드"}, brief)}
        plan_issue_ids = {item["id"] for item in audit_plan(brief, plan)}

        self.assertIn("brief_low_strategic_enrichment", brief_issue_ids)
        self.assertIn("plan_generic_channel_roles", plan_issue_ids)
        self.assertIn("plan_repetitive_strategy_thesis", plan_issue_ids)

    def test_specific_brand_visuals_override_generic_profile_colors(self) -> None:
        direction = _build_reference_direction(
            {
                "intent": {"event_profile": "cosmetics_skincare"},
                "search_queries": [],
            },
            [],
            event_input={"references": ["차분한 장마철 실내외 대비"]},
            brand_guide={
                "visual": {
                    "mood": ["calm dermacosmetic", "soft neutral"],
                    "brandColors": ["#E8F0ED", "#334640"],
                }
            },
        )

        self.assertEqual(["#E8F0ED", "#334640"], direction["colorPalette"])
        self.assertFalse(any("orange accent" in hint for hint in direction["promptHints"]))
        self.assertTrue(any("차분한 장마철" in hint for hint in direction["promptHints"]))

    def test_meta_copy_is_abstracted_without_verbatim_reuse(self) -> None:
        record = extract_strategy_record(
            {
                "brand": "테스트브랜드",
                "libraryId": "123",
                "cta": "더 알아보기",
                "copy": "활성\n라이브러리 ID: 123\n테스트브랜드\n광고\n속당김이 고민이라면?\n세라마이드로 매일 장벽 케어\n구매 시 미니 크림 증정\n더 알아보기",
            },
            query="스킨케어 세럼",
            source_path=Path("references/meta_ads/searches/test/collected-ads.json"),
        )

        self.assertIsNotNone(record)
        serialized = str(record["strategy"])
        self.assertNotIn("속당김이 고민이라면", serialized)
        self.assertEqual("question_or_challenge", record["strategy"]["hookType"])
        self.assertIn("gift_with_purchase", record["strategy"]["offerMechanics"])

    def test_patterns_are_rewritten_for_current_event(self) -> None:
        concepts = adapt_patterns(
            {
                "event_input": {
                    "eventName": "장마철 이벤트",
                    "target": "장마철에는 번들거리지만 냉방 공간에서는 속당김을 느끼는 직장인",
                    "offer": "앰플 구매 시 장벽 크림 증정",
                    "requiredPhrases": ["장마철 수분 장벽 케어", "세라마이드 앰플"],
                }
            },
            [{"hookType": "question_or_challenge"}],
        )

        self.assertIn("장마철", concepts["headlineDirections"][0])
        self.assertIn("세라마이드 앰플", concepts["channelCopyDirections"]["blog_inline_image"][0])
        self.assertNotIn("앰플를", str(concepts))
        self.assertNotIn("케어을", str(concepts))


if __name__ == "__main__":
    unittest.main()
