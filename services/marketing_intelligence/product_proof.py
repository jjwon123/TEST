"""Create reviewable product-proof signals from verified brand or internal facts."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from services.marketing_intelligence.repository import append_signals, normalize_signal


ALLOWED_SOURCE_KINDS = {"brand_site", "internal"}
RISKY_CLAIM_TERMS = {
    "치료",
    "완치",
    "재생",
    "즉시 개선",
    "영구",
    "부작용 없음",
    "100% 효과",
}


def create_product_proof_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    event_id = _required(payload, "eventId", 3)
    topic = _required(payload, "topic", 3)
    source_kind = str(payload.get("sourceKind") or "").strip()
    if source_kind not in ALLOWED_SOURCE_KINDS:
        raise ValueError("sourceKind must be brand_site or internal")

    source_name = _required(payload, "sourceName", 2)
    product_name = _required(payload, "productName", 2)
    verified_fact = _required(payload, "verifiedFact", 20)
    normalized_insight = _required(payload, "normalizedInsight", 20)
    target_segment = _required(payload, "targetSegment", 10)
    claim_boundary = _required(payload, "claimBoundary", 10)
    observed_at = _required(payload, "observedAt", 10)
    methodology = _required(payload, "methodology", 10)
    _validate_date(observed_at)

    url = str(payload.get("url") or "").strip()
    document_ref = str(payload.get("documentRef") or "").strip()
    if source_kind == "brand_site":
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Official brand proof requires an https URL")
    elif len(document_ref) < 3:
        raise ValueError("Internal proof requires a document reference")

    _validate_claim_scope(verified_fact, normalized_insight)
    signal_id = _proof_id(event_id, source_kind, url or document_ref, verified_fact)
    now = datetime.now(timezone.utc).isoformat()
    signal = normalize_signal({
        "id": signal_id,
        "industry": "cosmetics_skincare",
        "sourceType": source_kind,
        "sourceRef": {
            "collector": "verified_product_proof",
            "eventId": event_id,
            "sourceKind": source_kind,
            "sourceName": source_name,
            "productName": product_name,
            "url": url,
            "host": urlparse(url).netloc if url else "",
            "documentRef": document_ref,
            "observedAt": observed_at,
            "methodology": methodology,
            "claimBoundary": claim_boundary,
        },
        "collectedAt": now,
        "topic": topic,
        "signalText": verified_fact,
        "normalizedInsight": normalized_insight,
        "targetSegment": target_segment,
        "funnelStage": "consideration",
        "evidenceType": "proof",
        "strength": 4,
        "freshness": 4,
        "confidence": 4 if source_kind == "brand_site" else 3,
        "riskFlags": [
            "needs_human_review",
            "product_proof_unreviewed",
            "do_not_expand_beyond_verified_fact",
        ],
        "usableFor": ["concept", "copy", "qa"],
        "review": {
            "decision": "unreviewed",
            "reasonTags": [],
            "reviewNote": "공식 또는 내부 자료에서 옮긴 제품 사실입니다. 원문과 사용 한계를 사람이 대조하기 전에는 생성 근거로 사용하지 않습니다.",
            "reviewedAt": "",
        },
    })
    result = append_signals([signal])
    return {"signal": signal, "repository": result}


def _required(payload: dict[str, Any], field: str, minimum: int) -> str:
    value = str(payload.get(field) or "").strip()
    if len(value) < minimum:
        raise ValueError(f"{field} must contain at least {minimum} characters")
    return value


def _validate_date(value: str) -> None:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("observedAt must use YYYY-MM-DD format") from exc


def _validate_claim_scope(verified_fact: str, normalized_insight: str) -> None:
    combined = f"{verified_fact} {normalized_insight}"
    risky = sorted(term for term in RISKY_CLAIM_TERMS if term in combined)
    if risky:
        raise ValueError(f"High-risk efficacy expression is not accepted: {', '.join(risky)}")
    fact_numbers = set(re.findall(r"\d+(?:[.,]\d+)?%?", verified_fact))
    insight_numbers = set(re.findall(r"\d+(?:[.,]\d+)?%?", normalized_insight))
    unsupported_numbers = sorted(insight_numbers - fact_numbers)
    if unsupported_numbers:
        raise ValueError(
            "normalizedInsight contains numbers not present in verifiedFact: "
            + ", ".join(unsupported_numbers)
        )


def _proof_id(event_id: str, source_kind: str, reference: str, verified_fact: str) -> str:
    digest = hashlib.sha256(
        f"{event_id}|{source_kind}|{reference}|{verified_fact}".encode("utf-8")
    ).hexdigest()[:16]
    return f"product_proof_{digest}"
