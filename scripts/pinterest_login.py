"""Save a local Pinterest login session for private board collection."""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "assets" / "references" / "pinterest-storage-state.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Open Pinterest login and save Playwright storage state.")
    parser.add_argument("--out", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--browser-channel", default="chrome")
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.browser_channel, headless=False)
        context = browser.new_context(viewport={"width": 1400, "height": 1000})
        page = context.new_page()
        page.goto("https://www.pinterest.com/login/", wait_until="domcontentloaded", timeout=60_000)
        print("")
        print("Pinterest login window opened.")
        print("1. Log in normally in the browser window.")
        print("2. Open your target board once if Pinterest asks for anything.")
        print("3. Come back here and press Enter.")
        input("")
        context.storage_state(path=str(args.out))
        browser.close()
    print(f"Saved Pinterest session: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
