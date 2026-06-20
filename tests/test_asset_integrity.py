from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_asset_integrity import audit


class AssetIntegrityTests(unittest.TestCase):
    def test_detects_missing_approved_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            assets = root / "assets"
            runs = root / "runs"
            self._write(assets / "indexes" / "global-index.json", {"assets": [{
                "asset_id": "a1",
                "event_id": "event",
                "archive_path_approved": "approved/event/a1.png",
                "reuse_status": "limited_reuse",
                "archive_path_reusable": "",
            }]})
            self._write(assets / "indexes" / "by-event" / "event.json", {
                "event_id": "event",
                "assets": [{"asset_id": "a1"}],
            })

            report = audit(assets_root=assets, runs_root=runs)

            self.assertEqual("fail", report["status"])
            self.assertIn("missing_approved_file", [item["code"] for item in report["findings"]])

    def test_passes_consistent_archive_and_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            assets = root / "assets"
            runs = root / "runs"
            approved = assets / "approved" / "event" / "a1.png"
            approved.parent.mkdir(parents=True)
            approved.write_bytes(b"image")
            record = {
                "asset_id": "a1",
                "event_id": "event",
                "archive_path_approved": "approved/event/a1.png",
                "reuse_status": "limited_reuse",
                "archive_path_reusable": "",
            }
            self._write(assets / "indexes" / "global-index.json", {"assets": [record]})
            self._write(assets / "indexes" / "by-event" / "event.json", {"event_id": "event", "assets": [record]})
            self._write(runs / "run" / "07_asset_archive" / "asset-archive.json", {"assets": [record]})

            report = audit(assets_root=assets, runs_root=runs)

            self.assertEqual("pass", report["status"])

    @staticmethod
    def _write(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
