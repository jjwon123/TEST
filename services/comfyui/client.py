"""ComfyUI client boundary.

The pipeline should call this module through a narrow interface instead of
embedding ComfyUI HTTP details inside stage handlers. The current version keeps
network calls out, but the method signatures show where queue submission and
status polling will live.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from services.comfyui.preset_adapters import build_api_prompt


@dataclass
class ComfyUIJob:
    prompt_id: str
    workflow_preset: str
    payload: dict[str, Any]


class ComfyUIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188", timeout_seconds: int = 1200) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def build_submission(self, job: ComfyUIJob) -> dict[str, Any]:
        """Return the request shape that will later be posted to ComfyUI."""
        api_prompt = build_api_prompt(job.workflow_preset, job.payload)
        return {
            "target": f"{self.base_url}/prompt",
            "prompt_id": job.prompt_id,
            "workflow_preset": job.workflow_preset,
            "payload": job.payload,
            "api_prompt": api_prompt,
        }

    def submit(self, job: ComfyUIJob) -> dict[str, Any]:
        """Return a dry-run submission payload for inspection."""
        submission = self.build_submission(job)
        submission["status"] = "dry_run"
        return submission

    def run_image_job(self, job: ComfyUIJob) -> dict[str, Any]:
        """Queue a ComfyUI prompt, wait for completion, and return image bytes."""
        job = self._with_uploaded_inputs(job)
        submission = self.build_submission(job)
        client_id = str(uuid4())
        prompt_response = self._post_json("/prompt", {
            "prompt": submission["api_prompt"],
            "client_id": client_id,
        })
        comfy_prompt_id = prompt_response.get("prompt_id")
        if not comfy_prompt_id:
            raise RuntimeError(f"ComfyUI did not return prompt_id: {prompt_response}")

        history = self._wait_for_history(str(comfy_prompt_id))
        images = self._extract_images(history, str(comfy_prompt_id))
        if not images:
            raise RuntimeError(f"ComfyUI job completed without image outputs: {comfy_prompt_id}")

        first = images[0]
        image_bytes = self._get_bytes("/view", {
            "filename": first["filename"],
            "subfolder": first.get("subfolder", ""),
            "type": first.get("type", "output"),
        })
        return {
            "status": "generated",
            "target": submission["target"],
            "prompt_id": job.prompt_id,
            "workflow_preset": job.workflow_preset,
            "comfyui_prompt_id": comfy_prompt_id,
            "outputs": images,
            "image_bytes": image_bytes,
        }

    def _with_uploaded_inputs(self, job: ComfyUIJob) -> ComfyUIJob:
        payload = dict(job.payload)
        product_image = self._upload_if_present(payload.get("product_image_path"), payload.get("product_image"))
        product_mask = self._upload_if_present(payload.get("product_mask_path"), payload.get("product_mask"))
        if product_image:
            payload["product_image"] = product_image
        if product_mask:
            payload["product_mask"] = product_mask
        uploaded_refs = []
        for path, fallback in zip(payload.get("reference_image_paths") or [], payload.get("reference_images") or []):
            uploaded = self._upload_if_present(path, fallback)
            if uploaded:
                uploaded_refs.append(uploaded)
        if uploaded_refs:
            payload["reference_images"] = uploaded_refs
        return ComfyUIJob(prompt_id=job.prompt_id, workflow_preset=job.workflow_preset, payload=payload)

    def _upload_if_present(self, path_value: Any, fallback_name: Any = "") -> str:
        if not path_value:
            return str(fallback_name or "")
        path = Path(str(path_value))
        if not path.exists() or not path.is_file():
            return str(fallback_name or path.name)
        return self._upload_image(path)

    def _upload_image(self, path: Path) -> str:
        boundary = f"----CodexComfyBoundary{uuid4().hex}"
        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
        footer = (
            f"\r\n--{boundary}\r\n"
            'Content-Disposition: form-data; name="type"\r\n\r\n'
            "input\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
            "true\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/upload/image",
            data=header + path.read_bytes() + footer,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"Could not upload ComfyUI input image: {exc}") from exc
        return result.get("name") or path.name

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ComfyUI {path} returned HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not reach ComfyUI at {self.base_url}: {exc}") from exc

    def _get_json(self, path: str) -> dict[str, Any]:
        try:
            with urlopen(f"{self.base_url}{path}", timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"Could not reach ComfyUI at {self.base_url}: {exc}") from exc

    def _get_bytes(self, path: str, params: dict[str, Any]) -> bytes:
        url = f"{self.base_url}{path}?{urlencode(params)}"
        try:
            with urlopen(url, timeout=60) as response:
                return response.read()
        except URLError as exc:
            raise RuntimeError(f"Could not download ComfyUI output: {exc}") from exc

    def _wait_for_history(self, comfy_prompt_id: str) -> dict[str, Any]:
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            history = self._get_json(f"/history/{comfy_prompt_id}")
            if comfy_prompt_id in history:
                record = history[comfy_prompt_id]
                status = record.get("status", {})
                if status.get("completed") is False and status.get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI job failed: {status}")
                return history
            time.sleep(1.0)
        raise TimeoutError(f"Timed out waiting for ComfyUI prompt: {comfy_prompt_id}")

    def _extract_images(self, history: dict[str, Any], comfy_prompt_id: str) -> list[dict[str, Any]]:
        record = history.get(comfy_prompt_id, {})
        outputs = record.get("outputs", {})
        images: list[dict[str, Any]] = []
        for node_output in outputs.values():
            for image in node_output.get("images", []):
                images.append(dict(image))
        return images
