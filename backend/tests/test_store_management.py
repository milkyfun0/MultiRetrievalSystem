from pathlib import Path

from app.core.config import get_settings
from tests.conftest import wait_for_job


def _create_demo_store(client, tmp_path: Path):
    resource_dir = tmp_path / "ImageRetrieval"
    resource_dir.mkdir(parents=True, exist_ok=True)
    for idx in range(3):
        (resource_dir / f"sample_{idx}.jpg").write_bytes(f"image-{idx}".encode())

    job = client.post(
        "/api/v1/vectorize",
        json={
            "scene": "Text2Image",
            "store_type": "Folder",
            "store_name": "demo-store",
            "store_description": "demo desc",
            "keys": [str(resource_dir)],
            "params": {"model_alias": "prod", "batch_size": 2, "force_rebuild": True},
        },
    )
    job.raise_for_status()
    payload = job.json()
    task = wait_for_job(client, payload["job_id"])
    assert task["state"] == "success"
    return payload["store_id"]


def test_store_detail_returns_file_and_vector_counts(client, temp_data_dir):
    store_id = _create_demo_store(client, temp_data_dir)

    resp = client.get(f"/api/v1/stores/{store_id}")
    resp.raise_for_status()
    body = resp.json()
    assert body["file_count"] == 3
    assert body["vector_count"] == 3

    status_resp = client.get(f"/api/v1/stores/{store_id}/status")
    status_resp.raise_for_status()
    status_body = status_resp.json()
    assert status_body["file_count"] == 3
    assert status_body["vector_count"] == 3


def test_delete_store_removes_index_and_metadata(client, temp_data_dir):
    store_id = _create_demo_store(client, temp_data_dir)

    settings = get_settings()
    faiss_npy = Path(settings.faiss_dir) / f"{store_id}.npy"
    faiss_meta = Path(settings.faiss_dir) / f"{store_id}.json"
    managed_dir = Path(settings.managed_assets_dir) / "Text2Image" / store_id
    assert faiss_npy.exists()
    assert faiss_meta.exists()
    assert managed_dir.exists()

    resp = client.delete(f"/api/v1/stores/{store_id}")
    resp.raise_for_status()
    body = resp.json()
    assert body["status"] == "deleted"

    assert client.get(f"/api/v1/stores/{store_id}").status_code == 404
    assert not faiss_npy.exists()
    assert not faiss_meta.exists()
    assert not managed_dir.exists()


def test_task_result_contains_file_and_vector_counters(client, temp_data_dir):
    resource_dir = temp_data_dir / "MedicalRetrieval"
    resource_dir.mkdir(parents=True, exist_ok=True)
    for idx in range(2):
        (resource_dir / f"case_{idx}.jpg").write_bytes(f"medical-{idx}".encode())

    resp = client.post(
        "/api/v1/vectorize",
        json={
            "scene": "Image2Image",
            "store_type": "Folder",
            "store_name": "medical-store",
            "store_description": "medical desc",
            "keys": [str(resource_dir)],
            "params": {"model_alias": "prod", "batch_size": 2, "force_rebuild": True},
        },
    )
    resp.raise_for_status()
    task = wait_for_job(client, resp.json()["job_id"])

    assert task["result"]["new_files"] == 2
    assert task["result"]["new_vectors"] == 2
    assert task["result"]["skipped_files"] == 0
    assert task["result"]["file_count"] == 2
    assert task["result"]["vector_count"] == 2


def test_managed_resource_copy_survives_source_file_rename(client, temp_data_dir):
    resource_dir = temp_data_dir / "VideoRetrieval"
    resource_dir.mkdir(parents=True, exist_ok=True)
    source_file = resource_dir / "video0.mp4"
    source_file.write_bytes(b"video-data")

    resp = client.post(
        "/api/v1/vectorize",
        json={
            "scene": "Text2Video",
            "store_type": "Folder",
            "store_name": "managed-video-store",
            "store_description": "video demo",
            "keys": [str(resource_dir)],
            "params": {"model_alias": "prod", "batch_size": 2, "force_rebuild": True},
        },
    )
    resp.raise_for_status()
    task = wait_for_job(client, resp.json()["job_id"])
    store_id = task["result"]["store_id"]

    detail = client.get(f"/api/v1/stores/{store_id}").json()
    assert detail["file_count"] == 1

    source_file.rename(resource_dir / "video0_renamed.mp4")

    search_resp = client.post(
        "/api/v1/search",
        json={
            "scene": "Text2Video",
            "store_type": "Folder",
            "topk": 1,
            "need_vectorize": False,
            "input": {"text": "video", "image_object_keys": []},
            "params": {"model_alias": "prod", "auto_prepare": False, "batch_mode": False},
        },
    )
    search_resp.raise_for_status()
    body = search_resp.json()
    assert body["meta"]["store_status"] == "ready"
    assert len(body["results"]) == 1
    assert "video0.mp4" in body["results"][0]["object_key"]
