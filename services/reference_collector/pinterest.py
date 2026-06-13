"""Pinterest board collector backed by Playwright and local file storage."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from playwright.sync_api import Browser, Page, sync_playwright


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
)


@dataclass(frozen=True)
class CollectorOptions:
    board_url: str
    output_dir: Path
    limit: int = 200
    scrolls: int = 30
    headless: bool = True
    browser_channel: str = "msedge"
    storage_state: Path | None = None
    request_delay: float = 0.25
    dry_run: bool = False
    allow_page_fallback: bool = False


@dataclass(frozen=True)
class ImageCandidate:
    image_url: str
    pin_url: str
    alt: str
    source_url: str


def collect_pinterest_board(options: CollectorOptions) -> dict[str, Any]:
    options.output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = options.output_dir / "metadata.jsonl"

    candidates = scrape_board_candidates(options)
    saved_records: list[dict[str, Any]] = []
    seen_hashes = _read_existing_hashes(metadata_path)

    for index, candidate in enumerate(candidates[: options.limit], start=1):
        if options.dry_run:
            saved_records.append(_record(candidate, index=index, status="dry_run"))
            continue

        record = download_candidate(
            candidate,
            output_dir=options.output_dir,
            index=index,
            known_hashes=seen_hashes,
            delay=options.request_delay,
        )
        saved_records.append(record)
        _append_jsonl(metadata_path, record)

    summary = {
        "board_url": options.board_url,
        "output_dir": str(options.output_dir),
        "candidates_found": len(candidates),
        "processed": len(saved_records),
        "downloaded": sum(1 for item in saved_records if item.get("status") == "downloaded"),
        "duplicates": sum(1 for item in saved_records if item.get("status") == "duplicate"),
        "failed": sum(1 for item in saved_records if item.get("status") == "failed"),
        "metadata": str(metadata_path),
    }
    summary_path = options.output_dir / "collection-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def scrape_board_candidates(options: CollectorOptions) -> list[ImageCandidate]:
    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, options)
        try:
            board_errors: list[str] = []
            feed_items: list[dict[str, Any]] = []
            context_kwargs: dict[str, Any] = {
                "user_agent": DEFAULT_USER_AGENT,
                "viewport": {"width": 1440, "height": 1200},
            }
            if options.storage_state:
                context_kwargs["storage_state"] = str(options.storage_state)
            context = browser.new_context(**context_kwargs)
            page = context.new_page()

            def on_response(response: Any) -> None:
                url = response.url
                if "BoardResource/get" in url:
                    _capture_board_error(response, board_errors)
                if "BoardFeedResource/get" in url:
                    _capture_feed_items(response, feed_items)

            page.on("response", on_response)
            page.goto(options.board_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(3000)
            _scroll_until_stable(page, target_count=options.limit, max_scrolls=options.scrolls)

            if board_errors:
                raise RuntimeError(
                    "Pinterest board is not accessible: "
                    + "; ".join(board_errors)
                    + ". If this is your private board, run pinterest_login.bat first."
                )

            feed_candidates = _candidates_from_feed_items(feed_items, options.board_url)
            if feed_candidates:
                return _dedupe_candidates(feed_candidates)

            if not options.allow_page_fallback:
                raise RuntimeError(
                    "Could not find Pinterest BoardFeedResource items. "
                    "This usually means the board is private, unavailable, or Pinterest showed recommendations instead of board pins."
                )

            raw = page.evaluate(_EXTRACT_SCRIPT)
            return _dedupe_candidates(
                ImageCandidate(
                    image_url=item["imageUrl"],
                    pin_url=item.get("pinUrl", ""),
                    alt=item.get("alt", ""),
                    source_url=options.board_url,
                )
                for item in raw
                if item.get("imageUrl")
            )
        finally:
            browser.close()


def download_candidate(
    candidate: ImageCandidate,
    *,
    output_dir: Path,
    index: int,
    known_hashes: set[str],
    delay: float = 0.25,
) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT, "Referer": candidate.source_url})
    errors: list[str] = []

    for url in _download_url_candidates(candidate.image_url):
        try:
            response = session.get(url, timeout=30)
            if response.status_code >= 400:
                errors.append(f"{response.status_code} {url}")
                continue
            content_type = response.headers.get("content-type", "")
            if "image" not in content_type and not _looks_like_image(response.content):
                errors.append(f"not image {url}")
                continue
            digest = hashlib.sha256(response.content).hexdigest()
            if digest in known_hashes:
                return _record(candidate, index=index, status="duplicate", downloaded_url=url, sha256=digest)
            known_hashes.add(digest)
            extension = _extension_from_url(url, content_type)
            filename = f"{index:04d}_{_safe_stem(candidate.alt) or 'pin'}_{digest[:10]}{extension}"
            output_path = output_dir / filename
            output_path.write_bytes(response.content)
            if delay:
                time.sleep(delay)
            return _record(
                candidate,
                index=index,
                status="downloaded",
                downloaded_url=url,
                sha256=digest,
                saved_path=str(output_path),
                bytes=len(response.content),
                content_type=content_type,
            )
        except requests.RequestException as exc:
            errors.append(f"{type(exc).__name__}: {url}")

    return _record(candidate, index=index, status="failed", error="; ".join(errors[:5]))


def _launch_browser(playwright: Any, options: CollectorOptions) -> Browser:
    launch_kwargs = {
        "headless": options.headless,
        "channel": options.browser_channel,
    }
    try:
        return playwright.chromium.launch(**launch_kwargs)
    except Exception:
        if options.browser_channel != "chrome":
            launch_kwargs["channel"] = "chrome"
            return playwright.chromium.launch(**launch_kwargs)
        raise


def _scroll_until_stable(page: Page, *, target_count: int, max_scrolls: int) -> None:
    last_count = 0
    stable_rounds = 0
    for _ in range(max_scrolls):
        count = page.evaluate("document.querySelectorAll('img[src]').length")
        if count >= target_count:
            break
        if count == last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
        if stable_rounds >= 4:
            break
        last_count = count
        page.mouse.wheel(0, 2400)
        page.wait_for_timeout(1500)


def _capture_board_error(response: Any, board_errors: list[str]) -> None:
    try:
        payload = response.json()
    except Exception:
        return
    error = payload.get("resource_response", {}).get("error")
    if isinstance(error, dict):
        message = error.get("message") or "board error"
        http_status = error.get("http_status")
        board_errors.append(f"{http_status or ''} {message}".strip())


def _capture_feed_items(response: Any, feed_items: list[dict[str, Any]]) -> None:
    try:
        payload = response.json()
    except Exception:
        return
    data = payload.get("resource_response", {}).get("data")
    feed_items.extend(_find_pin_dicts(data))


def _find_pin_dicts(value: Any) -> list[dict[str, Any]]:
    pins: list[dict[str, Any]] = []
    if isinstance(value, dict):
        images = value.get("images")
        if isinstance(images, dict) and (value.get("id") or value.get("grid_title")):
            pins.append(value)
        for child in value.values():
            pins.extend(_find_pin_dicts(child))
    elif isinstance(value, list):
        for child in value:
            pins.extend(_find_pin_dicts(child))
    return pins


def _candidates_from_feed_items(items: list[dict[str, Any]], source_url: str) -> list[ImageCandidate]:
    candidates: list[ImageCandidate] = []
    for item in items:
        image_url = _best_image_url(item.get("images", {}))
        if not image_url:
            continue
        pin_id = str(item.get("id") or "").strip()
        pin_url = f"https://www.pinterest.com/pin/{pin_id}/" if pin_id else str(item.get("link") or "")
        candidates.append(
            ImageCandidate(
                image_url=image_url,
                pin_url=pin_url,
                alt=str(item.get("grid_title") or item.get("title") or item.get("description") or ""),
                source_url=source_url,
            )
        )
    return candidates


def _best_image_url(images: dict[str, Any]) -> str:
    if not isinstance(images, dict):
        return ""
    preferred = ["orig", "originals", "1200x", "736x", "564x", "474x", "236x"]
    for key in preferred:
        value = images.get(key)
        if isinstance(value, dict) and value.get("url"):
            return str(value["url"])
        if isinstance(value, str):
            return value
    for value in images.values():
        if isinstance(value, dict) and value.get("url"):
            return str(value["url"])
    return ""


_EXTRACT_SCRIPT = """
() => {
  const bestFromSrcset = (srcset) => {
    if (!srcset) return "";
    const parts = srcset.split(",").map((part) => {
      const [url, size] = part.trim().split(/\\s+/);
      const score = size && size.endsWith("w") ? parseInt(size, 10) : 0;
      return {url, score: Number.isFinite(score) ? score : 0};
    }).filter((item) => item.url);
    parts.sort((a, b) => b.score - a.score);
    return parts[0]?.url || "";
  };
  return Array.from(document.querySelectorAll("img[src]")).map((img) => {
    const link = img.closest("a[href]");
    const href = link ? new URL(link.getAttribute("href"), location.href).href : "";
    return {
      imageUrl: bestFromSrcset(img.getAttribute("srcset")) || img.currentSrc || img.src,
      pinUrl: href,
      alt: img.getAttribute("alt") || img.getAttribute("aria-label") || ""
    };
  }).filter((item) => item.imageUrl && item.imageUrl.includes("pinimg.com"));
}
"""


def _dedupe_candidates(candidates: Any) -> list[ImageCandidate]:
    seen: set[str] = set()
    result: list[ImageCandidate] = []
    for candidate in candidates:
        key = _normalize_pinimg_url(candidate.image_url)
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def _download_url_candidates(url: str) -> list[str]:
    normalized = _normalize_pinimg_url(url)
    urls = [normalized]
    for size in ("originals", "1200x", "736x", "564x"):
        upgraded = re.sub(r"/(?:\d+x|originals)/", f"/{size}/", normalized, count=1)
        if upgraded not in urls:
            urls.insert(0, upgraded)
    return urls


def _normalize_pinimg_url(url: str) -> str:
    return url.split("?")[0].replace("\\u002F", "/")


def _extension_from_url(url: str, content_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return ".jpg" if suffix == ".jpeg" else suffix
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    if "gif" in content_type:
        return ".gif"
    return ".jpg"


def _looks_like_image(data: bytes) -> bool:
    return data.startswith((b"\xff\xd8", b"\x89PNG", b"GIF8", b"RIFF"))


def _safe_stem(value: str) -> str:
    value = re.sub(r"\s+", "-", value.strip().lower())
    value = re.sub(r"[^a-z0-9가-힣_-]+", "", value)
    return value[:48].strip("-_")


def _record(
    candidate: ImageCandidate,
    *,
    index: int,
    status: str,
    downloaded_url: str = "",
    sha256: str = "",
    saved_path: str = "",
    bytes: int = 0,
    content_type: str = "",
    error: str = "",
) -> dict[str, Any]:
    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "index": index,
        "status": status,
        "source_url": candidate.source_url,
        "pin_url": candidate.pin_url,
        "image_url": candidate.image_url,
        "downloaded_url": downloaded_url,
        "alt": candidate.alt,
        "saved_path": saved_path,
        "sha256": sha256,
        "bytes": bytes,
        "content_type": content_type,
        "error": error,
    }


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_existing_hashes(path: Path) -> set[str]:
    if not path.exists():
        return set()
    hashes: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                digest = json.loads(line).get("sha256", "")
            except json.JSONDecodeError:
                continue
            if digest:
                hashes.add(digest)
    return hashes
