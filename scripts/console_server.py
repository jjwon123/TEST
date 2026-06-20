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
JOBS_PATH = ROOT / ".tmp" / "console-jobs" / "jobs.json"
JOBS_LOCK = threading.Lock()

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_manifest import build_manifest, load_candidates, load_prompts, load_references, write_manifest
from core.utils.schema_validation import validate_json
from services.products.library import list_products, load_product, load_product_from_event, split_product_key
from services.ad_reference.brand_registry import registry_summary
from services.ad_reference.registry_metrics import collection_metrics_summary
from services.ad_reference.collection_strategy import strategy_summary
from services.ad_reference.source_mix_metrics import source_mix_summary
from services.ad_strategy.planning_engine import score_planning
from services.ad_strategy.generation import generate_copy
from services.ad_strategy.repository import append_correction, load_examples_for_review, strategy_quality_metrics, update_example_review
from services.marketing_intelligence.insight_brief import INSIGHT_BRIEF_PATH, build_and_save_insight_brief
from services.marketing_intelligence.repository import load_signals, signal_metrics, update_signal_review
from scripts.benchmark_ad_planning import DEFAULT_REPORT, DEFAULT_RESULTS, DEFAULT_REVIEWS, aggregate, evaluate_case, run_external_cases, save_human_review, select_external_concept
from scripts.export_ad_planning_review_packet import build_packet as build_ad_planning_review_packet
from scripts.workflow import approve_stage


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


def recover_persisted_jobs(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    recovered: dict[str, dict[str, Any]] = {}
    recovered_at = datetime.now(timezone.utc).isoformat()
    for record in records:
        job_id = str(record.get("job_id") or "").strip()
        if not job_id:
            continue
        item = dict(record)
        if item.get("status") == "running":
            item["status"] = "interrupted"
            item["finished_at"] = recovered_at
            item["recovery_note"] = "Console restarted before this job reported a final status."
        recovered[job_id] = item
    return recovered


def load_persisted_jobs() -> dict[str, dict[str, Any]]:
    payload = read_json(JOBS_PATH, {"jobs": []})
    records = payload.get("jobs", []) if isinstance(payload, dict) else []
    return recover_persisted_jobs(records if isinstance(records, list) else [])


def persist_jobs() -> None:
    with JOBS_LOCK:
        records = sorted(
            JOBS.values(),
            key=lambda item: str(item.get("started_at") or ""),
            reverse=True,
        )[:200]
        write_json(JOBS_PATH, {"jobs": records})


JOBS.update(load_persisted_jobs())
if JOBS:
    persist_jobs()


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
        "--brand-limit", str(max(1, min(30, int(payload.get("brandLimit") or 5)))),
        "--ads-per-brand", str(max(1, min(20, int(payload.get("adsPerBrand") or 5)))),
        "--scrolls", str(max(0, min(30, int(payload.get("scrolls") or 5)))),
        "--strategy", "registry" if payload.get("strategy") == "registry" else "adaptive",
        "--media-type", "image" if payload.get("mediaType") == "image" else "all",
    ]
    country = str(payload.get("country") or "").strip()
    if country:
        command.extend(["--country", country])
    if payload.get("headful"):
        command.append("--headful")
    return start_process(command, ROOT, f"Meta brand registry: {profile}")


def collect_meta_source_mix_job(payload: dict[str, Any]) -> dict[str, Any]:
    command = [
        python_exe(), "scripts/collect_meta_source_mix.py",
        "--query-limit", str(max(1, min(5, int(payload.get("queryLimit") or 2)))),
        "--ads-per-query", str(max(1, min(20, int(payload.get("adsPerQuery") or 5)))),
    ]
    return start_process(command, ROOT, "Meta source mix fallback")


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
        "strategic_brief": read_json(run_dir / "01_event_brief" / "strategic-brief.json", {}),
        "planning": {
            "contentPlan": read_json(run_dir / "02_content_planning" / "content-plan.json", {}),
            "conceptCandidates": read_json(run_dir / "02_content_planning" / "concept-candidates.json", {}),
            "conceptReview": read_json(run_dir / "02_content_planning" / "concept-review.json", {}),
            "selectedConcept": read_json(run_dir / "02_content_planning" / "selected-concept.json", {}),
            "copyPackage": read_json(run_dir / "02_content_planning" / "copy-package.json", {}),
            "copyReview": read_json(run_dir / "02_content_planning" / "copy-review.json", {}),
            "scorecard": read_json(run_dir / "02_content_planning" / "planning-scorecard.json", {}),
        },
    }


