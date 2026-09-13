"""Select the canonical cosmetics pilot cases from the evidence plan."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils.json_io import read_json


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_PLAN = ROOT / "assets" / "rules" / "cosmetics-benchmark-evidence-plan.json"


def select_pilot_cases(
    dataset: dict[str, Any],
    *,
    limit: int = 5,
    evidence_plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return cases in evidence-plan priority order, then dataset order.

    Fixture and custom datasets whose IDs do not appear in the production
    evidence plan retain their original order.
    """
    cases = [item for item in dataset.get("cases", []) if isinstance(item, dict)]
    if limit < 0:
        raise ValueError("limit must be zero or greater")
    if not cases:
        return []

    plan = evidence_plan
    if plan is None:
        plan = read_json(DEFAULT_EVIDENCE_PLAN, {"events": []})

    case_by_id: dict[str, dict[str, Any]] = {}
    for case in cases:
        case_id = str(case.get("id") or "").strip()
        if not case_id:
            continue
        if case_id in case_by_id:
            raise ValueError(f"duplicate benchmark case id: {case_id}")
        case_by_id[case_id] = case

    plan_events = [
        (index, item)
        for index, item in enumerate(plan.get("events", []))
        if isinstance(item, dict)
    ]
    plan_events.sort(key=lambda entry: (int(entry[1].get("priority") or 2), entry[0]))

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for _, event in plan_events:
        event_id = str(event.get("id") or "").strip()
        case = case_by_id.get(event_id)
        if case is None or event_id in selected_ids:
            continue
        selected.append(case)
        selected_ids.add(event_id)

    for case in cases:
        case_id = str(case.get("id") or "").strip()
        if case_id and case_id in selected_ids:
            continue
        selected.append(case)
        if case_id:
            selected_ids.add(case_id)

    return selected[:limit or None]


def pilot_dataset(
    dataset: dict[str, Any],
    *,
    limit: int = 5,
    evidence_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Copy dataset metadata while replacing cases with the canonical pilot."""
    return {
        **dataset,
        "cases": select_pilot_cases(dataset, limit=limit, evidence_plan=evidence_plan),
    }
