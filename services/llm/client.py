"""LLM service boundary for agent reasoning stages.

The project still runs without a live provider by default, but stage handlers
should already depend on the same request contract that a real provider will
consume later. That keeps prompt work, schema design, and runtime integration
aligned instead of forcing another refactor when model execution is enabled.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError


@dataclass
class LLMRequest:
    stage_id: str
    prompt: str
    context: dict[str, Any]
    output_schema: str | None = None
    goals: list[str] | None = None
    guardrails: list[str] | None = None


class LLMClient:
    def build_request(self, request: LLMRequest) -> dict[str, Any]:
        return {
            "stage_id": request.stage_id,
            "prompt": request.prompt,
            "context": request.context,
            "output_schema": request.output_schema,
            "goals": request.goals or [],
            "guardrails": request.guardrails or [],
            "status": "dry_run",
        }

    def build_repair_request(
        self,
        *,
        stage_id: str,
        original_request: dict[str, Any],
        quality_flags: list[str],
        retry_index: int = 1,
    ) -> dict[str, Any]:
        return {
            "stage_id": stage_id,
            "repair_of": original_request,
            "quality_flags": quality_flags,
            "retry_index": retry_index,
            "repair_policy": [
                "Preserve valid approved facts and contracts.",
                "Resolve only the listed quality failures.",
                "Return output that still conforms to the target schema.",
            ],
            "status": "dry_run_repair",
        }

    def execute_local_repair(
        self,
        *,
        stage_id: str,
        draft: dict[str, Any],
        quality_flags: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        repaired = dict(draft)
        applied: list[str] = []

        if stage_id == "01_event_brief":
            repaired, applied = self._repair_brief(repaired, quality_flags, context)
        elif stage_id == "02_content_planning":
            repaired, applied = self._repair_content_plan(repaired, quality_flags)

        return {
            "status": "executed" if applied else "no_change",
            "applied_repairs": applied,
            "result": repaired,
        }

    def execute_structured_generation(
        self,
        *,
        request_envelope: dict[str, Any],
        draft: dict[str, Any],
    ) -> dict[str, Any]:
        started = time.perf_counter()
        provider_url = os.getenv("LLM_PROVIDER_URL", "").strip()
        if not provider_url:
            return {
                "status": "fallback_local_draft",
                "provider_execution": {
                    "mode": "local_draft",
                    "status": "provider_disabled",
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "estimated_cost_usd": 0.0,
                },
                "result": draft,
            }

        payload = json.dumps(
            {
                "request": request_envelope,
                "draft": draft,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        token = os.getenv("LLM_PROVIDER_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib_request.Request(provider_url, data=payload, headers=headers, method="POST")
        try:
            with urllib_request.urlopen(req, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            return {
                "status": "provider_error_fallback",
                "provider_execution": {
                    "mode": "http_json_provider",
                    "status": "provider_error",
                    "error": str(exc),
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                },
                "result": draft,
            }

        output = body.get("output") or body.get("result")
        if not isinstance(output, dict):
            return {
                "status": "invalid_provider_payload_fallback",
                "provider_execution": {
                    "mode": "http_json_provider",
                    "status": "invalid_payload",
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                },
                "result": draft,
            }
        return {
            "status": "provider_output_used",
            "provider_execution": {
                "mode": "http_json_provider",
                "status": "ok",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "model": body.get("model", ""),
                "usage": body.get("usage", {}),
                "estimated_cost_usd": body.get("estimated_cost_usd"),
            },
            "result": output,
        }

    def _repair_brief(
        self,
        brief: dict[str, Any],
        quality_flags: list[str],
        context: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        applied: list[str] = []
        event_input = context.get("event_input", {})
        references = event_input.get("references", [])
        visual_direction = brief.get("content_direction", {}).get("visual_direction", [])

        if (
            any("비주얼 가이드가 약해" in flag for flag in quality_flags)
            and not visual_direction
            and references
        ):
            inferred = [str(item).strip() for item in references[:3] if str(item).strip()]
            if inferred:
                brief = {
                    **brief,
                    "brand": {
                        **brief.get("brand", {}),
                        "visual_keywords": inferred,
                    },
                    "content_direction": {
                        **brief.get("content_direction", {}),
                        "visual_direction": inferred,
                    },
                }
                applied.append("derived_visual_direction_from_event_references")
        return brief, applied

    def _repair_content_plan(
        self,
        content_plan: dict[str, Any],
        quality_flags: list[str],
    ) -> tuple[dict[str, Any], list[str]]:
        applied: list[str] = []
        deliverables = [dict(item) for item in content_plan.get("deliverables", [])]
        messages = content_plan.get("brief", {}).get("core_messages", [])

        if (
            any("같은 copy intent" in flag for flag in quality_flags)
            and len(messages) >= 2
            and deliverables
        ):
            for index, item in enumerate(deliverables):
                item["copy_intent"] = messages[index % len(messages)]
            content_plan = {**content_plan, "deliverables": deliverables}
            applied.append("redistributed_copy_intent_across_deliverables")
        return content_plan, applied
