from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.console_server import (
    add_product_proof_candidate,
    build_marketing_insight_brief,
    focus_marketing_signals,
    run_cosmetics_evidence_source_audit_job,
    marketing_signal_packet,
    repair_marketing_signal,
    review_marketing_signal,
    review_marketing_signals_batch,
    refresh_planning_for_ready_evidence,
    run_marketing_signal_job,
)


class MarketingIntelligenceConsoleTests(unittest.TestCase):
    def test_ready_evidence_builds_brief_and_refreshes_only_focused_case(self) -> None:
        queue = {
            "cases": [{
                "eventId": "pilot",
                "status": "ready",
                "requirements": {"minimumSelectedSignals": 3},
            }]
        }
        dataset = {
            "cases": [{
                "id": "pilot",
                "eventName": "파일럿",
                "eventType": "seasonal",
                "target": "고객",
                "product": "앰플",
                "offer": "",
            }]
        }
        refreshed_result = {
            "results": [{
                "caseId": "pilot",
                "status": "concept_review_pending",
                "concepts": {"candidates": [{}, {}, {}]},
            }]
        }
        with patch(
            "scripts.console_server.build_and_save_insight_brief",
            return_value={"status": "ready", "eventId": "pilot"},
        ) as build, patch(
            "scripts.console_server.read_json",
            return_value=dataset,
        ), patch(
            "scripts.console_server.run_external_cases",
            return_value=refreshed_result,
        ) as run, patch(
            "scripts.console_server.refresh_planning_benchmark",
            return_value={"summary": {"candidateGenerated": 1}},
        ), patch(
            "scripts.console_server.ad_planning_review_packet",
            return_value={"summary": {"pilotCandidateReady": 1}},
        ):
            result = refresh_planning_for_ready_evidence(
                event_id="pilot",
                topic="pilot_topic",
                evidence_queue=queue,
            )

        build.assert_called_once_with(
            event_id="pilot",
            industry="cosmetics_skincare",
            topic="pilot_topic",
            minimum_selected=3,
        )
        self.assertTrue(run.call_args.kwargs["force_refresh"])
        self.assertEqual(["pilot"], [item["id"] for item in run.call_args.args[0]["cases"]])
        self.assertEqual("concept_review_pending", result["status"])

    def test_evidence_regression_invalidates_existing_copy(self) -> None:
        queue = {
            "cases": [{
                "eventId": "pilot",
                "status": "needs_review",
                "requirements": {"minimumSelectedSignals": 3},
            }]
        }
        with patch(
            "scripts.console_server.invalidate_planning_for_evidence",
            return_value=True,
        ) as invalidate, patch(
            "scripts.console_server.refresh_planning_benchmark",
            return_value={"summary": {"externalGenerated": 0}},
        ), patch(
            "scripts.console_server.ad_planning_review_packet",
            return_value={"summary": {"pilotHumanReviewed": 0}},
        ):
            result = refresh_planning_for_ready_evidence(
                event_id="pilot",
                topic="pilot_topic",
                evidence_queue=queue,
            )

        invalidate.assert_called_once_with("pilot", evidence_status="needs_review")
        self.assertEqual("evidence_not_ready", result["status"])
        self.assertTrue(result["planningInvalidated"])
    def test_add_product_proof_returns_focused_review_queue(self) -> None:
        created = {"signal": signal("proof-one", "unreviewed", "proof"), "repository": {"added": 1}}
        with patch(
            "scripts.console_server.create_product_proof_candidate",
            return_value=created,
        ), patch(
            "scripts.console_server.marketing_signal_packet",
            return_value={"reviewQueue": [created["signal"]]},
        ) as packet, patch(
            "scripts.console_server.marketing_evidence_queue",
            return_value={"summary": {"needsReview": 5}},
        ):
            result = add_product_proof_candidate({
                "eventId": "launch-serum",
                "topic": "elasticity_serum_launch",
            })

        packet.assert_called_once_with(
            event_id="launch-serum",
            topic="elasticity_serum_launch",
            limit=60,
        )
        self.assertTrue(result["ok"])
        self.assertEqual("proof-one", result["signal"]["id"])

    def test_packet_prioritizes_unreviewed_signals(self) -> None:
        signals = [
            signal("selected-one", "selected", "desire"),
            signal("waiting-one", "unreviewed", "pain"),
            signal("waiting-two", "unreviewed", "timing"),
        ]
        with patch("scripts.console_server.load_signals", return_value=signals):
            packet = marketing_signal_packet(limit=2)

        self.assertEqual(2, len(packet["signals"]))
        self.assertEqual(["waiting-one", "waiting-two"], [item["id"] for item in packet["reviewQueue"]])
        self.assertEqual(3, packet["metrics"]["total"])
        self.assertEqual(2, packet["metrics"]["decisions"]["unreviewed"])
        self.assertEqual("보조 후보", packet["reviewQueue"][0]["reviewRecommendation"]["label"])
        self.assertEqual("shortlist", packet["reviewQueue"][0]["reviewRecommendation"]["suggestedDecision"])
        self.assertTrue(packet["reviewQueue"][0]["reviewRecommendation"]["limitations"])
        self.assertGreaterEqual(packet["reviewQueue"][0]["reviewRecommendation"]["score"], packet["reviewQueue"][1]["reviewRecommendation"]["score"])

    def test_packet_recommends_high_score_signals_first(self) -> None:
        low = signal("low", "unreviewed", "channel_pattern")
        low["strength"] = 2
        high = signal("high", "unreviewed", "pain")
        high["strength"] = 5
        high["confidence"] = 3
        with patch("scripts.console_server.load_signals", return_value=[low, high]):
            packet = marketing_signal_packet(limit=2)

        self.assertEqual(["high", "low"], [item["id"] for item in packet["reviewQueue"]])
        self.assertIn("타깃", packet["reviewQueue"][0]["reviewRecommendation"]["reasons"][0])

    def test_signal_recommendation_surfaces_source_limitations(self) -> None:
        old_study = signal("old-study", "unreviewed", "desire")
        old_study.update({
            "sourceType": "public_web",
            "sourceRef": {
                "sourceName": "Journal of Consumer Psychology",
                "url": "https://example.test/study",
                "publishedAt": "2004-01-01",
                "methodology": "두 개의 소비자 실험",
            },
            "strength": 3,
            "freshness": 2,
            "confidence": 4,
        })
        with patch("scripts.console_server.load_signals", return_value=[old_study]):
            packet = marketing_signal_packet(limit=1)

        recommendation = packet["reviewQueue"][0]["reviewRecommendation"]
        self.assertIn("10년 이상", recommendation["limitations"][0])
        self.assertIn(recommendation["suggestedDecision"], {"selected", "shortlist"})

    def test_peer_reviewed_pmc_channel_study_can_be_selected_with_caution(self) -> None:
        study = signal("pmc-study", "unreviewed", "channel_pattern")
        study.update({
            "sourceType": "public_web",
            "sourceRef": {
                "sourceName": "PMC dermatology social media study",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/example/",
                "publishedAt": "2025-11-01",
                "methodology": "피부 정보 이용에 대한 단면 조사",
            },
            "strength": 4,
            "freshness": 4,
            "confidence": 4,
        })
        with patch("scripts.console_server.load_signals", return_value=[study]):
            recommendation = marketing_signal_packet(limit=1)["reviewQueue"][0]["reviewRecommendation"]

        self.assertEqual("selected", recommendation["suggestedDecision"])
        self.assertTrue(any("단면 조사" in item for item in recommendation["limitations"]))

    def test_packet_can_focus_one_event_topic(self) -> None:
        matching = signal("matching", "unreviewed", "pain")
        matching["topic"] = "pilot_topic"
        other = signal("other", "unreviewed", "timing")
        other["topic"] = "other_topic"
        with patch("scripts.console_server.load_signals", return_value=[matching, other]):
            packet = marketing_signal_packet(limit=5, event_id="pilot", topic="pilot_topic")

        self.assertEqual(["matching"], [item["id"] for item in packet["reviewQueue"]])
        self.assertEqual(1, packet["scope"]["matched"])
        self.assertEqual(1, packet["scope"]["decisions"]["unreviewed"])

    def test_focus_endpoint_returns_scoped_packet_and_queue(self) -> None:
        with patch(
            "scripts.console_server.marketing_signal_packet",
            return_value={"signals": [], "scope": {"eventId": "pilot", "matched": 0}},
        ) as packet, patch(
            "scripts.console_server.marketing_evidence_queue",
            return_value={"summary": {"total": 20}},
        ):
            result = focus_marketing_signals({"eventId": "pilot", "topic": "pilot_topic"})

        packet.assert_called_once_with(limit=24, event_id="pilot", topic="pilot_topic")
        self.assertTrue(result["ok"])
        self.assertEqual(20, result["evidenceQueue"]["summary"]["total"])

    def test_review_signal_returns_updated_packet(self) -> None:
        updated = signal("waiting-one", "selected", "pain")
        with patch("scripts.console_server.update_signal_review", return_value=updated) as update, patch(
            "scripts.console_server.marketing_signal_packet",
            return_value={"signals": [updated], "metrics": {"total": 1}, "reviewQueue": []},
        ):
            result = review_marketing_signal({
                "signalId": "waiting-one",
                "decision": "selected",
                "reasonTags": ["useful_target"],
                "reviewNote": "쓸만한 타깃 가설",
            })

        update.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual("selected", result["signal"]["review"]["decision"])
        self.assertEqual(1, result["marketingSignals"]["metrics"]["total"])

    def test_batch_review_requires_confirmation_and_saves_scoped_signals(self) -> None:
        waiting = signal("waiting-one", "unreviewed", "pain")
        waiting["topic"] = "pilot_topic"
        updated = {**waiting, "review": {"decision": "selected", "reasonTags": ["useful_target"], "reviewNote": "확인"}}
        payload = {
            "humanConfirmed": True,
            "eventId": "pilot",
            "topic": "pilot_topic",
            "reviews": [{
                "signalId": "waiting-one",
                "decision": "selected",
                "reasonTags": ["useful_target"],
                "reviewNote": "공개 출처와 관찰 요약을 확인한 뒤 고객 문제 근거로 선택했습니다.",
            }],
        }
        with patch("scripts.console_server.load_signals", return_value=[waiting]), patch(
            "scripts.console_server.update_signal_reviews",
            return_value=[updated],
        ) as save, patch(
            "scripts.console_server.marketing_signal_packet",
            return_value={"reviewQueue": [updated]},
        ), patch(
            "scripts.console_server.marketing_evidence_queue",
            return_value={"summary": {"needsReview": 1}},
        ):
            result = review_marketing_signals_batch(payload)

        save.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual("selected", result["signals"][0]["review"]["decision"])

    def test_batch_review_rejects_missing_confirmation_or_cross_event_signal(self) -> None:
        with self.assertRaises(ValueError):
            review_marketing_signals_batch({
                "humanConfirmed": False,
                "eventId": "pilot",
                "reviews": [{"signalId": "waiting-one"}],
            })
        waiting = signal("waiting-one", "unreviewed", "pain")
        waiting["topic"] = "other_topic"
        with patch("scripts.console_server.load_signals", return_value=[waiting]):
            with self.assertRaises(ValueError):
                review_marketing_signals_batch({
                    "humanConfirmed": True,
                    "eventId": "pilot",
                    "topic": "pilot_topic",
                    "reviews": [{
                        "signalId": "waiting-one",
                        "decision": "selected",
                        "reasonTags": ["useful_target"],
                        "reviewNote": "다른 이벤트 신호라 저장되면 안 되는 검수 메모입니다.",
                    }],
                })

    def test_repair_signal_returns_updated_packet(self) -> None:
        updated = signal("waiting-one", "shortlist", "pain")
        updated["normalizedInsight"] = "정제된 기획 인사이트"
        with patch("scripts.console_server.update_signal_content", return_value=updated) as repair, patch(
            "scripts.console_server.marketing_signal_packet",
            return_value={"signals": [updated], "metrics": {"total": 1}, "reviewQueue": []},
        ):
            result = repair_marketing_signal({
                "signalId": "waiting-one",
                "signalText": "정제된 관찰 요약",
                "targetSegment": "정제된 타깃",
                "normalizedInsight": "정제된 기획 인사이트",
            })

        repair.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual("정제된 기획 인사이트", result["signal"]["normalizedInsight"])
        self.assertEqual(1, result["marketingSignals"]["metrics"]["total"])

    def test_build_insight_brief_returns_marketing_packet(self) -> None:
        ready = {"status": "needs_signal_review", "selectedSignalCount": 0}
        with patch("scripts.console_server.build_and_save_insight_brief", return_value=ready) as build, patch(
            "scripts.console_server.marketing_signal_packet",
            return_value={"signals": [], "metrics": {"total": 0}, "reviewQueue": [], "insightBrief": ready},
        ):
            result = build_marketing_insight_brief({"minimumSelected": 3})

        build.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual("needs_signal_review", result["insightBrief"]["status"])
        self.assertEqual(0, result["marketingSignals"]["metrics"]["total"])

    def test_console_job_starts_random_signal_collection(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "job", "status": "running"}) as start_mock:
            result = run_marketing_signal_job({"mode": "random_seed", "count": 50, "topic": "daily_random_seed"})

        self.assertEqual("running", result["status"])
        command = start_mock.call_args.args[0]
        self.assertIn("scripts/collect_marketing_signals.py", command)
        self.assertIn("--random-seed", command)
        self.assertIn("--export-review", command)
        self.assertIn("--count", command)
        self.assertIn("50", command)

    def test_console_job_starts_marketing_signal_csv_import_modes(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "dry", "status": "running"}) as start_mock:
            run_marketing_signal_job({"mode": "import_dry_run"})
        self.assertEqual(["--import-review"], start_mock.call_args.args[0][-1:])

        with patch("scripts.console_server.start_process", return_value={"job_id": "apply", "status": "running"}) as start_mock:
            run_marketing_signal_job({"mode": "import_apply"})
        self.assertEqual(["--import-review", "--apply"], start_mock.call_args.args[0][-2:])

    def test_console_job_starts_public_snapshot_import(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "public", "status": "running"}) as start_mock:
            result = run_marketing_signal_job({
                "mode": "public_snapshot",
                "snapshot": ".tmp/public-signals/hsgn.json",
                "topic": "hsgn_summer_tone_care",
            })

        command = start_mock.call_args.args[0]
        self.assertEqual("running", result["status"])
        self.assertIn("--public-snapshot", command)
        self.assertIn(".tmp/public-signals/hsgn.json", command)
        self.assertIn("--export-review", command)

    def test_console_job_starts_public_url_capture(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "capture", "status": "running"}) as start_mock:
            result = run_marketing_signal_job({
                "mode": "public_capture",
                "url": "https://example.test/hsgn",
                "sourceKind": "brand_site",
                "topic": "hsgn_summer_tone_care",
            })

        command = start_mock.call_args.args[0]
        self.assertEqual("running", result["status"])
        self.assertIn("--capture-url", command)
        self.assertIn("https://example.test/hsgn", command)
        self.assertIn("--source-kind", command)
        self.assertIn("brand_site", command)
        self.assertNotIn("--event-id", command)

    def test_console_public_capture_binds_event_id(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "capture", "status": "running"}) as start_mock:
            run_marketing_signal_job({
                "mode": "public_capture",
                "url": "https://example.test/product",
                "sourceKind": "brand_site",
                "topic": "elasticity_serum_launch",
                "eventId": "launch-serum",
            })

        command = start_mock.call_args.args[0]
        self.assertIn("--event-id", command)
        self.assertIn("launch-serum", command)

    def test_console_job_starts_public_url_batch_capture(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "capture-batch", "status": "running"}) as start_mock:
            result = run_marketing_signal_job({
                "mode": "public_capture",
                "urls": ["https://example.test/one", "https://example.test/two"],
                "sourceKind": "public_web",
                "topic": "hsgn_summer_tone_care",
            })

        command = start_mock.call_args.args[0]
        self.assertEqual("running", result["status"])
        self.assertEqual(2, command.count("--capture-url"))
        self.assertIn("https://example.test/one", command)
        self.assertIn("https://example.test/two", command)

    def test_console_job_rejects_unknown_marketing_signal_mode(self) -> None:
        with self.assertRaises(ValueError):
            run_marketing_signal_job({"mode": "mystery"})

    def test_console_job_refreshes_evidence_queue(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "queue", "status": "running"}) as start_mock:
            result = run_marketing_signal_job({"mode": "evidence_queue"})

        self.assertEqual("running", result["status"])
        self.assertIn("scripts/build_cosmetics_evidence_queue.py", start_mock.call_args.args[0])

    def test_console_job_starts_evidence_source_audit(self) -> None:
        with patch("scripts.console_server.start_process", return_value={"job_id": "source-audit", "status": "running"}) as start_mock:
            result = run_cosmetics_evidence_source_audit_job({})

        self.assertEqual("running", result["status"])
        self.assertIn("scripts/audit_cosmetics_pilot_evidence_sources.py", start_mock.call_args.args[0])


def signal(signal_id: str, decision: str, evidence_type: str) -> dict:
    return {
        "id": signal_id,
        "industry": "cosmetics_skincare",
        "sourceType": "seed_random",
        "sourceRef": {},
        "collectedAt": "2026-06-18T00:00:00+09:00",
        "topic": "daily_random_seed",
        "signalText": "가설 후보",
        "normalizedInsight": "타깃이 반응할 수 있는 가설",
        "targetSegment": "장마철 속당김 고객",
        "funnelStage": "awareness",
        "evidenceType": evidence_type,
        "strength": 3,
        "freshness": 2,
        "confidence": 1,
        "riskFlags": ["needs_external_validation"],
        "usableFor": ["concept", "copy"],
        "review": {"decision": decision, "reasonTags": [], "reviewNote": ""},
    }


if __name__ == "__main__":
    unittest.main()
