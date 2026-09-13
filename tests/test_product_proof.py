from __future__ import annotations

import unittest
from unittest.mock import patch

from services.marketing_intelligence.product_proof import create_product_proof_candidate


class ProductProofTests(unittest.TestCase):
    def test_creates_unreviewed_event_scoped_proof(self) -> None:
        with patch(
            "services.marketing_intelligence.product_proof.append_signals",
            return_value={"added": 1, "total": 1},
        ) as append:
            result = create_product_proof_candidate(valid_payload())

        signal = result["signal"]
        self.assertEqual("launch-serum", signal["sourceRef"]["eventId"])
        self.assertEqual("proof", signal["evidenceType"])
        self.assertEqual("unreviewed", signal["review"]["decision"])
        self.assertIn("needs_human_review", signal["riskFlags"])
        append.assert_called_once()

    def test_rejects_non_https_brand_source(self) -> None:
        payload = valid_payload()
        payload["url"] = "http://example.test/product"
        with self.assertRaisesRegex(ValueError, "https URL"):
            create_product_proof_candidate(payload)

    def test_rejects_number_added_only_in_insight(self) -> None:
        payload = valid_payload()
        payload["normalizedInsight"] += " 2주 만에 개선된다고 설명한다."
        with self.assertRaisesRegex(ValueError, "numbers not present"):
            create_product_proof_candidate(payload)

    def test_internal_source_requires_document_reference(self) -> None:
        payload = valid_payload()
        payload["sourceKind"] = "internal"
        payload["url"] = ""
        payload["documentRef"] = ""
        with self.assertRaisesRegex(ValueError, "document reference"):
            create_product_proof_candidate(payload)


def valid_payload() -> dict:
    return {
        "eventId": "launch-serum",
        "topic": "elasticity_serum_launch",
        "sourceKind": "brand_site",
        "sourceName": "브랜드 공식 제품 페이지",
        "url": "https://example.test/elastic-serum",
        "documentRef": "",
        "productName": "탄력 세럼",
        "verifiedFact": "공식 제품 페이지에는 펩타이드 성분과 아침저녁 사용법이 기재되어 있다.",
        "normalizedInsight": "입증되지 않은 탄력 개선을 약속하지 않고 공개된 성분과 사용법을 제품 선택 기준으로 설명한다.",
        "targetSegment": "신제품 구매 전에 성분과 사용법을 확인하려는 고객",
        "claimBoundary": "제품별 인체적용시험 자료가 없으므로 탄력 개선 수치와 기간은 주장하지 않는다.",
        "observedAt": "2026-07-01",
        "methodology": "공식 제품 페이지의 전성분과 사용법 영역을 사람이 직접 대조했다.",
    }


if __name__ == "__main__":
    unittest.main()
