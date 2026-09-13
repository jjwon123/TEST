"""Role-separated external planning generation and critique loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.ad_strategy.local_critic import review_local_concepts, review_local_copy
from services.ad_strategy.planning_engine import build_concept_candidates, build_copy_package, detect_industry, score_planning
from services.ad_strategy.quality_gate import copy_character_count
from services.ad_strategy.repository import retrieve_corrections, retrieve_examples
from services.llm.openai_provider import OpenAIPlanningProvider


CONCEPT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["candidates"],
    "properties": {
        "candidates": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["conceptId", "axis", "name", "targetInsight", "corePromise", "emotionalDirection", "persuasionSequence", "offerPresentation", "cta", "headlineDirections", "expectedEffect", "risks", "strategyExampleIds", "status"],
                "properties": {
                    "conceptId": {"type": "string"},
                    "axis": {"type": "string"},
                    "name": {"type": "string"},
                    "targetInsight": {"type": "string"},
                    "corePromise": {"type": "string"},
                    "emotionalDirection": {"type": "string"},
                    "persuasionSequence": {"type": "array", "items": {"type": "string"}},
                    "offerPresentation": {"type": "string"},
                    "cta": {"type": "string"},
                    "headlineDirections": {"type": "array", "items": {"type": "string"}},
                    "expectedEffect": {"type": "string"},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "strategyExampleIds": {"type": "array", "items": {"type": "string"}},
                    "status": {"type": "string"},
                },
            },
        }
    },
}

CRITIC_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "issues", "rubric"],
    "properties": {
        "status": {"type": "string", "enum": ["pass", "revise", "fail"]},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["severity", "id", "message", "targetIds"],
                "properties": {
                    "severity": {"type": "string", "enum": ["critical", "warning"]},
                    "id": {"type": "string"},
                    "message": {"type": "string"},
                    "targetIds": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "rubric": {
            "type": "object",
            "additionalProperties": False,
            "required": ["strategyClarity", "targetEmpathy", "productConnection", "distinctiveness", "channelFit", "koreanCopyQuality", "brandFit", "actionability"],
            "properties": {key: {"type": "number"} for key in ["strategyClarity", "targetEmpathy", "productConnection", "distinctiveness", "channelFit", "koreanCopyQuality", "brandFit", "actionability"]},
        },
    },
}

COPY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["outputs"],
    "properties": {
        "outputs": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["deliverableId", "channelId", "purpose", "strategyBasis", "copyJson", "characterCount"],
                "properties": {
                    "deliverableId": {"type": "string"},
                    "channelId": {"type": "string"},
                    "purpose": {"type": "string"},
                    "strategyBasis": {"type": "string"},
                    "copyJson": {"type": "string"},
                    "characterCount": {"type": "integer"},
                },
            },
        }
    },
}


def generate_concepts(brief: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    baseline = build_concept_candidates(brief)
    provider = OpenAIPlanningProvider(run_dir)
    selected = retrieve_examples(brief, decision="selected")
    shortlist = retrieve_examples(brief, decision="shortlist")
    result = provider.execute(
        role="strategist",
        instructions=_strategist_instructions(),
        input_payload={"brief": brief, "selectedExamples": selected, "shortlistReferences": shortlist, "baselineShape": baseline},
        output_schema=CONCEPT_SCHEMA,
    )
    if result["status"] != "ok":
        if _should_use_local_provider(result):
            return {
                **baseline,
                "status": "review_pending",
                "providerExecution": [_local_provider_execution("strategist")],
                "criticReview": review_local_concepts(brief, baseline),
                "repairHistory": [],
            }
        return {**baseline, "status": "provider_unavailable", "providerExecution": [result["providerExecution"]], "criticReview": {}, "repairHistory": []}
    generated = {**baseline, **result["output"], "status": "review_pending", "providerExecution": [result["providerExecution"]]}
    critic = _critique(provider, brief, generated, "concepts")
    generated["criticReview"] = critic.get("output") or {}
    generated["providerExecution"].append(critic["providerExecution"])
    generated["repairHistory"] = []
    if generated["criticReview"].get("status") == "revise":
        repaired = provider.execute(
            role="strategist",
            instructions=_strategist_instructions() + " 비평에서 지적된 항목만 수정하고 나머지는 유지한다.",
            input_payload={"brief": brief, "draft": generated, "criticReview": generated["criticReview"]},
            output_schema=CONCEPT_SCHEMA,
        )
        generated["providerExecution"].append(repaired["providerExecution"])
        if repaired["status"] == "ok":
            _apply_targeted_concept_repair(generated, repaired["output"], generated["criticReview"].get("issues", []))
            generated["repairHistory"].append({"attempt": 1, "issues": generated["criticReview"].get("issues", []), "status": "repaired"})
            critic = _critique(provider, brief, generated, "concepts")
            generated["criticReview"] = critic.get("output") or {}
            generated["providerExecution"].append(critic["providerExecution"])
    return generated


def generate_copy(brief: dict[str, Any], concept: dict[str, Any], deliverables: list[dict[str, Any]], run_dir: Path) -> dict[str, Any]:
    baseline = build_copy_package(brief, concept, deliverables)
    provider = OpenAIPlanningProvider(run_dir)
    corrections = retrieve_corrections(
        industry=detect_industry(brief),
        brand_name=str(brief.get("brand", {}).get("name") or brief.get("brand_name") or ""),
        approved_only=True,
        limit=6,
    )
    result = provider.execute(
        role="copywriter",
        instructions=_copywriter_instructions(),
        input_payload={"brief": brief, "selectedConcept": concept, "deliverables": deliverables, "approvedCorrections": corrections, "baselineShape": baseline},
        output_schema=COPY_SCHEMA,
    )
    if result["status"] != "ok":
        if _should_use_local_provider(result):
            return {
                **baseline,
                "model": "deterministic_planning_engine",
                "status": "review_pending",
                "providerExecution": [_local_provider_execution("copywriter")],
                "criticReview": review_local_copy(brief, generated_concepts_stub(concept), baseline),
                "repairHistory": [],
            }
        return {**baseline, "status": "provider_unavailable", "providerExecution": [result["providerExecution"]], "criticReview": {}, "repairHistory": []}
    package = {**baseline, **result["output"], "model": result["providerExecution"]["model"], "status": "review_pending", "providerExecution": [result["providerExecution"]]}
    _parse_copy_json(package)
    critic = _critique(provider, brief, package, "copy")
    package["criticReview"] = critic.get("output") or {}
    package["providerExecution"].append(critic["providerExecution"])
    package["repairHistory"] = []
    if package["criticReview"].get("status") == "revise":
        repaired = provider.execute(
            role="copywriter",
            instructions=_copywriter_instructions() + " 비평에서 지적된 채널과 문장만 수정하고 유효한 카피는 유지한다.",
            input_payload={"brief": brief, "selectedConcept": concept, "deliverables": deliverables, "draft": package, "criticReview": package["criticReview"]},
            output_schema=COPY_SCHEMA,
        )
        package["providerExecution"].append(repaired["providerExecution"])
        if repaired["status"] == "ok":
            _apply_targeted_copy_repair(package, repaired["output"], package["criticReview"].get("issues", []))
            _parse_copy_json(package)
            package["repairHistory"].append({"attempt": 1, "issues": package["criticReview"].get("issues", []), "status": "repaired"})
            critic = _critique(provider, brief, package, "copy")
            package["criticReview"] = critic.get("output") or {}
            package["providerExecution"].append(critic["providerExecution"])
    return package


def _critique(provider: OpenAIPlanningProvider, brief: dict[str, Any], draft: dict[str, Any], target: str) -> dict[str, Any]:
    return provider.execute(
        role="critic",
        instructions="광고 기획 비평가로서 허위 주장, 전략 중복, 약한 제품 연결, 어색한 한국어, 채널 부적합을 엄격히 판정한다. 낮은 품질을 pass 처리하지 않는다.",
        input_payload={"target": target, "brief": brief, "draft": draft},
        output_schema=CRITIC_SCHEMA,
    )


def _should_use_local_provider(result: dict[str, Any]) -> bool:
    execution = result.get("providerExecution", {})
    return execution.get("status") == "missing_api_key"


def _local_provider_execution(role: str) -> dict[str, Any]:
    return {
        "provider": "local_deterministic",
        "model": "deterministic_planning_engine",
        "role": role,
        "status": "ok",
        "latencyMs": 0,
        "estimatedCostUsd": 0,
    }


def generated_concepts_stub(concept: dict[str, Any]) -> dict[str, Any]:
    return {"candidates": [concept], "status": "review_pending", "providerExecution": [_local_provider_execution("strategist")]}


def _strategist_instructions() -> str:
    return "한국 화장품 광고 전략가다. 검증된 사실만 사용한다. 서로 다른 3안은 타깃 인사이트, 핵심 약속, 설득 구조, CTA 중 최소 두 항목이 달라야 한다. 경쟁사 표현을 복제하지 않는다."


def _copywriter_instructions() -> str:
    return "한국 화장품 전문 카피라이터다. 선택된 전략을 채널별 완성 카피로 확장한다. 자연스러운 한국어를 쓰고 내부 메모, 추상 설명, 확인되지 않은 효능을 출력하지 않는다."


def _parse_copy_json(package: dict[str, Any]) -> None:
    import json
    for output in package.get("outputs", []):
        if "copyJson" in output:
            output["copy"] = json.loads(output.pop("copyJson"))
        if "copy" in output:
            output["characterCount"] = copy_character_count(output["copy"])


def _apply_targeted_concept_repair(draft: dict[str, Any], repaired: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    targets = {target for item in issues for target in item.get("targetIds", []) if target}
    repaired_by_id = {item.get("conceptId"): item for item in repaired.get("candidates", [])}
    if not targets:
        targets = set(repaired_by_id)
    draft["candidates"] = [
        repaired_by_id.get(item.get("conceptId"), item) if item.get("conceptId") in targets else item
        for item in draft.get("candidates", [])
    ]


def _apply_targeted_copy_repair(draft: dict[str, Any], repaired: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    targets = {target for item in issues for target in item.get("targetIds", []) if target}
    repaired_by_id = {item.get("channelId") or item.get("deliverableId"): item for item in repaired.get("outputs", [])}
    if not targets:
        targets = set(repaired_by_id)
    draft["outputs"] = [
        repaired_by_id.get(item.get("channelId") or item.get("deliverableId"), item)
        if (item.get("channelId") or item.get("deliverableId")) in targets else item
        for item in draft.get("outputs", [])
    ]
