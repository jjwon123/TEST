from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ingest_image_folder_session import build_folder_session
from services.visual_reference.taste_labels import session_examples


class IngestImageFolderSessionTests(unittest.TestCase):
    def _make_images(self, folder: Path, n: int) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            (folder / f"img_{i}.jpg").write_bytes(b"x")

    def test_builds_console_compatible_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "board"
            self._make_images(src, 3)
            training_root = root / "training_sessions"
            result = build_folder_session(
                src, profile="cosmetics_skincare", session_id="board_001",
                training_root=training_root, root=root)

            session_dir = training_root / "cosmetics_skincare" / "board_001"
            self.assertEqual(3, result["images"])
            self.assertTrue((session_dir / "ai_judgement.json").exists())
            self.assertTrue((session_dir / "kiwon_review_state.json").exists())
            self.assertEqual(3, len(list((session_dir / "references").glob("*.jpg"))))

            judgement = json.loads((session_dir / "ai_judgement.json").read_text(encoding="utf-8"))
            self.assertEqual("folder_import", judgement["sessionType"])
            item = judgement["items"][0]
            # 콘솔이 basename으로 이미지를 서빙하므로 file은 references/ 아래여야 한다.
            self.assertIn("references/", item["file"])
            self.assertTrue((root / item["file"]).exists())

    def test_ingested_session_feeds_taste_labels_after_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "board"
            self._make_images(src, 2)
            training_root = root / "training_sessions"
            build_folder_session(src, profile="cosmetics_skincare", session_id="board_001",
                                 training_root=training_root, root=root)
            session_dir = training_root / "cosmetics_skincare" / "board_001"

            # 사람 검수 시뮬레이션: 첫 이미지 good, 둘째 bad
            judgement = json.loads((session_dir / "ai_judgement.json").read_text(encoding="utf-8"))
            ids = [it["id"] for it in judgement["items"]]
            (session_dir / "kiwon_review_state.json").write_text(json.dumps({"reviews": {
                ids[0]: {"status": "disagree", "correctDecision": "selected"},
                ids[1]: {"status": "disagree", "correctDecision": "rejected"},
            }}), encoding="utf-8")

            examples = session_examples(session_dir, root=root)
            labels = sorted(e.label for e in examples)
        self.assertEqual([0, 1], labels)


if __name__ == "__main__":
    unittest.main()
