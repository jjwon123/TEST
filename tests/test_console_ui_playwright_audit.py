from __future__ import annotations

import unittest
from pathlib import Path

from scripts.audit_console_ui_playwright import evaluate_console_snapshot
from scripts.verify_console_journey_harness import console_handoff_checks, verify_browser_concept_to_copy_transition


class ConsoleUiPlaywrightAuditTests(unittest.TestCase):
    def test_concept_selection_opens_copy_review_mission(self) -> None:
        source = Path("ui/console/app.js").read_text(encoding="utf-8")
        handler = source.split("async function selectPlanningBenchmarkConcept", 1)[1].split("async function runPlanningPilot", 1)[0]

        self.assertIn('state.missionMode = "copy_review"', handler)

    def test_copy_review_hands_off_to_reference_selection_when_no_run_is_linked(self) -> None:
        source = Path("ui/console/app.js").read_text(encoding="utf-8")
        handler = source.split("async function reviewPlanningBenchmark", 1)[1].split("function collectBenchmarkCopyEdits", 1)[0]

        self.assertIn('"/api/planning-benchmark/production-handoff"', handler)
        self.assertIn('setView("references")', handler)

    def test_new_copy_approval_defaults_to_the_server_approval_threshold(self) -> None:
        source = Path("ui/console/app.js").read_text(encoding="utf-8")
        form = source.split("function renderPlanningHumanReviewForm", 1)[1].split("function renderPlanningBenchmark", 1)[0]

        self.assertIn("approvalDefaultScores", form)
        self.assertIn("[key, 4]", form)
        self.assertIn("평균 4점 이상", form)

    def test_workflow_completion_hook_accepts_server_done_status(self) -> None:
        source = Path("ui/console/app.js").read_text(encoding="utf-8")
        hook = source.split("async function waitForWorkflowJob", 1)[1].split("async function updateCandidateDecision", 1)[0]

        self.assertIn('["done", "completed"].includes(job?.status)', hook)

    def test_console_handoff_contracts_are_all_present(self) -> None:
        self.assertTrue(all(console_handoff_checks().values()))

    def test_browser_click_moves_concept_selection_to_copy_review(self) -> None:
        result = verify_browser_concept_to_copy_transition()

        self.assertTrue(result.get("pass"), result)
        self.assertGreater(result.get("copyCards", 0), 0)

    def test_clean_console_snapshot_passes(self) -> None:
        report = evaluate_console_snapshot(snapshot("광고 기획 검수 데스크\n마케팅 신호 검수", planning_cases=5))

        self.assertEqual("pass", report["status"])
        self.assertTrue(report["checks"]["developerTermsHidden"]["pass"])
        self.assertTrue(report["checks"]["noHorizontalOverflow"]["pass"])

    def test_developer_terms_and_raw_json_fail(self) -> None:
        report = evaluate_console_snapshot(snapshot('provider meta_strategy_123 {"copy":"bad"}', planning_cases=1))

        self.assertEqual("fail", report["status"])
        self.assertIn("developerTermsHidden", report["errors"])
        self.assertIn("rawJsonHidden", report["errors"])

    def test_ab_and_overflow_fail(self) -> None:
        data = snapshot("안 A\n안 B", planning_cases=1)
        data["metrics"]["overflowing"] = [{"tag": "article", "text": "long card"}]

        report = evaluate_console_snapshot(data)

        self.assertEqual("fail", report["status"])
        self.assertIn("abComparisonHidden", report["errors"])
        self.assertIn("noHorizontalOverflow", report["errors"])

    def test_english_pipeline_and_next_action_labels_fail(self) -> None:
        report = evaluate_console_snapshot(snapshot(
            "광고 기획 검수 데스크\nBrief\nContinue Plan\nGenerate and select image candidates",
            planning_cases=1,
        ))

        self.assertEqual("fail", report["status"])
        self.assertIn("operationLabelsLocalized", report["errors"])
        self.assertEqual(
            ["Brief", "Continue Plan", "Generate and select image candidates"],
            report["checks"]["operationLabelsLocalized"]["terms"],
        )

    def test_signal_cards_require_quality_summary(self) -> None:
        data = snapshot("마케팅 신호 검수", signal_cards=3, signal_quality_summaries=0)

        report = evaluate_console_snapshot(data)

        self.assertEqual("fail", report["status"])
        self.assertIn("signalQualitySummaryVisible", report["errors"])

    def test_signal_cards_require_repair_fields(self) -> None:
        data = snapshot("마케팅 신호 검수", signal_cards=3, signal_repair_fields=0)

        report = evaluate_console_snapshot(data)

        self.assertEqual("fail", report["status"])
        self.assertIn("signalRepairFieldsVisible", report["errors"])

    def test_copy_cards_require_edit_fields_and_review_form(self) -> None:
        data = snapshot(
            "광고 기획 검수 데스크",
            planning_cases=1,
            copy_cards=4,
            benchmark_copy_edit_fields=0,
            benchmark_review_forms=0,
        )

        report = evaluate_console_snapshot(data)

        self.assertEqual("fail", report["status"])
        self.assertIn("benchmarkCopyEditingVisible", report["errors"])
        self.assertIn("benchmarkReviewFormVisible", report["errors"])

    def test_evidence_blocked_cards_hide_editing_and_review(self) -> None:
        data = snapshot(
            "근거 준비 필요",
            planning_cases=3,
            copy_cards=12,
            benchmark_copy_edit_fields=0,
            benchmark_review_forms=0,
            event_evidence_blocked_cards=3,
            evidence_queue_cards=5,
            evidence_queue_summaries=1,
            evidence_focus_actions=5,
        )

        report = evaluate_console_snapshot(data)

        self.assertEqual("pass", report["status"])

    def test_hidden_copy_cards_outside_planning_cases_do_not_fail_current_desk(self) -> None:
        data = snapshot(
            "광고 기획 검수 데스크",
            planning_cases=4,
            copy_cards=4,
            benchmark_copy_edit_fields=0,
            benchmark_review_forms=0,
            event_evidence_blocked_cards=3,
            planning_case_details=[
                {"caseId": "ready", "copyCards": 0, "editFields": 0, "reviewForms": 0, "evidenceBlocked": False, "qualityBlocked": False, "qualitySummaries": 1, "conceptSelectButtons": 3},
                {"caseId": "blocked-1", "copyCards": 0, "editFields": 0, "reviewForms": 0, "evidenceBlocked": True, "qualityBlocked": False},
                {"caseId": "blocked-2", "copyCards": 0, "editFields": 0, "reviewForms": 0, "evidenceBlocked": True, "qualityBlocked": False},
                {"caseId": "blocked-3", "copyCards": 0, "editFields": 0, "reviewForms": 0, "evidenceBlocked": True, "qualityBlocked": False},
            ],
        )

        report = evaluate_console_snapshot(data)

        self.assertEqual("pass", report["status"])

    def test_ready_concept_case_requires_quality_summary_and_selection_action(self) -> None:
        data = snapshot(
            "광고 기획 검수 데스크",
            planning_cases=1,
            copy_cards=0,
            planning_case_details=[{
                "caseId": "ready",
                "copyCards": 0,
                "editFields": 0,
                "reviewForms": 0,
                "evidenceBlocked": False,
                "qualityBlocked": False,
                "qualitySummaries": 0,
                "conceptSelectButtons": 0,
            }],
        )

        report = evaluate_console_snapshot(data)

        self.assertEqual("fail", report["status"])
        self.assertIn("conceptQualitySummaryVisible", report["errors"])
        self.assertIn("conceptSelectionActionVisible", report["errors"])

    def test_blocked_planning_requires_event_evidence_queue(self) -> None:
        data = snapshot(
            "근거 준비 필요",
            planning_cases=3,
            copy_cards=12,
            benchmark_copy_edit_fields=0,
            benchmark_review_forms=0,
            event_evidence_blocked_cards=3,
            evidence_queue_cards=0,
            evidence_queue_summaries=0,
            evidence_focus_actions=0,
        )

        report = evaluate_console_snapshot(data)

        self.assertEqual("fail", report["status"])
        self.assertIn("eventEvidenceQueueVisible", report["errors"])

    def test_strategy_cards_require_recommendation_action(self) -> None:
        data = snapshot(
            "고급 정보 데이터 검수",
            signal_cards=1,
            strategy_review_cards=3,
            strategy_recommendation_actions=0,
        )

        report = evaluate_console_snapshot(data)

        self.assertEqual("fail", report["status"])
        self.assertIn("strategyRecommendationActionVisible", report["errors"])

    def test_copy_correction_audit_requires_action_and_summary(self) -> None:
        data = snapshot(
            "광고 기획 검수 데스크",
            planning_cases=1,
            copy_correction_audit_buttons=0,
            copy_correction_audit_summaries=0,
        )

        report = evaluate_console_snapshot(data)

        self.assertEqual("fail", report["status"])
        self.assertIn("copyCorrectionAuditActionVisible", report["errors"])
        self.assertIn("copyCorrectionAuditSummaryVisible", report["errors"])

    def test_planning_review_requires_entry_action(self) -> None:
        data = snapshot("광고 기획 검수 데스크", planning_cases=1, planning_review_entry_buttons=0)

        report = evaluate_console_snapshot(data)

        self.assertEqual("fail", report["status"])
        self.assertIn("planningReviewEntryVisible", report["errors"])

    def test_planning_desk_requires_one_primary_action(self) -> None:
        data = snapshot("광고 기획 검수 데스크", planning_cases=1, primary_planning_actions=0)

        report = evaluate_console_snapshot(data)

        self.assertEqual("fail", report["status"])
        self.assertIn("primaryPlanningActionVisible", report["errors"])


