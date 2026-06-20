"""올리브영 랭킹·리뷰 키워드 CSV를 MarketingSignal로 import한다.

CSV 포맷 (UTF-8, 헤더 필수):
    rank,brand,product,category,review_keywords
    1,브랜드A,수분세럼,세럼,"수분감, 흡수력, 끈적임 없음"

사용:
    python scripts/import_oliveyoung_ranking.py path/to/ranking.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.marketing_intelligence.oliveyoung_csv import parse_oliveyoung_ranking_csv
from services.marketing_intelligence.repository import SIGNALS_PATH, append_signals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="올리브영 랭킹/리뷰 CSV 경로")
    parser.add_argument("--industry", default="cosmetics_skincare")
    parser.add_argument("--topic", default="oliveyoung_ranking")
    parser.add_argument("--signals-path", type=Path, default=SIGNALS_PATH)
    args = parser.parse_args()

    if not args.csv.exists():
        print({"error": f"file not found: {args.csv}"})
        return 1
    signals = parse_oliveyoung_ranking_csv(args.csv, industry=args.industry, topic=args.topic)
    result = append_signals(signals, args.signals_path)
    print({"csv": str(args.csv), "parsed": len(signals), **result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
