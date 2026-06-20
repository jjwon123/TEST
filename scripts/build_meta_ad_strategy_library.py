#!/usr/bin/env python3
"""Build an abstract advertising strategy library from collected Meta ad copy."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ad_strategy.library import DEFAULT_LIBRARY_PATH, DEFAULT_SOURCE_ROOT, build_library, save_library


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_LIBRARY_PATH)
    args = parser.parse_args()
    payload = build_library(args.source_root.resolve())
    path = save_library(payload, args.output.resolve())
    print(f"AD_STRATEGY_LIBRARY records={payload['recordCount']} output={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
