#!/usr/bin/env python3
"""Local web console for the event content automation project."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from collections import Counter
from urllib.error import URLError
from urllib.parse import unquote, urlparse
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui" / "console"
RUNS_DIR = ROOT / "runs"
EVENTS_DIR = ROOT / "events"
TRAINING_SESSIONS_DIR = ROOT / "design_brain_wiki" / "training_sessions"
META_AD_SEARCHES_DIR = ROOT / "references" / "meta_ads" / "searches"
META_BRAND_RUNS_DIR = ROOT / "references" / "meta_ads" / "brand_registry_runs"
REFERENCE_LEARNING_DIR = ROOT / "design_brain_wiki" / "reference_learning_1000"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
COMFY_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_manifest import build_manifest, load_candidates, load_prompts, load_references, write_manifest
from services.products.library import list_products, load_product, load_product_from_event, split_product_key
from services.ad_reference.brand_registry import registry_summary


JOBS: dict[str, dict[str, Any]] = {}
REFERENCE_LEARNING_ALL_SESSION = "all"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(value: str) -> str:
    value = str(value or "event").strip().lower()
    value = re.sub(r"[^\w가-힣]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "event"


def safe_child(base: Path, *parts: str) -> Path:
    target = (base.joinpath(*parts)).resolve()
    if base.resolve() not in [target, *target.parents]:
        raise ValueError("Path escapes project boundary")
    return target


def run_dir_from_id(run_id: str) -> Path:
    run_dir = safe_child(RUNS_DIR, unquote(run_id))
    if not run_dir.exists() or not run_dir.is_dir():
        raise FileNotFoundError(run_id)
    return run_dir


def event_relative_path(event_dir: Path) -> str:
    return str(event_dir.relative_to(ROOT)).replace("\\", "/")


def python_exe() -> str:
    return str(PYTHON if PYTHON.exists() else Path(sys.executable))


def list_events() -> list[dict[str, Any]]:
    events = []
    if not EVENTS_DIR.exists():
        return events
    for event_dir in sorted(path for path in EVENTS_DIR.iterdir() if path.is_dir()):
        event_input = read_json(event_dir / "event-input.json", {})
        brand_guide = read_json(event_dir / "brand-guide.json", {})
        events.append({
            "id": event_dir.name,
            "path": event_relative_path(event_dir),
            "event_name": event_input.get("eventName") or event_dir.name,
            "brand_name": brand_guide.get("brandName") or event_input.get("brandName") or "",
            "product_library_id": event_input.get("productLibraryId") or "",
            "product_name": event_input.get("productName") or event_input.get("productOrService") or "",
        })
    return events


def list_runs() -> list[dict[str, Any]]:
    runs = []
    if not RUNS_DIR.exists():
        return runs
    run_dirs = sorted((path for path in RUNS_DIR.iterdir() if path.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
    for run_dir in run_dirs:
        if not (run_dir / "run-status.json").exists() and not (run_dir / "run-manifest.json").exists():
            continue
        runs.append(build_manifest(run_dir) if os.environ.get("VERCEL") else write_manifest(run_dir))
    return runs


def list_meta_ad_collections() -> list[dict[str, Any]]:
    collections: list[dict[str, Any]] = []
    if not META_AD_SEARCHES_DIR.exists():
        return collections
    for search_dir in sorted((path for path in META_AD_SEARCHES_DIR.iterdir() if path.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True):
        payload = read_json(search_dir / "collected-ads.json", {})
        if not payload:
            continue
        items = []
        for item in payload.get("items", []):
            enriched = dict(item)
            if item.get("captureFile"):
                enriched["captureUrl"] = f"/meta-ad-assets/{search_dir.name}/captures/{item['captureFile']}"
            enriched["media"] = [
                {
                    **media,
                    "mediaUrl": f"/meta-ad-assets/{search_dir.name}/images/{media.get('savedFile', '')}",
                }
                for media in item.get("media", [])
                if media.get("savedFile")
            ]
            items.append(enriched)
        collections.append({**payload, "id": search_dir.name, "items": items})
    return collections


def collect_meta_ads_job(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")
    command = [
        python_exe(), "scripts/collect_meta_ads.py", "--query", query,
        "--country", str(payload.get("country") or "KR"),
        "--category", str(payload.get("category") or "all"),
        "--limit", str(max(1, int(payload.get("limit") or 20))),
        "--scrolls", str(max(0, int(payload.get("scrolls") or 12))),
    ]
    if payload.get("headless"):
        command.append("--headless")
    if payload.get("qwen"):
        command.append("--qwen")
    if payload.get("advertiserMatch"):
        command.append("--advertiser-match")
    command.extend(["--creative-profile", str(payload.get("creativeProfile") or "product_visual")])
    run_id = str(payload.get("runId") or "").strip()
    if payload.get("connectRun", True) and run_id:
        command.extend(["--run", str(run_dir_from_id(run_id))])
    return start_process(command, ROOT, f"Meta Ad Library: {query}")


def collect_meta_brand_registry_job(payload: dict[str, Any]) -> dict[str, Any]:
    profile = str(payload.get("profile") or "cosmetics_skincare").strip()
    if profile not in {"cosmetics_skincare", "jewelry_luxury"}:
        raise ValueError(f"Unsupported profile: {profile}")
    command = [
        python_exe(), "scripts/collect_meta_brand_registry.py",
        "--profile", profile,
        "--brand-limit", str(max(1, min(30, int(payload.get("brandLimit") or 3)))),
        "--ads-per-brand", str(max(1, min(20, int(payload.get("adsPerBrand") or 3)))),
        "--scrolls", str(max(0, min(30, int(payload.get("scrolls") or 5)))),
    ]
    country = str(payload.get("country") or "").strip()
    if country:
        command.extend(["--country", country])
    if payload.get("headful"):
        command.append("--headful")
    return start_process(command, ROOT, f"Meta brand registry: {profile}")


def list_training_sessions() -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    if not TRAINING_SESSIONS_DIR.exists():
        return sessions
    for profile_dir in sorted(path for path in TRAINING_SESSIONS_DIR.iterdir() if path.is_dir()):
        for session_dir in sorted(path for path in profile_dir.iterdir() if path.is_dir()):
            judgement = read_json(session_dir / "ai_judgement.json", {})
            if not judgement:
                continue
            review_state = read_json(session_dir / "kiwon_review_state.json", {"reviews": {}})
            reviews = review_state.get("reviews", {}) if isinstance(review_state, dict) else {}
            summary = judgement.get("summary", {}) if isinstance(judgement, dict) else {}
            review_summary = training_review_summary(judgement.get("items", []), reviews)
            sessions.append({
                "profile": profile_dir.name,
                "session_id": session_dir.name,
                "sessionType": judgement.get("sessionType", ""),
                "sourceRun": judgement.get("sourceRun", ""),
                "path": str(session_dir.relative_to(ROOT)).replace("\\", "/"),
                "total": summary.get("total", 0),
                "decisionCounts": summary.get("decisionCounts", {}),
                "reviewed": review_summary.get("reviewed", 0),
                "accuracy": review_summary.get("accuracy", 0.0),
                "finalDecisionCounts": review_summary.get("finalDecisionCounts", {}),
                "transitionCounts": review_summary.get("transitionCounts", {}),
                "reasonTagCounts": review_summary.get("reasonTagCounts", {}),
                "overSelected": review_summary.get("overSelected", 0),
                "overRejected": review_summary.get("overRejected", 0),
                "updated_at": review_state.get("updatedAt", ""),
            })
    learning_batches = [session for session in sessions if session.get("profile") == "reference_learning"]
    if learning_batches:
        total = sum(int(session.get("total", 0) or 0) for session in learning_batches)
        reviewed = sum(int(session.get("reviewed", 0) or 0) for session in learning_batches)
        sessions.insert(0, {
            "profile": "reference_learning",
            "session_id": REFERENCE_LEARNING_ALL_SESSION,
            "sessionType": "reference_learning_all",
            "sourceRun": "design_brain_wiki/reference_learning_1000/dataset-index.json",
            "path": "design_brain_wiki/training_sessions/reference_learning",
            "total": total,
            "reviewed": reviewed,
            "accuracy": round(
                sum(float(session.get("accuracy", 0) or 0) * int(session.get("reviewed", 0) or 0) for session in learning_batches) / reviewed,
                3,
            ) if reviewed else 0.0,
            "decisionCounts": merge_count_maps(learning_batches, "decisionCounts"),
            "finalDecisionCounts": merge_count_maps(learning_batches, "finalDecisionCounts"),
            "transitionCounts": merge_count_maps(learning_batches, "transitionCounts"),
            "reasonTagCounts": merge_count_maps(learning_batches, "reasonTagCounts"),
            "overSelected": sum(int(session.get("overSelected", 0) or 0) for session in learning_batches),
            "overRejected": sum(int(session.get("overRejected", 0) or 0) for session in learning_batches),
            "updated_at": max((str(session.get("updated_at") or "") for session in learning_batches), default=""),
        })
    return sessions


def merge_count_maps(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts.update(record.get(key, {}) or {})
    return dict(counts)


def reference_learning_records() -> dict[str, dict[str, Any]]:
    dataset = read_json(REFERENCE_LEARNING_DIR / "dataset-index.json", {})
    return {str(item.get("id") or ""): item for item in dataset.get("items", []) if item.get("id")}


def enrich_reference_learning_item(
    item: dict[str, Any],
    reviews: dict[str, Any],
    session_id: str,
    records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    enriched = dict(item)
    review = {**(item.get("kiwonReview") or {}), **(reviews.get(item.get("id", "")) or {})}
    record = records.get(str(item.get("datasetId") or ""), {})
    reject_reasons = list(record.get("hardRejectReasons", []) or item.get("riskSignals", []) or [])
    if review.get("status"):
        bucket = "completed"
    elif reject_reasons:
        bucket = "auto_excluded"
        enriched["originalAiDecision"] = enriched.get("decision", "")
        enriched["decision"] = "rejected"
    else:
        bucket = "pending"
    enriched["kiwonReview"] = review
    enriched["riskSignals"] = reject_reasons
    enriched["referencePool"] = record.get("referencePool") or ("rejection_example" if reject_reasons else "creative_candidate")
    enriched["reviewBucket"] = bucket
    enriched["originSessionId"] = session_id
    enriched["imageUrl"] = f"/training-assets/reference_learning/{session_id}/{Path(str(item.get('file', ''))).name}"
    return enriched


def reference_learning_status() -> dict[str, Any]:
    summary = read_json(REFERENCE_LEARNING_DIR / "summary.json", {})
    batches = read_json(REFERENCE_LEARNING_DIR / "review-batches.json", {}).get("batches", [])
    sessions = [
        session for session in list_training_sessions()
        if session.get("profile") == "reference_learning" and session.get("session_id") != REFERENCE_LEARNING_ALL_SESSION
    ]
    sessions_by_id = {session["session_id"]: session for session in sessions}
    batch_progress = []
    for batch in batches:
        session = sessions_by_id.get(batch.get("id"), {})
        batch_progress.append({
            **batch,
            "reviewed": session.get("reviewed", 0),
            "accuracy": session.get("accuracy", 0),
            "status": "completed" if session.get("reviewed", 0) >= batch.get("itemCount", 0) else "in_progress" if session.get("reviewed", 0) else "ready",
        })
    learning_reviewed = sum(int(session.get("reviewed", 0) or 0) for session in sessions)
    learning_total = sum(int(session.get("total", 0) or 0) for session in sessions)
    return {
        **summary,
        "learningBatchReviewed": learning_reviewed,
        "learningBatchTotal": learning_total,
        "learningBatchCount": len(batch_progress),
        "completedBatchCount": sum(batch.get("status") == "completed" for batch in batch_progress),
        "batches": batch_progress,
    }


def training_session_dir(profile: str, session_id: str) -> Path:
    session_dir = safe_child(TRAINING_SESSIONS_DIR, unquote(profile), unquote(session_id))
    if not session_dir.exists() or not session_dir.is_dir():
        raise FileNotFoundError(f"{profile}/{session_id}")
    return session_dir


def training_session_detail(profile: str, session_id: str) -> dict[str, Any]:
    if profile == "reference_learning" and session_id == REFERENCE_LEARNING_ALL_SESSION:
        return reference_learning_all_detail()
    session_dir = training_session_dir(profile, session_id)
    judgement = read_json(session_dir / "ai_judgement.json", {})
    review_state = read_json(session_dir / "kiwon_review_state.json", {"reviews": {}})
    reviews = review_state.get("reviews", {}) if isinstance(review_state, dict) else {}
    review_state = {**review_state, "summary": training_review_summary(judgement.get("items", []), reviews)}
    items = []
    for item in judgement.get("items", []):
        session_file = item.get("file", "")
        filename = Path(str(session_file)).name
        enriched = dict(item)
        enriched["imageUrl"] = f"/training-assets/{profile}/{session_id}/{filename}"
        enriched["kiwonReview"] = {**(item.get("kiwonReview") or {}), **(reviews.get(item.get("id", "")) or {})}
        if profile == "reference_learning":
            enriched = enrich_reference_learning_item(enriched, reviews, session_id, reference_learning_records())
        items.append(enriched)
    return {
        "profile": profile,
        "session_id": session_id,
        "sessionType": judgement.get("sessionType", ""),
        "sourceRun": judgement.get("sourceRun", ""),
        "path": str(session_dir.relative_to(ROOT)).replace("\\", "/"),
        "judgement": {**judgement, "items": items},
        "reviewState": review_state,
        "files": {
            "ai_judgement": str((session_dir / "ai_judgement.json").relative_to(ROOT)).replace("\\", "/"),
            "kiwon_review_state": str((session_dir / "kiwon_review_state.json").relative_to(ROOT)).replace("\\", "/"),
            "correction_log": str((session_dir / "correction_log.md").relative_to(ROOT)).replace("\\", "/"),
            "wiki_update_suggestions": str((session_dir / "wiki_update_suggestions.md").relative_to(ROOT)).replace("\\", "/"),
        },
    }


def reference_learning_all_detail() -> dict[str, Any]:
    records = reference_learning_records()
    items_by_dataset: dict[str, dict[str, Any]] = {}
    merged_reviews: dict[str, Any] = {}
    for session_dir in sorted(path for path in (TRAINING_SESSIONS_DIR / "reference_learning").iterdir() if path.is_dir()):
        judgement = read_json(session_dir / "ai_judgement.json", {})
        reviews = read_json(session_dir / "kiwon_review_state.json", {"reviews": {}}).get("reviews", {})
        for item in judgement.get("items", []):
            record = records.get(str(item.get("datasetId") or ""), {})
            if not record.get("eligible", False):
                continue
            enriched = enrich_reference_learning_item(item, reviews, session_dir.name, records)
            dataset_id = str(item.get("datasetId") or item.get("id") or "")
            if reviews.get(item.get("id", "")):
                merged_reviews[str(item.get("id") or "")] = reviews[item["id"]]
            previous = items_by_dataset.get(dataset_id)
            if previous is None or enriched.get("reviewBucket") == "completed":
                items_by_dataset[dataset_id] = enriched
    items = list(items_by_dataset.values())
    decision_counts = dict(Counter(item.get("decision", "") for item in items if item.get("decision")))
    source_counts = dict(Counter(item.get("sourceType", "other") for item in items))
    summary = {
        "total": len(items),
        "decisionCounts": decision_counts,
        "sourceCounts": source_counts,
        "poolCounts": dict(Counter(item.get("referencePool", "creative_candidate") for item in items)),
    }
    return {
        "profile": "reference_learning",
        "session_id": REFERENCE_LEARNING_ALL_SESSION,
        "sessionType": "reference_learning_all",
        "sourceRun": "design_brain_wiki/reference_learning_1000/dataset-index.json",
        "path": "design_brain_wiki/training_sessions/reference_learning",
        "judgement": {"summary": summary, "items": items, "sessionType": "reference_learning_all"},
        "reviewState": {"reviews": merged_reviews, "summary": training_review_summary(items, merged_reviews)},
        "files": {},
    }


def update_training_review(profile: str, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if profile == "reference_learning" and session_id == REFERENCE_LEARNING_ALL_SESSION:
        item_id = str(payload.get("itemId") or "").strip()
        for candidate in sorted(path for path in (TRAINING_SESSIONS_DIR / "reference_learning").iterdir() if path.is_dir()):
            judgement = read_json(candidate / "ai_judgement.json", {})
            if any(item.get("id") == item_id for item in judgement.get("items", [])):
                update_training_review(profile, candidate.name, payload)
                return {"ok": True, "detail": reference_learning_all_detail()}
        raise FileNotFoundError(item_id)
    session_dir = training_session_dir(profile, session_id)
    item_id = str(payload.get("itemId") or "").strip()
    status = str(payload.get("status") or "").strip().lower()
    correct_decision = str(payload.get("correctDecision") or "").strip().lower()
    kiwon_reason = str(payload.get("kiwonReason") or "").strip()
    rule_to_update = str(payload.get("ruleToUpdate") or "").strip()
    reason_tags = normalize_reason_tags(payload.get("reasonTags"))
    if not item_id:
        raise ValueError("itemId is required")
    if status not in {"agree", "disagree", "unsure", ""}:
        raise ValueError("status must be agree, disagree, unsure, or empty")
    if correct_decision and correct_decision not in {"selected", "shortlist", "rejected"}:
        raise ValueError("correctDecision must be selected, shortlist, or rejected")
    judgement = read_json(session_dir / "ai_judgement.json", {})
    items = judgement.get("items", [])
    if not any(item.get("id") == item_id for item in items):
        raise FileNotFoundError(item_id)
    review_state = read_json(session_dir / "kiwon_review_state.json", {"reviews": {}})
    reviews = review_state.setdefault("reviews", {})
    reviews[item_id] = {
        "status": status,
        "correctDecision": correct_decision,
        "kiwonReason": kiwon_reason,
        "ruleToUpdate": rule_to_update,
        "reasonTags": reason_tags,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    review_state["profile"] = profile
    review_state["sessionId"] = session_id
    review_state["updatedAt"] = datetime.now(timezone.utc).isoformat()
    review_state["summary"] = training_review_summary(items, reviews)
    write_json(session_dir / "kiwon_review_state.json", review_state)
    (session_dir / "kiwon_review_summary.md").write_text(render_training_review_summary(items, reviews), encoding="utf-8")
    write_json(session_dir / "learned_rules.json", build_learned_rules(judgement, items, reviews))
    (session_dir / "correction_summary.md").write_text(render_correction_summary(judgement, items, reviews), encoding="utf-8")
    return {"ok": True, "detail": training_session_detail(profile, session_id)}


def summarize_training_session(profile: str, session_id: str) -> dict[str, Any]:
    session_dir = training_session_dir(profile, session_id)
    job = start_process([
        python_exe(),
        "scripts/summarize_reference_training_session.py",
        "--profile",
        profile,
        "--session-id",
        session_id,
    ], ROOT, f"{profile} {session_id} summary")
    return {"ok": True, "job": job}


def compare_training_sessions(profile: str) -> dict[str, Any]:
    profile_dir = safe_child(TRAINING_SESSIONS_DIR, unquote(profile))
    if not profile_dir.exists() or not profile_dir.is_dir():
        raise FileNotFoundError(profile)
    job = start_process([
        python_exe(),
        "scripts/compare_reference_sessions.py",
        "--profile",
        profile,
    ], ROOT, f"{profile} compare sessions")
    return {"ok": True, "job": job}


def create_mixed_training_session(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    run_dir = run_dir_from_id(run_id)
    research = read_json(run_dir / "03_reference_research" / "reference-research.json", {})
    event_profile = research.get("eventProfile", {}) if isinstance(research, dict) else {}
    profile = str(payload.get("profile") or event_profile.get("category") or "cosmetics_skincare").strip()
    if profile == "general":
        profile = "cosmetics_skincare"
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_id = str(payload.get("sessionId") or f"mixed_reference_{stamp}").strip()
    command = [
        python_exe(),
        "scripts/create_reference_training_session.py",
        "--profile", profile,
        "--session-id", session_id,
        "--session-type", "mixed_reference",
        "--run", str(run_dir),
        "--limit", str(max(2, int(payload.get("limit") or 30))),
        "--force",
    ]
    if payload.get("qwenVision"):
        command.append("--qwen-vision")
    return start_process(command, ROOT, f"{profile} Pinterest + Meta training")


def normalize_reason_tags(value: Any) -> list[str]:
    if isinstance(value, str):
        raw = [item.strip() for item in re.split(r"[,|\n]", value) if item.strip()]
    elif isinstance(value, list):
        raw = [str(item).strip() for item in value if str(item).strip()]
    else:
        raw = []
    allowed = {
        "low_resolution",
        "website_capture",
        "weak_local_fit",
        "weak_product",
        "good_benefit_hierarchy",
        "usable_selected",
        "foreign_sale_risk",
        "fake_text_risk",
        "good_layout",
        "wrong_category",
    }
    return [item for item in dict.fromkeys(raw) if item in allowed]


def training_review_summary(items: list[dict[str, Any]], reviews: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "total": len(items),
        "reviewed": 0,
        "agree": 0,
        "disagree": 0,
        "unsure": 0,
        "overSelected": 0,
        "overRejected": 0,
        "abstractFeedback": 0,
        "accuracy": 0.0,
        "finalDecisionCounts": {"selected": 0, "shortlist": 0, "rejected": 0},
        "transitionCounts": {},
        "reasonTagCounts": {},
    }
    by_id = {item.get("id"): item for item in items}
    correct_matches = 0
    transition_counter: Counter[str] = Counter()
    tag_counter: Counter[str] = Counter()
    for item_id, review in reviews.items():
        status = review.get("status", "")
        if status:
            summary["reviewed"] += 1
        if status in {"agree", "disagree", "unsure"}:
            summary[status] += 1
        ai_decision = by_id.get(item_id, {}).get("decision", "")
        correct = review.get("correctDecision", "")
        final_decision = correct or ai_decision
        if final_decision in summary["finalDecisionCounts"]:
            summary["finalDecisionCounts"][final_decision] += 1
        if status:
            if final_decision == ai_decision:
                correct_matches += 1
            if ai_decision and final_decision:
                transition_counter[f"{ai_decision}->{final_decision}"] += 1
        if ai_decision == "selected" and correct in {"shortlist", "rejected"}:
            summary["overSelected"] += 1
        if ai_decision == "rejected" and correct in {"selected", "shortlist"}:
            summary["overRejected"] += 1
        tag_counter.update(review.get("reasonTags", []) or [])
        feedback = by_id.get(item_id, {}).get("seniorDesignerFeedback", "")
        if len(feedback) < 80 or feedback.strip() in {"좋습니다", "고급스럽습니다"}:
            summary["abstractFeedback"] += 1
    summary["accuracy"] = round(correct_matches / summary["reviewed"], 3) if summary["reviewed"] else 0.0
    summary["transitionCounts"] = dict(sorted(transition_counter.items()))
    summary["reasonTagCounts"] = dict(tag_counter.most_common())
    return summary


def render_training_review_summary(items: list[dict[str, Any]], reviews: dict[str, Any]) -> str:
    summary = training_review_summary(items, reviews)
    lines = [
        "# Kiwon Review Summary",
        "",
        f"- Total: {summary['total']}",
        f"- Reviewed: {summary['reviewed']}",
        f"- Agree: {summary['agree']}",
        f"- Disagree: {summary['disagree']}",
        f"- Unsure: {summary['unsure']}",
        f"- Over-selected: {summary['overSelected']}",
        f"- Over-rejected: {summary['overRejected']}",
        f"- Abstract feedback: {summary['abstractFeedback']}",
        f"- Accuracy: {summary['accuracy']}",
        f"- Final decisions: {summary['finalDecisionCounts']}",
        f"- Reason tags: {summary['reasonTagCounts']}",
        "",
        "## Corrections",
        "",
    ]
    by_id = {item.get("id"): item for item in items}
    for item_id, review in reviews.items():
        if not review.get("status"):
            continue
        item = by_id.get(item_id, {})
        lines.extend([
            f"### {item_id}",
            "",
            f"- AI decision: {item.get('decision', '')}",
            f"- Review: {review.get('status', '')}",
            f"- Correct decision: {review.get('correctDecision', '')}",
            f"- Reason tags: {', '.join(review.get('reasonTags', []) or []) or '-'}",
            f"- Kiwon reason: {review.get('kiwonReason', '')}",
            f"- Rule to update: {review.get('ruleToUpdate', '')}",
            "",
        ])
    return "\n".join(lines)


def build_learned_rules(judgement: dict[str, Any], items: list[dict[str, Any]], reviews: dict[str, Any]) -> dict[str, Any]:
    summary = training_review_summary(items, reviews)
    by_id = {item.get("id"): item for item in items}
    hard_reject_tags = {"low_resolution", "website_capture", "wrong_category", "fake_text_risk"}
    selected_tags = {"good_benefit_hierarchy", "usable_selected", "good_layout"}
    rules = []
    tag_counts = summary["reasonTagCounts"]
    if any(tag_counts.get(tag, 0) for tag in hard_reject_tags):
        rules.append({
            "id": "hard_reject_visual_defects",
            "decision": "rejected",
            "whenAnyReasonTag": sorted(tag for tag in hard_reject_tags if tag_counts.get(tag, 0)),
            "guidance": "저해상도, 웹페이지 캡처, 카테고리 오류, 가짜 텍스트 위험은 selected로 올리지 않는다.",
        })
    if summary["overRejected"]:
        rules.append({
            "id": "soften_rejected_to_shortlist",
            "decision": "shortlist",
            "unlessAnyReasonTag": sorted(hard_reject_tags),
            "guidance": "명확한 hard reject 신호가 없고 부분 참고 가치가 있으면 rejected보다 shortlist를 우선한다.",
        })
    if any(tag_counts.get(tag, 0) for tag in selected_tags):
        rules.append({
            "id": "selected_requires_event_usable_structure",
            "decision": "selected",
            "whenAnyReasonTag": sorted(tag for tag in selected_tags if tag_counts.get(tag, 0)),
            "guidance": "혜택 위계, 제작 가능한 레이아웃, 선택 가능성이 함께 보이는 이미지를 selected 후보로 둔다.",
        })
    examples = []
    for item_id, review in reviews.items():
        if not review.get("status"):
            continue
        item = by_id.get(item_id, {})
        examples.append({
            "id": item_id,
            "aiDecision": item.get("decision", ""),
            "finalDecision": review.get("correctDecision") or item.get("decision", ""),
            "reasonTags": review.get("reasonTags", []) or [],
            "kiwonReason": review.get("kiwonReason", ""),
        })
    return {
        "sessionId": judgement.get("sessionId", ""),
        "profile": judgement.get("profile", ""),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "rules": rules,
        "examples": examples,
    }


def render_correction_summary(judgement: dict[str, Any], items: list[dict[str, Any]], reviews: dict[str, Any]) -> str:
    summary = training_review_summary(items, reviews)
    learned = build_learned_rules(judgement, items, reviews)
    lines = [
        f"# Correction Summary - {judgement.get('sessionId', '')}",
        "",
        f"- Profile: `{judgement.get('profile', '')}`",
        f"- Reviewed: {summary['reviewed']}/{summary['total']}",
        f"- Accuracy: {summary['accuracy']}",
        f"- Final distribution: {summary['finalDecisionCounts']}",
        f"- Transitions: {summary['transitionCounts']}",
        f"- Reason tags: {summary['reasonTagCounts']}",
        "",
        "## Learned Rules",
        "",
    ]
    if learned["rules"]:
        for rule in learned["rules"]:
            lines.append(f"- `{rule['id']}`: {rule['guidance']}")
    else:
        lines.append("- 아직 반복 패턴이 충분하지 않습니다.")
    lines.extend(["", "## Reviewed Examples", ""])
    for example in learned["examples"]:
        lines.append(
            f"- `{example['id']}` {example['aiDecision']} -> {example['finalDecision']} "
            f"| tags: {', '.join(example['reasonTags']) or '-'} | {example['kiwonReason']}"
        )
    lines.append("")
    return "\n".join(lines)


def job_log(job_id: str) -> dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        raise FileNotFoundError(job_id)
    log_path = Path(str(job.get("log_path") or ""))
    if not log_path.exists() or not log_path.is_file():
        return {"ok": True, "job": job, "log": ""}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return {"ok": True, "job": job, "log": text[-12000:]}


def run_detail(run_id: str) -> dict[str, Any]:
    run_dir = run_dir_from_id(run_id)
    manifest = build_manifest(run_dir) if os.environ.get("VERCEL") else write_manifest(run_dir)
    selected_assets = read_json(run_dir / "04_admin_selection" / "selected-assets.json", {})
    selected_items = selected_assets.get("selectedAssets", selected_assets.get("selections", []))
    selections = {
        item.get("id") or item.get("candidate_id"): item
        for item in selected_items
        if item.get("id") or item.get("candidate_id")
    }
    candidates = load_candidates(run_dir)
    for candidate in candidates:
        selection = selections.get(candidate.get("candidate_id")) or {}
        candidate["review_decision"] = selection.get("status") or selection.get("decision") or "unreviewed"
        candidate["manager_note"] = selection.get("note") or selection.get("manager_note") or ""
        candidate["selected_file"] = selection.get("sourceFile") or selection.get("selected_file") or ""
    event_input = read_json(run_dir / "event-input.json", {})
    try:
        product = load_product_from_event(event_input)
    except Exception as exc:
        product = {"error": str(exc), "library_id": event_input.get("productLibraryId") or ""}
    return {
        "manifest": manifest,
        "event_input": event_input,
        "brand_guide": read_json(run_dir / "brand-guide.json", {}),
        "product": product,
        "references": load_references(run_dir),
        "candidates": candidates,
        "prompts": load_prompts(run_dir),
        "selected_assets": selected_assets,
        "package_manifest": read_json(run_dir / "production-package" / "archive-metadata.json", {}),
        "qa_report": read_json(run_dir / "06_qa_packaging" / "qa-report.json", {}),
        "final_package_manifest": read_json(run_dir / "06_qa_packaging" / "final-package-manifest.json", []),
        "qa_packaging": read_json(run_dir / "06_qa_packaging" / "qa-packaging.json", {}),
    }


def split_lines(value: str) -> list[str]:
    if isinstance(value, list):
        return value
    return [line.strip() for line in str(value or "").replace(",", "\n").splitlines() if line.strip()]


def create_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_name = payload.get("eventName") or payload.get("event_name") or "New Event"
    brand_name = payload.get("brandName") or payload.get("brand_name") or ""
    event_dir = safe_child(EVENTS_DIR, slugify(event_name))
    suffix = 2
    while event_dir.exists():
        event_dir = safe_child(EVENTS_DIR, f"{slugify(event_name)}-{suffix}")
        suffix += 1
    event_dir.mkdir(parents=True)

    event_input = {
        "brandName": brand_name,
        "eventName": event_name,
        "purpose": payload.get("purpose", ""),
        "target": payload.get("target", ""),
        "productOrService": payload.get("productOrService", ""),
        "channels": payload.get("channels") or ["instagram", "naver_blog", "community"],
        "schedule": {
            "startDate": payload.get("startDate", ""),
            "endDate": payload.get("endDate", ""),
            "publishDate": payload.get("publishDate", ""),
        },
        "offer": payload.get("offer", ""),
        "toneAndManner": payload.get("toneAndManner", ""),
        "references": split_lines(payload.get("referenceDirection", "")),
        "requiredPhrases": split_lines(payload.get("requiredPhrases", "")),
        "bannedWords": split_lines(payload.get("bannedWords", "")),
        "notes": payload.get("notes", ""),
    }
    product_library_id = str(payload.get("productLibraryId") or "").strip()
    if product_library_id:
        product = load_product_from_event({"productLibraryId": product_library_id})
        event_input.update({
            "productLibraryId": product_library_id,
            "productId": product.get("product_id", ""),
            "productName": product.get("product_name", ""),
            "productOrService": product.get("product_name", event_input["productOrService"]),
            "productSource": {
                "library_id": product_library_id,
                "main_image": product.get("main_image_asset", {}),
                "mask_image": product.get("mask_image_asset", {}),
                "brand_style_refs": product.get("brand_style_refs", []),
                "recommended_workflows": product.get("recommended_workflows", []),
            },
        })
        if not brand_name:
            brand_name = product.get("brand_name", "")
            event_input["brandName"] = brand_name
    brand_guide = {
        "brandName": brand_name,
        "tone": split_lines(payload.get("toneAndManner", "")),
        "styleRules": split_lines(payload.get("styleRules", "")),
        "preferredWords": split_lines(payload.get("preferredWords", "")),
        "avoidWords": split_lines(payload.get("bannedWords", "")),
    }
    if product_library_id:
        product = load_product_from_event({"productLibraryId": product_library_id})
        brand_guide["productTone"] = product.get("tone", [])
        brand_guide["productForbidden"] = product.get("forbidden", [])
    write_json(event_dir / "event-input.json", event_input)
    write_json(event_dir / "brand-guide.json", brand_guide)
    write_json(event_dir / "selection.json", {"selected": []})
    return {"ok": True, "event": {"id": event_dir.name, "path": event_relative_path(event_dir), "event_name": event_name, "brand_name": brand_name}}


def product_asset(category: str, product_id: str, asset_kind: str, ref_name: str = "") -> Path:
    product = load_product(category, product_id)
    if asset_kind == "main":
        path = Path(product.get("main_image_asset", {}).get("absolute_path", ""))
    elif asset_kind == "mask":
        path = Path(product.get("mask_image_asset", {}).get("absolute_path", ""))
    elif asset_kind == "ref" and ref_name:
        refs = {item.get("name"): item for item in product.get("brand_style_refs", [])}
        path = Path(refs.get(ref_name, {}).get("absolute_path", ""))
    else:
        raise FileNotFoundError(asset_kind)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    return path


def create_package(run_id: str) -> dict[str, Any]:
    run_dir = run_dir_from_id(run_id)
    package_dir = run_dir / "production-package"
    package_dir.mkdir(exist_ok=True)
    detail = run_detail(run_id)

    final_copy = [
        f"# {detail['manifest']['event_name']}",
        "",
        f"- Brand: {detail['manifest'].get('brand_name', '')}",
        f"- Status: {detail['manifest'].get('status', '')}",
        f"- Next: {detail['manifest'].get('next_action', '')}",
        "",
    ]
    for prompt in detail["prompts"][:10]:
        if prompt.get("deliverable_id"):
            final_copy.extend([f"## {prompt['deliverable_id']}", prompt.get("positive_prompt", ""), ""])

    selected_assets = detail.get("selected_assets") or {}
    selected_items = selected_assets.get("selectedAssets", selected_assets.get("selections", []))
    selected_candidate_ids = {
        item.get("id") or item.get("candidate_id")
        for item in selected_items
        if item.get("status", item.get("decision")) == "selected"
    }
    selected_prompts = [
        prompt for prompt in detail["prompts"]
        if not selected_candidate_ids or prompt.get("candidate_id") in selected_candidate_ids
    ]
    selected_candidates = [
        candidate for candidate in detail["candidates"]
        if not selected_candidate_ids or candidate.get("candidate_id") in selected_candidate_ids
    ]
    write_json(package_dir / "selected-assets.json", selected_assets)
    write_json(package_dir / "selected-prompts.json", {"prompts": selected_prompts})
    write_json(package_dir / "reference-trace.json", {"references": detail["references"]})
    write_json(package_dir / "generated-images.json", {"candidates": selected_candidates})
    write_json(package_dir / "qa-checklist.json", {
        "checks": [
            {"id": "copy_required_phrases", "label": "Required phrases included", "status": "pending"},
            {"id": "reference_risk", "label": "Reference risk reviewed", "status": "pending"},
            {"id": "channel_specs", "label": "Channel specs matched", "status": "pending"},
        ]
    })
    (package_dir / "final-copy.md").write_text("\n".join(final_copy), encoding="utf-8")
    (package_dir / "package-summary.md").write_text(
        build_human_package_summary(detail, selected_items, selected_prompts, selected_candidates),
        encoding="utf-8",
    )
    (package_dir / "layout-guide.md").write_text(
        "# Production Guide\n\nUse the selected assets and prompts as the source of truth for the next production step.\n",
        encoding="utf-8",
    )
    archive = {
        "run_id": detail["manifest"]["run_id"],
        "event_name": detail["manifest"]["event_name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [
            "package-summary.md",
            "final-copy.md",
            "selected-assets.json",
            "selected-prompts.json",
            "reference-trace.json",
            "generated-images.json",
            "layout-guide.md",
            "qa-checklist.json",
            "archive-metadata.json",
        ],
    }
    write_json(package_dir / "archive-metadata.json", archive)
    return {"ok": True, "package_dir": str(package_dir), "archive": archive}


def build_human_package_summary(
    detail: dict[str, Any],
    selected_items: list[dict[str, Any]],
    selected_prompts: list[dict[str, Any]],
    selected_candidates: list[dict[str, Any]],
) -> str:
    prompt_by_candidate = {item.get("candidate_id"): item for item in selected_prompts}
    candidate_by_id = {item.get("candidate_id"): item for item in selected_candidates}
    selected = [
        item for item in selected_items
        if item.get("status", item.get("decision")) == "selected"
    ]
    lines = [
        f"# 제작 패키지 요약 - {detail['manifest']['event_name']}",
        "",
        "## 이 폴더로 할 일",
        "",
        "- 아래 선택된 후보와 카피를 기준으로 다음 제작 단계를 진행한다.",
        "- `selected-assets.json`은 자동화 입력 원본이고, 이 파일은 사람이 보는 요약본이다.",
        "- 아직 최종 업로드 이미지가 아니라 제작 지시서/인수인계 패키지다.",
        "",
        "## 선택된 후보",
        "",
    ]
    if not selected:
        lines.append("- 선택된 후보가 없습니다.")
    for item in selected:
        candidate_id = item.get("id") or item.get("candidate_id", "")
        prompt = prompt_by_candidate.get(candidate_id, {})
        candidate = candidate_by_id.get(candidate_id, {})
        lines.extend([
            f"### {item.get('channel') or item.get('channel_id', '-')}",
            "",
            f"- 후보 ID: `{candidate_id}`",
            f"- 용도: {item.get('type') or item.get('visual_role', '-')}",
            f"- 산출물: {item.get('deliverableId') or item.get('deliverable_id', '-')}",
            f"- 파일: `{item.get('sourceFile') or item.get('selected_file', '')}`",
            f"- 상태: {candidate.get('generation_status', '-')}",
            f"- 메모: {item.get('note') or item.get('manager_note', '')}",
            "",
            "프롬프트:",
            "",
            prompt.get("positive_prompt") or item.get("prompt") or "-",
            "",
        ])
    lines.extend([
        "## 다음 작업",
        "",
        "1. 선택 후보가 맞는지 콘솔 이미지 선택 화면에서 확인한다.",
        "2. 선택 프롬프트를 실제 이미지 생성 단계에 넘긴다.",
        "3. 생성 결과물을 다시 QA하고 최종 배포 파일로 묶는다.",
        "",
    ])
    return "\n".join(lines)


def update_candidate_selection(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    run_dir = run_dir_from_id(run_id)
    candidate_id = str(payload.get("candidate_id") or "").strip()
    decision = str(payload.get("decision") or "hold").strip().lower()
    note = str(payload.get("manager_note") or "").strip()
    if not candidate_id:
        raise ValueError("candidate_id is required")
    if decision not in {"selected", "rejected", "hold", "regenerate"}:
        raise ValueError("decision must be selected, rejected, hold, or regenerate")

    candidate_manifest = read_json(run_dir / "03_visual_candidates" / "candidate-manifest.json", {"candidates": [], "regeneration_groups": []})
    candidates = {
        item.get("candidate_id"): item
        for item in candidate_manifest.get("candidates", [])
        if item.get("candidate_id")
    }
    candidate = candidates.get(candidate_id)
    if not candidate:
        raise FileNotFoundError(f"Unknown candidate: {candidate_id}")
    if decision == "selected" and candidate.get("generation_status") in {"failed", "error"}:
        raise ValueError(f"Cannot select failed candidate: {candidate_id}")

    selected_path = run_dir / "04_admin_selection" / "selected-assets.json"
    selected_assets = read_json(selected_path, {})
    if not selected_assets:
        selected_assets = {
            "eventId": candidate_manifest.get("event_id") or run_id,
            "selectedAssets": [],
            "regenerationRequests": [],
            "summary": {},
            "approvalStatus": "review_pending",
        }

    selections = selected_assets.setdefault("selectedAssets", selected_assets.pop("selections", []))
    current = next((item for item in selections if (item.get("id") or item.get("candidate_id")) == candidate_id), None)
    if current is None:
        current = {
            "id": candidate_id,
            "channel": candidate.get("channel_id", ""),
            "type": candidate.get("visual_role", ""),
            "prompt": "",
            "deliverableId": candidate.get("deliverable_id", ""),
            "regenerationGroup": candidate.get("regeneration_group", ""),
        }
        selections.append(current)

    current.update({
        "status": decision,
        "sourceFile": candidate.get("image_path", "") if decision == "selected" else "",
        "note": note,
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
    })

    if decision == "selected":
        for item in selections:
            if item is current:
                continue
            if item.get("deliverableId") == current.get("deliverableId") and item.get("status") == "selected":
                item["status"] = "rejected"
                item["sourceFile"] = ""
                item["note"] = item.get("note") or "다른 후보가 최종 선택되어 자동 탈락 처리"

    if decision == "regenerate":
        group_id = candidate.get("regeneration_group", "")
        groups = {
            item.get("group_id"): item
            for item in candidate_manifest.get("regeneration_groups", [])
            if item.get("group_id")
        }
        if group_id and not any(item.get("groupId") == group_id and item.get("status") in {"requested", "queued", "running"} for item in selected_assets.get("regenerationRequests", [])):
            group_meta = groups.get(group_id, {})
            selected_assets.setdefault("regenerationRequests", []).append({
                "groupId": group_id,
                "reason": note or "operator requested regeneration",
                "requestedBy": "console",
                "requestedAt": datetime.now(timezone.utc).isoformat(),
                "status": "requested",
                "stageId": "04_visual_candidates",
                "candidateIds": group_meta.get("candidate_ids", [candidate_id]),
                "workflowCommand": group_meta.get("regenerate_command", ""),
            })

    summary = selected_assets.setdefault("summary", {})
    summary.update({
        "reviewer": "console",
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
        "decisionCount": len(selections),
        "selectedCount": sum(1 for item in selections if item.get("status") == "selected"),
        "regenerationRequestCount": len(selected_assets.get("regenerationRequests", [])),
        "blockingIssues": summary.get("blockingIssues", []),
    })
    selected_assets["approvalStatus"] = "review_pending"
    write_json(selected_path, selected_assets)
    notes_path = run_dir / "04_admin_selection" / "selection-notes.md"
    notes_path.write_text(build_selection_notes(selected_assets), encoding="utf-8")
    return {"ok": True, "selected_assets": selected_assets}


def build_selection_notes(selected_assets: dict[str, Any]) -> str:
    summary = selected_assets.get("summary", {})
    lines = [
        "# Admin Selection Notes",
        "",
        f"- Reviewer: {summary.get('reviewer', 'console')}",
        f"- Decisions: {summary.get('decisionCount', 0)}",
        f"- Selected: {summary.get('selectedCount', 0)}",
        f"- Regeneration requests: {summary.get('regenerationRequestCount', 0)}",
        "",
        "## Decisions",
    ]
    for item in selected_assets.get("selectedAssets", []):
        lines.append(f"- {item.get('id')}: {item.get('status')} | {item.get('note', '')}")
    lines.extend(["", "## Regeneration Requests"])
    requests = selected_assets.get("regenerationRequests", [])
    lines.extend([f"- {item.get('groupId')}: {item.get('reason', '')}" for item in requests] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def start_process(command: list[str], cwd: Path, label: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    job_id = f"{int(time.time())}-{slugify(label)}"
    log_dir = ROOT / ".tmp" / "console-jobs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{job_id}.log"
    JOBS[job_id] = {"job_id": job_id, "label": label, "status": "running", "log_path": str(log_path), "started_at": datetime.now(timezone.utc).isoformat()}

    def worker() -> None:
        with log_path.open("w", encoding="utf-8", errors="ignore") as log:
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, text=True, env=process_env)
            code = process.wait()
        JOBS[job_id]["status"] = "done" if code == 0 else "failed"
        JOBS[job_id]["returncode"] = code
        JOBS[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()

    threading.Thread(target=worker, daemon=True).start()
    return JOBS[job_id]


def run_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_dir_value = payload.get("eventDir") or payload.get("eventPath") or "events/sample"
    event_dir = safe_child(ROOT, str(event_dir_value))
    if not event_dir.exists():
        raise FileNotFoundError(str(event_dir))
    bat = ROOT / "run_event_with_reference_ai.bat"
    return start_process([
        "cmd",
        "/c",
        str(bat),
        str(event_dir),
        str(payload.get("queryLimit") or 1),
        str(payload.get("perQueryLimit") or 3),
        str(payload.get("selectCount") or 1),
        str(payload.get("reviewLimit") or 1),
    ], ROOT, f"run {event_dir.name}")


def run_stage(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    run_dir = run_dir_from_id(run_id)
    stage = payload.get("stage")
    if not stage:
        raise ValueError("stage is required")
    return start_process([python_exe(), "scripts/workflow.py", "--mode", "run", "--run", str(run_dir), "--stage", str(stage)], ROOT, f"{run_id} {stage}")


def run_reference_pipeline(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    run_dir = run_dir_from_id(run_id)
    command = [
        python_exe(),
        "scripts/workflow.py",
        "--run",
        str(run_dir),
        "--run-reference-pipeline",
        "--reference-update-03",
        "--reference-reviewer",
        str(payload.get("reviewer") or "qwen"),
        "--reference-query-limit",
        str(payload.get("queryLimit") or 1),
        "--reference-per-query-limit",
        str(payload.get("perQueryLimit") or 3),
        "--reference-select-count",
        str(payload.get("selectCount") or 1),
    ]
    if payload.get("reviewLimit"):
        command.extend(["--reference-review-limit", str(payload["reviewLimit"])])
    if payload.get("headful"):
        command.append("--reference-headful")
    return start_process(command, ROOT, f"{run_id} reference pipeline")


def run_comfy_generation(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    run_dir = run_dir_from_id(run_id)
    group = payload.get("group")
    command = [python_exe(), "scripts/workflow.py", "--mode", "regenerate" if group else "run", "--run", str(run_dir), "--stage", "04_visual_candidates"]
    if group:
        command.extend(["--group", str(group)])
    generation_mode = "live" if payload.get("live", True) else "placeholder"
    return start_process(command, ROOT, f"{run_id} ComfyUI {group or 'all'}", env={"COMFYUI_GENERATION_MODE": generation_mode})


def comfy_status() -> dict[str, Any]:
    try:
        with urlopen(f"{COMFY_URL}/system_stats", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {"ok": True, "connected": True, "url": COMFY_URL, "system": payload}
    except (URLError, TimeoutError, OSError) as exc:
        return {"ok": True, "connected": False, "url": COMFY_URL, "error": str(exc)}


def open_project_path(payload: dict[str, Any]) -> dict[str, Any]:
    target_value = payload.get("path")
    if not target_value:
        raise ValueError("path is required")
    target = Path(str(target_value))
    if not target.is_absolute():
        target = safe_child(ROOT, str(target_value))
    target = target.resolve()
    if ROOT.resolve() not in [target, *target.parents]:
        raise ValueError("Path escapes project boundary")
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(["explorer", str(target)])
    return {"ok": True, "path": str(target)}


class ConsoleHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, exc: Exception, status: int = 400) -> None:
        self.send_json({"ok": False, "error": str(exc)}, status)

    def read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/bootstrap":
                self.send_json({
                    "runs": list_runs(),
                    "events": list_events(),
                    "products": list_products(),
                    "trainingSessions": list_training_sessions(),
                    "referenceLearning": reference_learning_status(),
                    "metaAdCollections": list_meta_ad_collections(),
                    "metaBrandRegistry": registry_summary(),
                    "jobs": list(JOBS.values()),
                    "comfy": comfy_status(),
                })
            elif path == "/api/comfy/status":
                self.send_json(comfy_status())
            elif path == "/api/products":
                self.send_json({"products": list_products()})
            elif path.startswith("/api/products/") and "/asset/" in path:
                parts = path.removeprefix("/api/products/").split("/")
                if len(parts) < 4 or parts[2] != "asset":
                    raise FileNotFoundError(path)
                category, product_id, _, asset_kind, *rest = [unquote(part) for part in parts]
                self.send_file(product_asset(category, product_id, asset_kind, "/".join(rest)))
            elif path == "/api/runs":
                self.send_json({"runs": list_runs()})
            elif path.startswith("/api/runs/"):
                run_id = unquote(path.removeprefix("/api/runs/")).strip("/")
                self.send_json(run_detail(run_id))
            elif path == "/api/events":
                self.send_json({"events": list_events()})
            elif path == "/api/training-sessions":
                self.send_json({"sessions": list_training_sessions()})
            elif path == "/api/reference-learning":
                self.send_json(reference_learning_status())
            elif path == "/api/meta-ads":
                self.send_json({"collections": list_meta_ad_collections()})
            elif path == "/api/meta-brand-registry":
                self.send_json(registry_summary())
            elif path.startswith("/api/training-sessions/"):
                parts = [unquote(part) for part in path.removeprefix("/api/training-sessions/").strip("/").split("/")]
                if len(parts) != 2:
                    raise FileNotFoundError(path)
                self.send_json(training_session_detail(parts[0], parts[1]))
            elif path == "/api/jobs":
                self.send_json({"jobs": list(JOBS.values())})
            elif path.startswith("/api/jobs/") and path.endswith("/log"):
                job_id = unquote(path[len("/api/jobs/"):-len("/log")].strip("/"))
                self.send_json(job_log(job_id))
            elif path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            elif path.startswith("/assets/"):
                self.serve_asset(path.removeprefix("/assets/"))
            elif path.startswith("/training-assets/"):
                self.serve_training_asset(path.removeprefix("/training-assets/"))
            elif path.startswith("/meta-ad-assets/"):
                self.serve_meta_ad_asset(path.removeprefix("/meta-ad-assets/"))
            else:
                self.serve_static(path)
        except Exception as exc:
            self.send_error_json(exc, 404 if isinstance(exc, FileNotFoundError) else 400)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self.read_body()
            if path == "/api/events":
                self.send_json(create_event(payload))
            elif path == "/api/run-event":
                self.send_json(run_event(payload))
            elif path == "/api/open-path":
                self.send_json(open_project_path(payload))
            elif path == "/api/meta-ads/collect":
                self.send_json(collect_meta_ads_job(payload))
            elif path == "/api/meta-brand-registry/collect":
                self.send_json(collect_meta_brand_registry_job(payload))
            elif path.startswith("/api/runs/") and path.endswith("/training-sessions/mixed"):
                run_id = unquote(path[len("/api/runs/"):-len("/training-sessions/mixed")].strip("/"))
                self.send_json(create_mixed_training_session(run_id, payload))
            elif path.startswith("/api/runs/") and path.endswith("/package"):
                run_id = unquote(path[len("/api/runs/"):-len("/package")].strip("/"))
                self.send_json(create_package(run_id))
            elif path.startswith("/api/runs/") and path.endswith("/references/run"):
                run_id = unquote(path[len("/api/runs/"):-len("/references/run")].strip("/"))
                self.send_json(run_reference_pipeline(run_id, payload))
            elif path.startswith("/api/runs/") and path.endswith("/comfy/generate"):
                run_id = unquote(path[len("/api/runs/"):-len("/comfy/generate")].strip("/"))
                self.send_json(run_comfy_generation(run_id, payload))
            elif path.startswith("/api/runs/") and path.endswith("/candidates/selection"):
                run_id = unquote(path[len("/api/runs/"):-len("/candidates/selection")].strip("/"))
                self.send_json(update_candidate_selection(run_id, payload))
            elif path.startswith("/api/runs/") and path.endswith("/stage"):
                run_id = unquote(path[len("/api/runs/"):-len("/stage")].strip("/"))
                self.send_json(run_stage(run_id, payload))
            elif path.startswith("/api/training-sessions/") and path.endswith("/review"):
                parts = [unquote(part) for part in path[len("/api/training-sessions/"):-len("/review")].strip("/").split("/")]
                if len(parts) != 2:
                    raise FileNotFoundError(path)
                self.send_json(update_training_review(parts[0], parts[1], payload))
            elif path.startswith("/api/training-sessions/") and path.endswith("/summary"):
                parts = [unquote(part) for part in path[len("/api/training-sessions/"):-len("/summary")].strip("/").split("/")]
                if len(parts) != 2:
                    raise FileNotFoundError(path)
                self.send_json(summarize_training_session(parts[0], parts[1]))
            elif path.startswith("/api/training-sessions/") and path.endswith("/compare"):
                profile = unquote(path[len("/api/training-sessions/"):-len("/compare")].strip("/"))
                if not profile:
                    raise FileNotFoundError(path)
                self.send_json(compare_training_sessions(profile))
            else:
                self.send_error_json(ValueError("Unknown endpoint"), 404)
        except Exception as exc:
            self.send_error_json(exc)

    def serve_static(self, path: str) -> None:
        if path in {"", "/"}:
            path = "/index.html"
        file_path = safe_child(UI_DIR, path.lstrip("/"))
        if not file_path.exists() or not file_path.is_file():
            file_path = UI_DIR / "index.html"
        self.send_file(file_path)

    def serve_asset(self, asset_path: str) -> None:
        parts = asset_path.split("/", 1)
        if len(parts) != 2:
            raise FileNotFoundError(asset_path)
        run_dir = run_dir_from_id(parts[0])
        file_path = safe_child(run_dir, unquote(parts[1]))
        self.send_file(file_path)

    def serve_training_asset(self, asset_path: str) -> None:
        parts = asset_path.split("/", 2)
        if len(parts) != 3:
            raise FileNotFoundError(asset_path)
        profile, session_id, filename = [unquote(part) for part in parts]
        session_dir = training_session_dir(profile, session_id)
        file_path = safe_child(session_dir / "references", filename)
        self.send_file(file_path)

    def serve_meta_ad_asset(self, asset_path: str) -> None:
        parts = asset_path.split("/", 1)
        if len(parts) != 2:
            raise FileNotFoundError(asset_path)
        search_id, relative_path = [unquote(part) for part in parts]
        file_path = safe_child(META_AD_SEARCHES_DIR, search_id, relative_path)
        self.send_file(file_path)

    def send_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(str(file_path))
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Start Brand Event Console.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5177)
    args = parser.parse_args()

    if not UI_DIR.exists():
        raise SystemExit(f"UI directory not found: {UI_DIR}")
    server = ThreadingHTTPServer((args.host, args.port), ConsoleHandler)
    print(f"Brand Event Console: http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
