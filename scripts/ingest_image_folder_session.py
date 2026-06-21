#!/usr/bin/env python3
"""임의 이미지 폴더를 콘솔에서 라벨 가능한 판단 훈련 세션으로 만든다.

Meta 수집 폴더, Chrome 확장으로 긁은 고품질 보드 등 아무 이미지 폴더를 받아
design_brain_wiki/training_sessions/<profile>/<session_id>/ 세션으로 변환한다.
콘솔 '판단 훈련' 탭에서 good/bad 라벨 후, train_taste_model.py가 학습 연료로 사용한다.

사용:
    python scripts/ingest_image_folder_session.py <이미지폴더> --session-id board_001
    python scripts/ingest_image_folder_session.py <Meta수집폴더> --session-id meta_serum_001
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TRAINING_ROOT = ROOT / "design_brain_wiki" / "training_sessions"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _list_images(image_dir: Path) -> list[Path]:
    return sorted(
        p for p in image_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )


def build_folder_session(
    image_dir: Path,
    *,
    profile: str,
    session_id: str,
    source_type: str = "folder_import",
    exclude_from_training: bool = False,
    training_root: Path = TRAINING_ROOT,
    root: Path = ROOT,
) -> dict:
    images = _list_images(image_dir)
    if not images:
        raise ValueError(f"이미지를 찾지 못했습니다: {image_dir}")
    session_dir = training_root / profile / session_id
    refs = session_dir / "references"
    refs.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    items = []
    for index, src in enumerate(images, start=1):
        dest_name = f"{index:03d}_{src.name}"
        dest = refs / dest_name
        shutil.copy2(src, dest)
        items.append({
            "id": f"{profile}_folder_{index:03d}",
            "file": str(dest.relative_to(root)).replace("\\", "/"),
            "sourceType": source_type,
            "sourceSplit": "folder_import",
            "category": "unscored",
            # 폴더 임포트는 AI 사전판단이 없으므로 중립(shortlist)에서 시작.
            "decision": "shortlist",
            "confidence": 0.0,
            "reason": "폴더 임포트 이미지. 콘솔에서 good/bad 판단해 주세요.",
            "referenceRole": [],
            "usableElements": [],
            "riskSignals": [],
            "wikiSources": [],
            "seniorDesignerFeedback": "",
            "kiwonReview": {"agree": "", "disagree": "", "unsure": "", "correctDecision": "", "kiwonReason": "", "ruleToUpdate": ""},
        })

    judgement = {
        "sessionId": session_id,
        "sessionType": "folder_import",
        "createdAt": now,
        "profile": profile,
        "purpose": "임의 이미지 폴더 라벨링 → 취향 모델 학습 연료",
        "sourceFolder": str(image_dir),
        "excludeFromTraining": bool(exclude_from_training),
        "summary": {
            "total": len(items),
            "decisionCounts": dict(Counter(it["decision"] for it in items)),
            "sessionType": "folder_import",
        },
        "items": items,
    }
    (session_dir / "ai_judgement.json").write_text(
        json.dumps(judgement, ensure_ascii=False, indent=2), encoding="utf-8")
    (session_dir / "kiwon_review_state.json").write_text(
        json.dumps({"reviews": {}, "profile": profile, "sessionId": session_id}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return {"session_dir": str(session_dir), "profile": profile, "session_id": session_id, "images": len(items)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image_dir", type=Path, help="이미지 폴더 (Meta 수집/확장 보드 등)")
    parser.add_argument("--profile", default="cosmetics_skincare")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--source-type", default="folder_import")
    parser.add_argument("--exclude-from-training", action="store_true", help="노이즈성 임포트: 라벨링은 하되 취향 모델 학습에서는 제외.")
    args = parser.parse_args()

    result = build_folder_session(
        args.image_dir, profile=args.profile, session_id=args.session_id,
        source_type=args.source_type, exclude_from_training=args.exclude_from_training)
    print(result)
    print(f"콘솔 판단 훈련에서 '{args.profile}/{args.session_id}' 라벨 후 train_taste_model.py 재실행")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
