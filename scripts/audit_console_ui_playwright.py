#!/usr/bin/env python3
"""Audit the local console UI with Playwright.

This check is intentionally focused on what the human reviewer sees:
developer terms, raw JSON, A/B remnants, and horizontal overflow at 1280px.
It expects the console server to already be running.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import write_json, write_text


DEFAULT_URL = "http://127.0.0.1:5177/"
DEFAULT_OUTPUT = ROOT / ".tmp" / "console-ui-audit" / "latest-console-ui-playwright.json"

FORBIDDEN_VISIBLE_TERMS = [
    "meta_strategy",
    "concept_selection_pending",
    "provider",
    "blockers",
    "hook",
    "cta",
    "reason_to_believe",
    "JSON.stringify",
]

RAW_JSON_MARKERS = [
    '{"',
    "'{",
    '":',
    "strategyBasis",
    "planningEvidence",
]

ENGLISH_OPERATION_LINES = {
    "Brief",
    "Plan",
    "References",
    "Candidates",
    "Selection",
    "QA",
    "Archive",
    "Continue Brief",
    "Continue Plan",
    "Continue References",
    "Continue Candidates",
    "Generate and select image candidates",
    "Review selected references",
    "Build output package",
    "Review QA package",
    "Archive complete",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=1100)
    parser.add_argument("--timeout-ms", type=int, default=15000)
    parser.add_argument("--browser-channel", default="", help="Optional Playwright browser channel, for example chrome or msedge.")
    args = parser.parse_args()

    try:
        snapshot = capture_console_snapshot(
            url=args.url,
            width=args.width,
            height=args.height,
            timeout_ms=args.timeout_ms,
            browser_channel=args.browser_channel,
        )
        report = evaluate_console_snapshot(snapshot)
    except Exception as exc:
        report = {
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "status": "fail",
            "url": args.url,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "checks": {},
        }

    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    write_json(output_path, report)
    write_text(output_path.with_suffix(".md"), render_markdown(report))
    print(f"CONSOLE_UI_AUDIT {report['status']} {output_path}")
    return 0 if report["status"] == "pass" else 1


def capture_console_snapshot(*, url: str, width: int, height: int, timeout_ms: int, browser_channel: str = "") -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Playwright is not installed. Install requirements-reference-vision.txt first.") from exc

    with sync_playwright() as playwright:
        browser = launch_browser(playwright, browser_channel=browser_channel)
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            body_text = page.locator("body").inner_text(timeout=timeout_ms)
            metrics = page.evaluate(
                """() => {
                  const viewportWidth = window.innerWidth;
                  const nodes = Array.from(document.body.querySelectorAll("*"));
                  const overflowing = [];
                  for (const node of nodes) {
                    const style = window.getComputedStyle(node);
                    if (style.display === "none" || style.visibility === "hidden") continue;
                    const rect = node.getBoundingClientRect();
                    if (!rect.width || !rect.height) continue;
                    const horizontalOverflow = rect.right > viewportWidth + 1;
                    if (horizontalOverflow) {
                      overflowing.push({
                        tag: node.tagName.toLowerCase(),
                        className: String(node.className || ""),
                        text: String(node.innerText || node.textContent || "").trim().slice(0, 160),
                        right: Math.round(rect.right),
                        scrollWidth: node.scrollWidth,
                        clientWidth: node.clientWidth
                      });
                    }
                  }
                  return {
                    viewportWidth,
                    bodyScrollWidth: document.body.scrollWidth,
                    documentScrollWidth: document.documentElement.scrollWidth,
                    planningCases: document.querySelectorAll(".planning-case-card").length,
                    conceptCards: document.querySelectorAll(".planning-concept-card").length,
                    copyCards: document.querySelectorAll(".planning-copy-card").length,
                    benchmarkCopyEditFields: document.querySelectorAll("[data-benchmark-copy-edit]").length,
                    benchmarkReviewForms: document.querySelectorAll(".planning-review-form").length,
                    strategyReviewCards: document.querySelectorAll(".strategy-review-card").length,
                    strategyRecommendationActions: document.querySelectorAll("[data-review-strategy-recommendation]").length,
                    strategyReviewEntryButtons: document.querySelectorAll("[data-open-strategy-review]").length,
                    planningReviewEntryButtons: document.querySelectorAll("[data-open-planning-review]").length,
                    primaryPlanningActions: Array.from(document.querySelectorAll("[data-primary-planning-action]")).filter((node) => {
                      const style = window.getComputedStyle(node);
                      return style.display !== "none" && style.visibility !== "hidden" && node.getClientRects().length > 0;
                    }).length,
                    reviewSessionProgress: document.querySelectorAll(".review-session-progress").length,
                    eventEvidenceMetrics: document.querySelectorAll(".event-evidence-metric").length,
                    eventEvidenceBlockedCards: document.querySelectorAll(".event-evidence-blocked").length,
                    evidenceQueueCards: document.querySelectorAll(".evidence-work-card").length,
                    evidenceQueueSummaries: document.querySelectorAll(".evidence-queue-summary").length,
                    evidenceFocusActions: document.querySelectorAll("[data-evidence-focus]").length,
                    signalCards: document.querySelectorAll(".signal-card").length,
                    signalJobButtons: document.querySelectorAll("[data-signal-job]").length,
                    signalQualitySummaries: document.querySelectorAll(".signal-quality-summary").length,
                    signalRepairFields: document.querySelectorAll(".signal-repair-fields").length,
                    signalRecommendations: document.querySelectorAll(".signal-recommendation").length,
                    marketingLoopAuditButtons: document.querySelectorAll("[data-run-marketing-loop-audit]").length,
                    marketingLoopAuditSummaries: document.querySelectorAll(".planning-loop-audit").length,
                    copyCorrectionAuditButtons: document.querySelectorAll("[data-run-copy-correction-audit]").length,
                    copyCorrectionAuditSummaries: document.querySelectorAll(".correction-loop-audit").length,
                    planningCaseDetails: Array.from(document.querySelectorAll(".planning-case-card")).slice(0, 12).map((card) => ({
                      caseId: card.getAttribute("data-planning-case-id") || "",
                      title: String(card.querySelector("h3")?.textContent || "").trim(),
                      badge: String(card.querySelector(".planning-case-head .badge")?.textContent || "").trim(),
                      copyCards: card.querySelectorAll(".planning-copy-card").length,
                      editFields: card.querySelectorAll("[data-benchmark-copy-edit]").length,
                      reviewForms: card.querySelectorAll(".planning-review-form").length,
                      evidenceBlocked: card.querySelectorAll(".event-evidence-blocked").length > 0,
                      qualityBlocked: card.querySelectorAll(".selected-pill.blocked").length > 0,
                      qualitySummaries: card.querySelectorAll(".concept-quality-summary").length,
                      conceptSelectButtons: card.querySelectorAll("[data-benchmark-concept]").length
                    })),
                    overflowing: overflowing.slice(0, 20)
                  };
                }"""
            )
            return {
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "url": url,
                "viewport": {"width": width, "height": height},
                "bodyText": body_text,
                "metrics": metrics,
            }
        finally:
            browser.close()


def launch_browser(playwright: Any, *, browser_channel: str = "") -> Any:
    channels = [browser_channel] if browser_channel else [None, "chrome", "msedge"]
    errors: list[str] = []
    for channel in channels:
        try:
            if channel:
                return playwright.chromium.launch(channel=channel, headless=True)
            return playwright.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover - depends on local browser setup
            label = channel or "bundled chromium"
            errors.append(f"{label}: {exc}")
    joined = "\n".join(errors[-3:])
    raise RuntimeError(f"No Playwright browser could be launched.\n{joined}")


def evaluate_console_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    body_text = str(snapshot.get("bodyText") or "")
    metrics = snapshot.get("metrics") or {}
    forbidden_terms = [term for term in FORBIDDEN_VISIBLE_TERMS if term in body_text]
    raw_json_terms = [term for term in RAW_JSON_MARKERS if term in body_text]
    ab_terms = [term for term in ["안 A", "안 B", "A/B", "blindPreferred"] if term in body_text]
    broken_text_terms = [term for term in ["\ufffd", "�"] if term in body_text]
    visible_lines = {line.strip() for line in body_text.splitlines() if line.strip()}
    english_operation_lines = sorted(visible_lines & ENGLISH_OPERATION_LINES)
    overflowing = list(metrics.get("overflowing") or [])
    case_details = list(metrics.get("planningCaseDetails") or [])
    copy_cases = [item for item in case_details if int(item.get("copyCards") or 0) > 0]
    editable_copy_cases = [item for item in copy_cases if not item.get("evidenceBlocked") and not item.get("qualityBlocked")]
    concept_ready_cases = [
        item for item in case_details
        if not item.get("evidenceBlocked")
        and not item.get("qualityBlocked")
        and int(item.get("copyCards") or 0) == 0
    ]
    aggregate_copy_editing_pass = (
        int(metrics.get("copyCards") or 0) == 0
        or int(metrics.get("benchmarkCopyEditFields") or 0) > 0
        or int(metrics.get("eventEvidenceBlockedCards") or 0) >= int(metrics.get("planningCases") or 0)
    )
    aggregate_review_form_pass = (
        int(metrics.get("copyCards") or 0) == 0
        or int(metrics.get("benchmarkReviewForms") or 0) > 0
        or int(metrics.get("eventEvidenceBlockedCards") or 0) >= int(metrics.get("planningCases") or 0)
    )
    page_overflow = max(
        int(metrics.get("bodyScrollWidth") or 0),
        int(metrics.get("documentScrollWidth") or 0),
    ) > int(metrics.get("viewportWidth") or 1280) + 1

    checks = {
        "developerTermsHidden": {"pass": not forbidden_terms, "terms": forbidden_terms},
        "rawJsonHidden": {"pass": not raw_json_terms, "terms": raw_json_terms},
        "abComparisonHidden": {"pass": not ab_terms, "terms": ab_terms},
        "koreanTextReadable": {"pass": not broken_text_terms, "terms": broken_text_terms},
        "operationLabelsLocalized": {"pass": not english_operation_lines, "terms": english_operation_lines},
        "noHorizontalOverflow": {"pass": not overflowing and not page_overflow, "overflowing": overflowing},
        "planningDeskVisible": {
            "pass": int(metrics.get("planningCases") or 0) > 0 or int(metrics.get("signalCards") or 0) > 0,
            "planningCases": metrics.get("planningCases") or 0,
            "conceptCards": metrics.get("conceptCards") or 0,
            "copyCards": metrics.get("copyCards") or 0,
            "signalCards": metrics.get("signalCards") or 0,
            "eventEvidenceBlockedCards": metrics.get("eventEvidenceBlockedCards") or 0,
            "caseDetails": case_details,
        },
        "benchmarkCopyEditingVisible": {
            "pass": all(int(item.get("editFields") or 0) > 0 for item in editable_copy_cases)
            if case_details else aggregate_copy_editing_pass,
            "copyCards": metrics.get("copyCards") or 0,
            "benchmarkCopyEditFields": metrics.get("benchmarkCopyEditFields") or 0,
            "eventEvidenceBlockedCards": metrics.get("eventEvidenceBlockedCards") or 0,
            "failedCases": [item for item in editable_copy_cases if int(item.get("editFields") or 0) == 0],
        },
        "benchmarkReviewFormVisible": {
            "pass": all(int(item.get("reviewForms") or 0) > 0 for item in editable_copy_cases)
            if case_details else aggregate_review_form_pass,
            "benchmarkReviewForms": metrics.get("benchmarkReviewForms") or 0,
            "eventEvidenceBlockedCards": metrics.get("eventEvidenceBlockedCards") or 0,
            "failedCases": [item for item in editable_copy_cases if int(item.get("reviewForms") or 0) == 0],
        },
        "conceptQualitySummaryVisible": {
            "pass": all(int(item.get("qualitySummaries") or 0) > 0 for item in concept_ready_cases),
            "failedCases": [item for item in concept_ready_cases if int(item.get("qualitySummaries") or 0) == 0],
        },
        "conceptSelectionActionVisible": {
            "pass": all(int(item.get("conceptSelectButtons") or 0) > 0 for item in concept_ready_cases),
            "failedCases": [item for item in concept_ready_cases if int(item.get("conceptSelectButtons") or 0) == 0],
        },
        "strategyRecommendationActionVisible": {
            "pass": int(metrics.get("strategyReviewCards") or 0) == 0
            or int(metrics.get("strategyRecommendationActions") or 0) >= int(metrics.get("strategyReviewCards") or 0),
            "strategyReviewCards": metrics.get("strategyReviewCards") or 0,
            "strategyRecommendationActions": metrics.get("strategyRecommendationActions") or 0,
        },
        "strategyReviewEntryVisible": {
            "pass": int(metrics.get("strategyReviewEntryButtons") or 0) > 0,
            "strategyReviewEntryButtons": metrics.get("strategyReviewEntryButtons") or 0,
        },
        "planningReviewEntryVisible": {
            "pass": int(metrics.get("planningReviewEntryButtons") or 0) > 0,
            "planningReviewEntryButtons": metrics.get("planningReviewEntryButtons") or 0,
        },
        "primaryPlanningActionVisible": {
            "pass": int(metrics.get("primaryPlanningActions") or 0) == 1,
            "primaryPlanningActions": metrics.get("primaryPlanningActions") or 0,
        },
        "eventEvidenceQueueVisible": {
            "pass": int(metrics.get("eventEvidenceBlockedCards") or 0) == 0
            or (
                int(metrics.get("evidenceQueueCards") or 0) >= 5
                and int(metrics.get("evidenceQueueSummaries") or 0) > 0
                and int(metrics.get("evidenceFocusActions") or 0) >= 5
            ),
            "evidenceQueueCards": metrics.get("evidenceQueueCards") or 0,
            "evidenceQueueSummaries": metrics.get("evidenceQueueSummaries") or 0,
            "evidenceFocusActions": metrics.get("evidenceFocusActions") or 0,
        },
        "reviewSessionProgressVisible": {
            "pass": int(metrics.get("reviewSessionProgress") or 0) > 0,
            "reviewSessionProgress": metrics.get("reviewSessionProgress") or 0,
        },
        "eventEvidenceMetricVisible": {
            "pass": int(metrics.get("eventEvidenceMetrics") or 0) > 0,
            "eventEvidenceMetrics": metrics.get("eventEvidenceMetrics") or 0,
        },
        "signalCollectionActionsVisible": {
            "pass": int(metrics.get("signalJobButtons") or 0) >= 4,
            "signalJobButtons": metrics.get("signalJobButtons") or 0,
        },
        "signalQualitySummaryVisible": {
            "pass": int(metrics.get("signalCards") or 0) == 0 or int(metrics.get("signalQualitySummaries") or 0) > 0,
            "signalQualitySummaries": metrics.get("signalQualitySummaries") or 0,
        },
        "signalRepairFieldsVisible": {
            "pass": int(metrics.get("signalCards") or 0) == 0 or int(metrics.get("signalRepairFields") or 0) > 0,
            "signalRepairFields": metrics.get("signalRepairFields") or 0,
        },
        "signalRecommendationsVisible": {
            "pass": int(metrics.get("signalCards") or 0) == 0 or int(metrics.get("signalRecommendations") or 0) > 0,
            "signalRecommendations": metrics.get("signalRecommendations") or 0,
        },
        "marketingLoopAuditActionVisible": {
            "pass": int(metrics.get("marketingLoopAuditButtons") or 0) > 0,
            "marketingLoopAuditButtons": metrics.get("marketingLoopAuditButtons") or 0,
        },
        "marketingLoopAuditSummaryVisible": {
            "pass": int(metrics.get("marketingLoopAuditSummaries") or 0) > 0,
            "marketingLoopAuditSummaries": metrics.get("marketingLoopAuditSummaries") or 0,
        },
        "copyCorrectionAuditActionVisible": {
            "pass": int(metrics.get("copyCorrectionAuditButtons") or 0) > 0,
            "copyCorrectionAuditButtons": metrics.get("copyCorrectionAuditButtons") or 0,
        },
        "copyCorrectionAuditSummaryVisible": {
            "pass": int(metrics.get("copyCorrectionAuditSummaries") or 0) > 0,
            "copyCorrectionAuditSummaries": metrics.get("copyCorrectionAuditSummaries") or 0,
        },
    }
    errors = [name for name, value in checks.items() if not value["pass"]]
    return {
        "createdAt": snapshot.get("createdAt") or datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not errors else "fail",
        "url": snapshot.get("url"),
        "viewport": snapshot.get("viewport"),
        "errors": errors,
        "checks": checks,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Console UI Playwright Audit",
        "",
        f"- Status: `{report['status']}`",
        f"- URL: `{report.get('url') or '-'}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in (report.get("checks") or {}).items():
        mark = "PASS" if check.get("pass") else "FAIL"
        lines.append(f"- `{mark}` {name}")
    if report.get("errors"):
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- `{item}`" for item in report["errors"])
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
