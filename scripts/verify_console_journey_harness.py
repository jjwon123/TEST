#!/usr/bin/env python3
"""Repeat the isolated 01→06 production journey and verify console handoff hooks.

The harness deliberately uses the full-pipeline smoke fixture under ``.tmp`` so
it never changes a user's event, run, asset, or human-review record.  Each
iteration performs all workflow stages and then validates the browser-side
handoff contracts that advance the console between workspaces.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import write_json
from scripts.smoke_test_full_pipeline import (
    DEFAULT_EVENT,
    DEFAULT_IMAGE,
    DEFAULT_INSIGHT,
    run_smoke,
)


STAGES = (
    "01_event_brief",
    "02_content_planning",
    "03_reference_research",
    "04_visual_candidates",
    "05_admin_selection",
    "06_qa_packaging",
)


def console_handoff_checks() -> dict[str, bool]:
    source = (ROOT / "ui" / "console" / "app.js").read_text(encoding="utf-8")
    completion_hook = source.split("async function waitForWorkflowJob", 1)[1].split("async function updateCandidateDecision", 1)[0]
    concept_hook = source.split("async function selectPlanningBenchmarkConcept", 1)[1].split("async function runPlanningPilot", 1)[0]
    copy_review_hook = source.split("async function reviewPlanningBenchmark", 1)[1].split("function collectBenchmarkCopyEdits", 1)[0]
    return {
        "job_done_advances": '"done", "completed"' in completion_hook,
        "concept_selection_opens_copy_review": 'state.missionMode = "copy_review"' in concept_hook,
        "copy_review_creates_or_opens_production_run": '"/api/planning-benchmark/production-handoff"' in copy_review_hook and 'setView("references")' in copy_review_hook,
        "reference_job_opens_prompts": 'setView("prompts")' in source,
        "prompt_job_opens_images": 'setView("images")' in source,
        "image_selection_opens_package": 'setView("package")' in source,
    }


def verify_browser_concept_to_copy_transition(url: str = "http://127.0.0.1:5177/") -> dict[str, Any]:
    """Click the real step-2 CTA in Playwright without mutating production data.

    Bootstrap and the selection response are intercepted only for this browser
    session. This keeps human review records untouched while exercising the
    same HTML, JavaScript listeners, render cycle, and scroll handoff a user
    receives in the console.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"pass": False, "error": f"Playwright unavailable: {exc}"}

    with urlopen(f"{url.rstrip('/')}/api/bootstrap", timeout=10) as response:
        bootstrap = json.loads(response.read().decode("utf-8"))
    case = dict((bootstrap.get("planningBenchmark", {}).get("cases") or [])[0])
    external = dict(case.get("external") or {})
    candidates = ((external.get("concepts") or {}).get("candidates") or [])
    if not case or not external or not candidates or not (external.get("copyPackage") or {}).get("outputs"):
        return {"pass": False, "error": "No complete benchmark fixture is available for browser transition verification."}

    case_id = str(case["caseId"])
    concept_id = str(candidates[0]["conceptId"])
    initial_external = {**external, "status": "concept_selection_pending", "selectedConceptId": ""}
    initial_external.pop("copyPackage", None)
    initial_case = {**case, "external": initial_external}
    initial = {**bootstrap, "planningBenchmark": {"cases": [initial_case]}, "planningReviewPacket": {"benchmarkReviewQueue": [{"caseId": case_id, "status": "concept_selection_pending"}]}}
    selected_external = {**external, "status": "human_review_pending", "selectedConceptId": concept_id}
    selected_case = {**case, "external": selected_external}
    selection_response = {
        "ok": True,
        "case": selected_case,
        "report": {"cases": [selected_case]},
        "metrics": bootstrap.get("adStrategyQuality") or {},
        "reviewPacket": {"benchmarkReviewQueue": [{"caseId": case_id, "status": "human_review_pending"}]},
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 1100})
            page.route("**/api/bootstrap", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(initial)))
            page.route("**/api/planning-benchmark/concept-selection", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(selection_response)))
            page.goto(url, wait_until="networkidle", timeout=15000)
            page.locator("[data-confirm-mission]").click(timeout=10000)
            page.locator(f'[data-copy-review-case="{case_id}"]').wait_for(state="visible", timeout=10000)
            return {
                "pass": True,
                "caseId": case_id,
                "conceptId": concept_id,
                "copyCards": page.locator(".planning-copy-card").count(),
                "viewText": page.locator(f'[data-copy-review-case="{case_id}"]').inner_text()[:160],
            }
        except Exception as exc:
            return {"pass": False, "error": f"{type(exc).__name__}: {exc}"}
        finally:
            browser.close()


def run_harness(iterations: int, output_root: Path, console_url: str) -> dict[str, Any]:
    session_root = output_root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    session_root.mkdir(parents=True, exist_ok=False)
    results: list[dict[str, Any]] = []
    for index in range(1, iterations + 1):
        iteration_root = session_root / f"iteration-{index:02d}"
        try:
            result = run_smoke(
                session_root=iteration_root,
                source_event=DEFAULT_EVENT.resolve(),
                insight_source=DEFAULT_INSIGHT.resolve(),
                fixture_image=DEFAULT_IMAGE.resolve(),
                concept_id="concept_03",
            )
            stage_status = result.get("stageStatus", {})
            stages_complete = all(stage_status.get(stage) in {"approved", "done"} for stage in STAGES)
            results.append({
                "iteration": index,
                "status": result.get("status"),
                "run": result.get("run"),
                "stagesComplete01To06": stages_complete,
                "stageStatus": {stage: stage_status.get(stage) for stage in STAGES},
                "checks": result.get("checks", {}),
            })
        except Exception as exc:  # keep the remaining repetitions observable
            results.append({
                "iteration": index,
                "status": "fail",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc().splitlines()[-10:],
            })

    hooks = console_handoff_checks()
    browser_transition = verify_browser_concept_to_copy_transition(console_url)
    passed = all(item.get("status") == "pass" and item.get("stagesComplete01To06") for item in results) and all(hooks.values()) and browser_transition.get("pass") is True
    return {
        "schemaVersion": "1.0.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if passed else "fail",
        "scope": "isolated 01-to-06 workflow repetitions plus console handoff contracts",
        "iterationsRequested": iterations,
        "iterationsPassed": sum(1 for item in results if item.get("status") == "pass" and item.get("stagesComplete01To06")),
        "consoleHandoffChecks": hooks,
        "browserConceptToCopyTransition": browser_transition,
        "results": results,
        "sessionRoot": str(session_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--console-url", default="http://127.0.0.1:5177/")
    parser.add_argument("--output-root", type=Path, default=ROOT / ".tmp" / "console-journey-harness")
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be at least 1")
    output_root = args.output_root.resolve()
    if ROOT not in output_root.parents:
        parser.error("--output-root must stay inside this workspace")
    output_root.mkdir(parents=True, exist_ok=True)
    report = run_harness(args.iterations, output_root, args.console_url)
    write_json(output_root / "latest-report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
