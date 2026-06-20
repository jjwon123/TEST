#!/usr/bin/env python3
"""Audit progress toward the fixed cosmetics ad-planning quality goal."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json
from services.ad_strategy.repository import strategy_quality_metrics

REPORT_PATH = ROOT / ".tmp" / "model-benchmarks" / "ad-planning-goal-audit.json"


def build_audit(benchmark: dict[str, Any], strategy_metrics: dict[str, Any]) -> dict[str, Any]:
    summary = benchmark.get("summary", {})
    cases = int(summary.get("cases") or 0)
    candidate_generated = int(summary.get("candidateGenerated") or summary.get("externalGenerated") or 0)
    completed_copy = int(summary.get("externalGenerated") or 0)
    reviewed = int(summary.get("reviewed") or 0)
    checks = [
        check("fixed_evaluation_set", cases == 20, f"{cases}/20 cases"),
        check("candidate_results_complete", candidate_generated == 20, f"{candidate_generated}/20 candidate results"),
        check("human_reviews_complete", reviewed == 20, f"{reviewed}/20 human reviews"),
        check("critical_errors_zero_on_all_cases", completed_copy == 20 and int(summary.get("criticalErrors") or 0) == 0, f"{summary.get('criticalErrors', 0)} critical errors across {completed_copy}/20 completed copy cases"),
        check("average_human_score", reviewed == 20 and float(summary.get("averageHumanScore") or 0) >= 4, f"{summary.get('averageHumanScore', 0)}/5"),
        check("unchanged_approval_rate", reviewed == 20 and float(summary.get("unchangedApprovalRate") or 0) >= .5, f"{float(summary.get('unchangedApprovalRate') or 0):.1%}"),
        check("blind_candidate_preference", reviewed == 20 and float(summary.get("blindPreferenceRate") or 0) >= .7, f"{float(summary.get('blindPreferenceRate') or 0):.1%}"),
        check("strategy_review_readiness", int(strategy_metrics.get("decisions", {}).get("selected", 0)) + int(strategy_metrics.get("decisions", {}).get("shortlist", 0)) >= 30, f"{int(strategy_metrics.get('decisions', {}).get('selected', 0)) + int(strategy_metrics.get('decisions', {}).get('shortlist', 0))}/30 selected or shortlist"),
    ]
    goal_checks = [item for item in checks if item["id"] != "strategy_review_readiness"]
    return {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(item["passed"] for item in goal_checks) else "incomplete",
        "summary": {
            "passed": sum(item["passed"] for item in checks),
            "total": len(checks),
            "goalPassed": sum(item["passed"] for item in goal_checks),
            "goalTotal": len(goal_checks),
        },
        "checks": checks,
    }


def check(check_id: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {"id": check_id, "passed": bool(passed), "evidence": evidence}


def main() -> int:
    benchmark = read_json(ROOT / ".tmp" / "model-benchmarks" / "cosmetics-planning-benchmark.json", default={})
    audit = build_audit(benchmark, strategy_quality_metrics())
    write_json(REPORT_PATH, audit)
    print(json.dumps({"status": audit["status"], **audit["summary"]}, ensure_ascii=False))
    return 0 if audit["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
