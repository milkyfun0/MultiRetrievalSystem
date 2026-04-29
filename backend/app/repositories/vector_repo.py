from __future__ import annotations

import json
import uuid
from typing import Any

from app.models.sqlite import Database
from app.utils.time import now_iso


class VectorRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, store_id: str, object_id: str, faiss_id: int, scene: str, model_alias: str, model_version: str, embedding: list[float]) -> dict[str, Any]:
        payload = {
            "vector_id": f"vec_{uuid.uuid4().hex[:10]}",
            "store_id": store_id,
            "object_id": object_id,
            "faiss_id": faiss_id,
            "scene": scene,
            "model_alias": model_alias,
            "model_version": model_version,
            "created_at": now_iso(),
            "embedding_json": json.dumps(embedding, ensure_ascii=False),
        }
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO vectors(vector_id, store_id, object_id, faiss_id, scene, model_alias, model_version, created_at, embedding_json)
                VALUES (:vector_id, :store_id, :object_id, :faiss_id, :scene, :model_alias, :model_version, :created_at, :embedding_json)
                """,
                payload,
            )
        return self.get_existing_for_object(store_id, object_id, model_version)

    def get_existing_for_object(self, store_id: str, object_id: str, model_version: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM vectors WHERE store_id = ? AND object_id = ? AND model_version = ? LIMIT 1",
                (store_id, object_id, model_version),
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["embedding"] = json.loads(item["embedding_json"]) if item.get("embedding_json") else None
        return item

    def list_by_store(self, store_id: str) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM vectors WHERE store_id = ? ORDER BY faiss_id ASC", (store_id,)).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["embedding"] = json.loads(item["embedding_json"]) if item.get("embedding_json") else None
            items.append(item)
        return items

    def list_active_with_embeddings(self, store_id: str) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT v.*, o.object_key, o.filename, o.is_active
                FROM vectors v
                JOIN objects o ON v.object_id = o.object_id
                WHERE v.store_id = ? AND o.is_active = 1
                ORDER BY o.created_at ASC, v.created_at ASC
                """,
                (store_id,),
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["embedding"] = json.loads(item["embedding_json"]) if item.get("embedding_json") else None
            items.append(item)
        return items

    def count_by_store(self, store_id: str) -> int:
        with self.db.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM vectors WHERE store_id = ?", (store_id,)).fetchone()
        return int(row["c"]) if row else 0

    def list_by_faiss_ids(self, store_id: str, faiss_ids: list[int]) -> list[dict[str, Any]]:
        if not faiss_ids:
            return []
        placeholders = ",".join("?" for _ in faiss_ids)
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM vectors WHERE store_id = ? AND faiss_id IN ({placeholders})",
                [store_id, *faiss_ids],
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["embedding"] = json.loads(item["embedding_json"]) if item.get("embedding_json") else None
            items.append(item)
        return items

    def delete_by_store(self, store_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM vectors WHERE store_id = ?", (store_id,))

    def delete_by_object_ids(self, store_id: str, object_ids: list[str]) -> None:
        if not object_ids:
            return
        placeholders = ",".join("?" for _ in object_ids)
        with self.db.connect() as conn:
            conn.execute(
                f"DELETE FROM vectors WHERE store_id = ? AND object_id IN ({placeholders})",
                [store_id, *object_ids],
            )

    def update_faiss_id(self, vector_id: str, faiss_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("UPDATE vectors SET faiss_id = ? WHERE vector_id = ?", (faiss_id, vector_id))
