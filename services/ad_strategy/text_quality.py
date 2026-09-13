"""Text-level quality checks shared by ad-planning audits and gates."""

from __future__ import annotations

import re
from typing import Any


CJK_MOJIBAKE_RE = re.compile(r"[\u4e00-\u9fff\uf900-\ufaff]")
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
RAW_JSON_RE = re.compile(r'(^\s*[\[{]\s*["{])|("schemaVersion"\s*:)|("candidates"\s*:)|("outputs"\s*:)', re.I)
RAW_HTML_RE = re.compile(r"<(?:html|body|script|style|div|span|section|article|meta|link)\b", re.I)
CODE_ARTIFACT_RE = re.compile(r"\b(?:undefined|null|NaN|object Object|JSON\.stringify|console\.log|function\s*\(|const\s+\w+|let\s+\w+)\b")
PARTICLE_CHECK_TOKENS = (
    "앰플", "세럼", "크림", "토너", "로션", "마스크", "에센스", "선크림",
    "스킨케어", "수분", "장벽", "탄력", "진정", "보습",
)
PARTICLE_PAIRS = (("은", "는"), ("이", "가"), ("을", "를"), ("과", "와"), ("으로", "로"))


def collect_text_values(value: Any) -> list[str]:
    values: list[str] = []

    def collect(item: Any) -> None:
        if isinstance(item, dict):
            for child in item.values():
                collect(child)
        elif isinstance(item, list):
            for child in item:
                collect(child)
        elif isinstance(item, str) and item.strip():
            values.append(item)

    collect(value)
    return values


def has_broken_korean(text: str) -> bool:
    value = str(text or "")
    if "\ufffd" in value or "�" in value:
        return True
    if re.search(r"\?{3,}", value):
        return True
    cjk_count = len(CJK_MOJIBAKE_RE.findall(value))
    if cjk_count >= 3:
        return True
    hangul_count = len(HANGUL_RE.findall(value))
    question_count = value.count("?")
    if cjk_count >= 1 and question_count >= 2:
        return True
    if question_count >= 5 and hangul_count >= 3:
        return True
    return False


def has_raw_json(text: str) -> bool:
    return bool(RAW_JSON_RE.search(str(text or "")))


def has_raw_html(text: str) -> bool:
    return bool(RAW_HTML_RE.search(str(text or "")))


def has_programming_artifact(text: str) -> bool:
    return bool(CODE_ARTIFACT_RE.search(str(text or "")))


def text_artifact_summary(value: Any, *, sample_limit: int = 5) -> dict[str, Any]:
    texts = collect_text_values(value)
    broken = [text for text in texts if has_broken_korean(text)]
    raw_json = [text for text in texts if has_raw_json(text)]
    raw_html = [text for text in texts if has_raw_html(text)]
    programming = [text for text in texts if has_programming_artifact(text)]
    particle_errors = particle_mismatches(value)
    return {
        "textCount": len(texts),
        "brokenKoreanCount": len(broken),
        "rawJsonCount": len(raw_json),
        "rawHtmlCount": len(raw_html),
        "programmingArtifactCount": len(programming),
        "particleMismatchCount": len(particle_errors),
        "samples": {
            "brokenKorean": [_preview(text) for text in broken[:sample_limit]],
            "rawJson": [_preview(text) for text in raw_json[:sample_limit]],
            "rawHtml": [_preview(text) for text in raw_html[:sample_limit]],
            "programmingArtifact": [_preview(text) for text in programming[:sample_limit]],
            "particleMismatch": particle_errors[:sample_limit],
        },
    }


def has_blocking_text_artifacts(value: Any) -> bool:
    summary = text_artifact_summary(value)
    return any(
        int(summary.get(key) or 0) > 0
        for key in ("brokenKoreanCount", "rawJsonCount", "rawHtmlCount", "programmingArtifactCount")
    )


def particle_mismatches(value: Any) -> list[str]:
    texts = collect_text_values(value)
    mismatches: list[str] = []
    for text in texts:
        for token in PARTICLE_CHECK_TOKENS:
            for consonant, vowel in PARTICLE_PAIRS:
                expected = _particle(token, consonant, vowel)
                wrong = vowel if expected == consonant else consonant
                candidate = f"{token}{wrong}"
                if candidate in text:
                    mismatches.append(candidate)
    return list(dict.fromkeys(mismatches))


def _particle(text: str, consonant: str, vowel: str) -> str:
    code = ord(str(text)[-1])
    if not 0xAC00 <= code <= 0xD7A3:
        return vowel
    jong = (code - 0xAC00) % 28
    if (consonant, vowel) == ("으로", "로") and jong == 8:
        return vowel
    return consonant if jong else vowel


def _preview(text: str, limit: int = 160) -> str:
    normalized = " ".join(str(text or "").split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit - 1]}..."
