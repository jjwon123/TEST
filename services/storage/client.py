"""Storage service boundary."""

from __future__ import annotations

from pathlib import Path


class StorageClient:
    def __init__(self, root: Path = Path(".")) -> None:
        self.root = root

    def resolve_run_path(self, run_id: str) -> Path:
        return self.root / "runs" / run_id

    def resolve_asset_path(self, asset_id: str, bucket: str = "reusable") -> Path:
        return self.root / "assets" / bucket / asset_id
