#!/usr/bin/env python3
"""Backfill correction_summary.md and learned_rules.json for training sessions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.console_server import build_learned_rules, render_correction_summary, render_training_review_summary


TRAINING_ROOT = ROOT / "design_brain_wiki" / "training_sessions"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--session-id", help="One session id. If omitted, all sessions for profile are processed.")
    args = parser.parse_args()
    profile_dir = TRAINING_ROOT / args.profile
    session_dirs = [profile_dir / args.session_id] if args.session_id else [path for path in sorted(profile_dir.iterdir()) if path.is_dir()]
    processed = []
    for session_dir in session_dirs:
        if summarize_session(session_dir):
            processed.append(str(session_dir.relative_to(ROOT)).replace("\\", "/"))
    print(json.dumps({"ok": True, "processed": processed}, ensure_ascii=False, indent=2))
    return 0


def summarize_session(session_dir: Path) -> bool:
    judgement = read_json(session_dir / "ai_judgement.json")
    review_state = read_json(session_dir / "kiwon_review_state.json")
    if not judgement:
        return False
    items = judgement.get("items", [])
    reviews = (review_state or {}).get("reviews", {})
    (session_dir / "kiwon_review_summary.md").write_text(render_training_review_summary(items, reviews), encoding="utf-8")
    (session_dir / "correction_summary.md").write_text(render_correction_summary(judgement, items, reviews), encoding="utf-8")
    (session_dir / "learned_rules.json").write_text(
        json.dumps(build_learned_rules(judgement, items, reviews), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return True


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