def select_planning_concept(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    run_dir = run_dir_from_id(run_id)
    stage_dir = run_dir / "02_content_planning"
    candidates_doc = read_json(stage_dir / "concept-candidates.json", {})
    concept_id = str(payload.get("conceptId") or "").strip()
    candidates = candidates_doc.get("candidates", [])
    selected = next((item for item in candidates if item.get("conceptId") == concept_id), None)
    if not selected:
        raise ValueError("A valid conceptId is required.")
    reason_tags = normalize_planning_reason_tags(payload.get("reasonTags"))
    rejected = [item.get("conceptId") for item in candidates if item.get("conceptId") != concept_id]
    review = {
        "schemaVersion": "1.0.0",
        "status": "approved",
        "selectedConceptId": concept_id,
        "rejectedConceptIds": rejected,
        "reasonTags": reason_tags,
        "reviewNote": str(payload.get("reviewNote") or ""),
        "approvedAt": datetime.now(timezone.utc).isoformat(),
    }
    brief = read_json(run_dir / "01_event_brief" / "brief.json", {})
    plan = read_json(stage_dir / "content-plan.json", {})
    package = generate_copy(brief, selected, plan.get("deliverables", []), run_dir)
    copy_review = {
        "schemaVersion": "1.0.0",
        "status": "review_pending",
        "approved": False,
        "edits": [],
        "reasonTags": [],
        "reviewNote": "",
    }
    scorecard = score_planning(brief, candidates_doc, package)
    write_json(stage_dir / "concept-review.json", review)
    write_json(stage_dir / "selected-concept.json", {"schemaVersion": "1.0.0", "status": "approved", "concept": selected})
    write_json(stage_dir / "copy-package.json", package)
    write_json(stage_dir / "copy-review.json", copy_review)
    write_json(stage_dir / "planning-scorecard.json", scorecard)
    return {"ok": True, "detail": run_detail(run_id)}


def review_planning_copy(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    run_dir = run_dir_from_id(run_id)
    stage_dir = run_dir / "02_content_planning"
    package = read_json(stage_dir / "copy-package.json", {})
    if package.get("status") != "review_pending":
        raise ValueError("Select a concept and generate a copy package first.")
    approved = bool(payload.get("approved"))
    edits = payload.get("edits", [])
    if not isinstance(edits, list):
        raise ValueError("edits must be a list")
    reason_tags = normalize_planning_reason_tags(payload.get("reasonTags"))
    outputs_by_channel = {item.get("channelId"): item for item in package.get("outputs", [])}
    for edit in edits:
        channel_id = edit.get("channelId")
        if channel_id in outputs_by_channel and isinstance(edit.get("editedCopy"), dict):
            outputs_by_channel[channel_id]["copy"] = edit["editedCopy"]
            outputs_by_channel[channel_id]["characterCount"] = len(str(edit["editedCopy"]))
    if edits:
        package["criticReview"] = {**package.get("criticReview", {}), "status": "human_revised", "issues": []}
    scorecard = score_planning(
        read_json(run_dir / "01_event_brief" / "brief.json", {}),
        read_json(stage_dir / "concept-candidates.json", {}),
        package,
    )
    human_scores = {
        key: max(1, min(5, int(value)))
        for key, value in (payload.get("scores") or {}).items()
        if key in scorecard.get("rubric", {}) and isinstance(value, (int, float))
    }
    if human_scores:
        scorecard["humanRubric"] = human_scores
        scorecard["rubric"].update(human_scores)
        scorecard["averageScore"] = round(sum(scorecard["rubric"].values()) / len(scorecard["rubric"]), 2)
        scorecard["issues"] = [item for item in scorecard["issues"] if item.get("id") != "rubric_below_four"]
        if scorecard["averageScore"] < 4:
            scorecard["issues"].append({"severity": "warning", "id": "rubric_below_four", "message": f"평균 품질 점수가 4점 미만입니다: {scorecard['averageScore']:.2f}"})
        scorecard["status"] = "fail" if scorecard.get("criticalErrorCount") else "warning" if scorecard["issues"] else "pass"
    review = {
        "schemaVersion": "1.0.0",
        "status": "approved" if approved else "changes_requested",
        "approved": approved,
        "edits": edits,
        "reasonTags": reason_tags,
        "reviewNote": str(payload.get("reviewNote") or ""),
        "scores": human_scores,
        "blindPreferred": str(payload.get("blindPreferred") or ""),
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
    }
    if approved and scorecard.get("issues"):
        raise ValueError("Resolve all planning quality warnings before approving final copy.")
    write_json(stage_dir / "copy-package.json", package)
    write_json(stage_dir / "copy-review.json", review)
    selected = read_json(stage_dir / "selected-concept.json", {}).get("concept", {})
    brief = read_json(run_dir / "01_event_brief" / "brief.json", {})
    records = edits or [
        {
            "channelId": output.get("channelId", ""),
            "originalCopy": output.get("copy", {}),
            "editedCopy": output.get("copy", {}),
        }
        for output in package.get("outputs", [])
    ]
    for edit in records:
        append_correction({
            "runId": run_id,
            "eventId": str(brief.get("event_id") or ""),
            "eventName": str(brief.get("event_name") or ""),
            "brandName": str(brief.get("brand", {}).get("name") or brief.get("brand_name") or ""),
            "industry": read_json(run_dir / "01_event_brief" / "strategic-brief.json", {}).get("industry", ""),
            "channelId": edit.get("channelId", ""),
            "model": package.get("model", ""),
            "strategyExampleIds": selected.get("strategyExampleIds", []),
            "originalCopy": edit.get("originalCopy", {}),
            "editedCopy": edit.get("editedCopy", {}),
            "reasonTags": reason_tags,
            "qaResult": read_json(stage_dir / "planning-scorecard.json", {}),
            "approved": approved,
            "humanScores": human_scores,
            "blindPreferred": str(payload.get("blindPreferred") or ""),
        })
    write_json(stage_dir / "planning-scorecard.json", scorecard)
    return {"ok": True, "detail": run_detail(run_id)}


def review_strategy_example(payload: dict[str, Any]) -> dict[str, Any]:
    example_id = str(payload.get("exampleId") or "").strip()
    if not example_id:
        raise ValueError("exampleId is required")
    updated = update_example_review(example_id, payload)
    return {"ok": True, "example": updated, "metrics": strategy_quality_metrics(), "reviewPacket": ad_planning_review_packet()}


def marketing_signal_packet(limit: int = 24) -> dict[str, Any]:
    signals = load_signals()
    metrics = signal_metrics(signals)
    enriched = [with_signal_recommendation(item) for item in signals]
    ordered = sorted(enriched, key=lambda item: (
        item.get("review", {}).get("decision") != "unreviewed",
        -int(item.get("reviewRecommendation", {}).get("score") or 0),
        evidence_priority(item),
        item.get("topic", ""),
        item.get("id", ""),
    ))
    return {
        "signals": ordered[:limit],
        "metrics": metrics,
        "reviewQueue": [item for item in ordered if item.get("review", {}).get("decision") == "unreviewed"][:limit],
        "insightBrief": read_json(INSIGHT_BRIEF_PATH, {}),
    }


def with_signal_recommendation(signal: dict[str, Any]) -> dict[str, Any]:
    score, reasons = signal_recommendation_score(signal)
    if score >= 8:
        label = "우선 검토"
    elif score >= 6:
        label = "검토 후보"
    else:
        label = "보조 후보"
    return {
        **signal,
        "reviewRecommendation": {
            "score": score,
            "label": label,
            "reasons": reasons,
        },
    }


def signal_recommendation_score(signal: dict[str, Any]) -> tuple[int, list[str]]:
    score = int(signal.get("strength") or 0) + int(signal.get("freshness") or 0) + int(signal.get("confidence") or 0)
    reasons: list[str] = []
    evidence_type = str(signal.get("evidenceType") or "")
    usable_for = set(signal.get("usableFor") or [])
    if evidence_type in {"pain", "desire", "objection"}:
        score += 2
        reasons.append("타깃 감정/저항을 바로 설명할 수 있음")
    elif evidence_type in {"timing", "trend"}:
        score += 1
        reasons.append("시즌·트렌드 훅으로 확장 가능")
    elif evidence_type == "channel_pattern":
        score += 1
        reasons.append("채널 문구 구조 검토에 유용")
    if {"concept", "copy"}.issubset(usable_for):
        score += 1
        reasons.append("콘셉트와 카피에 모두 연결 가능")
    if "random_seed" in set(signal.get("riskFlags") or []):
        reasons.append("랜덤 가설이라 선택 전 사실 근거로는 사용 금지")
    if not reasons:
        reasons.append("검토 가능한 후보")
    return max(1, min(10, score)), reasons[:3]


def evidence_priority(signal: dict[str, Any]) -> int:
    return {
        "pain": 0,
        "desire": 1,
        "objection": 2,
        "timing": 3,
        "trend": 4,
        "channel_pattern": 5,
    }.get(str(signal.get("evidenceType") or ""), 9)


def review_marketing_signal(payload: dict[str, Any]) -> dict[str, Any]:
    signal_id = str(payload.get("signalId") or "").strip()
    if not signal_id:
        raise ValueError("signalId is required")
    updated = update_signal_review(signal_id, {
        "decision": payload.get("decision"),
        "reasonTags": payload.get("reasonTags") or [],
        "reviewNote": payload.get("reviewNote") or "",
    })
    return {"ok": True, "signal": updated, "marketingSignals": marketing_signal_packet()}


def build_marketing_insight_brief(payload: dict[str, Any]) -> dict[str, Any]:
    brief = build_and_save_insight_brief(
        event_id=str(payload.get("eventId") or "general"),
        industry=str(payload.get("industry") or "cosmetics_skincare"),
        topic=str(payload.get("topic") or ""),
        minimum_selected=max(1, int(payload.get("minimumSelected") or 3)),
    )
    return {"ok": True, "insightBrief": brief, "marketingSignals": marketing_signal_packet()}


def run_marketing_signal_job(payload: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or "random_seed").strip().lower()
    command = [python_exe(), "scripts/collect_marketing_signals.py"]
    label = "marketing signal review sheet export"
    if mode == "random_seed":
        count = max(1, int(payload.get("count") or 50))
        industry = str(payload.get("industry") or "cosmetics_skincare")
        topic = str(payload.get("topic") or "daily_random_seed")
        command.extend(["--industry", industry, "--topic", topic, "--random-seed", "--count", str(count), "--export-review"])
        if payload.get("seed") not in (None, ""):
            command.extend(["--seed", str(payload["seed"])])
        label = f"marketing signal random seed {count}"
    elif mode == "export":
        command.append("--export-review")
        label = "marketing signal review sheet export"
    elif mode == "import_dry_run":
        command.append("--import-review")
        label = "marketing signal review sheet import dry-run"
    elif mode == "import_apply":
        command.extend(["--import-review", "--apply"])
        label = "marketing signal review sheet import apply"
    elif mode == "public_snapshot":
        snapshot = str(payload.get("snapshot") or payload.get("publicSnapshot") or "").strip()
        if not snapshot:
            raise ValueError("snapshot is required for public_snapshot mode")
        industry = str(payload.get("industry") or "cosmetics_skincare")
        topic = str(payload.get("topic") or "public_marketing_signals")
        command.extend(["--industry", industry, "--topic", topic, "--public-snapshot", snapshot, "--export-review"])
        if payload.get("autoSelect"):
            command.append("--auto-select-public")
        label = "marketing signal public snapshot import"
    elif mode == "public_capture":
        url = str(payload.get("url") or payload.get("captureUrl") or "").strip()
        if not url:
            raise ValueError("url is required for public_capture mode")
        industry = str(payload.get("industry") or "cosmetics_skincare")
        topic = str(payload.get("topic") or "public_web_capture")
        source_kind = str(payload.get("sourceKind") or "public_web")
        snapshot_output = str(payload.get("snapshotOutput") or ".tmp/marketing-signals/public-capture-latest.json")
        command.extend([
            "--industry", industry,
            "--topic", topic,
            "--capture-url", url,
            "--source-kind", source_kind,
            "--snapshot-output", snapshot_output,
            "--export-review",
        ])
        label = "marketing signal public URL capture"
    else:
        raise ValueError("mode must be random_seed, export, import_dry_run, import_apply, public_snapshot, or public_capture")
    return start_process(command, ROOT, label)


def review_planning_benchmark(payload: dict[str, Any]) -> dict[str, Any]:
    case_id = str(payload.get("caseId") or "").strip()
    if not case_id:
        raise ValueError("caseId is required")
    save_human_review(case_id, payload)
    report = refresh_planning_benchmark()
    reviewed_case = next(item for item in report.get("cases", []) if item.get("caseId") == case_id)
    return {"ok": True, "case": reviewed_case, "report": report, "metrics": strategy_quality_metrics(), "reviewPacket": ad_planning_review_packet()}


def select_planning_benchmark_concept(payload: dict[str, Any]) -> dict[str, Any]:
    case_id = str(payload.get("caseId") or "").strip()
    concept_id = str(payload.get("conceptId") or "").strip()
    if not case_id or not concept_id:
        raise ValueError("caseId and conceptId are required")
    select_external_concept(case_id, concept_id)
    dataset = read_json(ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json", {})
    case = next((item for item in dataset.get("cases", []) if item.get("id") == case_id), None)
    if not case:
        raise ValueError("Unknown benchmark case.")
    run_external_cases({"cases": [case]}, DEFAULT_RESULTS)
    report = refresh_planning_benchmark()
    selected_case = next(item for item in report.get("cases", []) if item.get("caseId") == case_id)
    return {"ok": True, "case": selected_case, "report": report, "metrics": strategy_quality_metrics(), "reviewPacket": ad_planning_review_packet()}


def run_planning_pilot_job(payload: dict[str, Any]) -> dict[str, Any]:
    limit = max(1, int(payload.get("limit") or 5))
    return start_process([python_exe(), "scripts/run_ad_planning_pilot.py", "--limit", str(limit)], ROOT, f"ad planning pilot {limit}")


def run_ad_strategy_review_sheet_job(payload: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or "export").strip().lower()
    command = [python_exe(), "scripts/manage_ad_strategy_review_sheet.py"]
    label = "ad strategy review sheet export"
    if mode == "export":
        limit = max(1, int(payload.get("limit") or 30))
        command.extend(["--limit", str(limit)])
        label = f"ad strategy review sheet export {limit}"
    elif mode == "import_dry_run":
        command.append("--import-sheet")
        label = "ad strategy review sheet import dry-run"
    elif mode == "import_apply":
        command.extend(["--import-sheet", "--apply"])
        label = "ad strategy review sheet import apply"
    else:
        raise ValueError("mode must be export, import_dry_run, or import_apply")
    return start_process(command, ROOT, label)


def run_ad_planning_benchmark_review_sheet_job(payload: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or "export").strip().lower()
    command = [python_exe(), "scripts/manage_ad_planning_benchmark_review_sheet.py"]
    label = "ad planning benchmark review sheet export"
    if mode == "export":
        limit = max(1, int(payload.get("limit") or 5))
        command.extend(["--limit", str(limit)])
        label = f"ad planning benchmark review sheet export {limit}"
    elif mode == "import_dry_run":
        command.append("--import-sheet")
        label = "ad planning benchmark review sheet import dry-run"
    elif mode == "import_apply":
        command.extend(["--import-sheet", "--apply"])
        label = "ad planning benchmark review sheet import apply"
    else:
        raise ValueError("mode must be export, import_dry_run, or import_apply")
    return start_process(command, ROOT, label)


def refresh_planning_benchmark() -> dict[str, Any]:
    dataset = read_json(ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json", {})
    reviews = {item["caseId"]: item for item in read_json(DEFAULT_REVIEWS, {"reviews": []}).get("reviews", [])}
    external = {item["caseId"]: item for item in read_json(DEFAULT_RESULTS, {"results": []}).get("results", [])}
    cases = [evaluate_case(item, reviews.get(item["id"], {}), external.get(item["id"], {})) for item in dataset.get("cases", [])]
    report = aggregate(cases, dataset.get("target", {}))
    write_json(DEFAULT_REPORT, report)
    return report


def ad_planning_review_packet() -> dict[str, Any]:
    dataset = read_json(ROOT / "assets" / "rules" / "cosmetics-planning-benchmark.json", {"cases": []})
    benchmark = read_json(DEFAULT_REPORT, {})
    external = read_json(DEFAULT_RESULTS, {"results": []})
    reviews = read_json(DEFAULT_REVIEWS, {"reviews": []})
    return build_ad_planning_review_packet(
        dataset=dataset,
        benchmark=benchmark,
        external_results=external,
        human_reviews=reviews,
        strategy_examples=load_examples_for_review(),
        strategy_metrics=strategy_quality_metrics(),
        provider="local",
        pilot_limit=5,
    )


def normalize_planning_reason_tags(value: Any) -> list[str]:
    allowed = {
        "generic", "weak_insight", "awkward_korean", "brand_mismatch",
        "unsupported_claim", "copied_expression", "weak_cta", "channel_mismatch",
        "good_hook", "good_structure", "strong_product_link",
    }
    values = value if isinstance(value, list) else split_lines(value)
    return [item for item in dict.fromkeys(str(item).strip() for item in values) if item in allowed]


def approve_run_stage(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    run_dir = run_dir_from_id(run_id)
    stage = str(payload.get("stage") or "").strip()
    if not stage:
        raise ValueError("stage is required")
    approve_stage(run_dir, stage, approver=str(payload.get("approver") or "console"), note=str(payload.get("note") or ""))
    return {"ok": True, "detail": run_detail(run_id)}


def split_lines(value: str) -> list[str]:
    if isinstance(value, list):
        return value
    return [line.strip() for line in str(value or "").replace(",", "\n").splitlines() if line.strip()]


def create_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_name = payload.get("eventName") or payload.get("event_name") or "New Event"
    brand_name = payload.get("brandName") or payload.get("brand_name") or ""
    objective = payload.get("objective") or payload.get("purpose") or ""
    event_dir = safe_child(EVENTS_DIR, slugify(event_name))
    suffix = 2
    while event_dir.exists():
        event_dir = safe_child(EVENTS_DIR, f"{slugify(event_name)}-{suffix}")
        suffix += 1

    event_input = {
        "brandName": brand_name,
        "eventName": event_name,
        "objective": objective,
        "purpose": objective,
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
    validate_json(
        event_input,
        read_json(ROOT / "core" / "schemas" / "event-input.schema.json"),
        data_label="new event input",
        schema_label="core/schemas/event-input.schema.json",
    )
    validate_json(
        brand_guide,
        read_json(ROOT / "core" / "schemas" / "brand-guide.schema.json"),
        data_label="new brand guide",
        schema_label="core/schemas/brand-guide.schema.json",
    )
    event_dir.mkdir(parents=True)
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
    run_status = read_json(run_dir / "run-status.json", {})
    qa_stage_status = run_status.get("stage_status", {}).get("06_qa_packaging")
    if qa_stage_status != "approved":
        raise ValueError("Final production package requires approved 06_qa_packaging.")
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
    job_id = f"{time.time_ns()}-{slugify(label)}"
    log_dir = ROOT / ".tmp" / "console-jobs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{job_id}.log"
    JOBS[job_id] = {
        "job_id": job_id,
        "label": label,
        "status": "running",
        "command": command,
        "log_path": str(log_path),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    persist_jobs()

    def worker() -> None:
        with log_path.open("w", encoding="utf-8", errors="ignore") as log:
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, text=True, env=process_env)
            JOBS[job_id]["pid"] = process.pid
            persist_jobs()
            code = process.wait()
        JOBS[job_id]["status"] = "done" if code == 0 else "failed"
        JOBS[job_id]["returncode"] = code
        JOBS[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
        persist_jobs()

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
                    "metaBrandMetrics": collection_metrics_summary(),
                    "metaBrandStrategy": strategy_summary(),
                    "metaSourceMixMetrics": source_mix_summary(),
                    "operationsReadiness": read_json(ROOT / ".tmp" / "operations-readiness" / "latest-operations-readiness.json", {}),
                    "repeatedOperations": read_json(ROOT / ".tmp" / "repeated-operations" / "latest-repeated-operations.json", {}),
                    "adStrategyQuality": strategy_quality_metrics(),
                    "adStrategyExamples": load_examples_for_review(),
                    "marketingSignals": marketing_signal_packet(),
                    "planningBenchmark": read_json(DEFAULT_REPORT, {}),
                    "planningReviewPacket": ad_planning_review_packet(),
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
            elif path == "/api/meta-brand-metrics":
                self.send_json(collection_metrics_summary())
            elif path == "/api/meta-brand-strategy":
                self.send_json(strategy_summary())
            elif path == "/api/meta-source-mix":
                self.send_json(source_mix_summary())
            elif path == "/api/ad-strategy-quality":
                self.send_json(strategy_quality_metrics())
            elif path == "/api/ad-strategy-examples":
                self.send_json({"examples": load_examples_for_review(), "metrics": strategy_quality_metrics()})
            elif path == "/api/marketing-signals":
                self.send_json(marketing_signal_packet())
            elif path == "/api/planning-benchmark":
                self.send_json(refresh_planning_benchmark())
            elif path == "/api/planning-review-packet":
                self.send_json(ad_planning_review_packet())
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
            elif path == "/api/meta-source-mix/collect":
                self.send_json(collect_meta_source_mix_job(payload))
            elif path == "/api/ad-strategy/review":
                self.send_json(review_strategy_example(payload))
            elif path == "/api/marketing-signals/review":
                self.send_json(review_marketing_signal(payload))
            elif path == "/api/marketing-signals/insight-brief":
                self.send_json(build_marketing_insight_brief(payload))
            elif path == "/api/marketing-signals/job":
                self.send_json(run_marketing_signal_job(payload))
            elif path == "/api/planning-benchmark/review":
                self.send_json(review_planning_benchmark(payload))
            elif path == "/api/planning-benchmark/concept-selection":
                self.send_json(select_planning_benchmark_concept(payload))
            elif path == "/api/planning-pilot/run":
                self.send_json(run_planning_pilot_job(payload))
            elif path == "/api/ad-strategy/review-sheet":
                self.send_json(run_ad_strategy_review_sheet_job(payload))
            elif path == "/api/ad-planning/benchmark-review-sheet":
                self.send_json(run_ad_planning_benchmark_review_sheet_job(payload))
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
            elif path.startswith("/api/runs/") and path.endswith("/planning/concept"):
                run_id = unquote(path[len("/api/runs/"):-len("/planning/concept")].strip("/"))
                self.send_json(select_planning_concept(run_id, payload))
            elif path.startswith("/api/runs/") and path.endswith("/planning/copy-review"):
                run_id = unquote(path[len("/api/runs/"):-len("/planning/copy-review")].strip("/"))
                self.send_json(review_planning_copy(run_id, payload))
            elif path.startswith("/api/runs/") and path.endswith("/approve"):
                run_id = unquote(path[len("/api/runs/"):-len("/approve")].strip("/"))
                self.send_json(approve_run_stage(run_id, payload))
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
