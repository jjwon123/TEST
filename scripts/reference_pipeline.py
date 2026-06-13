#!/usr/bin/env python3
"""Run-scoped reference collection planning and download helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json
from core.utils.rulebook import (
    detect_event_profile,
    profile_reject_terms,
    profile_search_queries,
    profile_selection_gates,
)
from core.utils.reference_training import score_record_against_training, training_summary

try:
    from PIL import Image, ImageStat
except ImportError:  # pragma: no cover - the pipeline can still plan/queue sources.
    Image = None
    ImageStat = None


PLAN_NAME = "reference-collection-plan.json"
MANIFEST_NAME = "reference-manifest.json"
DEFAULT_LIMIT = 30
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
PINTEREST_STORAGE_STATE = ROOT / "assets" / "references" / "pinterest-storage-state.json"
BULLION_REJECT_TERMS = [
    "kids toy style",
    "cute mascot centered",
    "cartoon camping",
    "theme park",
    "picnic toy scene",
    "wine bottle",
    "random package box",
    "childlike 3d illustration",
    "excessive kawaii mood",
    "fake text poster",
    "cute camping",
    "character picnic",
    "toy diorama",
    "kawaii event poster",
    "cartoon promotion",
    "toy-like",
    "childish",
    "kawaii",
    "mascot",
    "camping",
    "picnic",
    "theme park",
    "wine",
    "fake text",
]
BULLION_SELECTION_GATES = {
    "brandFit": 7.0,
    "eventFit": 7.0,
    "productRelevance": 7.0,
    "seriousnessFit": 6.0,
    "riskLevelMax": 4.0,
}
BULLION_REJECT_TERMS = profile_reject_terms("bullion_investment") or BULLION_REJECT_TERMS
BULLION_SELECTION_GATES = profile_selection_gates("bullion_investment") or BULLION_SELECTION_GATES


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def pinterest_session_status(state_path: Path = PINTEREST_STORAGE_STATE) -> dict[str, Any]:
    status: dict[str, Any] = {
        "path": str(state_path),
        "exists": state_path.exists(),
        "usable": False,
        "cookie_count": 0,
        "pinterest_cookie_count": 0,
    }
    if not state_path.exists():
        status["error"] = "storage state file does not exist"
        return status
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        status["error"] = f"invalid JSON: {exc}"
        return status
    cookies = payload.get("cookies") if isinstance(payload, dict) else []
    if not isinstance(cookies, list):
        status["error"] = "storage state does not contain a cookies list"
        return status
    pinterest_cookies = [
        cookie for cookie in cookies
        if "pinterest." in str(cookie.get("domain", "")).lower()
    ]
    status["cookie_count"] = len(cookies)
    status["pinterest_cookie_count"] = len(pinterest_cookies)
    status["usable"] = bool(pinterest_cookies)
    return status


def references_dir(run_dir: Path) -> Path:
    path = run_dir / "references"
    path.mkdir(parents=True, exist_ok=True)
    (path / "raw").mkdir(exist_ok=True)
    return path


def plan_path(run_dir: Path) -> Path:
    return references_dir(run_dir) / PLAN_NAME


def manifest_path(run_dir: Path) -> Path:
    return references_dir(run_dir) / MANIFEST_NAME


def create_plan(run_dir: Path, *, force: bool = False) -> dict[str, Any]:
    path = plan_path(run_dir)
    if path.exists() and not force:
        return read_json(path)

    event_input = read_json(run_dir / "event-input.json")
    brand_guide = read_json(run_dir / "brand-guide.json", default={})
    references = [str(item).strip() for item in event_input.get("references", []) if str(item).strip()]
    channels = [str(item).strip() for item in event_input.get("channels", []) if str(item).strip()]
    base_terms = [
        brand_guide.get("brandName", ""),
        event_input.get("eventName", ""),
    ]

    search_queries = build_search_queries(event_input, references, base_terms, channels, brand_guide=brand_guide)
    event_profile = detect_event_profile(event_input, brand_guide)
    plan = {
        "run_id": run_dir.name,
        "created_at": now(),
        "status": "planned",
        "intent": {
            "event_name": event_input.get("eventName") or event_input.get("name") or run_dir.name,
            "objective": event_input.get("objective", ""),
            "target": event_input.get("target", ""),
            "channels": channels,
            "event_references": references,
            "event_profile": event_profile,
        },
        "rule_sources": {
            "brand_persona": "assets/rules/brand-persona.json",
            "event_rules": "assets/rules/event-rules.json",
            "reference_rules": "assets/rules/reference-rules.json",
            "visual_avoid_rules": "assets/rules/visual-avoid-rules.json",
        },
        "search_queries": [
            {
                "query_id": f"q{index:02d}",
                "query": query,
                "pinterest_search_url": pinterest_search_url(query),
                "status": "ready_for_board_curation",
            }
            for index, query in enumerate(search_queries, start=1)
        ],
        "source_boards": [],
        "notes": [
            "Use search_queries to curate a Pinterest board, then add the board URL with --add-reference-source.",
            "Pinterest save-to-board is intentionally kept outside the downloader because login, rate limits, and UI changes are brittle.",
        ],
    }
    write_json(path, plan)
    return plan


def build_search_queries(
    event_input: dict[str, Any],
    references: list[str],
    base_terms: list[Any],
    channels: list[str],
    brand_guide: dict[str, Any] | None = None,
) -> list[str]:
    queries: list[str] = []
    detected_profile = detect_event_profile(event_input, brand_guide)
    if detected_profile != "general":
        profile_queries = profile_search_queries(detected_profile, channels)
        if profile_queries:
            return profile_queries[:10]
    category_anchor = infer_category_anchor(event_input)
    category_terms = category_reference_terms(category_anchor)
    format_terms = format_reference_terms(channels)
    for category in category_terms:
        for output_format in format_terms:
            queries.append(f"{category} {output_format} 디자인")
    queries.extend(channel_design_queries(category_anchor, channels))
    return dedupe_keep_order(queries)[:10]


def category_reference_terms(category_anchor: str) -> list[str]:
    if category_anchor == "금융":
        return ["프리미엄 금융 상담 이벤트", "금 투자 상담", "금 자산관리 프로모션"]
    if category_anchor == "화장품":
        return ["화장품 프로모션", "뷰티 이벤트", "스킨케어 광고"]
    if category_anchor == "주얼리":
        return ["주얼리 브랜드", "주얼리 이벤트", "액세서리 프로모션"]
    if category_anchor == "향수":
        return ["향수 브랜드", "향수 프로모션", "뷰티 이벤트"]
    if category_anchor == "식음료":
        return ["카페 이벤트", "식품 프로모션", "브랜드 이벤트"]
    return ["브랜드 이벤트", "프로모션", "이벤트"]


def format_reference_terms(channels: list[str]) -> list[str]:
    channel_text = " ".join(channels).lower()
    terms = ["배너"]
    if "instagram" in channel_text or "인스타" in channel_text:
        terms.extend(["인스타 배너", "카드뉴스"])
    if "blog" in channel_text or "블로그" in channel_text or "naver" in channel_text:
        terms.extend(["블로그 배너", "네이버 블로그 배너"])
    if "community" in channel_text or "notice" in channel_text or "공지" in channel_text:
        terms.append("공지 배너")
    if "card" in channel_text or "카드" in channel_text:
        terms.append("카드뉴스")
    return dedupe_keep_order(terms)


def visual_reference_terms(event_input: dict[str, Any], references: list[str]) -> list[str]:
    text = " ".join(
        [str(event_input.get(key, "")) for key in ("eventName", "objective", "target", "offer")]
        + [str(item) for item in references]
    ).lower()
    terms: list[str] = []
    if is_bullion_investment_event(event_input):
        return [
            "premium gold investment campaign visual",
            "gold bar premium product photography",
            "bullion investment advertising",
            "luxury financial consultation poster",
            "high trust financial brand campaign",
        ]
    if any(token in text for token in ("앰플", "serum", "ampoule")):
        terms.append("ampoule serum glass bottle")
    if any(token in text for token in ("튜브", "tube", "크림", "cream", "선크림", "sunscreen", "핸드크림")):
        terms.append("cosmetic tube cream product")
    if any(token in text for token in ("향수", "perfume", "fragrance", "오드퍼퓸", "eau de parfum")):
        terms.append("perfume fragrance bottle product")
        terms.append("luxury perfume still life")
    if any(token in text for token in ("주얼리", "jewelry", "jewellery", "반지", "ring", "목걸이", "necklace", "귀걸이", "earring")):
        terms.append("fine jewelry product photography")
        terms.append("ring necklace luxury still life")
    if any(token in text for token in ("유리", "투명", "transparent", "glass")):
        terms.append("transparent glass cosmetic bottle")
    if any(token in text for token in ("수분", "촉촉", "hydrating", "moisture")):
        terms.append("hydrating skincare water splash")
    if any(token in text for token in ("진정", "민감", "calming", "sensitive")):
        terms.append("calming skincare cica green clean")
    if any(token in text for token in ("하얀", "흰", "white", "clean")):
        terms.append("minimal white background product hero")
    if any(token in text for token in ("클린", "clean beauty")):
        terms.append("clean beauty editorial product")
    if not terms:
        terms.append(short_query(" ".join(references)) or "brand product visual")
    return dedupe_keep_order(terms)[:5]


def mood_reference_terms(event_input: dict[str, Any], references: list[str]) -> list[str]:
    text = " ".join(
        [str(event_input.get(key, "")) for key in ("eventName", "objective", "target", "offer")]
        + [str(item) for item in references]
    ).lower()
    terms: list[str] = []
    if is_bullion_investment_event(event_input):
        return [
            "premium financial trust",
            "luxury gold asset management",
            "calm consultation event visual",
        ]
    if any(token in text for token in ("봄", "spring", "벚꽃", "플라워", "flower", "pastel")):
        terms.append("spring pastel fresh floral")
    if any(token in text for token in ("크리스마스", "christmas", "holiday", "연말", "겨울", "winter")):
        terms.append("christmas holiday festive red green")
    if any(token in text for token in ("럭셔리", "고급", "premium", "luxury")):
        terms.append("premium luxury editorial")
    return dedupe_keep_order(terms)


def channel_design_queries(category_anchor: str, channels: list[str]) -> list[str]:
    channel_text = " ".join(channels).lower()
    korean_queries: list[str] = []
    if "instagram" in channel_text or "인스타" in channel_text:
        korean_queries.append(f"{category_anchor} 인스타그램 배너 디자인")
    if "blog" in channel_text or "블로그" in channel_text or "naver" in channel_text:
        korean_queries.append(f"{category_anchor} 블로그 배너 디자인")
    if "community" in channel_text or "notice" in channel_text or "공지" in channel_text:
        korean_queries.append(f"{category_anchor} 공지 배너 디자인")
    if "card" in channel_text or "카드" in channel_text:
        korean_queries.append(f"{category_anchor} 카드뉴스 디자인")
    if korean_queries:
        return korean_queries
    queries: list[str] = []
    if "instagram" in channel_text:
        queries.append(f"{category_anchor} instagram ad design template")
    if "blog" in channel_text:
        queries.append(f"{category_anchor} blog banner editorial layout")
    if "card" in channel_text or "카드" in channel_text:
        queries.append(f"{category_anchor} card news layout design")
    return queries


def infer_category_anchor(event_input: dict[str, Any]) -> str:
    text = " ".join(
        str(event_input.get(key, ""))
        for key in ("eventName", "objective", "target", "offer")
    ).lower()
    if any(token in text for token in ("주얼리", "쥬얼리", "귀금속", "보석", "반지", "목걸이", "jewelry", "jewellery", "ring", "necklace", "earring")):
        return "주얼리"
    if any(token in text for token in ("향수", "퍼퓸", "프래그런스", "perfume", "fragrance", "eau de parfum")):
        return "향수"
    if any(token in text for token in ("화장품", "스킨케어", "앰플", "세럼", "크림", "선크림", "뷰티", "skincare", "beauty", "cosmetic", "serum", "ampoule", "tube", "cream", "sunscreen")):
        return "화장품"
    if any(token in text for token in ("금", "은", "투자", "금융", "은행", "자산", "상담", "gold", "silver", "finance", "bank", "investment")):
        return "금융"
    if any(token in text for token in ("음식", "식품", "카페", "레스토랑", "푸드", "restaurant", "food", "cafe")):
        return "식음료"
    if any(token in text for token in ("주얼리", "jewelry", "jewellery", "반지", "목걸이", "귀걸이", "ring", "necklace", "earring")):
        return "jewelry luxury product ad"
    if any(token in text for token in ("향수", "perfume", "fragrance", "오드퍼퓸", "eau de parfum")):
        return "perfume fragrance product ad"
    if any(token in text for token in ("피부", "앰플", "뷰티", "화장품", "튜브", "크림", "skincare", "beauty", "cosmetic", "tube", "cream")):
        return "skincare cosmetic product ad"
    if any(token in text for token in ("금", "은", "투자", "gold", "silver", "finance")):
        return "premium gold finance event banner"
    if any(token in text for token in ("음식", "카페", "restaurant", "food", "cafe")):
        return "food brand promotion design"
    return "brand campaign design"


def fallback_reference_queries(category_anchor: str, mood_terms: list[str]) -> list[str]:
    mood = f" {mood_terms[0]}" if mood_terms else ""
    if "gold" in category_anchor or "finance" in category_anchor:
        return bullion_investment_search_queries([])
    if "jewelry" in category_anchor:
        return [
            f"fine jewelry campaign photography{mood}",
            f"luxury ring necklace advertisement layout{mood}",
            "korean jewelry brand instagram ad design",
        ]
    if "perfume" in category_anchor:
        return [
            f"perfume bottle product photography{mood}",
            f"luxury fragrance advertisement layout{mood}",
            "korean perfume brand instagram ad design",
        ]
    if "skincare" in category_anchor or "cosmetic" in category_anchor:
        return [
            f"korean skincare product advertisement layout{mood}",
            f"clean beauty product photography white background{mood}",
            f"cosmetic product hero campaign layout{mood}",
        ]
    return [
        f"brand campaign design reference{mood}",
        f"product promotion advertising photography{mood}",
    ]


def is_bullion_investment_event(event_input: dict[str, Any]) -> bool:
    text = " ".join(
        str(event_input.get(key, ""))
        for key in ("brandName", "eventName", "objective", "purpose", "target", "offer", "notes")
    )
    references = event_input.get("references", [])
    if isinstance(references, list):
        text += " " + " ".join(str(item) for item in references)
    text = text.lower()
    tokens = (
        "bullion", "gold", "silver", "investment", "consultation", "asset management",
        "금", "은", "골드", "실버", "금거래", "금융", "투자", "상담", "자산", "시세",
    )
    return any(token in text for token in tokens)


def bullion_investment_search_queries(channels: list[str]) -> list[str]:
    rule_queries = profile_search_queries("bullion_investment", channels)
    if rule_queries:
        return rule_queries[:10]
    base = [
        "premium gold investment campaign visual",
        "luxury financial consultation poster",
        "gold bar premium product photography",
        "bullion investment advertising",
        "high trust financial brand campaign",
        "premium consultation event visual",
        "gold asset management visual",
        "premium finance instagram campaign design",
        "gold investment card news layout",
        "luxury bullion consultation banner",
    ]
    channel_text = " ".join(channels).lower()
    if "blog" in channel_text or "naver" in channel_text or "블로그" in channel_text:
        base.append("premium gold investment blog cover")
    if "community" in channel_text or "notice" in channel_text or "공지" in channel_text:
        base.append("financial consultation notice banner")
    return dedupe_keep_order(base)[:10]


def add_source(
    run_dir: Path,
    url: str,
    *,
    label: str = "",
    limit: int = DEFAULT_LIMIT,
    allow_page_fallback: bool = False,
) -> dict[str, Any]:
    plan = create_plan(run_dir)
    label = safe_slug(label or source_slug(url))
    existing = next(
        (item for item in plan.get("source_boards", []) if item.get("source_id") == label or item.get("label") == label),
        None,
    )
    source_id = str(existing.get("source_id")) if existing else unique_source_id(plan.get("source_boards", []), label)
    record = {
        "source_id": source_id,
        "label": label,
        "url": url,
        "limit": max(1, int(limit)),
        "status": "queued",
        "added_at": now(),
        "collector": "gallery-dl",
        "allow_page_fallback": allow_page_fallback,
        "output_dir": str(Path("references") / "raw" / f"{source_id}-originals"),
    }
    if existing:
        existing.update(record)
        existing["status"] = "queued"
    else:
        plan.setdefault("source_boards", []).append(record)
    plan["status"] = "sources_queued"
    write_json(plan_path(run_dir), plan)
    return existing or record


def collect_sources(run_dir: Path, *, use_cookies: bool = True, only_source: str | None = None) -> dict[str, Any]:
    plan = create_plan(run_dir)
    sources = [
        item for item in plan.get("source_boards", [])
        if item.get("status") in {"queued", "failed"} and (not only_source or item.get("source_id") == only_source)
    ]
    if not sources:
        manifest = load_manifest(run_dir)
        manifest["updated_at"] = now()
        manifest.setdefault("notes", []).append("No queued reference sources.")
        write_json(manifest_path(run_dir), manifest)
        return manifest

    manifest = load_manifest(run_dir)
    for source in sources:
        source_id = source["source_id"]
        output_dir = references_dir(run_dir) / "raw" / f"{source_id}-originals"
        output_dir.mkdir(parents=True, exist_ok=True)
        source["status"] = "collecting"
        source["started_at"] = now()
        write_json(plan_path(run_dir), plan)

        result = run_gallery_dl(
            source["url"],
            output_dir=output_dir,
            limit=int(source.get("limit") or DEFAULT_LIMIT),
            use_cookies=use_cookies,
        )
        records = records_from_output(output_dir, source)
        fallback_summary: dict[str, Any] = {}
        if result.returncode != 0 or not records:
            fallback_summary = run_playwright_collection_fallback(
                source["url"],
                output_dir=output_dir,
                limit=int(source.get("limit") or DEFAULT_LIMIT),
                allow_page_fallback=bool(source.get("allow_page_fallback")),
            )
            records = records_from_output(output_dir, source)
        source["completed_at"] = now()
        source["returncode"] = result.returncode
        source["status"] = "collected" if result.returncode == 0 and records else "failed"
        source["downloaded_count"] = len(records)
        source["log_path"] = str((output_dir / "gallery-dl.log").relative_to(run_dir))
        source["fallback_summary"] = fallback_summary
        if records and fallback_summary:
            source["status"] = "collected"

        manifest.setdefault("sources", {})[source_id] = {
            "source_id": source_id,
            "url": source["url"],
            "label": source.get("label", source_id),
            "status": source["status"],
            "output_dir": str(output_dir.relative_to(run_dir)),
            "downloaded_count": len(records),
            "collected_at": source["completed_at"],
            "fallback_summary": fallback_summary,
        }
        upsert_assets(manifest, records)
        write_json(plan_path(run_dir), plan)
        write_json(manifest_path(run_dir), manifest)

    manifest["updated_at"] = now()
    manifest["asset_count"] = len(manifest.get("assets", []))
    write_json(manifest_path(run_dir), manifest)
    return manifest


def import_local_reference_source(
    run_dir: Path,
    source_dir: Path,
    *,
    label: str = "",
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(source_dir)
    source_id = safe_slug(label or source_dir.name)
    target_dir = references_dir(run_dir) / "raw" / f"{source_id}-local"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for image_path in sorted(source_dir.rglob("*")):
        if image_path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        copied += 1
        shutil.copy2(image_path, target_dir / image_path.name)
        if copied >= max(1, limit):
            break

    plan = create_plan(run_dir)
    existing = next(
        (item for item in plan.get("source_boards", []) if item.get("source_id") == source_id),
        None,
    )
    source_record = {
        "source_id": source_id,
        "label": source_id,
        "url": str(source_dir),
        "limit": max(1, limit),
        "status": "collected" if copied else "failed",
        "added_at": now(),
        "collector": "local-folder",
        "output_dir": str(target_dir.relative_to(run_dir)),
        "downloaded_count": copied,
        "completed_at": now(),
    }
    if existing:
        existing.update(source_record)
    else:
        plan.setdefault("source_boards", []).append(source_record)
    plan["status"] = "sources_queued"
    write_json(plan_path(run_dir), plan)

    manifest = load_manifest(run_dir)
    manifest.setdefault("sources", {})[source_id] = {
        "source_id": source_id,
        "url": str(source_dir),
        "label": source_id,
        "status": source_record["status"],
        "output_dir": str(target_dir.relative_to(run_dir)),
        "downloaded_count": copied,
        "collected_at": source_record["completed_at"],
    }
    upsert_assets(manifest, records_from_output(target_dir, source_record))
    manifest["updated_at"] = now()
    manifest["asset_count"] = len(manifest.get("assets", []))
    write_json(manifest_path(run_dir), manifest)
    return source_record


def select_collected_references(
    run_dir: Path,
    *,
    select_count: int = 30,
    only_source: str | None = None,
    only_sources: list[str] | None = None,
    reviewer: str = "heuristic",
    review_limit: int | None = None,
    review_model: str = "qwen2.5vl:7b",
    review_host: str = "http://127.0.0.1:11434",
) -> dict[str, Any]:
    manifest = load_manifest(run_dir)
    source_filter = set(only_sources or [])
    if only_source:
        source_filter.add(only_source)
    sources = [
        source for source in manifest.get("sources", {}).values()
        if not source_filter or source.get("source_id") in source_filter
    ]
    ranked = rank_downloaded_candidates(run_dir, sources)
    selection_method = "deterministic_image_quality_v1"
    review_summary: dict[str, Any] = {}
    selection_pool = ranked
    if reviewer == "qwen":
        qwen_limit = review_limit if review_limit is not None else select_count * 3
        reviewed = review_ranked_candidates(
            run_dir,
            ranked[: max(1, qwen_limit)],
            model=review_model,
            host=review_host,
        )
        if reviewed:
            selection_pool = reviewed
            selection_method = "qwen_event_reference_review_v1"
            review_summary = {
                "reviewer": "qwen",
                "model": review_model,
                "host": review_host,
                "reviewed_count": len(reviewed),
            }
        else:
            review_summary = {
                "reviewer": "qwen",
                "model": review_model,
                "host": review_host,
                "reviewed_count": 0,
                "fallback": "deterministic_image_quality_v1",
            }

    if not selection_pool:
        manifest["selection"] = {
            "updated_at": now(),
            "ranked_count": len(ranked),
            "selected_count": 0,
            "source_filter": ",".join(sorted(source_filter)),
            "selection_method": selection_method,
            "review": review_summary,
            "error": "No candidate images were available for the requested source filter.",
        }
        manifest["updated_at"] = now()
        write_json(manifest_path(run_dir), manifest)
        return manifest

    event_input = read_json(run_dir / "event-input.json", default={})
    gated_pool = apply_reference_quality_filter(selection_pool, event_input)
    write_json(references_dir(run_dir) / "reference-quality-filter.json", gated_pool)
    unique_pool = unique_image_records(gated_pool["accepted"])
    selected = materialize_selected_references(run_dir, unique_pool[: max(1, select_count)])
    manifest["assets"] = [
        asset for asset in manifest.get("assets", [])
        if asset.get("status") != "selected" or not str(asset.get("asset_id", "")).startswith("selected_")
    ]
    upsert_assets(manifest, selected)
    manifest["asset_count"] = len(manifest.get("assets", []))
    manifest["selection"] = {
        "updated_at": now(),
        "ranked_count": len(ranked),
        "selected_count": len(selected),
        "source_filter": ",".join(sorted(source_filter)),
            "selection_method": selection_method,
            "review": review_summary,
            "quality_filter": gated_pool["summary"],
        }
    manifest["updated_at"] = now()
    write_json(manifest_path(run_dir), manifest)
    return manifest


def auto_collect_from_search(
    run_dir: Path,
    *,
    query_limit: int = 12,
    per_query_limit: int = 24,
    select_count: int = 30,
    headful: bool = False,
    reviewer: str = "heuristic",
    review_limit: int | None = None,
    review_model: str = "qwen2.5vl:7b",
    review_host: str = "http://127.0.0.1:11434",
) -> dict[str, Any]:
    from services.reference_collector.pinterest import CollectorOptions, collect_pinterest_board

    plan = create_plan(run_dir)
    searches = plan.get("search_queries", [])[: max(1, query_limit)]
    manifest = load_manifest(run_dir)
    auto_sources: list[dict[str, Any]] = []

    for search in searches:
        query_id = search["query_id"]
        source_id = f"auto-{query_id}-{safe_slug(search['query'])[:32]}"
        output_dir = references_dir(run_dir) / "candidates" / source_id
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        summary = collect_pinterest_board(
            CollectorOptions(
                board_url=search["pinterest_search_url"],
                output_dir=output_dir,
                limit=max(1, per_query_limit),
                scrolls=max(8, min(40, per_query_limit // 3 + 8)),
                headless=not headful,
                browser_channel="chrome",
                storage_state=None,
                allow_page_fallback=True,
            )
        )
        source = {
            "source_id": source_id,
            "query_id": query_id,
            "query": search["query"],
            "url": search["pinterest_search_url"],
            "collector": "playwright_search_fallback",
            "status": "collected",
            "output_dir": str(output_dir.relative_to(run_dir)),
            "candidates_found": summary.get("candidates_found", 0),
            "downloaded_count": summary.get("downloaded", 0),
            "collected_at": now(),
        }
        auto_sources.append(source)
        manifest.setdefault("sources", {})[source_id] = source

    ranked = rank_downloaded_candidates(run_dir, auto_sources)
    selection_method = "deterministic_image_quality_v1"
    review_summary: dict[str, Any] = {}
    selection_pool = ranked
    if reviewer == "qwen":
        qwen_limit = review_limit if review_limit is not None else select_count * 3
        reviewed = review_ranked_candidates(
            run_dir,
            ranked[: max(1, qwen_limit)],
            model=review_model,
            host=review_host,
        )
        if reviewed:
            selection_pool = reviewed
            selection_method = "qwen_event_reference_review_v1"
            review_summary = {
                "reviewer": "qwen",
                "model": review_model,
                "host": review_host,
                "reviewed_count": len(reviewed),
            }
        else:
            review_summary = {
                "reviewer": "qwen",
                "model": review_model,
                "host": review_host,
                "reviewed_count": 0,
                "fallback": "deterministic_image_quality_v1",
            }
    if not selection_pool:
        unique_pool: list[dict[str, Any]] = []
        manifest["auto_collection"] = {
            "updated_at": now(),
            "query_count": len(auto_sources),
            "ranked_count": len(ranked),
            "unique_count": len(unique_pool),
            "selected_count": 0,
            "selection_method": selection_method,
            "review": review_summary,
            "error": "No candidate images were available from Pinterest search.",
        }
        manifest["updated_at"] = now()
        write_json(manifest_path(run_dir), manifest)
        return manifest
    event_input = read_json(run_dir / "event-input.json", default={})
    gated_pool = apply_reference_quality_filter(selection_pool, event_input)
    write_json(references_dir(run_dir) / "reference-quality-filter.json", gated_pool)
    unique_pool = unique_image_records(gated_pool["accepted"])
    selected = materialize_selected_references(run_dir, unique_pool[: max(1, select_count)])
    manifest["assets"] = [
        asset for asset in manifest.get("assets", [])
        if asset.get("status") != "selected" or not str(asset.get("asset_id", "")).startswith("selected_")
    ]
    manifest["auto_collection"] = {
        "updated_at": now(),
        "query_count": len(auto_sources),
        "ranked_count": len(ranked),
        "unique_count": len(unique_pool),
        "selected_count": len(selected),
        "selection_method": selection_method,
        "review": review_summary,
        "quality_filter": gated_pool["summary"],
    }
    upsert_assets(manifest, selected)
    manifest["asset_count"] = len(manifest.get("assets", []))
    manifest["updated_at"] = now()
    write_json(manifest_path(run_dir), manifest)
    return manifest


def review_ranked_candidates(
    run_dir: Path,
    ranked: list[dict[str, Any]],
    *,
    model: str,
    host: str,
) -> list[dict[str, Any]]:
    from requests import RequestException
    from services.visual_reference.qwen_reviewer import build_event_reference_prompt, review_image

    plan = create_plan(run_dir)
    prompt = build_event_reference_prompt(plan.get("intent", {}))
    reviewed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for candidate in ranked:
        try:
            review = review_image(Path(candidate["path"]), model=model, host=host, prompt=prompt)
        except (RequestException, OSError, KeyError, ValueError) as exc:
            errors.append({
                "candidate_id": candidate.get("asset_id") or candidate.get("candidate_id"),
                "file": candidate.get("path", ""),
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue
        merged = dict(candidate)
        merged["qwen_review"] = review
        merged["review_decision"] = normalize_decision(review.get("decision", ""))
        merged["review_score"] = numeric_score(review.get("score"), default=0)
        merged["event_fit"] = numeric_score(review.get("event_fit"), default=merged["review_score"])
        merged["brand_fit"] = numeric_score(review.get("brand_fit") or review.get("brandFit"), default=merged["review_score"])
        merged["copy_space"] = numeric_score(review.get("copy_space"), default=0)
        merged["category_fit"] = numeric_score(review.get("category_fit"), default=merged["review_score"])
        merged["product_relevance"] = numeric_score(review.get("product_relevance") or review.get("productRelevance"), default=merged["category_fit"])
        merged["seriousness_fit"] = numeric_score(review.get("seriousness_fit") or review.get("seriousnessFit"), default=0)
        merged["risk_level"] = numeric_score(review.get("risk_level") or review.get("riskLevel"), default=0)
        merged["layout_idea"] = numeric_score(review.get("layout_idea"), default=0)
        merged["production_value"] = numeric_score(review.get("production_value"), default=0)
        merged["originality"] = numeric_score(review.get("originality"), default=0)
        merged["risk_control"] = numeric_score(review.get("risk_control"), default=0)
        merged["score"] = combined_review_score(merged)
        merged["status"] = "reviewed_candidate"
        reviewed.append(merged)

    decision_weight = {"selected": 2, "shortlist": 1, "rejected": 0}
    reviewed.sort(
        key=lambda item: (
            decision_weight.get(item.get("review_decision", "rejected"), 0),
            item.get("score", 0),
        ),
        reverse=True,
    )
    for index, item in enumerate(reviewed, start=1):
        item["rank"] = index

    write_json(references_dir(run_dir) / "qwen-reviewed-candidates.json", {
        "reviewed": reviewed,
        "errors": errors,
        "model": model,
        "host": host,
        "reviewed_at": now(),
    })
    return [item for item in reviewed if item.get("review_decision") in {"selected", "shortlist"}]


def normalize_decision(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in {"selected", "select", "approved", "approve"}:
        return "selected"
    if normalized in {"shortlist", "candidate", "maybe"}:
        return "shortlist"
    return "rejected"


def numeric_score(value: Any, *, default: float = 0) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return default


def combined_review_score(candidate: dict[str, Any]) -> float:
    quality = numeric_score(candidate.get("score"), default=0)
    review_score = numeric_score(candidate.get("review_score"), default=0)
    event_fit = numeric_score(candidate.get("event_fit"), default=review_score)
    copy_space = numeric_score(candidate.get("copy_space"), default=0)
    category_fit = numeric_score(candidate.get("category_fit"), default=review_score)
    layout_idea = numeric_score(candidate.get("layout_idea"), default=0)
    production_value = numeric_score(candidate.get("production_value"), default=0)
    originality = numeric_score(candidate.get("originality"), default=0)
    risk_control = numeric_score(candidate.get("risk_control"), default=0)
    return round(
        quality * 0.15
        + review_score * 0.10
        + event_fit * 0.18
        + category_fit * 0.18
        + layout_idea * 0.12
        + copy_space * 0.12
        + production_value * 0.10
        + originality * 0.08
        + risk_control * 0.07,
        2,
    )


def apply_reference_quality_filter(records: list[dict[str, Any]], event_input: dict[str, Any]) -> dict[str, Any]:
    bullion_event = is_bullion_investment_event(event_input)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    shortlisted: list[dict[str, Any]] = []

    for record in records:
        item = dict(record)
        quality_defects = reference_quality_defects(item)
        if quality_defects:
            item["evaluation"] = build_reference_evaluation(item, bullion_event=bullion_event)
            item["quality_gate"] = {"decision": "rejected", "reasons": quality_defects}
            rejected.append(item)
            continue
        if bullion_event:
            item["training_alignment"] = score_record_against_training(item, "bullion_investment")
        evaluation = build_reference_evaluation(item, bullion_event=bullion_event)
        item["evaluation"] = evaluation
        item["quality_gate"] = reference_quality_gate(evaluation, item, bullion_event=bullion_event)
        if bullion_event:
            alignment = item.get("training_alignment") or {}
            item["score"] = round(max(
                0.0,
                min(100.0, float(item.get("score", 0)) + alignment.get("goodScore", 0) * 1.2 - alignment.get("badScore", 0) * 2.0),
            ), 2)
        if item["quality_gate"]["decision"] == "accepted":
            accepted.append(item)
        elif item["quality_gate"]["decision"] == "shortlist":
            shortlisted.append(item)
        else:
            rejected.append(item)

    accepted.sort(key=lambda item: item.get("score", 0), reverse=True)
    if bullion_event:
        accepted = diversify_by_training_category(accepted)
    shortlisted.sort(key=lambda item: item.get("score", 0), reverse=True)
    rejected.sort(key=lambda item: item.get("score", 0), reverse=True)
    return {
        "summary": {
            "profile": "bullion_investment_strict_v1" if bullion_event else "default_reference_quality_v1",
            "input_count": len(records),
            "accepted_count": len(accepted),
            "shortlist_count": len(shortlisted),
            "rejected_count": len(rejected),
            "gates": BULLION_SELECTION_GATES if bullion_event else {},
            "reject_terms": BULLION_REJECT_TERMS if bullion_event else [],
            "reference_training": training_summary("bullion_investment") if bullion_event else {},
        },
        "accepted": accepted,
        "shortlist": shortlisted,
        "rejected": rejected,
    }


def reference_quality_defects(record: dict[str, Any]) -> list[str]:
    """Hard defects that make a reference unusable before brand/event judgement."""
    reasons: list[str] = []
    width = numeric_value(record.get("width"), default=0)
    height = numeric_value(record.get("height"), default=0)
    if width <= 0 or height <= 0:
        reasons.append("unreadable_or_missing_dimensions")
    elif width < 300 or height < 300:
        reasons.append(f"low_resolution<{int(width)}x{int(height)}")
    quality_score = numeric_score(record.get("quality_score"), default=numeric_score(record.get("score"), default=0))
    if quality_score < 35:
        reasons.append(f"quality_score<{quality_score:.1f}")
    return reasons


def numeric_value(value: Any, *, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_reference_evaluation(record: dict[str, Any], *, bullion_event: bool) -> dict[str, float]:
    review_score = numeric_score(record.get("review_score"), default=numeric_score(record.get("score"), default=0))
    quality_score = numeric_score(record.get("quality_score"), default=numeric_score(record.get("score"), default=0))
    event_fit = numeric_score(record.get("event_fit"), default=numeric_score(record.get("text_relevance_score"), default=review_score))
    category_fit = numeric_score(record.get("category_fit"), default=numeric_score(record.get("text_relevance_score"), default=review_score))
    product_relevance = numeric_score(record.get("product_relevance"), default=category_fit)
    copy_space = numeric_score(record.get("copy_space"), default=quality_score)
    layout_idea = numeric_score(record.get("layout_idea"), default=quality_score)
    production_value = numeric_score(record.get("production_value"), default=quality_score)
    risk_control = numeric_score(record.get("risk_control"), default=review_score or 65)
    seriousness = numeric_score(record.get("seriousness_fit"), default=production_value * 0.65 + risk_control * 0.35)
    risk_level = numeric_score(record.get("risk_level"), default=max(0.0, 100.0 - risk_control))

    if bullion_event:
        hits = reference_reject_hits(record)
        alignment = record.get("training_alignment") or score_record_against_training(record, "bullion_investment")
        good_boost = min(22.0, float(alignment.get("goodScore", 0)) * 2.2)
        bad_penalty = min(35.0, float(alignment.get("badScore", 0)) * 3.5)
        review_score = min(100.0, max(0.0, review_score + good_boost - bad_penalty))
        event_fit = min(100.0, max(0.0, event_fit + good_boost - bad_penalty))
        product_relevance = min(100.0, max(0.0, product_relevance + good_boost - bad_penalty))
        seriousness = min(100.0, max(0.0, seriousness + good_boost - bad_penalty))
        risk_level = min(100.0, max(0.0, risk_level - good_boost + bad_penalty))
        if hits:
            seriousness = max(0.0, seriousness - 35.0)
            product_relevance = max(0.0, product_relevance - 30.0)
            event_fit = max(0.0, event_fit - 25.0)
            risk_level = max(risk_level, 85.0)

    return {
        "brandFit": round(review_score / 10, 2),
        "eventFit": round(event_fit / 10, 2),
        "visualQuality": round(quality_score / 10, 2),
        "compositionUsefulness": round(max(copy_space, layout_idea) / 10, 2),
        "promptUsefulness": round((event_fit * 0.35 + product_relevance * 0.35 + layout_idea * 0.30) / 10, 2),
        "seriousnessFit": round(seriousness / 10, 2),
        "productRelevance": round(product_relevance / 10, 2),
        "riskLevel": round(risk_level / 10, 2),
    }


def reference_quality_gate(
    evaluation: dict[str, float],
    record: dict[str, Any],
    *,
    bullion_event: bool,
) -> dict[str, Any]:
    if not bullion_event:
        return {"decision": "accepted", "reasons": []}

    reasons: list[str] = []
    reject_hits = reference_reject_hits(record)
    alignment = record.get("training_alignment") or {}
    categories = set(alignment.get("matchedCategories") or [])
    event_min = BULLION_SELECTION_GATES["eventFit"]
    product_min = BULLION_SELECTION_GATES["productRelevance"]
    if alignment.get("goodScore", 0) >= 5 and categories.intersection({"finance_mood_reference", "poster_layout_reference"}):
        event_min = 5.5
        product_min = 5.5
    if reject_hits:
        reasons.append("reject_terms=" + ",".join(reject_hits[:6]))
    if alignment.get("badScore", 0) >= 3:
        reasons.append(f"bad_training_similarity={alignment.get('badScore')}")
    if alignment.get("goodScore", 0) < 1:
        reasons.append("weak_good_training_similarity")
    if evaluation.get("brandFit", 0) < BULLION_SELECTION_GATES["brandFit"]:
        reasons.append(f"brandFit<{BULLION_SELECTION_GATES['brandFit']}")
    if evaluation.get("eventFit", 0) < event_min:
        reasons.append(f"eventFit<{event_min}")
    if evaluation.get("productRelevance", 0) < product_min:
        reasons.append(f"productRelevance<{product_min}")
    if evaluation.get("seriousnessFit", 0) < BULLION_SELECTION_GATES["seriousnessFit"]:
        reasons.append(f"seriousnessFit<{BULLION_SELECTION_GATES['seriousnessFit']}")
    if evaluation.get("riskLevel", 10) > BULLION_SELECTION_GATES["riskLevelMax"]:
        reasons.append(f"riskLevel>{BULLION_SELECTION_GATES['riskLevelMax']}")

    if reject_hits or len(reasons) >= 2:
        return {"decision": "rejected", "reasons": reasons}
    if reasons:
        return {"decision": "shortlist", "reasons": reasons}
    return {"decision": "accepted", "reasons": []}


def reference_reject_hits(record: dict[str, Any]) -> list[str]:
    review = record.get("qwen_review") or {}
    text = " ".join([
        str(record.get("query", "")),
        str(record.get("source_id", "")),
        str(record.get("relative_path", "")),
        str(record.get("path", "")),
        str(record.get("text_relevance_reason", "")),
        str(review.get("reason", "")),
        str(review.get("risk", "")),
        " ".join(str(tag) for tag in record.get("negative_tags", []) or []),
        " ".join(str(tag) for tag in review.get("negative_tags", []) or []),
    ]).lower()
    return [term for term in BULLION_REJECT_TERMS if term in text]


def diversify_by_training_category(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target_categories = ["product_reference", "finance_mood_reference", "poster_layout_reference"]
    buckets: dict[str, list[dict[str, Any]]] = {category: [] for category in target_categories}
    uncategorized: list[dict[str, Any]] = []
    for item in records:
        categories = item.get("training_alignment", {}).get("matchedCategories") or []
        category = next((candidate for candidate in target_categories if candidate in categories), "")
        if category:
            buckets[category].append(item)
        else:
            uncategorized.append(item)
    ordered: list[dict[str, Any]] = []
    while any(buckets.values()):
        for category in target_categories:
            if buckets[category]:
                ordered.append(buckets[category].pop(0))
    return ordered + uncategorized


def rank_downloaded_candidates(run_dir: Path, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    category_anchor = infer_category_anchor(read_json(run_dir / "event-input.json", default={}))
    for source in sources:
        source_dir = run_dir / source["output_dir"]
        source_metadata = load_source_image_metadata(source_dir)
        for image_path in sorted(source_dir.rglob("*")):
            if image_path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            key = image_path.name.lower()
            if key in seen:
                continue
            seen.add(key)
            image_metadata = source_metadata.get(image_path.name, {})
            score = score_image_candidate(image_path)
            relevance = text_relevance_score(image_path, source, category_anchor, image_metadata)
            score["quality_score"] = score["score"]
            score["text_relevance_score"] = relevance["score"]
            score["text_relevance_reason"] = relevance["reason"]
            score["score"] = round(max(0.0, min(100.0, score["quality_score"] * 0.78 + relevance["score"] * 0.22)), 2)
            score.update({
                "asset_id": f"{source['source_id']}_{len(records) + 1:04d}",
                "source_id": source["source_id"],
                "query_id": source.get("query_id", ""),
                "query": source.get("query", ""),
                "source_url": source.get("url", ""),
                "pin_url": image_metadata.get("pin_url", ""),
                "image_url": image_metadata.get("image_url", ""),
                "downloaded_url": image_metadata.get("downloaded_url", ""),
                "title": image_metadata.get("alt", "") or image_metadata.get("title", ""),
                "sha256": image_metadata.get("sha256", ""),
                "path": str(image_path),
                "relative_path": str(image_path.relative_to(run_dir)),
                "status": "ranked_candidate",
                "collected_at": now(),
            })
            records.append(score)
    records.sort(key=lambda item: item["score"], reverse=True)
    for index, record in enumerate(records, start=1):
        record["rank"] = index
    write_json(references_dir(run_dir) / "ranked-candidates.json", {"ranked": records})
    return records


def load_source_image_metadata(source_dir: Path) -> dict[str, dict[str, Any]]:
    """Load collector metadata keyed by saved image filename."""
    metadata: dict[str, dict[str, Any]] = {}
    jsonl_path = source_dir / "metadata.jsonl"
    if jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                saved_path = Path(str(record.get("saved_path", ""))).name
                if saved_path:
                    metadata[saved_path] = record

    for metadata_path in source_dir.glob("*.json"):
        if metadata_path.name in {"info.json", "collection-summary.json"}:
            continue
        try:
            record = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        saved_path = Path(str(record.get("saved_path", ""))).name or metadata_path.with_suffix("").name
        if saved_path:
            metadata.setdefault(saved_path, record)
    return metadata


def text_relevance_score(
    image_path: Path,
    source: dict[str, Any],
    category_anchor: str,
    image_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score source metadata relevance without using search query or file path as evidence."""
    metadata = image_metadata or {}
    text = " ".join([
        str(metadata.get("alt", "")),
        str(metadata.get("title", "")),
        str(metadata.get("description", "")),
        str(metadata.get("grid_title", "")),
        str(metadata.get("seo_title", "")),
    ]).lower()
    if not text.strip():
        return {
            "score": 50.0,
            "reason": "metadata_evidence=empty; query_ignored=true",
        }
    category = category_anchor.lower()
    korean_terms = {
        "주얼리": (
            ["주얼리", "쥬얼리", "귀금속", "보석", "반지", "목걸이", "jewelry", "ring", "necklace"],
            ["스킨케어", "화장품", "음식", "향수", "skincare", "cosmetic", "food", "perfume"],
        ),
        "향수": (
            ["향수", "퍼퓸", "프래그런스", "보틀", "광고", "perfume", "fragrance", "bottle"],
            ["스킨케어", "세럼", "크림", "주얼리", "음식", "skincare", "serum", "cream", "jewelry", "food"],
        ),
        "화장품": (
            ["화장품", "스킨케어", "뷰티", "세럼", "앰플", "크림", "선크림", "광고", "skincare", "cosmetic", "beauty", "serum", "ampoule", "cream"],
            ["꽃병", "인테리어", "가구", "쿠키", "음식", "주얼리", "향수", "vase", "interior", "furniture", "food", "jewelry", "perfume"],
        ),
        "금융": (
            ["금융", "은행", "투자", "자산", "상담", "금", "은", "이벤트", "배너", "finance", "bank", "investment", "gold", "silver"],
            ["스킨케어", "음식", "패션", "화장품", "skincare", "food", "fashion", "cosmetic"],
        ),
        "식음료": (
            ["식품", "음식", "카페", "푸드", "레스토랑", "메뉴", "food", "cafe", "restaurant"],
            ["금융", "화장품", "주얼리", "finance", "cosmetic", "jewelry"],
        ),
    }
    if category_anchor in korean_terms:
        positive, negative = korean_terms[category_anchor]
        hits = [token for token in positive if token in text]
        misses = [token for token in negative if token in text]
        score = 52 + min(38, len(hits) * 7) - min(35, len(misses) * 10)
        return {
            "score": round(max(0.0, min(100.0, score)), 2),
            "reason": f"metadata_positive={','.join(hits[:5]) or '-'}; metadata_negative={','.join(misses[:5]) or '-'}; query_ignored=true",
        }
    positive: list[str]
    negative: list[str]
    if "jewelry" in category:
        positive = ["jewelry", "jewellery", "ring", "necklace", "earring", "gold", "silver", "diamond", "luxury", "주얼리", "반지", "목걸이", "귀걸이", "보석"]
        negative = ["skincare", "cosmetic", "serum", "cream", "food", "perfume", "화장품", "피부", "음식", "향수"]
    elif "perfume" in category or "fragrance" in category:
        positive = ["perfume", "fragrance", "scent", "bottle", "luxury", "product", "ad", "campaign", "향수", "오드퍼퓸", "보틀", "광고"]
        negative = ["skincare", "serum", "cream", "jewelry", "food", "화장품", "세럼", "크림", "주얼리", "음식"]
    elif "skincare" in category or "cosmetic" in category:
        positive = ["skincare", "cosmetic", "beauty", "product", "ad", "campaign", "serum", "ampoule", "cream", "tube", "sunscreen", "화장품", "세럼", "앰플", "토너", "크림", "튜브", "콜라겐", "광고", "피부"]
        negative = ["vase", "interior", "furniture", "cookie", "food", "jewelry", "dress", "perfume", "꽃병", "인테리어", "가구", "쿠키", "음식", "주얼리", "향수"]
    elif "finance" in category or "gold" in category:
        positive = ["gold", "silver", "finance", "investment", "premium", "metal", "금", "은", "투자", "상담"]
        negative = ["skincare", "food", "fashion", "cosmetic", "화장품", "음식", "패션"]
    else:
        positive = ["campaign", "event", "brand", "promotion", "design", "광고", "이벤트", "프로모션", "디자인"]
        negative = ["random", "meme", "wallpaper"]

    hits = [token for token in positive if token in text]
    misses = [token for token in negative if token in text]
    score = 52 + min(38, len(hits) * 7) - min(35, len(misses) * 10)
    return {
        "score": round(max(0.0, min(100.0, score)), 2),
        "reason": f"metadata_positive={','.join(hits[:5]) or '-'}; metadata_negative={','.join(misses[:5]) or '-'}; query_ignored=true",
    }


