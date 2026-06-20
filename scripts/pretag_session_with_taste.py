#!/usr/bin/env python3
"""학습된 취향 모델로 훈련 세션에 AI 1차 추천(decision)을 미리 붙인다.

폴더 임포트 세션은 결정이 전부 중립(shortlist)이라 사람이 맨땅에서 판단해야 한다.
이 스크립트가 저장된 취향 분류기로 각 이미지에 점수를 매겨 selected/shortlist/rejected
추천을 채워 넣으면, 콘솔에서 '맞다/틀리다'만 누르는 빠른 교정이 가능해진다(AI 제안→사람 교정).

사용:
    python scripts/pretag_session_with_taste.py --profile cosmetics_skincare --session-id meta_serum_test_001
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TRAINING_ROOT = ROOT / "design_brain_wiki" / "training_sessions"


def taste_decision(score: float, *, selected_min: float = 55.0, shortlist_min: float = 25.0) -> str:
    """취향 점수(0-100)를 결정 추천으로 매핑."""
    if score >= selected_min:
        return "selected"
    if score >= shortlist_min:
        return "shortlist"
    return "rejected"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="cosmetics_skincare")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--model-path", type=Path, default=ROOT / ".tmp" / "taste-model" / "taste-classifier.joblib")
    parser.add_argument("--selected-min", type=float, default=55.0)
    parser.add_argument("--shortlist-min", type=float, default=25.0)
    args = parser.parse_args()

    if not args.model_path.exists():
        print(f"모델이 없습니다: {args.model_path}. 먼저 train_taste_model.py 실행.")
        return 1
    session_dir = TRAINING_ROOT / args.profile / args.session_id
    judgement_path = session_dir / "ai_judgement.json"
    if not judgement_path.exists():
        print(f"세션이 없습니다: {judgement_path}")
        return 1

    import joblib
    from services.visual_reference.clip_ranker import ClipEmbedder

    judgement = json.loads(judgement_path.read_text(encoding="utf-8"))
    items = judgement.get("items", [])
    image_paths = [ROOT / str(item.get("file") or "") for item in items]
    valid = [(i, p) for i, p in enumerate(image_paths) if p.exists()]
    if not valid:
        print("세션 이미지가 없습니다.")
        return 1

    embeddings = ClipEmbedder().embed_images([p for _, p in valid])
    classifier = joblib.load(args.model_path)
    scores = classifier.predict_proba(embeddings)[:, 1] * 100

    counts = {"selected": 0, "shortlist": 0, "rejected": 0}
    for (item_index, _), score in zip(valid, scores):
        decision = taste_decision(float(score), selected_min=args.selected_min, shortlist_min=args.shortlist_min)
        counts[decision] += 1
        item = items[item_index]
        item["decision"] = decision
        item["confidence"] = round(float(score) / 100, 4)
        item["reason"] = f"취향 모델 점수 {float(score):.1f}/100 기반 AI 추천. 콘솔에서 맞다/틀리다로 교정해 주세요."
        item["tasteScore"] = round(float(score), 2)

    judgement["pretaggedBy"] = "taste-model"
    judgement_path.write_text(json.dumps(judgement, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"pretagged {len(valid)} items -> selected {counts['selected']} / shortlist {counts['shortlist']} / rejected {counts['rejected']}")
    print(f"세션: {args.profile}/{args.session_id} — 콘솔 판단 훈련에서 교정하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
