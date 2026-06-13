"""Create bullion_investment reference judgement training session 001."""

from __future__ import annotations

import json
import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "assets" / "reference_training" / "bullion_investment"
SESSION_ROOT = ROOT / "design_brain_wiki" / "training_sessions" / "bullion_investment"

WIKI_SOURCES = [
    "design_brain_wiki/00_JUDGE_SCHEMA.md",
    "design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json",
    "design_brain_wiki/05_industry_playbooks/bullion_investment.md",
    "design_brain_wiki/05_industry_playbooks/deep/bullion_investment_v0_2.md",
    "design_brain_wiki/03_reference_judgement/selected_criteria.md",
    "design_brain_wiki/03_reference_judgement/shortlist_criteria.md",
    "design_brain_wiki/03_reference_judgement/rejected_criteria.md",
    "design_brain_wiki/08_feedback_language/senior_designer_critique_phrases.md",
]

BAD_TAGS = {
    "mascot_character",
    "toy_3d",
    "childish_mood",
    "fake_text",
    "not_financial",
    "not_premium",
    "wrong_event_tone",
}


def main() -> None:
    args = parse_args()
    session_dir = SESSION_ROOT / args.session_id
    references_dir = session_dir / "references"
    if session_dir.exists() and args.force:
        shutil.rmtree(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    references_dir.mkdir(parents=True, exist_ok=True)

    if args.run:
        candidates = _build_run_candidates(args.run.resolve(), references_dir, args.limit)
        source_type = "pinterest_search_reference"
        purpose = "Actual Pinterest/search reference review set for Kiwon review and rule correction."
        local_model_used = False
        judgement_method = "Codex/wiki heuristic first pass over run-collected Pinterest/search references; no Qwen/Ollama visual model call."
    else:
        good_meta = _read_json(SOURCE_ROOT / "good" / "metadata.json")
        bad_meta = _read_json(SOURCE_ROOT / "bad" / "metadata.json")
        candidates = _build_seed_candidates(good_meta, bad_meta, references_dir)
        source_type = "seed_test"
        purpose = "Seed reference sanity-check set. This is not an actual Pinterest collection session."
        local_model_used = False
        judgement_method = "Codex/wiki heuristic first pass over local seed metadata; no Qwen/Ollama visual model call."

    if args.require_pinterest and not any(item.get("sourceIsPinterest") for item in candidates):
        raise RuntimeError(
            "No Pinterest-backed references found. Run 03_reference_research with "
            "REFERENCE_RESEARCH_MODE=auto_search or pass a run that contains Pinterest/search sources."
        )

    if len(candidates) < args.limit:
        print(f"WARNING only {len(candidates)} references available for {args.session_id}; requested {args.limit}.")

    judgements = [_judge(item) for item in candidates]
    report = {
        "sessionId": f"bullion_investment_{args.session_id}",
        "sessionType": source_type,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "profile": "bullion_investment",
        "purpose": purpose,
        "sourceRun": str(args.run.relative_to(ROOT)) if args.run else "",
        "localModelUsed": local_model_used,
        "judgementMethod": judgement_method,
        "wikiSources": WIKI_SOURCES,
        "summary": _summary(judgements),
        "items": judgements,
    }
    _write_json(session_dir / "ai_judgement.json", report)
    _write_text(session_dir / "ai_judgement.md", _render_ai_markdown(report))
    _write_text(session_dir / "kiwon_review_template.md", _render_kiwon_template(report))
    _write_text(session_dir / "correction_log.md", _render_correction_log(report))
    _write_text(session_dir / "wiki_update_suggestions.md", _render_wiki_suggestions(report))
    _write_text(session_dir / "README.md", _render_readme(report))
    print(f"OK created {session_dir.relative_to(ROOT)} items={len(judgements)} type={source_type}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a bullion reference judgement training session.")
    parser.add_argument("--session-id", default="session_001")
    parser.add_argument("--run", type=Path, help="Use actual references from a run instead of local seed images.")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--require-pinterest", action="store_true", help="Fail if the source run has no Pinterest/search-backed images.")
    return parser.parse_args()


def _old_main() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)

    good_meta = _read_json(SOURCE_ROOT / "good" / "metadata.json")
    bad_meta = _read_json(SOURCE_ROOT / "bad" / "metadata.json")
    candidates = _build_candidates(good_meta, bad_meta)
    judgements = [_judge(item) for item in candidates]
    report = {
        "sessionId": "bullion_investment_session_001",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "profile": "bullion_investment",
        "purpose": "30-reference first-pass training set for Kiwon review and rule correction.",
        "localModelUsed": False,
        "judgementMethod": "Codex/wiki heuristic first pass; no Qwen/Ollama visual model call.",
        "wikiSources": WIKI_SOURCES,
        "summary": _summary(judgements),
        "items": judgements,
    }
    _write_json(SESSION_DIR / "ai_judgement.json", report)
    _write_text(SESSION_DIR / "ai_judgement.md", _render_ai_markdown(report))
    _write_text(SESSION_DIR / "kiwon_review_template.md", _render_kiwon_template(report))
    _write_text(SESSION_DIR / "correction_log.md", _render_correction_log(report))
    _write_text(SESSION_DIR / "wiki_update_suggestions.md", _render_wiki_suggestions(report))
    _write_text(SESSION_DIR / "README.md", _render_readme(report))
    print(f"OK created {SESSION_DIR.relative_to(ROOT)} items={len(judgements)}")


