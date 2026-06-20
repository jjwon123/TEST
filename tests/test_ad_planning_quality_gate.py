from __future__ import annotations

import unittest

from services.ad_strategy.quality_gate import deterministic_quality_issues


def issue(severity: str, issue_id: str, message: str) -> dict[str, str]:
    return {"severity": severity, "id": issue_id, "message": message}


def brief(*, offer: str = "", required: list[str] | None = None) -> dict:
    return {
        "event_name": "수분 장벽 위크",
        "target": {"summary": "건조함을 느끼는 고객"},
        "offer": {"summary": offer},
        "constraints": {"required_phrases": required or ["세라마이드 앰플"], "banned_words": []},
    }


def package(channel: str, copy: dict) -> dict:
    return {"outputs": [{"channelId": channel, "copy": copy}]}


class AdPlanningQualityGateTests(unittest.TestCase):
    def test_blocks_unverified_price_discount_duration_and_efficacy_claims(self) -> None:
        value = package("instagram_feed", {
            "firstLine": "단 3일 만에 즉시 개선",
            "body": "세라마이드 앰플을 지금 20% 할인된 19,900원에 만나보세요.",
            "cta": "구매하기",
        })
        ids = {item["id"] for item in deterministic_quality_issues(brief(), value, industry="cosmetics_skincare", source_originals=[], issue=issue)}
        self.assertIn("unsupported_claim", ids)

    def test_allows_claims_explicitly_present_in_input_facts(self) -> None:
        value = package("instagram_feed", {
            "firstLine": "세라마이드 앰플 20% 할인",
            "body": "세라마이드 앰플을 20% 할인 혜택으로 만나보세요.",
            "cta": "구매하기",
        })
        ids = {item["id"] for item in deterministic_quality_issues(brief(offer="세라마이드 앰플 20% 할인"), value, industry="cosmetics_skincare", source_originals=[], issue=issue)}
        self.assertNotIn("unsupported_claim", ids)

    def test_blocks_competitor_expression_and_industry_mismatch(self) -> None:
        copied = "바쁜 아침에도 피부가 편안하도록 한 번의 루틴으로 준비했습니다."
        value = package("instagram_feed", {
            "firstLine": "다이아몬드처럼 빛나는 피부",
            "body": copied,
            "cta": "자세히 보기",
        })
        ids = {item["id"] for item in deterministic_quality_issues(brief(), value, industry="cosmetics_skincare", source_originals=[copied], issue=issue)}
        self.assertIn("copied_expression", ids)
        self.assertIn("industry_mismatch", ids)

    def test_warns_on_channel_contract_internal_marker_and_weak_connections(self) -> None:
        value = package("instagram_feed", {
            "firstLine": "여기에 입력",
            "body": "작성 필요",
        })
        ids = {item["id"] for item in deterministic_quality_issues(brief(offer="미니 크림 증정"), value, industry="cosmetics_skincare", source_originals=[], issue=issue)}
        self.assertTrue({"channel_contract_missing", "internal_writing_marker", "weak_product_connection", "weak_offer_connection", "weak_cta"}.issubset(ids))

    def test_warns_when_long_copy_is_reused_across_channels(self) -> None:
        repeated = "세라마이드 앰플로 매일 부담 없이 이어가는 수분 장벽 루틴을 시작해보세요."
        value = {
            "outputs": [
                {"channelId": "instagram_feed", "copy": {"firstLine": "첫 문장", "body": repeated, "cta": "보기"}},
                {"channelId": "blog_thumbnail", "copy": {"headline": repeated, "subcopy": "설명", "cta": "보기"}},
            ]
        }
        ids = {item["id"] for item in deterministic_quality_issues(brief(), value, industry="cosmetics_skincare", source_originals=[], issue=issue)}
        self.assertIn("channel_copy_reuse", ids)

    def test_blocks_requested_channel_mismatch_and_warns_on_metadata_and_length(self) -> None:
        value = package("twitter_image", {"post": "가" * 300, "followUp": "보기", "cta": "보기"})
        current_brief = brief()
        current_brief["channels"] = ["instagram_feed"]
        ids = {item["id"] for item in deterministic_quality_issues(current_brief, value, industry="cosmetics_skincare", source_originals=[], issue=issue)}
        self.assertIn("channel_mismatch", ids)
        self.assertIn("output_metadata_missing", ids)
        self.assertIn("channel_character_limit", ids)


if __name__ == "__main__":
    unittest.main()
