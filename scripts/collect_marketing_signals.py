#!/usr/bin/env python3
"""Collect, seed, and review marketing intelligence signals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.marketing_intelligence.repository import (  # noqa: E402
    DEFAULT_REVIEW_SHEET,
    SIGNALS_PATH,
    append_signals,
    export_review_sheet,
    generate_random_seed_signals,
    import_review_sheet,
    signal_metrics,
)
from services.marketing_intelligence.public_signal_collector import (  # noqa: E402
    capture_public_page_snapshot,
    collect_public_signals_from_snapshot,
    load_public_signal_snapshot,
)
from core.utils.json_io import write_json  # noqa: E402


def capture_public_urls_snapshot(
    urls: list[str],
    *,
    topic: str,
    event_id: str = "",
    source_kind: str,
    output_path: Path | None = None,
) -> dict[str, object]:
    observations: list[dict[str, object]] = []
    for url in urls:
        snapshot = capture_public_page_snapshot(
            url,
            topic=topic,
            event_id=event_id,
            source_kind=source_kind,
            output_path=None,
        )
        observations.extend(snapshot.get("observations", []))
    combined = {
        "schemaVersion": "1.0.0",
        "eventId": event_id,
        "observations": observations,
    }
    if output_path:
        write_json(output_path, combined)
    return combined


def load_capture_urls(path: Path) -> list[str]:
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        urls.append(value)
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--industry", default="cosmetics_skincare", choices=["cosmetics_skincare", "jewelry_luxury"])
    parser.add_argument("--topic", default="", help="Optional topic label, e.g. monsoon_hydration.")
    parser.add_argument("--event-id", default="", help="Bind public observations to one event.")
    parser.add_argument("--random-seed", action="store_true", help="Generate random hypothesis signals for later review.")
    parser.add_argument("--public-snapshot", type=Path, help="Import public marketing observations from a JSON snapshot.")
    parser.add_argument("--capture-url", action="append", default=[], help="Use Playwright to capture a public page into a public signal snapshot. Can be repeated.")
    parser.add_argument("--capture-urls-file", type=Path, help="Text file with one public URL per line. Blank lines and # comments are ignored.")
    parser.add_argument("--source-kind", default="public_web", help="Source kind for --capture-url, e.g. brand_site, google_trends, weather.")
    parser.add_argument("--snapshot-output", type=Path, help="Where to save the Playwright page snapshot.")
    parser.add_argument("--auto-select-public", action="store_true", help="Mark imported public observations as selected. Default keeps them unreviewed.")
    parser.add_argument("--count", type=int, default=50, help="Number of random signals to generate.")
    parser.add_argument("--seed", type=int, default=None, help="Deterministic random seed for repeatable tests.")
    parser.add_argument("--signals", type=Path, default=SIGNALS_PATH)
    parser.add_argument("--review-sheet", type=Path, default=DEFAULT_REVIEW_SHEET)
    parser.add_argument("--export-review", action="store_true", help="Export the signal review CSV.")
    parser.add_argument("--import-review", action="store_true", help="Import review decisions from --review-sheet.")
    parser.add_argument("--apply", action="store_true", help="Persist imported review decisions.")
    parser.add_argument("--metrics", action="store_true", help="Print current signal metrics.")
    args = parser.parse_args()

    if args.count < 1:
        raise SystemExit("--count must be at least 1")

    result: dict[str, object] = {}
    if args.random_seed:
        generated = generate_random_seed_signals(
            count=args.count,
            industry=args.industry,
            topic=args.topic,
            seed=args.seed,
        )
        result["collection"] = append_signals(generated, args.signals.resolve())

    public_snapshot = None
    capture_urls = [str(item).strip() for item in args.capture_url if str(item).strip()]
    if args.capture_urls_file:
        capture_urls.extend(load_capture_urls(args.capture_urls_file.resolve()))
    if capture_urls:
        public_snapshot = capture_public_urls_snapshot(
            capture_urls,
            topic=args.topic or "public_web_capture",
            event_id=args.event_id,
            source_kind=args.source_kind,
            output_path=args.snapshot_output.resolve() if args.snapshot_output else None,
        )
        result["publicCapture"] = {
            "urls": capture_urls,
            "sourceKind": args.source_kind,
            "observations": len(public_snapshot.get("observations", [])),
            "snapshotOutput": str(args.snapshot_output.resolve()) if args.snapshot_output else "",
        }
    elif args.public_snapshot:
        public_snapshot = load_public_signal_snapshot(args.public_snapshot.resolve())

    if public_snapshot is not None:
        signals = collect_public_signals_from_snapshot(
            public_snapshot,
            industry=args.industry,
            default_topic=args.topic or "public_marketing_signals",
            default_event_id=args.event_id,
            auto_select=args.auto_select_public,
        )
        result["publicSignals"] = append_signals(signals, args.signals.resolve())
        result["publicSignalCount"] = len(signals)

    if args.import_review:
        result["reviewImport"] = import_review_sheet(args.review_sheet.resolve(), apply=args.apply, signals_path=args.signals.resolve())

    if args.export_review or args.random_seed or public_snapshot is not None:
        result["reviewExport"] = export_review_sheet(args.review_sheet.resolve(), signals_path=args.signals.resolve())

    if args.metrics or not result:
        result["metrics"] = signal_metrics()

    print(json.dumps(result, ensure_ascii=False))
    has_errors = bool(result.get("reviewImport", {}) and result["reviewImport"].get("errors"))  # type: ignore[index, union-attr]
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
