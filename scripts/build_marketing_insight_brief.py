#!/usr/bin/env python3
"""Build an InsightBrief from selected MarketingSignal records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.marketing_intelligence.insight_brief import INSIGHT_BRIEF_PATH, build_and_save_insight_brief  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-id", default="general")
    parser.add_argument("--industry", default="cosmetics_skincare", choices=["cosmetics_skincare", "jewelry_luxury"])
    parser.add_argument("--topic", default="")
    parser.add_argument("--minimum-selected", type=int, default=3)
    parser.add_argument("--output", type=Path, default=INSIGHT_BRIEF_PATH)
    args = parser.parse_args()

    brief = build_and_save_insight_brief(
        event_id=args.event_id,
        industry=args.industry,
        topic=args.topic,
        minimum_selected=max(1, args.minimum_selected),
        output=args.output.resolve(),
    )
    print(json.dumps({"output": str(args.output), "brief": brief}, ensure_ascii=False))
    return 0 if brief.get("status") == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
