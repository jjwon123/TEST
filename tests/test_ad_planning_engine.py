from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.ad_strategy.planning_engine import (
    build_concept_candidates,
    build_copy_package,
    build_strategic_brief,
    detect_event_type,
    score_planning,
)
from services.ad_strategy.quality_gate import copy_character_count
from services.ad_strategy.repository import legacy_to_example
from scripts.audit_planning_quality import audit_campaign_package
from scripts.workflow import approve_stage
from services.llm.promotion import evaluate_local_promotion


def sample_brief() -> dict:
    return {
        "event_id": "test-event",
        "event_name": "6월 장마철 장벽 케어",
        "brand": {"name": "테스트브랜드"},
        "objective": {"primary": "구매 고려를 높인다."},
        "target": {"summary": "장마철 속당김을 느끼는 직장인"},
        "offer": {"summary": "앰플 구매 시 샘플 증정"},
        "channels": ["instagram_cardnews", "instagram_feed"],
        "constraints": {
            "required_phrases": ["장마철 수분 장벽 케어", "세라마이드 앰플"],
            "banned_words": ["기적"],
        },
        "open_questions": [],
    }


class AdPlanningEngineTests(unittest.TestCase):
    def test_builds_three_distinct_concepts_and_copy(self) -> None:
        brief = sample_brief()
        strategic = build_strategic_brief(brief)
        candidates = build_concept_candidates(brief)
        concepts = candidates["candidates"]
        package = build_copy_package(brief, concepts[0], [
            {"deliverable_id": "card", "channel_id": "instagram_cardnews", "purpose": "설득", "slides": [{"role": "hook"}, {"role": "benefit"}, {"role": "cta"}]},
            {"deliverable_id": "feed", "channel_id": "instagram_feed", "purpose": "전환"},
        ])
        scorecard = score_planning(brief, candidates, package)

        self.assertEqual("cosmetics_skincare", strategic["industry"])
        self.assertEqual(3, len(concepts))
        self.assertEqual(3, len({item["axis"] for item in concepts}))
        self.assertEqual(2, len(package["outputs"]))
        self.assertEqual(0, scorecard["criticalErrorCount"])
        self.assertNotIn("은(는)", str(package))
        self.assertNotIn("입력된 사실 안에서", str(package))
        first_output = package["outputs"][0]
        self.assertIn("장마철 속당김을 느끼는 직장인", first_output["strategyBasis"])
        self.assertNotIn("직장인로", first_output["strategyBasis"])
        self.assertNotIn("증정는", first_output["strategyBasis"])
        self.assertIn("세라마이드 앰플", first_output["planningEvidence"]["productRole"])
        self.assertIn("앰플 구매 시 샘플 증정", first_output["planningEvidence"]["offerRole"])
        self.assertIn("공감에서 이해와 행동까지 순차 설득", first_output["planningEvidence"]["channelRole"])
        for output in package["outputs"]:
            self.assertEqual(copy_character_count(output["copy"]), output["characterCount"])
        transitions = [
            slide["transition"]
            for slide in first_output["copy"]["slides"]
            if slide.get("transition")
        ]
        self.assertEqual(len(transitions), len(set(transitions)))

    def test_channel_copy_variants_do_not_reuse_long_sentences(self) -> None:
        brief = sample_brief()
        candidates = build_concept_candidates(brief)
        concept = candidates["candidates"][2]
        package = build_copy_package(brief, concept, [
            {
                "deliverable_id": "card",
                "channel_id": "instagram_cardnews",
                "purpose": "설득",
                "slides": [
                    {"role": "hook"},
                    {"role": "problem"},
                    {"role": "benefit"},
                    {"role": "offer"},
                    {"role": "cta"},
                ],
            },
            {"deliverable_id": "feed", "channel_id": "instagram_feed", "purpose": "전환"},
            {"deliverable_id": "thumb", "channel_id": "blog_thumbnail", "purpose": "진입"},
            {"deliverable_id": "article", "channel_id": "blog_inline_image", "purpose": "설명"},
        ])
        scorecard = score_planning(brief, candidates, package)
        issue_ids = {item["id"] for item in scorecard["issues"]}

        self.assertNotIn("repetitive_copy", issue_ids)
        self.assertNotIn("channel_copy_reuse", issue_ids)

    def test_copy_uses_natural_particles_for_vowel_ending_product(self) -> None:
        brief = {
            **sample_brief(),
            "constraints": {
                **sample_brief()["constraints"],
                "required_phrases": ["장마철 수분 루틴", "진정 토너"],
            },
        }
        candidates = build_concept_candidates(brief)
        package = build_copy_package(brief, candidates["candidates"][0], [
            {"deliverable_id": "feed", "channel_id": "instagram_feed", "purpose": "전환"},
            {"deliverable_id": "community", "channel_id": "community_banner", "purpose": "전환"},
        ])

        rendered = json.dumps(package, ensure_ascii=False)
        self.assertIn("진정 토너를", rendered)
        self.assertIn("진정 토너와", rendered)
        self.assertNotIn("진정 토너을", rendered)
        self.assertNotIn("진정 토너과", rendered)

    def test_explicit_event_type_wins_over_offer_keywords(self) -> None:
        brief = {
            **sample_brief(),
            "event_type": "seasonal",
            "offer": {"summary": "앰플 구매 시 장벽 크림 증정"},
        }

        strategic = build_strategic_brief(brief)
        candidates = build_concept_candidates(brief)

        self.assertEqual("seasonal", strategic["eventType"])
        self.assertEqual("seasonal", candidates["eventType"])

    def test_seasonal_campaign_intent_wins_over_secondary_gift_offer(self) -> None:
        brief = {
            **sample_brief(),
            "event_name": "6월 장마철 수분 장벽 리셋 위크",
            "objective": {
                "primary": "장마철 습도와 냉방 환경에 맞는 장벽 케어 루틴을 제안한다."
            },
            "offer": {"summary": "앰플 구매 시 장벽 크림 10ml 증정"},
        }

        self.assertEqual("seasonal", detect_event_type(brief))

    def test_promotion_campaign_stays_promotion_when_gift_is_primary_intent(self) -> None:
        brief = {
            **sample_brief(),
            "event_name": "앰플 구매 사은 행사",
            "objective": {"primary": "증정 혜택으로 신규 구매 전환을 유도한다."},
        }

        self.assertEqual("promotion", detect_event_type(brief))

    def test_local_copy_reuses_only_same_event_exact_corrections(self) -> None:
        brief = sample_brief()
        deliverables = [{"deliverable_id": "feed", "channel_id": "instagram_feed", "purpose": "전환"}]
        candidates = build_concept_candidates(brief)
        with patch("services.ad_strategy.planning_engine.retrieve_corrections", return_value=[]):
            baseline = build_copy_package(brief, candidates["candidates"][0], deliverables)
        original = baseline["outputs"][0]["copy"]
        edited = {**original, "firstLine": "장마철 속당김, 루틴의 기준부터 다시 봅니다."}
        correction = {
            "id": "correction-1",
            "eventId": "test-event",
            "channelId": "instagram_feed",
            "originalCopy": original,
            "editedCopy": edited,
            "approved": True,
        }
        with patch("services.ad_strategy.planning_engine.retrieve_corrections", return_value=[correction]):
            corrected = build_copy_package(brief, candidates["candidates"][0], deliverables)
        self.assertEqual(edited["firstLine"], corrected["outputs"][0]["copy"]["firstLine"])
        self.assertEqual(["correction-1"], corrected["outputs"][0]["correctionExampleIds"])
        self.assertEqual(["correction-1"], corrected["correctionSearch"]["appliedIds"])

        other_event = {**correction, "id": "correction-2", "eventId": "another-event"}
        with patch("services.ad_strategy.planning_engine.retrieve_corrections", return_value=[other_event]):
            untouched = build_copy_package(brief, candidates["candidates"][0], deliverables)
        self.assertEqual(original["firstLine"], untouched["outputs"][0]["copy"]["firstLine"])
        self.assertEqual([], untouched["correctionSearch"]["appliedIds"])

    def test_scorecard_warns_when_marketing_signals_are_not_selected(self) -> None:
        brief = sample_brief()
        with tempfile.TemporaryDirectory() as tmp:
            insight_path = Path(tmp) / "missing-insight.json"
            with patch("services.ad_strategy.planning_engine.INSIGHT_BRIEF_PATH", insight_path):
                candidates = build_concept_candidates(brief)
                package = build_copy_package(brief, candidates["candidates"][0], [
            {"deliverable_id": "feed", "channel_id": "instagram_feed", "purpose": "전환"},
                ])
        scorecard = score_planning(brief, candidates, package)

        self.assertIn("marketing_signal_review_required", {item["id"] for item in scorecard["issues"]})
        self.assertEqual("needs_signal_review", candidates["marketingEvidenceStatus"])
        self.assertEqual("needs_signal_review", package["marketingEvidenceStatus"])

    def test_ready_insight_brief_is_attached_to_concepts_and_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            insight_path = Path(tmp) / "insight-brief.json"
            insight_path.write_text(json.dumps({
                "schemaVersion": "1.0.0",
                "eventId": "test-event",
                "industry": "cosmetics_skincare",
                "status": "ready",
                "minimumSelectedSignals": 3,
                "selectedSignalCount": 3,
                "targetHypotheses": ["냉방으로 건조해지는 사무직 고객"],
                "customerPains": ["냉방으로 건조해지는 사무직 고객은 오후 들뜸에 반응한다."],
                "customerDesires": ["간단한 루틴으로 컨디션을 정리하고 싶다."],
                "purchaseObjections": ["또 비슷한 앰플인지 모르겠다는 의심"],
                "trendHooks": ["장마철 습도와 냉방 간극"],
                "seasonalHooks": ["휴가 전후 피부 컨디션 관리 수요"],
                "productProofs": [],
                "offerAngles": [],
                "channelPatterns": ["첫 문장에서 내 상황을 바로 말해야 멈춘다."],
                "evidenceDetails": [
                    {
                        "signalId": "signal-a",
                        "evidenceType": "pain",
                        "targetSegment": "냉방 실내에서 오후 속당김을 느끼는 사무직 고객",
                        "insight": "냉방 환경의 불편을 생활 루틴 기준으로 다룬다.",
                        "sourceType": "review",
                        "sourceName": "고객 리뷰",
                        "observedAt": "2026-06-18",
                        "claimBoundary": "",
                    },
                    {
                        "signalId": "signal-b",
                        "evidenceType": "trend",
                        "targetSegment": "복잡한 루틴을 줄이고 싶은 고객",
                        "insight": "편안함과 단순함을 선택 기준으로 제안한다.",
                        "sourceType": "public_web",
                        "sourceName": "시장 조사",
                        "observedAt": "2026-06-18",
                        "claimBoundary": "",
                    },
                    {
                        "signalId": "signal-c",
                        "evidenceType": "timing",
                        "targetSegment": "계절 변화에 맞춰 루틴을 점검하는 고객",
                        "insight": "계절 변화는 루틴 점검의 시기 명분으로만 사용한다.",
                        "sourceType": "weather",
                        "sourceName": "날씨 자료",
                        "observedAt": "2026-06-18",
                        "claimBoundary": "",
                    },
                ],
                "doNotClaim": ["랭킹을 단정하지 않는다."],
                "evidenceSignalIds": ["signal-a", "signal-b", "signal-c"],
                "createdAt": "2026-06-18T00:00:00+00:00",
            }, ensure_ascii=False), encoding="utf-8")

            with patch("services.ad_strategy.planning_engine.INSIGHT_BRIEF_PATH", insight_path):
                candidates = build_concept_candidates(sample_brief())
                package = build_copy_package(sample_brief(), candidates["candidates"][0], [
                    {"deliverable_id": "feed", "channel_id": "instagram_feed", "purpose": "전환"},
                ])

        self.assertEqual("ready", candidates["marketingEvidenceStatus"])
        self.assertEqual("test-event", candidates["marketingEvidenceEventId"])
        self.assertEqual(["signal-a", "signal-b", "signal-c"], candidates["marketingSignalIds"])
        self.assertEqual("ready", candidates["candidates"][0]["marketingEvidence"]["status"])
        self.assertIn("냉방 실내에서 오후 속당김을 느끼는 사무직 고객", candidates["candidates"][0]["targetInsight"])
        self.assertNotIn("날씨 자료", candidates["candidates"][0]["targetInsight"])
        self.assertEqual(["pain"], candidates["candidates"][0]["marketingEvidence"]["evidenceTypes"])
        self.assertEqual(["trend"], candidates["candidates"][1]["marketingEvidence"]["evidenceTypes"])
        self.assertEqual(["timing", "trend"], candidates["candidates"][2]["marketingEvidence"]["evidenceTypes"])
        for concept in candidates["candidates"]:
            evidence = concept["marketingEvidence"]
            self.assertEqual(3, len(evidence["signalIds"]))
            self.assertTrue(set(evidence["primarySignalIds"]).issubset(set(evidence["signalIds"])))
            self.assertEqual(
                set(evidence["signalIds"]),
                set(evidence["primarySignalIds"]) | set(evidence["supportingSignalIds"]),
            )
        self.assertEqual(["signal-a"], candidates["candidates"][0]["marketingEvidence"]["primarySignalIds"])
        self.assertEqual(["signal-b"], candidates["candidates"][1]["marketingEvidence"]["primarySignalIds"])
        self.assertEqual(
            ["signal-c", "signal-b"],
            candidates["candidates"][2]["marketingEvidence"]["primarySignalIds"],
        )
        self.assertEqual("concept_03", candidates["recommendation"]["recommendedConceptId"])
        self.assertEqual(
            "recommendation_only_human_selection_required",
            candidates["recommendation"]["decisionPolicy"],
        )
        output = package["outputs"][0]
        self.assertEqual("ready", output["planningEvidence"]["marketingEvidenceStatus"])
        self.assertEqual("test-event", output["planningEvidence"]["marketingEvidenceEventId"])
        self.assertIn("검수된 마케팅 신호", output["strategyBasis"])
        self.assertIn("첫 문장에서 내 상황", output["planningEvidence"]["marketingSignals"][0])

    def test_ready_evidence_from_another_event_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            insight_path = Path(tmp) / "insight-brief.json"
            insight_path.write_text(json.dumps({
                "eventId": "another-event",
                "industry": "cosmetics_skincare",
                "status": "ready",
                "selectedSignalCount": 3,
                "minimumSelectedSignals": 3,
                "evidenceSignalIds": ["other-1", "other-2", "other-3"],
                "doNotClaim": [],
            }), encoding="utf-8")
            with patch("services.ad_strategy.planning_engine.INSIGHT_BRIEF_PATH", insight_path):
                candidates = build_concept_candidates(sample_brief())
        self.assertEqual("needs_signal_review", candidates["marketingEvidenceStatus"])
        self.assertEqual([], candidates["marketingSignalIds"])

    def test_scorecard_warns_on_awkward_and_repetitive_copy(self) -> None:
        brief = sample_brief()
        brief["channels"] = []
        candidates = build_concept_candidates(brief)
        bad_copy = {
            "status": "review_pending",
            "outputs": [
                {
                    "copy": {
                        "body": "직장인은(는) 입력된 사실 안에서 설명합니다.",
                        "sections": [
                            "같은 문장이 세 번 이상 반복되는 품질 문제입니다.",
                            "같은 문장이 세 번 이상 반복되는 품질 문제입니다.",
                            "같은 문장이 세 번 이상 반복되는 품질 문제입니다.",
                        ],
                    }
                }
            ],
        }
        scorecard = score_planning(brief, candidates, bad_copy)
        ids = {item["id"] for item in scorecard["issues"]}

        self.assertEqual("warning", scorecard["status"])
        self.assertIn("awkward_korean", ids)
        self.assertIn("repetitive_copy", ids)
        self.assertEqual(1, scorecard["rubric"]["koreanCopyQuality"])

    def test_scorecard_blocks_critic_failure_and_keeps_unresolved_revision_as_warning(self) -> None:
        brief = sample_brief()
        candidates = build_concept_candidates(brief)
        package = build_copy_package(brief, candidates["candidates"][0], [
            {"deliverable_id": "feed", "channel_id": "instagram_feed", "purpose": "전환"},
            {"deliverable_id": "card", "channel_id": "instagram_cardnews", "purpose": "설득"},
        ])
        package["criticReview"] = {"status": "fail", "issues": [], "rubric": {}}
        failed = score_planning(brief, candidates, package)
        package["criticReview"] = {"status": "revise", "issues": [], "rubric": {}}
        revise = score_planning(brief, candidates, package)
        self.assertIn("copy_critic_failed", {item["id"] for item in failed["issues"]})
        self.assertEqual("fail", failed["status"])
        self.assertIn("copy_critic_revision_unresolved", {item["id"] for item in revise["issues"]})

    def test_scorecard_does_not_hide_concept_critic_failure_behind_copy_critic_pass(self) -> None:
        brief = sample_brief()
        candidates = build_concept_candidates(brief)
        candidates["criticReview"] = {"status": "fail", "issues": [], "rubric": {}}
        package = build_copy_package(brief, candidates["candidates"][0], [
            {"deliverable_id": "feed", "channel_id": "instagram_feed", "purpose": "전환"},
            {"deliverable_id": "card", "channel_id": "instagram_cardnews", "purpose": "설득"},
        ])
        package["criticReview"] = {"status": "pass", "issues": [], "rubric": {}}
        scorecard = score_planning(brief, candidates, package)
        self.assertIn("concept_critic_failed", {item["id"] for item in scorecard["issues"]})
        self.assertEqual("fail", scorecard["status"])

    def test_legacy_patterns_are_unreviewed(self) -> None:
        item = legacy_to_example({
            "patternId": "legacy-1",
            "profile": "jewelry_luxury",
            "strategy": {"hookType": "brand_statement", "persuasionSequence": ["hook"], "offerMechanics": [], "ctaType": "soft_action", "toneTraits": []},
            "source": {},
        })
        self.assertEqual("jewelry_luxury", item["industry"])
        self.assertEqual("unreviewed", item["review"]["decision"])

    def test_audit_requires_human_approvals(self) -> None:
        issues = audit_campaign_package(
            sample_brief(),
            build_concept_candidates(sample_brief()),
            {"status": "review_pending"},
            {"status": "blocked_pending_concept_selection", "outputs": []},
            {"status": "blocked_pending_copy", "approved": False},
            {"criticalErrorCount": 0},
        )
        ids = {item["id"] for item in issues}
        self.assertIn("planning_concept_not_approved", ids)
        self.assertIn("planning_copy_not_approved", ids)

    def test_audit_surfaces_scorecard_quality_warnings(self) -> None:
        issues = audit_campaign_package(
            sample_brief(),
            build_concept_candidates(sample_brief()),
            {"status": "approved"},
            {"status": "review_pending", "outputs": []},
            {"status": "approved", "approved": True},
            {"criticalErrorCount": 0, "issues": [{"severity": "warning", "id": "awkward_korean"}]},
        )
        self.assertIn("planning_quality_warning", {item["id"] for item in issues})

    def test_workflow_blocks_stage_approval_without_internal_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "02_content_planning").mkdir()
            (run / "run-status.json").write_text(json.dumps({
                "run_id": "test",
                "event_id": "event",
                "run_state": "planning",
                "current_stage": "02_content_planning",
                "stage_status": {"01_event_brief": "approved", "02_content_planning": "review_pending"},
            }), encoding="utf-8")
            (run / "approvals.json").write_text('{"approvals":[]}', encoding="utf-8")
            (run / "02_content_planning" / "concept-review.json").write_text('{"status":"review_pending"}', encoding="utf-8")
            (run / "02_content_planning" / "copy-review.json").write_text('{"status":"blocked_pending_copy","approved":false}', encoding="utf-8")
            (run / "02_content_planning" / "planning-scorecard.json").write_text('{"criticalErrorCount":0}', encoding="utf-8")
            with self.assertRaises(SystemExit):
                approve_stage(run, "02_content_planning")

    def test_local_model_requires_eighty_percent_and_zero_critical_errors(self) -> None:
        eligible = evaluate_local_promotion([
            {"externalScore": 5, "localScore": 4, "localCriticalErrors": 0, "preferred": "external"},
            {"externalScore": 5, "localScore": 4.5, "localCriticalErrors": 0, "preferred": "local"},
        ])
        blocked = evaluate_local_promotion([
            {"externalScore": 5, "localScore": 5, "localCriticalErrors": 1, "preferred": "local"},
        ])
        self.assertEqual("eligible", eligible["promotionStatus"])
        self.assertEqual("not_eligible", blocked["promotionStatus"])


if __name__ == "__main__":
    unittest.main()
