#!/usr/bin/env python3
"""Audit that reviewed marketing signals are usable in planning outputs."""

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

from core.utils.json_io import read_json, write_json  # noqa: E402
from services.marketing_intelligence.insight_brief import INSIGHT_BRIEF_PATH  # noqa: E402
from services.marketing_intelligence.repository import signal_metrics  # noqa: E402


DEFAULT_OUTPUT = ROOT / ".tmp" / "model-benchmarks" / "marketing-planning-loop-audit.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", dest="run_dir", type=Path, required=True, help="Run directory to audit.")
    parser.add_argument("--minimum-signals", type=int, default=3)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = build_audit(args.run_dir.resolve(), minimum_signals=max(1, args.minimum_signals))
    write_json(args.output.resolve(), report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


def build_audit(run_dir: Path, *, minimum_signals: int = 3) -> dict[str, Any]:
    stage_dir = run_dir / "02_content_planning"
    insight = read_json(INSIGHT_BRIEF_PATH, default={})
    concepts = read_json(stage_dir / "concept-candidates.json", default={})
    copy_package = read_json(stage_dir / "copy-package.json", default={})
    scorecard = read_json(stage_dir / "planning-scorecard.json", default={})
    metrics = signal_metrics()

    checks = {
        "selectedUsableEnough": {
            "pass": int(metrics.get("selectedUsable") or 0) >= minimum_signals,
            "selectedUsable": metrics.get("selectedUsable") or 0,
            "minimum": minimum_signals,
        },
        "insightBriefReady": {
            "pass": insight.get("status") == "ready" and int(insight.get("selectedSignalCount") or 0) >= minimum_signals,
            "status": insight.get("status"),
            "selectedSignalCount": insight.get("selectedSignalCount") or 0,
        },
        "scorecardPasses": {
            "pass": scorecard.get("status") == "pass"
            and int(scorecard.get("criticalErrorCount") or 0) == 0
            and float(scorecard.get("averageScore") or 0) >= 4.0,
            "status": scorecard.get("status"),
            "criticalErrorCount": scorecard.get("criticalErrorCount"),
            "averageScore": scorecard.get("averageScore"),
        },
        "conceptsUseMarketingEvidence": concept_evidence_check(concepts, minimum_signals=minimum_signals),
        "copyUsesMarketingEvidence": copy_evidence_check(copy_package),
    }
    errors = [name for name, value in checks.items() if not value.get("pass")]
    return {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not errors else "fail",
        "runDir": display_path(run_dir),
        "errors": errors,
        "checks": checks,
    }


def concept_evidence_check(concepts: dict[str, Any], *, minimum_signals: int) -> dict[str, Any]:
    candidates = concepts.get("candidates") or []
    ids_by_concept = {
        str(item.get("conceptId") or ""): list(item.get("marketingSignalIds") or [])
        for item in candidates
    }
    return {
        "pass": concepts.get("marketingEvidenceStatus") == "ready"
        and len(candidates) == 3
        and all(len(ids) >= min(3, minimum_signals) for ids in ids_by_concept.values()),
        "marketingEvidenceStatus": concepts.get("marketingEvidenceStatus"),
        "candidateCount": len(candidates),
        "idsByConcept": ids_by_concept,
    }


def copy_evidence_check(copy_package: dict[str, Any]) -> dict[str, Any]:
    outputs = copy_package.get("outputs") or []
    ids_by_output = {
        str(item.get("deliverableId") or item.get("channelId") or ""): list((item.get("planningEvidence") or {}).get("marketingSignalIds") or [])
        for item in outputs
    }
    return {
        "pass": copy_package.get("marketingEvidenceStatus") == "ready"
        and len(outputs) > 0
        and all(len(ids) > 0 for ids in ids_by_output.values()),
        "marketingEvidenceStatus": copy_package.get("marketingEvidenceStatus"),
        "outputCount": len(outputs),
        "idsByOutput": ids_by_output,
    }


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
