"""Channel policy registry.

Channel policies live in `core/channels/*.json`. The registry keeps handlers
data-driven: stages ask for channel policy by ID or requested channel alias,
instead of hardcoding channel-to-template mapping in handler code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils.json_io import read_json


ROOT = Path(__file__).resolve().parents[2]
CHANNEL_DIR = ROOT / "core" / "channels"


class ChannelRegistryError(LookupError):
    pass


def get(channel_id: str) -> dict[str, Any]:
    channel_id = normalize_token(channel_id)
    path = _path_for(channel_id)
    if not path.exists():
        available = ", ".join(sorted(policy["channel_id"] for policy in list_all()))
        raise ChannelRegistryError(
            f"Channel policy not found for '{channel_id}'. Expected {path}. Available channel ids: {available}"
        )
    policy = read_json(path)
    if policy.get("channel_id") != channel_id:
        raise ChannelRegistryError(
            f"Channel policy id mismatch in {path}: expected '{channel_id}', got '{policy.get('channel_id')}'"
        )
    return policy


def list_all() -> list[dict[str, Any]]:
    policies = []
    for path in sorted(CHANNEL_DIR.glob("*.json")):
        policies.append(read_json(path))
    return policies


def resolve_requested(requested_channel: str) -> list[str]:
    """Resolve an operator-facing channel token to concrete channel policy ids."""
    requested_channel = normalize_token(requested_channel)
    exact_path = _path_for(requested_channel)
    if exact_path.exists():
        return [requested_channel]

    matches = []
    for policy in list_all():
        aliases = [normalize_token(alias) for alias in policy.get("aliases", [])]
        if requested_channel == policy.get("channel_id") or requested_channel in aliases:
            matches.append(policy["channel_id"])

    if not matches:
        available = ", ".join(sorted(policy["channel_id"] for policy in list_all()))
        raise ChannelRegistryError(
            f"Requested channel '{requested_channel}' does not match any channel_id or alias. Available channel ids: {available}"
        )
    policies_by_id = {policy["channel_id"]: policy for policy in list_all()}
    return sorted(
        matches,
        key=lambda channel_id: (
            policies_by_id[channel_id].get("planning_order", 100),
            channel_id,
        ),
    )


def canonicalize(channel_id: str) -> str:
    """Return one canonical channel id for an existing canonical id or alias.

    Aliases that expand to multiple concrete channels are ambiguous for a
    single-output context and must be resolved upstream.
    """
    matches = resolve_requested(channel_id)
    if len(matches) != 1:
        raise ChannelRegistryError(
            f"Channel alias '{channel_id}' expands to multiple canonical ids: {', '.join(matches)}"
        )
    return matches[0]


def normalize_token(value: str) -> str:
    return str(value).strip().lower().replace("-", "_")


def _path_for(channel_id: str) -> Path:
    return CHANNEL_DIR / f"{channel_id.replace('_', '-')}.json"