def score_image_candidate(image_path: Path) -> dict[str, Any]:
    if Image is None or ImageStat is None:
        return {"score": 50.0, "width": 0, "height": 0, "reason": "Pillow not installed; neutral score."}

    try:
        with Image.open(image_path) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            stat = ImageStat.Stat(rgb.resize((64, 64)))
            mean = sum(stat.mean) / 3
            extrema = stat.extrema
            contrast = sum(high - low for low, high in extrema) / 3
            thumb = rgb.resize((64, 64))
            pixels = list(thumb.getdata())
            light_pixels = sum(1 for pixel in pixels if min(pixel) >= 218)
            very_dark_pixels = sum(1 for pixel in pixels if max(pixel) <= 28)
    except Exception as exc:
        return {"score": 0.0, "width": 0, "height": 0, "reason": f"Unreadable image: {type(exc).__name__}"}

    min_side = min(width, height)
    ratio = width / max(height, 1)
    resolution_score = min(30.0, min_side / 40)
    ratio_score = 16.0 if 0.72 <= ratio <= 1.8 else 8.0
    brightness_score = max(0.0, 18.0 - abs(mean - 185) / 8)
    contrast_score = min(16.0, contrast / 8)
    light_space = light_pixels / max(len(pixels), 1)
    dark_penalty = min(10.0, very_dark_pixels / max(len(pixels), 1) * 30)
    whitespace_score = min(20.0, light_space * 36)
    score = resolution_score + ratio_score + brightness_score + contrast_score + whitespace_score - dark_penalty
    reasons = [
        f"{width}x{height}",
        f"light_space={light_space:.2f}",
        f"contrast={contrast:.1f}",
    ]
    return {
        "score": round(max(0.0, min(100.0, score)), 2),
        "width": width,
        "height": height,
        "mean_luma": round(mean, 2),
        "contrast": round(contrast, 2),
        "light_space": round(light_space, 3),
        "reason": "; ".join(reasons),
    }


