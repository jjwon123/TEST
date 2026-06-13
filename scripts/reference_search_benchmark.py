"""Create and run reference-search benchmark events."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.utils.json_io import read_json, write_json
from scripts.reference_pipeline import create_plan
from scripts.workflow import create_run_status
from scripts.workflow import run_reference_pipeline


BENCH_ROOT = ROOT / "runs" / "_reference_search_benchmark"


@dataclass(frozen=True)
class Case:
    case_id: str
    event_name: str
    objective: str
    target: str
    offer: str
    references: list[str]


CASES = [
    Case(
        "ampoule-spring",
        "봄 민감 피부 진정 앰플 체험 이벤트",
        "앰플 신제품 체험 신청 유도",
        "환절기 민감 피부 여성",
        "봄 시즌 3일 체험 키트",
        ["앰플 유리병 제품컷", "봄 파스텔 수분감", "화이트 배경 제품 중심 구성"],
    ),
    Case(
        "ampoule-christmas",
        "크리스마스 진정 앰플 기프트 이벤트",
        "앰플 선물세트 이벤트 참여 유도",
        "연말 스킨케어 선물을 찾는 고객",
        "크리스마스 한정 앰플 키트",
        ["앰플 유리병 제품컷", "크리스마스 선물 무드", "화이트 배경과 레드 그린 포인트"],
    ),
    Case(
        "tube-spring",
        "봄 데일리 선크림 튜브 체험 이벤트",
        "튜브형 선크림 체험 신청 유도",
        "가벼운 데일리 선케어를 찾는 고객",
        "봄 야외활동 선케어 키트",
        ["튜브형 화장품 제품컷", "봄 파스텔 클린 뷰티", "화이트 배경 튜브 패키지"],
    ),
    Case(
        "tube-christmas",
        "크리스마스 핸드크림 튜브 선물 이벤트",
        "튜브형 핸드크림 기프트 프로모션 참여 유도",
        "연말 가벼운 뷰티 선물을 찾는 고객",
        "크리스마스 한정 튜브 화장품 세트",
        ["튜브형 화장품 제품컷", "크리스마스 기프트 무드", "레드 그린 포인트 패키지"],
    ),
    Case(
        "perfume-spring",
        "봄 플로럴 향수 체험 이벤트",
        "향수 체험 신청과 브랜드 인지도 확보",
        "봄 향수를 찾는 20~35세 고객",
        "봄 플로럴 향수 샘플 키트",
        ["향수 보틀 제품컷", "봄 플로럴 파스텔 무드", "럭셔리 향수 스틸라이프"],
    ),
    Case(
        "perfume-christmas",
        "크리스마스 향수 선물 이벤트",
        "향수 선물세트 구매와 이벤트 참여 유도",
        "연말 선물을 찾는 20~40대 고객",
        "크리스마스 한정 패키지",
        ["향수 보틀 제품컷", "크리스마스 선물 무드", "럭셔리 향수 스틸라이프"],
    ),
    Case(
        "jewelry-spring",
        "봄 주얼리 스타일링 이벤트",
        "반지와 목걸이 스타일링 프로모션 참여 유도",
        "봄 데일리 주얼리를 찾는 고객",
        "봄 컬렉션 한정 혜택",
        ["반지 목걸이 주얼리 제품컷", "봄 파스텔 플로럴 무드", "골드 주얼리 스틸라이프"],
    ),
    Case(
        "jewelry-christmas",
        "크리스마스 주얼리 기프트 이벤트",
        "반지와 목걸이 선물 프로모션 참여 유도",
        "연말 주얼리 선물을 찾는 고객",
        "크리스마스 한정 기프트 박스",
        ["반지 목걸이 주얼리 제품컷", "크리스마스 럭셔리 선물 무드", "골드 주얼리 스틸라이프"],
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Pinterest reference search by product and mood.")
    parser.add_argument("--prepare", action="store_true", help="Create benchmark run folders and reference plans.")
    parser.add_argument("--run", action="store_true", help="Run small Pinterest auto-search passes for each case.")
    parser.add_argument("--case", choices=[case.case_id for case in CASES], help="Limit to one benchmark case.")
    parser.add_argument("--query-limit", type=int, default=2)
    parser.add_argument("--per-query-limit", type=int, default=4)
    parser.add_argument("--select-count", type=int, default=3)
    parser.add_argument("--reviewer", choices=["heuristic", "qwen"], default="heuristic")
    parser.add_argument("--review-limit", type=int)
    parser.add_argument("--review-model", default="qwen2.5vl:7b")
    parser.add_argument("--review-host", default="http://127.0.0.1:11434")
    parser.add_argument("--fresh", action="store_true", help="Remove the benchmark root before preparing.")
    args = parser.parse_args()

    cases = [case for case in CASES if not args.case or case.case_id == args.case]
    if args.fresh and BENCH_ROOT.exists():
        shutil.rmtree(BENCH_ROOT)
    BENCH_ROOT.mkdir(parents=True, exist_ok=True)

    summaries: list[dict[str, Any]] = []
    for case in cases:
        run_dir = prepare_case(case)
        if args.run:
            run_reference_pipeline(
                run_dir,
                include_search=True,
                include_queued=False,
                update_visual_candidates=False,
                query_limit=args.query_limit,
                per_query_limit=args.per_query_limit,
                select_count=args.select_count,
                headful=False,
                reviewer=args.reviewer,
                review_limit=args.review_limit,
                review_model=args.review_model,
                review_host=args.review_host,
            )
        summaries.append(summarize_case(run_dir, case))

    report = {
        "benchmark_root": str(BENCH_ROOT),
        "case_count": len(summaries),
        "cases": summaries,
        "quality_summary": summarize_quality(summaries),
    }
    write_json(BENCH_ROOT / "benchmark-report.json", report)
    write_evaluation_table(report)
    write_feedback_template(report)
    write_markdown_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def prepare_case(case: Case) -> Path:
    run_dir = BENCH_ROOT / case.case_id
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "event-input.json", {
        "eventName": case.event_name,
        "objective": case.objective,
        "target": case.target,
        "channels": ["instagram", "blog"],
        "offer": case.offer,
        "references": case.references,
        "requiredPhrases": ["이벤트 참여", "한정 혜택"],
        "bannedWords": ["100% 보장", "기적"],
    })
    write_json(run_dir / "brand-guide.json", {
        "brandName": "Benchmark Brand",
        "tone": "premium clean commercial",
    })
    if not (run_dir / "run-status.json").exists():
        write_json(run_dir / "run-status.json", create_run_status(case.case_id, f"benchmark-{case.case_id}"))
    (run_dir / "logs").mkdir(exist_ok=True)
    create_plan(run_dir, force=True)
    return run_dir


def summarize_case(run_dir: Path, case: Case) -> dict[str, Any]:
    plan = read_json(run_dir / "references" / "reference-collection-plan.json", default={})
    selected = read_json(run_dir / "references" / "selected-references.json", default={"selected": []})
    manifest = read_json(run_dir / "references" / "reference-manifest.json", default={})
    reviewed = read_json(run_dir / "references" / "qwen-reviewed-candidates.json", default={"reviewed": [], "errors": []})
    selected_items = selected.get("selected", [])
    evaluation_rows = [evaluation_row(case, run_dir, item) for item in selected_items]
    operation = manifest.get("selection") or manifest.get("auto_collection") or {}
    return {
        "case_id": case.case_id,
        "run_dir": str(run_dir),
        "event_name": case.event_name,
        "queries": [item.get("query", "") for item in plan.get("search_queries", [])[:6]],
        "selected_count": len(selected_items),
        "asset_count": manifest.get("asset_count", 0),
        "selection_method": operation.get("selection_method", ""),
        "review": operation.get("review", {}),
        "reviewed_count": len(reviewed.get("reviewed", [])),
        "review_error_count": len(reviewed.get("errors", [])),
        "quality": summarize_case_quality(evaluation_rows),
        "evaluation_rows": evaluation_rows,
        "selected": [
            {
                "asset_id": item.get("asset_id"),
                "source_id": item.get("source_id"),
                "query": item.get("query"),
                "score": item.get("score"),
                "quality_score": item.get("quality_score"),
                "text_relevance_score": item.get("text_relevance_score"),
                "review_decision": item.get("review_decision"),
                "review_score": item.get("review_score"),
                "event_fit": item.get("event_fit"),
                "category_fit": item.get("category_fit"),
                "copy_space": item.get("copy_space"),
                "layout_idea": item.get("layout_idea"),
                "production_value": item.get("production_value"),
                "originality": item.get("originality"),
                "risk_control": item.get("risk_control"),
                "relative_path": item.get("relative_path"),
            }
            for item in selected_items
        ],
    }


def evaluation_row(case: Case, run_dir: Path, item: dict[str, Any]) -> dict[str, Any]:
    review = item.get("qwen_review") if isinstance(item.get("qwen_review"), dict) else {}
    absolute_path = Path(run_dir) / str(item.get("relative_path", ""))
    score = numeric(item.get("score"))
    quality_score = numeric(item.get("quality_score"))
    text_score = numeric(item.get("text_relevance_score"))
    review_score = numeric(item.get("review_score"))
    event_fit = numeric(item.get("event_fit"))
    category_fit = numeric(item.get("category_fit"))
    copy_space = numeric(item.get("copy_space"))
    layout_idea = numeric(item.get("layout_idea"))
    production_value = numeric(item.get("production_value"))
    originality = numeric(item.get("originality"))
    risk_control = numeric(item.get("risk_control"))
    weighted = weighted_quality_score(
        score=score,
        quality_score=quality_score,
        text_score=text_score,
        review_score=review_score,
        event_fit=event_fit,
        category_fit=category_fit,
        copy_space=copy_space,
        layout_idea=layout_idea,
        production_value=production_value,
        originality=originality,
        risk_control=risk_control,
    )
    return {
        "case_id": case.case_id,
        "asset_id": item.get("asset_id", ""),
        "source_id": item.get("source_id", ""),
        "query_id": item.get("query_id", ""),
        "query": item.get("query", ""),
        "image_path": str(absolute_path),
        "relative_path": item.get("relative_path", ""),
        "score": score,
        "quality_score": quality_score,
        "text_relevance_score": text_score,
        "review_decision": item.get("review_decision", ""),
        "review_score": review_score,
        "event_fit": event_fit,
        "category_fit": category_fit,
        "copy_space": copy_space,
        "layout_idea": layout_idea,
        "production_value": production_value,
        "originality": originality,
        "risk_control": risk_control,
        "weighted_quality_score": weighted,
        "quality_grade": quality_grade(weighted),
        "needs_human_review": needs_human_review(item, weighted),
        "ai_role": review.get("role", ""),
        "ai_positive_tags": ",".join(str(tag) for tag in review.get("positive_tags", []) if str(tag).strip()),
        "ai_negative_tags": ",".join(str(tag) for tag in review.get("negative_tags", []) if str(tag).strip()),
        "ai_reason": review.get("reason", ""),
        "ai_risk": review.get("risk", ""),
        "human_decision": "",
        "human_score": "",
        "human_notes": "",
        "feedback_tags": "",
    }


def weighted_quality_score(
    *,
    score: float,
    quality_score: float,
    text_score: float,
    review_score: float,
    event_fit: float,
    category_fit: float,
    copy_space: float,
    layout_idea: float,
    production_value: float,
    originality: float,
    risk_control: float,
) -> float:
    if review_score:
        value = (
            score * 0.15
            + quality_score * 0.10
            + text_score * 0.10
            + review_score * 0.10
            + event_fit * 0.15
            + category_fit * 0.15
            + layout_idea * 0.10
            + copy_space * 0.10
            + production_value * 0.07
            + originality * 0.04
            + risk_control * 0.04
        )
    else:
        value = score * 0.50 + quality_score * 0.25 + text_score * 0.25
    return round(max(0.0, min(100.0, value)), 2)


def quality_grade(score: float) -> str:
    if score >= 82:
        return "A"
    if score >= 70:
        return "B"
    if score >= 58:
        return "C"
    return "D"


def needs_human_review(item: dict[str, Any], weighted_score: float) -> bool:
    decision = str(item.get("review_decision", "")).lower()
    if decision == "rejected":
        return True
    if 55 <= weighted_score < 75:
        return True
    return not decision and weighted_score < 70


def numeric(value: Any) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def summarize_case_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "average_weighted_quality_score": 0,
            "grade_counts": {},
            "needs_human_review_count": 0,
        }
    average = sum(numeric(row.get("weighted_quality_score")) for row in rows) / len(rows)
    grade_counts: dict[str, int] = {}
    for row in rows:
        grade = str(row.get("quality_grade", ""))
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    return {
        "average_weighted_quality_score": round(average, 2),
        "grade_counts": grade_counts,
        "needs_human_review_count": sum(1 for row in rows if row.get("needs_human_review")),
    }


def summarize_quality(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for case in cases for row in case.get("evaluation_rows", [])]
    summary = summarize_case_quality(rows)
    summary["evaluated_assets"] = len(rows)
    summary["cases_with_selected_assets"] = sum(1 for case in cases if case.get("selected_count", 0) > 0)
    return summary


def write_evaluation_table(report: dict[str, Any]) -> None:
    rows = [row for case in report.get("cases", []) for row in case.get("evaluation_rows", [])]
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with (BENCH_ROOT / "benchmark-evaluation.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    write_json(BENCH_ROOT / "benchmark-evaluation.json", {"rows": rows})


def write_feedback_template(report: dict[str, Any]) -> None:
    rows = [row for case in report.get("cases", []) for row in case.get("evaluation_rows", [])]
    lines = []
    for row in rows:
        lines.append(json.dumps({
            "file": row.get("image_path", ""),
            "candidate_id": row.get("asset_id", ""),
            "case_id": row.get("case_id", ""),
            "query": row.get("query", ""),
            "decision": "",
            "score": "",
            "notes": "",
            "tags": [],
        }, ensure_ascii=False))
    (BENCH_ROOT / "benchmark-feedback-template.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_markdown_report(report: dict[str, Any]) -> None:
    lines = [
        "# Reference Search Benchmark",
        "",
        f"Benchmark root: `{report['benchmark_root']}`",
        "",
        "Quality summary:",
        "",
        f"- Evaluated assets: `{report.get('quality_summary', {}).get('evaluated_assets', 0)}`",
        f"- Average weighted quality: `{report.get('quality_summary', {}).get('average_weighted_quality_score', 0)}`",
        f"- Needs human review: `{report.get('quality_summary', {}).get('needs_human_review_count', 0)}`",
        "",
    ]
    for case in report.get("cases", []):
        lines.extend([
            f"## {case['case_id']}",
            "",
            f"- Event: {case['event_name']}",
            f"- Selected: {case['selected_count']}",
            f"- Selection method: `{case.get('selection_method', '')}`",
            f"- Avg quality: `{case.get('quality', {}).get('average_weighted_quality_score', 0)}`",
            f"- Human review needed: `{case.get('quality', {}).get('needs_human_review_count', 0)}`",
            "",
            "Queries:",
            "",
        ])
        for query in case.get("queries", [])[:4]:
            lines.append(f"- `{query}`")
        lines.append("")
        for item in case.get("selected", []):
            image_path = Path(case["run_dir"]) / item["relative_path"]
            lines.extend([
                f"![{case['case_id']} {item['asset_id']}]({image_path.as_posix()})",
                "",
                f"- score: `{item.get('score')}` / quality: `{item.get('quality_score')}` / text: `{item.get('text_relevance_score')}`",
                f"- review: `{item.get('review_decision') or '-'}` / review_score: `{item.get('review_score') or '-'}` / event: `{item.get('event_fit') or '-'}` / category: `{item.get('category_fit') or '-'}`",
                f"- query: `{item.get('query')}`",
                "",
            ])
        if case.get("evaluation_rows"):
            lines.extend(["Evaluation rows:", ""])
            for row in case.get("evaluation_rows", []):
                lines.append(
                    f"- `{row.get('asset_id')}` grade `{row.get('quality_grade')}` "
                    f"weighted `{row.get('weighted_quality_score')}` "
                    f"human_review `{row.get('needs_human_review')}`"
                )
            lines.append("")
    (BENCH_ROOT / "benchmark-report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
