#!/usr/bin/env python3
"""Build the cosmetics benchmark event evidence work queue."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.marketing_intelligence.evidence_queue import (  # noqa: E402
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
    DEFAULT_PLAN,
    build_and_save_evidence_queue,
)
from services.marketing_intelligence.repository import SIGNALS_PATH  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--signals", type=Path, default=SIGNALS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    queue = build_and_save_evidence_queue(
        output=args.output.resolve(),
        dataset_path=args.dataset.resolve(),
        plan_path=args.plan.resolve(),
        signals_path=args.signals.resolve(),
    )
    print(json.dumps(queue["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