def materialize_selected_references(run_dir: Path, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_dir = references_dir(run_dir) / "selected"
    if selected_dir.exists():
        for item in selected_dir.iterdir():
            if item.is_file():
                item.unlink()
    selected_dir.mkdir(parents=True, exist_ok=True)
    selected: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        source_path = Path(record["path"])
        target_name = f"{index:03d}_{safe_slug(record.get('query', 'reference'))[:36]}_{source_path.name}"
        target_path = selected_dir / target_name
        shutil.copy2(source_path, target_path)
        item = dict(record)
        item.update({
            "asset_id": f"selected_{index:03d}",
            "status": "selected",
            "selected_at": now(),
            "original_path": record["relative_path"],
            "path": str(target_path),
            "relative_path": str(target_path.relative_to(run_dir)),
        })
        selected.append(item)
    write_json(references_dir(run_dir) / "selected-references.json", {"selected": selected})
    return selected


def unique_image_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        key = image_identity_key(record)
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def image_identity_key(record: dict[str, Any]) -> str:
    path = Path(str(record.get("path", "")))
    if path.exists() and path.is_file():
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            return f"sha256:{digest}"
        except OSError:
            pass
    pin_url = str(record.get("pin_url", "")).strip()
    if pin_url:
        return f"pin:{pin_url}"
    relative_path = str(record.get("relative_path", "")).strip()
    return f"path:{relative_path or record.get('asset_id', '')}"


def run_gallery_dl(url: str, *, output_dir: Path, limit: int, use_cookies: bool) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "gallery_dl",
        "--directory",
        str(output_dir),
        "--range",
        f"1-{limit}",
        "--sleep-request",
        "2-5",
        "--sleep",
        "4-8",
        "--sleep-429",
        "300-600",
        "--write-metadata",
        "--write-info-json",
        "--windows-filenames",
        "--verbose",
        url,
    ]
    if use_cookies:
        command.insert(-1, "chrome")
        command.insert(-2, "--cookies-from-browser")
    with (output_dir / "gallery-dl.log").open("w", encoding="utf-8") as log:
        return subprocess.run(command, cwd=ROOT, text=True, stdout=log, stderr=subprocess.STDOUT)


