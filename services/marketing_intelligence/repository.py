"""MarketingSignal repository and seed collectors."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils.json_io import read_json, write_json
from core.utils.schema_validation import validate_json


ROOT = Path(__file__).resolve().parents[2]
SIGNALS_PATH = ROOT / "design_brain_wiki" / "marketing_signals" / "signals.json"
SCHEMA_PATH = ROOT / "core" / "schemas" / "marketing-signal.schema.json"
DEFAULT_REVIEW_SHEET = ROOT / ".tmp" / "marketing-signals" / "marketing-signal-review-sheet.csv"

DECISIONS = {"unreviewed", "selected", "shortlist", "rejected"}
SELECTED_BLOCKING_RISK_FLAGS = {
    "capture_quality_blocked",
    "raw_html_detected",
    "raw_json_detected",
    "broken_text_suspected",
}
REASON_TAGS = {
    "useful_target",
    "useful_trend",
    "useful_season",
    "useful_channel",
    "useful_objection",
    "useful_proof",
    "useful_offer",
    "too_generic",
    "needs_source",
    "unsupported_claim",
    "brand_mismatch",
    "duplicate",
    "capture_quality_blocked",
    "human_cleaned",
}
REVIEW_FIELDNAMES = [
    "id",
    "decision",
    "industry",
    "topic",
    "sourceType",
    "evidenceType",
    "targetSegment",
    "signalText",
    "normalizedInsight",
    "strength",
    "freshness",
    "confidence",
    "riskFlags",
    "usableFor",
    "reasonTags",
    "reviewNote",
]


TARGET_SEGMENTS = [
    "장마철 속당김을 느끼는 직장인",
    "냉방으로 피부가 건조해지는 사무직 고객",
    "화장 전 들뜸을 줄이고 싶은 20대 후반 고객",
    "민감해진 피부 때문에 성분을 먼저 확인하는 고객",
    "간단한 루틴으로 효과를 느끼고 싶은 바쁜 고객",
    "여름 휴가 전 피부 컨디션을 정리하려는 고객",
    "선물보다 내 피부 관리에 작은 보상을 쓰는 고객",
    "리뷰를 보고 실패 가능성을 줄이고 싶은 고객",
]

TOPICS = [
    "summer_barrier_care",
    "monsoon_hydration",
    "cooling_office_dryness",
    "sensitive_skin_routine",
    "brightening_serum",
    "pore_texture_care",
    "minimal_routine",
    "gift_promotion",
]

PAINS = [
    "습도는 높은데 피부 속은 당긴다고 느낀다",
    "냉방 환경에서 오후가 되면 화장이 뜬다",
    "새 제품을 쓰고 싶지만 민감 반응이 걱정된다",
    "성분과 후기가 많아도 무엇을 골라야 할지 헷갈린다",
    "여러 단계를 바르는 루틴을 오래 유지하기 어렵다",
    "프로모션은 많지만 진짜 필요한 혜택인지 판단하기 어렵다",
]

DESIRES = [
    "루틴을 복잡하게 늘리지 않고 피부 컨디션을 정리하고 싶다",
    "지금 계절에 맞는 선택 기준을 빠르게 알고 싶다",
    "구매 전에 내 상황과 맞는 이유를 확인하고 싶다",
    "강한 효능 주장보다 부담 없는 사용 맥락을 원한다",
    "작은 혜택이라도 지금 시작할 명분이 있으면 움직인다",
]

OBJECTIONS = [
    "또 비슷한 앰플인지 모르겠다는 의심",
    "피부 타입과 맞지 않을까 봐 미루는 마음",
    "할인보다 제품 선택 근거가 부족하다는 불안",
    "지금 사야 할 이유가 약하다는 망설임",
]

SEASONAL_TRIGGERS = [
    "장마철 습도와 실내 냉방의 간극",
    "여름 자외선 이후 칙칙해 보이는 피부 인상",
    "휴가 전후 피부 컨디션 관리 수요",
    "환절기 전 미리 장벽 루틴을 정리하려는 움직임",
]

CHANNEL_PATTERNS = [
    "인스타그램 피드는 첫 문장에서 내 상황을 바로 말할 때 멈춤 가능성이 높다",
    "카드뉴스는 문제 공감 후 선택 기준을 한 장씩 쪼개야 읽힌다",
    "블로그는 제품명보다 고민 키워드로 들어와 근거를 확인한다",
    "배너는 혜택보다 사용 상황이 먼저 잡히면 클릭 이유가 선명해진다",
]


def load_signals(path: Path = SIGNALS_PATH) -> list[dict[str, Any]]:
    payload = read_json(path, default={"signals": []})
    return [item for item in payload.get("signals", []) if isinstance(item, dict)]


def save_signals(signals: list[dict[str, Any]], path: Path = SIGNALS_PATH) -> None:
    schema = read_json(SCHEMA_PATH)
    for signal in signals:
        validate_json(signal, schema, data_label=f"signal {signal.get('id')}", schema_label="marketing-signal.schema.json")
    write_json(path, {
        "schemaVersion": "1.0.0",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
    })


def append_signals(new_signals: list[dict[str, Any]], path: Path = SIGNALS_PATH) -> dict[str, Any]:
    existing = load_signals(path)
    by_id = {item.get("id"): item for item in existing}
    added = 0
    skipped = 0
    for signal in new_signals:
        normalized = normalize_signal(signal)
        if normalized["id"] in by_id:
            skipped += 1
            continue
        by_id[normalized["id"]] = normalized
        added += 1
    ordered = sorted(by_id.values(), key=lambda item: (item.get("collectedAt", ""), item.get("id", "")))
    save_signals(ordered, path)
    return {"path": str(path), "existing": len(existing), "added": added, "skipped": skipped, "total": len(ordered)}


def normalize_signal(signal: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    normalized = {
        **signal,
        "industry": signal.get("industry") or "cosmetics_skincare",
        "sourceType": signal.get("sourceType") or "seed_random",
        "sourceRef": signal.get("sourceRef") or {},
        "collectedAt": signal.get("collectedAt") or now,
        "topic": signal.get("topic") or "general_cosmetics",
        "signalText": str(signal.get("signalText") or "").strip(),
        "normalizedInsight": str(signal.get("normalizedInsight") or "").strip(),
        "targetSegment": str(signal.get("targetSegment") or "").strip(),
        "funnelStage": signal.get("funnelStage") or "awareness",
        "evidenceType": signal.get("evidenceType") or "trend",
        "strength": _clamp_score(signal.get("strength", 3)),
        "freshness": _clamp_score(signal.get("freshness", 3)),
        "confidence": _clamp_score(signal.get("confidence", 2)),
        "riskFlags": _dedupe_strings(signal.get("riskFlags") or []),
        "usableFor": _dedupe_strings(signal.get("usableFor") or ["concept", "copy"]),
        "review": {
            "decision": (signal.get("review") or {}).get("decision") or "unreviewed",
            "reasonTags": _dedupe_strings((signal.get("review") or {}).get("reasonTags") or []),
            "reviewNote": str((signal.get("review") or {}).get("reviewNote") or ""),
        },
    }
    normalized["id"] = signal.get("id") or _signal_id(normalized)
    return normalized


def generate_random_seed_signals(
    *,
    count: int,
    industry: str = "cosmetics_skincare",
    topic: str = "",
    seed: int | None = None,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    generated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    attempts = 0
    max_attempts = max(count * 20, 100)
    while len(generated) < count and attempts < max_attempts:
        attempts += 1
        evidence_type = rng.choice(["pain", "desire", "objection", "timing", "channel_pattern", "trend"])
        selected_topic = topic or rng.choice(TOPICS)
        target = rng.choice(TARGET_SEGMENTS)
        raw = _random_signal_text(rng, evidence_type)
        insight = _normalize_seed_insight(target, raw, evidence_type)
        signal = normalize_signal({
            "industry": industry,
            "sourceType": "seed_random",
            "sourceRef": {"generator": "collect_marketing_signals.py", "seed": seed, "attempt": attempts},
            "topic": selected_topic,
            "signalText": f"가설 후보: {raw}",
            "normalizedInsight": insight,
            "targetSegment": target,
            "funnelStage": _funnel_stage_for(evidence_type),
            "evidenceType": evidence_type,
            "strength": rng.randint(2, 4),
            "freshness": 2,
            "confidence": 1,
            "riskFlags": ["needs_external_validation", "random_seed"],
            "usableFor": _usable_for(evidence_type),
            "review": {"decision": "unreviewed", "reasonTags": [], "reviewNote": "랜덤 후보 신호. 외부 근거 확인 전 생성 근거로 직접 사용 금지."},
        })
        if signal["id"] in seen_ids:
            continue
        seen_ids.add(signal["id"])
        generated.append(signal)
    return generated


def export_review_sheet(path: Path = DEFAULT_REVIEW_SHEET, *, signals_path: Path = SIGNALS_PATH, limit: int = 0) -> dict[str, Any]:
    signals = sorted(load_signals(signals_path), key=lambda item: (
        item.get("review", {}).get("decision") != "unreviewed",
        item.get("sourceType", ""),
        item.get("topic", ""),
        item.get("id", ""),
    ))
    rows = [signal_to_row(item) for item in signals[:limit or None]]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return {"mode": "export", "sheet": str(path), "rows": len(rows), "metrics": signal_metrics(signals)}


def import_review_sheet(path: Path, *, apply: bool = False, signals_path: Path = SIGNALS_PATH) -> dict[str, Any]:
    rows = read_review_rows(path)
    signals = load_signals(signals_path)
    by_id = {item.get("id"): item for item in signals}
    applied = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        signal_id = str(row.get("id") or "").strip()
        decision = str(row.get("decision") or "").strip().lower()
        if not decision:
            skipped += 1
            continue
        try:
            if decision not in DECISIONS:
                raise ValueError("decision must be selected, shortlist, rejected, or unreviewed")
            if signal_id not in by_id:
                raise ValueError(f"unknown signal id: {signal_id}")
            reason_tags = [tag for tag in _split_csvish(str(row.get("reasonTags") or "")) if tag in REASON_TAGS]
            if apply:
                item = by_id[signal_id]
                decision, forced_reason = review_decision_after_quality_gate(item, decision)
                if forced_reason and forced_reason not in reason_tags:
                    reason_tags.append(forced_reason)
                review_note = str(row.get("reviewNote") or "").strip()
                if forced_reason:
                    review_note = _append_review_note(review_note, "캡처 품질 문제가 있어 selected 대신 보류로 저장했습니다. 원문 정리 후 다시 선택하세요.")
                item["review"] = {
                    "decision": decision,
                    "reasonTags": reason_tags,
                    "reviewNote": review_note,
                    "reviewedAt": datetime.now(timezone.utc).isoformat(),
                }
                applied += 1
        except Exception as exc:
            errors.append({"row": row_number, "id": signal_id, "error": str(exc)})
    if apply and not errors:
        save_signals(list(by_id.values()), signals_path)
    return {
        "mode": "import",
        "sheet": str(path),
        "apply": apply,
        "rows": len(rows),
        "applied": applied,
        "skipped": skipped,
        "errors": errors,
        "metrics": signal_metrics(list(by_id.values())),
    }


def update_signal_review(signal_id: str, review: dict[str, Any], path: Path = SIGNALS_PATH) -> dict[str, Any]:
    signals = load_signals(path)
    item = next((signal for signal in signals if signal.get("id") == signal_id), None)
    if not item:
        raise ValueError(f"Unknown marketing signal: {signal_id}")
    _apply_signal_review(item, review)
    save_signals(signals, path)
    return item


def update_signal_reviews(reviews: list[dict[str, Any]], path: Path = SIGNALS_PATH) -> list[dict[str, Any]]:
    if not reviews:
        raise ValueError("reviews must contain at least one signal review")
    signals = load_signals(path)
    by_id = {str(item.get("id") or ""): item for item in signals}
    updated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for review in reviews:
        signal_id = str(review.get("signalId") or review.get("id") or "").strip()
        if not signal_id or signal_id not in by_id:
            raise ValueError(f"Unknown marketing signal: {signal_id}")
        if signal_id in seen:
            raise ValueError(f"Duplicate marketing signal review: {signal_id}")
        seen.add(signal_id)
        item = by_id[signal_id]
        _apply_signal_review(item, review)
        updated.append(item)
    save_signals(signals, path)
    return updated


def _apply_signal_review(item: dict[str, Any], review: dict[str, Any]) -> None:
    decision = str(review.get("decision") or "").strip().lower()
    if decision not in DECISIONS:
        raise ValueError("decision must be selected, shortlist, rejected, or unreviewed")
    decision, forced_reason = review_decision_after_quality_gate(item, decision)
    reason_tags = [tag for tag in _dedupe_strings(review.get("reasonTags") or []) if tag in REASON_TAGS]
    if forced_reason and forced_reason not in reason_tags:
        reason_tags.append(forced_reason)
    review_note = str(review.get("reviewNote") or "").strip()
    if forced_reason:
        review_note = _append_review_note(review_note, "캡처 품질 문제가 있어 selected 대신 보류로 저장했습니다. 원문 정리 후 다시 선택하세요.")
    item["review"] = {
        "decision": decision,
        "reasonTags": reason_tags,
        "reviewNote": review_note,
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
    }


def update_signal_content(signal_id: str, patch: dict[str, Any], path: Path = SIGNALS_PATH) -> dict[str, Any]:
    signals = load_signals(path)
    item = next((signal for signal in signals if signal.get("id") == signal_id), None)
    if not item:
        raise ValueError(f"Unknown marketing signal: {signal_id}")
    for field in ("signalText", "normalizedInsight", "targetSegment"):
        value = str(patch.get(field) or "").strip()
        if value:
            item[field] = value
    if patch.get("evidenceType"):
        item["evidenceType"] = str(patch.get("evidenceType")).strip()
    if patch.get("usableFor"):
        item["usableFor"] = _dedupe_strings(patch.get("usableFor") or [])
    remaining_blockers = _content_quality_blockers(item)
    flags = [flag for flag in item.get("riskFlags", []) if flag not in SELECTED_BLOCKING_RISK_FLAGS and flag != "capture_quality_blocked"]
    flags.extend(remaining_blockers)
    if not remaining_blockers:
        flags.append("human_cleaned_public_signal")
    item["riskFlags"] = _dedupe_strings(flags)
    review = item.get("review") or {}
    reason_tags = _dedupe_strings(review.get("reasonTags") or [])
    if not remaining_blockers and "human_cleaned" not in reason_tags:
        reason_tags.append("human_cleaned")
    item["review"] = {
        **review,
        "reasonTags": reason_tags,
        "reviewNote": _append_review_note(str(review.get("reviewNote") or ""), "사람이 공개 캡처 신호를 정제했습니다."),
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
    }
    save_signals(signals, path)
    return item


def review_decision_after_quality_gate(signal: dict[str, Any], decision: str) -> tuple[str, str]:
    if decision == "selected" and SELECTED_BLOCKING_RISK_FLAGS.intersection(set(signal.get("riskFlags") or [])):
        return "shortlist", "capture_quality_blocked"
    return decision, ""


def _append_review_note(existing: str, addition: str) -> str:
    return f"{existing} {addition}".strip() if existing else addition


def _content_quality_blockers(signal: dict[str, Any]) -> list[str]:
    joined = " ".join(str(signal.get(field) or "") for field in ("signalText", "normalizedInsight", "targetSegment"))
    blockers: list[str] = []
    if re.search(r"<(html|body|div|script|style|span|section)\b", joined, re.IGNORECASE):
        blockers.append("raw_html_detected")
    if re.search(r"\{[\"'][A-Za-z0-9_\-]+[\"']\s*:|[\"']slides[\"']\s*:|[\"']headline[\"']\s*:", joined):
        blockers.append("raw_json_detected")
    if "�" in joined or re.search(r"(ì|ë|í|ê|ð|Ã|Â|爰|愿|怨|諛|섏|쒕|좏|留)", joined):
        blockers.append("broken_text_suspected")
    if len(str(signal.get("normalizedInsight") or "").strip()) < 35 or len(str(signal.get("targetSegment") or "").strip()) < 8:
        blockers.append("thin_public_observation")
    if blockers:
        blockers.append("capture_quality_blocked")
    return list(dict.fromkeys(blockers))



def signal_metrics(signals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    items = signals if signals is not None else load_signals()
    decisions = {decision: sum(item.get("review", {}).get("decision") == decision for item in items) for decision in DECISIONS}
    selected_usable = sum(
        item.get("review", {}).get("decision") == "selected"
        and not SELECTED_BLOCKING_RISK_FLAGS.intersection(set(item.get("riskFlags") or []))
        for item in items
    )
    quality_blocked = sum(bool(SELECTED_BLOCKING_RISK_FLAGS.intersection(set(item.get("riskFlags") or []))) for item in items)
    source_types = sorted({str(item.get("sourceType") or "") for item in items if item.get("sourceType")})
    evidence_types = sorted({str(item.get("evidenceType") or "") for item in items if item.get("evidenceType")})
    return {
        "total": len(items),
        "decisions": decisions,
        "reviewed": len(items) - decisions["unreviewed"],
        "sourceTypes": source_types,
        "evidenceTypes": evidence_types,
        "selectedUsable": selected_usable,
        "qualityBlocked": quality_blocked,
    }


def signal_to_row(signal: dict[str, Any]) -> dict[str, Any]:
    review = signal.get("review", {})
    return {
        "id": signal.get("id", ""),
        "decision": "" if review.get("decision") == "unreviewed" else review.get("decision", ""),
        "industry": signal.get("industry", ""),
        "topic": signal.get("topic", ""),
        "sourceType": signal.get("sourceType", ""),
        "evidenceType": signal.get("evidenceType", ""),
        "targetSegment": signal.get("targetSegment", ""),
        "signalText": signal.get("signalText", ""),
        "normalizedInsight": signal.get("normalizedInsight", ""),
        "strength": signal.get("strength", ""),
        "freshness": signal.get("freshness", ""),
        "confidence": signal.get("confidence", ""),
        "riskFlags": ", ".join(signal.get("riskFlags", []) or []),
        "usableFor": ", ".join(signal.get("usableFor", []) or []),
        "reasonTags": ", ".join(review.get("reasonTags", []) or []),
        "reviewNote": review.get("reviewNote", ""),
    }


def read_review_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _random_signal_text(rng: random.Random, evidence_type: str) -> str:
    if evidence_type == "pain":
        return rng.choice(PAINS)
    if evidence_type == "desire":
        return rng.choice(DESIRES)
    if evidence_type == "objection":
        return rng.choice(OBJECTIONS)
    if evidence_type == "timing":
        return rng.choice(SEASONAL_TRIGGERS)
    if evidence_type == "channel_pattern":
        return rng.choice(CHANNEL_PATTERNS)
    return rng.choice(SEASONAL_TRIGGERS + DESIRES)


def _normalize_seed_insight(target: str, raw: str, evidence_type: str) -> str:
    if evidence_type == "channel_pattern":
        return f"{target}에게 '{raw}' 패턴이 첫 접점 문장으로 작동하는지 검증한다."
    if evidence_type == "timing":
        return f"{target}에게 '{raw}'{_particle(raw, '을', '를')} 지금 행동할 이유로 쓸 수 있는지 검증한다."
    if evidence_type == "objection":
        return f"{target}은 '{raw}' 때문에 구매를 미룰 수 있으므로 선택 기준을 먼저 제시해야 한다."
    return f"{target}은 '{raw}'라는 맥락에 반응할 수 있으므로 제품 역할과 연결 가능성을 검증한다."


def _funnel_stage_for(evidence_type: str) -> str:
    return {
        "pain": "awareness",
        "desire": "consideration",
        "objection": "consideration",
        "proof": "consideration",
        "offer": "conversion",
        "channel_pattern": "awareness",
        "timing": "conversion",
        "trend": "awareness",
    }.get(evidence_type, "awareness")


def _usable_for(evidence_type: str) -> list[str]:
    if evidence_type == "channel_pattern":
        return ["channel", "copy", "qa"]
    if evidence_type in {"objection", "proof"}:
        return ["concept", "copy", "qa"]
    if evidence_type in {"offer", "timing"}:
        return ["concept", "offer", "copy"]
    return ["concept", "copy"]


def _signal_id(signal: dict[str, Any]) -> str:
    key = "|".join([
        str(signal.get("industry") or ""),
        str(signal.get("sourceType") or ""),
        str(signal.get("topic") or ""),
        str(signal.get("targetSegment") or ""),
        str(signal.get("evidenceType") or ""),
        str(signal.get("normalizedInsight") or signal.get("signalText") or ""),
    ])
    return f"signal_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"


def _clamp_score(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 1
    return max(1, min(5, number))


def _dedupe_strings(values: list[Any]) -> list[str]:
    return [item for item in dict.fromkeys(str(value).strip() for value in values) if item]


def _split_csvish(value: str) -> list[str]:
    return [item.strip() for item in value.replace("|", ",").split(",") if item.strip()]


def _particle(text: str, consonant: str, vowel: str) -> str:
    stripped = str(text or "").strip()
    if not stripped:
        return vowel
    code = ord(stripped[-1])
    if not 0xAC00 <= code <= 0xD7A3:
        return vowel
    return consonant if (code - 0xAC00) % 28 else vowel
