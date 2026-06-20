from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from services.visual_reference.taste_labels import gather_labeled_examples, session_examples


class TasteLabelsTests(unittest.TestCase):
    def _make_session(self, root: Path, items: list[dict], reviews: dict) -> Path:
        session = root / "cosmetics_skincare" / "sess_001"
        refs = session / "references"
        refs.mkdir(parents=True)
        for item in items:
            # 실제 이미지 파일을 만들어 존재 검사를 통과시킨다.
            (root / item["file"]).parent.mkdir(parents=True, exist_ok=True)
            (root / item["file"]).write_bytes(b"x")
        (session / "ai_judgement.json").write_text(json.dumps({"items": items}), encoding="utf-8")
        (session / "kiwon_review_state.json").write_text(json.dumps({"reviews": reviews}), encoding="utf-8")
        return session

    def test_maps_truth_to_good_bad_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = [
                {"id": "a", "file": "img/a.jpg", "decision": "shortlist"},
                {"id": "b", "file": "img/b.jpg", "decision": "selected"},
                {"id": "c", "file": "img/c.jpg", "decision": "selected"},
                {"id": "d", "file": "img/d.jpg", "decision": "shortlist"},
            ]
            reviews = {
                "a": {"status": "disagree", "correctDecision": "rejected"},  # -> bad
                "b": {"status": "agree"},                                     # -> good (ai selected)
                "c": {"status": "disagree", "correctDecision": "rejected"},   # -> bad
                "d": {"status": "unsure"},                                    # -> skip
            }
            session = self._make_session(root, items, reviews)
            examples = session_examples(session, root=root)

        by_id = {e.id: e for e in examples}
        self.assertEqual({"a", "b", "c"}, set(by_id))  # d skipped
        self.assertEqual(0, by_id["a"].label)
        self.assertEqual(1, by_id["b"].label)
        self.assertEqual(0, by_id["c"].label)

    def test_include_shortlist_counts_shortlist_as_good(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = [{"id": "a", "file": "img/a.jpg", "decision": "shortlist"}]
            reviews = {"a": {"status": "agree"}}  # truth shortlist
            session = self._make_session(root, items, reviews)
            without = session_examples(session, root=root, include_shortlist=False)
            with_short = session_examples(session, root=root, include_shortlist=True)
        self.assertEqual([], without)
        self.assertEqual(1, with_short[0].label)

    def test_skips_missing_image_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = root / "cosmetics_skincare" / "sess_001"
            session.mkdir(parents=True)
            (session / "ai_judgement.json").write_text(
                json.dumps({"items": [{"id": "a", "file": "img/missing.jpg", "decision": "selected"}]}), encoding="utf-8")
            (session / "kiwon_review_state.json").write_text(
                json.dumps({"reviews": {"a": {"status": "agree"}}}), encoding="utf-8")
            examples = session_examples(session, root=root)
        self.assertEqual([], examples)

    def test_excludes_session_flagged_exclude_from_training(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = [{"id": "a", "file": "img/a.jpg", "decision": "selected"}]
            reviews = {"a": {"status": "agree"}}
            session = self._make_session(root, items, reviews)
            # 정상일 땐 라벨이 잡힌다
            self.assertEqual(1, len(session_examples(session, root=root)))
            # excludeFromTraining 플래그를 켜면 제외된다
            judgement = json.loads((session / "ai_judgement.json").read_text(encoding="utf-8"))
            judgement["excludeFromTraining"] = True
            (session / "ai_judgement.json").write_text(json.dumps(judgement), encoding="utf-8")
            self.assertEqual([], session_examples(session, root=root))

    def test_gather_dedupes_repeated_images_across_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = [{"id": "a", "file": "img/a.jpg", "decision": "selected"}]
            reviews = {"a": {"status": "agree"}}
            s1 = self._make_session(root, items, reviews)
            # 같은 이미지 파일을 가리키는 두 번째 세션
            s2 = root / "cosmetics_skincare" / "sess_002"
            s2.mkdir(parents=True)
            (s2 / "ai_judgement.json").write_text(json.dumps({"items": items}), encoding="utf-8")
            (s2 / "kiwon_review_state.json").write_text(json.dumps({"reviews": reviews}), encoding="utf-8")
            examples = gather_labeled_examples(sessions=[s1, s2], root=root)
        self.assertEqual(1, len(examples))  # 중복 1회만


if __name__ == "__main__":
    unittest.main()
