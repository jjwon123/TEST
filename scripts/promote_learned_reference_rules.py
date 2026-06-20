#!/usr/bin/env python3
"""Promote repeated learned reference rules into the runtime rule set."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.learned_reference_rules import PROMOTED_RULES_PATH, write_promoted_rules


def main() -> int:
    payload = write_promoted_rules()
    print(json.dumps({
        "path": str(PROMOTED_RULES_PATH.relative_to(ROOT)),
        "summary": payload["summary"],
        "rules": [rule["id"] for rule in payload["rules"]],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
