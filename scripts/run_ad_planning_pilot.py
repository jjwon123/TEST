#!/usr/bin/env python3
"""Run the cosmetics ad-planning pilot preflight and optional candidate generation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json, write_text
from scripts.audit_ad_planning_goal import REPORT_PATH as GOAL_AUDIT_PATH
from scripts.audit_ad_planning_goal import build_audit
from scripts.audit_cosmetics_pilot_goal import DEFAULT_OUTPUT as PILOT_GOAL_AUDIT_PATH
from scripts.audit_cosmetics_pilot_goal import build_audit as build_pilot_goal_audit
from scripts.benchmark_ad_planning import DEFAULT_REPORT, DEFAULT_RESULTS, DEFAULT_REVIEWS, aggregate, evaluate_case, run_external_cases, select_pending_concepts_for_connection_check
from scripts.export_ad_planning_review_packet import DEFAULT_MARKDOWN, DEFAULT_OUTPUT, build_packet, render_markdown
from scripts.manage_ad_planning_benchmark_review_sheet import DEFAULT_SHEET as DEFAULT_BENCHMARK_REVIEW_SHEET
from scripts.manage_ad_planning_benchmark_review_sheet import export_sheet as export_benchmark_review_sheet
from scripts.manage_ad_planning_benchmark_review_sheet import import_sheet as import_benchmark_review_sheet
from scripts.manage_ad_strategy_review_sheet import DEFAULT_SHEET, export_sheet, import_sheet
from services.ad_strategy.pilot_selection import pilot_dataset
from services.ad_strategy.text_quality import has_broken_korean
from services.ad_strategy.repository import load_examples_for_review, strategy_quality_metrics


SUMMARY_PATH = ROOT / ".tmp" / "model-benchmarks" / "ad-planning-pilot-run.json"
DATASET_PATH = ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--provider", choices=["local", "openai"], default="local", help="Candidate generator to use. Default: local.")
    parser.add_argument("--force-without-api", action="store_true", help="Deprecated. Kept for compatibility; local mode never needs an API key.")
    parser.add_argument("--select-pending-concepts", action="store_true", help="Connection-check mode: select default concepts for pending cases and generate copy without human approval.")
    args = parser.parse_args()
    summary = run_pilot(
        limit=args.limit,
        provider=args.provider,
        force_without_api=args.force_without_api,
        select_pending_concepts=args.select_pending_concepts,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def run_pilot(
    *,
    limit: int = 5,
    provider: str = "local",
    force_without_api: bool = False,
    select_pending_concepts: bool = False,
) -> dict[str, Any]:
    dataset = read_json(DATASET_PATH, default={"cases": [], "target": {}})
    selected_dataset = pilot_dataset(dataset, limit=limit)
    selected_count = len(selected_dataset.get("cases", []))
    review_cleanup = normalize_existing_reviews(DEFAULT_REVIEWS)
    candidate_generation_attempted = False
    if provider == "local" or force_without_api:
        candidate_generation_attempted = True
        run_external_cases(selected_dataset, DEFAULT_RESULTS, limit=selected_count, provider="local")
    elif provider == "openai":
        candidate_generation_attempted = True
        run_external_cases(selected_dataset, DEFAULT_RESULTS, limit=selected_count, provider="openai")
    connection_selection = {"selected": 0, "status": "not_requested"}
    if select_pending_concepts:
        before = pending_connection_check_count(DEFAULT_RESULTS)
        select_pending_concepts_for_connection_check(
            selected_dataset,
            DEFAULT_RESULTS,
            limit=selected_count,
            provider=provider,
        )
        after = pending_connection_check_count(DEFAULT_RESULTS)
        connection_selection = {
            "status": "attempted",
            "selected": max(0, before - after),
            "remainingPending": after,
            "note": "연결 확인용 기본 콘셉트 선택입니다. 사람 승인이나 최종 평가로 집계하지 않습니다.",
        }

    benchmark = refresh_benchmark(dataset)
    sheet_summary = export_sheet(DEFAULT_SHEET, limit=30)
    sheet_dry_run = import_sheet(DEFAULT_SHEET, apply=False)
    benchmark_sheet_summary = export_benchmark_review_sheet(
        DEFAULT_BENCHMARK_REVIEW_SHEET,
        dataset_path=DATASET_PATH,
        external_path=DEFAULT_RESULTS,
        reviews_path=DEFAULT_REVIEWS,
        limit=limit,
    )
    benchmark_sheet_dry_run = import_benchmark_review_sheet(DEFAULT_BENCHMARK_REVIEW_SHEET, apply=False)
    strategy_metrics = strategy_quality_metrics()
    packet = build_packet(
        dataset=dataset,
        benchmark=benchmark,
        external_results=read_json(DEFAULT_RESULTS, default={"results": []}),
        human_reviews=read_json(DEFAULT_REVIEWS, default={"reviews": []}),
        strategy_examples=load_examples_for_review(),
        strategy_metrics=strategy_metrics,
        provider=provider,
        pilot_limit=limit,
    )
    write_json(DEFAULT_OUTPUT, packet)
    write_text(DEFAULT_MARKDOWN, render_markdown(packet))
    audit = build_audit(benchmark, strategy_metrics)
    write_json(GOAL_AUDIT_PATH, audit)
    pilot_goal_audit = build_pilot_goal_audit(
        dataset=dataset,
        results=read_json(DEFAULT_RESULTS, default={"results": []}),
        reviews=read_json(DEFAULT_REVIEWS, default={"reviews": []}),
        limit=limit,
    )
    write_json(PILOT_GOAL_AUDIT_PATH, pilot_goal_audit)
    summary = {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "candidate_generation_attempted" if candidate_generation_attempted else "ready_for_manual_review",
        "provider": provider,
        "limit": selected_count,
        "pilotCaseIds": [str(item.get("id") or "") for item in selected_dataset.get("cases", [])],
        "candidateGenerationAttempted": candidate_generation_attempted,
        "externalGenerationAttempted": candidate_generation_attempted,
        "benchmark": benchmark.get("summary", {}),
        "reviewPacket": packet.get("summary", {}),
        "strategySheet": {
            "path": display_path(DEFAULT_SHEET),
            "rows": sheet_summary.get("rows", 0),
            "dryRunErrors": len(sheet_dry_run.get("errors", [])),
            "dryRunSkipped": sheet_dry_run.get("skipped", 0),
        },
        "benchmarkReviewSheet": {
            "path": display_path(DEFAULT_BENCHMARK_REVIEW_SHEET),
            "rows": benchmark_sheet_summary.get("rows", 0),
            "dryRunErrors": len(benchmark_sheet_dry_run.get("errors", [])),
            "dryRunSkipped": benchmark_sheet_dry_run.get("skipped", 0),
        },
        "reviewCleanup": review_cleanup,
        "connectionCheckSelection": connection_selection,
        "goalAudit": audit.get("summary", {}),
        "pilotGoalAudit": pilot_goal_audit.get("summary", {}),
        "blockers": packet.get("summary", {}).get("blockers", []),
    }
    write_json(SUMMARY_PATH, summary)
    return summary


def normalize_existing_reviews(path: Path) -> dict[str, Any]:
    payload = read_json(path, default={"schemaVersion": "1.0.0", "reviews": []})
    changed = 0
    for record in payload.get("reviews", []):
        note = str(record.get("reviewNote") or "")
        if has_broken_korean(note):
            record["reviewNote"] = "연결 단계 확인용 승인 기록입니다. 실제 품질 평가는 후속 검수에서 보강합니다."
            reason_tags = list(record.get("reasonTags") or [])
            if "review_note_cleaned" not in reason_tags:
                reason_tags.append("review_note_cleaned")
            record["reasonTags"] = reason_tags
            changed += 1
    if changed:
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        write_json(path, payload)
    return {"path": display_path(path), "cleanedReviewNotes": changed}


def pending_connection_check_count(path: Path) -> int:
    payload = read_json(path, default={"results": []})
    return sum(
        item.get("status") == "concept_review_pending" and not item.get("selectedConceptId")
        for item in payload.get("results", [])
        if isinstance(item, dict)
    )


def refresh_benchmark(dataset: dict[str, Any]) -> dict[str, Any]:
    reviews = {item["caseId"]: item for item in read_json(DEFAULT_REVIEWS, default={"reviews": []}).get("reviews", [])}
    external = {item["caseId"]: item for item in read_json(DEFAULT_RESULTS, default={"results": []}).get("results", [])}
    cases = [evaluate_case(item, reviews.get(item["id"], {}), external.get(item["id"], {})) for item in dataset.get("cases", [])]
    report = aggregate(cases, dataset.get("target", {}))
    write_json(DEFAULT_REPORT, report)
    return report


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
