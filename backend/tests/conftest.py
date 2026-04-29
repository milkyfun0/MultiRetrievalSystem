import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.main import app


@pytest.fixture()
def temp_data_dir(monkeypatch):
    root = Path(tempfile.mkdtemp(prefix="mmr_backend_test_"))
    sqlite_path = root / "sqlite" / "app.db"
    faiss_dir = root / "faiss"
    query_upload_dir = root / "query_uploads"
    managed_assets_dir = root / "assets"
    preprocess_temp_dir = root / "preprocess_tmp"
    monkeypatch.setenv("MMR_SQLITE_PATH", str(sqlite_path))
    monkeypatch.setenv("MMR_FAISS_DIR", str(faiss_dir))
    monkeypatch.setenv("MMR_QUERY_UPLOAD_DIR", str(query_upload_dir))
    monkeypatch.setenv("MMR_MANAGED_ASSETS_DIR", str(managed_assets_dir))
    monkeypatch.setenv("MMR_PREPROCESS_TEMP_DIR", str(preprocess_temp_dir))
    monkeypatch.setenv("MMR_ALGORITHM_MODE", "deterministic")
    get_settings.cache_clear()
    yield root
    get_settings.cache_clear()
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture()
def client(temp_data_dir):
    with TestClient(app) as c:
        yield c


def wait_for_job(client: TestClient, job_id: str, timeout: float = 10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/v1/tasks/{job_id}")
        resp.raise_for_status()
        data = resp.json()
        if data["state"] in {"success", "failed", "terminated"}:
            return data
        time.sleep(0.05)
    raise TimeoutError(f"job {job_id} did not finish in time")
