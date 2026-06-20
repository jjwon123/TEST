#!/usr/bin/env python3
"""Export and import human review sheets for ad strategy examples."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ad_strategy.repository import REASON_TAGS, RUBRIC_KEYS, load_examples_for_review, strategy_quality_metrics, update_example_review


DEFAULT_SHEET = ROOT / ".tmp" / "model-benchmarks" / "ad-strategy-review-sheet.csv"
STRATEGY_FIELDS = ["targetInsight", "hookMechanism", "persuasionSequence", "offerMechanism", "proofMechanism", "ctaType", "toneTraits", "channelFit"]
SCORE_FIELDS = sorted(RUBRIC_KEYS)
SCORE_COLUMNS = {field: f"score_{field}" for field in SCORE_FIELDS}
FIELDNAMES = [
    "id",
    "industry",
    "sourceBrand",
    "sourceCopyPreview",
    "decision",
    *STRATEGY_FIELDS,
    *SCORE_COLUMNS.values(),
    "reasonTags",
    "reviewNote",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", type=Path, default=DEFAULT_SHEET)
    parser.add_argument("--import-sheet", action="store_true", help="Read review rows from --sheet instead of exporting.")
    parser.add_argument("--apply", action="store_true", help="Persist imported review rows. Without this, import is validation only.")
    parser.add_argument("--limit", type=int, default=0, help="Export at most N rows.")
    args = parser.parse_args()

    if args.import_sheet:
        summary = import_sheet(args.sheet.resolve(), apply=args.apply)
    else:
        summary = export_sheet(args.sheet.resolve(), limit=args.limit)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not summary.get("errors") else 1


def export_sheet(path: Path, *, limit: int = 0) -> dict[str, Any]:
    examples = sorted(load_examples_for_review(), key=lambda item: (item.get("review", {}).get("decision", "unreviewed") != "unreviewed", str(item.get("id", ""))))
    rows = [example_to_row(item) for item in examples[:limit or None]]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return {"mode": "export", "sheet": str(path), "rows": len(rows), "metrics": strategy_quality_metrics(), "errors": []}


def import_sheet(path: Path, *, apply: bool = False) -> dict[str, Any]:
    rows = read_rows(path)
    applied = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        decision = normalize_decision(row.get("decision", ""))
        if not decision:
            skipped += 1
            continue
        try:
            payload = row_to_payload(row, decision)
            validate_payload_shape(row.get("id", ""), payload)
            if apply:
                update_example_review(str(row.get("id") or ""), payload)
                applied += 1
        except Exception as exc:
            errors.append({"row": index, "id": row.get("id", ""), "error": str(exc)})
    return {
        "mode": "import",
        "sheet": str(path),
        "apply": apply,
        "rows": len(rows),
        "applied": applied,
        "skipped": skipped,
        "errors": errors,
        "metrics": strategy_quality_metrics(),
    }


def example_to_row(item: dict[str, Any]) -> dict[str, Any]:
    review = item.get("review", {})
    source = item.get("sourceOriginal", {})
    scores = review.get("scores", {})
    row = {
        "id": item.get("id", ""),
        "industry": item.get("industry", ""),
        "sourceBrand": source.get("brand", ""),
        "sourceCopyPreview": preview(source.get("copy", "")),
        "decision": "" if review.get("decision") == "unreviewed" else review.get("decision", ""),
        "reasonTags": ", ".join(review.get("reasonTags", []) or []),
        "reviewNote": review.get("reviewNote", ""),
    }
    for field in STRATEGY_FIELDS:
        value = item.get(field, "")
        row[field] = ", ".join(value) if isinstance(value, list) else value
    for field in SCORE_FIELDS:
        row[SCORE_COLUMNS[field]] = scores.get(field, "")
    return row


def row_to_payload(row: dict[str, str], decision: str) -> dict[str, Any]:
    scores = {
        key: int(str(row.get(SCORE_COLUMNS[key]) or "").strip())
        for key in SCORE_FIELDS
        if str(row.get(SCORE_COLUMNS[key]) or "").strip()
    }
    strategy = {}
    for field in STRATEGY_FIELDS:
        value = str(row.get(field) or "").strip()
        if field in {"persuasionSequence", "toneTraits", "channelFit"}:
            strategy[field] = split_csvish(value)
        else:
            strategy[field] = value
    return {
        "exampleId": str(row.get("id") or "").strip(),
        "decision": decision,
        "strategy": strategy,
        "scores": scores,
        "reasonTags": [tag for tag in split_csvish(str(row.get("reasonTags") or "")) if tag in REASON_TAGS],
        "reviewNote": str(row.get("reviewNote") or "").strip(),
    }


def validate_payload_shape(example_id: str, payload: dict[str, Any]) -> None:
    if not str(example_id or "").strip():
        raise ValueError("id is required")
    decision = payload["decision"]
    if decision not in {"selected", "shortlist", "rejected", "unreviewed"}:
        raise ValueError("decision must be selected, shortlist, rejected, or unreviewed")
    if decision != "unreviewed" and set(payload.get("scores", {})) != set(SCORE_FIELDS):
        raise ValueError("all eight rubric scores are required")
    for key, value in payload.get("scores", {}).items():
        if value < 1 or value > 5:
            raise ValueError(f"{key} must be between 1 and 5")
    if decision == "selected":
        strategy = payload.get("strategy", {})
        missing = [field for field in ("targetInsight", "hookMechanism", "persuasionSequence", "ctaType") if not strategy.get(field)]
        if missing:
            raise ValueError(f"selected row is missing strategy fields: {', '.join(missing)}")
        average = sum(payload["scores"].values()) / len(payload["scores"])
        if average < 4:
            raise ValueError("selected row requires average score >= 4")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def split_csvish(value: str) -> list[str]:
    return [item.strip() for item in value.replace("|", ",").split(",") if item.strip()]


def normalize_decision(value: str) -> str:
    decision = str(value or "").strip().lower()
    return decision if decision in {"selected", "shortlist", "rejected", "unreviewed"} else ""


def preview(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else f"{text[:limit - 1]}..."


if __name__ == "__main__":
    raise SystemExit(main())
