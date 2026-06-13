"""File-path based dynamic module loading for pipeline stage handlers."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Callable


def load_module_from_path(path: Path, module_prefix: str = "pipeline_handler") -> ModuleType:
    resolved = path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Handler file not found: {resolved}")

    digest = hashlib.sha1(str(resolved).encode("utf-8")).hexdigest()[:12]
    module_name = f"{module_prefix}_{resolved.stem}_{digest}"
    spec = importlib.util.spec_from_file_location(module_name, resolved)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from: {resolved}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_callable_from_path(path: Path, callable_name: str = "run") -> Callable:
    module = load_module_from_path(path)
    handler = getattr(module, callable_name, None)
    if handler is None or not callable(handler):
        raise AttributeError(f"{path} does not define callable '{callable_name}'")
    return handler
