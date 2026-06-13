"""Create a reference judgement training session from run-collected references."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRAINING_ROOT = ROOT / "design_brain_wiki" / "training_sessions"
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from services.visual_reference.qwen_reviewer import build_profile_reference_prompt, review_image

COMMON_WIKI_SOURCES = [
    "design_brain_wiki/00_JUDGE_SCHEMA.md",
    "design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json",
    "design_brain_wiki/03_reference_judgement/selected_criteria.md",
    "design_brain_wiki/03_reference_judgement/shortlist_criteria.md",
    "design_brain_wiki/03_reference_judgement/rejected_criteria.md",
    "design_brain_wiki/08_feedback_language/senior_designer_critique_phrases.md",
]

PROFILE_CONFIG = {
    "cosmetics_skincare": {
        "title": "Cosmetics Skincare",
        "industrySource": "design_brain_wiki/05_industry_playbooks/deep/cosmetics_skincare_v0_2.md",
        "positive": [
            "화장품",
            "스킨케어",
            "뷰티",
            "세럼",
            "나이아신아마이드",
            "미백",
            "cardnews",
            "cosmetic",
            "skin care",
            "skincare",
            "serum",
            "advertisement",
        ],
        "event": [
            "세일",
            "할인",
            "증정",
            "이벤트",
            "사은품",
            "배너",
            "광고",
            "프로모션",
            "이벤트 페이지",
            "h&b",
            "promotion",
            "sale",
            "gift",
            "banner",
        ],
        "evidenceFields": [
            "title",
            "alt",
            "description",
            "qwen_reason",
            "qwen_risk",
            "qwen_positive_tags",
            "qwen_negative_tags",
            "kiwonReason",
            "ruleToUpdate",
        ],
        "risks": {
            "foreign_sale_mood": ["waterhouse", "foreign", "english-only"],
            "wrong_product_category": ["hair", "nail", "perfume", "fashion"],
            "ai_artifact": ["nano-banana", "broken", "unreadable"],
            "website_capture": [
                "website",
                "web site",
                "webpage",
                "web page",
                "homepage",
                "screen capture",
                "browser",
                "url bar",
                "address bar",
                "웹사이트",
                "홈페이지",
                "주소창",
            ],
            "weak_copy_space": [],
            "too_small": [],
        },
        "selectedFeedback": "한국 H&B 세일의 제품/혜택/카드뉴스 구조가 함께 보여서 여름 스킨케어 이벤트 제작 기준으로 쓸 수 있습니다.",
        "shortlistFeedback": "화장품 무드나 제품 표현은 참고 가능하지만, 혜택 구조와 한국형 세일 위계가 약해 단독 selected로는 부족합니다.",
        "rejectedFeedback": "스킨케어 세일 이벤트의 제품 신뢰, 혜택 전달, 한국 H&B 감성과 어긋나는 신호가 있어 제외 기준으로 남기는 편이 안전합니다.",
    }
}


def main() -> None:
    args = parse_args()
    profile = args.profile
    config = PROFILE_CONFIG.get(profile, default_config(profile))
    run_dir = args.run.resolve()
    session_dir = TRAINING_ROOT / profile / args.session_id
    references_dir = session_dir / "references"
    if session_dir.exists() and args.force:
        shutil.rmtree(session_dir)
    references_dir.mkdir(parents=True, exist_ok=True)

    records = load_records(run_dir)
    if args.exclude_profile_history:
        records = exclude_profile_history(records, profile, session_dir, run_dir)
    if not records:
        raise RuntimeError(f"No references found in {run_dir}")
    chosen = choose_mixed_records(records, args.limit, config) if args.session_type == "mixed_reference" else choose_records(records, args.limit, config)
    if args.qwen_vision:
        chosen = attach_qwen_reviews(chosen, profile, run_dir, args.qwen_limit, args.qwen_model, args.qwen_host)
    items = [build_item(profile, config, item, index, references_dir, run_dir) for index, item in enumerate(chosen, start=1)]
    items = [item for item in items if item]
    report = {
        "sessionId": f"{profile}_{args.session_id}",
        "sessionType": args.session_type,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "purpose": "Mixed Pinterest/search and Meta ad reference review set for Kiwon review and rule correction." if args.session_type == "mixed_reference" else "Actual Pinterest/search reference review set for Kiwon review and rule correction.",
        "sourceRun": str(run_dir.relative_to(ROOT)) if run_dir.is_relative_to(ROOT) else str(run_dir),
        "localModelUsed": bool(args.qwen_vision),
        "judgementMethod": "Qwen/Ollama vision review plus Codex/wiki heuristic first pass." if args.qwen_vision else "Codex/wiki heuristic first pass over run-collected Pinterest/search references; no Qwen/Ollama visual model call.",
        "wikiSources": [*COMMON_WIKI_SOURCES, config["industrySource"]],
        "summary": summary(items),
        "items": items,
    }
    write_json(session_dir / "ai_judgement.json", report)
    write_text(session_dir / "ai_judgement.md", render_ai_markdown(report, config))
    write_text(session_dir / "kiwon_review_template.md", render_review_template(report))
    write_text(session_dir / "correction_log.md", render_correction_log(report, config))
    write_text(session_dir / "wiki_update_suggestions.md", render_wiki_suggestions(report, config))
    write_text(session_dir / "README.md", render_readme(report, config))
    print(f"OK created {session_dir.relative_to(ROOT)} items={len(items)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--session-id", default="pinterest_session_001")
    parser.add_argument("--session-type", choices=["pinterest_search_reference", "mixed_reference"], default="pinterest_search_reference")
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--exclude-profile-history", action="store_true", help="Skip images already used in prior sessions for this profile.")
    parser.add_argument("--qwen-vision", action="store_true", help="Call local Ollama Qwen-VL and attach image-based qwen_review fields before judgement.")
    parser.add_argument("--qwen-limit", type=int, default=0, help="Maximum items to send to Qwen when --qwen-vision is set. 0 means all chosen items.")
    parser.add_argument("--qwen-model", default="qwen2.5vl:7b")
    parser.add_argument("--qwen-host", default="http://127.0.0.1:11434")
    return parser.parse_args()


def attach_qwen_reviews(
    records: list[dict[str, Any]],
    profile: str,
    run_dir: Path,
    limit: int,
    model: str,
    host: str,
) -> list[dict[str, Any]]:
    event_context = load_event_context(run_dir)
    prompt = build_profile_reference_prompt(profile, event_context)
    max_count = len(records) if limit <= 0 else min(limit, len(records))
    reviewed: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        item = dict(record)
        if index <= max_count and not item.get("qwen_review"):
            image_path = resolve_path(item, run_dir)
            if image_path:
                try:
                    item["qwen_review"] = review_image(image_path, model=model, host=host, prompt=prompt)
                except Exception as exc:
                    item["qwen_review"] = {
                        "decision": "shortlist",
                        "role": "composition",
                        "score": 50,
                        "reason": "Qwen vision review failed; kept for heuristic judgement.",
                        "risk": str(exc),
                        "review_model": model,
                    }
        reviewed.append(item)
    return reviewed


def load_event_context(run_dir: Path) -> dict[str, Any]:
    event_input = read_json(run_dir / "event-input.json", {})
    brand_guide = read_json(run_dir / "brand-guide.json", {})
    return {
        "event_name": event_input.get("eventName") or event_input.get("name") or run_dir.name,
        "product": event_input.get("productName") or event_input.get("productOrService") or "",
        "offer": event_input.get("offer") or "",
        "target": event_input.get("target") or "",
        "brand_name": brand_guide.get("brandName") or event_input.get("brandName") or "",
        "channels": event_input.get("channels") or [],
    }


def default_config(profile: str) -> dict[str, Any]:
    return {
        "title": profile.replace("_", " ").title(),
        "industrySource": f"design_brain_wiki/05_industry_playbooks/deep/{profile}_v0_2.md",
        "positive": [],
        "event": [],
        "risks": {},
        "selectedFeedback": "브랜드/이벤트/제작 활용성이 함께 보여 selected 기준으로 검토할 수 있습니다.",
        "shortlistFeedback": "일부 참고 요소는 있지만 단독 selected로 쓰기에는 역할 coverage가 부족합니다.",
        "rejectedFeedback": "브랜드/이벤트 적합도나 제작 활용성이 부족해 rejected 기준으로 둡니다.",
    }


def load_records(run_dir: Path) -> list[dict[str, Any]]:
    selected = read_json(run_dir / "references" / "selected-references.json", {})
    records = [dict(item) for item in selected.get("selected", [])] if isinstance(selected, dict) else []
    ranked = read_json(run_dir / "references" / "ranked-candidates.json", {})
    ranked_records = [dict(item) for item in ranked.get("ranked", [])] if isinstance(ranked, dict) else []
    if ranked_records:
        records.extend(ranked_records)
    records = dedupe_records(records, run_dir)
    if records:
        return records
    candidates = []
    for path in sorted((run_dir / "references" / "candidates").glob("*/*")):
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            candidates.append({"path": str(path), "relative_path": str(path.relative_to(run_dir)), "title": path.stem, "score": 50})
    return candidates


def dedupe_records(records: list[dict[str, Any]], run_dir: Path) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for record in records:
        digest = str(record.get("sha256") or "").strip()
        path = resolve_path(record, run_dir)
        key = digest or (str(path).lower() if path else str(record.get("source_url") or record.get("title") or ""))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def exclude_profile_history(records: list[dict[str, Any]], profile: str, current_session_dir: Path, run_dir: Path) -> list[dict[str, Any]]:
    used_hashes: set[str] = set()
    profile_dir = TRAINING_ROOT / profile
    if profile_dir.exists():
        for session_dir in profile_dir.iterdir():
            if not session_dir.is_dir() or session_dir == current_session_dir:
                continue
            for image_path in (session_dir / "references").glob("*"):
                digest = file_hash(image_path)
                if digest:
                    used_hashes.add(digest)
    if not used_hashes:
        return records
    filtered: list[dict[str, Any]] = []
    for record in records:
        path = resolve_path(record, run_dir)
        digest = file_hash(path) if path else ""
        if digest and digest in used_hashes:
            continue
        filtered.append(record)
    return filtered


def file_hash(path: Path | None) -> str:
    if not path or not path.exists() or not path.is_file():
        return ""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def choose_records(records: list[dict[str, Any]], limit: int, config: dict[str, Any]) -> list[dict[str, Any]]:
    scored = sorted(records, key=lambda item: score_record(item, config), reverse=True)
    bucket_target = max(1, (limit + 2) // 3)
    selected = [item for item in scored if auto_decision(item, config) == "selected"][:bucket_target]
    shortlist = [item for item in scored if auto_decision(item, config) == "shortlist"][:bucket_target]
    rejected = [item for item in sorted(records, key=lambda item: score_record(item, config)) if auto_decision(item, config) == "rejected"][:bucket_target]
    fallback = [item for item in scored if item not in selected and item not in shortlist and item not in rejected]
    while len(selected) < bucket_target and fallback:
        selected.append(fallback.pop(0))
    while len(shortlist) < bucket_target and fallback:
        shortlist.append(fallback.pop(0))
    while len(rejected) < bucket_target and fallback:
        rejected.append(fallback.pop())
    ordered = []
    for index in range(max(len(selected), len(shortlist), len(rejected))):
        for bucket in (selected, shortlist, rejected):
            if index < len(bucket):
                ordered.append(bucket[index])
    return ordered[:limit]


def choose_mixed_records(records: list[dict[str, Any]], limit: int, config: dict[str, Any]) -> list[dict[str, Any]]:
    meta = [item for item in records if is_meta(item)]
    search = [item for item in records if not is_meta(item)]
    if not meta or not search:
        return choose_records(records, limit, config)
    meta_limit = min(len(meta), max(1, limit // 2))
    search_limit = min(len(search), max(1, limit - meta_limit))
    chosen_meta = choose_records(meta, meta_limit, config)
    chosen_search = choose_records(search, search_limit, config)
    ordered: list[dict[str, Any]] = []
    for index in range(max(len(chosen_meta), len(chosen_search))):
        if index < len(chosen_search):
            ordered.append(chosen_search[index])
        if index < len(chosen_meta):
            ordered.append(chosen_meta[index])
    if len(ordered) < limit:
        fallback = [item for item in choose_records(records, limit, config) if item not in ordered]
        ordered.extend(fallback[: limit - len(ordered)])
    return ordered[:limit]


def score_record(record: dict[str, Any], config: dict[str, Any]) -> float:
    text = record_text(record)
    evaluation = record.get("evaluation") or {}
    qwen = record.get("qwen_review") or {}
    score = float(record.get("score", 0) or 0)
    score += sum(8 for word in config["positive"] if word.lower() in text)
    score += sum(5 for word in config["event"] if word.lower() in text)
    score += float(evaluation.get("eventFit", 0) or 0)
    score += float(evaluation.get("productRelevance", 0) or 0)
    score += float(qwen.get("local_hb_sale_fit", 0) or qwen.get("event_fit", 0) or 0) * 0.2
    score += float(qwen.get("benefit_hierarchy", 0) or 0) * 0.18
    score += float(qwen.get("product_trust", 0) or qwen.get("product_relevance", 0) or 0) * 0.18
    score += float(qwen.get("layout_usability", 0) or qwen.get("copy_space", 0) or 0) * 0.16
    score -= float(qwen.get("risk_level", 0) or 0) * 0.14
    score -= float(qwen.get("website_capture_risk", 0) or 0) * 0.18
    score -= float(qwen.get("text_artifact_risk", 0) or 0) * 0.12
    score -= risk_count(record, config) * 12
    if float(record.get("width", 999) or 999) < 300 or float(record.get("height", 999) or 999) < 300:
        score -= 30
    return score


def auto_decision(record: dict[str, Any], config: dict[str, Any]) -> str:
    text = record_text(record)
    evaluation = record.get("evaluation") or {}
    light_space = float(record.get("light_space", 0.5) or 0.5)
    has_product = any(word.lower() in text for word in config["positive"])
    has_event = any(word.lower() in text for word in config["event"])
    risks = risk_signals(record, config)
    hard_risks = hard_reject_signals(record, config)
    qwen = record.get("qwen_review") or {}
    qwen_hard_risk = max(
        float(qwen.get("website_capture_risk", 0) or 0),
        float(qwen.get("text_artifact_risk", 0) or 0),
        float(qwen.get("risk_level", 0) or 0),
    )
    if hard_risks or qwen_hard_risk >= 82:
        return "rejected"
    if config.get("title") != "Cosmetics Skincare" and light_space < 0.08:
        return "rejected"
    if qwen.get("decision") == "selected":
        if (
            float(qwen.get("local_hb_sale_fit", 0) or 0) >= 70
            and float(qwen.get("benefit_hierarchy", 0) or 0) >= 60
            and float(qwen.get("product_trust", 0) or 0) >= 60
        ):
            return "selected"
    if qwen.get("decision") == "shortlist" and qwen_hard_risk < 70:
        return "shortlist"
    if has_product and has_event and float(evaluation.get("eventFit", 6) or 6) >= 6 and light_space >= 0.18:
        return "selected"
    if has_product or has_event:
        return "shortlist"
    if config.get("title") == "Cosmetics Skincare":
        # Cosmetics holdouts showed that weak metadata often still has partial visual value.
        # Keep it reviewable unless a stable hard-reject signal is present.
        return "shortlist"
    return "shortlist" if risks else "rejected"


def build_item(profile: str, config: dict[str, Any], record: dict[str, Any], index: int, references_dir: Path, run_dir: Path) -> dict[str, Any] | None:
    source = resolve_path(record, run_dir)
    if not source or not source.exists():
        return None
    session_name = f"{index:02d}_{source.name}"
    copied = references_dir / session_name
    shutil.copy2(source, copied)
    decision = auto_decision(record, config)
    risks = risk_signals(record, config)
    usable = usable_elements(record, config)
    reason = reason_text(record, decision, usable, risks)
    return {
        "id": f"{profile}_ref_{index:02d}",
        "file": str(copied.relative_to(ROOT)),
        "sourcePath": str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),
        "sourceUrl": record.get("source_url", ""),
        "pinUrl": record.get("pin_url", ""),
        "sourceIsPinterest": is_pinterest(record),
        "sourceIsMeta": is_meta(record),
        "sourceType": "meta_ad_library" if is_meta(record) else "pinterest_search",
        "sourceSplit": "actual_reference",
        "category": category(record, config),
        "decision": decision,
        "confidence": confidence(record, decision, risks),
        "reason": reason,
        "referenceRole": reference_roles(record, config),
        "usableElements": usable,
        "riskSignals": risks,
        "wikiSources": [*COMMON_WIKI_SOURCES, config["industrySource"]],
        "seniorDesignerFeedback": feedback(config, decision),
        "kiwonReview": {
            "agree": "",
            "disagree": "",
            "unsure": "",
            "correctDecision": "",
            "kiwonReason": "",
            "ruleToUpdate": "",
        },
    }


def resolve_path(record: dict[str, Any], run_dir: Path) -> Path | None:
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


def record_text(record: dict[str, Any]) -> str:
    """Return judgement evidence text.

    Search query, source id, filename/path, and text_relevance_reason are intentionally
    excluded. They describe how the reference was found, not whether the image is a
    good design reference.
    """
    review = record.get("qwen_review") or {}
    review_state = record.get("kiwonReview") or record.get("kiwon_review") or {}
    fields = [
        record.get("title", ""),
        record.get("alt", ""),
        record.get("description", ""),
        review.get("reason", ""),
        review.get("risk", ""),
        " ".join(str(tag) for tag in review.get("positive_tags", []) or []),
        " ".join(str(tag) for tag in review.get("negative_tags", []) or []),
        review_state.get("kiwonReason", ""),
        review_state.get("ruleToUpdate", ""),
    ]
    return " ".join(str(value) for value in fields).lower()


def risk_signals(record: dict[str, Any], config: dict[str, Any]) -> list[str]:
    text = record_text(record)
    risks = []
    for label, terms in config.get("risks", {}).items():
        if terms and any(term.lower() in text for term in terms):
            risks.append(label)
    if float(record.get("width", 999) or 999) < 300 or float(record.get("height", 999) or 999) < 300:
        risks.append("too_small")
    if float(record.get("light_space", 0.5) or 0.5) < 0.08:
        risks.append("weak_copy_space")
    return dedupe(risks)


def hard_reject_signals(record: dict[str, Any], config: dict[str, Any]) -> list[str]:
    hard_labels = {"too_small", "website_capture", "wrong_product_category", "ai_artifact"}
    return [risk for risk in risk_signals(record, config) if risk in hard_labels]


def risk_count(record: dict[str, Any], config: dict[str, Any]) -> int:
    return len(risk_signals(record, config))


def usable_elements(record: dict[str, Any], config: dict[str, Any]) -> list[str]:
    text = record_text(record)
    elements = []
    if any(word.lower() in text for word in ["화장품", "cosmetic", "skin care", "skincare", "serum", "세럼", "스킨케어"]):
        elements.append("제품/스킨케어 카테고리 신호")
    if any(word.lower() in text for word in config["event"]):
        elements.append("세일/혜택 이벤트 구조")
    if float(record.get("light_space", 0.5) or 0.5) >= 0.2:
        elements.append("카피 배치 여백")
    if float(record.get("width", 0) or 0) >= 500:
        elements.append("카드뉴스/배너 제작 해상도")
    return elements or ["부분 참고"]


def category(record: dict[str, Any], config: dict[str, Any]) -> str:
    decision = auto_decision(record, config)
    if decision == "rejected":
        return "rejection_boundary"
    text = record_text(record)
    if any(word.lower() in text for word in config["event"]):
        return "event_sale_layout"
    return "product_mood_reference"


def reference_roles(record: dict[str, Any], config: dict[str, Any]) -> list[str]:
    roles = []
    text = record_text(record)
    if any(word.lower() in text for word in config["positive"]):
        roles.append("product_category")
    if any(word.lower() in text for word in config["event"]):
        roles.append("sale_event_layout")
    if float(record.get("light_space", 0.5) or 0.5) >= 0.2:
        roles.append("copy_space")
    return roles or ["rejection_boundary"]


def reason_text(record: dict[str, Any], decision: str, usable: list[str], risks: list[str]) -> str:
    useful = ", ".join(usable)
    if decision == "selected":
        return f"{useful}가 함께 확인되어 한국 H&B 스킨케어 세일 이벤트의 제작 기준으로 삼을 수 있습니다."
    if decision == "shortlist":
        return f"{useful}는 참고 가능하지만 제품, 혜택, 한국형 카드뉴스 위계 중 일부가 약해 후보로 둡니다."
    return f"{', '.join(risks) or '제품/이벤트 적합도 부족'} 때문에 화장품 세일 레퍼런스 기준에서는 제외합니다."


def confidence(record: dict[str, Any], decision: str, risks: list[str]) -> float:
    evaluation = record.get("evaluation") or {}
    values = [float(evaluation.get(key, 0) or 0) for key in ("brandFit", "eventFit", "productRelevance", "visualQuality")]
    base = (sum(values) / len(values) / 10) if any(values) else 0.72
    if decision == "rejected" and risks:
        base = max(base, 0.84)
    return round(max(0.55, min(0.96, base)), 2)


def feedback(config: dict[str, Any], decision: str) -> str:
    if decision == "selected":
        return config["selectedFeedback"]
    if decision == "shortlist":
        return config["shortlistFeedback"]
    return config["rejectedFeedback"]


def is_pinterest(record: dict[str, Any]) -> bool:
    text = " ".join(str(record.get(key, "")) for key in ("source_url", "pin_url", "image_url", "downloaded_url")).lower()
    return "pinterest." in text or "pinimg.com" in text


def is_meta(record: dict[str, Any]) -> bool:
    return str(record.get("source") or record.get("source_id") or "").lower() == "meta_ad_library" or bool(record.get("ad_library_id"))


def summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"selected": 0, "shortlist": 0, "rejected": 0}
    categories: dict[str, int] = {}
    sources = {"pinterest_search": 0, "meta_ad_library": 0}
    for item in items:
        counts[item["decision"]] += 1
        categories[item["category"]] = categories.get(item["category"], 0) + 1
        source_type = item.get("sourceType", "pinterest_search")
        sources[source_type] = sources.get(source_type, 0) + 1
    return {"total": len(items), "decisionCounts": counts, "categoryCounts": categories, "sourceCounts": sources, "needsKiwonReview": len(items)}


def render_ai_markdown(report: dict[str, Any], config: dict[str, Any]) -> str:
    lines = [
        f"# AI Judgement - {config['title']} {report['sessionId']}",
        "",
        f"- Profile: {report['profile']}",
        f"- Method: {report['judgementMethod']}",
        f"- Total: {report['summary']['total']}",
        f"- Decisions: {report['summary']['decisionCounts']}",
        "",
        "| ID | Decision | Confidence | Usable elements | Risk signals | Feedback |",
        "|---|---:|---:|---|---|---|",
    ]
    for item in report["items"]:
        lines.append(f"| `{item['id']}` | {item['decision']} | {item['confidence']} | {', '.join(item['usableElements'])} | {', '.join(item['riskSignals']) or '-'} | {item['seniorDesignerFeedback']} |")
    return "\n".join(lines) + "\n"


def render_review_template(report: dict[str, Any]) -> str:
    lines = ["# Kiwon Review Template", "", "agree / disagree / unsure, correctDecision, kiwonReason, ruleToUpdate를 기록한다.", ""]
    for item in report["items"]:
        lines.extend([
            f"## {item['id']} - {Path(item['file']).name}",
            "",
            f"- AI decision: `{item['decision']}`",
            f"- AI reason: {item['reason']}",
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


def render_correction_log(report: dict[str, Any], config: dict[str, Any]) -> str:
    return "\n".join([
        f"# Correction Log - {config['title']}",
        "",
        "## AI가 과하게 selected한 것",
        *[f"- [ ] `{item['id']}`: 현재 selected. 기원님이 낮추면 이유 기록." for item in report["items"] if item["decision"] == "selected"],
        "",
        "## AI가 너무 엄격하게 rejected한 것",
        *[f"- [ ] `{item['id']}`: 현재 rejected. 기원님이 올리면 이유 기록." for item in report["items"] if item["decision"] == "rejected"],
        "",
        "## 피드백이 추상적인 것",
        "- [ ] H&B 세일 감성, 혜택 위계, 제품 신뢰, 카피 여백 기준 중 추상 표현 확인.",
        "",
        "## 업종 playbook에 추가할 기준",
        "- [ ] 한국 H&B 세일 selected 기준.",
        "- [ ] 해외/영문 세일 레퍼런스를 보조 자료로만 쓰는 기준.",
        "- [ ] 제품컷 단독과 세일 카드뉴스 layout의 역할 분리.",
        "",
    ])


def render_wiki_suggestions(report: dict[str, Any], config: dict[str, Any]) -> str:
    return "\n".join([
        f"# Wiki Update Suggestions - {config['title']}",
        "",
        "## Cosmetics playbook 보강점",
        "- selected는 제품 신뢰, 혜택 전달, 한국형 H&B 세일 위계, 카피 여백이 함께 있어야 한다.",
        "- 제품 무드만 좋은 이미지는 shortlist로 두고, 이벤트 구조가 없으면 생성 기준으로 단독 사용하지 않는다.",
        "- 해외 세일/영문 프로모션 이미지는 로컬 감성 검증 후 보조 무드로만 사용한다.",
        "",
        "## Feedback phrase 보강점",
        "- `제품 표현은 좋지만 혜택 위계가 약해서 세일 카드뉴스 기준으로는 shortlist입니다.`",
        "- `한국 H&B 세일의 가격/혜택/CTA 구조가 보여 selected 후보로 볼 수 있습니다.`",
        "- `제품군이 맞지 않거나 AI 이미지 흔적이 강해 rejected로 두는 편이 안전합니다.`",
        "",
        "## Reference Judge rubric 수정점",
        "- cosmetics selected gate에 `localHBSaleFit`, `benefitHierarchy`, `claimSafety`, `productTrust`, `copySpace`를 추가한다.",
        "",
    ])


def render_readme(report: dict[str, Any], config: dict[str, Any]) -> str:
    return "\n".join([
        f"# {config['title']} Training Session",
        "",
        "이 세션은 실제 Pinterest/search 및 Meta 광고 레퍼런스를 기원님 빠른 비교 판정으로 교정하기 위한 세트다.",
        "",
        f"- Session type: `{report['sessionType']}`",
        f"- Source run: `{report['sourceRun']}`",
        f"- Summary: `{report['summary']}`",
        "",
    ])


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


if __name__ == "__main__":
    main()
