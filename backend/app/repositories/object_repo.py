from __future__ import annotations

import uuid
from typing import Any

from app.models.sqlite import Database
from app.utils.time import now_iso


class ObjectRepo:
    def __init__(self, db: Database):
        self.db = db

    def upsert(
        self,
        store_id: str,
        object_key: str,
        media_type: str,
        preview_url: str | None,
        source_label: str | None,
        *,
        source_path_original: str | None = None,
        managed_relpath: str | None = None,
        managed_object_key: str | None = None,
        content_hash: str | None = None,
        file_size: int | None = None,
        filename: str | None = None,
        storage_backend: str | None = None,
        parent_video_name: str | None = None,
        segment_start_sec: float | None = None,
        segment_end_sec: float | None = None,
        frame_timestamp_sec: float | None = None,
        derive_type: str | None = None,
    ) -> dict[str, Any]:
        existing = self.get_by_store_and_key(store_id, object_key)
        if existing:
            with self.db.connect() as conn:
                conn.execute(
                    """
                    UPDATE objects
                    SET media_type = ?,
                        preview_url = ?,
                        source_label = ?,
                        is_active = 1,
                        source_path_original = ?,
                        managed_relpath = ?,
                        managed_object_key = ?,
                        content_hash = ?,
                        file_size = ?,
                        filename = ?,
                        storage_backend = ?,
                        parent_video_name = ?,
                        segment_start_sec = ?,
                        segment_end_sec = ?,
                        frame_timestamp_sec = ?,
                        derive_type = ?,
                        last_seen_at = ?
                    WHERE object_id = ?
                    """,
                    (
                        media_type,
                        preview_url,
                        source_label,
                        source_path_original,
                        managed_relpath,
                        managed_object_key,
                        content_hash,
                        file_size,
                        filename,
                        storage_backend,
                        parent_video_name,
                        segment_start_sec,
                        segment_end_sec,
                        frame_timestamp_sec,
                        derive_type,
                        now_iso(),
                        existing["object_id"],
                    ),
                )
            return self.get(existing["object_id"])
        payload = {
            "object_id": f"obj_{uuid.uuid4().hex[:10]}",
            "store_id": store_id,
            "object_key": object_key,
            "media_type": media_type,
            "preview_url": preview_url,
            "source_label": source_label,
            "created_at": now_iso(),
            "source_path_original": source_path_original,
            "managed_relpath": managed_relpath,
            "managed_object_key": managed_object_key,
            "content_hash": content_hash,
            "file_size": file_size,
            "filename": filename,
            "storage_backend": storage_backend,
            "last_seen_at": now_iso(),
            "parent_video_name": parent_video_name,
            "segment_start_sec": segment_start_sec,
            "segment_end_sec": segment_end_sec,
            "frame_timestamp_sec": frame_timestamp_sec,
            "derive_type": derive_type,
        }
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO objects(
                    object_id, store_id, object_key, media_type, preview_url, source_label,
                    is_active, created_at, source_path_original, managed_relpath,
                    managed_object_key, content_hash, file_size, filename, storage_backend,
                    last_seen_at, parent_video_name, segment_start_sec, segment_end_sec,
                    frame_timestamp_sec, derive_type
                )
                VALUES (
                    :object_id, :store_id, :object_key, :media_type, :preview_url, :source_label,
                    1, :created_at, :source_path_original, :managed_relpath,
                    :managed_object_key, :content_hash, :file_size, :filename, :storage_backend,
                    :last_seen_at, :parent_video_name, :segment_start_sec, :segment_end_sec,
                    :frame_timestamp_sec, :derive_type
                )
                """,
                payload,
            )
        return payload

    def get(self, object_id: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM objects WHERE object_id = ?", (object_id,)).fetchone()
        return dict(row) if row else None

    def get_by_store_and_key(self, store_id: str, object_key: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM objects WHERE store_id = ? AND object_key = ? LIMIT 1",
                (store_id, object_key),
            ).fetchone()
        return dict(row) if row else None

    def list_by_store(self, store_id: str, *, active_only: bool = True) -> list[dict[str, Any]]:
        sql = "SELECT * FROM objects WHERE store_id = ?"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY created_at ASC"
        with self.db.connect() as conn:
            rows = conn.execute(sql, (store_id,)).fetchall()
        return [dict(r) for r in rows]

    def count_by_store(self, store_id: str, *, active_only: bool = False) -> int:
        sql = "SELECT COUNT(*) AS c FROM objects WHERE store_id = ?"
        if active_only:
            sql += " AND is_active = 1"
        with self.db.connect() as conn:
            row = conn.execute(sql, (store_id,)).fetchone()
        return int(row["c"]) if row else 0

    def mark_seen(self, object_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute("UPDATE objects SET is_active = 1, last_seen_at = ? WHERE object_id = ?", (now_iso(), object_id))

    def deactivate_missing(self, store_id: str, keep_object_keys: set[str]) -> list[str]:
        active_rows = self.list_by_store(store_id, active_only=True)
        missing_ids = [row["object_id"] for row in active_rows if row["object_key"] not in keep_object_keys]
        if not missing_ids:
            return []
        placeholders = ",".join("?" for _ in missing_ids)
        with self.db.connect() as conn:
            conn.execute(
                f"UPDATE objects SET is_active = 0 WHERE store_id = ? AND object_id IN ({placeholders})",
                [store_id, *missing_ids],
            )
        return missing_ids

    def soft_delete_by_store(self, store_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute("UPDATE objects SET is_active = 0 WHERE store_id = ?", (store_id,))

    def delete_by_store(self, store_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM objects WHERE store_id = ?", (store_id,))
