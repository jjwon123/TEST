"""Metadata-first Figma assembly planning handler."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils import template_registry
from core.utils.json_io import read_json, write_json, write_text
from core.utils.schema_validation import validate_json
from services.figma.text_fitter import fits_slot


ROOT = Path(__file__).resolve().parents[3]
STAGE_ID = "05_figma_assembly"


def run(
    run_dir: Path,
    mode: str = "run",
    outputs: list[str] | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    brief = read_json(run_dir / "01_event_brief" / "brief.json")
    content_plan = read_json(run_dir / "02_content_planning" / "content-plan.json")
    selected_assets = read_json(
        run_dir / "04_admin_selection" / "selected-assets.json",
        default={
            "stage": "04_admin_selection",
            "event_id": brief["event_id"],
            "selections": [],
            "regeneration_requests": [],
            "approval_status": "draft",
        },
    )
    templates = template_registry.list_all()

    input_schema = read_json(ROOT / "pipeline" / STAGE_ID / "input.schema.json")
    output_schema = read_json(ROOT / "pipeline" / STAGE_ID / "output.schema.json")
    core_output_schema = read_json(ROOT / "core" / "schemas" / "channel-outputs.schema.json")
    copy_map_schema = read_json(ROOT / "pipeline" / STAGE_ID / "copy-map.schema.json")
    core_copy_map_schema = read_json(ROOT / "core" / "schemas" / "copy-map.schema.json")
    validate_json(
        {"brief": brief, "content_plan": content_plan, "selected_assets": selected_assets, "templates": templates},
        input_schema,
        data_label=f"{STAGE_ID} input",
        schema_label=f"pipeline/{STAGE_ID}/input.schema.json",
    )

    assembly_plan, copy_map, channel_outputs = build_outputs(brief, content_plan, selected_assets)
    validate_json(channel_outputs, output_schema, data_label=f"{STAGE_ID}/channel-outputs.json", schema_label=f"pipeline/{STAGE_ID}/output.schema.json")
    validate_json(channel_outputs, core_output_schema, data_label=f"{STAGE_ID}/channel-outputs.json", schema_label="core/schemas/channel-outputs.schema.json")
    validate_json(copy_map, copy_map_schema, data_label=f"{STAGE_ID}/copy-map.json", schema_label=f"pipeline/{STAGE_ID}/copy-map.schema.json")
    validate_json(copy_map, core_copy_map_schema, data_label=f"{STAGE_ID}/copy-map.json", schema_label="core/schemas/copy-map.schema.json")

    stage_dir = run_dir / STAGE_ID
    assembly_path = stage_dir / "figma-assembly-plan.json"
    copy_map_path = stage_dir / "copy-map.json"
    refined_copy_map_path = stage_dir / "refined-copy-map.json"
    channel_outputs_path = stage_dir / "channel-outputs.json"
    notes_path = stage_dir / "notes.md"
    write_json(assembly_path, assembly_plan)
    write_json(copy_map_path, copy_map)
    write_json(refined_copy_map_path, copy_map)
    write_json(channel_outputs_path, channel_outputs)
    write_text(notes_path, build_notes(copy_map, channel_outputs))

    return {
        "stage_id": STAGE_ID,
        "status": "done",
        "outputs": [
            str(assembly_path.relative_to(run_dir)),
            str(copy_map_path.relative_to(run_dir)),
            str(refined_copy_map_path.relative_to(run_dir)),
            str(channel_outputs_path.relative_to(run_dir)),
            str(notes_path.relative_to(run_dir)),
        ],
        "notes": [],
        "next_state": "qa_pending",
    }


def build_outputs(
    brief: dict[str, Any],
    content_plan: dict[str, Any],
    selected_assets: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    selected_by_deliverable = {
        item.get("deliverable_id"): item
        for item in selected_assets.get("selections", [])
        if item.get("decision") == "selected"
    }

    frames = []
    copy_items = []
    channel_output_items = []
    allocation_state = build_allocation_state(brief)

    for deliverable in content_plan.get("deliverables", []):
        template_id = deliverable.get("template_id")
        template = template_registry.get(template_id) if template_id else {}
        output_id = f"{deliverable['deliverable_id']}_output"
        frame_id = f"{deliverable['deliverable_id']}_frame_01"
        copy_slots = build_copy_slots(
            frame_id,
            output_id,
            deliverable,
            brief,
            content_plan,
            template,
            allocation_state,
        )
        copy_slots = refine_copy_slots(copy_slots, brief, deliverable, template)
        asset_slot = build_asset_slot(deliverable, selected_by_deliverable)

        frames.append({
            "frame_id": frame_id,
            "output_id": output_id,
            "deliverable_id": deliverable["deliverable_id"],
            "channel_id": deliverable["channel_id"],
            "template_id": template_id,
            "copy_slots": copy_slots,
            "asset_slots": [asset_slot],
        })
        copy_items.extend(copy_slots)
        channel_output_items.append({
            "output_id": output_id,
            "deliverable_id": deliverable["deliverable_id"],
            "channel_id": deliverable["channel_id"],
            "template_id": template_id,
            "expected_export_path": f"05_figma_assembly/exports/{output_id}.png",
            "expected_dimensions": {},
            "copy_slots": copy_slots,
            "asset_slots": [asset_slot],
        })

    assembly_plan = {
        "stage": STAGE_ID,
        "event_id": content_plan["event_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "frames": frames,
    }
    copy_map = {
        "stage": STAGE_ID,
        "event_id": content_plan["event_id"],
        "items": copy_items,
    }
    channel_outputs = {
        "stage": STAGE_ID,
        "event_id": content_plan["event_id"],
        "figma_file_key": "",
        "outputs": channel_output_items,
    }
    return assembly_plan, copy_map, channel_outputs


def build_copy_slots(
    frame_id: str,
    output_id: str,
    deliverable: dict[str, Any],
    brief: dict[str, Any],
    content_plan: dict[str, Any],
    template: dict[str, Any],
    allocation_state: dict[str, Any],
) -> list[dict[str, Any]]:
    text_slots = template.get("text_slots", ["headline"])
    max_lengths = template.get("max_text_length", {})
    items = []
    for index, text_slot in enumerate(text_slots):
        allocation = allocate_slot_copy(
            text_slot=text_slot,
            index=index,
            deliverable=deliverable,
            brief=brief,
            content_plan=content_plan,
            max_length=max_lengths.get(text_slot),
            allocation_state=allocation_state,
        )
        text_value = allocation["text_value"]
        items.append({
            "frame_id": frame_id,
            "output_id": output_id,
            "deliverable_id": deliverable["deliverable_id"],
            "text_slot": text_slot,
            "text_value": text_value,
            "source_stage": allocation["source_stage"],
            "source_field": allocation["source_field"],
            "template_id": deliverable.get("template_id"),
            "fit_status": "fits" if fits_slot(text_value, max_lengths.get(text_slot)) else "too_long",
            "slot_role": allocation["slot_role"],
            "allocation_rule": allocation["allocation_rule"],
            "required_phrase_applied": bool(allocation["required_phrases_applied"]),
            "required_phrases_applied": allocation["required_phrases_applied"],
        })
    return items


def build_allocation_state(brief: dict[str, Any]) -> dict[str, Any]:
    phrases = _dedupe(brief.get("constraints", {}).get("required_phrases", []))
    return {
        "all_required": phrases,
        "used_required": set(),
        "action": [p for p in phrases if _phrase_role(p) == "action"],
        "scarcity": [p for p in phrases if _phrase_role(p) == "scarcity"],
        "benefit": [p for p in phrases if _phrase_role(p) == "benefit"],
    }


def allocate_slot_copy(
    text_slot: str,
    index: int,
    deliverable: dict[str, Any],
    brief: dict[str, Any],
    content_plan: dict[str, Any],
    max_length: int | None,
    allocation_state: dict[str, Any],
) -> dict[str, Any]:
    slot_role = _slot_role(text_slot)
    selected: list[str] = []
    rule = ""

    if slot_role == "cta":
        selected = _select_phrases(allocation_state, ["action"], max_length, min_count=1)
        rule = "cta_action_phrase"
    elif slot_role == "scarcity":
        selected = _select_phrases(allocation_state, ["scarcity"], max_length, min_count=1)
        rule = "scarcity_phrase"
    elif slot_role == "headline":
        selected = _select_phrases(allocation_state, ["benefit"], max_length, min_count=1)
        rule = "headline_primary_benefit"
    else:
        selected = _select_phrases(
            allocation_state,
            ["benefit", "scarcity"],
            max_length,
            min_count=1,
            max_count=3,
            pack=True,
        )
        rule = "supporting_required_phrase_pack"

    if selected:
        return {
            "text_value": _compose_phrase_text(selected, slot_role),
            "source_stage": "01_event_brief",
            "source_field": "constraints.required_phrases",
            "slot_role": slot_role,
            "allocation_rule": rule,
            "required_phrases_applied": selected,
        }

    text_value, source_stage, source_field = _fallback_source_text(
        text_slot,
        index,
        deliverable,
        brief,
        content_plan,
        slot_role,
    )
    return {
        "text_value": text_value,
        "source_stage": source_stage,
        "source_field": source_field,
        "slot_role": slot_role,
        "allocation_rule": "fallback_copy_source",
        "required_phrases_applied": _contained_required_phrases(text_value, allocation_state),
    }


def _fallback_source_text(
    text_slot: str,
    index: int,
    deliverable: dict[str, Any],
    brief: dict[str, Any],
    content_plan: dict[str, Any],
    slot_role: str,
) -> tuple[str, str, str]:
    if text_slot in {"headline", "title"}:
        messages = brief.get("core_messages", [])
        return (messages[0] if messages else brief.get("event_name", ""), "01_event_brief", "core_messages[0]")
    if text_slot in {"body", "subcopy", "subtitle", "details", "caption"}:
        return deliverable.get("copy_intent", ""), "02_content_planning", _deliverable_field(content_plan, deliverable["deliverable_id"], "copy_intent")
    if slot_role == "cta":
        return "자세히 보기", "manual_override", "default_cta"
    return "", "manual_override", "unmapped"


def _select_phrases(
    allocation_state: dict[str, Any],
    roles: list[str],
    max_length: int | None,
    min_count: int = 1,
    max_count: int | None = None,
    pack: bool = False,
) -> list[str]:
    candidates: list[str] = []
    used = allocation_state["used_required"]
    for role in roles:
        candidates.extend([phrase for phrase in allocation_state.get(role, []) if phrase not in used])
    if not candidates:
        return []

    selected: list[str] = []
    for phrase in candidates:
        trial = [*selected, phrase]
        if fits_slot(_compose_phrase_text(trial, "support"), max_length):
            selected.append(phrase)
            if max_count is not None and len(selected) >= max_count:
                break
            if not pack and len(selected) >= min_count:
                break

    if len(selected) < min_count:
        return []
    used.update(selected)
    return selected


def _compose_phrase_text(phrases: list[str], slot_role: str) -> str:
    if len(phrases) == 1:
        return phrases[0]
    return " · ".join(phrases)


def _contained_required_phrases(text: str, allocation_state: dict[str, Any]) -> list[str]:
    phrases = [phrase for phrase in allocation_state["all_required"] if phrase and phrase in text]
    allocation_state["used_required"].update(phrases)
    return phrases


def _slot_role(text_slot: str) -> str:
    if text_slot in {"cta", "button", "button_label"}:
        return "cta"
    if text_slot in {"badge", "label", "tag", "info"}:
        return "scarcity"
    if text_slot in {"headline", "title"}:
        return "headline"
    if text_slot in {"details", "detail", "subtitle", "subcopy", "body", "caption"}:
        return "support"
    return "support"


def _phrase_role(phrase: str) -> str:
    action_tokens = ["신청", "예약", "문의", "구매", "참여", "보기", "다운로드", "상담"]
    scarcity_tokens = ["한정", "수량", "마감", "기간", "선착순", "오늘", "D-", "d-", "마지막"]
    if any(token in phrase for token in action_tokens):
        return "action"
    if any(token in phrase for token in scarcity_tokens):
        return "scarcity"
    return "benefit"


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def build_asset_slot(deliverable: dict[str, Any], selected_by_deliverable: dict[str, dict[str, Any]]) -> dict[str, Any]:
    selected = selected_by_deliverable.get(deliverable["deliverable_id"], {})
    return {
        "slot": "main_visual",
        "candidate_id": selected.get("candidate_id"),
        "selected_file": selected.get("selected_file"),
        "status": "selected" if selected else "pending_selection",
    }


def refine_copy_slots(
    copy_slots: list[dict[str, Any]],
    brief: dict[str, Any],
    deliverable: dict[str, Any],
    template: dict[str, Any],
) -> list[dict[str, Any]]:
    max_lengths = template.get("max_text_length", {})
    banned_words = _dedupe(brief.get("constraints", {}).get("banned_words", []))
    refined = []
    for item in copy_slots:
        candidate, rule = _refined_text_candidate(item, brief, deliverable)
        updated = dict(item)
        original = item.get("text_value", "")
        if _can_apply_refinement(
            original=original,
            candidate=candidate,
            required=item.get("required_phrases_applied", []),
            banned_words=banned_words,
            max_length=max_lengths.get(item.get("text_slot", "")),
            original_fit=item.get("fit_status", "unchecked"),
        ):
            updated["text_value_original"] = original
            updated["text_value"] = candidate
            updated["fit_status"] = "fits" if fits_slot(candidate, max_lengths.get(item.get("text_slot", ""))) else "too_long"
            updated["refinement_applied"] = candidate != original
            updated["refinement_rule"] = rule if candidate != original else "kept_original"
        else:
            updated["text_value_original"] = original
            updated["refinement_applied"] = False
            updated["refinement_rule"] = "rejected_guardrail"
        refined.append(updated)
    return refined


def _refined_text_candidate(
    item: dict[str, Any],
    brief: dict[str, Any],
    deliverable: dict[str, Any],
) -> tuple[str, str]:
    phrases = item.get("required_phrases_applied", [])
    slot_role = item.get("slot_role", "support")
    text = item.get("text_value", "")
    tone = str(brief.get("content_direction", {}).get("tone", ""))

    if item.get("allocation_rule") == "fallback_copy_source":
        return text, "fallback_copy_kept"
    if not phrases:
        return text, "no_required_phrase"
    if len(phrases) == 1:
        return phrases[0], f"{slot_role}_single_phrase"
    if slot_role == "cta":
        return phrases[0], "cta_short_action"
    if slot_role == "headline":
        return _headline_refinement(phrases, tone), "headline_phrase_refinement"
    if any(_phrase_role(phrase) == "scarcity" for phrase in phrases):
        return _scarcity_refinement(phrases), "scarcity_support_refinement"
    return _benefit_refinement(phrases), "benefit_support_refinement"


def _headline_refinement(phrases: list[str], tone: str) -> str:
    if len(phrases) == 2:
        return f"{phrases[0]}를 위한 {phrases[1]}"
    return phrases[0]


def _benefit_refinement(phrases: list[str]) -> str:
    if len(phrases) == 2:
        return f"{phrases[0]}과 {phrases[1]}을 함께"
    if len(phrases) == 3:
        return f"{phrases[0]}, {phrases[1]}, {phrases[2]}를 한 번에"
    return " · ".join(phrases)


def _scarcity_refinement(phrases: list[str]) -> str:
    scarcity = [phrase for phrase in phrases if _phrase_role(phrase) == "scarcity"]
    others = [phrase for phrase in phrases if _phrase_role(phrase) != "scarcity"]
    if scarcity and others:
        return f"{scarcity[0]} {', '.join(others)}"
    if len(phrases) == 2:
        return f"{phrases[0]} {phrases[1]}"
    return " · ".join(phrases)


def _can_apply_refinement(
    original: str,
    candidate: str,
    required: list[str],
    banned_words: list[str],
    max_length: int | None,
    original_fit: str,
) -> bool:
    if not candidate:
        return False
    if any(phrase and phrase not in candidate for phrase in required):
        return False
    if any(word and word in candidate for word in banned_words):
        return False
    if original_fit == "fits" and not fits_slot(candidate, max_length):
        return False
    return True


def build_notes(copy_map: dict[str, Any], channel_outputs: dict[str, Any]) -> str:
    refined_count = sum(1 for item in copy_map.get("items", []) if item.get("refinement_applied"))
    return "\n".join([
        "# Figma Assembly Notes",
        "",
        "This file summarizes assembly planning. `copy-map.json` is the canonical copy traceability layer for QA.",
        "",
        f"- Copy map items: {len(copy_map.get('items', []))}",
        f"- Refined copy items: {refined_count}",
        f"- Channel outputs: {len(channel_outputs.get('outputs', []))}",
        "",
    ])


def _deliverable_field(content_plan: dict[str, Any], deliverable_id: str, field: str) -> str:
    for index, item in enumerate(content_plan.get("deliverables", [])):
        if item.get("deliverable_id") == deliverable_id:
            return f"deliverables[{index}].{field}"
    return f"deliverables[].{field}"
