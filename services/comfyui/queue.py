"""Queue state helpers for ComfyUI jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def new_queue_record(prompt_id: str, status: str = "queued") -> dict[str, Any]:
    return {
        "prompt_id": prompt_id,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "comfyui_queue_id": None,
        "outputs": [],
        "errors": [],
    }
