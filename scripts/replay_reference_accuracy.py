#!/usr/bin/env python3
"""Offline reference-judgement accuracy harness.

검수가 끝난 training session들에 대해, 사람 검수나 라이브 모델 없이 현재 판단
파이프라인의 정확도를 재측정한다.

- ground truth: kiwon_review_state.json (status agree -> 당시 AI 결정, disagree ->
  correctDecision, unsure/미검수 -> 제외)
- baseline: 세션 생성 시점에 저장된 AI decision (학습 룰 이전)
- learned: baseline에 현재 promoted learned rules를 적용한 결정
  (core.utils.learned_reference_rules.apply_promoted_rules)

3-class(selected/shortlist/rejected) 정확도와, 실무적으로 더 중요한
2-class(keep=selected|shortlist vs drop=rejected) 정확도, 그리고 혼동행렬과
과선택/과제외 방향을 출력한다.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.learned_reference_rules import apply_promoted_rules  # noqa: E402

TRAINING_ROOT = ROOT / "design_brain_wiki" / "training_sessions"
ORDER = ["rejected", "shortlist", "selected"]


def normalize(value: str) -> str:
    v = str(value or "").strip().lower()
    if v in {"selected", "select", "approved", "approve"}:
        return "selected"
    if v in {"shortlist", "candidate", "maybe"}:
        return "shortlist"
    if v in {"rejected", "reject", "drop", "exclude", "excluded"}:
        return "rejected"
    return ""


def load_items(session_dir: Path) -> list[dict[str, Any]]:
    data = json.loads((session_dir / "ai_judgement.json").read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    for key in ("items", "references", "judgements"):
        if isinstance(data.get(key), list):
            return data[key]
    return []


def truth_for(review: dict[str, Any], ai_decision: str) -> str:
    """기원님 최종 정답. 미검수/unsure는 빈 문자열."""
    status = str(review.get("status", "")).strip().lower()
    correct = normalize(review.get("correctDecision", ""))
    if status == "agree":
        return correct or ai_decision
    if status == "disagree":
        return correct or ""  # disagree인데 정답 미기입이면 신뢰 불가 -> 제외
    return ""  # unsure / 빈 상태


def evaluate_session(session_dir: Path, profile: str) -> dict[str, Any] | None:
    state_path = session_dir / "kiwon_review_state.json"
    if not state_path.exists():
        return None
    reviews = json.loads(state_path.read_text(encoding="utf-8")).get("reviews", {})
    items = load_items(session_dir)
    rows = []
    for item in items:
        ai = normalize(item.get("decision"))
        review = reviews.get(item.get("id")) or {}
        truth = truth_for(review, ai)
        if not truth or not ai:
            continue
        tags = item.get("riskSignals") or []
        learned, _applied = apply_promoted_rules(profile, ai, list(tags))
        rows.append({"truth": truth, "baseline": ai, "learned": normalize(learned)})
    if not rows:
        return None
    return {"session": session_dir.name, "rows": rows}


def evaluate_session_vision(
    session_dir: Path,
    profile: str,
    limit: int,
    model: str,
    host: str,
    hybrid_threshold: float = 70.0,
) -> list[dict[str, Any]]:
    """같은 항목에 대해 메타데이터(learned), 비전(vision), 하이브리드(hybrid) 판단을 함께 산출.

    hybrid = 메타데이터 learned 결정을 기본으로 두되, 비전이 강한 hard-risk
    (website_capture_risk / text_artifact_risk / risk_level >= hybrid_threshold)를
    줄 때만 rejected로 downgrade. 비전의 결함 탐지 강점만 쓰고 과제외는 피한다.

    qwen 결과는 세션 폴더의 .vision_cache.json에 캐시해, 임계값 튜닝 시 비전 재호출을 피한다.
    """
    import importlib
    from services.visual_reference.qwen_reviewer import build_profile_reference_prompt, review_image

    crts = importlib.import_module("scripts.create_reference_training_session")
    config = crts.PROFILE_CONFIG.get(profile) or crts.default_config(profile)
    prompt = build_profile_reference_prompt(profile)
    reviews = json.loads((session_dir / "kiwon_review_state.json").read_text(encoding="utf-8")).get("reviews", {})

    cache_path = session_dir / ".vision_cache.json"
    cache: dict[str, Any] = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    rows = []
    count = 0
    dirty = False
    for item in load_items(session_dir):
        item_id = str(item.get("id"))
        ai = normalize(item.get("decision"))
        truth = truth_for(reviews.get(item_id) or {}, ai)
        if not truth or not ai:
            continue
        img = ROOT / str(item.get("file", ""))
        if not img.exists():
            continue
        if limit and count >= limit:
            break
        count += 1
        cached = cache.get(item_id)
        if cached and cached.get("qwen_review") is not None:
            qwen = cached["qwen_review"]
            w, h = cached.get("w", 1024), cached.get("h", 1024)
        else:
            try:
                qwen = review_image(img, model=model, host=host, prompt=prompt)
            except Exception:
                qwen = {}
            try:
                from PIL import Image
                with Image.open(img) as im:
                    w, h = im.size
            except Exception:
                w = h = 1024
            cache[item_id] = {"qwen_review": qwen, "w": w, "h": h}
            dirty = True
        record = {"width": w, "height": h, "qwen_review": qwen}
        vision = normalize(crts.auto_decision(record, config))
        learned, _ = apply_promoted_rules(profile, ai, list(item.get("riskSignals") or []))
        learned = normalize(learned)
        qwen = qwen or {}
        hard_risk = max(
            float(qwen.get("website_capture_risk", 0) or 0),
            float(qwen.get("text_artifact_risk", 0) or 0),
            float(qwen.get("risk_level", 0) or 0),
        )
        hybrid = "rejected" if hard_risk >= hybrid_threshold else learned
        rows.append({
            "truth": truth, "baseline": ai, "learned": learned,
            "vision": vision, "hybrid": hybrid,
        })

    if dirty:
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


def accuracy(rows: list[dict], key: str) -> float:
    return sum(1 for r in rows if r[key] == r["truth"]) / len(rows)


def binary(d: str) -> str:
    return "drop" if d == "rejected" else "keep"


def binary_accuracy(rows: list[dict], key: str) -> float:
    return sum(1 for r in rows if binary(r[key]) == binary(r["truth"])) / len(rows)


def confusion(rows: list[dict], key: str) -> Counter:
    return Counter((r["truth"], r[key]) for r in rows)


def run_vision_ab(args, profile_root: Path) -> int:
    if args.sessions:
        session_dirs = [profile_root / s for s in args.sessions]
    else:
        session_dirs = sorted(p.parent for p in profile_root.glob("*/kiwon_review_state.json"))
    all_rows: list[dict] = []
    print(f"=== Vision A/B: {args.profile} (meta/vision/hybrid, hard-risk>={args.hybrid_threshold:.0f}) ===\n")
    print(f"{'session':<26}{'n':>4}{'meta2':>8}{'vis2':>8}{'hyb2':>8}{'meta3':>8}{'hyb3':>8}")
    for sd in session_dirs:
        rows = evaluate_session_vision(sd, args.profile, args.limit, args.qwen_model, args.qwen_host, args.hybrid_threshold)
        if not rows:
            continue
        all_rows.extend(rows)
        print(f"{sd.name:<26}{len(rows):>4}"
              f"{binary_accuracy(rows,'learned'):>8.1%}{binary_accuracy(rows,'vision'):>8.1%}{binary_accuracy(rows,'hybrid'):>8.1%}"
              f"{accuracy(rows,'learned'):>8.1%}{accuracy(rows,'hybrid'):>8.1%}")
    if not all_rows:
        print("평가 가능한 row 없음.")
        return 1
    print("\n=== 전체 집계 ===")
    print(f"평가 row 수: {len(all_rows)}")
    print(f"2-class(keep/drop): 메타 {binary_accuracy(all_rows,'learned'):.1%} | 비전 {binary_accuracy(all_rows,'vision'):.1%} | 하이브리드 {binary_accuracy(all_rows,'hybrid'):.1%}")
    print(f"3-class           : 메타 {accuracy(all_rows,'learned'):.1%} | 비전 {accuracy(all_rows,'vision'):.1%} | 하이브리드 {accuracy(all_rows,'hybrid'):.1%}")
    print("\n=== 혼동행렬 (hybrid): truth -> ai ===")
    conf = confusion(all_rows, "hybrid")
    header = "truth\\ai"
    print(f"{header:<12}" + "".join(f"{d:>10}" for d in ORDER))
    for t in ORDER:
        print(f"{t:<12}" + "".join(f"{conf.get((t,a),0):>10}" for a in ORDER))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="cosmetics_skincare")
    parser.add_argument("--sessions", nargs="*", help="세션 id. 기본은 프로필의 모든 검수 세션.")
    parser.add_argument("--qwen-vision", action="store_true", help="세션 이미지를 Qwen 비전으로 재판단해 메타데이터 vs 비전 정확도를 A/B 비교.")
    parser.add_argument("--limit", type=int, default=0, help="비전 모드에서 세션당 최대 항목 수. 0은 전체.")
    parser.add_argument("--hybrid-threshold", type=float, default=70.0, help="하이브리드: 비전 hard-risk가 이 값 이상이면 메타 결정을 rejected로 downgrade.")
    parser.add_argument("--qwen-model", default="qwen2.5vl:7b")
    parser.add_argument("--qwen-host", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    profile_root = TRAINING_ROOT / args.profile

    if args.qwen_vision:
        return run_vision_ab(args, profile_root)

    if args.sessions:
        session_dirs = [profile_root / s for s in args.sessions]
    else:
        session_dirs = sorted(p.parent for p in profile_root.glob("*/kiwon_review_state.json"))

    all_rows: list[dict] = []
    print(f"=== Reference accuracy replay: {args.profile} ===\n")
    print(f"{'session':<28}{'n':>4}{'base3':>8}{'learn3':>8}{'base2':>8}{'learn2':>8}")
    for sd in session_dirs:
        result = evaluate_session(sd, args.profile)
        if not result:
            continue
        rows = result["rows"]
        all_rows.extend(rows)
        print(f"{result['session']:<28}{len(rows):>4}"
              f"{accuracy(rows,'baseline'):>8.1%}{accuracy(rows,'learned'):>8.1%}"
              f"{binary_accuracy(rows,'baseline'):>8.1%}{binary_accuracy(rows,'learned'):>8.1%}")

    if not all_rows:
        print("검수된 row 없음.")
        return 1

    print("\n=== 전체 집계 ===")
    print(f"검수 row 수: {len(all_rows)}")
    print(f"3-class 정확도: baseline {accuracy(all_rows,'baseline'):.1%} -> learned {accuracy(all_rows,'learned'):.1%}")
    print(f"2-class(keep/drop) 정확도: baseline {binary_accuracy(all_rows,'baseline'):.1%} -> learned {binary_accuracy(all_rows,'learned'):.1%}")

    print("\n=== 혼동행렬 (learned): truth -> ai ===")
    conf = confusion(all_rows, "learned")
    header = "truth\\ai"
    print(f"{header:<12}" + "".join(f"{d:>10}" for d in ORDER))
    for t in ORDER:
        print(f"{t:<12}" + "".join(f"{conf.get((t,a),0):>10}" for a in ORDER))

    over = sum(conf.get((t, a), 0) for t in ORDER for a in ORDER if ORDER.index(a) > ORDER.index(t))
    under = sum(conf.get((t, a), 0) for t in ORDER for a in ORDER if ORDER.index(a) < ORDER.index(t))
    print(f"\n과선택(AI가 더 높게 평가): {over}건")
    print(f"과제외(AI가 더 낮게 평가): {under}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
