from __future__ import annotations

import unittest

from scripts.audit_cosmetics_pilot_goal import build_audit


class CosmeticsPilotGoalAuditTests(unittest.TestCase):
    def test_passes_when_five_cases_are_complete_clean_reviewed_and_distinct(self) -> None:
        dataset = {"cases": [case(i) for i in range(5)]}
        results = {"results": [result(i, complete=True) for i in range(5)]}
        reviews = {"reviews": [review(i) for i in range(5)]}

        audit = build_audit(dataset=dataset, results=results, reviews=reviews, limit=5)

        self.assertEqual("pass", audit["status"])
        self.assertEqual([], audit["errors"])
        self.assertEqual(5, audit["summary"]["passedCases"])

    def test_fails_when_generated_text_contains_mojibake(self) -> None:
        dataset = {"cases": [case(i) for i in range(5)]}
        results = {"results": [result(i, complete=True) for i in range(5)]}
        results["results"][0]["concepts"]["candidates"][0]["name"] = "?쇱긽??遺덊렪???ㅼ떆 ?뺤쓽"
        reviews = {"reviews": [review(i) for i in range(5)]}

        audit = build_audit(dataset=dataset, results=results, reviews=reviews, limit=5)

        self.assertEqual("fail", audit["status"])
        self.assertIn("criticalErrorsZero", audit["errors"])
        first = audit["cases"][0]
        self.assertIn("noCriticalArtifacts", first["errors"])
        self.assertGreater(first["checks"]["noCriticalArtifacts"]["artifacts"]["brokenKoreanCount"], 0)

    def test_fails_until_copy_and_human_review_are_complete(self) -> None:
        dataset = {"cases": [case(i) for i in range(5)]}
        results = {"results": [result(i, complete=False) for i in range(5)]}
        reviews = {"reviews": []}

        audit = build_audit(dataset=dataset, results=results, reviews=reviews, limit=5)

        self.assertEqual("fail", audit["status"])
        self.assertIn("copyReady", audit["errors"])
        self.assertIn("humanReviewed", audit["errors"])

    def test_next_actions_separate_evidence_review_from_concept_selection(self) -> None:
        dataset = {"cases": [case(i) for i in range(5)]}
        results = {"results": [result(i, complete=False) for i in range(5)]}
        results["results"][1]["concepts"]["marketingEvidenceStatus"] = "needs_signal_review"

        audit = build_audit(dataset=dataset, results=results, reviews={"reviews": []}, limit=5)

        action_text = " ".join(audit["nextActions"])
        self.assertIn("Event 1의 이벤트 전용 근거를 먼저 검수", action_text)
        self.assertIn("Event 0", action_text)
        self.assertIn("콘셉트 1개를 사람이 선택", action_text)
        self.assertNotIn("평균 4.0 미만", action_text)

    def test_connection_check_review_does_not_satisfy_human_review_gate(self) -> None:
        dataset = {"cases": [case(i) for i in range(5)]}
        results = {"results": [result(i, complete=True) for i in range(5)]}
        rows = [review(i) for i in range(5)]
        rows[0]["reasonTags"] = ["connection_test"]
        rows[0]["conceptSelectionSource"] = "connection_check_default"

        audit = build_audit(dataset=dataset, results=results, reviews={"reviews": rows}, limit=5)

        self.assertEqual("fail", audit["status"])
        self.assertEqual(4, audit["summary"]["humanReviewed"])
        self.assertFalse(audit["cases"][0]["checks"]["humanReviewed"]["pass"])

    def test_fails_when_scorecard_contains_critical_errors(self) -> None:
        dataset = {"cases": [case(i) for i in range(5)]}
        results = {"results": [result(i, complete=True) for i in range(5)]}
        results["results"][0]["scorecard"] = {
            "criticalErrorCount": 1,
            "issues": [{"severity": "critical", "id": "concept_critic_channel_mismatch"}],
        }
        reviews = {"reviews": [review(i) for i in range(5)]}

        audit = build_audit(dataset=dataset, results=results, reviews=reviews, limit=5)

        self.assertEqual("fail", audit["status"])
        self.assertIn("criticalErrorsZero", audit["errors"])
        self.assertIn("scorecardCriticalErrorsZero", audit["cases"][0]["errors"])

    def test_fails_when_evidence_belongs_to_another_event(self) -> None:
        dataset = {"cases": [case(i) for i in range(5)]}
        results = {"results": [result(i, complete=True) for i in range(5)]}
        results["results"][0]["concepts"]["marketingEvidenceEventId"] = "other-event"
        results["results"][0]["copyPackage"]["marketingEvidenceEventId"] = "other-event"
        reviews = {"reviews": [review(i) for i in range(5)]}

        audit = build_audit(dataset=dataset, results=results, reviews=reviews, limit=5)

        self.assertEqual("fail", audit["status"])
        self.assertIn("evidenceConnected", audit["errors"])
        self.assertFalse(audit["cases"][0]["checks"]["evidenceConnected"]["eventMatch"])


def case(index: int) -> dict:
    return {"id": f"case-{index}", "eventName": f"Event {index}"}


def result(index: int, *, complete: bool) -> dict:
    outputs = [
        {"deliverableId": "feed", "planningEvidence": {"marketingSignalIds": [f"s{index}-1"]}},
    ] if complete else []
    return {
        "caseId": f"case-{index}",
        "status": "complete" if complete else "concept_review_pending",
        "concepts": {
            "marketingEvidenceStatus": "ready",
            "marketingEvidenceEventId": f"case-{index}",
            "candidates": [
                concept("concept_01", "출근길 번들거림", "가볍게 정리", "공감", ["상황", "제품"], "샘플 증정", "루틴 보기"),
                concept("concept_02", "성분을 따지는 고객", "선택 기준 제시", "신뢰", ["근거", "사용"], "체험 제안", "기준 확인"),
                concept("concept_03", "여름 톤 고민", "계절 루틴 연결", "기대", ["계절", "행동"], "한정 구성", "제안 보기"),
            ],
        },
        "copyPackage": {
            "marketingEvidenceStatus": "ready",
            "marketingEvidenceEventId": f"case-{index}",
            "outputs": outputs,
        },
        "scorecard": {"criticalErrorCount": 0, "issues": []},
    }


def concept(
    concept_id: str,
    target: str,
    promise: str,
    emotion: str,
    sequence: list[str],
    offer: str,
    cta: str,
) -> dict:
    return {
        "conceptId": concept_id,
        "targetInsight": target,
        "corePromise": promise,
        "emotionalDirection": emotion,
        "persuasionSequence": sequence,
        "offerPresentation": offer,
        "cta": cta,
        "marketingSignalIds": ["s1", "s2", "s3"],
    }


def review(index: int) -> dict:
    return {
        "caseId": f"case-{index}",
        "approved": True,
        "edited": False,
        "scores": {
            "strategyClarity": 4,
            "targetEmpathy": 4,
            "productConnection": 4,
            "distinctiveness": 4,
            "channelFit": 4,
            "koreanCopyQuality": 4,
            "brandFit": 4,
            "actionability": 4,
        },
    }


if __name__ == "__main__":
    unittest.main()