def run_playwright_collection_fallback(
    url: str,
    *,
    output_dir: Path,
    limit: int,
    allow_page_fallback: bool = False,
) -> dict[str, Any]:
    try:
        from services.reference_collector.pinterest import CollectorOptions, collect_pinterest_board
    except ImportError as exc:
        return {
            "status": "unavailable",
            "collector": "playwright",
            "error": f"{type(exc).__name__}: {exc}",
        }

    storage_state = PINTEREST_STORAGE_STATE
    session_status = pinterest_session_status(storage_state)
    try:
        summary = collect_pinterest_board(
            CollectorOptions(
                board_url=url,
                output_dir=output_dir,
                limit=max(1, limit),
                scrolls=max(8, min(40, limit // 3 + 8)),
                headless=True,
                browser_channel="chrome",
                storage_state=storage_state if storage_state.exists() else None,
                allow_page_fallback=allow_page_fallback,
            )
        )
        summary["status"] = "collected" if summary.get("downloaded", 0) else "empty"
        summary["collector"] = "playwright"
        summary["allow_page_fallback"] = allow_page_fallback
        summary["pinterest_session"] = session_status
        return summary
    except Exception as exc:
        return {
            "status": "failed",
            "collector": "playwright",
            "error": f"{type(exc).__name__}: {exc}",
            "allow_page_fallback": allow_page_fallback,
            "pinterest_session": session_status,
        }


def records_from_output(output_dir: Path, source: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    metadata_by_name = load_source_image_metadata(output_dir)

    image_index = 0
    for image_path in sorted(output_dir.iterdir()):
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            continue
        image_index += 1
        metadata = metadata_by_name.get(image_path.name, {})
        asset_id = f"{source['source_id']}_{image_index:04d}"
        records.append({
            "asset_id": asset_id,
            "source_id": source["source_id"],
            "source_url": source["url"],
            "pin_url": metadata.get("pin_url") or metadata.get("url") or metadata.get("webpage_url") or "",
            "title": metadata.get("title") or metadata.get("description") or "",
            "path": str(image_path),
            "relative_path": str(image_path.relative_to(output_dir.parents[2])),
            "status": "candidate",
            "collected_at": now(),
        })
    return records


def load_manifest(run_dir: Path) -> dict[str, Any]:
    path = manifest_path(run_dir)
    if path.exists():
        return read_json(path)
    return {
        "run_id": run_dir.name,
        "created_at": now(),
        "updated_at": now(),
        "asset_count": 0,
        "sources": {},
        "assets": [],
        "notes": [],
    }


def upsert_assets(manifest: dict[str, Any], records: list[dict[str, Any]]) -> None:
    by_path = {item.get("relative_path"): item for item in manifest.setdefault("assets", [])}
    for record in records:
        by_path[record["relative_path"]] = record
    manifest["assets"] = list(by_path.values())


def pinterest_search_url(query: str) -> str:
    return f"https://kr.pinterest.com/search/pins/?q={quote_plus(query)}"


def short_query(value: str, max_words: int = 8) -> str:
    words = re.sub(r"\s+", " ", value).strip().split()
    return " ".join(words[:max_words])


def dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = re.sub(r"\s+", " ", value).strip()
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def source_slug(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part and part != "pin"]
    if parts:
        return safe_slug(parts[-1])
    return "reference-source"


def safe_slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "-", value)
    sanitized = re.sub(r"[^a-z0-9가-힣-]+", "", value)
    return sanitized.strip("-_") or "reference-source"


def unique_source_id(existing: list[dict[str, Any]], label: str) -> str:
    used = {str(item.get("source_id")) for item in existing}
    if label not in used:
        return label
    index = 2
    while f"{label}-{index}" in used:
        index += 1
    return f"{label}-{index}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan and collect run-scoped visual references.")
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--add-source", help="Pinterest board, section, search, or pin URL to queue.")
    parser.add_argument("--import-local-source", type=Path, help="Import an existing local folder of reference images as a queued source.")
    parser.add_argument("--label", default="")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--allow-page-fallback", action="store_true")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--select-collected", action="store_true")
    parser.add_argument("--only-source")
    parser.add_argument("--no-cookies", action="store_true")
    parser.add_argument("--auto-search", action="store_true")
    parser.add_argument("--query-limit", type=int, default=12)
    parser.add_argument("--per-query-limit", type=int, default=24)
    parser.add_argument("--select-count", type=int, default=30)
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--reviewer", choices=["heuristic", "qwen"], default="heuristic")
    parser.add_argument("--review-limit", type=int)
    parser.add_argument("--review-model", default="qwen2.5vl:7b")
    parser.add_argument("--review-host", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    run_dir = args.run.resolve()
    if args.plan:
        print(json.dumps(create_plan(run_dir, force=args.force), ensure_ascii=False, indent=2))
    if args.add_source:
        print(json.dumps(
            add_source(
                run_dir,
                args.add_source,
                label=args.label,
                limit=args.limit,
                allow_page_fallback=args.allow_page_fallback,
            ),
            ensure_ascii=False,
            indent=2,
        ))
    if args.import_local_source:
        print(json.dumps(
            import_local_reference_source(
                run_dir,
                args.import_local_source,
                label=args.label,
                limit=args.limit,
            ),
            ensure_ascii=False,
            indent=2,
        ))
    if args.collect:
        print(json.dumps(collect_sources(run_dir, use_cookies=not args.no_cookies, only_source=args.only_source), ensure_ascii=False, indent=2))
    if args.select_collected:
        print(json.dumps(
            select_collected_references(
                run_dir,
                select_count=args.select_count,
                only_source=args.only_source,
                reviewer=args.reviewer,
                review_limit=args.review_limit,
                review_model=args.review_model,
                review_host=args.review_host,
            ),
            ensure_ascii=False,
            indent=2,
        ))
    if args.auto_search:
        print(json.dumps(
            auto_collect_from_search(
                run_dir,
                query_limit=args.query_limit,
                per_query_limit=args.per_query_limit,
                select_count=args.select_count,
                headful=args.headful,
                reviewer=args.reviewer,
                review_limit=args.review_limit,
                review_model=args.review_model,
                review_host=args.review_host,
            ),
            ensure_ascii=False,
            indent=2,
        ))
    if not (args.plan or args.add_source or args.import_local_source or args.collect or args.select_collected or args.auto_search):
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
