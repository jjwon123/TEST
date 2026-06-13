"""Notification service boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_notification(event: str, run_id: str, stage_id: str | None, message: str) -> dict[str, Any]:
    return {
        "event": event,
        "run_id": run_id,
        "stage_id": stage_id,
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "dry_run"
    }
