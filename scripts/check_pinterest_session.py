"""Check saved Pinterest login state and optionally probe a board URL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "assets" / "references" / "pinterest-storage-state.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Pinterest storage-state and board accessibility.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE, help="Playwright storage-state JSON.")
    parser.add_argument("--url", help="Optional Pinterest board/pin URL to probe with the saved session.")
    parser.add_argument("--browser-channel", default="chrome")
    parser.add_argument("--headful", action="store_true", help="Show browser while probing the URL.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON only.")
    args = parser.parse_args()

    report = {"state": inspect_state(args.state)}
    if args.url:
        report["probe"] = probe_url(
            args.url,
            state_path=args.state,
            browser_channel=args.browser_channel,
            headless=not args.headful,
        )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human_report(report)

    return 0 if report.get("state", {}).get("usable") and report.get("probe", {}).get("accessible", True) else 1


def inspect_state(state_path: Path) -> dict[str, Any]:
    state_path = state_path.resolve()
    state: dict[str, Any] = {
        "path": str(state_path),
        "exists": state_path.exists(),
        "usable": False,
        "cookie_count": 0,
        "pinterest_cookie_count": 0,
    }
    if not state_path.exists():
        state["error"] = "storage state file does not exist"
        return state
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        state["error"] = f"invalid JSON: {exc}"
        return state

    cookies = payload.get("cookies") if isinstance(payload, dict) else []
    if not isinstance(cookies, list):
        state["error"] = "storage state does not contain a cookies list"
        return state

    pinterest_cookies = [
        cookie for cookie in cookies
        if "pinterest." in str(cookie.get("domain", "")).lower()
    ]
    state["cookie_count"] = len(cookies)
    state["pinterest_cookie_count"] = len(pinterest_cookies)
    state["usable"] = bool(pinterest_cookies)
    return state


def probe_url(url: str, *, state_path: Path, browser_channel: str, headless: bool) -> dict[str, Any]:
    if not state_path.exists():
        return {
            "url": url,
            "accessible": False,
            "error": "storage state file does not exist",
        }

    feed_items: list[dict[str, Any]] = []
    board_errors: list[str] = []
    response_urls: list[str] = []
    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, browser_channel, headless=headless)
        try:
            context = browser.new_context(
                storage_state=str(state_path),
                viewport={"width": 1440, "height": 1200},
            )
            page = context.new_page()

            def on_response(response: Any) -> None:
                response_url = response.url
                if "BoardResource/get" in response_url or "BoardFeedResource/get" in response_url:
                    response_urls.append(response_url)
                if "BoardResource/get" in response_url:
                    error = _read_resource_error(response)
                    if error:
                        board_errors.append(error)
                if "BoardFeedResource/get" in response_url:
                    feed_items.extend(_read_feed_items(response))

            page.on("response", on_response)
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(3000)
            for _ in range(6):
                if feed_items or board_errors:
                    break
                page.mouse.wheel(0, 2200)
                page.wait_for_timeout(1200)

            title = page.title()
            visible_images = page.locator("img[src]").count()
            accessible = bool(feed_items) and not board_errors
            return {
                "url": url,
                "accessible": accessible,
                "title": title,
                "visible_images": visible_images,
                "board_error_count": len(board_errors),
                "board_errors": board_errors[:5],
                "feed_item_count": len(feed_items),
                "pinterest_resource_responses": len(response_urls),
            }
        except Exception as exc:
            return {
                "url": url,
                "accessible": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        finally:
            browser.close()


def _launch_browser(playwright: Any, browser_channel: str, *, headless: bool) -> Any:
    try:
        return playwright.chromium.launch(channel=browser_channel, headless=headless)
    except Exception:
        if browser_channel != "msedge":
            return playwright.chromium.launch(channel="msedge", headless=headless)
        raise


def _read_resource_error(response: Any) -> str:
    try:
        payload = response.json()
    except Exception:
        return ""
    error = payload.get("resource_response", {}).get("error")
    if not isinstance(error, dict):
        return ""
    status = error.get("http_status") or ""
    message = error.get("message") or "board error"
    return f"{status} {message}".strip()


def _read_feed_items(response: Any) -> list[dict[str, Any]]:
    try:
        payload = response.json()
    except Exception:
        return []
    data = payload.get("resource_response", {}).get("data")
    return _find_pin_dicts(data)


def _find_pin_dicts(value: Any) -> list[dict[str, Any]]:
    pins: list[dict[str, Any]] = []
    if isinstance(value, dict):
        images = value.get("images")
        if isinstance(images, dict) and (value.get("id") or value.get("grid_title")):
            pins.append(value)
        for child in value.values():
            pins.extend(_find_pin_dicts(child))
    elif isinstance(value, list):
        for child in value:
            pins.extend(_find_pin_dicts(child))
    return pins


def print_human_report(report: dict[str, Any]) -> None:
    state = report.get("state", {})
    print("Pinterest session")
    print("=" * 18)
    print(f"state file: {state.get('path')}")
    print(f"exists: {state.get('exists')}")
    print(f"pinterest cookies: {state.get('pinterest_cookie_count', 0)}")
    print(f"usable: {state.get('usable')}")
    if state.get("error"):
        print(f"state error: {state['error']}")

    probe = report.get("probe")
    if not probe:
        return
    print("")
    print("Board probe")
    print("=" * 11)
    print(f"url: {probe.get('url')}")
    print(f"accessible: {probe.get('accessible')}")
    print(f"feed items: {probe.get('feed_item_count', 0)}")
    print(f"visible images: {probe.get('visible_images', 0)}")
    print(f"resource responses: {probe.get('pinterest_resource_responses', 0)}")
    if probe.get("board_errors"):
        print("board errors:")
        for error in probe["board_errors"]:
            print(f"- {error}")
    if probe.get("error"):
        print(f"probe error: {probe['error']}")


if __name__ == "__main__":
    raise SystemExit(main())
