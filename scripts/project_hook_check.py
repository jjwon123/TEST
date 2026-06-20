#!/usr/bin/env python3
"""Run non-destructive project hook checks for the local automation pipeline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import write_json, write_text


CHECKS = [
    ["python", "-m", "py_compile", "scripts/console_server.py"],
    ["python", "-m", "py_compile", "scripts/create_reference_training_session.py"],
    ["python", "-m", "py_compile", "scripts/audit_visual_prompts.py"],
    ["python", "-m", "py_compile", "scripts/audit_planning_quality.py"],
    ["python", "-m", "py_compile", "scripts/compare_reference_sessions.py"],
    ["python", "-m", "py_compile", "scripts/summarize_reference_training_session.py"],
    ["python", "-m", "py_compile", "scripts/project_hook_check.py"],
    ["python", "-m", "py_compile", "scripts/audit_full_pipeline_health.py"],
    ["python", "-m", "py_compile", "scripts/audit_operational_readiness.py"],
    ["python", "-m", "py_compile", "scripts/audit_asset_integrity.py"],
    ["python", "-m", "py_compile", "scripts/report_meta_brand_metrics.py"],
    ["python", "-m", "py_compile", "scripts/audit_repeated_operations.py"],
    ["python", "-m", "py_compile", "scripts/run_recovery_rehearsal.py"],
    ["python", "-m", "py_compile", "services/ad_reference/registry_metrics.py"],
    ["python", "-m", "py_compile", "services/ad_reference/collection_strategy.py"],
    ["python", "-m", "py_compile", "services/ad_reference/meta_collector.py"],
    ["python", "-m", "py_compile", "scripts/collect_meta_brand_registry.py"],
    ["python", "-m", "py_compile", "services/ad_reference/source_mix_metrics.py"],
    ["python", "-m", "py_compile", "scripts/report_meta_source_mix.py"],
    ["python", "-m", "py_compile", "scripts/audit_console_ui_playwright.py"],
    ["python", "-m", "py_compile", "scripts/collect_meta_source_mix.py"],
    ["python", "-m", "py_compile", "scripts/run_project_tests.py"],
    ["python", "-m", "py_compile", "scripts/validate_openclip_effect.py"],
    ["node", "--check", "ui/console/app.js"],
    ["python", "scripts/run_project_tests.py"],
    ["python", "scripts/audit_operational_readiness.py"],
    ["python", "scripts/audit_asset_integrity.py"],
    ["python", "scripts/report_meta_brand_metrics.py"],
    ["python", "scripts/audit_repeated_operations.py"],
    ["python", "scripts/report_meta_source_mix.py"],
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, help="Optional run directory for planning/prompt audits.")
    args = parser.parse_args()
    results = [run_check(command) for command in CHECKS]
    if args.run:
        run_dir = args.run.resolve()
        if (run_dir / "01_event_brief" / "brief.json").exists() or (run_dir / "02_content_planning" / "content-plan.json").exists():
            results.append(run_check(["python", "scripts/audit_planning_quality.py", "--run", str(run_dir)]))
        if (run_dir / "03_visual_candidates" / "image-prompts.json").exists():
            results.append(run_check(["python", "scripts/audit_visual_prompts.py", "--run", str(run_dir)]))
    status = "pass" if all(item["returncode"] == 0 for item in results) else "fail"
    report = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "results": results,
    }
    output_dir = ROOT / ".tmp" / "hook-checks"
    write_json(output_dir / "latest-hook-check.json", report)
    write_text(output_dir / "latest-hook-check.md", render_markdown(report))
    print(f"HOOK {status} {output_dir / 'latest-hook-check.json'}")
    return 0 if status == "pass" else 1


def run_check(command: list[str]) -> dict[str, Any]:
    executable_command = [sys.executable, *command[1:]] if command[0] == "python" else command
    process = subprocess.run(
        executable_command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return {
        "command": command,
        "returncode": process.returncode,
        "stdout": (process.stdout or "")[-4000:],
        "stderr": (process.stderr or "")[-4000:],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Hook Check",
        "",
        f"- Status: `{report['status']}`",
        f"- Created: {report['createdAt']}",
        "",
        "## Results",
        "",
    ]
    for item in report["results"]:
        command = " ".join(item["command"])
        lines.append(f"- `{item['returncode']}` `{command}`")
        if item["stderr"]:
            lines.append(f"  - stderr: {item['stderr'].splitlines()[-1]}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
