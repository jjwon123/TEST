#!/usr/bin/env python3
"""Evaluate whether a local planning model may become the default generator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json
from services.llm.promotion import evaluate_local_promotion


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="JSON with a comparisons array")
    parser.add_argument("--output", type=Path, default=ROOT / ".tmp" / "model-benchmarks" / "local-promotion.json")
    parser.add_argument("--minimum-ratio", type=float, default=0.8)
    args = parser.parse_args()
    payload = read_json(args.input.resolve(), default={})
    report = evaluate_local_promotion(payload.get("comparisons", []), minimum_ratio=args.minimum_ratio)
    write_json(args.output.resolve(), report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["promotionStatus"] == "eligible" else 1


if __name__ == "__main__":
    raise SystemExit(main())
