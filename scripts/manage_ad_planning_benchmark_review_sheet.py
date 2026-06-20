#!/usr/bin/env python3
"""Export and import human review sheets for the fixed ad-planning benchmark."""

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

from core.utils.json_io import read_json
from scripts.benchmark_ad_planning import DEFAULT_RESULTS, DEFAULT_REVIEWS, RUBRIC_KEYS, evaluate_case, save_human_review


DATASET_PATH = ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json"
DEFAULT_SHEET = ROOT / ".tmp" / "model-benchmarks" / "ad-planning-benchmark-review-sheet.csv"
SCORE_FIELDS = sorted(RUBRIC_KEYS)
SCORE_COLUMNS = {field: f"score_{field}" for field in SCORE_FIELDS}
FIELDNAMES = [
    "caseId",
    "eventType",
    "eventName",
    "product",
    "target",
    "offer",
    "externalStatus",
    "selectedConceptId",
    "variantA",
    "variantB",
    "blindPreferred",
    "approved",
    "edited",
    *SCORE_COLUMNS.values(),
    "reasonTags",
    "reviewNote",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", type=Path, default=DEFAULT_SHEET)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--external-results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--import-sheet", action="store_true", help="Read review rows from --sheet instead of exporting.")
    parser.add_argument("--apply", action="store_true", help="Persist imported benchmark reviews. Without this, import is validation only.")
    parser.add_argument("--limit", type=int, default=0, help="Export at most N rows.")
    args = parser.parse_args()

    if args.import_sheet:
        summary = import_sheet(args.sheet.resolve(), reviews_path=args.reviews.resolve(), apply=args.apply)
    else:
        summary = export_sheet(
            args.sheet.resolve(),
            dataset_path=args.dataset.resolve(),
            external_path=args.external_results.resolve(),
            reviews_path=args.reviews.resolve(),
            limit=args.limit,
        )
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not summary.get("errors") else 1


def export_sheet(path: Path, *, dataset_path: Path = DATASET_PATH, external_path: Path = DEFAULT_RESULTS, reviews_path: Path = DEFAULT_REVIEWS, limit: int = 0) -> dict[str, Any]:
    dataset = read_json(dataset_path, default={"cases": []})
    external = {item.get("caseId"): item for item in read_json(external_path, default={"results": []}).get("results", [])}
    reviews = {item.get("caseId"): item for item in read_json(reviews_path, default={"reviews": []}).get("reviews", [])}
    rows = [
        case_to_row(case, reviews.get(case.get("id"), {}), external.get(case.get("id"), {}))
        for case in dataset.get("cases", [])[:limit or None]
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return {"mode": "export", "sheet": str(path), "rows": len(rows), "reviewed": sum(1 for row in rows if row.get("blindPreferred")), "errors": []}


def import_sheet(path: Path, *, reviews_path: Path = DEFAULT_REVIEWS, apply: bool = False) -> dict[str, Any]:
    rows = read_rows(path)
    applied = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        if not has_review_input(row):
            skipped += 1
            continue
        try:
            payload = row_to_payload(row)
            if apply:
                save_human_review(str(row.get("caseId") or "").strip(), payload, reviews_path)
                applied += 1
        except Exception as exc:
            errors.append({"row": index, "caseId": row.get("caseId", ""), "error": str(exc)})
    return {"mode": "import", "sheet": str(path), "apply": apply, "rows": len(rows), "applied": applied, "skipped": skipped, "errors": errors}


def case_to_row(case: dict[str, Any], review: dict[str, Any], external: dict[str, Any]) -> dict[str, Any]:
    evaluated = evaluate_case(case, review, external)
    row = {
        "caseId": case.get("id", ""),
        "eventType": case.get("eventType", ""),
        "eventName": case.get("eventName", ""),
        "product": case.get("product", ""),
        "target": case.get("target", ""),
        "offer": case.get("offer", ""),
        "externalStatus": external.get("status", ""),
        "selectedConceptId": external.get("selectedConceptId", ""),
        "variantA": summarize_variant(evaluated.get("blindComparison", {}).get("A", {})),
        "variantB": summarize_variant(evaluated.get("blindComparison", {}).get("B", {})),
        "blindPreferred": review.get("blindPreferred", ""),
        "approved": bool_to_sheet(review.get("approved")) if review else "",
        "edited": bool_to_sheet(review.get("edited")) if review else "",
        "reasonTags": ", ".join(review.get("reasonTags", []) or []),
        "reviewNote": review.get("reviewNote", ""),
    }
    for field in SCORE_FIELDS:
        row[SCORE_COLUMNS[field]] = review.get("scores", {}).get(field, "")
    return row


def row_to_payload(row: dict[str, str]) -> dict[str, Any]:
    case_id = str(row.get("caseId") or "").strip()
    if not case_id:
        raise ValueError("caseId is required")
    scores = {
        key: int(str(row.get(SCORE_COLUMNS[key]) or "").strip())
        for key in SCORE_FIELDS
        if str(row.get(SCORE_COLUMNS[key]) or "").strip()
    }
    if set(scores) != set(SCORE_FIELDS):
        raise ValueError("all eight benchmark rubric scores are required")
    for key, value in scores.items():
        if value < 1 or value > 5:
            raise ValueError(f"{key} must be between 1 and 5")
    blind_preferred = str(row.get("blindPreferred") or "").strip().upper()
    if blind_preferred and blind_preferred not in {"A", "B"}:
        raise ValueError("blindPreferred must be A or B when A/B comparison is used")
    return {
        "scores": scores,
        "approved": parse_bool(row.get("approved")),
        "edited": parse_bool(row.get("edited")),
        "blindPreferred": blind_preferred,
        "reasonTags": split_csvish(str(row.get("reasonTags") or "")),
        "reviewNote": str(row.get("reviewNote") or "").strip(),
    }


def has_review_input(row: dict[str, str]) -> bool:
    values = [row.get("blindPreferred", ""), row.get("approved", ""), row.get("edited", ""), row.get("reviewNote", "")]
    values.extend(row.get(column, "") for column in SCORE_COLUMNS.values())
    return any(str(value or "").strip() for value in values)


def summarize_variant(variant: dict[str, Any]) -> str:
    if not variant.get("available"):
        return "not available"
    concept_bits = []
    for concept in variant.get("concepts", [])[:3]:
        concept_bits.append(" / ".join(str(concept.get(key) or "") for key in ("name", "targetInsight", "corePromise") if concept.get(key)))
    copy_bits = []
    for output in variant.get("copyPackage", [])[:2]:
        copy = output.get("copy") or {}
        copy_bits.append(" ".join(str(value) for value in copy.values()) if isinstance(copy, dict) else str(copy))
    text = " || ".join([*concept_bits, *copy_bits])
    return preview(text or "available")


def parse_bool(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "approved", "pass", "ok"}


def bool_to_sheet(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return ""


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def split_csvish(value: str) -> list[str]:
    return [item.strip() for item in value.replace("|", ",").split(",") if item.strip()]


def preview(value: Any, limit: int = 420) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else f"{text[:limit - 1]}..."


if __name__ == "__main__":
    raise SystemExit(main())
