#!/usr/bin/env python3
"""검수 라벨로 '취향 모델'(OpenCLIP 임베딩 + 분류기)을 학습·평가·저장한다.

기원님 목적: 경쟁 브랜드 마케팅 이미지를 학습해 좋은 마케팅/브랜딩을 체화.
여러 검수 세션의 selected/rejected 라벨을 모아 CLIP 임베딩 위 분류기를 학습하고,
교차검증 ROC AUC로 효과를 측정한 뒤 모델을 저장한다.

사용:
    python scripts/train_taste_model.py                       # 모든 검수 세션
    python scripts/train_taste_model.py --include-shortlist   # shortlist도 good으로
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import write_json, write_text
from services.visual_reference.clip_ranker import ClipEmbedder, read_embedding_cache, write_embedding_cache
from services.visual_reference.taste_labels import gather_labeled_examples


def _embeddings(image_paths: list[Path], cache_path: Path) -> np.ndarray:
    if cache_path.exists():
        cached, embeddings = read_embedding_cache(cache_path)
        if cached == image_paths:
            return embeddings
    embeddings = ClipEmbedder().embed_images(image_paths)
    write_embedding_cache(cache_path, image_paths, embeddings)
    return embeddings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-shortlist", action="store_true", help="shortlist도 good(1)으로 포함.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".tmp" / "taste-model")
    parser.add_argument("--model-path", type=Path, default=ROOT / ".tmp" / "taste-model" / "taste-classifier.joblib")
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    examples = gather_labeled_examples(include_shortlist=args.include_shortlist)
    if not examples:
        print("라벨된 예시가 없습니다.")
        return 1
    labels = np.array([ex.label for ex in examples])
    if len(set(labels.tolist())) < 2:
        print("good/bad 라벨이 모두 필요합니다.")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    image_paths = [ex.file for ex in examples]
    embeddings = _embeddings(image_paths, args.output_dir / "embeddings.npz")

    model = Pipeline([
        ("scale", StandardScaler()),
        ("model", LogisticRegression(class_weight="balanced", max_iter=1000)),
    ])
    folds = max(2, min(args.folds, int(np.bincount(labels).min())))
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=20260620)
    cv_scores = cross_val_predict(model, embeddings, labels, cv=splitter, method="predict_proba")[:, 1]
    baseline = float(labels.mean())
    order = np.argsort(-cv_scores)
    top_k = min(10, len(examples))
    top_precision = float(labels[order[:top_k]].mean())

    # 최종 모델은 전체 라벨로 학습해 저장(운영 사용용).
    model.fit(embeddings, labels)
    joblib.dump(model, args.model_path)

    by_session: dict[str, int] = {}
    for ex in examples:
        by_session[ex.session] = by_session.get(ex.session, 0) + 1

    report = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "evaluation": "good_vs_bad_stratified_cv",
        "includeShortlist": args.include_shortlist,
        "examples": len(examples),
        "good": int(labels.sum()),
        "bad": int(len(labels) - labels.sum()),
        "sessions": by_session,
        "folds": folds,
        "metrics": {
            "baselineGoodRate": round(baseline, 4),
            "rocAuc": round(float(roc_auc_score(labels, cv_scores)), 4),
            "averagePrecision": round(float(average_precision_score(labels, cv_scores)), 4),
            "topK": top_k,
            "topKGoodPrecision": round(top_precision, 4),
            "topKLiftVsBaseline": round(top_precision / baseline, 4) if baseline else 0,
        },
        "modelPath": str(args.model_path),
    }
    report["status"] = "pass" if report["metrics"]["rocAuc"] > 0.5 and top_precision > baseline else "no_measured_improvement"
    write_json(args.output_dir / "taste-model-report.json", report)
    write_text(args.output_dir / "taste-model-report.md", _markdown(report))
    print(f"examples={len(examples)} good={int(labels.sum())} bad={int(len(labels)-labels.sum())} "
          f"rocAuc={report['metrics']['rocAuc']} top{top_k}Lift={report['metrics']['topKLiftVsBaseline']}x "
          f"status={report['status']}")
    print(f"model -> {args.model_path}")
    return 0 if report["status"] == "pass" else 2


def _markdown(report: dict) -> str:
    m = report["metrics"]
    lines = [
        "# Taste Model (OpenCLIP + classifier)",
        "",
        f"- Status: `{report['status']}`",
        f"- Examples: {report['examples']} (good {report['good']}, bad {report['bad']})",
        f"- ROC AUC: {m['rocAuc']}",
        f"- Average precision: {m['averagePrecision']}",
        f"- Baseline good rate: {m['baselineGoodRate']}",
        f"- Top-{m['topK']} good precision: {m['topKGoodPrecision']} (lift {m['topKLiftVsBaseline']}x)",
        f"- Model: `{report['modelPath']}`",
        "",
        "## Sessions",
        "",
    ]
    lines.extend(f"- {name}: {count}" for name, count in sorted(report["sessions"].items()))
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
