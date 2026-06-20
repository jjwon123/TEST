#!/usr/bin/env python3
"""Collect and Qwen-review under-measured Meta product/ingredient queries."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ad_reference.source_mix_metrics import source_mix_summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--query-limit", type=int, default=2)
    parser.add_argument("--ads-per-query", type=int, default=5)
    parser.add_argument("--scrolls", type=int, default=5)
    args = parser.parse_args()

    before = source_mix_summary()
    queries = args.query or [item["query"] for item in before.get("collectionPlan", [])[: max(1, args.query_limit)]]
    if not queries:
        print("META_SOURCE_MIX_COLLECT no_queries")
        return 0

    results = []
    for query in queries:
        command = [
            sys.executable,
            str(ROOT / "scripts" / "collect_meta_ads.py"),
            "--query", query,
            "--limit", str(max(1, args.ads_per_query)),
            "--scrolls", str(max(0, args.scrolls)),
            "--headless",
            "--qwen",
            "--qwen-limit", str(max(5, args.ads_per_query * 5)),
            "--creative-profile", "product_visual",
        ]
        process = subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
        results.append({"query": query, "returncode": process.returncode, "stdout": process.stdout[-2000:], "stderr": process.stderr[-2000:]})
    after = source_mix_summary()
    output = ROOT / ".tmp" / "meta-source-mix" / "latest-collection.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"queries": queries, "results": results, "before": before, "after": after}, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = sum(item["returncode"] != 0 for item in results)
    print(f"META_SOURCE_MIX_COLLECT {'warning' if failed else 'pass'} queries={len(queries)} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
