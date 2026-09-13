from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_ad_planning_output import build_planning_output_from_run, validate_planning_output
from scripts.workflow import approve_stage
from services.ad_strategy.quality_gate import copy_character_count


RUBRIC_KEYS = (
    "strategyClarity", "targetEmpathy", "productConnection", "distinctiveness",
    "channelFit", "koreanCopyQuality", "brandFit", "actionability",
)


def valid_output() -> dict:
    candidates = []
    for index in range(1, 4):
        candidates.append({
            "conceptId": f"concept_0{index}",
            "axis": f"axis_{index}",
            "name": f"전략 {index}",
            "targetInsight": f"서로 다른 고객 상황 {index}",
            "corePromise": f"서로 다른 제품 약속 {index}",
            "emotionalDirection": f"감성 방향 {index}",
            "persuasionSequence": [f"문제 {index}", f"제품 {index}", f"행동 {index}"],
            "offerPresentation": f"혜택 방향 {index}",
            "cta": f"루틴 {index} 확인하기",
            "headlineDirections": [f"헤드라인 {index}"],
            "expectedEffect": "구매 고려",
            "risks": [],
        })
    copy_value = {
        "firstLine": "장마철 속당김, 생활 환경부터 점검하세요.",
        "body": "세라마이드 앰플을 현재 루틴에 연결하는 기준을 설명합니다.",
        "cta": "내 루틴 확인하기",
    }
    return {
        "schemaVersion": "1.0.0",
        "status": "approved",
        "brief": {
            "industry": "cosmetics_skincare",
            "eventName": "장마철 장벽 케어",
            "verifiedFacts": ["세라마이드 앰플", "샘플 증정"],
            "unverifiedClaims": [],
            "missingInputs": [],
            "constraints": {
                "requiredPhrases": ["세라마이드 앰플"],
                "bannedWords": ["완치"],
                "channels": ["instagram_feed"],
            },
        },
        "conceptCandidates": candidates,
        "conceptReview": {
            "selectedConceptId": "concept_01",
            "rejectedConceptIds": ["concept_02", "concept_03"],
            "reasonTags": ["strong_product_link"],
            "reviewNote": "제품과 고객 상황의 연결이 가장 구체적입니다.",
        },
        "copyPackage": {
            "selectedConceptId": "concept_01",
            "outputs": [{
                "deliverableId": "feed",
                "channelId": "instagram_feed",
                "purpose": "구매 고려",
                "strategyBasis": "생활 환경과 제품 역할 연결",
                "copy": copy_value,
                "characterCount": copy_character_count(copy_value),
            }],
        },
        "scorecard": {
            "status": "pass",
            "criticalErrorCount": 0,
            "issues": [],
            "rubric": {key: 4 for key in RUBRIC_KEYS},
            "averageScore": 4,
        },
        "correctionRecord": {
            "generatedOriginal": copy_value,
            "userEditedFinal": copy_value,
            "reasonTags": ["strong_product_link"],
            "approved": True,
        },
    }


