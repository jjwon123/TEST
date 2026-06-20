"""MVP reference research stage.

This stage makes reference research a first-class pipeline checkpoint without
forcing a live Pinterest/browser run every time. By default it creates the
run-scoped reference search plan and summarizes any already-collected reference
manifest. Set REFERENCE_RESEARCH_MODE=auto_search to run the existing automatic
search/selection helper from this stage.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json, write_json, write_text
from core.utils.rulebook import (
    detect_event_profile,
    profile_avoid_keywords,
    profile_fallback_directions,
    profile_negative_prompt_hints,
    profile_prompt_hints,
    profile_reference_direction,
    profile_reject_terms,
    profile_selection_gates,
)
from core.utils.reference_training import score_record_against_training, training_summary
from scripts.reference_pipeline import auto_collect_from_search, create_plan
from services.ad_reference.meta_brand_provider import add_meta_brand_references, build_brief_context
from services.ad_reference.meta_source_mix_provider import add_meta_source_mix_references


STAGE_ID = "03_reference_research"


def run(
    run_dir: Path,
    mode: str = "run",
    outputs: list[str] | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    stage_dir = run_dir / STAGE_ID
    reference_dir = run_dir / "references"

    plan = create_plan(run_dir, force=mode == "regenerate")
    execution_mode = os.getenv("REFERENCE_RESEARCH_MODE", "plan").strip().lower()
    reviewer = os.getenv("REFERENCE_REVIEWER", "heuristic").strip() or "heuristic"

    if execution_mode == "auto_search":
        manifest = auto_collect_from_search(
            run_dir,
            query_limit=_int_env("REFERENCE_QUERY_LIMIT", 8),
            per_query_limit=_int_env("REFERENCE_PER_QUERY_LIMIT", 12),
            select_count=_int_env("REFERENCE_SELECT_COUNT", 20),
            headful=os.getenv("REFERENCE_HEADFUL", "").strip().lower() in {"1", "true", "yes", "y"},
            reviewer=reviewer,
            review_limit=_optional_int_env("REFERENCE_REVIEW_LIMIT"),
            review_model=os.getenv("REFERENCE_REVIEW_MODEL", "qwen2.5vl:7b"),
            review_host=os.getenv("REFERENCE_REVIEW_HOST", "http://127.0.0.1:11434"),
        )
        research_status = "references_selected"
    else:
        manifest = read_json(reference_dir / "reference-manifest.json", default={"assets": []})
        research_status = "planned"

    quality_filter_artifact = read_json(reference_dir / "reference-quality-filter.json", default={})
    event_input = read_json(run_dir / "event-input.json", default={})
    brand_guide = read_json(run_dir / "brand-guide.json", default={})
    brief = read_json(run_dir / "01_event_brief" / "brief.json", default={})
    content_plan = read_json(run_dir / "02_content_planning" / "content-plan.json", default={})
    reference_context = build_brief_context(brief or event_input, content_plan)
    meta_limit = _int_env("META_BRAND_REFERENCE_LIMIT", 8)
    reference_evidence = {
        "stage": STAGE_ID,
        "providers": {
            "pinterest": {"status": "preserved_in_reference_manifest"},
        },
    }
    if os.getenv("META_BRAND_REFERENCE_MODE", "auto").strip().lower() not in {"off", "disabled", "none"}:
        manifest, brand_evidence = add_meta_brand_references(
            run_dir,
            manifest,
            brief or event_input,
            content_plan,
            limit=meta_limit,
        )
        reference_evidence["providers"]["meta_brand_review"] = brand_evidence["providers"]["meta_brand_review"]
    else:
        reference_evidence["providers"]["meta_brand_review"] = {"status": "disabled"}
    if os.getenv("META_SOURCE_MIX_REFERENCE_MODE", "auto").strip().lower() not in {"off", "disabled", "none"}:
        manifest, source_mix_evidence = add_meta_source_mix_references(
            run_dir,
            manifest,
            reference_context,
            limit=_int_env("META_SOURCE_MIX_REFERENCE_LIMIT", 6),
        )
        reference_evidence["providers"]["meta_source_mix"] = source_mix_evidence
    else:
        reference_evidence["providers"]["meta_source_mix"] = {"status": "disabled"}
    write_json(reference_dir / "reference-manifest.json", manifest)
    evidence_path = stage_dir / "reference-evidence.json"
    write_json(evidence_path, reference_evidence)
    summary = _build_summary(
        plan,
        manifest,
        execution_mode,
        research_status,
        quality_filter_artifact=quality_filter_artifact,
        event_input=event_input,
        brand_guide=brand_guide,
    )
    summary_path = stage_dir / "reference-research.json"
    notes_path = stage_dir / "notes.md"
    quality_report = _build_quality_report(summary, manifest, quality_filter_artifact)
    quality_report_json_path = stage_dir / "reference-quality-report.json"
    quality_report_md_path = stage_dir / "reference-quality-report.md"
    write_json(summary_path, summary)
    write_json(quality_report_json_path, quality_report)
    write_text(notes_path, _build_notes(summary))
    write_text(quality_report_md_path, _build_quality_report_notes(quality_report))

    return {
        "stage_id": STAGE_ID,
        "status": "done",
        "outputs": [
            str((reference_dir / "reference-collection-plan.json").relative_to(run_dir)),
            str(summary_path.relative_to(run_dir)),
            str(notes_path.relative_to(run_dir)),
            str(quality_report_json_path.relative_to(run_dir)),
            str(quality_report_md_path.relative_to(run_dir)),
            str(evidence_path.relative_to(run_dir)),
        ],
        "notes": [f"Reference research {summary['status']}: {summary['selected_reference_count']} selected."],
        "next_state": "reference_ready",
        "regeneration_groups": {},
    }


def _build_summary(
    plan: dict[str, Any],
    manifest: dict[str, Any],
    execution_mode: str,
    status: str,
    quality_filter_artifact: dict[str, Any] | None = None,
    event_input: dict[str, Any] | None = None,
    brand_guide: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assets = manifest.get("assets", []) if isinstance(manifest, dict) else []
    selected = [asset for asset in assets if asset.get("status") == "selected"]
    reference_direction = _build_reference_direction(
        plan,
        selected,
        event_input=event_input or {},
        brand_guide=brand_guide or {},
    )
    event_profile = _event_profile(plan, event_input or {}, brand_guide or {})
    return {
        "stage": STAGE_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "execution_mode": execution_mode,
        "plan_path": "references/reference-collection-plan.json",
        "manifest_path": "references/reference-manifest.json",
        "query_count": len(plan.get("search_queries", [])),
        "queued_source_count": len(plan.get("source_boards", [])),
        "reference_count": len(assets),
        "selected_reference_count": len(selected),
        "intent": plan.get("intent", {}),
        "eventProfile": event_profile,
        "qualityFilter": _quality_filter_summary(manifest, event_profile),
        "ruleSources": {
            "brand_persona": "assets/rules/brand-persona.json",
            "event_rules": "assets/rules/event-rules.json",
            "reference_rules": "assets/rules/reference-rules.json",
            "visual_avoid_rules": "assets/rules/visual-avoid-rules.json",
            "tone_rules": "assets/rules/tone-rules.md",
        },
        "referenceDecisions": _reference_decisions(quality_filter_artifact or {}),
        "referenceTraining": training_summary(event_profile.get("category", "general")) if event_profile.get("category") == "bullion_investment" else {},
        **reference_direction,
        "next_step": "04_visual_candidates reads selected references from references/reference-manifest.json when available.",
    }


def _build_notes(summary: dict[str, Any]) -> str:
    lines = [
        "# Reference Research Notes",
        "",
        f"- Status: {summary['status']}",
        f"- Execution mode: {summary['execution_mode']}",
        f"- Queries: {summary['query_count']}",
        f"- Queued sources: {summary['queued_source_count']}",
        f"- References: {summary['reference_count']}",
        f"- Selected references: {summary['selected_reference_count']}",
        f"- Mood: {', '.join(summary.get('moodKeywords', [])) or 'none'}",
        f"- Composition: {', '.join(summary.get('compositionKeywords', [])) or 'none'}",
        f"- Lighting: {', '.join(summary.get('lightingKeywords', [])) or 'none'}",
        f"- Color: {', '.join(summary.get('colorPalette', [])) or 'none'}",
        f"- Quality profile: {summary.get('qualityFilter', {}).get('profile', 'default')}",
        f"- Accepted/shortlist/rejected: {len(summary.get('referenceDecisions', {}).get('accepted', []))}/{len(summary.get('referenceDecisions', {}).get('shortlist', []))}/{len(summary.get('referenceDecisions', {}).get('rejected', []))}",
        "",
        "## Prompt Hints",
        *[f"- {hint}" for hint in summary.get("promptHints", [])],
        "",
        "## Negative Prompt Hints",
        *[f"- {hint}" for hint in summary.get("negativePromptHints", [])],
        "",
        "## Next",
        f"- {summary['next_step']}",
        "",
    ]
    return "\n".join(lines)


def _build_reference_direction(
    plan: dict[str, Any],
    selected: list[dict[str, Any]],
    event_input: dict[str, Any] | None = None,
    brand_guide: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intent = plan.get("intent", {})
    event_input = event_input or {}
    brand_guide = brand_guide or {}
    brand_visual = brand_guide.get("visual", {}) if isinstance(brand_guide.get("visual"), dict) else {}
    brand_mood = _string_list(brand_visual.get("mood"))
    brand_colors = _string_list(brand_visual.get("brandColors"))
    event_references = _string_list(event_input.get("references"))
    has_specific_visual_direction = bool(brand_mood or brand_colors or event_references)
    text = _flatten_text({
        "intent": intent,
        "queries": [item.get("query", "") for item in plan.get("search_queries", [])],
        "selected": selected,
    }).lower()
    selected_refs = [_selected_reference_trace(asset) for asset in selected]
    event_profile_name = str(plan.get("intent", {}).get("event_profile") or "").strip() or "general"
    bullion_event = event_profile_name == "bullion_investment"
    rule_direction = profile_reference_direction(event_profile_name) if event_profile_name != "general" else {}

    mood = _keyword_hits(text, {
        "premium": ("프리미엄", "고급", "premium", "luxury", "럭셔리"),
        "calm": ("차분", "calm", "trust", "신뢰"),
        "fresh": ("봄", "spring", "fresh", "산뜻", "플라워", "flower"),
        "festive": ("크리스마스", "holiday", "연말", "festive"),
        "clean": ("clean", "클린", "미니멀", "minimal"),
        "financial-trust": ("금융", "투자", "상담", "시세", "gold", "금 "),
        "beauty-editorial": ("화장품", "뷰티", "스킨케어", "serum", "ampoule"),
        "jewelry-luxury": ("주얼리", "다이아", "jewelry", "diamond"),
    })
    if event_profile_name != "general":
        mood = _dedupe([*rule_direction.get("moodKeywords", []), *[item for item in mood if item not in {"fresh", "festive"}]])
    if brand_mood:
        mood = _dedupe([*brand_mood, *mood])
    composition = _keyword_hits(text, {
        "clear-focal-product": ("product", "제품", "focal", "good-product-focus"),
        "copy-safe-negative-space": ("copy_space", "copy space", "good-copy-space", "여백", "배너"),
        "card-news-layout": ("카드뉴스", "card"),
        "blog-cover-layout": ("블로그", "blog", "thumbnail"),
        "banner-layout": ("배너", "banner", "공지"),
        "centered-hero": ("hero", "대표", "key visual"),
    })
    if event_profile_name != "general":
        composition = _dedupe([*rule_direction.get("compositionKeywords", []), *composition])
    lighting = _keyword_hits(text, {
        "soft-studio-light": ("soft", "studio", "lighting", "useful-lighting"),
        "premium-contrast": ("premium", "luxury", "metal", "gold"),
        "bright-clean-light": ("clean", "white", "밝", "클린"),
        "natural-fresh-light": ("spring", "fresh", "flower", "봄"),
    })
    if event_profile_name != "general":
        lighting = _dedupe([*rule_direction.get("lightingKeywords", []), *[item for item in lighting if item != "natural-fresh-light"]])
    colors = _keyword_hits(text, {
        "gold": ("금", "gold", "골드"),
        "white": ("white", "흰", "하얀", "클린"),
        "green": ("green", "진정", "cica", "그린"),
        "blue": ("blue", "수분", "trust", "블루"),
        "pastel": ("pastel", "봄", "spring", "파스텔"),
        "red-green": ("christmas", "크리스마스", "holiday"),
    })
    if event_profile_name != "general":
        colors = _dedupe([*rule_direction.get("colorPalette", []), *[item for item in colors if item != "pastel"]])
    if brand_colors:
        colors = _dedupe(brand_colors)
    textures = _keyword_hits(text, {
        "metallic": ("금", "gold", "metal", "골드바", "은", "silver"),
        "glass": ("유리", "glass", "transparent", "투명"),
        "cosmetic-gloss": ("화장품", "serum", "ampoule", "스킨케어"),
        "jewelry-sparkle": ("diamond", "다이아", "sparkle", "주얼리"),
        "paper-editorial": ("블로그", "카드뉴스", "editorial"),
    })
    if event_profile_name != "general":
        textures = _dedupe([*rule_direction.get("materialTexture", []), *textures])
    avoid = _dedupe([
        "generic stock-photo feeling",
        "cluttered layout",
        "unreadable or baked-in text",
        "wrong product category cues",
        *(profile_avoid_keywords(event_profile_name) if event_profile_name != "general" else []),
        *[tag for asset in selected_refs for tag in asset.get("negativeTags", [])],
    ])
    prompt_hints = _dedupe([
        *(
            []
            if has_specific_visual_direction
            else (profile_prompt_hints(event_profile_name) if event_profile_name != "general" else [])
        ),
        *[f"event visual direction: {item}" for item in event_references],
        *[f"brand visual mood: {item}" for item in brand_mood],
        *[f"brand color: {item}" for item in brand_colors],
        *_format_hints("mood", mood),
        *_format_hints("composition", composition),
        *_format_hints("lighting", lighting),
        *_format_hints("color", colors),
        *_format_hints("material texture", textures),
        *[asset.get("promptHint", "") for asset in selected_refs],
    ])
    negative_hints = _dedupe([
        *avoid,
        *(profile_negative_prompt_hints(event_profile_name) if event_profile_name != "general" else []),
        "do not copy reference text, logos, watermarks, or exact brand marks",
        "use references for mood, layout, lighting, color, and composition only",
    ])
    return {
        "moodKeywords": mood,
        "compositionKeywords": composition,
        "lightingKeywords": lighting,
        "colorPalette": colors,
        "materialTexture": textures,
        "avoidKeywords": avoid,
        "promptHints": prompt_hints,
        "negativePromptHints": negative_hints,
        "selectedReferences": selected_refs,
    }


def _selected_reference_trace(asset: dict[str, Any]) -> dict[str, Any]:
    qwen = asset.get("qwen_review") or {}
    positive_tags = _string_list(asset.get("positive_tags") or qwen.get("positive_tags"))
    negative_tags = _string_list(asset.get("negative_tags") or qwen.get("negative_tags"))
    reason = str(qwen.get("reason") or asset.get("reason") or asset.get("text_relevance_reason") or "").strip()
    query = str(asset.get("query") or "").strip()
    return {
        "assetId": asset.get("asset_id") or asset.get("candidate_id") or "",
        "relativePath": asset.get("relative_path") or "",
        "originalPath": asset.get("original_path") or "",
        "query": query,
        "score": asset.get("review_score") or qwen.get("score") or asset.get("score") or 0,
        "evaluation": asset.get("evaluation", {}),
        "qualityGate": asset.get("quality_gate", {}),
        "decision": asset.get("review_decision") or qwen.get("decision") or asset.get("status") or "",
        "role": qwen.get("role") or asset.get("role") or "",
        "reason": reason,
        "positiveTags": positive_tags,
        "negativeTags": negative_tags,
        "promptHint": _join_sentence_parts([
            f"reference query: {query}" if query else "",
            f"reference role: {qwen.get('role') or asset.get('role')}" if (qwen.get("role") or asset.get("role")) else "",
            f"usable idea: {reason}" if reason else "",
        ]),
    }


def _event_profile(plan: dict[str, Any], event_input: dict[str, Any], brand_guide: dict[str, Any]) -> dict[str, Any]:
    text = _flatten_text(plan.get("intent", {})).lower()
    detected_profile = detect_event_profile(event_input, brand_guide)
    category = detected_profile if detected_profile != "general" else ("bullion_investment" if _is_bullion_investment_context(text) else "general")
    return {
        "category": category,
        "requiresSeriousnessFilter": category == "bullion_investment",
        "requiresBlankTextArea": True,
    }


def _quality_filter_summary(manifest: dict[str, Any], event_profile: dict[str, Any]) -> dict[str, Any]:
    source = manifest.get("selection") or manifest.get("auto_collection") or {}
    quality = source.get("quality_filter", {})
    bullion_profile = event_profile.get("requiresSeriousnessFilter")
    gates = profile_selection_gates("bullion_investment") if bullion_profile else {}
    return {
        "profile": quality.get("profile") or ("bullion_investment_strict_v1" if bullion_profile else "default_reference_quality_v1"),
        "minimums": gates,
        "accepted_count": quality.get("accepted_count", 0),
        "shortlist_count": quality.get("shortlist_count", 0),
        "rejected_count": quality.get("rejected_count", 0),
        "rejectRules": profile_reject_terms("bullion_investment") if bullion_profile else [],
    }


def _reference_decisions(quality_filter_artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "accepted": [_decision_trace(item) for item in quality_filter_artifact.get("accepted", [])],
        "shortlist": [_decision_trace(item) for item in quality_filter_artifact.get("shortlist", [])],
        "rejected": [_decision_trace(item) for item in quality_filter_artifact.get("rejected", [])],
    }


def _decision_trace(item: dict[str, Any]) -> dict[str, Any]:
    gate = item.get("quality_gate") or {}
    return {
        "assetId": item.get("asset_id") or item.get("candidate_id") or "",
        "relativePath": item.get("relative_path") or "",
        "query": item.get("query") or "",
        "decision": gate.get("decision") or item.get("review_decision") or item.get("status") or "",
        "reasons": gate.get("reasons") or [],
        "evaluation": item.get("evaluation", {}),
        "trainingAlignment": item.get("training_alignment", {}),
    }


def _build_quality_report(
    summary: dict[str, Any],
    manifest: dict[str, Any],
    quality_filter_artifact: dict[str, Any],
) -> dict[str, Any]:
    profile = summary.get("eventProfile", {}).get("category", "general")
    selected = [
        asset for asset in manifest.get("assets", [])
        if isinstance(asset, dict) and asset.get("status") == "selected"
    ]
    rejected = quality_filter_artifact.get("rejected", []) if isinstance(quality_filter_artifact, dict) else []
    shortlist = quality_filter_artifact.get("shortlist", []) if isinstance(quality_filter_artifact, dict) else []
    accepted = quality_filter_artifact.get("accepted", []) if isinstance(quality_filter_artifact, dict) else []
    reject_terms = profile_reject_terms(profile) if profile == "bullion_investment" else []
    selected_checks = [_selected_quality_check(asset, profile, reject_terms) for asset in selected]
    rejected_checks = [_rejected_quality_check(asset) for asset in rejected]
    fallback_check = _fallback_quality_check(profile)
    good_scores = [item["trainingAlignment"].get("goodScore", 0) for item in selected_checks]
    bad_scores = [item["trainingAlignment"].get("badScore", 0) for item in selected_checks]
    selected_category_coverage = _selected_category_coverage(selected_checks)
    selected_useful_for_coverage = _selected_useful_for_coverage(selected_checks)
    seed_summary = training_summary(profile) if profile == "bullion_investment" else {}
    selected_bad_count = sum(1 for item in selected_checks if item["badHits"] or item["trainingAlignment"].get("badScore", 0) >= 3)
    clear_reject_count = sum(1 for item in rejected_checks if item["hasClearReason"])
    status = "pass"
    issues: list[str] = []
    if selected_bad_count:
        status = "fail"
        issues.append("selected reference contains bad-category signals")
    if selected_checks and (sum(good_scores) / len(good_scores)) < 2:
        status = "warning" if status == "pass" else status
        issues.append("selected references have weak similarity to good seeds")
    if rejected_checks and clear_reject_count < len(rejected_checks):
        status = "warning" if status == "pass" else status
        issues.append("some rejected references lack clear reasons")
    if not fallback_check["clean"]:
        status = "fail"
        issues.append("fallback directions contain contaminated terms")
    required_categories = ["product_reference", "finance_mood_reference", "poster_layout_reference"]
    missing_categories = [category for category in required_categories if selected_category_coverage.get(category, 0) == 0]
    if missing_categories:
        status = "warning" if status == "pass" else status
        issues.append("selected references miss good seed categories: " + ", ".join(missing_categories))
    return {
        "stage": STAGE_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "status": status,
        "issues": issues,
        "summary": {
            "selected_count": len(selected_checks),
            "accepted_count": len(accepted),
            "shortlist_count": len(shortlist),
            "rejected_count": len(rejected),
            "selected_bad_signal_count": selected_bad_count,
            "average_good_training_score": round(sum(good_scores) / len(good_scores), 2) if good_scores else 0,
            "average_bad_training_score": round(sum(bad_scores) / len(bad_scores), 2) if bad_scores else 0,
            "clear_reject_reason_count": clear_reject_count,
        },
        "goodSeedCoverage": seed_summary.get("goodSeedCoverage", {}),
        "selectedCategoryCoverage": selected_category_coverage,
        "selectedCoverage": selected_useful_for_coverage,
        "referenceTraining": seed_summary,
        "fallback": fallback_check,
        "selectedChecks": selected_checks,
        "rejectedChecks": rejected_checks,
        "nextGate": "Run 04_visual_candidates only after selected_bad_signal_count is 0 and selected references show good seed similarity.",
    }


def _selected_quality_check(asset: dict[str, Any], profile: str, reject_terms: list[str]) -> dict[str, Any]:
    text = _flatten_text(asset).lower()
    bad_hits = [term for term in reject_terms if term.lower() in text]
    alignment = asset.get("training_alignment") or (
        score_record_against_training(asset, profile) if profile == "bullion_investment" else {}
    )
    return {
        "assetId": asset.get("asset_id", ""),
        "relativePath": asset.get("relative_path", ""),
        "query": asset.get("query", ""),
        "badHits": bad_hits,
        "trainingAlignment": alignment,
        "matchedCategories": alignment.get("matchedCategories", []),
        "matchedUsefulFor": alignment.get("matchedUsefulFor", []),
        "decision": "pass" if not bad_hits and alignment.get("badScore", 0) < 3 else "fail",
    }


def _selected_category_coverage(selected_checks: list[dict[str, Any]]) -> dict[str, int]:
    categories = {
        "product_reference": 0,
        "finance_mood_reference": 0,
        "poster_layout_reference": 0,
    }
    for item in selected_checks:
        for category in item.get("matchedCategories", []):
            if category in categories:
                categories[category] += 1
    return categories


def _selected_useful_for_coverage(selected_checks: list[dict[str, Any]]) -> dict[str, int]:
    keys = {
        "product_identity": 0,
        "mood": 0,
        "composition": 0,
        "lighting": 0,
        "headline_space": 0,
    }
    for item in selected_checks:
        for value in item.get("matchedUsefulFor", []):
            if value in keys:
                keys[value] += 1
    return keys


def _rejected_quality_check(asset: dict[str, Any]) -> dict[str, Any]:
    gate = asset.get("quality_gate") or {}
    reasons = gate.get("reasons") or []
    return {
        "assetId": asset.get("asset_id", ""),
        "relativePath": asset.get("relative_path", ""),
        "query": asset.get("query", ""),
        "reasons": reasons,
        "hasClearReason": bool(reasons),
        "trainingAlignment": asset.get("training_alignment", {}),
    }


def _fallback_quality_check(profile: str) -> dict[str, Any]:
    if profile != "bullion_investment":
        return {"profile": profile, "clean": True, "directions": [], "badHits": []}
    directions = profile_fallback_directions(profile)
    reject_terms = profile_reject_terms(profile)
    text = " ".join(directions).lower()
    bad_hits = [term for term in reject_terms if term.lower() in text]
    return {
        "profile": profile,
        "clean": not bad_hits,
        "directions": directions,
        "badHits": bad_hits,
        "contaminationBlock": "qwen_image_edit_1024.png is blocked for bullion fallback in 03_visual_candidates",
    }


def _build_quality_report_notes(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Reference Quality Report",
        "",
        f"- Status: {report.get('status', '')}",
        f"- Profile: {report.get('profile', '')}",
        f"- Selected: {summary.get('selected_count', 0)}",
        f"- Accepted/shortlist/rejected: {summary.get('accepted_count', 0)}/{summary.get('shortlist_count', 0)}/{summary.get('rejected_count', 0)}",
        f"- Selected bad signal count: {summary.get('selected_bad_signal_count', 0)}",
        f"- Average good training score: {summary.get('average_good_training_score', 0)}",
        f"- Average bad training score: {summary.get('average_bad_training_score', 0)}",
        f"- Fallback clean: {report.get('fallback', {}).get('clean', False)}",
        f"- Good seed coverage: {report.get('goodSeedCoverage', {})}",
        f"- Selected category coverage: {report.get('selectedCategoryCoverage', {})}",
        f"- Selected role coverage: {report.get('selectedCoverage', {})}",
        "",
        "## Issues",
        *(([f"- {issue}" for issue in report.get("issues", [])]) or ["- none"]),
        "",
        "## Selected Checks",
    ]
    for item in report.get("selectedChecks", []):
        alignment = item.get("trainingAlignment", {})
        lines.append(
            f"- {item.get('assetId', '')}: {item.get('decision', '')}, "
            f"good={alignment.get('goodScore', 0)}, bad={alignment.get('badScore', 0)}, "
            f"badHits={', '.join(item.get('badHits', [])) or 'none'}"
        )
    if not report.get("selectedChecks"):
        lines.append("- none")
    lines.extend(["", "## Rejected Checks"])
    for item in report.get("rejectedChecks", [])[:20]:
        lines.append(
            f"- {item.get('assetId', '')}: "
            f"{'; '.join(item.get('reasons', [])) or 'no clear reason'}"
        )
    if not report.get("rejectedChecks"):
        lines.append("- none")
    lines.extend(["", "## Next Gate", f"- {report.get('nextGate', '')}", ""])
    return "\n".join(lines)


def _is_bullion_investment_context(text: str) -> bool:
    tokens = (
        "bullion", "gold", "silver", "investment", "consultation", "asset management",
        "골드바", "금거래", "금융", "금 투자", "금 시세", "실물 금", "투자 상담",
    )
    return any(token in text for token in tokens)


def _bullion_reject_rules() -> list[str]:
    return [
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
    ]


def _bullion_avoid_keywords() -> list[str]:
    return [
        "toy-like",
        "childish",
        "kawaii mascot",
        "random wine bottle",
        "fake text",
        "unreadable typography",
        "cartoon camping scene",
        "theme park mood",
        "excessive cute character",
    ]


def _bullion_negative_prompt_hints() -> list[str]:
    return [
        "no fake text",
        "no unreadable letters",
        "no random product packaging",
        "no wine bottle",
        "no toy-like mascot",
        "no childish 3d scene",
    ]


def _bullion_prompt_hints() -> list[str]:
    return [
        "premium financial consultation campaign",
        "gold bullion or precious metal investment visual language",
        "high-trust finance brand mood",
        "poster layout with empty text area",
        "blank space for Korean headline",
        "no readable text",
        "no fake typography",
    ]


def _keyword_hits(text: str, groups: dict[str, tuple[str, ...]]) -> list[str]:
    hits = []
    for label, needles in groups.items():
        if any(needle.lower() in text for needle in needles):
            hits.append(label)
    return hits


def _format_hints(label: str, values: list[str]) -> list[str]:
    return [f"{label}: {', '.join(values)}"] if values else []


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _join_sentence_parts(parts: list[str]) -> str:
    return "; ".join(part for part in parts if part)


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _optional_int_env(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
