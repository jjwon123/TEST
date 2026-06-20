#!/usr/bin/env python3
"""학습된 취향 모델로 신규 수집 이미지를 점수·순위 매긴다.

train_taste_model.py가 저장한 분류기를 임의의 이미지 폴더에 적용해, 좋은 마케팅/브랜딩
이미지일 확률(취향 점수)로 순위를 낸다. 신규 경쟁사 수집물에서 참고할 만한 것만 빠르게
추리는 용도.

사용:
    python scripts/rank_images_by_taste.py <이미지폴더> --top-k 30
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.visual_reference.clip_ranker import (
    ClipEmbedder,
    list_images,
    rank_candidates,
    write_embedding_cache,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image_dir", type=Path, help="순위를 매길 이미지 폴더")
    parser.add_argument("--model-path", type=Path, default=ROOT / ".tmp" / "taste-model" / "taste-classifier.joblib")
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--output", type=Path, default=ROOT / ".tmp" / "taste-model" / "ranked-new-images.json")
    parser.add_argument("--cache", type=Path, default=ROOT / ".tmp" / "taste-model" / "rank-embeddings.npz")
    args = parser.parse_args()

    if not args.model_path.exists():
        print(f"모델이 없습니다: {args.model_path}. 먼저 train_taste_model.py를 실행하세요.")
        return 1
    images = list_images(args.image_dir)
    if not images:
        print(f"이미지를 찾지 못했습니다: {args.image_dir}")
        return 1

    embeddings = ClipEmbedder().embed_images(images)
    write_embedding_cache(args.cache, images, embeddings)
    ranked = rank_candidates(args.cache, args.output, model_path=args.model_path, top_k=args.top_k)

    print(f"scored={len(images)} top_k={len(ranked)} -> {args.output}")
    for row in ranked[:10]:
        print(f"  {row['rank']:>2}. score={row['score']:>6}  {Path(row['file']).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