def snapshot(
    body: str,
    *,
    planning_cases: int = 0,
    signal_cards: int = 0,
    signal_quality_summaries: int = 1,
    signal_repair_fields: int = 1,
    marketing_loop_audit_buttons: int = 1,
    marketing_loop_audit_summaries: int = 1,
    copy_correction_audit_buttons: int = 1,
    copy_correction_audit_summaries: int = 1,
    copy_cards: int | None = None,
    benchmark_copy_edit_fields: int = 1,
    benchmark_review_forms: int = 1,
    strategy_review_cards: int = 0,
    strategy_recommendation_actions: int = 0,
    strategy_review_entry_buttons: int = 1,
    planning_review_entry_buttons: int = 1,
    primary_planning_actions: int = 1,
    review_session_progress: int = 1,
    event_evidence_metrics: int = 1,
    event_evidence_blocked_cards: int = 0,
    evidence_queue_cards: int = 5,
    evidence_queue_summaries: int = 1,
    evidence_focus_actions: int = 5,
    planning_case_details: list[dict] | None = None,
) -> dict:
    return {
        "createdAt": "2026-06-18T00:00:00+00:00",
        "url": "http://127.0.0.1:5177/",
        "viewport": {"width": 1280, "height": 1100},
        "bodyText": body,
        "metrics": {
            "viewportWidth": 1280,
            "bodyScrollWidth": 1280,
            "documentScrollWidth": 1280,
            "planningCases": planning_cases,
            "conceptCards": 15 if planning_cases else 0,
            "copyCards": (12 if planning_cases else 0) if copy_cards is None else copy_cards,
            "benchmarkCopyEditFields": benchmark_copy_edit_fields,
            "benchmarkReviewForms": benchmark_review_forms,
            "strategyReviewCards": strategy_review_cards,
            "strategyRecommendationActions": strategy_recommendation_actions,
            "strategyReviewEntryButtons": strategy_review_entry_buttons,
            "planningReviewEntryButtons": planning_review_entry_buttons,
            "primaryPlanningActions": primary_planning_actions,
            "reviewSessionProgress": review_session_progress,
            "eventEvidenceMetrics": event_evidence_metrics,
            "eventEvidenceBlockedCards": event_evidence_blocked_cards,
            "evidenceQueueCards": evidence_queue_cards,
            "evidenceQueueSummaries": evidence_queue_summaries,
            "evidenceFocusActions": evidence_focus_actions,
            "signalCards": signal_cards,
            "signalJobButtons": 4,
            "signalQualitySummaries": signal_quality_summaries,
            "signalRepairFields": signal_repair_fields,
            "signalRecommendations": 0,
            "marketingLoopAuditButtons": marketing_loop_audit_buttons,
            "marketingLoopAuditSummaries": marketing_loop_audit_summaries,
            "copyCorrectionAuditButtons": copy_correction_audit_buttons,
            "copyCorrectionAuditSummaries": copy_correction_audit_summaries,
            "planningCaseDetails": planning_case_details or [],
            "overflowing": [],
        },
    }


if __name__ == "__main__":
    unittest.main()
