#!/usr/bin/env python3
"""Audit visual candidate prompts before ComfyUI live generation."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json, write_text


PROFILE_REQUIRED_DIRECTIONS = {
    "bullion_investment": {
    "gold bar": ("gold bar", "gold bars", "bullion"),
    "gold coin": ("gold coin", "gold coins", "coins"),
    "bullion investment": ("bullion investment", "gold bullion", "precious metal investment"),
    "financial trust": ("financial trust", "financial-trust", "high-trust finance", "trust finance"),
    "premium consultation": ("premium consultation", "financial consultation", "consultation campaign", "consultation desk"),
    "luxury finance": ("luxury finance", "premium finance", "premium financial"),
    "clean premium layout": ("clean premium layout", "clean composition", "premium layout", "poster layout"),
    "blank space for Korean headline": ("blank space for korean headline", "empty text area"),
    "no readable text": ("no readable text", "no fake typography", "no fake text"),
    },
    "cosmetics_skincare": {
        "skincare product": ("skincare", "skin care", "serum", "cosmetic", "beauty product", "product focus"),
        "korean h&b sale": ("korean h&b", "h&b sale", "korean beauty sale", "local korean beauty"),
        "benefit hierarchy": ("discount", "gift", "free shipping", "benefit hierarchy", "promotion", "sale"),
        "clean cardnews layout": ("card news", "cardnews", "banner layout", "promotion layout", "clean layout"),
        "blank space for Korean headline": ("blank space for korean headline", "empty text area"),
        "no readable text": ("no readable text", "no fake typography", "no fake text"),
    },
    "general": {
        "campaign layout": ("campaign layout", "promotion layout", "banner layout", "clean layout"),
        "product focus": ("product focus", "hero product", "clear focal subject"),
        "copy space": ("copy space", "empty text area", "blank space"),
        "no readable text": ("no readable text", "no fake typography", "no fake text"),
    },
}

PROFILE_FORBIDDEN_POSITIVE = {
    "bullion_investment": (
    "mascot",
    "character",
    "cute",
    "camping",
    "picnic",
    "tent",
    "toy",
    "cartoon",
    "kawaii",
    "wine",
    "bottle",
    "random package",
    "package box",
    "fake text",
    ),
    "cosmetics_skincare": (
        "website screenshot",
        "browser",
        "url bar",
        "address bar",
        "homepage capture",
        "foreign sale",
        "english-only",
        "fake text",
        "broken text",
        "hair product",
        "nail product",
        "perfume",
    ),
    "general": ("fake text", "broken text", "website screenshot", "url bar"),
}

PROFILE_NEGATIVE_REQUIRED = {
    "bullion_investment": (
    "mascot",
    "character",
    "camping",
    "picnic",
    "wine bottle",
    "random package",
    "fake poster text",
    ),
    "cosmetics_skincare": (
        "website screenshot",
        "url bar",
        "homepage capture",
        "fake text",
        "broken korean text",
        "wrong product category",
    ),
    "general": ("fake text", "broken text", "website screenshot"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit 04 visual candidate prompts before live generation.")
    parser.add_argument("--run", required=True, type=Path, help="Run directory.")
    args = parser.parse_args()

    run_dir = args.run.resolve()
    audit = build_prompt_audit(run_dir)
    output_dir = run_dir / "03_visual_candidates"
    write_json(output_dir / "prompt-audit.json", audit)
    write_text(output_dir / "prompt-audit.md", build_markdown(audit))
    print(f"OK prompt audit {output_dir / 'prompt-audit.json'}")
    return 0


def build_prompt_audit(run_dir: Path) -> dict[str, Any]:
    prompts_payload = read_json(run_dir / "03_visual_candidates" / "image-prompts.json")
    reference_research = read_json(run_dir / "03_reference_research" / "reference-research.json", default={})
    profile = (reference_research.get("eventProfile") or {}).get("category") or "general"
    prompts = prompts_payload.get("prompts", [])
    items = [audit_prompt(prompt, profile) for prompt in prompts]
    passed = len([item for item in items if item["status"] == "pass"])
    failed = len([item for item in items if item["status"] == "fail"])
    warnings = len([item for item in items if item["status"] == "warning"])
    return {
        "runId": run_dir.name,
        "profile": profile,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "source": "03_visual_candidates/image-prompts.json",
        "totalPrompts": len(items),
        "passed": passed,
        "warning": warnings,
        "failed": failed,
        "criteria": {
            "minimumRequiredHits": 5,
            "positiveForbiddenHitsMustBeZero": True,
            "negativeMustIncludeForbiddenDirection": True,
            "requiresFakeTextPrevention": True,
            "requiresKoreanHeadlineBlankSpace": True,
        },
        "items": items,
    }


def audit_prompt(prompt: dict[str, Any], profile: str = "general") -> dict[str, Any]:
    positive = str(prompt.get("positive_prompt") or "")
    negative = str(prompt.get("negative_prompt") or "")
    positive_l = positive.lower()
    negative_l = negative.lower()
    required_directions = PROFILE_REQUIRED_DIRECTIONS.get(profile) or PROFILE_REQUIRED_DIRECTIONS["general"]
    forbidden_positive = PROFILE_FORBIDDEN_POSITIVE.get(profile) or PROFILE_FORBIDDEN_POSITIVE["general"]
    negative_required = PROFILE_NEGATIVE_REQUIRED.get(profile) or PROFILE_NEGATIVE_REQUIRED["general"]

    required_hits = [
        label
        for label, aliases in required_directions.items()
        if any(alias in positive_l or alias in negative_l for alias in aliases)
    ]
    missing_required = [label for label in required_directions if label not in required_hits]
    forbidden_hits = [term for term in forbidden_positive if term in positive_l]
    negative_missing = [term for term in negative_required if term not in negative_l]
    fake_text_ok = any(term in negative_l or term in positive_l for term in ("no fake text", "no readable text", "no fake typography"))
    headline_space_ok = any(term in positive_l for term in ("blank space for korean headline", "empty text area"))
    min_required_hits = 4 if profile == "cosmetics_skincare" else 5

    fail_reasons = []
    warning_reasons = []
    if forbidden_hits:
        fail_reasons.append("positive prompt contains forbidden direction")
    if len(required_hits) < min_required_hits:
        fail_reasons.append(f"required direction hit count is below {min_required_hits}")
    if not fake_text_ok:
        fail_reasons.append("missing fake text prevention")
    if not headline_space_ok:
        fail_reasons.append("missing Korean headline blank space")
    if negative_missing:
        warning_reasons.append("negative prompt is missing some blocker terms")

    if fail_reasons:
        status = "fail"
    elif warning_reasons:
        status = "warning"
    else:
        status = "pass"

    notes = []
    if fail_reasons:
        notes.extend(fail_reasons)
    if warning_reasons:
        notes.extend(warning_reasons)
    if not notes:
        notes.append("Prompt direction is ready for a small live generation test.")

    return {
        "promptId": prompt.get("prompt_id", ""),
        "candidateId": prompt.get("candidate_id", ""),
        "visualRole": prompt.get("visual_role", ""),
        "channelId": prompt.get("channel_id", ""),
        "status": status,
        "requiredHits": required_hits,
        "missingRequired": missing_required,
        "forbiddenHits": forbidden_hits,
        "negativeMissing": negative_missing,
        "fakeTextPrevention": fake_text_ok,
        "koreanHeadlineBlankSpace": headline_space_ok,
        "notes": "; ".join(notes),
    }


def build_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Prompt Audit",
        "",
        f"- Run: `{audit['runId']}`",
        f"- Profile: `{audit['profile']}`",
        f"- Total prompts: {audit['totalPrompts']}",
        f"- Passed: {audit['passed']}",
        f"- Warning: {audit['warning']}",
        f"- Failed: {audit['failed']}",
        "",
        "## Criteria",
        "",
        "- positive prompt forbidden hit = 0",
        "- negative prompt includes forbidden directions",
        "- required direction hit count >= 5",
        "- fake text prevention is present",
        "- Korean headline blank space is present",
        "",
        "## Items",
        "",
    ]
    for item in audit["items"]:
        lines.extend([
            f"### {item['promptId']}",
            "",
            f"- Status: `{item['status']}`",
            f"- Visual role: `{item['visualRole']}`",
            f"- Required hits: {', '.join(item['requiredHits']) or '-'}",
            f"- Missing required: {', '.join(item['missingRequired']) or '-'}",
            f"- Forbidden hits: {', '.join(item['forbiddenHits']) or '-'}",
            f"- Negative missing: {', '.join(item['negativeMissing']) or '-'}",
            f"- Notes: {item['notes']}",
            "",
        ])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
