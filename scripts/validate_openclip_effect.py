#!/usr/bin/env python3
"""Measure whether OpenCLIP feedback ranking improves held-out selections."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--session",
        type=Path,
        default=ROOT / "design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".tmp/openclip-effect")
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    session = args.session.resolve()
    output_dir = args.output_dir.resolve()
    judgement = read_json(session / "ai_judgement.json")
    reviews = read_json(session / "kiwon_review_state.json").get("reviews", {})
    examples = []
    for item in judgement.get("items", []):
        decision = str(reviews.get(item["id"], {}).get("correctDecision") or "")
        if decision not in {"selected", "rejected"}:
            continue
        image_path = (ROOT / str(item.get("file") or "")).resolve()
        if image_path.exists():
            examples.append({"id": item["id"], "file": image_path, "decision": decision})

    labels = np.array([1 if item["decision"] == "selected" else 0 for item in examples])
    if len(set(labels.tolist())) < 2:
        raise ValueError("Need both selected and rejected human decisions.")

    cache_path = output_dir / "meta_brand_review_001_embeddings.npz"
    image_paths = [item["file"] for item in examples]
    if cache_path.exists():
        cached_paths, embeddings = read_embedding_cache(cache_path)
        if cached_paths != image_paths:
            embeddings = embed_and_cache(image_paths, cache_path)
    else:
        embeddings = embed_and_cache(image_paths, cache_path)

    folds = min(args.folds, int(np.bincount(labels).min()))
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", LogisticRegression(class_weight="balanced", max_iter=1000)),
        ]
    )
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=20260613)
    scores = cross_val_predict(model, embeddings, labels, cv=splitter, method="predict_proba")[:, 1]
    order = np.argsort(-scores)
    top_k = min(10, len(examples))
    top_precision = float(labels[order[:top_k]].mean())
    baseline = float(labels.mean())
    report = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "session": str(session),
        "evaluation": "selected_vs_rejected_stratified_holdout",
        "examples": len(examples),
        "selected": int(labels.sum()),
        "rejected": int(len(labels) - labels.sum()),
        "folds": folds,
        "metrics": {
            "baselineSelectedRate": round(baseline, 4),
            "rocAuc": round(float(roc_auc_score(labels, scores)), 4),
            "averagePrecision": round(float(average_precision_score(labels, scores)), 4),
            "topK": top_k,
            "topKSelectedPrecision": round(top_precision, 4),
            "topKLiftVsBaseline": round(top_precision / baseline, 4) if baseline else 0,
        },
        "topRanked": [
            {
                "rank": rank + 1,
                "id": examples[index]["id"],
                "decision": examples[index]["decision"],
                "score": round(float(scores[index]), 6),
                "file": str(examples[index]["file"]),
            }
            for rank, index in enumerate(order[:top_k])
        ],
    }
    report["status"] = (
        "pass"
        if report["metrics"]["rocAuc"] > 0.5 and report["metrics"]["topKSelectedPrecision"] > baseline
        else "no_measured_improvement"
    )
    write_json(output_dir / "openclip-effect-report.json", report)
    write_text(output_dir / "openclip-effect-report.md", render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 2


def embed_and_cache(image_paths: list[Path], cache_path: Path) -> np.ndarray:
    embeddings = ClipEmbedder().embed_images(image_paths)
    write_embedding_cache(cache_path, image_paths, embeddings)
    return embeddings


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def render_markdown(report: dict) -> str:
    metrics = report["metrics"]
    lines = [
        "# OpenCLIP Holdout Effect",
        "",
        f"- Status: `{report['status']}`",
        f"- Examples: {report['examples']} (`selected` {report['selected']}, `rejected` {report['rejected']})",
        f"- ROC AUC: {metrics['rocAuc']}",
        f"- Average precision: {metrics['averagePrecision']}",
        f"- Baseline selected rate: {metrics['baselineSelectedRate']}",
        f"- Top-{metrics['topK']} selected precision: {metrics['topKSelectedPrecision']}",
        f"- Top-{metrics['topK']} lift: {metrics['topKLiftVsBaseline']}x",
        "",
        "## Top Ranked",
        "",
        "| Rank | ID | Human decision | Score |",
        "| ---: | --- | --- | ---: |",
    ]
    lines.extend(
        f"| {item['rank']} | `{item['id']}` | {item['decision']} | {item['score']} |"
        for item in report["topRanked"]
    )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
