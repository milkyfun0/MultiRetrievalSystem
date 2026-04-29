from __future__ import annotations

import uuid
from typing import Any

from app.models.sqlite import Database
from app.utils.time import now_iso


class StoreRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(
        self,
        store_name: str,
        store_description: str | None,
        scene: str,
        store_type: str,
        resource_path: str,
        model_alias: str,
        status: str,
        preprocess_mode: str | None = None,
        interval_sec: int | None = None,
    ) -> dict[str, Any]:
        store_id = f"store_{uuid.uuid4().hex[:8]}"
        ts = now_iso()
        payload = {
            "store_id": store_id,
            "store_name": store_name,
            "store_description": store_description,
            "scene": scene,
            "store_type": store_type,
            "resource_path": resource_path,
            "status": status,
            "current_index_id": None,
            "model_alias": model_alias,
            "preprocess_mode": preprocess_mode,
            "interval_sec": interval_sec,
            "created_at": ts,
            "updated_at": ts,
        }
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO stores(
                    store_id, store_name, store_description, scene, store_type, resource_path,
                    status, current_index_id, model_alias, preprocess_mode, interval_sec,
                    created_at, updated_at
                )
                VALUES (
                    :store_id, :store_name, :store_description, :scene, :store_type, :resource_path,
                    :status, :current_index_id, :model_alias, :preprocess_mode, :interval_sec,
                    :created_at, :updated_at
                )
                """,
                payload,
            )
        return payload

    def list(self) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM stores ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

    def get(self, store_id: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM stores WHERE store_id = ?", (store_id,)).fetchone()
        return dict(row) if row else None

    def find_by_identity(self, scene: str, store_type: str, resource_path: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM stores WHERE scene = ? AND store_type = ? AND resource_path = ? ORDER BY updated_at DESC LIMIT 1",
                (scene, store_type, resource_path),
            ).fetchone()
        return dict(row) if row else None

    def find_by_name(self, scene: str, store_type: str, store_name: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM stores WHERE scene = ? AND store_type = ? AND store_name = ? ORDER BY updated_at DESC LIMIT 1",
                (scene, store_type, store_name),
            ).fetchone()
        return dict(row) if row else None

    def get_latest_by_scene_store_type(self, scene: str, store_type: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM stores
                WHERE scene = ? AND store_type = ?
                ORDER BY CASE status WHEN 'ready' THEN 0 WHEN 'preparing' THEN 1 WHEN 'not_ready' THEN 2 ELSE 3 END,
                         updated_at DESC
                LIMIT 1
                """,
                (scene, store_type),
            ).fetchone()
        return dict(row) if row else None

    def update(self, store_id: str, **fields: Any) -> dict[str, Any] | None:
        existing = self.get(store_id)
        if not existing:
            return None
        merged = {**existing, **fields, "updated_at": now_iso()}
        with self.db.connect() as conn:
            conn.execute(
                """
                UPDATE stores
                SET store_name = :store_name,
                    store_description = :store_description,
                    scene = :scene,
                    store_type = :store_type,
                    resource_path = :resource_path,
                    status = :status,
                    current_index_id = :current_index_id,
                    model_alias = :model_alias,
                    preprocess_mode = :preprocess_mode,
                    interval_sec = :interval_sec,
                    updated_at = :updated_at
                WHERE store_id = :store_id
                """,
                merged,
            )
        return self.get(store_id)

    def delete(self, store_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM stores WHERE store_id = ?", (store_id,))

    def update_status(self, store_id: str, status: str, current_index_id: str | None = None) -> dict[str, Any] | None:
        existing = self.get(store_id)
        if not existing:
            return None
        fields = {"status": status}
        if current_index_id is not None:
            fields["current_index_id"] = current_index_id
        return self.update(store_id, **fields)
