"""Model benchmark aggregation and local-model promotion policy."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def evaluate_local_promotion(
    comparisons: list[dict[str, Any]],
    *,
    minimum_ratio: float = 0.8,
) -> dict[str, Any]:
    reviewed = [item for item in comparisons if item.get("externalScore") is not None and item.get("localScore") is not None]
    local_total = sum(float(item["localScore"]) for item in reviewed)
    external_total = sum(float(item["externalScore"]) for item in reviewed)
    quality_ratio = round(local_total / external_total, 3) if external_total else 0.0
    critical_errors = sum(int(item.get("localCriticalErrors") or 0) for item in reviewed)
    preferred = sum(1 for item in reviewed if item.get("preferred") == "local")
    return {
        "schemaVersion": "1.0.0",
        "reviewedComparisons": len(reviewed),
        "qualityRatio": quality_ratio,
        "minimumRatio": minimum_ratio,
        "localCriticalErrors": critical_errors,
        "localPreferredCount": preferred,
        "promotionStatus": "eligible" if reviewed and quality_ratio >= minimum_ratio and critical_errors == 0 else "not_eligible",
        "reasons": [
            reason
            for condition, reason in [
                (not reviewed, "No reviewed blind comparisons are available."),
                (quality_ratio < minimum_ratio, f"Local quality ratio is below {minimum_ratio:.0%}."),
                (critical_errors > 0, "Local model has critical errors."),
            ]
            if condition
        ],
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
