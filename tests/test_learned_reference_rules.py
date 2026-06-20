from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.utils.learned_reference_rules import apply_promoted_rules, build_promoted_rules


class LearnedReferenceRulesTests(unittest.TestCase):
    def test_promotes_only_repeated_rules_from_completed_profile_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._session(root, "cosmetics_skincare", "one", "soften_rejected_to_shortlist")
            self._session(root, "cosmetics_skincare", "two", "soften_rejected_to_shortlist")
            self._session(root, "meta_brand_review", "one", "hard_reject_visual_defects")
            payload = build_promoted_rules(training_root=root)

            self.assertEqual(1, payload["summary"]["promotedRules"])
            self.assertEqual("soften_rejected_to_shortlist", payload["rules"][0]["id"])
            self.assertEqual("cosmetics_skincare", payload["rules"][0]["profile"])

    def test_promoted_soften_rule_preserves_hard_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"rules": [{
                "id": "soften_rejected_to_shortlist",
                "profile": "cosmetics_skincare",
                "status": "promoted",
                "decision": "shortlist",
                "unlessAnyReasonTag": ["low_resolution", "website_capture", "fake_text_risk", "wrong_category"],
            }]}), encoding="utf-8")

            softened, applied = apply_promoted_rules("cosmetics_skincare", "rejected", [], path=path)
            preserved, blocked = apply_promoted_rules("cosmetics_skincare", "rejected", ["too_small"], path=path)

            self.assertEqual("shortlist", softened)
            self.assertEqual(["soften_rejected_to_shortlist"], applied)
            self.assertEqual("rejected", preserved)
            self.assertEqual([], blocked)

    @staticmethod
    def _session(root: Path, profile: str, session: str, rule_id: str) -> None:
        path = root / profile / session / "learned_rules.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({
            "profile": profile,
            "summary": {"reviewed": 30, "total": 30, "accuracy": 0.5},
            "rules": [{
                "id": rule_id,
                "decision": "shortlist",
                "unlessAnyReasonTag": ["low_resolution"],
            }],
        }), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
