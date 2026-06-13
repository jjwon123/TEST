"""Run Senior Designer Brain Wiki reference judge sample tests.

The test uses text descriptions as controlled stand-ins for visual references.
It verifies whether the wiki rubric can produce specific selected/shortlist/
rejected decisions and non-generic senior-designer feedback.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TEST_SET_PATH = ROOT / "design_brain_wiki" / "tests" / "reference_judge_sample_set.json"
RUBRIC_PATH = ROOT / "design_brain_wiki" / "REFERENCE_JUDGE_RUBRIC.json"
OUTPUT_DIR = ROOT / "design_brain_wiki" / "tests" / "output"


PROFILE_RULES: dict[str, dict[str, Any]] = {
    "bullion_investment": {
        "strong": {"gold_bar", "gold_coin", "financial_consultation", "wealth_management", "product_identity", "premium", "calm_trust", "minimal_layout", "dark_navy", "copy_space", "blank_headline_area", "cta_space", "no_fake_text"},
        "partial": {"abstract_background", "decorative", "tight_crop", "realistic_metal", "weak_product_identity", "low_copy_space"},
        "bad": {"mascot", "cute", "toy_3d", "camping", "picnic", "fake_text", "casino", "jackpot", "unreadable_typography", "hype", "not_financial", "not_trustworthy"},
        "selected_min_strong": 5,
        "risk_max": 0,
        "role_names": {
            "product": {"gold_bar", "gold_coin", "product_identity", "realistic_metal"},
            "mood": {"financial_consultation", "wealth_management", "calm_trust", "premium", "dark_navy"},
            "layout": {"blank_headline_area", "copy_space", "cta_space", "minimal_layout"}
        },
        "selected_use": "금 투자 상담 카드뉴스 메인 또는 상담 신청 배너",
        "shortlist_use": "제품 질감, 금융 무드, 포스터 레이아웃 중 일부 보조 기준",
        "industry_standard": "금융 투자 브랜드의 신뢰와 프리미엄 상담 톤"
    },
    "cosmetics_skincare": {
        "strong": {"clean", "serum", "product_identity", "clinical_warm", "blank_headline_area", "efficacy_trust", "soft_light", "texture", "ingredient", "benefit_copy_space", "dermocosmetic", "layout_zone", "premium"},
        "partial": {"spa", "pastel", "fresh", "flowers", "weak_product_identity", "weak_efficacy_trust", "no_package", "low_copy_space", "partial_reference", "clean_light"},
        "bad": {"fake_text", "before_after", "medical_claim", "unrealistic_skin", "claim_risk", "trust_risk", "cheap_discount", "crowded_layout", "unreadable_typography", "low_premium", "water_splash"},
        "selected_min_strong": 5,
        "risk_max": 0,
        "role_names": {
            "product": {"serum", "product_identity", "texture", "ingredient"},
            "mood": {"clinical_warm", "efficacy_trust", "dermocosmetic", "clean", "premium"},
            "layout": {"blank_headline_area", "benefit_copy_space", "layout_zone"}
        },
        "selected_use": "스킨케어 신제품 카드뉴스 메인 또는 랜딩 히어로",
        "shortlist_use": "제형감, 성분 무드, 보조 배경 기준",
        "industry_standard": "화장품 효능 신뢰와 깨끗한 제품 설득력"
    },
    "jewelry_luxury": {
        "strong": {"diamond", "ring", "gold_necklace", "precise_highlight", "controlled_shadow", "negative_space", "material_quality", "premium", "warm_directional_light", "copy_space", "restrained_background"},
        "partial": {"gemstone", "sparkle", "material_detail", "tight_crop", "low_copy_space", "partial_reference", "hand_pose", "soft_light", "weak_product_focus", "elegant_mood"},
        "bad": {"plastic_material", "fantasy_render", "rainbow_glow", "cheap_gift_box", "excessive_sparkle", "low_credibility", "fake_text", "discount_badge", "crowded_layout", "cheap_signal", "low_whitespace", "sale_poster"},
        "selected_min_strong": 5,
        "risk_max": 0,
        "role_names": {
            "product": {"diamond", "ring", "gold_necklace", "material_quality", "gemstone"},
            "mood": {"premium", "warm_directional_light", "elegant_mood", "controlled_shadow"},
            "layout": {"negative_space", "copy_space", "restrained_background"}
        },
        "selected_use": "럭셔리 컬렉션 캠페인 메인 비주얼 또는 배너 히어로",
        "shortlist_use": "소재 디테일, 조명, 착용 무드 보조 기준",
        "industry_standard": "주얼리 럭셔리의 소재 신뢰와 절제된 프리미엄 톤"
    },
}


GENERIC_BAD_PHRASES = [
    "브랜드와 잘 맞습니다",
    "고급스럽습니다",
    "시각적으로 좋습니다",
]


def main() -> None:
    test_set = _read_json(TEST_SET_PATH)
    rubric = _read_json(RUBRIC_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    profile_reports = []
    for profile_case in test_set["profiles"]:
        profile_reports.append(_evaluate_profile(profile_case, rubric))

    total = sum(item["summary"]["total"] for item in profile_reports)
    correct = sum(item["summary"]["correct"] for item in profile_reports)
    deep = sum(item["summary"]["deepFeedback"] for item in profile_reports)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "testSet": str(TEST_SET_PATH.relative_to(ROOT)),
        "rubric": str(RUBRIC_PATH.relative_to(ROOT)),
        "summary": {
            "profiles": len(profile_reports),
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total, 3) if total else 0,
            "deepFeedback": deep,
            "feedbackDepthRate": round(deep / total, 3) if total else 0,
            "status": "pass" if total and correct == total and deep == total else "needs_review",
        },
        "profiles": profile_reports,
        "nextActions": _next_actions(profile_reports),
    }
    _write_json(OUTPUT_DIR / "reference-judge-test-report.json", report)
    _write_text(OUTPUT_DIR / "reference-judge-test-report.md", _render_markdown(report))
    print(f"OK reference judge wiki test: {report['summary']['status']} total={total} accuracy={report['summary']['accuracy']}")


def _evaluate_profile(profile_case: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    profile = profile_case["profile"]
    results = []
    for candidate in profile_case["candidates"]:
        decision = _judge_candidate(profile, candidate, rubric)
        feedback = _feedback(profile, candidate, decision)
        depth = _feedback_depth(feedback)
        expected = candidate["expectedDecision"]
        results.append({
            "id": candidate["id"],
            "title": candidate["title"],
            "expectedDecision": expected,
            "actualDecision": decision["decision"],
            "correct": decision["decision"] == expected,
            "scores": decision["scores"],
            "signals": candidate.get("signals", []),
            "role": decision["role"],
            "feedback": feedback,
            "feedbackDepth": depth,
            "wikiSources": profile_case.get("wikiSources", []),
        })
    total = len(results)
    correct = sum(1 for item in results if item["correct"])
    deep = sum(1 for item in results if item["feedbackDepth"]["pass"])
    return {
        "profile": profile,
        "eventContext": profile_case.get("eventContext", ""),
        "wikiSources": profile_case.get("wikiSources", []),
        "summary": {
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total, 3) if total else 0,
            "deepFeedback": deep,
            "feedbackDepthRate": round(deep / total, 3) if total else 0,
        },
        "results": results,
    }


def _judge_candidate(profile: str, candidate: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    rules = PROFILE_RULES[profile]
    signals = set(candidate.get("signals", []))
    strong = signals & rules["strong"]
    partial = signals & rules["partial"]
    bad = signals & rules["bad"]
    copy_signals = {"blank_headline_area", "copy_space", "cta_space", "benefit_copy_space", "negative_space", "layout_zone"} & signals
    product_signals = rules["role_names"]["product"] & signals
    mood_signals = rules["role_names"]["mood"] & signals
    layout_signals = rules["role_names"]["layout"] & signals
    cheap_risk = min(10, len(bad) * 2)
    typo_risk = 8 if {"fake_text", "unreadable_typography"} & signals else 0
    scores = {
        "brandFit": min(10, 4 + len(strong) + len(mood_signals) - len(bad)),
        "eventFit": min(10, 4 + len(strong) + len(layout_signals) - len(bad)),
        "industryTrust": max(0, min(10, 5 + len(mood_signals) + len(product_signals) - len(bad) * 2)),
        "brandSystemFit": min(10, 4 + len(layout_signals) + len(copy_signals)),
        "scalability": min(10, 4 + len(layout_signals) + len(copy_signals) - (1 if "tight_crop" in signals else 0)),
        "distinctiveness": min(10, 5 + len(product_signals) + (1 if "premium" in signals else 0)),
        "premiumSignal": max(0, min(10, 4 + len(strong) - len(bad))),
        "cheapSignalRisk": cheap_risk,
        "layoutUsability": max(0, min(10, 5 + len(layout_signals) + len(copy_signals) - (2 if "low_copy_space" in signals else 0))),
        "copySpace": max(0, min(10, 3 + len(copy_signals) * 3 - (4 if "low_copy_space" in signals else 0))),
        "visualHierarchy": max(0, min(10, 5 + len(layout_signals) - (2 if "crowded_layout" in signals else 0))),
        "typographyRisk": typo_risk,
        "colorDiscipline": max(0, min(10, 6 + (1 if "restrained_background" in signals or "dark_navy" in signals else 0) - len(bad))),
        "channelFit": max(0, min(10, 4 + len(layout_signals) + len(copy_signals) - (2 if "tight_crop" in signals else 0))),
    }
    selected_gate = rubric.get("selectedGate", {})
    decision = "shortlist"
    if bad or scores["cheapSignalRisk"] > selected_gate.get("cheapSignalRiskMax", 3) or scores["typographyRisk"] > selected_gate.get("typographyRiskMax", 3):
        decision = "rejected"
    elif (
        len(strong) >= rules["selected_min_strong"]
        and scores["brandFit"] >= selected_gate.get("brandFit", 8)
        and scores["eventFit"] >= selected_gate.get("eventFit", 8)
        and scores["industryTrust"] >= selected_gate.get("industryTrust", 7)
        and (scores["layoutUsability"] >= selected_gate.get("layoutUsability", 7) or (product_signals and mood_signals and copy_signals))
        and scores["copySpace"] >= selected_gate.get("copySpace", 6)
    ):
        decision = "selected"
    return {
        "decision": decision,
        "scores": scores,
        "role": _role(product_signals, mood_signals, layout_signals),
        "strongSignals": sorted(strong),
        "partialSignals": sorted(partial),
        "badSignals": sorted(bad),
    }


def _feedback(profile: str, candidate: dict[str, Any], decision: dict[str, Any]) -> str:
    rules = PROFILE_RULES[profile]
    role = decision["role"]
    strong = decision["strongSignals"]
    partial = decision["partialSignals"]
    bad = decision["badSignals"]
    scores = decision["scores"]
    if decision["decision"] == "selected":
        return (
            f"이 레퍼런스는 {', '.join(strong[:3])} 신호가 분명해서 {rules['industry_standard']}에 맞습니다. "
            f"{role} 기준이 함께 살아 있고 copySpace {scores['copySpace']}점, layoutUsability {scores['layoutUsability']}점이라 "
            f"{rules['selected_use']}로 확장하기 좋습니다."
        )
    if decision["decision"] == "shortlist":
        gap = _main_gap(scores, partial)
        return (
            f"이 레퍼런스는 {role} 관점에서는 참고 가치가 있지만 {gap} 때문에 selected로 올리기에는 부족합니다. "
            f"{rules['shortlist_use']}으로만 쓰고, 메인 방향으로 쓰려면 카피 여백과 업종 신뢰 신호를 보강해야 합니다."
        )
    return (
        f"이 레퍼런스는 {', '.join(bad[:4])} 신호가 강해 {rules['industry_standard']}을 통과하지 못합니다. "
        f"특히 cheapSignalRisk {scores['cheapSignalRisk']}점, typographyRisk {scores['typographyRisk']}점이라 "
        f"다음 검색/생성에서는 해당 방향을 rejected seed로 차단해야 합니다."
    )


def _feedback_depth(feedback: str) -> dict[str, Any]:
    generic_hits = [phrase for phrase in GENERIC_BAD_PHRASES if phrase in feedback]
    criteria_terms = [
        "copySpace", "layoutUsability", "cheapSignalRisk", "typographyRisk",
        "제품", "무드", "레이아웃", "카피", "신뢰", "업종", "selected", "shortlist", "rejected",
    ]
    criteria_hits = [term for term in criteria_terms if term in feedback]
    use_case_terms = ["카드뉴스", "배너", "랜딩", "메인", "보조", "검색", "생성"]
    use_case_hits = [term for term in use_case_terms if term in feedback]
    return {
        "pass": len(feedback) >= 90 and len(criteria_hits) >= 3 and bool(use_case_hits) and not generic_hits,
        "length": len(feedback),
        "criteriaHits": criteria_hits,
        "useCaseHits": use_case_hits,
        "genericHits": generic_hits,
    }


def _role(product: set[str], mood: set[str], layout: set[str]) -> str:
    roles = []
    if product:
        roles.append("제품 정체성")
    if mood:
        roles.append("무드/신뢰")
    if layout:
        roles.append("레이아웃/카피 여백")
    return ", ".join(roles) if roles else "부분 참고"


def _main_gap(scores: dict[str, int], partial: list[str]) -> str:
    if scores.get("copySpace", 0) < 6:
        return "카피 여백이 부족합니다"
    if scores.get("industryTrust", 0) < 7:
        return "업종 신뢰감이 약합니다"
    if partial:
        return f"{', '.join(partial[:2])} 신호가 있어 역할이 제한됩니다"
    return "브랜드 시스템으로 확장할 근거가 부족합니다"


def _next_actions(profile_reports: list[dict[str, Any]]) -> list[str]:
    actions = []
    for profile in profile_reports:
        if profile["summary"]["accuracy"] < 1:
            actions.append(f"{profile['profile']}: selected/shortlist/rejected rubric 보강")
        if profile["summary"]["feedbackDepthRate"] < 1:
            actions.append(f"{profile['profile']}: feedback phrase와 industry playbook 보강")
    if not actions:
        actions.append("샘플 테스트는 통과. 다음 단계는 이 evaluator를 03_reference_research report에 연결.")
    return actions


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Reference Judge Wiki Test Report",
        "",
        f"- Status: {report['summary']['status']}",
        f"- Total: {report['summary']['total']}",
        f"- Accuracy: {report['summary']['accuracy']}",
        f"- Feedback depth rate: {report['summary']['feedbackDepthRate']}",
        f"- Test set: `{report['testSet']}`",
        f"- Rubric: `{report['rubric']}`",
        "",
    ]
    for profile in report["profiles"]:
        lines.extend([
            f"## {profile['profile']}",
            "",
            f"- Context: {profile['eventContext']}",
            f"- Accuracy: {profile['summary']['accuracy']}",
            f"- Feedback depth rate: {profile['summary']['feedbackDepthRate']}",
            "- Wiki sources:",
            *[f"  - `{source}`" for source in profile["wikiSources"]],
            "",
            "| Candidate | Expected | Actual | Feedback depth | Senior designer feedback |",
            "|---|---:|---:|---:|---|",
        ])
        for item in profile["results"]:
            feedback = item["feedback"].replace("|", "/")
            depth = "pass" if item["feedbackDepth"]["pass"] else "fail"
            lines.append(f"| `{item['id']}` | {item['expectedDecision']} | {item['actualDecision']} | {depth} | {feedback} |")
        lines.append("")
    lines.extend(["## Next Actions", "", *[f"- {item}" for item in report["nextActions"]], ""])
    return "\n".join(lines)


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
