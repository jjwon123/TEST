"""Meta Ad Library collector backed by Playwright screenshots."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode, urlparse

import requests

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page
else:
    Locator = Any
    Page = Any


META_AD_LIBRARY_URL = "https://www.facebook.com/ads/library/"


@dataclass(frozen=True)
class MetaCollectorOptions:
    query: str
    output_dir: Path
    country: str = "KR"
    category: str = "all"
    media_type: str = "all"
    limit: int = 20
    scrolls: int = 12
    headless: bool = False
    browser_channel: str = "msedge"
    skip_video: bool = False


def build_meta_ad_library_url(query: str, country: str = "KR", category: str = "all", media_type: str = "all") -> str:
    params = {
        "active_status": "active",
        "ad_type": category or "all",
        "country": country or "KR",
        "q": query,
        "search_type": "keyword_unordered",
        "media_type": media_type or "all",
    }
    return f"{META_AD_LIBRARY_URL}?{urlencode(params)}"


def collect_meta_ads(options: MetaCollectorOptions) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Meta Ad Library collection requires Playwright. Install it before running collection jobs.") from exc
    options.output_dir.mkdir(parents=True, exist_ok=True)
    captures_dir = options.output_dir / "captures"
    captures_dir.mkdir(parents=True, exist_ok=True)
    images_dir = options.output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    source_url = build_meta_ad_library_url(options.query, options.country, options.category, options.media_type)

    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, options)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 1200}, locale="ko-KR")
            page = context.new_page()
            page.goto(source_url, wait_until="domcontentloaded", timeout=90_000)
            page.wait_for_timeout(5000)
            _scroll(page, options.scrolls)
            cards = _find_cards(page)
            items = [
                _capture_card(card, captures_dir, images_dir, source_url, index, skip_video=options.skip_video)
                for index, card in enumerate(cards[: options.limit], 1)
            ]
        finally:
            browser.close()

    items = [item for item in items if item]
    payload = {
        "source": "meta_ad_library",
        "query": options.query,
        "country": options.country,
        "category": options.category,
        "mediaType": options.media_type,
        "sourceUrl": source_url,
        "collectedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "downloadedImageCount": sum(len(item.get("media", [])) for item in items),
        "items": items,
    }
    _atomic_write_json(options.output_dir / "collected-ads.json", payload)
    return payload


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _launch_browser(playwright: Any, options: MetaCollectorOptions) -> Any:
    try:
        return playwright.chromium.launch(channel=options.browser_channel, headless=options.headless)
    except Exception:
        return playwright.chromium.launch(channel="chrome", headless=options.headless)


def _scroll(page: Page, scrolls: int) -> None:
    for _ in range(max(0, scrolls)):
        page.mouse.wheel(0, 2200)
        page.wait_for_timeout(1200)


def _find_cards(page: Page) -> list[Locator]:
    selectors = [
        'div:has-text("Library ID:")',
        'div:has-text("라이브러리 ID:")',
    ]
    for selector in selectors:
        candidates = page.locator(selector)
        result: list[Locator] = []
        for index in range(min(candidates.count(), 500)):
            node = candidates.nth(index)
            try:
                text = node.inner_text(timeout=1000)
                box = node.bounding_box()
            except Exception:
                continue
            id_count = len(re.findall(r"(?:Library ID|라이브러리 ID)\s*[:：]\s*[0-9]+", text, re.IGNORECASE))
            if (
                box
                and id_count == 1
                and 280 <= box["width"] <= 900
                and 220 <= box["height"] <= 1800
                and len(text) >= 30
            ):
                result.append(node)
        if result:
            return _dedupe_nested(result)
    return []


def _dedupe_nested(cards: list[Locator]) -> list[Locator]:
    result: list[Locator] = []
    seen: set[str] = set()
    for card in cards:
        try:
            text = card.inner_text(timeout=1000)
        except Exception:
            continue
        key = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
        if key not in seen:
            seen.add(key)
            result.append(card)
    return result


def _capture_card(
    card: Locator,
    captures_dir: Path,
    images_dir: Path,
    source_url: str,
    index: int,
    *,
    skip_video: bool = False,
) -> dict[str, Any] | None:
    try:
        text = card.inner_text(timeout=3000).strip()
        if not text:
            return None
        library_id = _first_match(text, [r"(?:Library ID|라이브러리 ID)\s*[:：]\s*([0-9]+)"])
        item_id = f"meta_ad_{library_id or index:0>4}"
        is_video = _card_is_video(card)
        capture_path = captures_dir / f"{item_id}.png"
        card.screenshot(path=str(capture_path))
        links = card.locator("a[href]").evaluate_all(
            "(nodes) => nodes.map((node) => ({href: node.href, text: (node.innerText || '').trim()}))"
        )
        landing_url = next(
            (
                item["href"]
                for item in links
                if item.get("href")
                and (
                    "l.facebook.com/" in item["href"]
                    or ("facebook.com/" not in item["href"] and "instagram.com/" not in item["href"])
                )
            ),
            "",
        )
        brand = _brand_from_text(text)
        media_candidates = card.locator("img").evaluate_all(
            """(nodes) => nodes.map((img) => ({
              url: img.currentSrc || img.src || "",
              alt: img.alt || "",
              width: img.naturalWidth || 0,
              height: img.naturalHeight || 0,
              visibleWidth: Math.round(img.getBoundingClientRect().width),
              visibleHeight: Math.round(img.getBoundingClientRect().height)
            })).filter((item) =>
              item.url &&
              item.width >= 240 &&
              item.height >= 180 &&
              item.visibleWidth >= 150 &&
              item.visibleHeight >= 100
            ).slice(0, 10)"""
        )
        # 영상 광고는 포스터/캡처 프레임만 잡혀 취향 학습 노이즈가 되므로 옵션 시 미디어를 받지 않는다.
        if skip_video and is_video:
            media = []
        else:
            media = _download_media(media_candidates, images_dir, item_id, source_url)
        return {
            "id": item_id,
            "source": "meta_ad_library",
            "libraryId": library_id,
            "adLibraryUrl": source_url,
            "landingUrl": landing_url,
            "brand": brand,
            "isVideo": is_video,
            "capturePath": str(capture_path),
            "captureFile": capture_path.name,
            "media": media,
            "imagePaths": [item["savedPath"] for item in media],
            "imageUrls": [item["imageUrl"] for item in media],
            "copy": text,
            "cta": _cta_from_text(text),
            "visualTags": [],
            "copyTags": [],
            "layoutHint": "",
            "score": None,
            "needsReview": True,
        }
    except Exception:
        return None


def _card_is_video(card: Locator) -> bool:
    """카드가 영상 광고인지 감지. <video> 요소 또는 재생 버튼 오버레이로 판단."""
    try:
        if card.locator("video").count() > 0:
            return True
        play = card.locator(
            "[aria-label*='재생'], [aria-label*='동영상'], [aria-label*='Play' i], [aria-label*='video' i]"
        ).count()
        return play > 0
    except Exception:
        return False


def _first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _cta_from_text(text: str) -> str:
    known = ["Shop now", "Learn more", "Sign up", "Apply now", "Contact us", "구매하기", "더 알아보기", "가입하기"]
    lowered = text.lower()
    return next((cta for cta in known if cta.lower() in lowered), "")


def _brand_from_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for marker in ("광고 상세 정보 보기", "See ad details"):
        if marker in lines:
            index = lines.index(marker)
            if index + 1 < len(lines):
                return lines[index + 1]
    return ""


def _download_media(
    candidates: list[dict[str, Any]],
    images_dir: Path,
    item_id: str,
    source_url: str,
) -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
        "Referer": source_url,
    })
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        image_url = str(candidate.get("url") or "").replace("&amp;", "&")
        if not image_url or image_url.startswith(("data:", "blob:")):
            continue
        try:
            response = session.get(image_url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "image" not in content_type or len(response.content) < 10_000:
                continue
            digest = hashlib.sha256(response.content).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            extension = _image_extension(image_url, content_type)
            saved_path = images_dir / f"{item_id}_{len(result) + 1:02d}_{digest[:10]}{extension}"
            saved_path.write_bytes(response.content)
            result.append({
                "imageUrl": image_url,
                "savedPath": str(saved_path),
                "savedFile": saved_path.name,
                "sha256": digest,
                "width": int(candidate.get("width") or 0),
                "height": int(candidate.get("height") or 0),
                "alt": str(candidate.get("alt") or ""),
                "bytes": len(response.content),
                "contentType": content_type,
            })
            time.sleep(0.1)
        except requests.RequestException:
            continue
    return result


def _image_extension(url: str, content_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    if "gif" in content_type:
        return ".gif"
    return ".jpg"