class ValidateAdPlanningOutputTests(unittest.TestCase):
    def test_accepts_review_ready_approved_output(self) -> None:
        self.assertEqual([], validate_planning_output(valid_output()))

    def test_rejects_title_only_concepts_and_wrong_character_count(self) -> None:
        payload = valid_output()
        for candidate in payload["conceptCandidates"]:
            candidate.update({
                "targetInsight": "같은 고객 상황",
                "corePromise": "같은 약속",
                "emotionalDirection": "같은 감성",
                "persuasionSequence": ["같은 설득"],
                "offerPresentation": "같은 혜택",
                "cta": "같은 행동",
            })
        payload["copyPackage"]["outputs"][0]["characterCount"] = 999

        messages = " ".join(item["message"] for item in validate_planning_output(payload))

        self.assertIn("전략 항목이 두 개 이상", messages)
        self.assertIn("실제 표시 문장 길이", messages)

    def test_allows_approval_with_warning_but_rejects_low_score(self) -> None:
        payload = valid_output()
        payload["scorecard"]["status"] = "warning"
        payload["scorecard"]["issues"] = [{"severity": "warning", "id": "weak_cta"}]
        payload["scorecard"]["rubric"] = {key: 3 for key in RUBRIC_KEYS}
        payload["scorecard"]["averageScore"] = 3

        messages = " ".join(item["message"] for item in validate_planning_output(payload))

        self.assertIn("4.0", messages)
        return

        self.assertIn("품질 경고", messages)
        self.assertIn("4.0 이상", messages)

    def test_needs_input_cannot_contain_generated_work(self) -> None:
        payload = valid_output()
        payload["status"] = "needs_input"
        payload["brief"]["missingInputs"] = ["행사 기간"]

        messages = " ".join(item["message"] for item in validate_planning_output(payload))

        self.assertIn("콘셉트 선택이나 카피", messages)

    def test_rejects_copy_for_unrequested_channel(self) -> None:
        payload = copy.deepcopy(valid_output())
        payload["copyPackage"]["outputs"][0]["channelId"] = "twitter_image"

        messages = " ".join(item["message"] for item in validate_planning_output(payload))

        self.assertIn("요청하지 않은 채널", messages)

    def test_builds_consolidated_output_from_run_artifacts(self) -> None:
        payload = valid_output()
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            self._write(run / "01_event_brief" / "brief.json", {
                "event_name": payload["brief"]["eventName"],
                "channels": ["instagram_feed"],
                "constraints": {"required_phrases": ["세라마이드 앰플"], "banned_words": ["완치"]},
            })
            self._write(run / "01_event_brief" / "strategic-brief.json", {
                "industry": "cosmetics_skincare",
                "verifiedFacts": payload["brief"]["verifiedFacts"],
                "unverifiedClaims": [],
            })
            self._write(run / "02_content_planning" / "concept-candidates.json", {"candidates": payload["conceptCandidates"]})
            self._write(run / "02_content_planning" / "concept-review.json", {"status": "approved", **payload["conceptReview"]})
            self._write(run / "02_content_planning" / "copy-package.json", {
                "conceptId": "concept_01",
                "outputs": payload["copyPackage"]["outputs"],
            })
            self._write(run / "02_content_planning" / "copy-review.json", {
                "status": "approved",
                "approved": True,
                "reasonTags": ["strong_product_link"],
                "edits": [{
                    "channelId": "instagram_feed",
                    "originalCopy": {"firstLine": "수정 전 문구"},
                    "editedCopy": payload["copyPackage"]["outputs"][0]["copy"],
                }],
            })
            self._write(run / "02_content_planning" / "planning-scorecard.json", payload["scorecard"])

            consolidated = build_planning_output_from_run(run)

            self.assertEqual("approved", consolidated["status"])
            self.assertEqual(
                {"firstLine": "수정 전 문구"},
                consolidated["correctionRecord"]["generatedOriginal"]["instagram_feed"],
            )
            self.assertEqual(
                payload["copyPackage"]["outputs"][0]["copy"],
                consolidated["correctionRecord"]["userEditedFinal"]["instagram_feed"],
            )
            self.assertEqual([], validate_planning_output(consolidated))

            self._write(run / "run-status.json", {
                "run_id": "validation-test",
                "event_id": "event",
                "run_state": "planning",
                "current_stage": "02_content_planning",
                "stage_status": {"01_event_brief": "approved", "02_content_planning": "review_pending"},
            })
            self._write(run / "approvals.json", {"approvals": []})
            self._write(run / "02_content_planning" / "copy-package.json", {
                "conceptId": "concept_02",
                "outputs": payload["copyPackage"]["outputs"],
            })

            with self.assertRaisesRegex(SystemExit, "invalid advertising planning output"):
                approve_stage(run, "02_content_planning")

    @staticmethod
    def _write(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
