"""Friendly wrapper around gallery-dl for Pinterest original downloads."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("")
    print("Pinterest original collector (gallery-dl)")
    print("=" * 40)
    print("This uses gallery-dl's Pinterest extractor, which downloads original image URLs when available.")
    print("")

    url = ask("Board / section / pin URL")
    if not url:
        print("No URL entered.")
        return 1

    default_name = board_slug(url)
    folder = ask(f"Folder name [{default_name}]") or default_name
    limit_text = ask("Max items [20]") or "20"
    profile = (ask("Mode: safe or gentle? [safe]") or "safe").lower()
    use_cookies = (ask("Use Chrome login cookies? Y/n") or "y").lower() not in {"n", "no"}

    try:
        limit = max(1, int(limit_text))
    except ValueError:
        limit = 20

    output_dir = ROOT / "assets" / "references" / "inbox" / f"{safe_slug(folder)}-originals"
    output_dir.mkdir(parents=True, exist_ok=True)

    if profile == "gentle":
        sleep_request = "4-8"
        sleep_download = "8-15"
    else:
        sleep_request = "2-5"
        sleep_download = "4-8"

    command = [
        sys.executable,
        "-m",
        "gallery_dl",
        "--directory",
        str(output_dir),
        "--range",
        f"1-{limit}",
        "--sleep-request",
        sleep_request,
        "--sleep",
        sleep_download,
        "--sleep-429",
        "300-600",
        "--write-metadata",
        "--write-info-json",
        "--windows-filenames",
        "--verbose",
    ]
    if use_cookies:
        command.extend(["--cookies-from-browser", "chrome"])
    command.append(url)

    print("")
    print(f"Saving to: {output_dir}")
    print("Running gallery-dl safely. If Pinterest shows robot/rate-limit, stop and wait.")
    print("")

    result = subprocess.run(command, cwd=ROOT)
    return result.returncode


def ask(label: str) -> str:
    return input(f"{label}: ").strip().strip('"')


def board_slug(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part and part != "pin"]
    if parts:
        return safe_slug(parts[-1])
    return "pinterest"


def safe_slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9가-힣_-]+", "", value)
    return value.strip("-_") or "pinterest"


if __name__ == "__main__":
    raise SystemExit(main())

