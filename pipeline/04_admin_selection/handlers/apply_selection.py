"""Normalize manager review input into selected asset workflow artifacts."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json, write_json, write_text
from core.utils.schema_validation import validate_json


ROOT = Path(__file__).resolve().parents[3]
STAGE_ID = "04_admin_selection"


def run(
    run_dir: Path,
    mode: str = "run",
    outputs: list[str] | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    prompts_doc = read_json(run_dir / "03_visual_candidates" / "image-prompts.json")
    manifest = load_candidate_manifest(run_dir, prompts_doc)
    content_plan = read_json(run_dir / "02_content_planning" / "content-plan.json")
    review_input = load_review_input(run_dir, manifest)

    input_schema = read_json(ROOT / "pipeline" / STAGE_ID / "input.schema.json")
    output_schema = read_json(ROOT / "pipeline" / STAGE_ID / "output.schema.json")
    core_schema = read_json(ROOT / "core" / "schemas" / "selected-assets.schema.json")
    validate_json(
        {"candidate_manifest": manifest, "content_plan": content_plan},
        input_schema,
        data_label=f"{STAGE_ID} input",
        schema_label=f"pipeline/{STAGE_ID}/input.schema.json",
    )

    selected_assets = build_selected_assets(manifest, content_plan, review_input, prompts_doc)
    validate_json(selected_assets, output_schema, data_label=f"{STAGE_ID}/selected-assets.json", schema_label=f"pipeline/{STAGE_ID}/output.schema.json")
    validate_json(selected_assets, core_schema, data_label=f"{STAGE_ID}/selected-assets.json", schema_label="core/schemas/selected-assets.schema.json")

    stage_dir = run_dir / STAGE_ID
    selected_path = stage_dir / "selected-assets.json"
    notes_path = stage_dir / "selection-notes.md"
    write_json(selected_path, selected_assets)
    write_text(notes_path, build_notes(selected_assets))

    return {
        "stage_id": STAGE_ID,
        "status": "done",
        "outputs": [
            str(selected_path.relative_to(run_dir)),
            str(notes_path.relative_to(run_dir)),
        ],
        "notes": selected_assets.get("summary", {}).get("blockingIssues", []),
        "next_state": "qa_pending",
    }


def load_candidate_manifest(run_dir: Path, prompts_doc: dict[str, Any]) -> dict[str, Any]:
    manifest_path = run_dir / "03_visual_candidates" / "candidate-manifest.json"
    if manifest_path.exists():
        return read_json(manifest_path)

    groups: dict[str, dict[str, Any]] = {}
    candidates = []
    for prompt in prompts_doc.get("prompts", []):
        candidate_id = prompt.get("candidate_id") or prompt.get("prompt_id")
        group_id = prompt.get("regeneration_group") or f"{prompt.get('deliverable_id', 'deliverable')}__{prompt.get('visual_role', 'visual')}"
        preview_path = str(Path("03_visual_candidates") / "previews" / f"{candidate_id}.png")
        candidates.append({
            "candidate_id": candidate_id,
            "deliverable_id": prompt.get("deliverable_id", ""),
            "regeneration_group": group_id,
            "visual_role": prompt.get("visual_role", ""),
            "channel_id": prompt.get("channel_id", ""),
            "ratio": prompt.get("aspect_ratio") or prompt.get("ratio", ""),
            "preview_path": preview_path,
            "image_path": preview_path,
            "source_prompt_id": prompt.get("prompt_id", ""),
            "workflow_preset": prompt.get("workflow_preset", ""),
            "candidate_index": prompt.get("candidate_index"),
            "candidate_count": prompt.get("candidate_count"),
            "generation_status": "prompt_only",
            "generation_mode": "prompt_only",
            "status": "prompt_ready",
        })
        groups.setdefault(group_id, {
            "group_id": group_id,
            "stage_id": "03_visual_candidates",
            "scope": "deliverable_visual_need",
            "deliverable_id": prompt.get("deliverable_id", ""),
            "visual_role": prompt.get("visual_role", ""),
            "candidate_ids": [],
            "regenerate_command": f"python scripts/workflow.py --run <run-dir> --stage 04_visual_candidates --mode regenerate --group {group_id}",
        })["candidate_ids"].append(candidate_id)

    return {
        "event_id": prompts_doc.get("event_id") or read_json(run_dir / "run-status.json", default={}).get("event_id") or run_dir.name,
        "regeneration_groups": list(groups.values()),
        "candidates": candidates,
    }


def load_review_input(run_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    selected_assets = read_json(run_dir / STAGE_ID / "selected-assets.json", default={})
    if selected_assets.get("selectedAssets"):
        return {
            "reviewer": selected_assets.get("summary", {}).get("reviewer", "operator"),
            "reviewedAt": selected_assets.get("summary", {}).get("reviewedAt"),
            "decisions": selected_assets.get("selectedAssets", []),
        }
    if selected_assets.get("selections"):
        return {
            "reviewer": selected_assets.get("selection_summary", {}).get("reviewer", "operator"),
            "reviewedAt": selected_assets.get("selection_summary", {}).get("reviewed_at"),
            "decisions": selected_assets.get("selections", []),
        }

    review_input = read_json(run_dir / "selection.json", default={})
    if review_input.get("decisions"):
        return review_input

    if sys.stdin.isatty():
        return prompt_for_selections(manifest)

    raise SystemExit(
        "No selections found. Use the console image selection buttons first, "
        "or run this stage in an interactive terminal."
    )


def prompt_for_selections(manifest: dict[str, Any]) -> dict[str, Any]:
    decisions = []
    candidates_by_group: dict[str, list[dict[str, Any]]] = {}
    for candidate in manifest.get("candidates", []):
        candidates_by_group.setdefault(candidate.get("regeneration_group", ""), []).append(candidate)

    print("04_admin_selection: choose one candidate per visual group.")
    for group_id, candidates in candidates_by_group.items():
        print(f"\n[{group_id}]")
        for index, candidate in enumerate(candidates, start=1):
            print(
                f"  {index}. {candidate.get('candidate_id')} "
                f"({candidate.get('channel_id')}, {candidate.get('ratio')})"
            )
        raw = input("Select number, r=regenerate, h=hold [1]: ").strip().lower() or "1"
        if raw == "r":
            selected = candidates[0]
            decision = "regenerate"
        elif raw == "h":
            selected = candidates[0]
            decision = "hold"
        else:
            try:
                selected = candidates[max(0, min(int(raw) - 1, len(candidates) - 1))]
            except ValueError:
                selected = candidates[0]
            decision = "selected"
        decisions.append({
            "candidate_id": selected.get("candidate_id"),
            "decision": decision,
            "manager_note": input("Note (optional): ").strip(),
        })

    return {
        "reviewer": "cli",
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
        "decisions": decisions,
    }


def build_selected_assets(
    manifest: dict[str, Any],
    content_plan: dict[str, Any],
    review_input: dict[str, Any],
    prompts_doc: dict[str, Any],
) -> dict[str, Any]:
    candidates = {item["candidate_id"]: item for item in manifest.get("candidates", [])}
    prompts = {item.get("candidate_id"): item for item in prompts_doc.get("prompts", [])}
    groups = {item["group_id"]: item for item in manifest.get("regeneration_groups", [])}
    deliverables = {item["deliverable_id"]: item for item in content_plan.get("deliverables", [])}
    decisions = review_input.get("decisions", [])
    reviewer = review_input.get("reviewer", "operator")
    reviewed_at = review_input.get("reviewedAt") or datetime.now(timezone.utc).isoformat()

    selected_assets = []
    regeneration_requests = []
    blocking_issues = []

    for decision in decisions:
        candidate_id = decision.get("id") or decision.get("candidateId") or decision.get("candidate_id")
        candidate = candidates.get(candidate_id)
        if not candidate:
            blocking_issues.append(f"Unknown candidate id: {candidate_id}")
            continue
        deliverable_id = candidate["deliverable_id"]
        normalized_decision = _normalize_decision(decision.get("status") or decision.get("decision"))
        if normalized_decision == "selected" and candidate.get("generation_status") in {"failed", "error"}:
            blocking_issues.append(f"Cannot select failed candidate: {candidate_id}")
            normalized_decision = "hold"
        prompt = prompts.get(candidate_id, {})
        selection_entry = {
            "id": candidate_id,
            "channel": candidate.get("channel_id", ""),
            "type": candidate.get("visual_role", ""),
            "prompt": prompt.get("positive_prompt", ""),
            "status": normalized_decision,
            "sourceFile": (candidate.get("image_path") or candidate.get("preview_path", "")) if normalized_decision == "selected" else "",
            "deliverableId": deliverable_id,
            "promptId": prompt.get("prompt_id") or candidate.get("source_prompt_id", ""),
            "regenerationGroup": candidate.get("regeneration_group", ""),
            "note": decision.get("reason") or decision.get("manager_note") or decision.get("note") or "",
        }

        if normalized_decision == "regenerate":
            group_id = candidate.get("regeneration_group", "")
            group_meta = groups.get(group_id, {})
            regeneration_requests.append({
                "groupId": group_id,
                "reason": decision.get("request") or decision.get("reason") or "manager requested regeneration",
                "requestedBy": reviewer,
                "requestedAt": reviewed_at,
                "status": "requested",
                "stageId": "04_visual_candidates",
                "candidateIds": group_meta.get("candidate_ids", []),
                "workflowCommand": group_meta.get("regenerate_command", ""),
            })
        selected_assets.append(selection_entry)

    selected_deliverables = {
        item["deliverableId"]
        for item in selected_assets
        if item.get("status") == "selected"
    }
    unresolved_deliverables = [
        deliverable_id
        for deliverable_id in deliverables
        if deliverable_id not in selected_deliverables
    ]
    if unresolved_deliverables:
        blocking_issues.append(
            "No selected asset recorded for deliverables: " + ", ".join(sorted(unresolved_deliverables))
        )

    return {
        "eventId": manifest["event_id"],
        "selectedAssets": selected_assets,
        "regenerationRequests": regeneration_requests,
        "summary": {
            "reviewer": reviewer,
            "reviewedAt": reviewed_at,
            "decisionCount": len(selected_assets),
            "selectedCount": sum(1 for item in selected_assets if item.get("status") == "selected"),
            "regenerationRequestCount": len(regeneration_requests),
            "blockingIssues": blocking_issues,
        },
        "approvalStatus": "review_pending",
    }


def build_notes(selected_assets: dict[str, Any]) -> str:
    summary = selected_assets.get("summary", {})
    lines = [
        "# Admin Selection Notes",
        "",
        f"- Reviewer: {summary.get('reviewer', 'operator')}",
        f"- Decisions: {summary.get('decisionCount', 0)}",
        f"- Selected: {summary.get('selectedCount', 0)}",
        f"- Regeneration requests: {summary.get('regenerationRequestCount', 0)}",
        "",
        "## Decisions",
    ]
    for item in selected_assets.get("selectedAssets", []):
        lines.append(
            f"- {item.get('id')}: {item.get('status')} | {item.get('note', '')}"
        )
    lines.extend(["", "## Regeneration Requests"])
    for item in selected_assets.get("regenerationRequests", []):
        lines.append(f"- {item.get('groupId')}: {item.get('reason', '')}")
    if not selected_assets.get("regenerationRequests"):
        lines.append("- None")
    lines.extend(["", "## Blocking Issues"])
    issues = summary.get("blockingIssues", [])
    lines.extend([f"- {item}" for item in issues] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def _normalize_decision(value: str | None) -> str:
    value = str(value or "hold").strip().lower()
    return value if value in {"selected", "rejected", "regenerate", "hold"} else "hold"


def _append_note(existing: str, addition: str) -> str:
    return f"{existing} | {addition}" if existing else addition
