"""Audit curated marketing evidence snapshots before human review."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
import re


PILOT_EVENT_IDS = {
    "season-monsoon-barrier",
    "promotion-gift",
    "launch-serum",
    "education-barrier",
    "branding-minimal",
}
REQUIRED_FIELDS = (
    "eventId",
    "topic",
    "sourceKind",
    "sourceName",
    "title",
    "observedAt",
    "methodology",
    "evidenceType",
    "targetSegment",
    "observedText",
    "normalizedInsight",
)


def audit_evidence_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    observations = [item for item in snapshot.get("observations", []) if isinstance(item, dict)]
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    fingerprints: set[tuple[str, str, str, str]] = set()
    for index, item in enumerate(observations):
        event_id = str(item.get("eventId") or "")
        missing = [field for field in REQUIRED_FIELDS if not str(item.get(field) or "").strip()]
        if missing:
            errors.append({"index": index, "eventId": event_id, "code": "missing_provenance", "fields": missing})
        source_kind = str(item.get("sourceKind") or "")
        url = str(item.get("url") or "")
        if source_kind != "event_brief":
            host = urlparse(url).netloc.lower()
            if not host:
                errors.append({"index": index, "eventId": event_id, "code": "missing_public_url"})
        if event_id not in PILOT_EVENT_IDS:
            errors.append({"index": index, "eventId": event_id, "code": "unexpected_event"})
        joined = " ".join(str(item.get(field) or "") for field in ("observedText", "normalizedInsight"))
        if re.search(r"<(?:html|body|script|style|div)\b|[\"'](?:slides|headline)[\"']\s*:", joined, re.IGNORECASE):
            errors.append({"index": index, "eventId": event_id, "code": "raw_structure_exposed"})
        if "�" in joined or re.search(r"(ì|ë|í|ê|ð|Ã|Â|爰|愿|怨|諛|섏|쒕|좏|留)", joined):
            errors.append({"index": index, "eventId": event_id, "code": "broken_text"})
        fingerprint = (
            event_id,
            str(item.get("evidenceType") or ""),
            url,
            str(item.get("normalizedInsight") or ""),
        )
        if fingerprint in fingerprints:
            errors.append({"index": index, "eventId": event_id, "code": "duplicate_observation"})
        fingerprints.add(fingerprint)
        published_year = _year(item.get("publishedAt"))
        if published_year and datetime.now(timezone.utc).year - published_year > 5:
            warnings.append({"index": index, "eventId": event_id, "code": "foundational_source_over_five_years_old"})

    event_counts = Counter(str(item.get("eventId") or "") for item in observations)
    for event_id in sorted(PILOT_EVENT_IDS):
        if event_counts[event_id] < 3:
            errors.append({"eventId": event_id, "code": "fewer_than_three_candidates", "value": event_counts[event_id]})
    launch_types = {
        str(item.get("evidenceType") or "")
        for item in observations
        if item.get("eventId") == "launch-serum"
    }
    if "proof" not in launch_types:
        warnings.append({
            "eventId": "launch-serum",
            "code": "product_proof_intentionally_missing",
            "message": "가상 탄력 세럼의 공식 성분·시험 자료가 없어 제품 효능 근거를 만들지 않았습니다.",
        })
    return {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not errors else "fail",
        "summary": {
            "observations": len(observations),
            "events": len(event_counts),
            "errors": len(errors),
            "warnings": len(warnings),
            "unreviewedPolicy": snapshot.get("policy", {}).get("decision") == "unreviewed",
        },
        "eventCounts": dict(sorted(event_counts.items())),
        "errors": errors,
        "warnings": warnings,
    }


def _year(value: Any) -> int:
    match = re.match(r"^(\d{4})", str(value or "").strip())
    return int(match.group(1)) if match else 0
