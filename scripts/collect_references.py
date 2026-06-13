"""Collect visual references from Pinterest boards into local folders."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.reference_collector.pinterest import CollectorOptions, collect_pinterest_board


DEFAULT_STATE = ROOT / "assets" / "references" / "pinterest-storage-state.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download reference images from a Pinterest board.")
    parser.add_argument("--url", required=True, help="Pinterest board URL.")
    parser.add_argument("--out", required=True, type=Path, help="Output folder for images and metadata.")
    parser.add_argument("--limit", type=int, default=200, help="Maximum images to process.")
    parser.add_argument("--scrolls", type=int, default=30, help="Maximum browser scroll rounds.")
    parser.add_argument("--browser-channel", default="chrome", help="Playwright browser channel, usually chrome or msedge.")
    parser.add_argument("--headful", action="store_true", help="Show the browser window while collecting.")
    parser.add_argument("--storage-state", type=Path, help="Optional Playwright storage state JSON for logged-in boards.")
    parser.add_argument("--dry-run", action="store_true", help="Collect URLs without downloading files.")
    parser.add_argument(
        "--allow-page-fallback",
        action="store_true",
        help="Fallback to visible page images when board feed API is unavailable. This can collect recommendations.",
    )
    args = parser.parse_args()

    storage_state = args.storage_state or (DEFAULT_STATE if DEFAULT_STATE.exists() else None)
    try:
        summary = collect_pinterest_board(
            CollectorOptions(
                board_url=args.url,
                output_dir=args.out,
                limit=args.limit,
                scrolls=args.scrolls,
                headless=not args.headful,
                browser_channel=args.browser_channel,
                storage_state=storage_state,
                dry_run=args.dry_run,
                allow_page_fallback=args.allow_page_fallback,
            )
        )
    except RuntimeError as exc:
        print(f"Collection failed: {exc}")
        print("If this is your private board, run pinterest_login.bat first, then try again.")
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
