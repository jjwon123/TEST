"""Registry for ComfyUI workflow presets."""

from __future__ import annotations

from pathlib import Path

from services.comfyui.brand_workflows import brand_workflow_path, list_brand_workflows


PRESET_DIR = Path(__file__).parent / "presets"


def list_presets() -> list[str]:
    local = [path.stem for path in PRESET_DIR.glob("*.json")]
    return sorted([*local, *list_brand_workflows()])


def preset_path(name: str) -> Path:
    try:
        return brand_workflow_path(name)
    except FileNotFoundError:
        pass
    path = PRESET_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown ComfyUI preset: {name}")
    return path
