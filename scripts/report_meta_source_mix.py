#!/usr/bin/env python3
"""Write the Meta query-source fallback metrics report."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ad_reference.source_mix_metrics import source_mix_summary


def main() -> int:
    report = source_mix_summary()
    output = ROOT / ".tmp" / "meta-source-mix"
    output.mkdir(parents=True, exist_ok=True)
    (output / "latest-meta-source-mix.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"META_SOURCE_MIX {report['status']} reviewed={report['reviewedMedia']} clean={report['cleanProductVisuals']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
