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
                    planningCases: document.querySelectorAll(".planning-review-case").length,
                    conceptCards: document.querySelectorAll(".concept-card").length,
                    copyCards: document.querySelectorAll(".copy-card").length,
                    signalCards: document.querySelectorAll(".signal-card").length,
                    signalJobButtons: document.querySelectorAll("[data-signal-job]").length,
                    signalRecommendations: document.querySelectorAll(".signal-recommendation").length,
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
    overflowing = list(metrics.get("overflowing") or [])
    page_overflow = max(
        int(metrics.get("bodyScrollWidth") or 0),
        int(metrics.get("documentScrollWidth") or 0),
    ) > int(metrics.get("viewportWidth") or 1280) + 1

    checks = {
        "developerTermsHidden": {"pass": not forbidden_terms, "terms": forbidden_terms},
        "rawJsonHidden": {"pass": not raw_json_terms, "terms": raw_json_terms},
        "abComparisonHidden": {"pass": not ab_terms, "terms": ab_terms},
        "koreanTextReadable": {"pass": not broken_text_terms, "terms": broken_text_terms},
        "noHorizontalOverflow": {"pass": not overflowing and not page_overflow, "overflowing": overflowing},
        "planningDeskVisible": {
            "pass": int(metrics.get("planningCases") or 0) > 0 or int(metrics.get("signalCards") or 0) > 0,
            "planningCases": metrics.get("planningCases") or 0,
            "conceptCards": metrics.get("conceptCards") or 0,
            "copyCards": metrics.get("copyCards") or 0,
            "signalCards": metrics.get("signalCards") or 0,
        },
        "signalCollectionActionsVisible": {
            "pass": int(metrics.get("signalJobButtons") or 0) >= 4,
            "signalJobButtons": metrics.get("signalJobButtons") or 0,
        },
        "signalRecommendationsVisible": {
            "pass": int(metrics.get("signalCards") or 0) == 0 or int(metrics.get("signalRecommendations") or 0) > 0,
            "signalRecommendations": metrics.get("signalRecommendations") or 0,
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
