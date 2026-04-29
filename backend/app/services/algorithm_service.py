from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import httpx
import numpy as np

from app.core.enums import to_algorithm_scene
from app.utils.normalize import normalize_to_str_list


class HttpAlgorithmService:
    def __init__(self, gateway_url: str):
        self.gateway_url = gateway_url.rstrip("/")

    def encode(self, scene: str, query: Any = None, key: Any = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        algorithm_scene = to_algorithm_scene(scene)
        payload = {
            "scene": algorithm_scene,
            "query": query,
            "key": key,
            "params": params or {},
        }

        # t2v 编码明显比图片编码更重，这里单独放宽 timeout
        timeout_seconds = 1200 if algorithm_scene == "t2v" else 300

        with httpx.Client(timeout=timeout_seconds, trust_env=False) as client:
            response = client.post(f"{self.gateway_url}/encode", json=payload)
            if response.status_code >= 400:
                body = response.text
                raise RuntimeError(
                    f"Algorithm encode failed: status={response.status_code}, "
                    f"scene={algorithm_scene}, body={body[:1000]}"
                )
            data = response.json()

        return {
            "scene": data.get("scene", algorithm_scene),
            "query_embed": data.get("query_embed", []) or [],
            "key_embed": data.get("key_embed", []) or [],
        }


class DeterministicAlgorithmService:
    vocabulary = [
        "cat", "dog", "bird", "airplane", "car", "band", "club", "lecture", "indoor",
        "medicine", "cell", "video", "image", "sunset", "dance", "mountain", "ocean"
    ]

    def _embed_one(self, value: str) -> list[float]:
        text = Path(value).stem.lower()
        vec = np.zeros(len(self.vocabulary) + 4, dtype=float)
        for idx, token in enumerate(self.vocabulary):
            if token in text:
                vec[idx] = 1.0
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        for i in range(4):
            vec[len(self.vocabulary) + i] = digest[i] / 255.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(float).tolist()

    def _embed_many(self, items: list[str]) -> list[list[float]]:
        return [self._embed_one(item) for item in items]

    def encode(self, scene: str, query: Any = None, key: Any = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query_items = normalize_to_str_list(query)
        key_items = normalize_to_str_list(key)
        return {
            "scene": to_algorithm_scene(scene),
            "query_embed": self._embed_many(query_items) if query_items else [],
            "key_embed": self._embed_many(key_items) if key_items else [],
        }