def _build_seed_candidates(good_meta: dict[str, Any], bad_meta: dict[str, Any], references_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    good_items = good_meta.get("items", [])[:27]
    for index, item in enumerate(good_items, start=1):
        source = SOURCE_ROOT / "good" / item["filename"]
        session_name = f"{index:02d}_{Path(item['filename']).name}"
        copied = references_dir / session_name
        _copy_if_exists(source, copied)
        items.append({
            "id": f"bullion_ref_{index:02d}",
            "sourceSplit": "good_seed",
            "sourcePath": str(source.relative_to(ROOT)),
            "sessionPath": str(copied.relative_to(ROOT)),
            "sourceUrl": "",
            "pinUrl": "",
            "sourceIsPinterest": False,
            "filename": session_name,
            "category": item.get("category", ""),
            "tags": item.get("tags", []),
            "whyGood": item.get("whyGood", ""),
            "usefulFor": item.get("usefulFor", []),
        })
    bad_files = bad_meta.get("files", [])[:3]
    for offset, item in enumerate(bad_files, start=28):
        source = SOURCE_ROOT / "bad" / item["file"]
        session_name = f"{offset:02d}_{Path(item['file']).name}"
        copied = references_dir / session_name
        _copy_if_exists(source, copied)
        items.append({
            "id": f"bullion_ref_{offset:02d}",
            "sourceSplit": "bad_seed",
            "sourcePath": str(source.relative_to(ROOT)),
            "sessionPath": str(copied.relative_to(ROOT)),
            "sourceUrl": "",
            "pinUrl": "",
            "sourceIsPinterest": False,
            "filename": session_name,
            "category": "bad_reference",
            "tags": sorted(BAD_TAGS),
            "whyGood": "",
            "badReason": item.get("reason", ""),
            "usefulFor": [],
        })
    return items


def _build_run_candidates(run_dir: Path, references_dir: Path, limit: int) -> list[dict[str, Any]]:
    records = _load_run_reference_records(run_dir)
    items: list[dict[str, Any]] = []
    for index, record in enumerate(records[: max(1, limit)], start=1):
        source = _resolve_run_path(run_dir, record)
        if not source or not source.exists():
            continue
        session_name = f"{index:02d}_{source.name}"
        copied = references_dir / session_name
        _copy_if_exists(source, copied)
        decision = _record_decision(record)
        evaluation = record.get("evaluation") or {}
        alignment = record.get("training_alignment") or {}
        source_url = str(record.get("source_url", ""))
        pin_url = str(record.get("pin_url", ""))
        source_text = " ".join([source_url, pin_url, str(record.get("image_url", "")), str(record.get("downloaded_url", ""))]).lower()
        source_is_pinterest = "pinterest." in source_text or "pinimg.com" in source_text
        items.append({
            "id": f"bullion_ref_{index:02d}",
            "sourceSplit": "actual_reference",
            "sourcePath": str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),
            "sessionPath": str(copied.relative_to(ROOT)),
            "sourceUrl": source_url,
            "pinUrl": pin_url,
            "sourceIsPinterest": source_is_pinterest,
            "filename": session_name,
            "category": _record_category(record),
            "tags": _record_tags(record),
            "whyGood": "",
            "badReason": "; ".join((record.get("quality_gate") or {}).get("reasons") or []),
            "usefulFor": alignment.get("matchedUsefulFor", []),
            "pipelineDecision": decision,
            "pipelineEvaluation": evaluation,
            "trainingAlignment": alignment,
            "query": record.get("query", ""),
            "title": record.get("title", ""),
        })
    return items


