"""Product library helpers for Brand Event Console."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PRODUCTS_DIR = ROOT / "products"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def product_key(category: str, product_id: str) -> str:
    return f"{category}/{product_id}"


def split_product_key(value: str) -> tuple[str, str]:
    parts = str(value or "").replace("\\", "/").strip("/").split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("product_id must use category/product_id format")
    return parts[0], parts[1]


def resolve_product_asset(product_dir: Path, value: str) -> Path | None:
    if not value:
        return None
    raw = Path(str(value))
    target = raw if raw.is_absolute() else product_dir / raw
    target = target.resolve()
    if ROOT.resolve() not in [target, *target.parents]:
        raise ValueError("Product asset escapes project boundary")
    return target


def _asset_payload(product_dir: Path, value: str, product_id: str, field: str) -> dict[str, str]:
    path = resolve_product_asset(product_dir, value)
    if not path:
        return {"path": "", "absolute_path": "", "comfyui_name": "", "url": ""}
    try:
        relative_path = str(path.relative_to(product_dir.resolve())).replace("\\", "/")
    except ValueError:
        relative_path = str(path.relative_to(ROOT.resolve())).replace("\\", "/")
    return {
        "path": relative_path,
        "absolute_path": str(path),
        "comfyui_name": path.name,
        "url": f"/api/products/{product_id}/asset/{field}" if path.exists() else "",
    }


def load_product(category: str, product_id: str) -> dict[str, Any]:
    product_dir = (PRODUCTS_DIR / category / product_id).resolve()
    if PRODUCTS_DIR.resolve() not in [product_dir, *product_dir.parents]:
        raise ValueError("Product path escapes products directory")
    data = read_json(product_dir / "product.json", {})
    if not data:
        raise FileNotFoundError(f"product.json not found for {category}/{product_id}")

    key = product_key(category, product_id)
    data.setdefault("category", category)
    data.setdefault("product_id", product_id)
    data["library_id"] = key
    data["product_dir"] = str(product_dir)
    data["main_image_asset"] = _asset_payload(product_dir, data.get("main_image", ""), key, "main")
    data["mask_image_asset"] = _asset_payload(product_dir, data.get("mask_image", ""), key, "mask")

    refs = []
    refs_dir = product_dir / "brand_style_refs"
    if refs_dir.exists():
        for path in sorted(refs_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                refs.append({
                    "name": path.name,
                    "absolute_path": str(path.resolve()),
                    "comfyui_name": path.name,
                    "url": f"/api/products/{key}/asset/ref/{path.name}",
                })
    data["brand_style_refs"] = refs
    data["prompt_fragments"] = read_json(product_dir / "prompt_fragments.json", {})
    return data


def list_products() -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    if not PRODUCTS_DIR.exists():
        return products
    for product_json in sorted(PRODUCTS_DIR.glob("*/*/product.json")):
        product_dir = product_json.parent
        category = product_dir.parent.name
        product_id = product_dir.name
        try:
            product = load_product(category, product_id)
        except Exception:
            continue
        products.append({
            "id": product["library_id"],
            "category": category,
            "product_id": product_id,
            "brand_name": product.get("brand_name", ""),
            "product_name": product.get("product_name", product_id),
            "main_image_url": product.get("main_image_asset", {}).get("url", ""),
            "recommended_workflows": product.get("recommended_workflows", []),
            "tone": product.get("tone", []),
        })
    return products


def load_product_from_event(event_input: dict[str, Any]) -> dict[str, Any] | None:
    key = event_input.get("productLibraryId") or event_input.get("product_id") or ""
    if not key:
        return None
    category, product_id = split_product_key(str(key))
    return load_product(category, product_id)
