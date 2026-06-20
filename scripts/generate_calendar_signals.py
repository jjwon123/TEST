"""계절/캘린더 MarketingSignal을 생성해 검수 큐에 추가한다.

사용:
    python scripts/generate_calendar_signals.py            # 이번 달
    python scripts/generate_calendar_signals.py --month 6  # 특정 달
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.marketing_intelligence.calendar_signals import generate_calendar_signals
from services.marketing_intelligence.repository import SIGNALS_PATH, append_signals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", type=int, default=datetime.now().month, help="1-12. 기본은 이번 달.")
    parser.add_argument("--industry", default="cosmetics_skincare")
    parser.add_argument("--signals-path", type=Path, default=SIGNALS_PATH)
    args = parser.parse_args()

    signals = generate_calendar_signals(args.month, industry=args.industry)
    result = append_signals(signals, args.signals_path)
    print({"month": args.month, "generated": len(signals), **result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
