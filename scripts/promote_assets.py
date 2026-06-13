"""Asset promotion boundary.

Future implementation should promote QA-approved reusable assets from a run
into `assets/reusable` and update indexes.
"""

from pathlib import Path


def promotion_target(asset_id: str) -> Path:
    return Path("assets") / "reusable" / asset_id
