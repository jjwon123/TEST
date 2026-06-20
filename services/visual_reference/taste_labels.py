"""검수 완료 training session에서 (이미지, 취향 라벨) 쌍을 모은다.

라벨 = 기원님 최종 판단. selected(+옵션 shortlist)=1(good), rejected=0(bad).
ground truth 도출: correctDecision 우선, 없으면 status==agree일 때 당시 AI 결정,
그 외(unsure/미검수/disagree인데 정답 미기입)는 제외.

torch/open_clip를 import하지 않으므로 단독으로 테스트 가능하다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TRAINING_ROOT = ROOT / "design_brain_wiki" / "training_sessions"
EXCLUDED_PROFILES = {"reference_learning"}  # 브리프-비특화 대량 큐는 취향 학습에서 제외


@dataclass(frozen=True)
class LabeledExample:
    id: str
    file: Path
    label: int
    session: str
    truth: str


def _normalize(value: Any) -> str:
    v = str(value or "").strip().lower()
    if v in {"selected", "select", "approved", "approve"}:
        return "selected"
    if v in {"shortlist", "candidate", "maybe"}:
        return "shortlist"
    if v in {"rejected", "reject", "drop", "exclude", "excluded"}:
        return "rejected"
    return ""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _items(judgement: Any) -> list[dict[str, Any]]:
    if isinstance(judgement, list):
        return judgement
    for key in ("items", "references", "judgements"):
        if isinstance(judgement.get(key), list):
            return judgement[key]
    return []


def _truth(review: dict[str, Any], ai_decision: str) -> str:
    status = str(review.get("status", "")).strip().lower()
    correct = _normalize(review.get("correctDecision", ""))
    if correct:
        return correct
    if status == "agree":
        return ai_decision
    return ""


def session_examples(
    session_dir: Path,
    *,
    include_shortlist: bool = False,
    root: Path = ROOT,
) -> list[LabeledExample]:
    judgement_path = session_dir / "ai_judgement.json"
    state_path = session_dir / "kiwon_review_state.json"
    if not judgement_path.exists() or not state_path.exists():
        return []
    reviews = _read_json(state_path).get("reviews", {})
    examples: list[LabeledExample] = []
    for item in _items(_read_json(judgement_path)):
        item_id = str(item.get("id") or "")
        ai = _normalize(item.get("decision"))
        truth = _truth(reviews.get(item_id) or {}, ai)
        if truth == "selected":
            label = 1
        elif truth == "shortlist" and include_shortlist:
            label = 1
        elif truth == "rejected":
            label = 0
        else:
            continue
        rel = str(item.get("file") or "")
        if not rel:
            continue
        path = Path(rel)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            continue
        examples.append(LabeledExample(id=item_id, file=path.resolve(), label=label, session=session_dir.name, truth=truth))
    return examples


def gather_labeled_examples(
    *,
    sessions: list[Path] | None = None,
    training_root: Path = TRAINING_ROOT,
    include_shortlist: bool = False,
    root: Path = ROOT,
) -> list[LabeledExample]:
    if sessions is None:
        sessions = [
            p.parent
            for p in sorted(training_root.glob("*/*/kiwon_review_state.json"))
            if p.parent.parent.name not in EXCLUDED_PROFILES
        ]
    seen: set[Path] = set()
    examples: list[LabeledExample] = []
    for session_dir in sessions:
        for example in session_examples(session_dir, include_shortlist=include_shortlist, root=root):
            if example.file in seen:
                continue  # 같은 이미지가 여러 세션에 중복될 때 1회만
            seen.add(example.file)
            examples.append(example)
    return examples
