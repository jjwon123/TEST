"""Data-driven first-pass implementation for 02_content_planning."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils import channel_registry, template_registry
from core.utils.category_campaign_review import evaluate_category_risk
from core.utils.json_io import read_json, write_json, write_text
from core.utils.schema_validation import validate_json
from services.llm.client import LLMClient, LLMRequest
from services.research.client import ResearchClient, ResearchQuery


ROOT = Path(__file__).resolve().parents[3]
STAGE_ID = "02_content_planning"


def run(
    run_dir: Path,
    mode: str = "run",
    outputs: list[str] | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    brief_path = run_dir / "01_event_brief" / "brief.json"
    brief = read_json(brief_path)
    approvals = read_json(run_dir / "approvals.json", default={"approvals": []})
    if not _brief_is_approved(approvals):
        raise ValueError("02_content_planning requires an approved 01_event_brief gate.")

    input_schema = read_json(ROOT / "pipeline" / STAGE_ID / "input.schema.json")
    output_schema = read_json(ROOT / "pipeline" / STAGE_ID / "output.schema.json")
    core_schema = read_json(ROOT / "core" / "schemas" / "content-plan.schema.json")
    validate_json({"brief": brief}, input_schema, data_label=str(brief_path), schema_label=f"pipeline/{STAGE_ID}/input.schema.json")

    content_plan = build_content_plan(
        brief,
        _load_research_evidence(run_dir, STAGE_ID),
    )
    validate_json(content_plan, output_schema, data_label=f"{STAGE_ID}/content-plan.json", schema_label=f"pipeline/{STAGE_ID}/output.schema.json")
    validate_json(content_plan, core_schema, data_label=f"{STAGE_ID}/content-plan.json", schema_label="core/schemas/content-plan.schema.json")

    stage_dir = run_dir / STAGE_ID
    plan_path = stage_dir / "content-plan.json"
    notes_path = stage_dir / "notes.md"
    write_json(plan_path, content_plan)
    write_text(notes_path, build_notes(content_plan))

    return {
        "stage_id": STAGE_ID,
        "status": "review_pending",
        "outputs": [str(plan_path.relative_to(run_dir)), str(notes_path.relative_to(run_dir))],
        "notes": content_plan.get("open_questions", []),
        "next_state": "plan_review",
    }


def build_content_plan(
    brief: dict[str, Any],
    research_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    channel_plans = []
    deliverables = []
    image_needs = []
    open_questions = []
    priority = 1

    for requested_channel in brief.get("channels", []):
        channel_ids = channel_registry.resolve_requested(requested_channel)
        for channel_id in channel_ids:
            policy = channel_registry.get(channel_id)
            template_ids = policy.get("supported_templates") or []
            default_template_id = policy.get("default_template")
            template = template_registry.get(default_template_id) if default_template_id else None

            plan = {
                "channel_id": policy["channel_id"],
                "channel_name": policy.get("name", policy["channel_id"]),
                "policy": {
                    "default_ratio": policy.get("default_ratio"),
                    "content_roles": policy.get("content_roles", []),
                    "qa_requirements": policy.get("qa_requirements", []),
                    "default_template": default_template_id,
                    "supported_templates": template_ids,
                },
            }
            channel_plans.append(plan)

            deliverable_id = f"{policy['channel_id']}_01"
            visual_need = _visual_need(policy, template)
            deliverable = {
                "deliverable_id": deliverable_id,
                "channel_id": policy["channel_id"],
                "format": policy.get("name", policy["channel_id"]),
                "ratio": (template or {}).get("ratio") or policy.get("default_ratio", ""),
                "purpose": _purpose_from_roles(policy.get("content_roles", []), brief),
                "copy_intent": _copy_intent(brief, policy.get("content_roles", []), priority),
                "visual_need": visual_need,
                "priority": priority,
                "template_id": default_template_id,
                "supported_templates": template_ids,
                "slides": _slides(policy),
            }
            deliverables.append(deliverable)
            image_needs.append({
                "image_need_id": f"{deliverable_id}_visual",
                "deliverable_id": deliverable_id,
                "channel_id": policy["channel_id"],
                "visual_role": _visual_role(policy),
                "ratio": deliverable["ratio"],
                "text_safe_area_required": True,
                "template_id": default_template_id,
            })
            if not default_template_id:
                open_questions.append(f"{policy['channel_id']} 채널에 default_template이 없습니다.")
            priority += 1

    research_context = _build_research_context(brief, deliverables, open_questions, research_evidence)
    strategy_summary = _build_strategy_summary(brief, deliverables, channel_plans)
    draft = {
        "stage": STAGE_ID,
        "schema_version": "0.1.0",
        "event_id": brief["event_id"],
        "event_name": brief.get("event_name", ""),
        "brief": {
            "objective": brief.get("objective", {}),
            "core_messages": brief.get("core_messages", []),
            "constraints": brief.get("constraints", {}),
        },
        "channel_plans": channel_plans,
        "deliverables": deliverables,
        "image_needs": image_needs,
        "strategy_summary": strategy_summary,
        "research_context": research_context,
        "reasoning_trace": {},
        "quality_assessment": {},
        "open_questions": open_questions,
        "approval_status": "review_pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    reasoning_request = _build_reasoning_request(brief, strategy_summary, research_context)
    generation_execution = LLMClient().execute_structured_generation(
        request_envelope=reasoning_request,
        draft=draft,
    )
    draft = generation_execution.get("result", draft)
    deliverables = draft.get("deliverables", deliverables)
    strategy_summary = draft.get("strategy_summary", strategy_summary)
    quality_assessment = _build_quality_assessment(
        brief=brief,
        deliverables=deliverables,
        image_needs=image_needs,
        open_questions=open_questions,
    )
    category_risk = evaluate_category_risk(brief=brief, deliverables=deliverables)
    _apply_category_risk(quality_assessment, category_risk)
    repair_execution = LLMClient().execute_local_repair(
        stage_id=STAGE_ID,
        draft=draft,
        quality_flags=quality_assessment.get("flags", []),
        context={"brief": brief},
    )
    repaired = repair_execution.get("result", draft)
    repaired_deliverables = repaired.get("deliverables", deliverables)
    quality_assessment = _build_quality_assessment(
        brief=brief,
        deliverables=repaired_deliverables,
        image_needs=image_needs,
        open_questions=open_questions,
    )
    category_risk = evaluate_category_risk(brief=brief, deliverables=repaired_deliverables)
    _apply_category_risk(quality_assessment, category_risk)
    quality_assessment["repair_history"] = {
        "status": repair_execution.get("status", "no_change"),
        "applied_repairs": repair_execution.get("applied_repairs", []),
        "result_changed": bool(repair_execution.get("applied_repairs")),
    }
    repaired["quality_assessment"] = quality_assessment
    repaired["strategy_summary"] = _build_strategy_summary(
        brief,
        repaired_deliverables,
        channel_plans,
    )
    repaired["reasoning_trace"] = _build_reasoning_trace(
        reasoning_request,
        generation_execution,
        repaired["strategy_summary"],
        research_context,
        quality_assessment,
    )
    return repaired


def build_notes(content_plan: dict[str, Any]) -> str:
    strategy = content_plan.get("strategy_summary", {})
    quality = content_plan.get("quality_assessment", {})
    lines = [
        f"# {content_plan.get('event_name', content_plan['event_id'])} Content Plan Notes",
        "",
        "This file summarizes the planning output for human approval. `content-plan.json` is the canonical downstream input.",
        "",
        f"- Deliverables: {len(content_plan.get('deliverables', []))}",
        f"- Image needs: {len(content_plan.get('image_needs', []))}",
        f"- Strategy thesis: {strategy.get('planning_thesis', 'not provided')}",
        f"- Quality status: {quality.get('status', 'unknown')}",
        f"- Category risk: {quality.get('category_risk', {}).get('severity', 'not_detected')}",
        "",
        "## Deliverable Logic",
    ]
    lines.extend(
        [
            f"- {item.get('deliverable_id')}: {item.get('strategic_role', '')}"
            for item in strategy.get("deliverable_logic", [])
        ]
        or ["- None"]
    )
    lines.extend([
        "",
        "## Open Questions",
    ])
    questions = content_plan.get("open_questions") or []
    lines.extend([f"- {question}" for question in questions] or ["- None"])
    category_risk = quality.get("category_risk", {})
    if category_risk.get("detected"):
        lines.extend([
            "",
            "## Category Risk",
            f"- Category: {category_risk.get('label', category_risk.get('category_id'))}",
            f"- Reference: {category_risk.get('reference_path', '')}",
            f"- Blocking: {category_risk.get('blocking', False)}",
        ])
        lines.extend([f"- Repair: {item}" for item in category_risk.get("repair_required", [])] or ["- Repair: None"])
    lines.append("")
    return "\n".join(lines)


def _purpose_from_roles(roles: list[str], brief: dict[str, Any]) -> str:
    if "entry_point" in roles or "single_announcement" in roles or "notice" in roles:
        return "이벤트 핵심 내용을 빠르게 이해시키고 참여 행동으로 연결한다."
    if "editorial_cover" in roles:
        return "이벤트를 설명형/에디토리얼 콘텐츠로 진입시키는 표지 역할을 한다."
    return brief.get("objective", {}).get("primary", "이벤트 메시지를 채널 특성에 맞게 전달한다.")


def _copy_intent(brief: dict[str, Any], roles: list[str], priority: int) -> str:
    messages = brief.get("core_messages", [])
    if not messages:
        return brief.get("objective", {}).get("primary", "")
    if "cta" in roles or "how_to_join" in roles:
        return messages[min(1, len(messages) - 1)]
    if "entry_point" in roles or "single_announcement" in roles:
        return messages[0]
    if "benefit" in roles and len(messages) > 1:
        return messages[1]
    return messages[min(priority - 1, len(messages) - 1)]


def _visual_need(policy: dict[str, Any], template: dict[str, Any] | None) -> str:
    slots = (template or {}).get("visual_slots", [])
    role = _visual_role(policy)
    slot_text = f" Template visual slots: {', '.join(slots)}." if slots else ""
    return f"{role} 후보 이미지가 필요하며 텍스트 오버레이 안전 영역을 확보해야 한다.{slot_text}"


def _visual_role(policy: dict[str, Any]) -> str:
    roles = policy.get("content_roles", [])
    if "entry_point" in roles or "editorial_cover" in roles:
        return "cover"
    if "section_break" in roles or "explanation_support" in roles:
        return "support"
    return "key_visual"


def _slides(policy: dict[str, Any]) -> list[dict[str, Any]]:
    typical = policy.get("typical_slides", [])
    if not typical:
        return []
    count = typical[0]
    roles = policy.get("content_roles", [])
    return [
        {
            "slide": index + 1,
            "role": roles[index] if index < len(roles) else "support",
        }
        for index in range(count)
    ]


def _brief_is_approved(approvals: dict[str, Any]) -> bool:
    return any(
        item.get("stage_id") == "01_event_brief" and item.get("status") == "approved"
        for item in approvals.get("approvals", [])
    )


def _build_research_context(
    brief: dict[str, Any],
    deliverables: list[dict[str, Any]],
    open_questions: list[str],
    research_evidence: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    triggers: list[str] = []
    queries: list[ResearchQuery] = []
    event_name = brief.get("event_name") or brief.get("event_id") or "campaign"
    target_summary = brief.get("target", {}).get("summary", "")

    if len(deliverables) >= 3:
        triggers.append("multi_channel_consistency")
        queries.append(
            ResearchQuery(
                query=f"{event_name} 멀티채널 캠페인 운영 사례",
                purpose="채널별 역할 분화와 반복 메시지 균형을 점검",
                required=False,
            )
        )
    if target_summary:
        triggers.append("audience_channel_fit")
        queries.append(
            ResearchQuery(
                query=f"{target_summary} 선호 콘텐츠 채널 최근 경향",
                purpose="채널 우선순위와 메시지 강조점 보강",
                required=False,
            )
        )
    if open_questions:
        triggers.append("execution_gap_review")

    client = ResearchClient()
    plan = client.build_plan(
        stage_id=STAGE_ID,
        topic=event_name,
        triggers=triggers,
        queries=queries,
        context={
            "deliverable_count": len(deliverables),
            "channel_count": len({item.get("channel_id") for item in deliverables}),
        },
    )
    return client.execute_search(plan, research_evidence)


def _build_strategy_summary(
    brief: dict[str, Any],
    deliverables: list[dict[str, Any]],
    channel_plans: list[dict[str, Any]],
) -> dict[str, Any]:
    objective = brief.get("objective", {}).get("primary", "")
    primary_message = (brief.get("core_messages") or [""])[0]
    planning_thesis = (
        f"{objective} 목표를 기준으로, '{primary_message}' 메시지를 채널별 역할에 맞게 분산한다."
        if objective and primary_message
        else "브리프의 핵심 목적과 메시지를 채널별 산출물에 일관되게 배치한다."
    )
    return {
        "planning_thesis": planning_thesis,
        "channel_roles": [
            {
                "channel_id": plan.get("channel_id"),
                "role": _channel_role_summary(plan),
            }
            for plan in channel_plans
        ],
        "deliverable_logic": [
            {
                "deliverable_id": item.get("deliverable_id"),
                "strategic_role": item.get("purpose", ""),
                "message_focus": item.get("copy_intent", ""),
            }
            for item in deliverables
        ],
        "handoff_focus": [
            "03_reference_research는 이벤트/채널 기준의 레퍼런스 검색 계획과 선택 레퍼런스 요약을 만든다.",
            "04_visual_candidates는 deliverable별 visual_need와 image_needs를 기준으로 후보를 생성한다.",
        ],
    }


def _channel_role_summary(plan: dict[str, Any]) -> str:
    roles = plan.get("policy", {}).get("content_roles", [])
    if "entry_point" in roles or "single_announcement" in roles:
        return "빠른 인지와 참여 유도"
    if "editorial_cover" in roles:
        return "설명형 진입과 맥락 확장"
    if "section_break" in roles or "explanation_support" in roles:
        return "이해 보조와 메시지 증폭"
    return "브리프 메시지 전달"


def _build_reasoning_request(
    brief: dict[str, Any],
    strategy_summary: dict[str, Any],
    research_context: dict[str, Any],
) -> dict[str, Any]:
    client = LLMClient()
    return client.build_request(
        LLMRequest(
            stage_id=STAGE_ID,
            prompt=(
                "승인된 전략 브리프를 실제 콘텐츠 전략 설계안으로 변환한다. "
                "채널 역할, 산출물 우선순위, 메시지 배치, 다음 제작 단계 인수조건을 명확히 한다."
            ),
            context={
                "brief": brief,
                "strategy_summary": strategy_summary,
                "research_plan": research_context,
            },
            output_schema="pipeline/02_content_planning/output.schema.json",
            goals=[
                "채널마다 존재 이유가 분명한 산출물 세트를 구성",
                "복수 채널 간 메시지 중복은 줄이고 역할 보완성은 높임",
                "시각 후보 생성 단계가 바로 사용할 수 있는 구체적 handoff 제공",
            ],
            guardrails=[
                "승인되지 않은 brief를 전제로 범위를 확장하지 않는다.",
                "채널 정책과 템플릿 메타데이터를 벗어난 산출물을 만들지 않는다.",
            ],
        )
    )


def _build_reasoning_trace(
    request: dict[str, Any],
    generation_execution: dict[str, Any],
    strategy_summary: dict[str, Any],
    research_context: dict[str, Any],
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
        "decision_basis": {
            "channel_count": len(strategy_summary.get("channel_roles", [])),
            "deliverable_count": len(strategy_summary.get("deliverable_logic", [])),
            "research_status": research_context.get("status", "not_needed"),
        },
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
    *,
    brief: dict[str, Any],
    deliverables: list[dict[str, Any]],
    image_needs: list[dict[str, Any]],
    open_questions: list[str],
) -> dict[str, Any]:
    flags: list[str] = []
    if not deliverables:
        flags.append("채널 산출물이 생성되지 않았습니다.")
    if len(image_needs) != len(deliverables):
        flags.append("산출물과 이미지 요구 정의의 개수가 일치하지 않습니다.")
    if open_questions:
        flags.append("승인 전에 템플릿 또는 범위 관련 질문을 해소해야 합니다.")
    if not brief.get("core_messages"):
        flags.append("브리프 메시지가 비어 있어 콘텐츠 전략의 설득력이 약합니다.")
    copy_intents = {item.get("copy_intent", "") for item in deliverables if item.get("copy_intent", "")}
    if len(deliverables) >= 3 and len(copy_intents) == 1:
        flags.append("복수 채널 산출물이 같은 copy intent에만 의존하고 있습니다.")

    status = "approval_ready" if not flags else "needs_review"
    return {
        "status": status,
        "handoff_ready": not flags,
        "flags": flags,
        "coverage": {
            "deliverable_count": len(deliverables),
            "image_need_count": len(image_needs),
            "message_count": len(brief.get("core_messages", [])),
            "distinct_copy_intent_count": len(copy_intents),
        },
    }


def _apply_category_risk(quality_assessment: dict[str, Any], category_risk: dict[str, Any]) -> None:
    quality_assessment["category_risk"] = category_risk
    if not category_risk.get("detected"):
        return
    if category_risk.get("blocking"):
        quality_assessment.setdefault("flags", []).append("카테고리 리스크 검토에서 blocking 항목이 감지되었습니다.")
        quality_assessment["handoff_ready"] = False
        quality_assessment["status"] = "needs_review"
        return
    if category_risk.get("warnings"):
        quality_assessment.setdefault("warnings", []).extend(category_risk["warnings"])


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
