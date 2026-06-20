"""Build and retrieve abstract advertising strategy patterns from Meta ads."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = ROOT / "references" / "meta_ads" / "searches"
DEFAULT_LIBRARY_PATH = ROOT / "design_brain_wiki" / "ad_strategy" / "meta-ad-strategy-library.json"

BOILERPLATE_MARKERS = {
    "활성", "플랫폼", "드롭다운 열기", "광고 상세 정보 보기", "광고",
    "더 알아보기", "구매하기", "shop now", "learn more", "contact us",
}
CTA_TERMS = {"더 알아보기", "구매하기", "shop now", "learn more", "가입하기", "contact us"}


def build_library(source_root: Path = DEFAULT_SOURCE_ROOT) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(source_root.glob("*/collected-ads.json")) if source_root.exists() else []:
        payload = _read_json(path)
        query = str(payload.get("query") or "")
        for item in payload.get("items", []):
            record = extract_strategy_record(item, query=query, source_path=path)
            if not record or record["source"]["copyHash"] in seen:
                continue
            seen.add(record["source"]["copyHash"])
            records.append(record)
    summary = summarize_patterns(records)
    return {
        "schemaVersion": "0.1.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "source": "meta_ad_library_collected_copy",
        "copyrightPolicy": "Store abstract strategy patterns; never reuse competitor copy verbatim in generated output.",
        "recordCount": len(records),
        "summary": summary,
        "records": records,
    }


def save_library(payload: dict[str, Any], path: Path = DEFAULT_LIBRARY_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_library(path: Path = DEFAULT_LIBRARY_PATH) -> dict[str, Any]:
    return _read_json(path)


def retrieve_patterns(context: dict[str, Any], *, limit: int = 5, path: Path = DEFAULT_LIBRARY_PATH) -> dict[str, Any]:
    library = load_library(path)
    records = library.get("records", [])
    context_tokens = set(_tokens(_flatten(context)))
    scored = []
    for record in records:
        record_tokens = set(record.get("retrieval", {}).get("tokens", []))
        overlap = len(context_tokens & record_tokens)
        profile_bonus = 4 if record.get("profile") == _detect_profile(_flatten(context)) else 0
        quality = int(record.get("quality", {}).get("strategyUsefulness", 0)) / 20
        score = overlap * 3 + profile_bonus + quality
        if score > 0:
            scored.append((score, record))
    scored.sort(key=lambda item: (-item[0], item[1]["source"]["copyHash"]))
    selected = [record for _, record in scored[:limit]]
    public_patterns = [
        {
            "patternId": item["patternId"],
            "profile": item["profile"],
            "hookType": item["strategy"]["hookType"],
            "persuasionSequence": item["strategy"]["persuasionSequence"],
            "offerMechanics": item["strategy"]["offerMechanics"],
            "ctaType": item["strategy"]["ctaType"],
            "toneTraits": item["strategy"]["toneTraits"],
            "copyBlueprint": item["strategy"]["copyBlueprint"],
            "sourceBrand": item["source"]["brand"],
            "sourceLibraryId": item["source"]["libraryId"],
        }
        for item in selected
    ]
    return {
        "status": "matched" if selected else "empty",
        "libraryPath": str(path.relative_to(ROOT)) if path.exists() else str(path),
        "matchedCount": len(selected),
        "patterns": public_patterns,
        "adaptedConcepts": adapt_patterns(context, public_patterns),
    }


def adapt_patterns(context: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    event = context.get("event_input", context)
    target = str(event.get("target") or "")
    offer = str(event.get("offer") or "")
    required = [str(item) for item in event.get("requiredPhrases", []) if str(item).strip()]
    proposition = required[0] if required else str(event.get("eventName") or "이번 이벤트")
    product = required[1] if len(required) > 1 else "제품"
    situation = _compact_situation(target)
    hook_types = [item.get("hookType") for item in patterns]
    hooks = []
    if "question_or_challenge" in hook_types:
        hooks.append(f"{situation}, 지금 루틴은 괜찮을까요?")
    if "problem_empathy" in hook_types or target:
        hooks.append(f"{situation}. 피부 컨디션이 흔들리는 순간을 위한 {proposition}.")
    if "specific_value" in hook_types and offer:
        hooks.append(f"지금 시작할 이유: {proposition}. {offer}")
    if not hooks:
        hooks.append(f"{situation}을 위한 {proposition}.")
    return {
        "campaignArchitecture": [
            "타깃이 겪는 구체적인 순간으로 시작한다.",
            f"해결 프레임을 제안한다: {proposition}.",
            f"제품 역할과 사용 맥락을 설명한다: {product}.",
            f"혜택은 마지막 전환 이유로 제시한다: {offer}" if offer else "부담 없는 행동 제안으로 마무리한다.",
        ],
        "headlineDirections": _dedupe_text(hooks)[:3],
        "channelCopyDirections": {
            "instagram_cardnews": _dedupe_text(hooks)[:1] + [f"문제 인식 → {proposition} → {product} 역할 → 혜택 순서로 전개한다."],
            "instagram_feed": [f"{hooks[0]} 한 장에서 {product}의 역할까지 연결한다."],
            "blog_thumbnail": [f"{situation}: {proposition} 루틴 가이드"],
            "blog_inline_image": [f"루틴 안에서 언제, 왜 사용하는지 단계로 보여준다: {product}."],
        },
    }


def extract_strategy_record(item: dict[str, Any], *, query: str, source_path: Path) -> dict[str, Any] | None:
    raw_copy = str(item.get("copy") or "")
    lines = clean_ad_copy_lines(raw_copy, brand=str(item.get("brand") or ""), cta=str(item.get("cta") or ""))
    if len(lines) < 2:
        return None
    joined = " ".join(lines)
    copy_hash = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    hook_type = detect_hook_type(lines[0], joined)
    offer_mechanics = detect_offer_mechanics(joined)
    sequence = detect_persuasion_sequence(lines, hook_type, offer_mechanics)
    cta_type = detect_cta_type(str(item.get("cta") or ""), joined)
    tone_traits = detect_tone_traits(joined)
    profile = _detect_profile(" ".join([query, joined]))
    return {
        "patternId": f"meta_strategy_{copy_hash[:12]}",
        "profile": profile,
        "strategy": {
            "hookType": hook_type,
            "persuasionSequence": sequence,
            "offerMechanics": offer_mechanics,
            "ctaType": cta_type,
            "toneTraits": tone_traits,
            "copyBlueprint": blueprint_for(hook_type, sequence, offer_mechanics, cta_type),
        },
        "quality": {
            "strategyUsefulness": min(100, 45 + len(set(sequence)) * 10 + len(offer_mechanics) * 8),
            "lineCount": len(lines),
        },
        "retrieval": {
            "query": query,
            "tokens": sorted(set(_tokens(" ".join([query, joined, profile])))),
        },
        "source": {
            "brand": item.get("brand", ""),
            "libraryId": item.get("libraryId", ""),
            "copyHash": copy_hash,
            "sourceFile": _relative_source_path(source_path),
        },
    }


def clean_ad_copy_lines(raw: str, *, brand: str = "", cta: str = "") -> list[str]:
    result = []
    for raw_line in raw.replace("\u200b", "").splitlines():
        line = raw_line.strip(" \t-")
        lowered = line.lower()
        if not line or line == brand or line == cta or lowered in BOILERPLATE_MARKERS:
            continue
        if re.search(r"(library id|라이브러리 id|게재 시작함|제품분류|제품번호|https?://|^[A-Z0-9.-]+\.(COM|CO\.KR)$)", line, re.I):
            continue
        if line.startswith("#") or len(line) > 180:
            continue
        result.append(line)
    return result[:12]


def detect_hook_type(first_line: str, text: str) -> str:
    if "?" in first_line or any(term in first_line for term in ("왜", "혹시", "없잖", "아직")):
        return "question_or_challenge"
    if re.search(r"\d|%|ppm|만원|개월", first_line, re.I):
        return "specific_value"
    if any(term in text for term in ("무료", "증정", "할인", "환불", "단독", "한정")):
        return "offer_first"
    if any(term in first_line for term in ("피부", "속당김", "트러블", "고민", "번들")):
        return "problem_empathy"
    if any(term in first_line for term in ("입점", "출시", "공개", "런칭", "시작")):
        return "news_announcement"
    return "brand_statement"


def detect_offer_mechanics(text: str) -> list[str]:
    mapping = {
        "gift_with_purchase": ("증정", "사은품", "무료"),
        "discount": ("할인", "%", "특가", "만원대"),
        "risk_reversal": ("환불", "보장"),
        "exclusivity": ("단독", "오직", "한정"),
        "bundle_value": ("세트", "대용량", "개월치", "기획"),
        "trial": ("체험", "샘플", "키트"),
    }
    return [key for key, terms in mapping.items() if any(term in text for term in terms)]


def detect_persuasion_sequence(lines: list[str], hook_type: str, offers: list[str]) -> list[str]:
    text = " ".join(lines)
    sequence = ["hook"]
    if hook_type in {"problem_empathy", "question_or_challenge"}:
        sequence.append("problem_recognition")
    if any(term in text for term in ("기술", "성분", "ppm", "비건", "세라마이드", "히알루론")):
        sequence.append("reason_to_believe")
    if any(term in text for term in ("매일", "루틴", "써", "사용", "케어")):
        sequence.append("usage_or_routine")
    if offers:
        sequence.append("offer")
    sequence.append("cta")
    return sequence


def detect_cta_type(cta: str, text: str) -> str:
    value = f"{cta} {text}".lower()
    if any(term in value for term in ("구매", "shop now")):
        return "purchase"
    if any(term in value for term in ("가입", "신청", "apply", "sign up")):
        return "apply"
    if any(term in value for term in ("더 알아보기", "learn more")):
        return "learn_more"
    return "soft_action"


def detect_tone_traits(text: str) -> list[str]:
    traits = []
    if re.search(r"\d|%|ppm|만원|개월", text, re.I):
        traits.append("specific")
    if any(term in text for term in ("안 써볼 이유", "미쳤", "잖아요", "오직 지금")):
        traits.append("conversational")
    if any(term in text for term in ("기술", "성분", "투명", "비건")):
        traits.append("credible")
    if any(term in text for term in ("특별", "단독", "한정", "오직")):
        traits.append("exclusive")
    return traits or ["direct"]


def blueprint_for(hook_type: str, sequence: list[str], offers: list[str], cta_type: str) -> list[str]:
    labels = {
        "hook": f"{hook_type} 방식으로 첫 문장을 연다",
        "problem_recognition": "고객이 겪는 구체적인 상황을 짚는다",
        "reason_to_believe": "제품을 믿을 이유를 한 가지 근거로 설명한다",
        "usage_or_routine": "일상에서 사용할 장면이나 루틴을 제안한다",
        "offer": f"혜택을 전환 이유로 제시한다: {', '.join(offers)}",
        "cta": f"{cta_type} 행동으로 마무리한다",
    }
    return [labels[item] for item in sequence]


def summarize_patterns(records: list[dict[str, Any]]) -> dict[str, Any]:
    hooks = Counter(record["strategy"]["hookType"] for record in records)
    offers = Counter(value for record in records for value in record["strategy"]["offerMechanics"])
    sequences = Counter(" > ".join(record["strategy"]["persuasionSequence"]) for record in records)
    return {
        "hookTypes": dict(hooks.most_common()),
        "offerMechanics": dict(offers.most_common()),
        "topPersuasionSequences": dict(sequences.most_common(10)),
    }


def _detect_profile(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ("스킨케어", "세럼", "앰플", "크림", "피부", "beauty", "skincare")):
        return "cosmetics_skincare"
    if any(term in lowered for term in ("주얼리", "jewelry", "다이아", "목걸이", "반지")):
        return "jewelry_luxury"
    return "general"


def _tokens(text: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
        if token.lower() not in {"이벤트", "광고", "제품", "중심", "안내"}
    ]


def _compact_situation(target: str) -> str:
    if not target:
        return "일상 속 피부 고민이 느껴지는 순간"
    text = re.sub(r"\s+", " ", target).strip()
    text = re.sub(r"\s*\d{2}~\d{2}세.*$", "", text)
    text = re.sub(r"(속당김과 민감함을|속당김을|민감함을)\s*느끼는$", r"\1 느낄 때", text)
    return text[:55].rstrip(" ,.")


def _dedupe_text(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return str(value or "")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _relative_source_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)
