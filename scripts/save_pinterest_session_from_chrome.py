"""Save Pinterest cookies from a manually opened Chrome remote-debugging session."""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "assets" / "references" / "pinterest-storage-state.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Save Pinterest login state from Chrome on port 9222.")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    parser.add_argument("--out", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(args.cdp_url)
        contexts = browser.contexts
        if not contexts:
            raise RuntimeError("No Chrome context found. Open Chrome from chrome_pinterest_login.bat first.")
        context = contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        if "pinterest." not in page.url:
            page.goto("https://www.pinterest.com/", wait_until="domcontentloaded", timeout=60_000)
        context.storage_state(path=str(args.out))
        browser.close()

    print(f"Saved Pinterest session: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

