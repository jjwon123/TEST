"""Deterministic first-pass implementation for 01_event_brief.

This handler creates the minimum useful `brief.json` without calling an LLM.
It gives the pipeline a stable first executable stage while leaving room to add
LLM-assisted rewriting behind the same `run(...)` interface later.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json, write_json, write_text
from core.utils.category_campaign_review import detect_category, evaluate_category_risk
from core.utils.schema_validation import validate_json
from services.llm.client import LLMClient, LLMRequest
from services.research.client import ResearchClient, ResearchQuery
from services.ad_strategy.library import retrieve_patterns
from services.ad_strategy.planning_engine import build_strategic_brief


ROOT = Path(__file__).resolve().parents[3]
STAGE_ID = "01_event_brief"


def run(
    run_dir: Path,
    mode: str = "run",
    outputs: list[str] | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    event_input_path = run_dir / "event-input.json"
    brand_guide_path = run_dir / "brand-guide.json"

    event_input = read_json(event_input_path)
    brand_guide = read_json(brand_guide_path)

    input_schema = read_json(ROOT / "pipeline" / STAGE_ID / "input.schema.json")
    output_schema = read_json(ROOT / "pipeline" / STAGE_ID / "output.schema.json")
    core_brief_schema = read_json(ROOT / "core" / "schemas" / "brief.schema.json")
    validate_json(
        {"event_input": event_input, "brand_guide": brand_guide},
        input_schema,
        data_label=f"{event_input_path.name} + {brand_guide_path.name}",
        schema_label=f"pipeline/{STAGE_ID}/input.schema.json",
    )

    status = read_json(run_dir / "run-status.json", default={})
    event_id = status.get("event_id") or _slugify(event_input.get("eventName") or event_input.get("brandName") or "event")
    brief = build_brief(
        event_id,
        event_input,
        brand_guide,
        _load_research_evidence(run_dir, STAGE_ID),
    )
    validate_json(
        brief,
        output_schema,
        data_label=f"{STAGE_ID}/brief.json",
        schema_label=f"pipeline/{STAGE_ID}/output.schema.json",
    )
    validate_json(
        brief,
        core_brief_schema,
        data_label=f"{STAGE_ID}/brief.json",
        schema_label="core/schemas/brief.schema.json",
    )

    stage_dir = run_dir / STAGE_ID
    brief_path = stage_dir / "brief.json"
    strategic_brief_path = stage_dir / "strategic-brief.json"
    notes_path = stage_dir / "notes.md"
    write_json(brief_path, brief)
    write_json(strategic_brief_path, build_strategic_brief(brief))
    write_text(notes_path, build_notes(brief))

    return {
        "stage_id": STAGE_ID,
        "status": "review_pending",
        "outputs": [
            str(brief_path.relative_to(run_dir)),
            str(strategic_brief_path.relative_to(run_dir)),
            str(notes_path.relative_to(run_dir)),
        ],
        "notes": brief["open_questions"],
        "next_state": "brief_review",
    }


def build_brief(
    event_id: str,
    event_input: dict[str, Any],
    brand_guide: dict[str, Any],
    research_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    required_phrases = _unique_list(
        event_input.get("requiredPhrases", [])
        + brand_guide.get("requiredPhrases", [])
        + brand_guide.get("preferredWords", [])
    )
    banned_words = _unique_list(
        event_input.get("bannedWords", [])
        + brand_guide.get("bannedWords", [])
        + brand_guide.get("avoidWords", [])
    )
    tone = _as_list(brand_guide.get("tone") or brand_guide.get("voice", {}).get("tone"))
    style_rules = _as_list(brand_guide.get("styleRules") or brand_guide.get("voice", {}).get("style"))

    objective = event_input.get("objective") or event_input.get("purpose") or ""
    offer = event_input.get("offer") or ""
    target = event_input.get("target") or ""
    notes = event_input.get("notes") or ""

    core_messages = _core_messages(
        objective,
        offer,
        required_phrases,
        target=target,
        notes=notes,
    )
    open_questions = _open_questions(event_input, brand_guide)
    research_context = _build_research_context(event_input, brand_guide, open_questions, research_evidence)
    strategy_inspiration = retrieve_patterns({
        "event_input": event_input,
        "brand_guide": brand_guide,
    })
    draft = {
        "stage": STAGE_ID,
        "schema_version": "0.1.0",
        "event_id": event_id,
        "event_name": event_input.get("eventName") or event_input.get("name") or "",
        "brand": {
            "name": brand_guide.get("brandName") or event_input.get("brandName") or "",
            "tone": tone,
            "style_rules": style_rules,
            "visual_keywords": _as_list(brand_guide.get("visual", {}).get("mood")),
        },
        "objective": {
            "primary": objective,
            "secondary": [],
        },
        "target": {
            "summary": target,
        },
        "schedule": {
            "start_date": event_input.get("schedule", {}).get("startDate", ""),
            "end_date": event_input.get("schedule", {}).get("endDate", ""),
            "publish_date": event_input.get("schedule", {}).get("publishDate", ""),
        },
        "offer": {
            "summary": offer,
        },
        "channels": event_input.get("channels", []),
        "core_messages": core_messages,
        "constraints": {
            "required_phrases": required_phrases,
            "banned_words": banned_words,
            "brand_safety": _as_list(brand_guide.get("brandSafety", {}).get("disallowed")),
            "source_notes": notes,
        },
        "content_direction": {
            "tone": ", ".join(tone) if tone else "",
            "message_priority": core_messages,
            "visual_direction": _as_list(brand_guide.get("visual", {}).get("mood")),
        },
        "research_context": research_context,
        "strategy_inspiration": strategy_inspiration,
        "reasoning_trace": {},
        "quality_assessment": {},
        "open_questions": open_questions,
        "source_files": {
            "event_input": "event-input.json",
            "brand_guide": "brand-guide.json",
        },
        "approval_status": "review_pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    reasoning_request = _build_reasoning_request(event_input, brand_guide, research_context)
    generation_execution = LLMClient().execute_structured_generation(
        request_envelope=reasoning_request,
        draft=draft,
    )
    draft = generation_execution.get("result", draft)
    quality_assessment = _build_quality_assessment(
        event_input,
        brand_guide,
        open_questions,
        core_messages,
        research_context,
    )
    quality_assessment["category_detection"] = detect_category({
        "event_input": event_input,
        "brand_guide": brand_guide,
        "draft": draft,
    })
    quality_assessment["category_risk"] = evaluate_category_risk(
        brief={**draft, "quality_assessment": quality_assessment}
    )
    if quality_assessment["category_risk"].get("blocking"):
        quality_assessment.setdefault("flags", []).append("카테고리 리스크 검토에서 blocking 항목이 감지되었습니다.")
        quality_assessment["handoff_ready"] = False
        quality_assessment["approval_readiness"] = "needs_review"
    repair_execution = LLMClient().execute_local_repair(
        stage_id=STAGE_ID,
        draft=draft,
        quality_flags=quality_assessment.get("flags", []),
        context={"event_input": event_input, "brand_guide": brand_guide},
    )
    repaired = repair_execution.get("result", draft)
    if repair_execution.get("applied_repairs"):
        brand_for_quality = {
            **brand_guide,
            "visual": {"mood": repaired.get("content_direction", {}).get("visual_direction", [])},
        }
        quality_assessment = _build_quality_assessment(
            event_input,
            brand_for_quality,
            open_questions,
            core_messages,
            research_context,
        )
        quality_assessment["category_detection"] = detect_category({
            "event_input": event_input,
            "brand_guide": brand_guide,
            "draft": repaired,
        })
        quality_assessment["category_risk"] = evaluate_category_risk(
            brief={**repaired, "quality_assessment": quality_assessment}
        )
        if quality_assessment["category_risk"].get("blocking"):
            quality_assessment.setdefault("flags", []).append("카테고리 리스크 검토에서 blocking 항목이 감지되었습니다.")
            quality_assessment["handoff_ready"] = False
            quality_assessment["approval_readiness"] = "needs_review"
    quality_assessment["repair_history"] = {
        "status": repair_execution.get("status", "no_change"),
        "applied_repairs": repair_execution.get("applied_repairs", []),
        "result_changed": bool(repair_execution.get("applied_repairs")),
    }
    repaired["quality_assessment"] = quality_assessment
    repaired["reasoning_trace"] = _build_reasoning_trace(
        reasoning_request,
        generation_execution,
        quality_assessment,
    )
    return repaired


def build_notes(brief: dict[str, Any]) -> str:
    lines = [
        f"# {brief['event_name']} Brief Notes",
        "",
        "This file is an approval review summary for the human operator. It is not the canonical data contract; `brief.json` is the source consumed by downstream stages.",
        "",
        f"- Stage: {STAGE_ID}",
        f"- Approval status: {brief['approval_status']}",
        f"- Primary objective: {brief['objective']['primary'] or 'not provided'}",
        f"- Channels: {', '.join(brief.get('channels', [])) or 'not provided'}",
        f"- Research status: {brief.get('research_context', {}).get('status', 'not_needed')}",
        f"- Planning confidence: {brief.get('quality_assessment', {}).get('confidence', 'unknown')}",
        f"- Category risk: {brief.get('quality_assessment', {}).get('category_risk', {}).get('severity', 'not_detected')}",
        "",
        "## Open Questions",
    ]
    questions = brief.get("open_questions") or []
    lines.extend([f"- {question}" for question in questions] or ["- None"])
    lines.extend([
        "",
        "## Quality Flags",
    ])
    flags = brief.get("quality_assessment", {}).get("flags", [])
    lines.extend([f"- {flag}" for flag in flags] or ["- None"])
    category_risk = brief.get("quality_assessment", {}).get("category_risk", {})
    if category_risk.get("detected"):
        lines.extend([
            "",
            "## Category Risk",
            f"- Category: {category_risk.get('label', category_risk.get('category_id'))}",
            f"- Reference: {category_risk.get('reference_path', '')}",
            f"- Blocking: {category_risk.get('blocking', False)}",
        ])
        repairs = category_risk.get("repair_required", [])
        lines.extend([f"- Repair: {item}" for item in repairs] or ["- Repair: None"])
    lines.append("")
    return "\n".join(lines)


def _core_messages(
    objective: str,
    offer: str,
    required_phrases: list[str],
    *,
    target: str = "",
    notes: str = "",
) -> list[str]:
    messages = []
    if target:
        messages.append(f"공감 진입: {target}. 타깃이 자신의 일상 문제를 알아보도록 구체적인 상황에서 시작한다.")
    if required_phrases:
        messages.append(f"핵심 제안 방향: {required_phrases[0]}. 실행 가능한 데일리 루틴으로 설명한다.")
    if len(required_phrases) > 1:
        messages.append(f"제품 역할 정의: {required_phrases[1]}. 루틴 안에서 맡는 역할과 사용 이유를 명확히 한다.")
    if offer:
        messages.append(f"전환 이유: {offer}")
    if notes:
        messages.append(f"기획 원칙: {notes}")
    if not messages and objective:
        messages.append(f"사업 목표: {objective}")
    return _unique_list(messages)[:5]


def _open_questions(event_input: dict[str, Any], brand_guide: dict[str, Any]) -> list[str]:
    checks = [
        ("eventName", event_input, "이벤트명이 필요합니다."),
        ("target", event_input, "타깃 설명이 비어 있습니다."),
        ("channels", event_input, "운영 채널이 비어 있습니다."),
        ("offer", event_input, "혜택/오퍼 설명이 비어 있습니다."),
        ("brandName", brand_guide, "브랜드명이 필요합니다."),
    ]
    questions = [message for key, source, message in checks if not source.get(key)]
    schedule = event_input.get("schedule", {})
    if not schedule.get("startDate") or not schedule.get("endDate"):
        questions.append("이벤트 시작일과 종료일이 모두 필요합니다.")
    if (
        schedule.get("publishDate")
        and schedule.get("startDate")
        and schedule["publishDate"] > schedule["startDate"]
    ):
        questions.append("게시일이 이벤트 시작일보다 늦습니다. 운영 의도를 확인해야 합니다.")
    if not brand_guide.get("styleRules") and not brand_guide.get("voice", {}).get("style"):
        questions.append("브랜드 문체/표현 규칙이 부족합니다.")
    return questions


def _build_research_context(
    event_input: dict[str, Any],
    brand_guide: dict[str, Any],
    open_questions: list[str],
    research_evidence: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    triggers = []
    queries: list[ResearchQuery] = []
    topic = event_input.get("eventName") or event_input.get("name") or event_input.get("brandName") or "campaign"

    category = event_input.get("category") or brand_guide.get("category") or ""
    if category:
        triggers.append("category_context")
        queries.append(ResearchQuery(
            query=f"{category} 소비자 관심사 트렌드",
            purpose="카테고리 맥락과 메시지 각도를 보강",
            required=False,
        ))

    target = event_input.get("target") or ""
    if target:
        triggers.append("audience_context")
        queries.append(ResearchQuery(
            query=f"{target} 대상 캠페인 메시지 반응 포인트",
            purpose="타깃별 공감 포인트와 설득 근거를 보강",
            required=False,
        ))

    if any("타깃" in item or "혜택" in item for item in open_questions):
        triggers.append("missing_core_context")
        queries.append(ResearchQuery(
            query=f"{topic} 유사 이벤트 사례",
            purpose="입력 누락 시 비교 가능한 기획 사례를 확보",
            required=True,
        ))

    client = ResearchClient()
    plan = client.build_plan(
        stage_id=STAGE_ID,
        topic=topic,
        triggers=triggers,
        queries=queries,
        context={
            "event_name": event_input.get("eventName") or event_input.get("name") or "",
            "brand_name": brand_guide.get("brandName") or event_input.get("brandName") or "",
        },
    )
    return client.execute_search(plan, research_evidence)


def _build_reasoning_request(
    event_input: dict[str, Any],
    brand_guide: dict[str, Any],
    research_context: dict[str, Any],
) -> dict[str, Any]:
    prompt = (
        "입력된 이벤트/브랜드 정보를 바탕으로 승인 가능한 전략 브리프를 작성한다. "
        "목적, 타깃, 혜택, 메시지 우선순위, 리스크, 다음 단계 제약을 명확히 구조화한다."
    )
    return LLMClient().build_request(LLMRequest(
        stage_id=STAGE_ID,
        prompt=prompt,
        context={
            "event_input": event_input,
            "brand_guide": brand_guide,
            "research_plan": research_context,
        },
        output_schema="pipeline/01_event_brief/output.schema.json",
        goals=[
            "브리프를 단순 요약이 아닌 전략 판단 문서로 정제",
            "누락 정보와 검증 필요 포인트를 승인 단계에서 드러냄",
            "후속 콘텐츠 기획이 그대로 소비 가능한 제약과 메시지 구조를 산출",
        ],
        guardrails=[
            "가격, 일정, 제휴, 법적 주장을 입력 없이 발명하지 않는다.",
            "근거가 부족하면 추정하지 말고 open_questions 또는 research plan으로 넘긴다.",
        ],
    ))


def _build_reasoning_trace(
    request: dict[str, Any],
    generation_execution: dict[str, Any],
    quality_assessment: dict[str, Any],
) -> dict[str, Any]:
    client = LLMClient()
    trace = {
        "mode": "llm_ready",
        "request": request,
        "generation_execution": {
            "status": generation_execution.get("status", "unknown"),
            "provider_execution": generation_execution.get("provider_execution", {}),
        },
        "expected_enrichment": [
            "objective_refinement",
            "target_interpretation",
            "message_hierarchy",
            "risk_detection",
        ],
    }
    flags = quality_assessment.get("flags", [])
    if flags:
        trace["repair_request"] = client.build_repair_request(
            stage_id=STAGE_ID,
            original_request=request,
            quality_flags=flags,
        )
    return trace


def _build_quality_assessment(
    event_input: dict[str, Any],
    brand_guide: dict[str, Any],
    open_questions: list[str],
    core_messages: list[str],
    research_context: dict[str, Any],
) -> dict[str, Any]:
    flags = []
    if open_questions:
        flags.append("승인 전에 핵심 입력 누락을 검토해야 합니다.")
    if len(core_messages) < 2:
        flags.append("핵심 메시지 폭이 좁아 후속 콘텐츠 전략이 단조로울 수 있습니다.")
    if not brand_guide.get("visual"):
        flags.append("비주얼 가이드가 약해 후속 이미지 방향 해석 차이가 커질 수 있습니다.")
    required_queries = [item for item in research_context.get("queries", []) if item.get("required")]
    if required_queries and research_context.get("status") != "evidence_attached":
        flags.append("필수 외부 근거가 아직 연결되지 않았습니다.")

    confidence = "high"
    if len(flags) >= 2:
        confidence = "low"
    elif flags:
        confidence = "medium"

    return {
        "confidence": confidence,
        "flags": flags,
        "approval_readiness": "needs_review" if flags else "ready_for_review",
        "handoff_ready": not flags,
        "coverage": {
            "has_objective": bool(event_input.get("objective") or event_input.get("purpose")),
            "has_target": bool(event_input.get("target")),
            "has_offer": bool(event_input.get("offer")),
            "has_brand_name": bool(brand_guide.get("brandName")),
            "has_schedule_window": bool(
                event_input.get("schedule", {}).get("startDate")
                and event_input.get("schedule", {}).get("endDate")
            ),
            "research_evidence_count": research_context.get("evidence_count", 0),
        },
    }


def _load_research_evidence(run_dir: Path, stage_id: str) -> list[dict[str, Any]]:
    candidates = [
        run_dir / stage_id / "research-evidence.json",
        run_dir / "research-evidence.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        payload = read_json(path)
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            return [item for item in payload["items"] if isinstance(item, dict)]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
    return []


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _unique_list(values: list[Any]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w가-힣-]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "event"
