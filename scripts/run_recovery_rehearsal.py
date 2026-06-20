#!/usr/bin/env python3
"""Create a test-event run, record a real stage failure, and recover the same run."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow import approve_stage, mark_stage, setup_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path, default=ROOT / "events" / "test-event-automation")
    args = parser.parse_args()

    run_dir = setup_run(args.event.resolve())
    mark_stage(run_dir, "01_event_brief")
    approve_stage(run_dir, "01_event_brief", approver="operations_rehearsal", note="Automated recovery rehearsal gate.")
    mark_stage(run_dir, "02_content_planning")
    approve_stage(run_dir, "02_content_planning", approver="operations_rehearsal", note="Automated recovery rehearsal gate.")

    blocker = run_dir / "03_reference_research" / "reference-research.json"
    blocker.mkdir(parents=True, exist_ok=False)
    failure_recorded = False
    try:
        mark_stage(run_dir, "03_reference_research")
    except SystemExit:
        failure_recorded = True
    finally:
        if blocker.is_dir():
            shutil.rmtree(blocker)
    if not failure_recorded:
        raise RuntimeError("Recovery rehearsal failed to record the intended stage error.")

    mark_stage(run_dir, "03_reference_research", mode="regenerate")
    print(f"RECOVERY_REHEARSAL pass {run_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
