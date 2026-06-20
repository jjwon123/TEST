#!/usr/bin/env python3
"""Event content pipeline orchestrator scaffold.

This CLI is intentionally light on external integrations. Its job is to make
the repository's execution model concrete: create runs, track stage state,
record approvals, and prepare scoped regeneration without hiding decisions in
service-specific code.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
RUNS_DIR = ROOT / "runs"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json
from core.utils.module_loader import load_callable_from_path
from core.utils.schema_validation import SchemaValidationError, validate_json
from scripts.reference_pipeline import add_source as add_reference_source
from scripts.reference_pipeline import auto_collect_from_search as auto_collect_reference_search
from scripts.reference_pipeline import collect_sources as collect_reference_sources
from scripts.reference_pipeline import create_plan as create_reference_plan
from scripts.reference_pipeline import import_local_reference_source
from scripts.reference_pipeline import select_collected_references as select_collected_reference_assets


@dataclass(frozen=True)
class Stage:
    id: str
    title: str
    stage_type: str
    run_state: str
    pending_state: str
    approval_required: bool
    unlocks: str | None = None


@dataclass
class StageResult:
    stage_id: str
    status: str
    outputs: list[str]
    notes: list[str]
    next_state: str
    regeneration_groups: dict[str, list[str]]

    @classmethod
    def from_handler_output(cls, stage_id: str, output: Any, fallback_next_state: str) -> "StageResult":
        if isinstance(output, cls):
            return output
        if isinstance(output, dict):
            return cls(
                stage_id=output.get("stage_id", stage_id),
                status=output.get("status", "done"),
                outputs=list(output.get("outputs", [])),
                notes=list(output.get("notes", [])),
                next_state=output.get("next_state", fallback_next_state),
                regeneration_groups=dict(output.get("regeneration_groups", {})),
            )
        raise TypeError(f"Handler for {stage_id} returned unsupported result: {type(output).__name__}")


STAGES: list[Stage] = [
    Stage("01_event_brief", "Event brief", "agent_reasoning", "briefing", "brief_review", True, "02_content_planning"),
    Stage("02_content_planning", "Content planning", "agent_reasoning", "planning", "plan_review", True, "03_reference_research"),
    Stage("03_reference_research", "Reference research", "reference_research", "reference_research", "reference_ready", False, "04_visual_candidates"),
    Stage("04_visual_candidates", "Visual candidates", "agent_reasoning", "candidate_generating", "selection_pending", False, "05_admin_selection"),
    Stage("05_admin_selection", "Admin selection", "human_decision", "selection_pending", "qa_pending", False, "06_qa_packaging"),
    Stage("06_qa_packaging", "QA packaging", "agent_reasoning", "qa_pending", "review_pending", True, "07_asset_archive"),
    Stage("07_asset_archive", "Asset archive", "archive_index", "archived", "done", False, None),
]


RUN_STAGE_DIRS = {
    "01_event_brief": ["brief.json", "strategic-brief.json", "notes.md"],
    "02_content_planning": [
        "content-plan.json", "concept-candidates.json", "concept-review.json",
        "selected-concept.json", "copy-package.json", "copy-review.json",
        "planning-scorecard.json", "notes.md",
    ],
    "03_reference_research": ["reference-research.json", "notes.md"],
    "04_visual_candidates": ["visual-plan.json", "image-prompts.json", "candidate-manifest.json", "raw-generations", "previews"],
    "05_admin_selection": ["selected-assets.json", "selection-notes.md"],
    "06_qa_packaging": ["qa-report.json", "final-package-manifest.json"],
    "07_asset_archive": ["asset-archive.json", "reuse-notes.md"],
}


STAGE_HANDLERS: dict[str, Path] = {
    "01_event_brief": ROOT / "pipeline" / "01_event_brief" / "handlers" / "generate_brief.py",
    "02_content_planning": ROOT / "pipeline" / "02_content_planning" / "handlers" / "generate_content_plan.py",
    "03_reference_research": ROOT / "pipeline" / "03_reference_research" / "handlers" / "run_reference_research.py",
    "04_visual_candidates": ROOT / "pipeline" / "03_visual_candidates" / "handlers" / "generate_visual_candidates.py",
    "05_admin_selection": ROOT / "pipeline" / "04_admin_selection" / "handlers" / "apply_selection.py",
    "06_qa_packaging": ROOT / "pipeline" / "06_qa_packaging" / "handlers" / "run_qa_packaging.py",
    "07_asset_archive": ROOT / "pipeline" / "07_asset_archive" / "handlers" / "run_asset_archive.py",
}


STAGE_ALIASES = {
    "03_visual_candidates": "04_visual_candidates",
    "04_admin_selection": "05_admin_selection",
}


STAGE_STORAGE_DIRS = {
    "04_visual_candidates": "03_visual_candidates",
    "05_admin_selection": "04_admin_selection",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    value = str(value).strip().lower()
    value = re.sub(r"[^\w가-힣-]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "event"


def stage_by_id(stage_id: str) -> Stage:
    stage_id = STAGE_ALIASES.get(stage_id, stage_id)
    for stage in STAGES:
        if stage.id == stage_id:
            return stage
    valid = ", ".join(stage.id for stage in STAGES)
    raise SystemExit(f"Unknown stage '{stage_id}'. Valid stages: {valid}")


def event_id_from_dir(event_dir: Path) -> str:
    return slugify(event_dir.name)


def event_name(event_dir: Path) -> str:
    event_input = read_json(event_dir / "event-input.json", default={})
    return str(event_input.get("eventName") or event_input.get("name") or event_dir.name)


def new_run_id(event_dir: Path) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    return f"{timestamp}_{slugify(event_name(event_dir))}"


def initial_stage_status() -> dict[str, str]:
    status: dict[str, str] = {}
    for index, stage in enumerate(STAGES):
        status[stage.id] = "not_started" if index == 0 else "locked"
    return status


def create_run_status(run_id: str, event_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "event_id": event_id,
        "run_state": "created",
        "current_stage": "01_event_brief",
        "stage_status": initial_stage_status(),
        "regeneration_groups": {},
        "updated_at": now(),
        "history": [
            {
                "at": now(),
                "event": "run_created",
                "stage": None,
                "note": "Run workspace created from event source files.",
            }
        ],
    }


def append_history(status: dict[str, Any], event: str, stage_id: str | None, note: str) -> None:
    status.setdefault("history", []).append({
        "at": now(),
        "event": event,
        "stage": stage_id,
        "note": note,
    })
    status["updated_at"] = now()


def setup_run(event_dir: Path) -> Path:
    event_dir = event_dir.resolve()
    if not event_dir.exists():
        raise SystemExit(f"Event directory does not exist: {event_dir}")

    required = ["event-input.json", "brand-guide.json"]
    missing = [name for name in required if not (event_dir / name).exists()]
    if missing:
        raise SystemExit(f"Missing event source files: {', '.join(missing)}")
    validate_event_sources(event_dir)

    run_id = new_run_id(event_dir)
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    (run_dir / "logs").mkdir()
    shutil.copy2(event_dir / "event-input.json", run_dir / "event-input.json")
    shutil.copy2(event_dir / "brand-guide.json", run_dir / "brand-guide.json")
    if (event_dir / "research-evidence.json").exists():
        shutil.copy2(event_dir / "research-evidence.json", run_dir / "research-evidence.json")
    if (event_dir / "selection.json").exists():
        shutil.copy2(event_dir / "selection.json", run_dir / "selection.json")
    if (event_dir / "references").exists():
        shutil.copytree(event_dir / "references", run_dir / "references")
    if (event_dir / "notes.md").exists():
        shutil.copy2(event_dir / "notes.md", run_dir / "notes.md")

    for stage in STAGES:
        stage_dir = run_dir / stage.id
        stage_dir.mkdir()
        for item in RUN_STAGE_DIRS[stage.id]:
            if "." not in Path(item).name:
                (stage_dir / item).mkdir(exist_ok=True)

    write_json(run_dir / "run-status.json", create_run_status(run_id, event_id_from_dir(event_dir)))
    write_json(run_dir / "approvals.json", {"approvals": []})
    (run_dir / "logs" / "workflow.log").write_text(f"{now()} run_created {run_id}\n", encoding="utf-8")
    (run_dir / "logs" / "stage-errors.log").write_text("", encoding="utf-8")
    return run_dir


def validate_event_sources(event_dir: Path) -> None:
    sources = [
        ("event-input.json", ROOT / "core" / "schemas" / "event-input.schema.json"),
        ("brand-guide.json", ROOT / "core" / "schemas" / "brand-guide.schema.json"),
    ]
    for filename, schema_path in sources:
        validate_json(
            read_json(event_dir / filename),
            read_json(schema_path),
            data_label=str(event_dir / filename),
            schema_label=str(schema_path.relative_to(ROOT)),
        )


def load_status(run_dir: Path) -> dict[str, Any]:
    status = read_json(run_dir / "run-status.json")
    normalize_stage_status(status)
    return status


def save_status(run_dir: Path, status: dict[str, Any]) -> None:
    write_json(run_dir / "run-status.json", status)


def normalize_stage_status(status: dict[str, Any]) -> None:
    stage_status = status.setdefault("stage_status", {})
    for stage in STAGES:
        if stage.id not in stage_status:
            legacy_id = next((old for old, new in STAGE_ALIASES.items() if new == stage.id), None)
            if legacy_id and legacy_id in stage_status:
                stage_status[stage.id] = stage_status[legacy_id]
            else:
                stage_status[stage.id] = "locked"
    current = status.get("current_stage")
    if current in STAGE_ALIASES:
        status["current_stage"] = STAGE_ALIASES[current]


def write_stage_error(run_dir: Path, stage_id: str, message: str) -> None:
    error_log = run_dir / "logs" / "stage-errors.log"
    error_log.parent.mkdir(parents=True, exist_ok=True)
    with error_log.open("a", encoding="utf-8") as f:
        f.write(f"{now()} {stage_id} {message}\n")


def ensure_stage_unlocked(status: dict[str, Any], stage: Stage) -> None:
    state = status["stage_status"].get(stage.id)
    if state == "locked":
        raise SystemExit(f"{stage.id} is locked. Approve the upstream gate first.")


def invalidate_downstream_stages(status: dict[str, Any], stage_id: str) -> list[str]:
    stage_ids = [stage.id for stage in STAGES]
    stage_index = stage_ids.index(stage_id)
    invalidated: list[str] = []
    for downstream_id in stage_ids[stage_index + 1:]:
        previous = status["stage_status"].get(downstream_id)
        if previous not in {"locked", None}:
            invalidated.append(downstream_id)
        status["stage_status"][downstream_id] = "locked"
    if invalidated:
        status.setdefault("stale_stages", {}).update({
            downstream_id: {
                "invalidated_at": now(),
                "invalidated_by": stage_id,
            }
            for downstream_id in invalidated
        })
    return invalidated


def run_stage_handler(
    run_dir: Path,
    stage: Stage,
    mode: str,
    outputs: list[str] | None,
    group: str | None = None,
) -> StageResult | None:
    handler_path = STAGE_HANDLERS.get(stage.id)
    if not handler_path:
        return None
    handler = load_callable_from_path(handler_path, "run")
    result = handler(run_dir=run_dir, mode=mode, outputs=outputs, group=group)
    return StageResult.from_handler_output(stage.id, result, stage.pending_state)


def candidate_ids_for_group(run_dir: Path, stage_id: str, group: str) -> list[str]:
    storage_dir = STAGE_STORAGE_DIRS.get(stage_id, stage_id)
    manifest_path = run_dir / storage_dir / "candidate-manifest.json"
    if not manifest_path.exists():
        return []
    manifest = read_json(manifest_path)
    return [
        candidate["candidate_id"]
        for candidate in manifest.get("candidates", [])
        if candidate.get("regeneration_group") == group
    ]


def merge_regeneration_groups(
    status: dict[str, Any],
    stage_id: str,
    groups: dict[str, list[str]],
    mode: str,
    requested_group: str | None = None,
) -> None:
    stage_groups = status.setdefault("regeneration_groups", {}).setdefault(stage_id, {})
    for group_id, candidate_ids in groups.items():
        previous = stage_groups.get(group_id, {})
        if isinstance(previous, list):
            previous = {"candidate_ids": previous}
        stage_groups[group_id] = {
            "candidate_ids": candidate_ids,
            "last_materialized_at": now(),
            "last_requested_at": previous.get("last_requested_at"),
            "last_mode": mode if requested_group == group_id else previous.get("last_mode", mode),
        }


def mark_stage(
    run_dir: Path,
    stage_id: str,
    mode: str = "run",
    outputs: list[str] | None = None,
    group: str | None = None,
) -> None:
    stage = stage_by_id(stage_id)
    status = load_status(run_dir)
    ensure_stage_unlocked(status, stage)
    invalidated = invalidate_downstream_stages(status, stage.id)

    status["current_stage"] = stage.id
    status["run_state"] = stage.run_state
    status["stage_status"][stage.id] = "needs_regeneration" if mode == "regenerate" else "in_progress"
    append_history(status, mode, stage.id, f"{stage.title} marked {status['stage_status'][stage.id]}.")
    if invalidated:
        append_history(
            status,
            "downstream_invalidated",
            stage.id,
            f"Marked downstream stages stale: {', '.join(invalidated)}",
        )

    if outputs:
        append_history(status, "scoped_outputs", stage.id, f"Requested outputs: {', '.join(outputs)}")
    if group:
        group_candidates = candidate_ids_for_group(run_dir, stage.id, group)
        status.setdefault("regeneration_groups", {}).setdefault(stage.id, {})[group] = {
            "candidate_ids": group_candidates,
            "last_requested_at": now(),
            "mode": mode,
        }
        append_history(
            status,
            "scoped_group",
            stage.id,
            f"Requested regeneration group: {group}; candidates: {', '.join(group_candidates) if group_candidates else 'not yet materialized'}",
        )

    save_status(run_dir, status)

    try:
        result = run_stage_handler(run_dir, stage, mode, outputs, group=group)
    except SchemaValidationError as exc:
        record_stage_failure(run_dir, stage.id, exc)
        raise SystemExit(f"FAIL {stage.id}: {exc}") from exc
    except Exception as exc:
        record_stage_failure(run_dir, stage.id, exc)
        raise SystemExit(f"FAIL {stage.id}: {type(exc).__name__}: {exc}") from exc

    status = load_status(run_dir)
    if result:
        status["stage_status"][stage.id] = result.status
        status["run_state"] = result.next_state
        append_history(
            status,
            "stage_outputs",
            stage.id,
            f"Generated outputs: {', '.join(result.outputs) if result.outputs else 'none'}",
        )
        if result.notes:
            append_history(status, "stage_notes", stage.id, " | ".join(result.notes))
        if result.regeneration_groups:
            merge_regeneration_groups(status, stage.id, result.regeneration_groups, mode=mode, requested_group=group)
            append_history(status, "regeneration_groups_updated", stage.id, f"Tracked groups: {', '.join(result.regeneration_groups)}")
    else:
        status["stage_status"][stage.id] = "review_pending" if stage.approval_required else "done"
        status["run_state"] = stage.pending_state

    append_history(status, "stage_waiting", stage.id, f"{stage.title} reached {status['stage_status'][stage.id]}.")

    if not stage.approval_required and stage.unlocks:
        status["stage_status"][stage.unlocks] = "not_started"
        status["current_stage"] = stage.unlocks
        append_history(status, "stage_unlocked", stage.unlocks, f"Unlocked after {stage.id}.")

    save_status(run_dir, status)


def record_stage_failure(run_dir: Path, stage_id: str, exc: Exception) -> None:
    status = load_status(run_dir)
    message = f"{type(exc).__name__}: {exc}"
    status["stage_status"][stage_id] = "blocked"
    status["run_state"] = "failed"
    status.setdefault("stage_failures", {})[stage_id] = {
        "failed_at": now(),
        "error_type": type(exc).__name__,
        "message": str(exc),
    }
    append_history(status, "stage_failed", stage_id, message)
    save_status(run_dir, status)
    write_stage_error(run_dir, stage_id, message)


def load_regeneration_requests(run_dir: Path) -> list[dict[str, Any]]:
    selected_assets_path = run_dir / "04_admin_selection" / "selected-assets.json"
    if not selected_assets_path.exists():
        raise SystemExit(f"selected-assets.json not found: {selected_assets_path}")
    selected_assets = read_json(selected_assets_path)
    requests = selected_assets.get("regenerationRequests", selected_assets.get("regeneration_requests", []))
    if not isinstance(requests, list):
        raise SystemExit("selected-assets.json regenerationRequests must be an array")
    return requests


def process_regeneration_requests(run_dir: Path, auto_regenerate: bool = False) -> None:
    requests = load_regeneration_requests(run_dir)
    pending = [
        request
        for request in requests
        if request.get("status") in {"requested", "suggested", "queued"}
    ]

    if not pending:
        print("No pending regeneration requests.")
        return

    status = load_status(run_dir)
    for request in pending:
        group_id = request.get("groupId") or request.get("group_id")
        if not group_id:
            raise SystemExit("Regeneration request is missing group_id")
        command = f"python3 scripts/workflow.py --run {run_dir} --stage 04_visual_candidates --mode regenerate --group {group_id}"
        status.setdefault("regeneration_requests", []).append({
            "group_id": group_id,
            "reason": request.get("reason", ""),
            "requested_by": request.get("requestedBy") or request.get("requested_by", ""),
            "requested_at": request.get("requestedAt") or request.get("requested_at", ""),
            "source": "04_admin_selection/selected-assets.json",
            "status": "running" if auto_regenerate else "suggested",
            "workflow_command": command,
            "detected_at": now(),
        })
        append_history(
            status,
            "regeneration_request_detected",
            "04_admin_selection",
            f"{group_id}: {request.get('reason', '')}",
        )
        print(command)
        if auto_regenerate:
            save_status(run_dir, status)
            mark_stage(run_dir, "04_visual_candidates", mode="regenerate", group=group_id)
            status = load_status(run_dir)
            status.setdefault("regeneration_requests", []).append({
                "group_id": group_id,
                "status": "completed",
                "completed_at": now(),
                "source": "workflow_auto_regenerate",
            })

    save_status(run_dir, status)


def load_qa_report(run_dir: Path) -> dict[str, Any]:
    qa_report_path = run_dir / "06_qa_packaging" / "qa-report.json"
    if not qa_report_path.exists():
        raise SystemExit(f"qa-report.json not found: {qa_report_path}")
    return read_json(qa_report_path)


def parse_override_ids(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def process_qa_failures(run_dir: Path, override_ids: set[str] | None = None, dry_run: bool = False) -> None:
    override_ids = override_ids or set()
    qa_report = load_qa_report(run_dir)
    issues = qa_report.get("issues", [])
    failed_issues = [
        issue for issue in issues
        if issue.get("status") == "fail"
        or issue.get("qa_failed") is True
        or issue.get("severity") in {"error", "blocker"}
    ]

    if not failed_issues:
        print("No failed QA issues.")
        return

    status = load_status(run_dir)
    qa_actions = status.setdefault("qa_actions", [])
    for issue in failed_issues:
        issue_id = issue.get("issue_id")
        target_stage_id = issue.get("suggested_fix_stage")
        if not issue_id:
            raise SystemExit("QA issue is missing issue_id")
        if not target_stage_id:
            raise SystemExit(f"QA issue {issue_id} is missing suggested_fix_stage")
        stage = stage_by_id(target_stage_id)

        overridden = "all" in override_ids or issue_id in override_ids
        action = {
            "issue_id": issue_id,
            "affected_item_id": issue.get("affected_item_id"),
            "suggested_fix_stage": target_stage_id,
            "source_trace": issue.get("source_trace", {}),
            "status": "overridden" if overridden else ("suggested" if dry_run else "needs_regeneration"),
            "processed_at": now(),
        }
        qa_actions.append(action)

        if overridden:
            append_history(status, "qa_failure_overridden", target_stage_id, f"{issue_id}: human override")
            print(f"OVERRIDE {issue_id}: {target_stage_id}")
            continue

        print(f"QA_FAIL {issue_id}: {target_stage_id} <- {issue.get('affected_item_id', '')}")
        if not dry_run:
            status["stage_status"][stage.id] = "needs_regeneration"
            status["current_stage"] = stage.id
            status["run_state"] = stage.run_state
            append_history(
                status,
                "qa_failure_routed",
                stage.id,
                f"{issue_id}: {issue.get('message', '')}",
            )

    save_status(run_dir, status)


def plan_references(run_dir: Path, force: bool = False) -> None:
    plan = create_reference_plan(run_dir, force=force)
    status = load_status(run_dir)
    append_history(
        status,
        "reference_plan_ready",
        None,
        f"Prepared {len(plan.get('search_queries', []))} reference search queries.",
    )
    save_status(run_dir, status)
    print(f"OK reference plan {run_dir / 'references' / 'reference-collection-plan.json'}")


def queue_reference_source(
    run_dir: Path,
    url: str,
    label: str = "",
    limit: int = 30,
    allow_page_fallback: bool = False,
) -> None:
    source = add_reference_source(
        run_dir,
        url,
        label=label,
        limit=limit,
        allow_page_fallback=allow_page_fallback,
    )
    status = load_status(run_dir)
    append_history(
        status,
        "reference_source_queued",
        None,
        f"{source['source_id']}: {source['url']}",
    )
    save_status(run_dir, status)
    print(f"OK queued reference source {source['source_id']}")


def import_local_reference(run_dir: Path, source_dir: Path, label: str = "", limit: int = 30) -> None:
    source = import_local_reference_source(run_dir, source_dir, label=label, limit=limit)
    status = load_status(run_dir)
    append_history(
        status,
        "reference_local_source_imported",
        None,
        f"{source['source_id']}: {source.get('downloaded_count', 0)} files from {source_dir}",
    )
    save_status(run_dir, status)
    print(f"OK imported local reference source {source['source_id']}")


def collect_references(run_dir: Path, use_cookies: bool = True, only_source: str | None = None) -> None:
    manifest = collect_reference_sources(run_dir, use_cookies=use_cookies, only_source=only_source)
    status = load_status(run_dir)
    append_history(
        status,
        "references_collected",
        None,
        f"Collected {manifest.get('asset_count', 0)} reference assets across {len(manifest.get('sources', {}))} sources.",
    )
    save_status(run_dir, status)
    print(f"OK references collected {run_dir / 'references' / 'reference-manifest.json'}")


def select_references(
    run_dir: Path,
    *,
    select_count: int = 30,
    only_source: str | None = None,
    reviewer: str = "heuristic",
    review_limit: int | None = None,
    review_model: str = "qwen2.5vl:7b",
    review_host: str = "http://127.0.0.1:11434",
) -> None:
    manifest = select_collected_reference_assets(
        run_dir,
        select_count=select_count,
        only_source=only_source,
        reviewer=reviewer,
        review_limit=review_limit,
        review_model=review_model,
        review_host=review_host,
    )
    selection = manifest.get("selection", {})
    status = load_status(run_dir)
    append_history(
        status,
        "references_selected",
        None,
        f"Ranked {selection.get('ranked_count', 0)} collected reference candidates and selected {selection.get('selected_count', 0)} assets.",
    )
    save_status(run_dir, status)
    print(f"OK references selected {run_dir / 'references' / 'selected-references.json'}")


def auto_search_references(
    run_dir: Path,
    *,
    query_limit: int = 12,
    per_query_limit: int = 24,
    select_count: int = 30,
    headful: bool = False,
    reviewer: str = "heuristic",
    review_limit: int | None = None,
    review_model: str = "qwen2.5vl:7b",
    review_host: str = "http://127.0.0.1:11434",
) -> None:
    manifest = auto_collect_reference_search(
        run_dir,
        query_limit=query_limit,
        per_query_limit=per_query_limit,
        select_count=select_count,
        headful=headful,
        reviewer=reviewer,
        review_limit=review_limit,
        review_model=review_model,
        review_host=review_host,
    )
    auto = manifest.get("auto_collection", {})
    status = load_status(run_dir)
    append_history(
        status,
        "reference_auto_search_completed",
        None,
        f"Auto searched {auto.get('query_count', 0)} queries, ranked {auto.get('ranked_count', 0)} candidates, selected {auto.get('selected_count', 0)} assets.",
    )
    save_status(run_dir, status)
    print(f"OK reference auto-search {run_dir / 'references' / 'selected-references.json'}")


def run_reference_pipeline(
    run_dir: Path,
    *,
    include_search: bool = True,
    include_queued: bool = True,
    update_visual_candidates: bool = False,
    only_source: str | None = None,
    query_limit: int = 12,
    per_query_limit: int = 24,
    select_count: int = 30,
    headful: bool = False,
    use_cookies: bool = True,
    reviewer: str = "heuristic",
    review_limit: int | None = None,
    review_model: str = "qwen2.5vl:7b",
    review_host: str = "http://127.0.0.1:11434",
) -> None:
    plan = create_reference_plan(run_dir)
    board_source_ids = [source.get("source_id") for source in plan.get("source_boards", []) if source.get("source_id")]
    if only_source:
        board_source_ids = [only_source]
    status = load_status(run_dir)
    append_history(
        status,
        "reference_pipeline_started",
        None,
        f"include_search={include_search}; include_queued={include_queued}; update_03={update_visual_candidates}",
    )
    save_status(run_dir, status)

    manifest: dict[str, Any] | None = None
    if include_search:
        manifest = auto_collect_reference_search(
            run_dir,
            query_limit=query_limit,
            per_query_limit=per_query_limit,
            select_count=select_count,
            headful=headful,
            reviewer=reviewer,
            review_limit=review_limit,
            review_model=review_model,
            review_host=review_host,
        )

    queued_sources = [
        source for source in plan.get("source_boards", [])
        if source.get("status") in {"queued", "failed"} and (not only_source or source.get("source_id") == only_source)
    ]
    if include_queued and queued_sources:
        collect_reference_sources(run_dir, use_cookies=use_cookies, only_source=only_source)
        manifest = select_collected_reference_assets(
            run_dir,
            select_count=select_count,
            only_sources=board_source_ids if (only_source or not include_search) else None,
            reviewer=reviewer,
            review_limit=review_limit,
            review_model=review_model,
            review_host=review_host,
        )
    elif include_queued:
        status = load_status(run_dir)
        append_history(status, "reference_pipeline_no_queued_sources", None, "No queued board/pin sources to collect.")
        save_status(run_dir, status)

    if manifest is None:
        manifest = select_collected_reference_assets(
            run_dir,
            select_count=select_count,
            only_sources=board_source_ids if (only_source or not include_search) else None,
            reviewer=reviewer,
            review_limit=review_limit,
            review_model=review_model,
            review_host=review_host,
        )

    operation_selected_count = _reference_operation_selected_count(
        manifest,
        include_search=include_search,
        include_queued=include_queued,
        only_source=only_source,
    )
    if operation_selected_count == 0:
        status = load_status(run_dir)
        append_history(
            status,
        "reference_pipeline_failed",
        None,
        "No selected reference assets were produced; skipping 04_visual_candidates update.",
        )
        save_status(run_dir, status)
        raise SystemExit("FAIL reference pipeline: no selected reference assets were produced.")

    if update_visual_candidates:
        status = load_status(run_dir)
        stage_state = status.get("stage_status", {}).get("04_visual_candidates")
        if stage_state == "locked":
            append_history(
                status,
                "reference_pipeline_skipped_04",
                "04_visual_candidates",
                "04_visual_candidates is locked; approve upstream stages before updating visual candidates.",
            )
            save_status(run_dir, status)
        else:
            save_status(run_dir, status)
            mark_stage(run_dir, "04_visual_candidates", mode="run")

    status = load_status(run_dir)
    selected_count = len([asset for asset in manifest.get("assets", []) if asset.get("status") == "selected"])
    append_history(
        status,
        "reference_pipeline_completed",
        None,
        f"Selected {selected_count} reference assets; manifest={run_dir / 'references' / 'reference-manifest.json'}",
    )
    save_status(run_dir, status)
    print(f"OK reference pipeline {run_dir / 'references' / 'reference-manifest.json'}")


def _reference_operation_selected_count(
    manifest: dict[str, Any],
    *,
    include_search: bool,
    include_queued: bool,
    only_source: str | None,
) -> int:
    if only_source or (include_queued and not include_search):
        return int(manifest.get("selection", {}).get("selected_count") or 0)
    if include_search:
        return int(manifest.get("auto_collection", {}).get("selected_count") or 0)
    return len([asset for asset in manifest.get("assets", []) if asset.get("status") == "selected"])


def approve_stage(run_dir: Path, stage_id: str, approver: str = "operator", note: str = "") -> None:
    stage = stage_by_id(stage_id)
    status = load_status(run_dir)
    approvals = read_json(run_dir / "approvals.json", default={"approvals": []})
    if stage.id == "02_content_planning":
        concept_review = read_json(run_dir / stage.id / "concept-review.json", default={})
        copy_review = read_json(run_dir / stage.id / "copy-review.json", default={})
        scorecard = read_json(run_dir / stage.id / "planning-scorecard.json", default={})
        if concept_review.get("status") != "approved" or not concept_review.get("selectedConceptId"):
            raise SystemExit("Cannot approve 02_content_planning before a campaign concept is selected and approved.")
        if copy_review.get("status") != "approved" or copy_review.get("approved") is not True:
            raise SystemExit("Cannot approve 02_content_planning before the final copy package is approved.")
        if int(scorecard.get("criticalErrorCount") or 0) > 0:
            raise SystemExit("Cannot approve 02_content_planning while critical planning QA errors remain.")
        if scorecard.get("status") != "pass" or scorecard.get("issues"):
            raise SystemExit("Cannot approve 02_content_planning while planning quality warnings remain.")
    if stage.id == "06_qa_packaging":
        qa_report = load_qa_report(run_dir)
        qa_status = str(qa_report.get("summary", {}).get("status") or "").lower()
        unresolved = [
            issue.get("issue_id")
            for issue in qa_report.get("issues", [])
            if issue.get("status") == "fail"
            or issue.get("qa_failed") is True
            or issue.get("severity") in {"error", "blocker"}
        ]
        overridden = {
            item.get("issue_id")
            for item in status.get("qa_actions", [])
            if item.get("status") == "overridden"
        }
        unresolved = [issue_id for issue_id in unresolved if issue_id not in overridden]
        if unresolved:
            raise SystemExit(
                "Cannot approve failed QA. Process or override issues first: "
                + ", ".join(str(item) for item in unresolved)
            )
        if qa_status in {"warn", "warning", "pass_with_warnings"} and not note.strip():
            raise SystemExit("Cannot approve QA warnings without an approval note.")

    status["stage_status"][stage.id] = "approved"
    status["current_stage"] = stage.unlocks or stage.id
    append_history(status, "approved", stage.id, note or f"{stage.title} approved.")

    if stage.unlocks:
        status["stage_status"][stage.unlocks] = "not_started"
        append_history(status, "stage_unlocked", stage.unlocks, f"Unlocked by approval of {stage.id}.")
    elif stage.id == "07_asset_archive":
        status["run_state"] = "archived"

    approvals.setdefault("approvals", []).append({
        "stage_id": stage.id,
        "status": "approved",
        "approver": approver,
        "approved_at": now(),
        "note": note,
    })

    save_status(run_dir, status)
    write_json(run_dir / "approvals.json", approvals)


def list_stages() -> None:
    for stage in STAGES:
        gate = "approval" if stage.approval_required else "auto-handoff"
        print(f"{stage.id} | {stage.stage_type} | {gate} | {stage.title}")


def parse_outputs(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Event content pipeline orchestrator")
    parser.add_argument("--setup", action="store_true", help="Create a run workspace")
    parser.add_argument("--event", type=Path, help="Event folder containing event-input.json and brand-guide.json")
    parser.add_argument("--list-stages", action="store_true", help="List registered stages")
    parser.add_argument("--run", type=Path, help="Run directory")
    parser.add_argument("--stage", help="Mark a stage as executed up to its next gate")
    parser.add_argument("--mode", choices=["run", "regenerate"], default="run", help="Stage execution mode")
    parser.add_argument("--outputs", help="Comma-separated output names for scoped regeneration")
    parser.add_argument("--group", help="Regeneration group id for scoped candidate regeneration")
    parser.add_argument("--process-regeneration-requests", action="store_true", help="Read 04_admin_selection/selected-assets.json and suggest or run requested regeneration groups")
    parser.add_argument("--auto-regenerate", action="store_true", help="Execute pending regeneration requests instead of only printing commands")
    parser.add_argument("--process-qa-failures", action="store_true", help="Read 06_qa_packaging/qa-report.json and route failed issues to suggested fix stages")
    parser.add_argument("--qa-override", help="Comma-separated QA issue ids to override, or 'all'")
    parser.add_argument("--dry-run", action="store_true", help="Show workflow actions without changing stage status")
    parser.add_argument("--plan-references", action="store_true", help="Create run-scoped Pinterest reference search queries")
    parser.add_argument("--force-reference-plan", action="store_true", help="Overwrite an existing reference collection plan")
    parser.add_argument("--add-reference-source", help="Queue a Pinterest board, section, search, or pin URL for reference collection")
    parser.add_argument("--import-local-reference-source", type=Path, help="Import an existing local folder of reference images as a source")
    parser.add_argument("--reference-label", default="", help="Optional label for the queued reference source")
    parser.add_argument("--reference-limit", type=int, default=30, help="Maximum items to download from a queued reference source")
    parser.add_argument("--reference-allow-page-fallback", action="store_true", help="Allow visible page-image fallback for queued Pinterest sources when board feed/API extraction fails")
    parser.add_argument("--collect-references", action="store_true", help="Download queued reference sources into runs/{run}/references")
    parser.add_argument("--select-collected-references", action="store_true", help="Rank downloaded reference sources and save selected assets")
    parser.add_argument("--reference-source", help="Collect only one queued source_id")
    parser.add_argument("--no-reference-cookies", action="store_true", help="Do not pass Chrome cookies to gallery-dl")
    parser.add_argument("--auto-search-references", action="store_true", help="Search Pinterest query pages, download candidates, rank them, and save selected references")
    parser.add_argument("--run-reference-pipeline", action="store_true", help="Run the full reference pipeline: plan, search, queued source collection, selection, and optional 03 update")
    parser.add_argument("--reference-no-search", action="store_true", help="Skip Pinterest search pages in --run-reference-pipeline")
    parser.add_argument("--reference-no-queued", action="store_true", help="Skip queued board/pin sources in --run-reference-pipeline")
    parser.add_argument("--reference-update-03", action="store_true", help="After selecting references, regenerate 04_visual_candidates when it is unlocked")
    parser.add_argument("--reference-query-limit", type=int, default=12, help="Maximum generated search queries to process")
    parser.add_argument("--reference-per-query-limit", type=int, default=24, help="Maximum image candidates to download per query")
    parser.add_argument("--reference-select-count", type=int, default=30, help="Number of ranked reference images to save as selected")
    parser.add_argument("--reference-headful", action="store_true", help="Show browser while auto-searching references")
    parser.add_argument("--reference-reviewer", choices=["heuristic", "qwen"], default="heuristic", help="Image reviewer used after download ranking")
    parser.add_argument("--reference-review-limit", type=int, help="Maximum ranked candidates to send to the image reviewer")
    parser.add_argument("--reference-review-model", default="qwen2.5vl:7b", help="Ollama vision model for Qwen reference review")
    parser.add_argument("--reference-review-host", default="http://127.0.0.1:11434", help="Ollama host for Qwen reference review")
    parser.add_argument("--approve", help="Approve a stage and unlock the next stage")
    parser.add_argument("--approver", default="operator", help="Approval actor label")
    parser.add_argument("--note", default="", help="Approval or execution note")
    args = parser.parse_args()

    if args.list_stages:
        list_stages()
        return

    if args.setup:
        if not args.event:
            raise SystemExit("--setup requires --event")
        run_dir = setup_run(args.event)
        print(f"OK setup {run_dir.relative_to(ROOT)}")
        return

    if args.approve:
        if not args.run:
            raise SystemExit("--approve requires --run")
        approve_stage(args.run.resolve(), args.approve, approver=args.approver, note=args.note)
        print(f"OK approved {args.approve}")
        return

    if args.process_regeneration_requests:
        if not args.run:
            raise SystemExit("--process-regeneration-requests requires --run")
        process_regeneration_requests(args.run.resolve(), auto_regenerate=args.auto_regenerate)
        return

    if args.process_qa_failures:
        if not args.run:
            raise SystemExit("--process-qa-failures requires --run")
        process_qa_failures(
            args.run.resolve(),
            override_ids=parse_override_ids(args.qa_override),
            dry_run=args.dry_run,
        )
        return

    if args.plan_references:
        if not args.run:
            raise SystemExit("--plan-references requires --run")
        plan_references(args.run.resolve(), force=args.force_reference_plan)
        return

    if args.add_reference_source:
        if not args.run:
            raise SystemExit("--add-reference-source requires --run")
        queue_reference_source(
            args.run.resolve(),
            args.add_reference_source,
            label=args.reference_label,
            limit=args.reference_limit,
            allow_page_fallback=args.reference_allow_page_fallback,
        )
        return

    if args.import_local_reference_source:
        if not args.run:
            raise SystemExit("--import-local-reference-source requires --run")
        import_local_reference(
            args.run.resolve(),
            args.import_local_reference_source,
            label=args.reference_label,
            limit=args.reference_limit,
        )
        return

    if args.collect_references:
        if not args.run:
            raise SystemExit("--collect-references requires --run")
        collect_references(
            args.run.resolve(),
            use_cookies=not args.no_reference_cookies,
            only_source=args.reference_source,
        )
        return

    if args.select_collected_references:
        if not args.run:
            raise SystemExit("--select-collected-references requires --run")
        select_references(
            args.run.resolve(),
            select_count=args.reference_select_count,
            only_source=args.reference_source,
            reviewer=args.reference_reviewer,
            review_limit=args.reference_review_limit,
            review_model=args.reference_review_model,
            review_host=args.reference_review_host,
        )
        return

    if args.auto_search_references:
        if not args.run:
            raise SystemExit("--auto-search-references requires --run")
        auto_search_references(
            args.run.resolve(),
            query_limit=args.reference_query_limit,
            per_query_limit=args.reference_per_query_limit,
            select_count=args.reference_select_count,
            headful=args.reference_headful,
            reviewer=args.reference_reviewer,
            review_limit=args.reference_review_limit,
            review_model=args.reference_review_model,
            review_host=args.reference_review_host,
        )
        return

    if args.run_reference_pipeline:
        if not args.run:
            raise SystemExit("--run-reference-pipeline requires --run")
        run_reference_pipeline(
            args.run.resolve(),
            include_search=not args.reference_no_search,
            include_queued=not args.reference_no_queued,
            update_visual_candidates=args.reference_update_03,
            only_source=args.reference_source,
            query_limit=args.reference_query_limit,
            per_query_limit=args.reference_per_query_limit,
            select_count=args.reference_select_count,
            headful=args.reference_headful,
            use_cookies=not args.no_reference_cookies,
            reviewer=args.reference_reviewer,
            review_limit=args.reference_review_limit,
            review_model=args.reference_review_model,
            review_host=args.reference_review_host,
        )
        return

    if args.stage:
        if not args.run:
            raise SystemExit("--stage requires --run")
        mark_stage(args.run.resolve(), args.stage, mode=args.mode, outputs=parse_outputs(args.outputs), group=args.group)
        print(f"OK {args.mode} {args.stage}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
