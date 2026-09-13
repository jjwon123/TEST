from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.ad_strategy.generation import _apply_targeted_concept_repair, _apply_targeted_copy_repair, generate_concepts, generate_copy
from services.ad_strategy.local_critic import _brief_product, review_local_copy
from services.ad_strategy.planning_engine import _difference_point, build_concept_candidates
from services.ad_strategy.quality_gate import copy_character_count
from services.ad_strategy.repository import append_correction, load_examples_for_review, retrieve_corrections, strategy_quality_metrics, update_example_review
from services.llm.openai_provider import OpenAIPlanningProvider
from scripts.benchmark_ad_planning import ROOT, _concept_result_status, _local_concept_only_critic_review, aggregate, blind_order_for, evaluate_case, is_final_human_review, result_needs_refresh, run_external_cases, save_human_review, select_external_concept, select_pending_concepts_for_connection_check
from scripts.audit_ad_planning_goal import build_audit
from scripts.workflow import approve_stage


def response_with(value: dict) -> dict:
    return {"model": "test-model", "output_text": json.dumps(value, ensure_ascii=False), "usage": {"total_tokens": 12}}


class AdPlanningUpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = {
            "event_id": "x", "event_name": "테스트 이벤트", "target": {"summary": "민감한 피부 고객"},
            "offer": {"summary": "샘플 증정"}, "channels": ["instagram_feed"],
            "constraints": {"required_phrases": ["세라마이드 앰플"], "banned_words": []},
        }

    def test_local_critic_does_not_mistake_gift_item_for_primary_product(self) -> None:
        current = {
            **self.brief,
            "constraints": {
                "required_phrases": [
                    "장마철 수분 장벽 케어",
                    "세라마이드 앰플",
                    "장벽 크림 10ml 증정",
                ],
                "banned_words": [],
            },
        }

        self.assertEqual("세라마이드 앰플", _brief_product(current))

    def test_concept_difference_point_hides_operational_evidence_note(self) -> None:
        value = _difference_point(
            "identity_and_moment",
            {"signals": ["실제 장마 표현은 집행 직전 최신 단기 자료로 다시 확인해야 한다."]},
        )

        self.assertNotIn("집행 직전", value)
        self.assertIn("지금 루틴에 적용 가능한 선택 이유", value)

    def test_benchmark_cache_refreshes_when_evidence_belongs_to_another_event(self) -> None:
        result = {
            "caseId": "launch-serum",
            "status": "complete",
            "concepts": {
                "marketingEvidenceEventId": "hsgn-summer-tone-care-2026",
                "candidates": [{"marketingSignalIds": ["s1", "s2", "s3"]}],
            },
            "copyPackage": {
                "marketingEvidenceEventId": "hsgn-summer-tone-care-2026",
                "outputs": [{"planningEvidence": {"marketingSignalIds": ["s1"]}}],
            },
            "scorecard": {"criticalErrorCount": 0},
        }
        self.assertTrue(result_needs_refresh(result))

    def test_openai_provider_enforces_per_run_call_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"OPENAI_API_KEY": "test", "OPENAI_MAX_CALLS_PER_EVENT": "2"}):
            run = Path(tmp)
            calls = []

            def transport(payload, headers, timeout):
                calls.append(payload)
                return response_with({"ok": True})

            provider = OpenAIPlanningProvider(run, transport=transport)
            schema = {"type": "object", "additionalProperties": False, "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
            self.assertEqual("ok", provider.execute(role="strategist", instructions="x", input_payload={}, output_schema=schema)["status"])
            self.assertEqual("ok", provider.execute(role="critic", instructions="x", input_payload={}, output_schema=schema)["status"])
            blocked = provider.execute(role="copywriter", instructions="x", input_payload={}, output_schema=schema)
            self.assertEqual("provider_unavailable", blocked["status"])
            self.assertEqual("call_budget_exhausted", blocked["providerExecution"]["status"])
            self.assertEqual(2, len(calls))

    def test_openai_provider_records_usage_latency_and_estimated_cost(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"OPENAI_API_KEY": "test", "OPENAI_INPUT_COST_PER_MILLION": "1", "OPENAI_OUTPUT_COST_PER_MILLION": "2"}):
            provider = OpenAIPlanningProvider(Path(tmp), transport=lambda payload, headers, timeout: {"model": "test", "output_text": '{"ok":true}', "usage": {"input_tokens": 1000, "output_tokens": 500}})
            schema = {"type": "object", "additionalProperties": False, "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
            result = provider.execute(role="strategist", instructions="x", input_payload={}, output_schema=schema)
            self.assertEqual(0.002, result["providerExecution"]["estimatedCostUsd"])
            self.assertIn("latencyMs", result["providerExecution"])

    def test_openai_provider_rejects_structured_json_that_violates_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            provider = OpenAIPlanningProvider(Path(tmp), transport=lambda payload, headers, timeout: {"model": "test", "output_text": '{"wrong":true}'})
            schema = {"type": "object", "additionalProperties": False, "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
            result = provider.execute(role="strategist", instructions="x", input_payload={}, output_schema=schema)
        self.assertEqual("provider_unavailable", result["status"])
        self.assertEqual("provider_error", result["providerExecution"]["status"])

    def test_full_generation_and_repair_flow_stops_at_eight_provider_calls(self) -> None:
        concepts = {"candidates": build_concept_candidates(self.brief)["candidates"]}
        copy_output = {"outputs": [{"deliverableId": "feed", "channelId": "instagram_feed", "purpose": "benchmark", "strategyBasis": "concept_01", "copyJson": '{"firstLine":"세라마이드 앰플","body":"세라마이드 앰플 루틴","cta":"보기"}', "characterCount": 20}]}
        revise = {"status": "revise", "issues": [{"severity": "warning", "id": "weak", "message": "수정", "targetIds": ["concept_01"]}], "rubric": _rubric(3)}
        copy_revise = {"status": "revise", "issues": [{"severity": "warning", "id": "weak", "message": "수정", "targetIds": ["instagram_feed"]}], "rubric": _rubric(3)}
        responses = [concepts, revise, concepts, {"status": "pass", "issues": [], "rubric": _rubric(4)}, copy_output, copy_revise, copy_output, {"status": "pass", "issues": [], "rubric": _rubric(4)}]

        def transport(payload, headers, timeout):
            return response_with(responses.pop(0))

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"OPENAI_API_KEY": "test", "OPENAI_MAX_CALLS_PER_EVENT": "8"}), patch("services.ad_strategy.generation.OpenAIPlanningProvider", side_effect=lambda run_dir: OpenAIPlanningProvider(run_dir, transport=transport)):
            run = Path(tmp)
            generated = generate_concepts(self.brief, run)
            generate_copy(self.brief, generated["candidates"][0], [{"deliverable_id": "feed", "channel_id": "instagram_feed", "purpose": "benchmark"}], run)
            budget = json.loads((run / "02_content_planning" / "provider-budget.json").read_text(encoding="utf-8"))
            blocked = OpenAIPlanningProvider(run, transport=transport).execute(
                role="critic", instructions="x", input_payload={},
                output_schema={"type": "object", "additionalProperties": False, "required": ["ok"], "properties": {"ok": {"type": "boolean"}}},
            )
        self.assertEqual(8, budget["callsUsed"])
        self.assertEqual("call_budget_exhausted", blocked["providerExecution"]["status"])

    def test_missing_openai_key_uses_local_concept_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            result = generate_concepts(self.brief, Path(tmp))
        self.assertEqual("review_pending", result["status"])
        self.assertEqual("local_deterministic", result["providerExecution"][0]["provider"])
        self.assertEqual("ok", result["providerExecution"][0]["status"])

    def test_concept_generation_repairs_only_after_revise_and_stays_within_four_calls(self) -> None:
        draft = build_concept_candidates(self.brief)
        repaired = json.loads(json.dumps(draft))
        repaired["candidates"][0]["name"] = "수정된 전략"
        outputs = [
            draft,
            {"status": "revise", "issues": [{"severity": "warning", "id": "weak", "message": "약함", "targetIds": ["concept_01"]}], "rubric": _rubric(3)},
            repaired,
            {"status": "pass", "issues": [], "rubric": _rubric(4)},
        ]
        fake = _FakeProvider(outputs)
        with tempfile.TemporaryDirectory() as tmp, patch("services.ad_strategy.generation.OpenAIPlanningProvider", return_value=fake):
            result = generate_concepts(self.brief, Path(tmp))
        self.assertEqual(4, len(fake.calls))
        self.assertEqual(["strategist", "critic", "strategist", "critic"], fake.calls)
        self.assertEqual("수정된 전략", result["candidates"][0]["name"])
        self.assertEqual(1, len(result["repairHistory"]))

    def test_copy_generation_repairs_after_revise_and_preserves_call_budget_shape(self) -> None:
        concept = build_concept_candidates(self.brief)["candidates"][0]
        output = {"outputs": [{"deliverableId": "instagram_feed", "channelId": "instagram_feed", "purpose": "benchmark", "strategyBasis": "x", "copyJson": '{"headline":"초안"}', "characterCount": 2}]}
        repaired = {"outputs": [{**output["outputs"][0], "copyJson": '{"headline":"수정본"}', "characterCount": 3}]}
        fake = _FakeProvider([
            output, {"status": "revise", "issues": [{"severity": "warning", "id": "awkward", "message": "어색함", "targetIds": ["instagram_feed"]}], "rubric": _rubric(3)},
            repaired, {"status": "pass", "issues": [], "rubric": _rubric(4)},
        ])
        with tempfile.TemporaryDirectory() as tmp, patch("services.ad_strategy.generation.OpenAIPlanningProvider", return_value=fake):
            package = generate_copy(self.brief, concept, [{"deliverable_id": "instagram_feed", "channel_id": "instagram_feed", "purpose": "benchmark"}], Path(tmp))
        self.assertEqual(["copywriter", "critic", "copywriter", "critic"], fake.calls)
        self.assertEqual("수정본", package["outputs"][0]["copy"]["headline"])
        self.assertEqual(1, len(package["repairHistory"]))

    def test_targeted_repairs_do_not_change_unflagged_concepts_or_channels(self) -> None:
        concepts = build_concept_candidates({**self.brief, "event_id": "case-1", "event_type": "launch"})
        original_second = json.loads(json.dumps(concepts["candidates"][1]))
        repaired_concepts = json.loads(json.dumps(concepts))
        repaired_concepts["candidates"][0]["name"] = "수정 대상"
        repaired_concepts["candidates"][1]["name"] = "바뀌면 안 됨"
        _apply_targeted_concept_repair(concepts, repaired_concepts, [{"targetIds": ["concept_01"]}])
        self.assertEqual("수정 대상", concepts["candidates"][0]["name"])
        self.assertEqual(original_second, concepts["candidates"][1])

        copies = {"outputs": [
            {"channelId": "instagram_feed", "copyJson": '{"body":"기존 피드"}'},
            {"channelId": "blog_thumbnail", "copyJson": '{"headline":"기존 썸네일"}'},
        ]}
        repaired_copies = {"outputs": [
            {"channelId": "instagram_feed", "copyJson": '{"body":"수정 피드"}'},
            {"channelId": "blog_thumbnail", "copyJson": '{"headline":"바뀌면 안 됨"}'},
        ]}
        _apply_targeted_copy_repair(copies, repaired_copies, [{"targetIds": ["instagram_feed"]}])
        self.assertEqual('{"body":"수정 피드"}', copies["outputs"][0]["copyJson"])
        self.assertEqual('{"headline":"기존 썸네일"}', copies["outputs"][1]["copyJson"])

    def test_strategy_review_and_metrics_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            examples_path = Path(tmp) / "examples.json"
            corrections_path = Path(tmp) / "corrections.json"
            examples_path.write_text(json.dumps({"examples": [{"id": "one", "industry": "cosmetics_skincare", "targetInsight": "고객 인사이트", "hookMechanism": "공감", "persuasionSequence": ["공감", "제안"], "ctaType": "보기", "review": {"decision": "unreviewed", "scores": {}, "reasonTags": []}}]}), encoding="utf-8")
            with patch("services.ad_strategy.repository.EXAMPLES_PATH", examples_path), patch("services.ad_strategy.repository.CORRECTIONS_PATH", corrections_path):
                update_example_review("one", {
                    "decision": "selected",
                    "scores": _rubric(5),
                    "reasonTags": ["good_structure"],
                    "reviewNote": "설득 구조가 명확해 생성 예시로 적합합니다.",
                })
                metrics = strategy_quality_metrics()
            self.assertEqual(1, metrics["reviewed"])
            self.assertEqual(1, metrics["decisions"]["selected"])
            self.assertEqual(5, metrics["averageHumanScore"])

    def test_selected_strategy_requires_complete_abstraction_and_average_four(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            examples_path = Path(tmp) / "examples.json"
            examples_path.write_text(json.dumps({"examples": [{"id": "one", "industry": "cosmetics_skincare", "targetInsight": "", "hookMechanism": "공감", "persuasionSequence": ["공감"], "ctaType": "보기", "review": {"decision": "unreviewed", "scores": {}, "reasonTags": []}}]}), encoding="utf-8")
            with patch("services.ad_strategy.repository.EXAMPLES_PATH", examples_path):
                with self.assertRaisesRegex(ValueError, "incomplete"):
                    update_example_review("one", {"decision": "selected", "scores": _rubric(5)})
                with self.assertRaisesRegex(ValueError, "at least 4"):
                    update_example_review("one", {"decision": "selected", "strategy": {"targetInsight": "고객 인사이트"}, "scores": _rubric(3)})
                with self.assertRaisesRegex(ValueError, "reason tag"):
                    update_example_review("one", {
                        "decision": "selected",
                        "strategy": {"targetInsight": "고객 인사이트", "persuasionSequence": ["공감", "제안"]},
                        "scores": _rubric(4),
                    })
                selected = update_example_review("one", {
                    "decision": "selected",
                    "strategy": {"targetInsight": "고객 인사이트", "persuasionSequence": ["공감", "제안"]},
                    "scores": _rubric(4),
                    "reasonTags": ["good_structure"],
                    "reviewNote": "설득 흐름과 타깃 정의가 생성 예시 기준을 충족합니다.",
                })
            self.assertEqual("selected", selected["review"]["decision"])
            self.assertEqual("고객 인사이트", selected["targetInsight"])

    def test_corrections_require_learning_context_and_do_not_cross_brands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corrections_path = Path(tmp) / "corrections.json"
            base = {
                "runId": "run", "eventId": "event", "eventName": "이벤트", "industry": "cosmetics_skincare",
                "channelId": "instagram_feed", "model": "model", "strategyExampleIds": [], "originalCopy": {},
                "editedCopy": {}, "reasonTags": [], "qaResult": {}, "approved": True,
            }
            with patch("services.ad_strategy.repository.CORRECTIONS_PATH", corrections_path):
                with self.assertRaisesRegex(ValueError, "brandName"):
                    append_correction(base)
                append_correction({**base, "brandName": "브랜드 A"})
                append_correction({**base, "runId": "run-b", "brandName": "브랜드 B"})
                records = retrieve_corrections(industry="cosmetics_skincare", brand_name="브랜드 A")
                unbranded_records = retrieve_corrections(industry="cosmetics_skincare", brand_name="")
            self.assertEqual(1, len(records))
            self.assertEqual("브랜드 A", records[0]["brandName"])
            self.assertEqual([], unbranded_records)

    def test_correction_id_is_upserted_instead_of_duplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corrections_path = Path(tmp) / "corrections.json"
            base = {
                "id": "stable-correction",
                "runId": "run-a",
                "eventId": "event-a",
                "eventName": "이벤트",
                "brandName": "브랜드",
                "industry": "cosmetics_skincare",
                "channelId": "instagram_feed",
                "model": "model",
                "strategyExampleIds": [],
                "originalCopy": {"body": "원문"},
                "editedCopy": {"body": "수정문"},
                "reasonTags": ["good_hook"],
                "qaResult": {},
                "approved": False,
            }
            with patch("services.ad_strategy.repository.CORRECTIONS_PATH", corrections_path):
                append_correction(base)
                append_correction({**base, "approved": True})
                saved = json.loads(corrections_path.read_text(encoding="utf-8"))["records"]
        self.assertEqual(1, len(saved))
        self.assertTrue(saved[0]["approved"])
        self.assertIn("updatedAt", saved[0])

    def test_strategy_review_enriches_original_copy_without_persisting_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "references" / "collected-ads.json"
            source.parent.mkdir()
            source.write_text(json.dumps({"items": [{"libraryId": "123", "brand": "브랜드", "copy": "원문 광고", "cta": "구매하기"}]}, ensure_ascii=False), encoding="utf-8")
            examples_path = root / "examples.json"
            examples_path.write_text(json.dumps({"examples": [{"id": "one", "sourceRef": {"libraryId": "123", "sourceFile": "references/collected-ads.json"}}]}), encoding="utf-8")
            with patch("services.ad_strategy.repository.ROOT", root), patch("services.ad_strategy.repository.EXAMPLES_PATH", examples_path):
                reviewed = load_examples_for_review()
            self.assertEqual("원문 광고", reviewed[0]["sourceOriginal"]["copy"])
            self.assertNotIn("sourceOriginal", json.loads(examples_path.read_text(encoding="utf-8"))["examples"][0])

    def test_stage_approval_allows_quality_warnings_after_human_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            stage = run / "02_content_planning"
            stage.mkdir()
            (run / "run-status.json").write_text(json.dumps({"run_id": "x", "event_id": "x", "run_state": "plan_review", "current_stage": "02_content_planning", "stage_status": {"01_event_brief": "approved", "02_content_planning": "review_pending", "03_reference_research": "locked"}}), encoding="utf-8")
            (run / "approvals.json").write_text('{"approvals":[]}', encoding="utf-8")
            (stage / "concept-review.json").write_text('{"status":"approved","selectedConceptId":"concept_01"}', encoding="utf-8")
            (stage / "copy-review.json").write_text('{"status":"approved","approved":true}', encoding="utf-8")
            (stage / "planning-scorecard.json").write_text('{"status":"warning","criticalErrorCount":0,"issues":[{"severity":"warning","id":"weak"}]}', encoding="utf-8")
            with patch("scripts.validate_ad_planning_output.build_planning_output_from_run", return_value={}), patch("scripts.validate_ad_planning_output.validate_planning_output", return_value=[]):
                approve_stage(run, "02_content_planning")
            status = json.loads((run / "run-status.json").read_text(encoding="utf-8"))
            self.assertEqual("approved", status["stage_status"]["02_content_planning"])

    def test_benchmark_review_is_saved_and_external_preference_is_unblinded(self) -> None:
        case = {"id": "case-1", "eventType": "launch", "eventName": "신제품", "target": "고객", "product": "앰플", "offer": ""}
        external = {
            "caseId": "case-1", "status": "complete", "concepts": build_concept_candidates(self.brief),
            "copyPackage": {"outputs": []}, "scorecard": {"criticalErrorCount": 0}, "providerExecution": [{"latencyMs": 10, "estimatedCostUsd": .1}],
        }
        preferred = "A" if blind_order_for("case-1")[0] == "external" else "B"
        with tempfile.TemporaryDirectory() as tmp:
            reviews_path = Path(tmp) / "reviews.json"
            review = save_human_review("case-1", {"scores": _rubric(5), "approved": True, "edited": False, "blindPreferred": preferred}, reviews_path)
            evaluated = evaluate_case(case, review, external)
            report = aggregate([evaluated], {"cases": 1, "averageHumanScore": 4, "unchangedApprovalRate": .5, "blindPreferenceRate": .7})
        self.assertEqual("pass", report["summary"]["status"])
        self.assertEqual(1, report["summary"]["externalGenerated"])
        self.assertEqual(1, report["summary"]["blindPreferenceRate"])
        self.assertEqual(.1, report["summary"]["estimatedCostUsd"])

    def test_benchmark_review_rejects_partial_scores_and_invalid_blind_choice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reviews_path = Path(tmp) / "reviews.json"
            with self.assertRaisesRegex(ValueError, "eight"):
                save_human_review("case-1", {"scores": {"strategyClarity": 5}, "blindPreferred": "A"}, reviews_path)
            save_human_review("case-1", {"scores": _rubric(5), "approved": True, "edited": False, "blindPreferred": ""}, reviews_path)
            with self.assertRaisesRegex(ValueError, "A or B"):
                save_human_review("case-2", {"scores": _rubric(5), "blindPreferred": "Z"}, reviews_path)

    def test_benchmark_requires_human_concept_selection_before_copy_generation(self) -> None:
        case = {"id": "case-1", "eventType": "launch", "eventName": "신제품", "target": "고객", "product": "앰플", "offer": ""}
        concepts = {**build_concept_candidates(self.brief), "status": "review_pending", "providerExecution": []}
        concepts["marketingEvidenceStatus"] = "ready"
        concepts["marketingEvidenceEventId"] = "case-1"
        copy_package = {"status": "review_pending", "outputs": [], "providerExecution": []}
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "external.json"
            with patch("scripts.benchmark_ad_planning.generate_concepts", return_value=concepts), patch("scripts.benchmark_ad_planning.generate_copy", return_value=copy_package) as copy_mock:
                first = run_external_cases({"cases": [case]}, output, provider="openai")
                self.assertEqual("concept_review_pending", first["results"][0]["status"])
                copy_mock.assert_not_called()
                select_external_concept("case-1", concepts["candidates"][1]["conceptId"], output)
                second = run_external_cases({"cases": [case]}, output, provider="openai")
            self.assertEqual("complete", second["results"][0]["status"])
            self.assertEqual(concepts["candidates"][1]["conceptId"], second["results"][0]["selectedConceptId"])
            self.assertEqual("human", second["results"][0]["selectionSource"])
            copy_mock.assert_called_once()

    def test_connection_check_review_is_not_counted_as_final_human_review(self) -> None:
        review = {
            "scores": _rubric(4),
            "approved": True,
            "edited": False,
            "reasonTags": ["connection_test"],
            "conceptSelectionSource": "connection_check_default",
        }

        self.assertFalse(is_final_human_review(review))

    def test_stale_complete_result_returns_to_concept_review(self) -> None:
        case = {"id": "case-1", "eventType": "launch", "eventName": "신제품", "target": "고객", "product": "세럼", "offer": ""}
        stale = {
            "schemaVersion": "1.0.0",
            "results": [{
                "caseId": "case-1",
                "status": "complete",
                "selectedConceptId": "concept_01",
                "selectionSource": "connection_check_default",
                "concepts": {"marketingEvidenceEventId": "other-event", "candidates": []},
                "copyPackage": {"marketingEvidenceEventId": "other-event", "outputs": []},
                "scorecard": {"criticalErrorCount": 0},
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "external.json"
            output.write_text(json.dumps(stale, ensure_ascii=False), encoding="utf-8")

            refreshed = run_external_cases({"cases": [case]}, output, provider="local")

        result = refreshed["results"][0]
        self.assertEqual("evidence_review_required", result["status"])
        self.assertEqual("", result["selectedConceptId"])
        self.assertNotIn("copyPackage", result)

    def test_force_refresh_discards_old_human_selection_after_evidence_change(self) -> None:
        case = {"id": "case-1", "eventType": "launch", "eventName": "신제품", "target": "고객", "product": "세럼", "offer": ""}
        existing = {
            "schemaVersion": "1.0.0",
            "results": [{
                "caseId": "case-1",
                "status": "complete",
                "selectedConceptId": "concept_02",
                "selectionSource": "human",
                "concepts": {"marketingEvidenceEventId": "case-1", "candidates": [{"marketingSignalIds": ["old-1", "old-2", "old-3"]}]},
                "copyPackage": {"marketingEvidenceEventId": "case-1", "outputs": [{"planningEvidence": {"marketingSignalIds": ["old-1"]}}]},
                "scorecard": {"criticalErrorCount": 0},
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "external.json"
            output.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

            refreshed = run_external_cases(
                {"cases": [case]},
                output,
                provider="local",
                force_refresh=True,
            )

        result = refreshed["results"][0]
        self.assertEqual("evidence_review_required", result["status"])
        self.assertEqual("", result["selectedConceptId"])
        self.assertNotIn("copyPackage", result)

    def test_connection_check_can_select_pending_concepts_without_human_review(self) -> None:
        case = {"id": "case-1", "eventType": "launch", "eventName": "신제품", "target": "고객", "product": "앰플", "offer": ""}
        concepts = build_concept_candidates({
            **self.brief,
            "event_id": "case-1",
            "event_type": "launch",
            "offer": {"summary": ""},
        })
        concepts["marketingEvidenceStatus"] = "ready"
        concepts["marketingEvidenceEventId"] = "case-1"
        for index, candidate in enumerate(concepts["candidates"], start=1):
            signal_ids = [f"s{index}-1", f"s{index}-2", f"s{index}-3"]
            candidate["marketingSignalIds"] = signal_ids
            candidate["marketingEvidence"] = {
                "status": "ready",
                "sourceEventId": "case-1",
                "primaryInsight": f"검수된 고객 인사이트 {index}",
                "signalIds": signal_ids,
                "primarySignalIds": [signal_ids[0]],
            }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "external.json"
            with patch("scripts.benchmark_ad_planning.build_concept_candidates", return_value=concepts):
                first = run_external_cases({"cases": [case]}, output, provider="local")
            self.assertEqual("concept_review_pending", first["results"][0]["status"])

            with patch("scripts.benchmark_ad_planning.build_concept_candidates", return_value=concepts):
                second = select_pending_concepts_for_connection_check({"cases": [case]}, output, provider="local")

        result = second["results"][0]
        self.assertEqual("complete", result["status"])
        self.assertEqual("concept_01", result["selectedConceptId"])
        self.assertEqual("connection_check_default", result["selectionSource"])
        self.assertEqual(4, len(result["copyPackage"]["outputs"]))
        self.assertNotIn("humanReview", result)

    def test_local_generation_blocks_concept_selection_until_event_evidence_is_ready(self) -> None:
        case = {
            "id": "case-without-evidence",
            "eventType": "launch",
            "eventName": "근거 미검수 신제품",
            "target": "고객",
            "product": "세럼",
            "offer": "",
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "external.json"

            generated = run_external_cases({"cases": [case]}, output, provider="local")

            result = generated["results"][0]
            self.assertEqual("evidence_review_required", result["status"])
            self.assertEqual("", result["selectedConceptId"])
            with self.assertRaisesRegex(ValueError, "not waiting for concept selection"):
                select_external_concept(case["id"], "concept_01", output)

    def test_local_generation_blocks_event_type_mismatch_from_concept_selection(self) -> None:
        case = {
            "id": "season-case",
            "eventType": "seasonal",
            "eventName": "장마철 루틴",
            "target": "냉방 환경 고객",
            "product": "세라마이드 앰플",
            "offer": "크림 증정",
        }
        concepts = build_concept_candidates({**self.brief, "event_id": "season-case"})
        concepts["eventType"] = "promotion"
        concepts["marketingEvidenceStatus"] = "ready"
        concepts["marketingEvidenceEventId"] = "season-case"
        for candidate in concepts["candidates"]:
            evidence = candidate.setdefault("marketingEvidence", {})
            evidence["signalIds"] = ["s1", "s2", "s3"]
            evidence["primarySignalIds"] = ["s1"]
            candidate["marketingSignalIds"] = ["s1", "s2", "s3"]

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "external.json"
            with patch("scripts.benchmark_ad_planning.build_concept_candidates", return_value=concepts):
                generated = run_external_cases({"cases": [case]}, output, provider="local")

        result = generated["results"][0]
        self.assertEqual("quality_repair_required", result["status"])
        self.assertEqual("fail", result["concepts"]["criticReview"]["status"])
        self.assertIn(
            "event_type_mismatch",
            {item["id"] for item in result["concepts"]["criticReview"]["issues"]},
        )

    def test_local_critic_does_not_rubber_stamp_generic_concepts(self) -> None:
        brief = {
            **self.brief,
            "event_id": "season-case",
            "event_type": "seasonal",
            "offer": {"summary": "앰플 구매 시 크림 증정"},
        }
        concepts = build_concept_candidates(brief)
        concepts["eventType"] = "seasonal"
        concepts["marketingEvidenceStatus"] = "ready"
        concepts["marketingEvidenceEventId"] = "season-case"
        for index, candidate in enumerate(concepts["candidates"], start=1):
            candidate["targetInsight"] = "피부 고민 고객"
            candidate["corePromise"] = f"좋은 선택 {index}"
            candidate["cta"] = "자세히 보기"
            candidate["marketingSignalIds"] = [f"s{index}-1", f"s{index}-2", f"s{index}-3"]
            candidate["marketingEvidence"] = {
                "status": "ready",
                "sourceEventId": "season-case",
                "primaryInsight": "",
                "signalIds": candidate["marketingSignalIds"],
                "primarySignalIds": [f"s{index}-1"],
            }

        review = _local_concept_only_critic_review(brief, concepts)

        self.assertEqual("revise", review["status"])
        self.assertLess(review["rubric"]["targetEmpathy"], 4)
        self.assertLess(review["rubric"]["productConnection"], 4)
        self.assertLess(review["rubric"]["actionability"], 4)
        issue_ids = {item["id"] for item in review["issues"]}
        self.assertIn("weak_target_insight", issue_ids)
        self.assertIn("weak_product_connection", issue_ids)
        self.assertIn("weak_concept_cta", issue_ids)
        concepts["criticReview"] = review
        self.assertEqual("concept_review_pending", _concept_result_status(concepts, "season-case"))

    def test_local_copy_critic_does_not_rubber_stamp_weak_copy(self) -> None:
        repeated = "지금 자세히 확인해보세요."
        weak_copy = {"firstLine": repeated, "body": repeated, "cta": repeated}
        concepts = {
            "candidates": [{"conceptId": "concept_01"}],
            "criticReview": {"rubric": _rubric(4)},
        }
        package = {
            "conceptId": "concept_01",
            "marketingEvidenceStatus": "ready",
            "marketingEvidenceEventId": "x",
            "outputs": [{
                "deliverableId": "feed",
                "channelId": "instagram_feed",
                "purpose": "전환",
                "strategyBasis": "일반적인 확인 유도",
                "copy": weak_copy,
                "characterCount": copy_character_count(weak_copy),
                "planningEvidence": {
                    "target": "민감한 피부 고객",
                    "marketingSignalIds": ["signal-1"],
                },
            }],
        }

        review = review_local_copy(self.brief, concepts, package)

        self.assertEqual("revise", review["status"])
        self.assertLess(review["rubric"]["productConnection"], 4)
        self.assertLess(review["rubric"]["distinctiveness"], 4)
        self.assertLess(review["rubric"]["koreanCopyQuality"], 4)
        issue_ids = {item["id"] for item in review["issues"]}
        self.assertIn("weak_product_connection", issue_ids)
        self.assertIn("repetitive_copy", issue_ids)

    def test_fixed_cosmetics_benchmark_has_twenty_cases_and_zero_baseline_critical_errors(self) -> None:
        dataset = json.loads((ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json").read_text(encoding="utf-8"))
        evaluated = [evaluate_case(case, {}, {}) for case in dataset["cases"]]
        self.assertEqual(20, len(evaluated))
        self.assertEqual({"seasonal", "promotion", "launch", "education", "branding"}, {case["eventType"] for case in evaluated})
        self.assertEqual(0, sum(case["baseline"]["scorecard"]["criticalErrorCount"] for case in evaluated))

    def test_goal_audit_does_not_treat_zero_unrun_cases_as_zero_critical_success(self) -> None:
        incomplete = build_audit(
            {"summary": {"cases": 20, "externalGenerated": 0, "reviewed": 0, "criticalErrors": 0}},
            {"decisions": {"selected": 0, "shortlist": 0}},
        )
        complete = build_audit(
            {"summary": {"cases": 20, "externalGenerated": 20, "reviewed": 20, "criticalErrors": 0, "averageHumanScore": 4.2, "unchangedApprovalRate": .5, "blindPreferenceRate": .7}},
            {"decisions": {"selected": 20, "shortlist": 10}},
        )
        critical_check = next(item for item in incomplete["checks"] if item["id"] == "critical_errors_zero_on_all_cases")
        self.assertFalse(critical_check["passed"])
        self.assertEqual("incomplete", incomplete["status"])
        self.assertEqual("pass", complete["status"])


def _rubric(value: int) -> dict[str, int]:
    return {key: value for key in ["strategyClarity", "targetEmpathy", "productConnection", "distinctiveness", "channelFit", "koreanCopyQuality", "brandFit", "actionability"]}


class _FakeProvider:
    def __init__(self, outputs: list[dict]) -> None:
        self.outputs = list(outputs)
        self.calls: list[str] = []

    def execute(self, *, role: str, instructions: str, input_payload: dict, output_schema: dict) -> dict:
        self.calls.append(role)
        output = self.outputs.pop(0)
        return {
            "status": "ok", "output": output,
            "providerExecution": {"status": "ok", "provider": "fake", "model": "fake", "role": role, "callsUsed": len(self.calls), "maxCalls": 8},
        }


if __name__ == "__main__":
    unittest.main()
