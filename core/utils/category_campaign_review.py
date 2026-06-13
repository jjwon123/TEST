"""Category-specific campaign risk review.

This module turns the category-campaign-review skill references into a
deterministic pipeline gate. The detailed markdown files remain the human/audit
reference, while this code owns the yes/no checks that stage handlers can
apply consistently.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = ROOT / "skills" / "category-campaign-review" / "references"


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    reference_file: str
    keywords: tuple[str, ...]


CATEGORIES = (
    Category(
        id="skincare",
        label="Skincare",
        reference_file="skincare.md",
        keywords=("스킨케어", "피부", "앰플", "세럼", "진정", "수분", "클린뷰티", "화장품", "derma", "beauty"),
    ),
    Category(
        id="lab_grown_diamonds",
        label="Lab-Grown Diamonds",
        reference_file="lab-grown-diamonds.md",
        keywords=("랩다이아", "랩그로운", "lab-grown", "diamond", "다이아", "주얼리", "jewelry", "jewellery"),
    ),
    Category(
        id="gold_exchange",
        label="Gold Exchange / Precious Metals",
        reference_file="gold-exchange.md",
        keywords=("금거래소", "골드바", "실물 금", "금 투자", "금시세", "은화", "은 투자", "precious metal", "bullion"),
    ),
)


def detect_category(payload: dict[str, Any]) -> dict[str, Any]:
    text = _flatten_text(payload).lower()
    matches = []
    for category in CATEGORIES:
        hit_terms = [term for term in category.keywords if term.lower() in text]
        if hit_terms:
            matches.append({
                "category_id": category.id,
                "label": category.label,
                "matched_terms": hit_terms,
                "reference_path": str((REFERENCE_DIR / category.reference_file).relative_to(ROOT)),
            })

    if not matches:
        return {
            "detected": False,
            "category_id": "none",
            "label": "",
            "matched_terms": [],
            "reference_path": "",
            "available_categories": [category.id for category in CATEGORIES],
        }

    selected = matches[0]
    return {
        "detected": True,
        "category_id": selected["category_id"],
        "label": selected["label"],
        "matched_terms": selected["matched_terms"],
        "reference_path": selected["reference_path"],
        "multiple_matches": matches[1:],
    }


def evaluate_category_risk(
    *,
    brief: dict[str, Any],
    deliverables: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    detection = brief.get("quality_assessment", {}).get("category_detection")
    if not isinstance(detection, dict) or not detection.get("detected"):
        detection = detect_category(brief)

    category_id = detection.get("category_id", "none")
    if category_id == "none":
        return {
            "detected": False,
            "category_id": "none",
            "blocking": False,
            "triggered_patterns": [],
            "judgment_questions": [],
            "repair_required": [],
            "warnings": [],
            "reference_path": "",
        }

    context = _context(brief, deliverables or [])
    if category_id == "skincare":
        review = _skincare_review(context)
    elif category_id == "lab_grown_diamonds":
        review = _lab_diamond_review(context)
    elif category_id == "gold_exchange":
        review = _gold_exchange_review(context)
    else:
        review = {
            "triggered_patterns": [],
            "judgment_questions": [],
            "repair_required": [],
            "warnings": [],
        }

    blocking = any(not item["answer"] and item.get("blocking", False) for item in review["judgment_questions"])
    severity_rank = {
        "regulatory": 3,
        "substantiation": 3,
        "trust": 3,
        "positioning": 2,
        "persona": 2,
        "channel": 1,
    }
    max_severity = max(
        [severity_rank.get(item.get("severity", ""), 0) for item in review["triggered_patterns"]]
        or [0]
    )
    return {
        "detected": True,
        "category_id": category_id,
        "label": detection.get("label", ""),
        "reference_path": detection.get("reference_path", ""),
        "matched_terms": detection.get("matched_terms", []),
        "blocking": blocking,
        "severity": "blocking" if blocking else ("warning" if review["warnings"] else "clear"),
        "severity_score": max_severity,
        "triggered_patterns": review["triggered_patterns"],
        "judgment_questions": review["judgment_questions"],
        "repair_required": review["repair_required"],
        "warnings": review["warnings"],
    }


def _context(brief: dict[str, Any], deliverables: list[dict[str, Any]]) -> dict[str, str]:
    fields = [
        brief.get("event_name", ""),
        brief.get("brand", {}).get("name", ""),
        brief.get("objective", {}).get("primary", ""),
        brief.get("target", {}).get("summary", ""),
        brief.get("offer", {}).get("summary", ""),
        " ".join(brief.get("channels", [])),
        " ".join(brief.get("core_messages", [])),
        " ".join(brief.get("constraints", {}).get("required_phrases", [])),
        " ".join(brief.get("content_direction", {}).get("visual_direction", [])),
        " ".join(str(item.get("copy_intent", "")) for item in deliverables),
    ]
    text = " ".join(str(field) for field in fields if field).lower()
    return {
        "text": text,
        "target": str(brief.get("target", {}).get("summary", "")).lower(),
        "channels": " ".join(brief.get("channels", [])).lower(),
        "brand": str(brief.get("brand", {}).get("name", "")).lower(),
    }


def _skincare_review(context: dict[str, str]) -> dict[str, Any]:
    text = context["text"]
    target = context["target"]
    channels = context["channels"]
    triggered = []
    questions = []
    repairs = []
    warnings = []

    vague_target = _has_any(target, ("mz", "m.z", "2030", "젊은", "여성")) and not _has_any(
        target, ("민감", "여드름", "트러블", "건조", "광채", "흉터", "환절기", "루틴")
    )
    _add_question(questions, "타깃이 CEP/피부 고민 기준으로 정의됐는가?", not vague_target, True)
    if vague_target:
        triggered.append(_pattern("S1", "persona", "타깃이 인구통계 중심으로만 정의됨"))
        repairs.append("타깃을 CEP, 피부 고민, 가격대, 정보 탐색 채널 기준으로 재정의해야 합니다.")

    drug_claim = _has_any(text, ("완치", "치료", "재생", "dna", "유전자", "기적", "100% 보장", "clinically proven"))
    _add_question(questions, "효능 주장이 화장품 범위를 넘지 않고 입증 가능하게 표현됐는가?", not drug_claim, True)
    if drug_claim:
        triggered.append(_pattern("S3", "regulatory", "drug claim 또는 과대 효능 주장 가능성"))
        repairs.append("치료/재생/보장형 표현을 제거하거나 제품별 입증 자료를 첨부해야 합니다.")

    clean_overclaim = _has_any(text, ("무첨가", "free", "clean", "클린")) and _has_any(text, ("유해", "독성", "화학"))
    _add_question(questions, "성분 메시지가 공포 기반이 아니라 결과와 근거 중심인가?", not clean_overclaim, True)
    if clean_overclaim:
        triggered.append(_pattern("S2", "substantiation", "성분 공포 또는 클린뷰티 과잉 주장 가능성"))
        repairs.append("성분 폄하형 메시지를 제거하고 단일 효능과 근거 중심으로 재작성해야 합니다.")

    same_creative = "instagram" in channels and "tiktok" in channels
    _add_question(questions, "채널별 콘텐츠 문법이 분리되어 있는가?", not same_creative, False)
    if same_creative:
        triggered.append(_pattern("S7", "channel", "Instagram/TikTok 동일 문법 운영 위험"))
        warnings.append("Instagram은 미학, TikTok은 효능 검증/검색형 콘텐츠로 분리하는 것이 안전합니다.")

    return _review(triggered, questions, repairs, warnings)


def _lab_diamond_review(context: dict[str, str]) -> dict[str, Any]:
    text = context["text"]
    target = context["target"]
    triggered = []
    questions = []
    repairs = []
    warnings = []

    positioning_terms = sum(
        1 for terms in (
            ("럭셔리", "프리미엄", "forever", "영원"),
            ("저렴", "가성비", "할인", "가격"),
            ("친환경", "지속가능", "윤리"),
            ("기술", "혁신"),
        )
        if _has_any(text, terms)
    )
    clear_positioning = positioning_terms <= 1
    _add_question(questions, "단일 포지셔닝을 선택했는가?", clear_positioning, True)
    if not clear_positioning:
        triggered.append(_pattern("L3", "positioning", "럭셔리/가성비/지속가능 메시지 충돌"))
        repairs.append("Fashion accessible luxury, bridal premium alternative, sustainable lifestyle, technology innovation 중 하나로 포지셔닝을 고정해야 합니다.")

    natural_equivalence = _has_any(text, ("천연과 똑같", "천연 동일", "same as natural", "4cs", "gia"))
    _add_question(questions, "천연 다이아와 혼동되는 동등성/등급 표현을 피했는가?", not natural_equivalence, True)
    if natural_equivalence:
        triggered.append(_pattern("L2", "regulatory", "천연 다이아 동등성 또는 GIA/4Cs 혼동 가능성"))
        repairs.append("랩그로운 표기를 명확히 하고 천연 다이아 등급/상징과 혼동되는 표현을 제거해야 합니다.")

    vague_target = _has_any(target, ("mz", "2030", "여성")) and not _has_any(target, ("셀프", "브라이덜", "예비", "vip", "커플", "선물"))
    _add_question(questions, "타깃이 self-gift/bridal/VIP 중 하나로 분리됐는가?", not vague_target, True)
    if vague_target:
        triggered.append(_pattern("L6", "persona", "랩다이아 구매 페르소나 혼합"))
        repairs.append("self-gift, bridal couple, VIP/collector 중 하나로 타깃과 채널을 분리해야 합니다.")

    green_claim = _has_any(text, ("친환경", "지속가능", "윤리"))
    _add_question(questions, "환경/원산지 주장이 검증 자료를 전제로 하는가?", not green_claim, False)
    if green_claim:
        triggered.append(_pattern("L5", "substantiation", "환경 우월 주장 입증 필요"))
        warnings.append("친환경/지속가능 메시지는 원산지, 전력, 인증 근거 없이는 greenwashing 리스크가 있습니다.")

    return _review(triggered, questions, repairs, warnings)


def _gold_exchange_review(context: dict[str, str]) -> dict[str, Any]:
    text = context["text"]
    target = context["target"]
    channels = context["channels"]
    triggered = []
    questions = []
    repairs = []
    warnings = []

    return_claim = _has_any(text, ("수익 보장", "원금 보장", "무조건 수익", "두 배", "고수익", "안전한 수익"))
    _add_question(questions, "수익률/원금/위기 수익 보장 암시가 없는가?", not return_claim, True)
    if return_claim:
        triggered.append(_pattern("G1", "regulatory", "수익 또는 원금 보장형 투자 광고 위험"))
        repairs.append("수익/원금/보장 표현을 제거하고 가격 투명성, 인증, 교육 메시지로 전환해야 합니다.")

    fear_claim = _has_any(text, ("달러 붕괴", "은행 동결", "위기", "폭락", "마지막 기회", "공포"))
    _add_question(questions, "공포 기반 투자 권유 표현을 피했는가?", not fear_claim, True)
    if fear_claim:
        triggered.append(_pattern("G3", "regulatory", "고령층 공포 마케팅 또는 위기 조장 위험"))
        repairs.append("거시경제 공포를 이용한 권유를 제거하고 분산투자 교육 맥락으로 낮춰야 합니다.")

    trust_signal = _has_any(text, ("krx", "lbma", "조폐공사", "품질보증", "인증", "시세", "부가세", "수수료", "마크업"))
    _add_question(questions, "신뢰 신호와 가격/수수료/세금 투명성이 보이는가?", trust_signal, True)
    if not trust_signal:
        triggered.append(_pattern("G7", "trust", "신뢰 비대칭 시장에서 신뢰 신호 부족"))
        repairs.append("KRX/LBMA/조폐공사/시세/부가세/수수료 등 신뢰와 가격 투명성 정보를 명시해야 합니다.")

    persona_defined = _has_any(target, ("투자", "자산", "선물", "수집", "기념", "신규 진입", "예비 고객"))
    _add_question(questions, "투자자/신규 진입자/선물 구매자/컬렉터 중 타깃이 분리됐는가?", persona_defined, True)
    if not persona_defined:
        triggered.append(_pattern("G9", "persona", "금거래소 CEP/타깃 혼합"))
        repairs.append("투자자, 자산형성형 신규 진입자, 선물 구매자, 컬렉터 중 하나로 타깃을 분리해야 합니다.")

    social_first = ("instagram" in channels or "tiktok" in channels) and not _has_any(channels, ("blog", "naver", "youtube", "community"))
    _add_question(questions, "채널이 신뢰 구축과 구매 사이클에 맞는가?", not social_first, False)
    if social_first:
        triggered.append(_pattern("G4", "channel", "금거래소 고관여 구매에 SNS 중심 채널 미스매치"))
        warnings.append("금거래소는 검색, 블로그, 유튜브 교육, 오프라인 상담 신뢰 경로가 우선입니다.")

    return _review(triggered, questions, repairs, warnings)


def _review(triggered: list[dict[str, str]], questions: list[dict[str, Any]], repairs: list[str], warnings: list[str]) -> dict[str, Any]:
    return {
        "triggered_patterns": triggered,
        "judgment_questions": questions,
        "repair_required": _dedupe(repairs),
        "warnings": _dedupe(warnings),
    }


def _add_question(items: list[dict[str, Any]], question: str, answer: bool, blocking: bool) -> None:
    items.append({
        "question": question,
        "answer": bool(answer),
        "blocking": blocking,
    })


def _pattern(pattern_id: str, severity: str, reason: str) -> dict[str, str]:
    return {
        "pattern_id": pattern_id,
        "severity": severity,
        "reason": reason,
    }


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle.lower() in text for needle in needles)


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
