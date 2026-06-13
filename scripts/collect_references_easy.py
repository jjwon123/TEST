"""Friendly interactive launcher for collecting Pinterest references."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.reference_collector.pinterest import CollectorOptions, collect_pinterest_board
from scripts.workflow import import_local_reference, run_reference_pipeline


DEFAULT_STATE = ROOT / "assets" / "references" / "pinterest-storage-state.json"


def main() -> int:
    print("")
    print("Pinterest reference collector")
    print("=" * 30)
    print("Paste a Pinterest board URL. For private boards, run pinterest_login.bat first.")
    print("")

    url = _ask("Board URL")
    if not url:
        print("No URL entered. Exiting.")
        return 1

    default_name = _board_slug(url)
    folder_name = _ask(f"Folder name [{default_name}]") or default_name
    limit_text = _ask("How many images? [100]") or "100"
    visible_text = (_ask("Show browser while collecting? y/N") or "n").lower()
    run_text = _ask("Attach to run directory after download? [blank to skip]")
    update_03_text = "n"
    select_count_text = "30"
    if run_text:
        select_count_text = _ask("How many references should the run select? [30]") or "30"
        update_03_text = (_ask("Update 03_visual_candidates after selection? Y/n") or "y").lower()

    try:
        limit = max(1, int(limit_text))
    except ValueError:
        limit = 100
    try:
        select_count = max(1, int(select_count_text))
    except ValueError:
        select_count = 30

    source_id = _safe_slug(folder_name)
    output_dir = ROOT / "assets" / "references" / "inbox" / source_id
    print("")
    print(f"Saving to: {output_dir}")
    print("Collecting... this can take a minute if the board is large.")
    print("")

    try:
        summary = collect_pinterest_board(
            CollectorOptions(
                board_url=url,
                output_dir=output_dir,
                limit=limit,
                scrolls=max(10, min(80, limit // 5 + 10)),
                headless=visible_text not in {"y", "yes"},
                browser_channel="chrome",
                storage_state=DEFAULT_STATE if DEFAULT_STATE.exists() else None,
                allow_page_fallback=False,
            )
        )
    except RuntimeError as exc:
        print("")
        print(f"Collection failed: {exc}")
        print("")
        print("If this is your private board:")
        print("1. Close this window.")
        print("2. Run pinterest_login.bat once.")
        print("3. Run reference_collect.bat again.")
        print("")
        return 1

    print("")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if run_text:
        run_dir = _resolve_run_dir(run_text)
        print("")
        print(f"Attaching collected board to run: {run_dir}")
        import_local_reference(run_dir, output_dir, label=source_id, limit=limit)
        run_reference_pipeline(
            run_dir,
            include_search=False,
            include_queued=True,
            update_03=update_03_text not in {"n", "no"},
            query_limit=0,
            per_query_limit=0,
            select_count=select_count,
            headless=True,
            only_source=source_id,
        )
        print("")
        print("Done. Selected references are now saved under the run references folder.")
    else:
        print("")
        print("Done. To attach this folder to a run later:")
        print(
            ".venv\\Scripts\\python.exe scripts\\workflow.py "
            f"--run runs\\[run-dir] --import-local-reference-source \"{output_dir}\" "
            f"--reference-label {source_id} --reference-limit {limit}"
        )
        print(
            ".venv\\Scripts\\python.exe scripts\\workflow.py "
            f"--run runs\\[run-dir] --run-reference-pipeline --reference-no-search "
            f"--reference-source {source_id} --reference-select-count 30 --reference-update-03"
        )
    print("")
    return 0


def _ask(label: str) -> str:
    return input(f"{label}: ").strip().strip('"')


def _board_slug(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2:
        return _safe_slug(parts[-1])
    return "pinterest-board"


def _safe_slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9가-힣_-]+", "", value)
    return value.strip("-_") or "pinterest-board"


def _resolve_run_dir(value: str) -> Path:
    path = Path(value.strip().strip('"'))
    if not path.is_absolute():
        path = ROOT / path
    return path


if __name__ == "__main__":
    raise SystemExit(main())
