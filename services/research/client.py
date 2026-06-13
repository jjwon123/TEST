"""Search/research planning boundary for planning stages.

The current implementation intentionally stops at a deterministic research
plan. This lets stage handlers surface when outside context is needed and what
should be searched, while keeping the provider wiring isolated for the next
integration step.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError


@dataclass
class ResearchQuery:
    query: str
    purpose: str
    required: bool = False


class ResearchClient:
    def build_plan(
        self,
        *,
        stage_id: str,
        topic: str,
        triggers: list[str],
        queries: list[ResearchQuery],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "stage_id": stage_id,
            "topic": topic,
            "triggers": triggers,
            "queries": [
                {
                    "query": item.query,
                    "purpose": item.purpose,
                    "required": item.required,
                }
                for item in queries
            ],
            "context": context or {},
            "status": "planned" if queries else "not_needed",
        }

    def attach_evidence(
        self,
        plan: dict[str, Any],
        evidence_items: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        items = [item for item in (evidence_items or []) if isinstance(item, dict)]
        matched_queries = {
            str(item.get("query", "")).strip()
            for item in items
            if str(item.get("query", "")).strip()
        }
        attached = {
            **plan,
            "evidence": items,
            "evidence_count": len(items),
            "matched_query_count": len(matched_queries),
            "insights": [
                str(item.get("summary", "")).strip()
                for item in items
                if str(item.get("summary", "")).strip()
            ],
        }
        if items:
            attached["status"] = "evidence_attached"
        elif plan.get("queries"):
            attached["status"] = "planned"
        else:
            attached["status"] = "not_needed"
        return attached

    def execute_snapshot_search(
        self,
        plan: dict[str, Any],
        evidence_items: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        queries = {
            str(item.get("query", "")).strip()
            for item in plan.get("queries", [])
            if str(item.get("query", "")).strip()
        }
        selected = []
        for item in evidence_items or []:
            if not isinstance(item, dict):
                continue
            item_query = str(item.get("query", "")).strip()
            if item_query and (not queries or item_query in queries):
                selected.append(item)
        result = self.attach_evidence(plan, selected)
        result["search_mode"] = "snapshot_exact_query_match"
        result["candidate_evidence_count"] = len(evidence_items or [])
        return result

    def execute_search(
        self,
        plan: dict[str, Any],
        evidence_items: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        provider_url = os.getenv("RESEARCH_PROVIDER_URL", "").strip()
        if not provider_url:
            result = self.execute_snapshot_search(plan, evidence_items)
            result["provider_execution"] = {
                "mode": "snapshot",
                "status": "fallback_local_snapshot",
            }
            return result

        live = self._execute_http_provider(plan, provider_url)
        if live["status"] == "ok":
            result = self.attach_evidence(plan, live["items"])
            result["search_mode"] = "http_json_provider"
            result["candidate_evidence_count"] = len(live["items"])
            result["provider_execution"] = live["metadata"]
            return result

        result = self.execute_snapshot_search(plan, evidence_items)
        result["provider_execution"] = live["metadata"]
        result["provider_execution"]["fallback"] = "snapshot"
        return result

    def _execute_http_provider(self, plan: dict[str, Any], provider_url: str) -> dict[str, Any]:
        payload = json.dumps({"plan": plan}, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        token = os.getenv("RESEARCH_PROVIDER_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib_request.Request(provider_url, data=payload, headers=headers, method="POST")
        try:
            with urllib_request.urlopen(req, timeout=10) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            return {
                "status": "error",
                "items": [],
                "metadata": {
                    "mode": "http_json_provider",
                    "status": "provider_error",
                    "error": str(exc),
                },
            }
        items = body.get("items") or body.get("results") or []
        if not isinstance(items, list):
            items = []
        return {
            "status": "ok",
            "items": [item for item in items if isinstance(item, dict)],
            "metadata": {
                "mode": "http_json_provider",
                "status": "ok",
                "item_count": len(items),
            },
        }
