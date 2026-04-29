import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _has_column(self, conn, table: str, column: str) -> bool:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(r[1] == column for r in rows)

    def _ensure_column(self, conn, table: str, column: str, ddl: str) -> None:
        if not self._has_column(conn, table, column):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS stores (
                    store_id TEXT PRIMARY KEY,
                    store_name TEXT NOT NULL,
                    store_description TEXT,
                    scene TEXT NOT NULL,
                    store_type TEXT NOT NULL,
                    resource_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_index_id TEXT,
                    model_alias TEXT NOT NULL,
                    preprocess_mode TEXT,
                    interval_sec INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS objects (
                    object_id TEXT PRIMARY KEY,
                    store_id TEXT NOT NULL,
                    object_key TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    preview_url TEXT,
                    source_label TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    source_path_original TEXT,
                    managed_relpath TEXT,
                    managed_object_key TEXT,
                    content_hash TEXT,
                    file_size INTEGER,
                    filename TEXT,
                    storage_backend TEXT,
                    last_seen_at TEXT,
                    parent_video_name TEXT,
                    segment_start_sec REAL,
                    segment_end_sec REAL,
                    frame_timestamp_sec REAL,
                    derive_type TEXT,
                    UNIQUE(store_id, object_key)
                );

                CREATE TABLE IF NOT EXISTS vectors (
                    vector_id TEXT PRIMARY KEY,
                    store_id TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    faiss_id INTEGER NOT NULL,
                    scene TEXT NOT NULL,
                    model_alias TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    embedding_json TEXT,
                    UNIQUE(store_id, object_id, model_version)
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    scene TEXT NOT NULL,
                    store_id TEXT,
                    state TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    message TEXT,
                    error TEXT,
                    payload_json TEXT,
                    result_json TEXT,
                    terminated_at TEXT,
                    terminate_reason TEXT,
                    phase TEXT,
                    can_terminate INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._ensure_column(conn, "stores", "store_description", "store_description TEXT")
            self._ensure_column(conn, "stores", "preprocess_mode", "preprocess_mode TEXT")
            self._ensure_column(conn, "stores", "interval_sec", "interval_sec INTEGER")
            self._ensure_column(conn, "jobs", "payload_json", "payload_json TEXT")
            self._ensure_column(conn, "jobs", "terminated_at", "terminated_at TEXT")
            self._ensure_column(conn, "jobs", "terminate_reason", "terminate_reason TEXT")
            self._ensure_column(conn, "jobs", "phase", "phase TEXT")
            self._ensure_column(conn, "jobs", "can_terminate", "can_terminate INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "objects", "source_path_original", "source_path_original TEXT")
            self._ensure_column(conn, "objects", "managed_relpath", "managed_relpath TEXT")
            self._ensure_column(conn, "objects", "managed_object_key", "managed_object_key TEXT")
            self._ensure_column(conn, "objects", "content_hash", "content_hash TEXT")
            self._ensure_column(conn, "objects", "file_size", "file_size INTEGER")
            self._ensure_column(conn, "objects", "filename", "filename TEXT")
            self._ensure_column(conn, "objects", "storage_backend", "storage_backend TEXT")
            self._ensure_column(conn, "objects", "last_seen_at", "last_seen_at TEXT")
            self._ensure_column(conn, "objects", "parent_video_name", "parent_video_name TEXT")
            self._ensure_column(conn, "objects", "segment_start_sec", "segment_start_sec REAL")
            self._ensure_column(conn, "objects", "segment_end_sec", "segment_end_sec REAL")
            self._ensure_column(conn, "objects", "frame_timestamp_sec", "frame_timestamp_sec REAL")
            self._ensure_column(conn, "objects", "derive_type", "derive_type TEXT")
            self._ensure_column(conn, "vectors", "embedding_json", "embedding_json TEXT")