def _load_run_reference_records(run_dir: Path) -> list[dict[str, Any]]:
    quality = _read_json(run_dir / "references" / "reference-quality-filter.json", default={})
    if isinstance(quality, dict) and any(quality.get(decision) for decision in ("accepted", "shortlist", "rejected")):
        buckets: dict[str, list[dict[str, Any]]] = {}
        for decision in ("accepted", "shortlist", "rejected"):
            buckets[decision] = []
            for item in quality.get(decision, []):
                record = dict(item)
                record["_qualityDecision"] = decision
                buckets[decision].append(record)
            buckets[decision].sort(key=lambda item: float(item.get("score", 0) or 0), reverse=True)
        return _balanced_quality_records(buckets)

    selected = _read_json(run_dir / "references" / "selected-references.json", default={})
    records = [dict(item) for item in selected.get("selected", [])] if isinstance(selected, dict) else []
    for item in records:
        item["_qualityDecision"] = "accepted"
    return records


def _balanced_quality_records(buckets: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Keep judgement sessions useful by mixing selected, shortlist, and rejected examples."""
    order = ["accepted", "shortlist", "rejected"]
    records: list[dict[str, Any]] = []
    target_per_bucket = 10
    selected_buckets = {
        decision: buckets.get(decision, [])[:target_per_bucket]
        for decision in order
    }
    for index in range(target_per_bucket):
        for decision in order:
            if index < len(selected_buckets[decision]):
                records.append(selected_buckets[decision][index])
    if len(records) < 30:
        used = {id(item) for item in records}
        remainder: list[dict[str, Any]] = []
        for decision in order:
            remainder.extend(item for item in buckets.get(decision, [])[target_per_bucket:] if id(item) not in used)
        remainder.sort(key=lambda item: float(item.get("score", 0) or 0), reverse=True)
        records.extend(remainder[: 30 - len(records)])
    return records


def _decision_sort_key(record: dict[str, Any]) -> tuple[int, float]:
    weights = {"accepted": 2, "shortlist": 1, "rejected": 0}
    return (weights.get(str(record.get("_qualityDecision", "")), 0), float(record.get("score", 0) or 0))


def _resolve_run_path(run_dir: Path, record: dict[str, Any]) -> Path | None:
    for key in ("path", "relative_path", "original_path"):
        value = str(record.get(key, "")).strip()
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            path = run_dir / path
        if path.exists():
            return path.resolve()
    return None


def _record_decision(record: dict[str, Any]) -> str:
    decision = str(record.get("_qualityDecision") or (record.get("quality_gate") or {}).get("decision") or "").lower()
    if decision == "accepted":
        return "selected"
    if decision == "shortlist":
        return "shortlist"
    return "rejected"


def _record_category(record: dict[str, Any]) -> str:
    categories = (record.get("training_alignment") or {}).get("matchedCategories") or []
    if categories:
        return str(categories[0])
    decision = _record_decision(record)
    return "bad_reference" if decision == "rejected" else "actual_reference"


def _record_tags(record: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    alignment = record.get("training_alignment") or {}
    tags.extend(str(item) for item in alignment.get("goodHits", [])[:12])
    tags.extend(str(item) for item in alignment.get("badHits", [])[:12])
    tags.extend(str(item) for item in reference_reasons(record))
    qwen = record.get("qwen_review") or {}
    tags.extend(str(item) for item in qwen.get("positive_tags", []) if str(item).strip())
    tags.extend(str(item) for item in qwen.get("negative_tags", []) if str(item).strip())
    return _dedupe(tags)


def reference_reasons(record: dict[str, Any]) -> list[str]:
    gate = record.get("quality_gate") or {}
    return [str(item) for item in gate.get("reasons", []) if str(item).strip()]


def _judge(item: dict[str, Any]) -> dict[str, Any]:
    tags = {str(tag).lower().replace("_", " ") for tag in item.get("tags", [])}
    useful = set(item.get("usefulFor", []))
    category = item.get("category", "")
    risk_signals = _risk_signals(tags, item)
    usable = _usable_elements(category, tags, useful)
    pipeline_decision = item.get("pipelineDecision", "")
    if pipeline_decision in {"selected", "shortlist", "rejected"}:
        decision = pipeline_decision
        confidence = _confidence_from_record(item, risk_signals)
        reason = _reason_from_record(item, decision, usable, risk_signals)
    else:
        decision = "shortlist"
        confidence = 0.72
        reason = ""
    if not pipeline_decision and risk_signals:
        decision = "rejected"
        confidence = 0.94
        reason = "bad seed와 일치하는 캐릭터/장난감/가짜 텍스트/비금융 신호가 있어 금융 투자 상담 브랜드 기준을 통과하지 못합니다."
    elif not pipeline_decision and category == "poster_layout_reference" and ("headline_space" in useful or "campaign_layout" in useful):
        decision = "selected"
        confidence = 0.86
        reason = "카피 여백과 캠페인 레이아웃 기준이 분명해 카드뉴스/배너 제작 방향 기준으로 삼을 수 있습니다."
    elif not pipeline_decision and category == "finance_mood_reference" and ("financial_trust" in useful or "mood" in useful):
        decision = "shortlist"
        confidence = 0.78
        reason = "금융 신뢰 무드는 유용하지만 제품 정체성이나 실제 이벤트 레이아웃이 부족해 단독 selected로는 약합니다."
    elif not pipeline_decision and category == "product_reference":
        decision = "shortlist"
        confidence = 0.76
        reason = "불리언 제품 정체성과 소재 기준은 좋지만 카피 여백/상담 이벤트 구조가 부족해 제품 보조 레퍼런스가 맞습니다."
    feedback = _feedback(item, decision, reason, usable, risk_signals)
    return {
        "id": item["id"],
        "file": item["sessionPath"],
        "sourcePath": item["sourcePath"],
        "sourceUrl": item.get("sourceUrl", ""),
        "pinUrl": item.get("pinUrl", ""),
        "sourceIsPinterest": item.get("sourceIsPinterest", False),
        "sourceSplit": item["sourceSplit"],
        "category": category,
        "decision": decision,
        "confidence": confidence,
        "reason": reason,
        "referenceRole": _roles(category, useful),
        "usableElements": usable,
        "riskSignals": risk_signals,
        "wikiSources": WIKI_SOURCES,
        "seniorDesignerFeedback": feedback,
        "kiwonReview": {
            "agree": "",
            "disagree": "",
            "unsure": "",
            "correctDecision": "",
            "kiwonReason": "",
            "ruleToUpdate": "",
        },
    }


def _confidence_from_record(item: dict[str, Any], risks: list[str]) -> float:
    evaluation = item.get("pipelineEvaluation") or {}
    values = [
        float(evaluation.get("brandFit", 0) or 0),
        float(evaluation.get("eventFit", 0) or 0),
        float(evaluation.get("productRelevance", 0) or 0),
        float(evaluation.get("seriousnessFit", 0) or 0),
    ]
    if any(values):
        confidence = sum(values) / len(values) / 10
    else:
        confidence = 0.72
    if risks:
        confidence = max(confidence, 0.86)
    return round(max(0.55, min(0.96, confidence)), 2)


def _reason_from_record(item: dict[str, Any], decision: str, usable: list[str], risks: list[str]) -> str:
    evaluation = item.get("pipelineEvaluation") or {}
    gate_reasons = reference_reasons({"quality_gate": {"reasons": item.get("badReason", "").split("; ") if item.get("badReason") else []}})
    usable_text = ", ".join(usable) if usable else "부분 참고 요소"
    if decision == "selected":
        return f"실제 수집 레퍼런스 중 {usable_text}가 확인되고, brand/event/product/seriousness 평가가 기준선을 통과했습니다."
    if decision == "shortlist":
        reasons = ", ".join(gate_reasons) or f"평가값 {evaluation}"
        return f"{usable_text}는 참고 가능하지만 selected 기준에는 일부 부족합니다. 보류 사유: {reasons}"
    return f"위험 요소({', '.join(risks) or ', '.join(gate_reasons) or '품질/적합도 기준 미달'}) 때문에 rejected로 둡니다."


def _risk_signals(tags: set[str], item: dict[str, Any]) -> list[str]:
    cleaned_tags = [
        tag for tag in tags
        if not tag.startswith("no ") and not tag.startswith("without ")
    ]
    text = " ".join([*cleaned_tags, item.get("badReason", "")]).lower()
    risks = []
    mapping = {
        "mascot_character": ["mascot", "character"],
        "toy_3d": ["toy", "3d"],
        "fake_text": ["fake text", "broken poster text", "unreadable"],
        "not_financial": ["not financial"],
        "not_premium": ["not premium"],
        "wrong_event_tone": ["wrong event tone", "childish", "cute"],
    }
    for label, needles in mapping.items():
        if any(needle in text for needle in needles):
            risks.append(label)
    return risks


def _usable_elements(category: str, tags: set[str], useful: set[str]) -> list[str]:
    elements = []
    if category == "product_reference" or "product_identity" in useful:
        elements.append("불리언 제품 정체성")
    if category == "finance_mood_reference" or "financial_trust" in useful or "mood" in useful:
        elements.append("금융 신뢰 무드")
    if category == "poster_layout_reference" or "headline_space" in useful or "campaign_layout" in useful:
        elements.append("카피 여백/캠페인 레이아웃")
    if "lighting" in useful:
        elements.append("조명 기준")
    if "material_texture" in useful:
        elements.append("금속 소재감")
    if "composition" in useful:
        elements.append("구도")
    if not elements and not _risk_signals(tags, {"badReason": ""}):
        elements.append("부분 참고")
    return _dedupe(elements)


def _roles(category: str, useful: set[str]) -> list[str]:
    roles = []
    if category == "product_reference" or "product_identity" in useful:
        roles.append("product_identity")
    if category == "finance_mood_reference" or "mood" in useful or "financial_trust" in useful:
        roles.append("finance_mood")
    if category == "poster_layout_reference" or "headline_space" in useful or "campaign_layout" in useful:
        roles.append("poster_layout")
    if not roles:
        roles.append("rejection_boundary")
    return roles


def _feedback(item: dict[str, Any], decision: str, reason: str, usable: list[str], risks: list[str]) -> str:
    usable_text = ", ".join(usable) if usable else "참고 가능 요소"
    if decision == "selected":
        return (
            f"이 레퍼런스는 {usable_text}가 분명해서 금 투자 상담 카드뉴스나 상담 신청 배너의 방향 기준으로 쓸 수 있습니다. "
            "다만 실제 제작에서는 fake text 없이 한국어 헤드라인을 후작업으로 얹고, 제품/카피/CTA 위계를 유지해야 합니다."
        )
    if decision == "shortlist":
        return (
            f"이 레퍼런스는 {usable_text}에는 유용하지만 단독 selected로 쓰기에는 부족합니다. "
            f"{reason} 제품 정체성, 금융 신뢰 무드, 포스터 레이아웃 중 빠진 축을 다른 레퍼런스로 보강해야 합니다."
        )
    return (
        f"이 레퍼런스는 {', '.join(risks)} 신호가 강해 bullion_investment의 금융 신뢰 기준을 통과하지 못합니다. "
        "예쁘거나 눈에 띄더라도 캐릭터/장난감/fake text 방향은 rejected seed로 남기고 다음 검색과 생성에서 차단해야 합니다."
    )


def _summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {"selected": 0, "shortlist": 0, "rejected": 0}
    category_counts: dict[str, int] = {}
    for item in items:
        counts[item["decision"]] += 1
        category_counts[item["category"]] = category_counts.get(item["category"], 0) + 1
    return {
        "total": len(items),
        "decisionCounts": counts,
        "categoryCounts": category_counts,
        "needsKiwonReview": len(items),
    }


def _render_ai_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AI Judgement - Bullion Investment Session 001",
        "",
        f"- Profile: {report['profile']}",
        f"- Local model used: {report['localModelUsed']}",
        f"- Method: {report['judgementMethod']}",
        f"- Total: {report['summary']['total']}",
        f"- Decisions: {report['summary']['decisionCounts']}",
        "",
        "## Items",
        "",
        "| ID | File | Decision | Confidence | Usable elements | Risk signals | Feedback |",
        "|---|---|---:|---:|---|---|---|",
    ]
    for item in report["items"]:
        lines.append(
            "| "
            f"`{item['id']}` | `{item['file']}` | {item['decision']} | {item['confidence']} | "
            f"{', '.join(item['usableElements']) or '-'} | {', '.join(item['riskSignals']) or '-'} | "
            f"{item['seniorDesignerFeedback']} |"
        )
    lines.extend(["", "## Wiki Sources", "", *[f"- `{source}`" for source in report["wikiSources"]], ""])
    return "\n".join(lines)


def _render_kiwon_template(report: dict[str, Any]) -> str:
    lines = [
        "# Kiwon Review Template - Bullion Investment Session 001",
        "",
        "각 항목마다 `agree`, `disagree`, `unsure` 중 하나를 표시하고, 틀렸다면 `correctDecision`과 이유를 적는다.",
        "",
    ]
    for item in report["items"]:
        lines.extend([
            f"## {item['id']} - {Path(item['file']).name}",
            "",
            f"- AI decision: `{item['decision']}`",
            f"- AI confidence: `{item['confidence']}`",
            f"- AI reason: {item['reason']}",
            f"- AI feedback: {item['seniorDesignerFeedback']}",
            "",
            "```text",
            "agree:",
            "disagree:",
            "unsure:",
            "correctDecision:",
            "kiwonReason:",
            "ruleToUpdate:",
            "```",
            "",
        ])
    return "\n".join(lines)


def _render_correction_log(report: dict[str, Any]) -> str:
    selected = [item for item in report["items"] if item["decision"] == "selected"]
    rejected = [item for item in report["items"] if item["decision"] == "rejected"]
    shallow = [
        item for item in report["items"]
        if len(item["seniorDesignerFeedback"]) < 80 or "좋습니다" in item["seniorDesignerFeedback"]
    ]
    lines = [
        "# Correction Log - Bullion Investment Session 001",
        "",
        "기원님 리뷰 후 이 파일을 업데이트한다.",
        "",
        "## AI가 과하게 selected한 것",
        "",
        *[f"- [ ] `{item['id']}`: 현재 selected. 기원님이 shortlist/rejected로 낮추면 이유 기록." for item in selected],
        "",
        "## AI가 너무 엄격하게 rejected한 것",
        "",
        *[f"- [ ] `{item['id']}`: 현재 rejected. 기원님이 shortlist/selected로 올리면 이유 기록." for item in rejected],
        "",
        "## 피드백이 추상적인 것",
        "",
        *([f"- [ ] `{item['id']}`: feedback 보강 필요." for item in shallow] or ["- 현재 자동 검사 기준으로는 없음."]),
        "",
        "## 업종 playbook에 추가할 기준",
        "",
        "- [ ] selected와 shortlist 사이의 poster_layout 기준이 너무 느슨한지 확인.",
        "- [ ] product_reference가 단독 selected로 올라가야 하는 예외 조건이 있는지 확인.",
        "- [ ] finance_mood_reference가 제품 없이 selected가 될 수 있는 조건 확인.",
        "- [ ] fake text, mascot, toy 3D 외 추가 bad signal 기록.",
        "",
    ]
    return "\n".join(lines)


def _render_wiki_suggestions(report: dict[str, Any]) -> str:
    return "\n".join([
        "# Wiki Update Suggestions - Bullion Investment Session 001",
        "",
        "## Bullion playbook 보강점",
        "",
        "- product_reference는 제품 정체성 기준으로는 good이어도, 카피 여백과 상담 이벤트 구조가 없으면 shortlist로 둔다.",
        "- poster_layout_reference는 headline area와 CTA 위계가 있으면 selected 후보로 볼 수 있다.",
        "- finance_mood_reference는 제품 없이도 무드 기준으로는 좋지만, 단독 selected가 되려면 상담/자산관리 맥락과 카피 구조가 필요하다.",
        "",
        "## Feedback phrase 보강점",
        "",
        "- `제품 정체성은 좋지만 메인 비주얼이 아니라 제품 보조 레퍼런스입니다.`",
        "- `금융 신뢰 무드는 맞지만 실제 이벤트 구조가 약해 shortlist가 안전합니다.`",
        "- `카피 여백과 CTA 위계가 있어 제작 기준으로 selected 가능성이 있습니다.`",
        "- `캐릭터/장난감/fake text 신호는 금융 투자 브랜드에서 미학과 무관하게 rejected입니다.`",
        "",
        "## Reference Judge rubric 수정점",
        "",
        "- selected gate에 `referenceRoleCoverage`를 추가한다.",
        "- product/mood/layout 중 2개 이상 충족하면 selected 후보, 1개만 충족하면 기본 shortlist.",
        "- bad signal은 점수와 무관하게 hard reject.",
        "- `confidence`는 점수뿐 아니라 역할 coverage와 risk signal 수로 계산한다.",
        "",
    ])


def _render_readme(report: dict[str, Any]) -> str:
    return "\n".join([
        "# Bullion Investment Training Session 001",
        "",
        "이 세션은 Senior Designer Brain Wiki를 실제 판단 훈련으로 바꾸기 위한 첫 bullion reference review 세트다.",
        "",
        "## Files",
        "",
        "- `references/`: 리뷰 대상 30장",
        "- `ai_judgement.json`: AI 1차 판단 구조화 데이터",
        "- `ai_judgement.md`: 사람이 읽는 AI 판단표",
        "- `kiwon_review_template.md`: 기원님 교정 입력용",
        "- `correction_log.md`: 틀린 패턴 기록용",
        "- `wiki_update_suggestions.md`: 위키/rubric 보강 제안",
        "",
        "## Important",
        "",
        f"Session type: `{report.get('sessionType', '')}`",
        f"Source run: `{report.get('sourceRun', '') or '-'}`",
        "",
        "이번 판단은 로컬 Qwen/Ollama 비전 모델을 호출하지 않았다. Pinterest/search 수집물 또는 seed metadata와 design_brain_wiki 기준을 사용한 1차 판단이다.",
        "",
        f"Summary: {report['summary']}",
        "",
    ])


def _copy_if_exists(source: Path, target: Path) -> None:
    if not source.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _read_json(path: Path, default: Any | None = None) -> dict[str, Any]:
    if not path.exists():
        return default if default is not None else {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


if __name__ == "__main__":
    main()
