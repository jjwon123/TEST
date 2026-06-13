#!/usr/bin/env python3
"""Collect diverse Pinterest search references for the 1,000-image learning dataset."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.reference_collector.pinterest import CollectorOptions, collect_pinterest_board


QUERY_GROUPS = {
    "cosmetics_skincare": [
        "Korean skincare promotion banner design",
        "cosmetic serum product campaign layout",
        "beauty sale card news design Korea",
        "skincare ingredient benefit infographic ad",
        "clean cosmetic product photography campaign",
        "olive young beauty sale promotion design",
    ],
    "bullion_investment": [
        "premium gold investment campaign design",
        "wealth management consultation advertising layout",
        "gold bar luxury product photography",
        "financial education card news design",
    ],
    "jewelry_luxury": [
        "luxury jewelry campaign layout",
        "diamond product advertising photography",
        "fine jewelry editorial campaign design",
        "premium watch jewelry promotion banner",
    ],
    "promotion_layout": [
        "Korean retail promotion card news layout",
        "benefit hierarchy sale banner design",
        "event promotion social media carousel design",
        "product launch campaign layout design",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-query", type=int, default=30)
    parser.add_argument("--query-limit", type=int, default=0, help="0 means all queries.")
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--profile", choices=[*QUERY_GROUPS, "all"], default="all")
    args = parser.parse_args()

    queries = [
        (profile, query)
        for profile, profile_queries in QUERY_GROUPS.items()
        if args.profile in {"all", profile}
        for query in profile_queries
    ]
    if args.query_limit > 0:
        queries = queries[: args.query_limit]

    output_root = ROOT / "assets" / "references" / "inbox" / "reference-learning-1000"
    output_root.mkdir(parents=True, exist_ok=True)
    results = []
    for index, (profile, query) in enumerate(queries, start=1):
        source_id = f"{profile}__{safe_slug(query)}"
        output_dir = output_root / source_id
        url = f"https://www.pinterest.com/search/pins/?q={quote_plus(query)}"
        print(f"[{index}/{len(queries)}] {profile}: {query}", flush=True)
        try:
            summary = collect_pinterest_board(CollectorOptions(
                board_url=url,
                output_dir=output_dir,
                limit=max(1, args.per_query),
                scrolls=max(10, min(50, args.per_query // 2 + 10)),
                headless=not args.headful,
                browser_channel="chrome",
                storage_state=None,
                allow_page_fallback=True,
                request_delay=0.15,
            ))
            results.append({"profile": profile, "query": query, "sourceId": source_id, **summary})
        except Exception as exc:
            results.append({
                "profile": profile,
                "query": query,
                "sourceId": source_id,
                "downloaded": 0,
                "failed": 1,
                "error": f"{type(exc).__name__}: {exc}",
            })

    payload = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "queryCount": len(queries),
        "perQuery": args.per_query,
        "downloaded": sum(int(item.get("downloaded", 0) or 0) for item in results),
        "duplicates": sum(int(item.get("duplicates", 0) or 0) for item in results),
        "failedQueries": sum(bool(item.get("error")) for item in results),
        "results": results,
    }
    (output_root / "collection-summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "results"}, ensure_ascii=False, indent=2))
    return 0 if not payload["failedQueries"] else 1


def safe_slug(value: str) -> str:
    value = re.sub(r"\s+", "-", value.strip().lower())
    value = re.sub(r"[^a-z0-9가-힣_-]+", "", value)
    return value[:64].strip("-_") or "query"


if __name__ == "__main__":
    raise SystemExit(main())
