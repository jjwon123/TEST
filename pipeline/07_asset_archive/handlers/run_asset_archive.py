"""07_asset_archive handler.

Reads QA-pass frames from 06_qa_packaging outputs, scores them for reuse,
copies files to assets/approved/ and assets/reusable/, writes asset-archive.json
and reuse-notes.md, and upserts records into the global index.

Classification policy is read from core/policies/archive-reuse-policy.json —
nothing is hardcoded here.
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils import channel_registry
from core.utils import template_registry
from core.utils.json_io import read_json, write_json, write_text
from core.utils.schema_validation import validate_json


ROOT = Path(__file__).resolve().parents[3]
STAGE_ID = "07_asset_archive"
SCHEMA_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    run_dir: Path,
    mode: str = "run",
    outputs: list[str] | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()

    policy = read_json(ROOT / "core" / "policies" / "archive-reuse-policy.json")
    input_schema = read_json(ROOT / "pipeline" / STAGE_ID / "input.schema.json")
    output_schema = read_json(ROOT / "pipeline" / STAGE_ID / "output.schema.json")

    # New runs: stage_dir/filename  |  Legacy runs: stage_dir/output/filename
    manifest_path = _find_stage_file(run_dir, "06_qa_packaging", "final-package-manifest.json")
    qa_report_path = _find_stage_file(run_dir, "06_qa_packaging", "qa-report.json")

    manifest_raw = read_json(manifest_path)
    qa_report = read_json(qa_report_path)

    # final-package-manifest.json is either a bare array or wrapped in an object
    if isinstance(manifest_raw, list):
        frames = manifest_raw
    else:
        frames = manifest_raw.get("packageManifest", manifest_raw.get("items", []))

    validate_json(
        {"final_package_manifest": frames, "qa_report": qa_report},
        input_schema,
        data_label="06_qa_packaging outputs",
        schema_label=f"pipeline/{STAGE_ID}/input.schema.json",
    )

    selected_assets_path = _find_stage_file(run_dir, "04_admin_selection", "selected-assets.json")
    selected_assets = read_json(selected_assets_path, default={}) if selected_assets_path.exists() else {}
    channel_outputs_path = _find_stage_file(run_dir, "05_figma_assembly", "channel-outputs.json")
    channel_outputs = read_json(channel_outputs_path, default={}) if channel_outputs_path.exists() else {}
    content_plan_path = _find_stage_file(run_dir, "02_content_planning", "content-plan.json")
    content_plan = read_json(content_plan_path, default={}) if content_plan_path.exists() else {}

    brand_guide = read_json(run_dir / "brand-guide.json", default={})

    status = read_json(run_dir / "run-status.json", default={}) if (run_dir / "run-status.json").exists() else {}
    event_input = read_json(run_dir / "event-input.json", default={}) if (run_dir / "event-input.json").exists() else {}

    raw_event_id = (
        status.get("event_id")
        or _slugify(event_input.get("eventName") or event_input.get("name") or "")
        or _slugify(run_dir.name)
    )
    event_id = raw_event_id
    source_run_id = status.get("run_id") or run_dir.name

    archived_at = _now()

    blocked_frame_ids = _collect_blocked_frames(qa_report, policy)
    qa_overall = qa_report.get("summary", {}).get("status", "fail")

    assets, qa_filtered_out = _build_asset_records(
        frames=frames,
        qa_overall=qa_overall,
        blocked_frame_ids=blocked_frame_ids,
        event_id=event_id,
        source_run_id=source_run_id,
        selected_assets=selected_assets,
        channel_outputs=channel_outputs,
        content_plan=content_plan,
        brand_guide=brand_guide,
        policy=policy,
        archived_at=archived_at,
    )

    reusable_assets = [a for a in assets if a["reuse_status"] == "reusable"]
    completion_status, completion_state = archive_completion_status(assets)

    archive_doc = {
        "stage": STAGE_ID,
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id,
        "source_run_id": source_run_id,
        "archived_at": archived_at,
        "summary": {
            "completion_status": completion_status,
            "total_assets": len(assets),
            "approved": len(assets),
            "reusable": len(reusable_assets),
            "qa_filtered_out": qa_filtered_out,
        },
        "assets": assets,
    }

    validate_json(
        archive_doc,
        output_schema,
        data_label=f"{STAGE_ID}/asset-archive.json",
        schema_label=f"pipeline/{STAGE_ID}/output.schema.json",
    )

    stage_dir = run_dir / STAGE_ID
    archive_path = stage_dir / "asset-archive.json"
    notes_path = stage_dir / "reuse-notes.md"
    write_json(archive_path, archive_doc)
    write_text(notes_path, _build_reuse_notes(assets, event_id, archived_at))

    _copy_to_assets(assets, run_dir, policy)
    _upsert_global_index(assets, archived_at)
    _write_event_index(assets, event_id, archived_at)

    notes = [
        f"Archived {len(assets)} QA-pass assets ({qa_filtered_out} filtered out).",
        f"Reusable: {len(reusable_assets)} assets copied to assets/reusable/.",
        f"Global index updated: assets/indexes/global-index.json",
    ]

    return {
        "stage_id": STAGE_ID,
        "status": completion_status,
        "outputs": [
            str(archive_path.relative_to(run_dir)),
            str(notes_path.relative_to(run_dir)),
        ],
        "notes": notes,
        "next_state": completion_state,
        "regeneration_groups": {},
    }


def archive_completion_status(assets: list[dict[str, Any]]) -> tuple[str, str]:
    if assets:
        return "done", "archived"
    return "done_no_assets", "archived_no_assets"


# ---------------------------------------------------------------------------
# QA filtering
# ---------------------------------------------------------------------------

def _collect_blocked_frames(qa_report: dict[str, Any], policy: dict[str, Any]) -> set[str]:
    """Return frame IDs that have a blocker/error-level issue."""
    blocker_severities = set(policy.get("qa_filter", {}).get("blocker_severities", ["blocker", "error"]))
    blocked: set[str] = set()
    for issue in qa_report.get("issues", []):
        if issue.get("severity") in blocker_severities and issue.get("frameId"):
            blocked.add(issue["frameId"])
    return blocked


# ---------------------------------------------------------------------------
# Asset record construction
# ---------------------------------------------------------------------------

def _build_asset_records(
    frames: list[dict[str, Any]],
    qa_overall: str,
    blocked_frame_ids: set[str],
    event_id: str,
    source_run_id: str,
    selected_assets: dict[str, Any],
    channel_outputs: dict[str, Any],
    content_plan: dict[str, Any],
    brand_guide: dict[str, Any],
    policy: dict[str, Any],
    archived_at: str,
) -> tuple[list[dict[str, Any]], int]:
    if qa_overall != "pass":
        return [], len(frames)

    # selected-assets.json may be a bare list or wrapped in an object
    if isinstance(selected_assets, list):
        selections_list = selected_assets
    else:
        selections_list = selected_assets.get("selectedAssets", selected_assets.get("selections", []))
    selection_map = {
        (s.get("deliverableId") or s.get("deliverable_id")): s
        for s in selections_list
        if s.get("deliverableId") or s.get("deliverable_id")
    }
    template_context = _build_template_context(
        channel_outputs=channel_outputs,
        content_plan=content_plan,
        selected_assets=selected_assets,
    )
    brand_mood = brand_guide.get("visual", {}).get("mood", [])
    if isinstance(brand_mood, str):
        brand_mood = [brand_mood]

    assets: list[dict[str, Any]] = []
    filtered_out = 0

    for frame in frames:
        frame_id = frame.get("frameId", "")
        if frame_id in blocked_frame_ids:
            filtered_out += 1
            continue

        frame_name = frame.get("frameName", frame_id)
        channel_id = _canonical_archive_channel(frame.get("channel", "unknown"), frame_id, frame_name)
        template_inference = _infer_template_identity(frame, channel_id, template_context)
        template_family = template_inference["template_id"]
        intended_use = _infer_intended_use(frame_id, frame_name)
        event_type = _infer_event_type(brand_guide)

        visual_keywords = _build_visual_keywords(
            brand_mood, channel_id, template_family, intended_use, policy
        )
        selection_entry = selection_map.get(_deliverable_id_from_frame(frame_id))
        source_candidate_id = _extract_source_candidate(selection_entry, frame_id)

        score, breakdown = _compute_reuse_score(
            channel_id=channel_id,
            template_family=template_family,
            frame_name=frame_name,
            intended_use=intended_use,
            policy=policy,
        )
        breakdown["template_inference_source"] = template_inference["source"]
        if template_inference["warning"]:
            breakdown["template_inference_warning"] = template_inference["warning"]
        reuse_status = _score_to_status(score, policy)
        reuse_recommended = _recommend_channels(channel_id, event_type, policy)

        approved_path = _approved_path(event_id, frame.get("exportFileName", f"{frame_id}.png"))
        reusable_path = (
            _reusable_path(channel_id, template_family, frame.get("exportFileName", f"{frame_id}.png"))
            if reuse_status == "reusable"
            else ""
        )

        tags = _build_tags(
            channel_id=channel_id,
            width=frame.get("width", 0),
            height=frame.get("height", 0),
            reuse_status=reuse_status,
            policy=policy,
        )

        asset_id = f"{event_id}__{frame_id}"

        assets.append({
            "asset_id": asset_id,
            "event_id": event_id,
            "event_type": event_type,
            "channel_id": channel_id,
            "template_family": template_family,
            "template_id": template_family if template_family != "unknown" else "",
            "template_inference_source": template_inference["source"],
            "template_inference_warning": template_inference["warning"],
            "intended_use": intended_use,
            "visual_keywords": visual_keywords,
            "tags": tags,
            "qa_status": "pass",
            "reuse_score": round(score, 3),
            "reuse_score_breakdown": breakdown,
            "reuse_recommended_for": reuse_recommended,
            "reuse_status": reuse_status,
            "source_candidate_id": source_candidate_id,
            "source_run_id": source_run_id,
            "archive_path_approved": approved_path,
            "archive_path_reusable": reusable_path,
            "source_export_path": frame.get("sourceExportPath", ""),
            "dimensions": {
                "width": frame.get("width", 0),
                "height": frame.get("height", 0),
            },
            "archived_at": archived_at,
        })

    return assets, filtered_out


# ---------------------------------------------------------------------------
# reuse_score calculation (policy-driven, auditable)
# ---------------------------------------------------------------------------

def _compute_reuse_score(
    channel_id: str,
    template_family: str,
    frame_name: str,
    intended_use: str,
    policy: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    cfg = policy.get("reuse_score", {})
    components = cfg.get("components", {})

    qa_weight = components.get("qa_pass", {}).get("weight", 0.3)

    ch_weight = 0.0
    friendly = components.get("channel_suitability", {}).get("reuse_friendly_channels", [])
    if channel_id in friendly:
        ch_weight = components.get("channel_suitability", {}).get("weight", 0.1)

    tpl_weight = 0.0
    stable = components.get("template_stability", {}).get("stable_template_families", [])
    if template_family in stable:
        tpl_weight = components.get("template_stability", {}).get("weight", 0.1)

    penalty_cfg = components.get("event_specificity_penalty", {})
    keywords = penalty_cfg.get("penalty_keywords", [])
    per_kw = penalty_cfg.get("per_keyword_penalty", 0.1)
    max_pen = penalty_cfg.get("max_penalty", 0.3)
    search_text = f"{frame_name} {intended_use}".lower()
    hits = sum(1 for kw in keywords if kw in search_text)
    penalty = min(hits * per_kw, max_pen)

    score = qa_weight + ch_weight + tpl_weight - penalty
    score = max(0.0, min(1.0, score))

    breakdown = {
        "qa_pass": qa_weight,
        "channel_suitability": ch_weight,
        "template_stability": tpl_weight,
        "event_specificity_penalty": -penalty,
    }
    return score, breakdown


def _score_to_status(score: float, policy: dict[str, Any]) -> str:
    cfg = policy.get("reuse_score", {})
    if score >= cfg.get("reusable_threshold", 0.7):
        return "reusable"
    if score >= cfg.get("limited_reuse_threshold", 0.4):
        return "limited_reuse"
    return "not_reusable"


# ---------------------------------------------------------------------------
# File copy helpers
# ---------------------------------------------------------------------------

def _copy_to_assets(assets: list[dict[str, Any]], run_dir: Path, policy: dict[str, Any]) -> None:
    dest_cfg = policy.get("destination_dirs", {})
    assets_root = ROOT / "assets"

    for asset in assets:
        src = _resolve_source_file(asset, run_dir)
        if src is None or not src.exists():
            continue

        approved_dest = assets_root / asset["archive_path_approved"]
        _safe_copy(src, approved_dest)

        if asset["reuse_status"] == "reusable" and asset["archive_path_reusable"]:
            reusable_dest = assets_root / asset["archive_path_reusable"]
            _safe_copy(src, reusable_dest)


def _resolve_source_file(asset: dict[str, Any], run_dir: Path) -> Path | None:
    source_export_path = asset.get("source_export_path", "")
    if source_export_path:
        source = run_dir / source_export_path
        if source.exists():
            return source
    approved_path = asset.get("archive_path_approved", "")
    if not approved_path:
        return None
    filename = Path(approved_path).name
    candidates = [
        run_dir / "06_qa_packaging" / "package" / "final" / filename,
        run_dir / "05_figma_assembly" / "exports" / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _safe_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        version = 2
        while True:
            candidate = dest.parent / f"{stem}_v{version}{suffix}"
            if not candidate.exists():
                dest = candidate
                break
            version += 1
    shutil.copy2(src, dest)


# ---------------------------------------------------------------------------
# Index management (upsert)
# ---------------------------------------------------------------------------

def _upsert_global_index(assets: list[dict[str, Any]], archived_at: str) -> None:
    index_path = ROOT / "assets" / "indexes" / "global-index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    existing = read_json(index_path, default={"updated_at": "", "assets": []}) if index_path.exists() else {"updated_at": "", "assets": []}

    by_id: dict[str, dict[str, Any]] = {a["asset_id"]: a for a in existing.get("assets", [])}
    for asset in assets:
        record = dict(asset)
        record["updated_at"] = archived_at
        by_id[asset["asset_id"]] = record

    write_json(index_path, {
        "updated_at": archived_at,
        "assets": list(by_id.values()),
    })


def _write_event_index(assets: list[dict[str, Any]], event_id: str, archived_at: str) -> None:
    event_index_dir = ROOT / "assets" / "indexes" / "by-event"
    event_index_dir.mkdir(parents=True, exist_ok=True)
    write_json(event_index_dir / f"{event_id}.json", {
        "event_id": event_id,
        "updated_at": archived_at,
        "assets": assets,
    })


# ---------------------------------------------------------------------------
# reuse-notes.md builder
# ---------------------------------------------------------------------------

def _build_reuse_notes(assets: list[dict[str, Any]], event_id: str, archived_at: str) -> str:
    reusable = [a for a in assets if a["reuse_status"] == "reusable"]
    limited = [a for a in assets if a["reuse_status"] == "limited_reuse"]

    lines: list[str] = [
        f"# 재사용 요약 — {event_id}",
        f"",
        f"생성일: {archived_at[:10]}  |  전체 자산: {len(assets)}개  |  재사용 가능: {len(reusable)}개  |  제한적 재사용: {len(limited)}개",
        "",
    ]

    if reusable:
        lines += ["## 다음 이벤트에 바로 쓸 수 있는 자산", ""]
        by_channel: dict[str, list[dict[str, Any]]] = {}
        for a in reusable:
            by_channel.setdefault(a["channel_id"], []).append(a)
        for channel, items in sorted(by_channel.items()):
            lines.append(f"### {channel}")
            for a in items:
                score_str = f"{a['reuse_score']:.2f}"
                recommended = ", ".join(a["reuse_recommended_for"]) or "—"
                lines.append(f"- **{a['intended_use']}** (`{a['asset_id']}`)")
                lines.append(f"  - 재사용 점수: {score_str}  |  추천 채널: {recommended}")
                lines.append(f"  - 경로: `{a['archive_path_reusable']}`")
            lines.append("")

    if limited:
        lines += ["## 부분 수정 후 재사용 가능한 자산", ""]
        for a in limited:
            lines.append(f"- `{a['asset_id']}` ({a['channel_id']} / {a['template_family']})")
            lines.append(f"  - 점수: {a['reuse_score']:.2f}  |  제한 이유: 이벤트 특정 문구 포함 가능")
        lines.append("")

    if not reusable and not limited:
        lines += [
            "## 재사용 가능 자산 없음",
            "",
            "이번 이벤트 자산은 특정 날짜·이벤트 조건에 강하게 묶여 있어 재사용 권장 자산이 없습니다.",
            "",
        ]

    lines += [
        "---",
        "",
        "> 이 문서는 운영자 참고용입니다. 자동화 시스템은 `asset-archive.json`을 읽습니다.",
    ]

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------

def _build_template_context(
    channel_outputs: dict[str, Any],
    content_plan: dict[str, Any],
    selected_assets: dict[str, Any],
) -> dict[str, dict[str, dict[str, str]]]:
    by_output_id: dict[str, dict[str, str]] = {}
    by_deliverable_id: dict[str, dict[str, str]] = {}

    for output in channel_outputs.get("outputs", []):
        template_id = output.get("template_id", "")
        record = {
            "template_id": template_id,
            "source": "channel-outputs.template_id",
        }
        if output.get("output_id"):
            by_output_id[output["output_id"]] = record
        if output.get("deliverable_id"):
            by_deliverable_id[output["deliverable_id"]] = record

    for deliverable in content_plan.get("deliverables", []):
        deliverable_id = deliverable.get("deliverable_id", "")
        template_id = deliverable.get("template_id", "")
        if deliverable_id and template_id and deliverable_id not in by_deliverable_id:
            by_deliverable_id[deliverable_id] = {
                "template_id": template_id,
                "source": "content-plan.deliverables[].template_id",
            }

    selections = selected_assets if isinstance(selected_assets, list) else selected_assets.get("selectedAssets", selected_assets.get("selections", []))
    for selection in selections:
        deliverable_id = selection.get("deliverable_id") or selection.get("deliverableId")
        template_id = selection.get("template_id") or selection.get("templateId")
        if deliverable_id and template_id and deliverable_id not in by_deliverable_id:
            by_deliverable_id[deliverable_id] = {
                "template_id": template_id,
                "source": "selected-assets.template_id",
            }

    return {
        "by_output_id": by_output_id,
        "by_deliverable_id": by_deliverable_id,
    }


def _infer_template_identity(
    frame: dict[str, Any],
    channel_id: str,
    template_context: dict[str, dict[str, dict[str, str]]],
) -> dict[str, str]:
    frame_id = frame.get("frameId", "")
    frame_name = frame.get("frameName", frame_id)
    deliverable_id = frame.get("deliverableId") or frame.get("deliverable_id") or _deliverable_id_from_frame(frame_id)

    candidates = [
        (frame.get("template_id") or frame.get("templateId"), "final-package-manifest.template_id"),
        (template_context["by_output_id"].get(frame_id, {}).get("template_id"), template_context["by_output_id"].get(frame_id, {}).get("source", "")),
        (template_context["by_deliverable_id"].get(deliverable_id, {}).get("template_id"), template_context["by_deliverable_id"].get(deliverable_id, {}).get("source", "")),
        (_infer_template_id_from_registry(channel_id, frame_id, frame_name), "filename_pattern"),
    ]

    for template_id, source in candidates:
        if not template_id:
            continue
        valid, warning = _validate_template_id(template_id)
        if valid:
            return {"template_id": template_id, "source": source or "unknown", "warning": ""}
        if source == "final-package-manifest.template_id":
            return {"template_id": "unknown", "source": source, "warning": warning}

    return {
        "template_id": "unknown",
        "source": "unresolved",
        "warning": f"No registry-backed template could be inferred for frame_id={frame_id}, channel_id={channel_id}",
    }


def _validate_template_id(template_id: str) -> tuple[bool, str]:
    try:
        template_registry.get(template_id)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _infer_template_id_from_registry(channel_id: str, frame_id: str, frame_name: str) -> str:
    text = channel_registry.normalize_token(f"{frame_id} {frame_name}")
    templates = [t for t in template_registry.list_all() if t.get("channel_id") == channel_id]
    if not templates:
        return ""

    for template in templates:
        template_id = template.get("template_id", "")
        if template_id and channel_registry.normalize_token(template_id) in text:
            return template_id

    matched = [
        template
        for template in templates
        if _template_tokens_match(template.get("template_id", ""), text)
    ]
    if len(matched) == 1:
        return matched[0].get("template_id", "")

    if len(templates) == 1:
        return templates[0].get("template_id", "")
    return ""


def _template_tokens_match(template_id: str, text: str) -> bool:
    tokens = [token for token in channel_registry.normalize_token(template_id).split("_") if token not in {"v1", "v2"}]
    meaningful = [token for token in tokens if token not in {"instagram", "blog", "community"}]
    return bool(meaningful) and all(token in text for token in meaningful[:2])

def _infer_template_family(frame_id: str, frame_name: str) -> str:
    text = f"{frame_id} {frame_name}".lower()
    if "card_news" in text or "cardnews" in text or "카드뉴스" in text:
        return "card_news"
    if "single_feed" in text or "feed_single" in text or "instagram_feed" in text or "단일" in text or "피드" in text:
        return "single_feed"
    if "thumbnail" in text or "썸네일" in text:
        return "blog_thumbnail"
    if "inline_image" in text or "section" in text or "섹션" in text:
        return "blog_section"
    if "story" in text or "스토리" in text:
        return "story"
    return "unknown"


def _canonical_archive_channel(channel_id: str, frame_id: str, frame_name: str) -> str:
    try:
        return channel_registry.canonicalize(channel_id)
    except Exception:
        pass

    try:
        candidates = channel_registry.resolve_requested(channel_id)
    except Exception:
        return channel_registry.normalize_token(channel_id) or "unknown"

    text = channel_registry.normalize_token(f"{frame_id} {frame_name}")
    for candidate in candidates:
        if candidate in text:
            return candidate

    template_family = _infer_template_family(frame_id, frame_name)
    for candidate in candidates:
        if template_family and template_family in candidate:
            return candidate
        if template_family == "single_feed" and "feed" in candidate:
            return candidate
        if template_family == "blog_section" and "inline" in candidate:
            return candidate

    return candidates[0] if candidates else channel_registry.normalize_token(channel_id)


def _infer_intended_use(frame_id: str, frame_name: str) -> str:
    text = f"{frame_id} {frame_name}".lower()
    for keyword in ["hook", "problem", "benefit", "how_to", "cta", "thumbnail", "section", "outro", "intro"]:
        if keyword in text:
            return keyword
    return "content"


def _infer_event_type(brand_guide: dict[str, Any]) -> str:
    objective = str(brand_guide.get("eventObjective") or brand_guide.get("objective") or "").lower()
    if any(w in objective for w in ["투자", "금융", "상담", "investment", "financial"]):
        return "investment_consulting"
    if any(w in objective for w in ["출시", "launch", "신제품"]):
        return "product_launch"
    if any(w in objective for w in ["할인", "sale", "이벤트", "프로모션"]):
        return "seasonal_sale"
    return "general"


def _build_visual_keywords(
    brand_mood: list[str],
    channel_id: str,
    template_family: str,
    intended_use: str,
    policy: dict[str, Any],
) -> list[str]:
    keywords: list[str] = []
    keywords.extend(brand_mood)
    keywords.append(channel_id)
    if template_family != "unknown":
        keywords.append(template_family)
    if intended_use not in ("content", "unknown"):
        keywords.append(intended_use)
    return list(dict.fromkeys(kw for kw in keywords if kw))


def _recommend_channels(channel_id: str, event_type: str, policy: dict[str, Any]) -> list[str]:
    rec = policy.get("reuse_recommendation", {})
    channel_affinities = rec.get("channel_affinities", {})
    return list(channel_affinities.get(channel_id, [channel_id]))


def _build_tags(
    channel_id: str,
    width: int,
    height: int,
    reuse_status: str,
    policy: dict[str, Any],
) -> list[str]:
    auto_tags = policy.get("tagging", {}).get("auto_tags", {})
    tags: list[str] = []
    if "channel" in auto_tags:
        tags.append(f"channel:{channel_id}")
    if "format" in auto_tags and width and height:
        tags.append(f"format:{width}x{height}")
    if "reuse" in auto_tags:
        tags.append(f"reuse:{reuse_status}")
    return tags


def _deliverable_id_from_frame(frame_id: str) -> str:
    # instagram_card_news_01_slide_01 → instagram_card_news_01
    parts = frame_id.rsplit("_slide_", 1)
    if len(parts) > 1:
        return parts[0]
    return frame_id.removesuffix("_output")


def _extract_source_candidate(selection_entry: dict[str, Any] | None, frame_id: str) -> str:
    if not selection_entry:
        return ""
    return (
        selection_entry.get("candidate_id")
        or selection_entry.get("candidateId")
        or Path(selection_entry.get("filePath") or selection_entry.get("selected_file") or "").stem
        or ""
    )


def _approved_path(event_id: str, filename: str) -> str:
    return f"approved/{event_id}/{filename}"


def _reusable_path(channel_id: str, template_family: str, filename: str) -> str:
    return f"reusable/{channel_id}/{template_family}/{filename}"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _find_stage_file(run_dir: Path, stage: str, filename: str) -> Path:
    """Resolve a stage output file, checking stage root then output/ subdirectory."""
    direct = run_dir / stage / filename
    if direct.exists():
        return direct
    return run_dir / stage / "output" / filename


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    value = str(value).strip().lower()
    value = re.sub(r"[^\w가-힣-]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "event"
