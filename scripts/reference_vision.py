"""CLI for reference image ranking and Qwen-VL review."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.visual_reference.clip_ranker import (
    ClipEmbedder,
    rank_candidates,
    read_embedding_cache,
    train_classifier,
    write_embedding_cache,
    list_images,
)
from services.visual_reference.qwen_reviewer import DEFAULT_HOST, DEFAULT_MODEL, review_image


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank and review visual reference candidates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health")
    health.add_argument("--host", default=DEFAULT_HOST)

    embed = subparsers.add_parser("embed")
    embed.add_argument("--images", required=True, type=Path)
    embed.add_argument("--cache", required=True, type=Path)

    train = subparsers.add_parser("train")
    train.add_argument("--cache", required=True, type=Path)
    train.add_argument("--feedback", required=True, type=Path)
    train.add_argument("--model-path", required=True, type=Path)

    rank = subparsers.add_parser("rank")
    rank.add_argument("--cache", required=True, type=Path)
    rank.add_argument("--output", required=True, type=Path)
    rank.add_argument("--model-path", type=Path)
    rank.add_argument("--positive-reference-dir", type=Path)
    rank.add_argument("--top-k", type=int, default=20)

    review = subparsers.add_parser("review")
    review.add_argument("--ranked", required=True, type=Path)
    review.add_argument("--output", required=True, type=Path)
    review.add_argument("--model", default=DEFAULT_MODEL)
    review.add_argument("--host", default=DEFAULT_HOST)
    review.add_argument("--limit", type=int, default=10)

    feedback = subparsers.add_parser("feedback-from-table")
    feedback.add_argument("--table", required=True, type=Path)
    feedback.add_argument("--output", default=ROOT / "assets" / "references" / "feedback.jsonl", type=Path)
    feedback.add_argument("--decision-field", default="human_decision")
    feedback.add_argument("--score-field", default="human_score")
    feedback.add_argument("--notes-field", default="human_notes")
    feedback.add_argument("--include-ai-decisions", action="store_true", help="Use review_decision/review_score when human fields are blank.")

    args = parser.parse_args()
    if args.command == "health":
        return _health(args.host)
    if args.command == "embed":
        return _embed(args.images, args.cache)
    if args.command == "train":
        return _print_json(train_classifier(args.cache, args.feedback, args.model_path))
    if args.command == "rank":
        ranked = rank_candidates(
            args.cache,
            args.output,
            model_path=args.model_path,
            positive_reference_dir=args.positive_reference_dir,
            top_k=args.top_k,
        )
        return _print_json({"output": str(args.output), "ranked": len(ranked)})
    if args.command == "review":
        return _review(args.ranked, args.output, args.model, args.host, args.limit)
    if args.command == "feedback-from-table":
        return _feedback_from_table(
            args.table,
            args.output,
            decision_field=args.decision_field,
            score_field=args.score_field,
            notes_field=args.notes_field,
            include_ai_decisions=args.include_ai_decisions,
        )
    return 1


def _health(host: str) -> int:
    import requests
    import torch
    import open_clip
    import sklearn

    try:
        tags = requests.get(f"{host}/api/tags", timeout=10).json()
        ollama_status = "ok"
        ollama_models = [item["name"] for item in tags.get("models", [])]
    except requests.RequestException as exc:
        ollama_status = f"offline: {exc.__class__.__name__}"
        ollama_models = []
    return _print_json(
        {
            "torch": torch.__version__,
            "cuda": torch.cuda.is_available(),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
            "open_clip": getattr(open_clip, "__version__", "installed"),
            "sklearn": sklearn.__version__,
            "ollama_status": ollama_status,
            "ollama_models": ollama_models,
        }
    )


def _embed(images: Path, cache: Path) -> int:
    image_paths = list_images(images)
    embedder = ClipEmbedder()
    embeddings = embedder.embed_images(image_paths)
    write_embedding_cache(cache, image_paths, embeddings)
    return _print_json({"cache": str(cache), "images": len(image_paths), "shape": list(embeddings.shape)})


def _review(ranked_path: Path, output_path: Path, model: str, host: str, limit: int) -> int:
    ranked = json.loads(ranked_path.read_text(encoding="utf-8-sig")).get("ranked", [])
    reviews: list[dict[str, Any]] = []
    for item in ranked[:limit]:
        reviews.append(review_image(Path(item["file"]), model=model, host=host))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"reviews": reviews}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return _print_json({"output": str(output_path), "reviews": len(reviews)})


def _feedback_from_table(
    table_path: Path,
    output_path: Path,
    *,
    decision_field: str,
    score_field: str,
    notes_field: str,
    include_ai_decisions: bool = False,
) -> int:
    rows = _read_table_rows(table_path)
    existing_keys = _read_feedback_keys(output_path)
    records: list[dict[str, Any]] = []
    skipped_duplicates = 0
    for row in rows:
        decision = str(row.get(decision_field, "")).strip()
        score = row.get(score_field, "")
        notes = row.get(notes_field, "")
        source_type = "human"
        if not decision and include_ai_decisions:
            decision = str(row.get("review_decision", "")).strip()
            score = row.get("review_score", "")
            notes = row.get("ai_reason", "")
            source_type = "ai"
        if not decision:
            continue
        file_value = row.get("image_path") or row.get("file") or row.get("relative_path") or ""
        key = (str(file_value), decision, source_type)
        if key in existing_keys:
            skipped_duplicates += 1
            continue
        record = {
            "file": file_value,
            "candidate_id": row.get("asset_id") or row.get("candidate_id") or "",
            "decision": decision,
            "score": score,
            "notes": notes,
            "tags": _split_tags(str(row.get("feedback_tags", ""))),
            "ai_positive_tags": _split_tags(str(row.get("ai_positive_tags", ""))),
            "ai_negative_tags": _split_tags(str(row.get("ai_negative_tags", ""))),
            "case_id": row.get("case_id", ""),
            "query": row.get("query", ""),
            "source": str(table_path),
            "source_type": source_type,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        records.append(record)
        existing_keys.add(key)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return _print_json({"output": str(output_path), "appended": len(records), "skipped_duplicates": skipped_duplicates})


def _read_feedback_keys(output_path: Path) -> set[tuple[str, str, str]]:
    if not output_path.exists():
        return set()
    keys: set[tuple[str, str, str]] = set()
    with output_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            keys.add((
                str(record.get("file", "")),
                str(record.get("decision", "")),
                str(record.get("source_type", "human")),
            ))
    return keys


def _read_table_rows(table_path: Path) -> list[dict[str, Any]]:
    if table_path.suffix.lower() == ".json":
        payload = json.loads(table_path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            rows = payload.get("rows", [])
        else:
            rows = payload
        return [row for row in rows if isinstance(row, dict)]
    with table_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _split_tags(value: str) -> list[str]:
    return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]


def _print_json(data: dict[str, Any]) -> int:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
