#!/usr/bin/env python3
"""Audit archive manifests, approved files, and global/event indexes for consistency."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json, write_text


def main() -> int:
    report = audit()
    output_dir = ROOT / ".tmp" / "asset-integrity"
    write_json(output_dir / "latest-asset-integrity.json", report)
    write_text(output_dir / "latest-asset-integrity.md", render_markdown(report))
    print(f"ASSET_INTEGRITY {report['status']} {output_dir / 'latest-asset-integrity.json'}")
    return 0 if report["status"] == "pass" else 1


def audit(
    *,
    assets_root: Path | None = None,
    runs_root: Path | None = None,
) -> dict[str, Any]:
    assets_root = assets_root or ROOT / "assets"
    runs_root = runs_root or ROOT / "runs"
    findings: list[dict[str, Any]] = []
    global_index = read_json(assets_root / "indexes" / "global-index.json", default={"assets": []})
    global_assets = global_index.get("assets", [])
    global_by_id = {str(item.get("asset_id") or ""): item for item in global_assets if item.get("asset_id")}
    duplicate_ids = [asset_id for asset_id, count in Counter(item.get("asset_id") for item in global_assets).items() if asset_id and count > 1]
    if duplicate_ids:
        add(findings, "P0", "duplicate_global_asset_ids", "Global index contains duplicate asset IDs.", duplicate_ids)

    event_indexes: dict[str, dict[str, Any]] = {}
    for path in (assets_root / "indexes" / "by-event").glob("*.json"):
        payload = read_json(path, default={})
        event_indexes[str(payload.get("event_id") or path.stem)] = payload

    for asset_id, record in global_by_id.items():
        approved = assets_root / str(record.get("archive_path_approved") or "")
        if not record.get("archive_path_approved") or not approved.is_file():
            add(findings, "P0", "missing_approved_file", f"Approved file is missing for {asset_id}.", str(approved))
        if record.get("reuse_status") == "reusable":
            reusable = assets_root / str(record.get("archive_path_reusable") or "")
            if not record.get("archive_path_reusable") or not reusable.is_file():
                add(findings, "P0", "missing_reusable_file", f"Reusable file is missing for {asset_id}.", str(reusable))
        event_id = str(record.get("event_id") or "")
        event_assets = {
            str(item.get("asset_id") or ""): item
            for item in event_indexes.get(event_id, {}).get("assets", [])
        }
        if asset_id not in event_assets:
            add(findings, "P1", "missing_event_index_record", f"{asset_id} is absent from its event index.", event_id)

    archive_assets = 0
    for archive_path in runs_root.glob("*/07_asset_archive/asset-archive.json"):
        archive = read_json(archive_path, default={})
        for record in archive.get("assets", []):
            archive_assets += 1
            asset_id = str(record.get("asset_id") or "")
            if asset_id and asset_id not in global_by_id:
                add(findings, "P1", "archive_missing_global_record", f"{asset_id} is absent from the global index.", str(archive_path))

    severity_counts = Counter(item["severity"] for item in findings)
    status = "fail" if severity_counts["P0"] else "warning" if findings else "pass"
    return {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "summary": {
            "globalAssets": len(global_assets),
            "eventIndexes": len(event_indexes),
            "archiveAssets": archive_assets,
            "severityCounts": dict(severity_counts),
        },
        "findings": findings,
    }


def add(findings: list[dict[str, Any]], severity: str, code: str, message: str, evidence: Any = None) -> None:
    findings.append({"severity": severity, "code": code, "message": message, "evidence": evidence})


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Asset Integrity",
        "",
        f"- Status: `{report['status']}`",
        f"- Global assets: {summary['globalAssets']}",
        f"- Archive assets: {summary['archiveAssets']}",
        f"- Event indexes: {summary['eventIndexes']}",
        "",
        "## Findings",
        "",
    ]
    lines.extend(f"- **{item['severity']} {item['code']}**: {item['message']}" for item in report["findings"])
    if not report["findings"]:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
