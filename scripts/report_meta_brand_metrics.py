#!/usr/bin/env python3
"""Write an operational metrics report for Meta known-brand batches."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ad_reference.registry_metrics import collection_metrics_summary


def main() -> int:
    report = collection_metrics_summary()
    output = ROOT / ".tmp" / "meta-brand-metrics"
    output.mkdir(parents=True, exist_ok=True)
    (output / "latest-meta-brand-metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output / "latest-meta-brand-metrics.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"META_BRAND_METRICS {report['status']} batches={report['batchCount']}")
    return 0


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Meta Brand Collection Metrics", "", f"- Status: `{report['status']}`", f"- Batches: {report['batchCount']}", ""]
    for profile, batch in report["latestByProfile"].items():
        rates = batch["rates"]
        lines.extend([
            f"## {profile}",
            "",
            f"- Batch: `{batch['batchId']}`",
            f"- Advertiser match: `{percent(rates['advertiserMatchRate'])}`",
            f"- Creative acceptance: `{percent(rates['creativeAcceptanceRate'])}`",
            f"- Brand coverage: `{percent(rates['brandCoverageRate'])}`",
            f"- Top-brand share: `{percent(rates['topBrandShare'])}`",
            f"- Accepted images: `{batch['summary']['acceptedImages']}`",
            "",
        ])
    lines.append("## Warnings")
    lines.append("")
    lines.extend(f"- **{item['profile']} / {item['code']}**: {item['message']}" for item in report["warnings"])
    if not report["warnings"]:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def percent(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
