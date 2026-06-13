"""OpenCLIP embedding, feedback training, and candidate ranking."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import open_clip
import torch
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
DEFAULT_MODEL = "ViT-B-32"
DEFAULT_PRETRAINED = "laion2b_s34b_b79k"


@dataclass(frozen=True)
class ClipConfig:
    model_name: str = DEFAULT_MODEL
    pretrained: str = DEFAULT_PRETRAINED
    device: str = "cuda" if torch.cuda.is_available() else "cpu"


def list_images(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
        return [path]
    if not path.exists():
        return []
    return sorted(
        item
        for item in path.rglob("*")
        if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES
    )


class ClipEmbedder:
    def __init__(self, config: ClipConfig | None = None) -> None:
        self.config = config or ClipConfig()
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            self.config.model_name,
            pretrained=self.config.pretrained,
            device=self.config.device,
        )
        self.model.eval()

    @torch.inference_mode()
    def embed_images(self, image_paths: list[Path]) -> np.ndarray:
        vectors: list[np.ndarray] = []
        for image_path in tqdm(image_paths, desc="embedding images"):
            image = Image.open(image_path).convert("RGB")
            tensor = self.preprocess(image).unsqueeze(0).to(self.config.device)
            features = self.model.encode_image(tensor)
            features = features / features.norm(dim=-1, keepdim=True)
            vectors.append(features.cpu().numpy()[0])
        if not vectors:
            return np.empty((0, 0), dtype=np.float32)
        return np.vstack(vectors).astype(np.float32)


def write_embedding_cache(cache_path: Path, image_paths: list[Path], embeddings: np.ndarray) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        cache_path,
        paths=np.array([str(path) for path in image_paths]),
        embeddings=embeddings,
    )


def read_embedding_cache(cache_path: Path) -> tuple[list[Path], np.ndarray]:
    data = np.load(cache_path, allow_pickle=False)
    return [Path(str(item)) for item in data["paths"]], data["embeddings"]


def read_feedback(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def feedback_label(value: str) -> int | None:
    normalized = value.strip().lower()
    if normalized in {"approved", "selected", "shortlist", "like", "good"}:
        return 1
    if normalized in {"rejected", "reject", "bad", "dislike"}:
        return 0
    return None


def train_classifier(cache_path: Path, feedback_path: Path, model_path: Path) -> dict[str, Any]:
    image_paths, embeddings = read_embedding_cache(cache_path)
    index = {path.name: i for i, path in enumerate(image_paths)}
    index.update({str(path): i for i, path in enumerate(image_paths)})

    x_rows: list[np.ndarray] = []
    y_rows: list[int] = []
    used_records = 0
    for record in read_feedback(feedback_path):
        label = feedback_label(str(record.get("decision") or record.get("label") or ""))
        image_key = str(record.get("file") or record.get("image_path") or record.get("candidate_id") or "")
        row_index = index.get(image_key)
        if row_index is None:
            row_index = index.get(Path(image_key).name)
        if label is None or row_index is None:
            continue
        x_rows.append(embeddings[row_index])
        y_rows.append(label)
        used_records += 1

    if len(set(y_rows)) < 2:
        raise ValueError("Need at least one approved and one rejected feedback record.")

    classifier = Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", LogisticRegression(class_weight="balanced", max_iter=1000)),
        ]
    )
    classifier.fit(np.vstack(x_rows), np.array(y_rows))
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(classifier, model_path)
    return {"model_path": str(model_path), "feedback_records": used_records}


def rank_candidates(
    cache_path: Path,
    output_path: Path,
    model_path: Path | None = None,
    positive_reference_dir: Path | None = None,
    top_k: int = 20,
) -> list[dict[str, Any]]:
    image_paths, embeddings = read_embedding_cache(cache_path)
    if embeddings.size == 0:
        ranked: list[dict[str, Any]] = []
    elif model_path and model_path.exists():
        classifier = joblib.load(model_path)
        scores = classifier.predict_proba(embeddings)[:, 1]
        ranked = _rank_rows(image_paths, scores, top_k)
    elif positive_reference_dir:
        ref_paths = list_images(positive_reference_dir)
        if not ref_paths:
            raise ValueError(f"No reference images found: {positive_reference_dir}")
        ref_embeddings = ClipEmbedder().embed_images(ref_paths)
        scores = cosine_similarity(embeddings, ref_embeddings).mean(axis=1)
        ranked = _rank_rows(image_paths, scores, top_k)
    else:
        raise ValueError("Provide either --model-path or --positive-reference-dir.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"ranked": ranked}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ranked


def _rank_rows(image_paths: list[Path], scores: np.ndarray, top_k: int) -> list[dict[str, Any]]:
    order = np.argsort(-scores)[:top_k]
    return [
        {
            "rank": rank + 1,
            "score": round(float(scores[index]) * 100, 2),
            "file": str(image_paths[index]),
            "candidate_id": image_paths[index].stem,
        }
        for rank, index in enumerate(order)
    ]
