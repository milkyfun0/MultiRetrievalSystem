from __future__ import annotations

import json
import uuid
from typing import Any

from app.models.sqlite import Database
from app.utils.time import now_iso


class JobRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(
        self,
        job_type: str,
        scene: str,
        store_id: str | None,
        state: str,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
        phase: str | None = None,
        can_terminate: bool = False,
    ) -> dict[str, Any]:
        job_id = f"prep_{uuid.uuid4().hex[:12]}"
        ts = now_iso()
        raw = {
            "job_id": job_id,
            "job_type": job_type,
            "scene": scene,
            "store_id": store_id,
            "state": state,
            "progress": 0,
            "message": message,
            "error": None,
            "payload_json": json.dumps(payload, ensure_ascii=False) if payload is not None else None,
            "result_json": None,
            "terminated_at": None,
            "terminate_reason": None,
            "phase": phase,
            "can_terminate": 1 if can_terminate else 0,
            "created_at": ts,
            "updated_at": ts,
        }
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs(
                    job_id, job_type, scene, store_id, state, progress, message, error,
                    payload_json, result_json, terminated_at, terminate_reason, phase,
                    can_terminate, created_at, updated_at
                )
                VALUES (
                    :job_id, :job_type, :scene, :store_id, :state, :progress, :message, :error,
                    :payload_json, :result_json, :terminated_at, :terminate_reason, :phase,
                    :can_terminate, :created_at, :updated_at
                )
                """,
                raw,
            )
        return self.get(job_id)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["payload"] = json.loads(item["payload_json"]) if item.get("payload_json") else None
        item["result"] = json.loads(item["result_json"]) if item.get("result_json") else None
        item["can_terminate"] = bool(item.get("can_terminate"))
        return item

    def update(self, job_id: str, **fields: Any) -> dict[str, Any] | None:
        existing = self.get(job_id)
        if not existing:
            return None
        merged = {**existing, **fields, "updated_at": now_iso()}
        merged["payload_json"] = json.dumps(merged.get("payload"), ensure_ascii=False) if merged.get("payload") is not None else None
        merged["result_json"] = json.dumps(merged.get("result"), ensure_ascii=False) if merged.get("result") is not None else None
        merged["can_terminate"] = 1 if bool(merged.get("can_terminate")) else 0
        with self.db.connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET job_type = :job_type,
                    scene = :scene,
                    store_id = :store_id,
                    state = :state,
                    progress = :progress,
                    message = :message,
                    error = :error,
                    payload_json = :payload_json,
                    result_json = :result_json,
                    terminated_at = :terminated_at,
                    terminate_reason = :terminate_reason,
                    phase = :phase,
                    can_terminate = :can_terminate,
                    updated_at = :updated_at
                WHERE job_id = :job_id
                """,
                merged,
            )
        return self.get(job_id)

    def delete_by_store(self, store_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM jobs WHERE store_id = ?", (store_id,))
