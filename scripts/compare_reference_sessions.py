#!/usr/bin/env python3
"""Compare reviewed reference judgement sessions for one profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRAINING_ROOT = ROOT / "design_brain_wiki" / "training_sessions"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--sessions", nargs="*", help="Session ids. Defaults to all reviewed sessions for the profile.")
    args = parser.parse_args()
    profile_dir = TRAINING_ROOT / args.profile
    session_ids = args.sessions or [path.name for path in sorted(profile_dir.iterdir()) if path.is_dir()]
    rows = [session_row(profile_dir / session_id) for session_id in session_ids]
    rows = [row for row in rows if row]
    report = {"profile": args.profile, "sessions": rows}
    output_dir = profile_dir / "_comparisons"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "session-comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "session-comparison.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def session_row(session_dir: Path) -> dict[str, Any] | None:
    judgement = read_json(session_dir / "ai_judgement.json")
    review_state = read_json(session_dir / "kiwon_review_state.json")
    if not judgement:
        return None
    items = judgement.get("items", [])
    reviews = (review_state or {}).get("reviews", {})
    reviewed = [item for item in items if reviews.get(item.get("id"), {}).get("status")]
    matches = 0
    transitions: dict[str, int] = {}
    final_counts = {"selected": 0, "shortlist": 0, "rejected": 0}
    for item in reviewed:
        review = reviews.get(item.get("id"), {})
        ai = item.get("decision", "")
        final = review.get("correctDecision") or ai
        if final == ai:
            matches += 1
        if final in final_counts:
            final_counts[final] += 1
        key = f"{ai}->{final}"
        transitions[key] = transitions.get(key, 0) + 1
    accuracy = round(matches / len(reviewed), 3) if reviewed else None
    return {
        "sessionId": session_dir.name,
        "total": len(items),
        "reviewed": len(reviewed),
        "reviewStatus": "reviewed" if reviewed else "pending_review",
        "accuracy": accuracy,
        "aiDecisionCounts": judgement.get("summary", {}).get("decisionCounts", {}),
        "finalDecisionCounts": final_counts,
        "transitionCounts": transitions,
        "sourceRun": judgement.get("sourceRun", ""),
    }


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Reference Session Comparison - {report['profile']}",
        "",
        "| Session | Reviewed | Accuracy | AI decisions | Final decisions | Main transitions |",
        "|---|---:|---:|---|---|---|",
    ]
    for row in report["sessions"]:
        transitions = ", ".join(f"{key}:{value}" for key, value in row["transitionCounts"].items()) or "-"
        accuracy = row["accuracy"] if row["accuracy"] is not None else "pending"
        lines.append(
            f"| `{row['sessionId']}` | {row['reviewed']}/{row['total']} | {accuracy} | "
            f"{row['aiDecisionCounts']} | {row['finalDecisionCounts']} | {transitions} |"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
