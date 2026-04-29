from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


class FaissLikeService:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _paths(self, store_id: str) -> tuple[Path, Path]:
        return self.base_dir / f"{store_id}.npy", self.base_dir / f"{store_id}.json"

    def get_index_paths(self, store_id: str) -> list[str]:
        data_path, meta_path = self._paths(store_id)
        return [str(data_path), str(meta_path)]

    def load_index(self, store_id: str) -> dict[str, Any]:
        data_path, meta_path = self._paths(store_id)
        if not data_path.exists() or not meta_path.exists():
            return {"vectors": np.zeros((0, 0), dtype=float), "next_id": 0, "index_id": f"index_{store_id}"}
        vectors = np.load(data_path)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return {"vectors": vectors, "next_id": meta["next_id"], "index_id": meta["index_id"]}

    def save_index(self, store_id: str, vectors: np.ndarray, next_id: int, index_id: str) -> None:
        data_path, meta_path = self._paths(store_id)
        np.save(data_path, vectors)
        meta_path.write_text(json.dumps({"next_id": next_id, "index_id": index_id}, ensure_ascii=False, indent=2), encoding="utf-8")

    def reset_index(self, store_id: str) -> str:
        index_id = f"index_{store_id}"
        self.save_index(store_id, np.zeros((0, 0), dtype=float), 0, index_id)
        return index_id

    def delete_index(self, store_id: str) -> list[str]:
        deleted: list[str] = []
        for path_str in self.get_index_paths(store_id):
            path = Path(path_str)
            if path.exists():
                path.unlink()
                deleted.append(str(path))
        return deleted

    def add_vectors(self, store_id: str, embeddings: list[list[float]]) -> tuple[list[int], str]:
        index = self.load_index(store_id)
        existing = index["vectors"]
        incoming = np.asarray(embeddings, dtype=float)
        if incoming.size == 0:
            return [], index["index_id"]
        merged = incoming if existing.size == 0 else np.vstack([existing, incoming])
        faiss_ids = list(range(index["next_id"], index["next_id"] + len(embeddings)))
        next_id = index["next_id"] + len(embeddings)
        self.save_index(store_id, merged, next_id, index["index_id"])
        return faiss_ids, index["index_id"]

    def search(self, store_id: str, query_vector: list[float], topk: int) -> list[tuple[int, float]]:
        index = self.load_index(store_id)
        vectors = index["vectors"]
        if vectors.size == 0:
            return []
        query = np.asarray(query_vector, dtype=float)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []
        scores = vectors @ query / (np.linalg.norm(vectors, axis=1) * query_norm + 1e-12)
        top_indices = np.argsort(-scores)[:topk]
        return [(int(i), float(scores[i])) for i in top_indices]
