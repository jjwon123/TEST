from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.migrate_legacy_draft_packages import migrate_legacy_packages


class LegacyPackageMigrationTests(unittest.TestCase):
    def test_moves_only_packages_without_qa_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp) / "runs"
            legacy = self._run(runs, "legacy", "locked")
            approved = self._run(runs, "approved", "approved")

            report = migrate_legacy_packages(runs, apply=True)

            self.assertEqual(1, report["summary"]["applied"])
            self.assertFalse((legacy / "production-package").exists())
            self.assertTrue((legacy / "production-package-legacy-draft" / "legacy-draft-migration.json").exists())
            self.assertTrue((approved / "production-package").exists())

    @staticmethod
    def _run(runs: Path, name: str, qa_status: str) -> Path:
        run = runs / name
        package = run / "production-package"
        package.mkdir(parents=True)
        (package / "file.txt").write_text("draft", encoding="utf-8")
        (run / "run-status.json").write_text(json.dumps({
            "stage_status": {"06_qa_packaging": qa_status},
        }), encoding="utf-8")
        return run


if __name__ == "__main__":
    unittest.main()
