#!/usr/bin/env python3
"""Run the event pipeline through AI-reviewed visual references and 03 handoff."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json
from scripts.verify_reference_pipeline import verify as verify_reference_pipeline
from scripts.workflow import approve_stage, load_status, mark_stage, run_reference_pipeline, setup_run


DEFAULT_REVIEW_HOST = "http://127.0.0.1:11434"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run event automation with Qwen-VL reference review.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--event", type=Path, help="Event folder containing event-input.json and brand-guide.json.")
    source.add_argument("--run", type=Path, help="Existing run folder.")
    parser.add_argument("--query-limit", type=int, default=1)
    parser.add_argument("--per-query-limit", type=int, default=3)
    parser.add_argument("--select-count", type=int, default=1)
    parser.add_argument("--review-limit", type=int, default=1)
    parser.add_argument("--review-model", default="qwen2.5vl:7b")
    parser.add_argument("--review-host", default=DEFAULT_REVIEW_HOST)
    parser.add_argument("--no-start-ai", action="store_true", help="Do not start Ollama automatically.")
    parser.add_argument("--headful", action="store_true", help="Show browser while collecting Pinterest references.")
    args = parser.parse_args()

    if not args.no_start_ai:
        ensure_ai_server(args.review_host, args.review_model)

    run_dir = args.run.resolve() if args.run else setup_run(args.event.resolve())
    run_dir = run_dir.resolve()
    run_to_reference_handoff(
        run_dir,
        query_limit=args.query_limit,
        per_query_limit=args.per_query_limit,
        select_count=args.select_count,
        review_limit=args.review_limit,
        review_model=args.review_model,
        review_host=args.review_host,
        headful=args.headful,
    )
    summary = write_summary(run_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def ensure_ai_server(host: str, model: str) -> None:
    if ai_health_ok(host, model):
        return
    ollama_exe = find_ollama_executable()
    if ollama_exe is None:
        raise SystemExit("Ollama executable not found in PATH or a known Windows install location.")

    env = os.environ.copy()
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [str(ollama_exe), "serve"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    for _ in range(12):
        time.sleep(2)
        if ai_health_ok(host, model):
            return
    raise SystemExit(f"Local AI server did not become ready: {host} / {model}")


def find_ollama_executable() -> Path | None:
    configured = os.getenv("OLLAMA_EXE")
    candidates = [
        Path(configured) if configured else None,
        Path(shutil.which("ollama")) if shutil.which("ollama") else None,
        Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
        Path(r"C:\tmp\ollama\ollama.exe"),
    ]
    return next((path for path in candidates if path and path.is_file()), None)


def ai_health_ok(host: str, model: str) -> bool:
    try:
        payload = requests.get(f"{host}/api/tags", timeout=5).json()
    except requests.RequestException:
        return False
    models = [item.get("name") for item in payload.get("models", [])]
    return model in models


def run_to_reference_handoff(
    run_dir: Path,
    *,
    query_limit: int,
    per_query_limit: int,
    select_count: int,
    review_limit: int,
    review_model: str,
    review_host: str,
    headful: bool,
) -> None:
    ensure_stage_approved(run_dir, "01_event_brief")
    ensure_stage_approved(run_dir, "02_content_planning")
    run_reference_pipeline(
        run_dir,
        include_search=True,
        include_queued=True,
        update_visual_candidates=True,
        query_limit=query_limit,
        per_query_limit=per_query_limit,
        select_count=select_count,
        headful=headful,
        reviewer="qwen",
        review_limit=review_limit,
        review_model=review_model,
        review_host=review_host,
    )
    ensure_qwen_accepted_selected_reference(run_dir)
    checks = verify_reference_pipeline(run_dir, require_03=True)
    failed = [item for item in checks if not item.get("ok")]
    if failed:
        write_json(run_dir / "references" / "reference-ai-verification.json", {"checks": checks})
        raise SystemExit("Reference AI handoff verification failed. See references/reference-ai-verification.json")
    write_json(run_dir / "references" / "reference-ai-verification.json", {"checks": checks})


def ensure_stage_approved(run_dir: Path, stage_id: str) -> None:
    status = load_status(run_dir)
    current = status.get("stage_status", {}).get(stage_id)
    if current == "approved":
        return
    if current == "locked":
        raise SystemExit(f"{stage_id} is locked; approve the upstream stage first.")
    if current not in {"review_pending", "done"}:
        mark_stage(run_dir, stage_id, mode="run")
    approve_stage(run_dir, stage_id, approver="reference-ai-auto", note="Auto-approved for reference AI handoff run.")


def ensure_qwen_accepted_selected_reference(run_dir: Path) -> None:
    manifest = read_json(run_dir / "references" / "reference-manifest.json", default={})
    selected_assets = [
        asset for asset in manifest.get("assets", [])
        if asset.get("status") == "selected"
    ]
    accepted = [
        asset for asset in selected_assets
        if asset.get("review_decision") in {"selected", "shortlist"}
    ]
    if accepted:
        return
    reviewed_path = run_dir / "references" / "qwen-reviewed-candidates.json"
    reviewed = read_json(reviewed_path, default={"reviewed": [], "errors": []})
    write_json(run_dir / "references" / "reference-ai-verification.json", {
        "checks": [
            {
                "name": "qwen_accepted_selected_reference",
                "ok": False,
                "detail": f"selected={len(selected_assets)} accepted=0 reviewed={len(reviewed.get('reviewed', []))}",
            }
        ],
        "reviewed_path": str(reviewed_path),
    })
    raise SystemExit(
        "Qwen did not accept any selected reference. Increase --query-limit, --per-query-limit, or --review-limit."
    )


def write_summary(run_dir: Path) -> dict[str, Any]:
    manifest = read_json(run_dir / "references" / "reference-manifest.json", default={})
    selected = read_json(run_dir / "references" / "selected-references.json", default={"selected": []})
    verification = read_json(run_dir / "references" / "reference-ai-verification.json", default={"checks": []})
    visual_plan = read_json(run_dir / "03_visual_candidates" / "visual-plan.json", default={})
    summary = {
        "run_dir": str(run_dir),
        "reference_manifest": str(run_dir / "references" / "reference-manifest.json"),
        "selected_references": str(run_dir / "references" / "selected-references.json"),
        "qwen_review": str(run_dir / "references" / "qwen-reviewed-candidates.json"),
        "visual_plan": str(run_dir / "03_visual_candidates" / "visual-plan.json"),
        "image_prompts": str(run_dir / "03_visual_candidates" / "image-prompts.json"),
        "candidate_manifest": str(run_dir / "03_visual_candidates" / "candidate-manifest.json"),
        "selected_count": len(selected.get("selected", [])),
        "selection_method": (
            manifest.get("selection", {}).get("selection_method")
            or manifest.get("auto_collection", {}).get("selection_method")
            or ""
        ),
        "reference_handoff_status": visual_plan.get("reference_manifest", {}).get("status", ""),
        "verification_ok": all(item.get("ok") for item in verification.get("checks", [])),
    }
    write_json(run_dir / "references" / "reference-ai-summary.json", summary)
    return summary


if __name__ == "__main__":
    raise SystemExit(main())
