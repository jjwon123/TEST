"""Crop preview boundary for generated images."""

from __future__ import annotations

from pathlib import Path


def planned_preview_path(source_path: Path, suffix: str = "preview") -> Path:
    return source_path.with_name(f"{source_path.stem}_{suffix}{source_path.suffix}")
