from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_repeated_operations import audit


class RepeatedOperationsTests(unittest.TestCase):
    def test_requires_three_terminal_events_and_a_recovered_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(3):
                self._write_run(root, f"run-{index}", f"Event {index}", recovered=index == 0)

            report = audit(root)

        self.assertEqual("pass", report["status"])
        self.assertEqual(3, report["summary"]["terminalSuccessEvents"])
        self.assertEqual(1, report["summary"]["recoveredRuns"])

    def test_distinguishes_automation_checkpoint_from_terminal_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(3):
                self._write_run(root, f"run-{index}", f"Event {index}", terminal=index < 2)

            report = audit(root)

        self.assertEqual("incomplete", report["status"])
        self.assertEqual(3, report["summary"]["automationCheckpointEvents"])
        self.assertEqual(2, report["summary"]["terminalSuccessEvents"])

    @staticmethod
    def _write_run(root: Path, run_id: str, event_name: str, *, terminal: bool = True, recovered: bool = False) -> None:
        run = root / run_id
        run.mkdir(parents=True)
        payload = {
            "event_name": event_name,
            "run_state": "archived" if terminal else "reference_ready",
            "stage_status": {
                "01_event_brief": "approved",
                "02_content_planning": "approved",
                "03_reference_research": "done",
            },
            "stage_failures": [{"stage": "03_reference_research"}] if recovered else [],
        }
        (run / "run-status.json").write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
