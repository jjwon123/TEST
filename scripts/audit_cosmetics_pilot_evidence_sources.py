#!/usr/bin/env python3
"""Audit the curated cosmetics pilot evidence source snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json  # noqa: E402
from services.marketing_intelligence.source_audit import audit_evidence_snapshot  # noqa: E402


DEFAULT_SNAPSHOT = ROOT / "assets" / "rules" / "cosmetics-pilot-public-evidence-snapshot.json"
DEFAULT_OUTPUT = ROOT / ".tmp" / "model-benchmarks" / "cosmetics-pilot-source-audit.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = audit_evidence_snapshot(read_json(args.snapshot.resolve(), {"observations": []}))
    write_json(args.output.resolve(), report)
    print(json.dumps({"status": report["status"], **report["summary"]}, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
