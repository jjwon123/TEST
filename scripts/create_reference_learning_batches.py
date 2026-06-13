#!/usr/bin/env python3
"""Materialize master reference-learning review batches as console training sessions."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "design_brain_wiki" / "reference_learning_1000"
TRAINING_DIR = ROOT / "design_brain_wiki" / "training_sessions" / "reference_learning"
COMMON_WIKI_SOURCES = [
    "design_brain_wiki/00_JUDGE_SCHEMA.md",
    "design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json",
    "design_brain_wiki/03_reference_judgement/selected_criteria.md",
    "design_brain_wiki/03_reference_judgement/shortlist_criteria.md",
    "design_brain_wiki/03_reference_judgement/rejected_criteria.md",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", help="Materialize one batch. Omit to materialize all.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    dataset = read_json(DATASET_DIR / "dataset-index.json", {})
    items_by_id = {item["id"]: item for item in dataset.get("items", [])}
    batches = [
        batch for batch in dataset.get("batches", [])
        if not args.batch_id or batch["id"] == args.batch_id
    ]
    created = []
    skipped = []
    for batch in batches:
        session_dir = TRAINING_DIR / batch["id"]
        if session_dir.exists() and not args.force:
            skipped.append(batch["id"])
            continue
        if session_dir.exists():
            shutil.rmtree(session_dir)
        refs_dir = session_dir / "references"
        refs_dir.mkdir(parents=True, exist_ok=True)
        session_items = []
        for index, item_id in enumerate(batch["itemIds"], start=1):
            record = items_by_id.get(item_id)
            if not record:
                continue
            source = ROOT / record["path"]
            if not source.exists():
                continue
            filename = f"{index:03d}_{record['id']}{source.suffix.lower()}"
            copied = refs_dir / filename
            shutil.copy2(source, copied)
            session_items.append(build_item(record, copied, index))
        report = {
            "sessionId": f"reference_learning_{batch['id']}",
            "sessionType": "reference_learning_1000_batch",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "profile": "reference_learning",
            "purpose": "Human review batch from the deduplicated 1,000-image reference learning dataset.",
            "sourceRun": "design_brain_wiki/reference_learning_1000/dataset-index.json",
            "localModelUsed": False,
            "judgementMethod": "Existing AI judgement when available; otherwise conservative shortlist first pass.",
            "wikiSources": COMMON_WIKI_SOURCES,
            "summary": build_summary(session_items),
            "items": session_items,
        }
        write_json(session_dir / "ai_judgement.json", report)
        (session_dir / "README.md").write_text(render_readme(report), encoding="utf-8")
        created.append(batch["id"])
    print(json.dumps({"ok": True, "created": created, "skipped": skipped}, ensure_ascii=False, indent=2))
    return 0


def build_item(record: dict[str, Any], copied: Path, index: int) -> dict[str, Any]:
    risks = record.get("hardRejectReasons", []) or (["low_resolution"] if record.get("lowResolution") else [])
    decision = "rejected" if risks else record.get("aiDecision") or "shortlist"
    source = record.get("source", "other")
    return {
        "id": f"learning_ref_{record['sha256'][:12]}",
        "file": relative(copied),
        "sourcePath": record["path"],
        "sourceUrl": record.get("sourceUrl", ""),
        "sourceType": source,
        "sourceIsPinterest": source == "pinterest_search",
        "sourceIsMeta": source == "meta_ad_library",
        "sourceSplit": "reference_learning_1000",
        "category": record.get("profile", "general"),
        "decision": decision,
        "confidence": 0.75 if record.get("aiDecision") else 0.55,
        "reason": existing_reason(record, decision),
        "referenceRole": ["human_review_required"],
        "usableElements": ["사람 검수로 활용 범위 확정"],
        "riskSignals": risks,
        "referencePool": record.get("referencePool", "rejection_example" if risks else "creative_candidate"),
        "wikiSources": COMMON_WIKI_SOURCES,
        "seniorDesignerFeedback": "출처와 업종 맥락을 확인하고 selected, shortlist, rejected 중 하나로 교정합니다.",
        "kiwonReview": {
            "agree": "",
            "disagree": "",
            "unsure": "",
            "correctDecision": "",
            "kiwonReason": "",
            "ruleToUpdate": "",
        },
        "datasetId": record["id"],
        "datasetProfile": record.get("profile", "general"),
        "batchOrder": index,
    }


def existing_reason(record: dict[str, Any], decision: str) -> str:
    if record.get("aiDecision"):
        return f"기존 AI 판정 `{decision}`을 마스터 데이터셋에서 다시 검수합니다."
    if record.get("lowResolution"):
        return "짧은 변이 300px 미만의 저해상도 이미지라 초기 rejected로 분류했습니다."
    return "아직 AI 시각 판정이 없는 고유 이미지라 안전하게 shortlist에서 사람 검수를 기다립니다."


def build_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    decisions: dict[str, int] = {}
    sources: dict[str, int] = {}
    profiles: dict[str, int] = {}
    for item in items:
        decisions[item["decision"]] = decisions.get(item["decision"], 0) + 1
        sources[item["sourceType"]] = sources.get(item["sourceType"], 0) + 1
        profiles[item["datasetProfile"]] = profiles.get(item["datasetProfile"], 0) + 1
    return {
        "total": len(items),
        "decisionCounts": decisions,
        "sourceCounts": sources,
        "profileCounts": profiles,
        "needsKiwonReview": len(items),
    }


def render_readme(report: dict[str, Any]) -> str:
    summary = report["summary"]
    return "\n".join([
        f"# {report['sessionId']}",
        "",
        "1,000장 마스터 레퍼런스 데이터셋의 사람 검수 배치입니다.",
        "",
        f"- Total: {summary['total']}",
        f"- Sources: {summary['sourceCounts']}",
        f"- Profiles: {summary['profileCounts']}",
        f"- Initial decisions: {summary['decisionCounts']}",
        "",
    ])


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
