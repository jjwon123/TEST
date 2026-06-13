"""Text fitting helpers for Figma templates."""

from __future__ import annotations


def fits_slot(text: str, max_length: int | None) -> bool:
    if max_length is None:
        return True
    return len(text.strip()) <= max_length
