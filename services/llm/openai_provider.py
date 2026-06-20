"""OpenAI Responses API adapter for structured advertising-planning roles."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from core.utils.json_io import read_json, write_json
from core.utils.schema_validation import validate_json


Transport = Callable[[dict[str, Any], dict[str, str], int], dict[str, Any]]


class OpenAIPlanningProvider:
    def __init__(self, run_dir: Path | None = None, transport: Transport | None = None) -> None:
        self.run_dir = run_dir
        self.transport = transport or self._http_transport
        self.model = os.getenv("OPENAI_PLANNING_MODEL", "gpt-5.5").strip() or "gpt-5.5"
        self.max_calls = max(1, int(os.getenv("OPENAI_MAX_CALLS_PER_EVENT", "8")))
        self.timeout = max(1, int(os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "90")))

    def execute(
        self,
        *,
        role: str,
        instructions: str,
        input_payload: dict[str, Any],
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        started = time.perf_counter()
        budget = self._load_budget()
        if budget["callsUsed"] >= self.max_calls:
            return self._failure("call_budget_exhausted", role, started, budget)
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return self._failure("missing_api_key", role, started, budget)

        budget["callsUsed"] += 1
        budget["callsByRole"][role] = int(budget["callsByRole"].get(role, 0)) + 1
        self._save_budget(budget)
        request_payload = {
            "model": self.model,
            "instructions": instructions,
            "input": json.dumps(input_payload, ensure_ascii=False),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": f"ad_planning_{role}",
                    "strict": True,
                    "schema": output_schema,
                }
            },
        }
        try:
            response = self.transport(
                request_payload,
                {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                self.timeout,
            )
            output = _extract_structured_output(response)
            if not isinstance(output, dict):
                raise ValueError("Structured response did not contain a JSON object.")
            validate_json(output, output_schema, data_label=f"{role} response", schema_label="structured output schema")
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            return self._failure("provider_error", role, started, budget, str(exc))
        execution = {
            "status": "ok",
            "provider": "openai_responses",
            "model": response.get("model") or self.model,
            "role": role,
            "latencyMs": round((time.perf_counter() - started) * 1000, 2),
            "usage": response.get("usage", {}),
            "estimatedCostUsd": response.get("estimated_cost_usd") if response.get("estimated_cost_usd") is not None else _estimate_cost(response.get("usage", {})),
            "callsUsed": budget["callsUsed"],
            "maxCalls": self.max_calls,
        }
        return {"status": "ok", "output": output, "providerExecution": execution}

    def _failure(
        self,
        status: str,
        role: str,
        started: float,
        budget: dict[str, Any],
        error: str = "",
    ) -> dict[str, Any]:
        return {
            "status": "provider_unavailable",
            "output": None,
            "providerExecution": {
                "status": status,
                "provider": "openai_responses",
                "model": self.model,
                "role": role,
                "latencyMs": round((time.perf_counter() - started) * 1000, 2),
                "error": error,
                "callsUsed": budget["callsUsed"],
                "maxCalls": self.max_calls,
            },
        }

    def _load_budget(self) -> dict[str, Any]:
        default = {"callsUsed": 0, "callsByRole": {}, "maxCalls": self.max_calls}
        if not self.run_dir:
            return default
        return read_json(self.run_dir / "02_content_planning" / "provider-budget.json", default=default)

    def _save_budget(self, budget: dict[str, Any]) -> None:
        if self.run_dir:
            write_json(self.run_dir / "02_content_planning" / "provider-budget.json", budget)

    @staticmethod
    def _http_transport(payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
        req = urllib_request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))


def _extract_structured_output(response: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(response.get("output_parsed"), dict):
        return response["output_parsed"]
    if isinstance(response.get("output_text"), str):
        return json.loads(response["output_text"])
    for item in response.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                return json.loads(text)
    return None


def _estimate_cost(usage: dict[str, Any]) -> float:
    input_rate = float(os.getenv("OPENAI_INPUT_COST_PER_MILLION", "0") or 0)
    output_rate = float(os.getenv("OPENAI_OUTPUT_COST_PER_MILLION", "0") or 0)
    input_tokens = float(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    output_tokens = float(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    return round((input_tokens * input_rate + output_tokens * output_rate) / 1_000_000, 6)
