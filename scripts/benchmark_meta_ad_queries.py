#!/usr/bin/env python3
"""Compare Meta Ad Library query styles for an event category."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ad_reference.meta_collector import MetaCollectorOptions, collect_meta_ads


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", nargs="+", required=True)
    parser.add_argument("--country", default="KR")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--scrolls", type=int, default=0)
    parser.add_argument("--name", default="meta-query-benchmark")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    benchmark_dir = ROOT / "references" / "meta_ads" / "benchmarks" / f"{stamp}_{safe_slug(args.name)}"
    rows = []
    for index, query in enumerate(args.queries, 1):
        output_dir = benchmark_dir / f"{index:02d}_{safe_slug(query)}"
        payload = collect_meta_ads(MetaCollectorOptions(
            query=query,
            output_dir=output_dir,
            country=args.country,
            limit=max(1, args.limit),
            scrolls=max(0, args.scrolls),
            headless=True,
        ))
        rows.append(summarize(payload, output_dir))

    report = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "country": args.country,
        "limitPerQuery": args.limit,
        "queries": rows,
    }
    (benchmark_dir / "meta-query-benchmark.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (benchmark_dir / "meta-query-benchmark.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"output": str(benchmark_dir), "queries": rows}, ensure_ascii=False))
    return 0


def summarize(payload: dict, output_dir: Path) -> dict:
    items = payload.get("items", [])
    brands = [str(item.get("brand") or "").strip() for item in items if item.get("brand")]
    copy_text = " ".join(str(item.get("copy") or "") for item in items).lower()
    return {
        "query": payload.get("query", ""),
        "adCount": len(items),
        "downloadedImageCount": payload.get("downloadedImageCount", 0),
        "brands": brands,
        "ctaCount": sum(1 for item in items if item.get("cta")),
        "skincareSignalCount": sum(copy_text.count(term) for term in ["skincare", "skin", "스킨케어", "피부", "화장품", "cosmetic"]),
        "saleSignalCount": sum(copy_text.count(term) for term in ["sale", "discount", "할인", "세일", "무료배송", "free shipping"]),
        "ingredientSignalCount": sum(copy_text.count(term) for term in ["niacinamide", "나이아신아마이드", "vitamin", "retinol", "성분"]),
        "outputDir": str(output_dir.relative_to(ROOT)),
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Meta Ad Query Benchmark",
        "",
        "| Query | Ads | Images | CTA | Skincare | Sale | Ingredient | Brands |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report["queries"]:
        lines.append(
            f"| {row['query']} | {row['adCount']} | {row['downloadedImageCount']} | "
            f"{row['ctaCount']} | {row['skincareSignalCount']} | {row['saleSignalCount']} | "
            f"{row['ingredientSignalCount']} | {', '.join(row['brands'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def safe_slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^\w가-힣]+", "-", value.lower())).strip("-") or "query"


if __name__ == "__main__":
    raise SystemExit(main())
