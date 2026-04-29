from pathlib import Path

from app.core.config import get_settings
from tests.conftest import wait_for_job


def test_text2image_vectorize_and_search(client, temp_data_dir):
    folder = temp_data_dir / "images"
    folder.mkdir(parents=True)
    for name in ["cat_001.jpg", "dog_001.jpg", "bird_001.jpg"]:
        (folder / name).write_text("demo", encoding="utf-8")

    create_resp = client.post(
        "/api/v1/stores",
        json={
            "store_name": "demo_image_folder",
            "scene": "Text2Image",
            "store_type": "Folder",
            "resource_path": str(folder),
            "model_alias": "prod",
        },
    )
    assert create_resp.status_code == 200
    store_id = create_resp.json()["store_id"]

    vec_resp = client.post(
        "/api/v1/vectorize",
        json={
            "scene": "Text2Image",
            "store_type": "Folder",
            "store_name": "demo_image_folder_build",
            "keys": [store_id],
            "params": {"model_alias": "prod", "batch_size": 2, "force_rebuild": False},
        },
    )
    assert vec_resp.status_code == 200
    status = wait_for_job(client, vec_resp.json()["job_id"])
    assert status["state"] == "success"
    assert status["result"]["new_vectors"] == 3
    assert status["result"]["scanned_files"] == 3
    assert status["result"]["total_batches"] == 2

    search_resp = client.post(
        "/api/v1/search",
        json={
            "scene": "Text2Image",
            "store_type": "Folder",
            "topk": 2,
            "need_vectorize": False,
            "input": {"text": "cat", "image_object_keys": []},
            "params": {"model_alias": "prod", "auto_prepare": True, "batch_mode": False},
        },
    )
    assert search_resp.status_code == 200
    data = search_resp.json()
    assert data["meta"]["store_status"] == "ready"
    assert len(data["results"]) == 2
    assert "cat_001.jpg" in data["results"][0]["object_key"]
    assert data["results"][0]["preview_url"].startswith("http://127.0.0.1:8000/api/v1/media/preview")

    detail_resp = client.get(f"/api/v1/stores/{status['result']['store_id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["object_count"] == 3
    assert detail["active_object_count"] == 3
    assert detail["vector_count"] == 3


def test_auto_prepare_search_flow(client, temp_data_dir):
    folder = temp_data_dir / "videos"
    folder.mkdir(parents=True)
    for name in ["band_club_001.mp4", "lecture_indoor_001.mp4"]:
        (folder / name).write_text("demo", encoding="utf-8")

    create_resp = client.post(
        "/api/v1/stores",
        json={
            "store_name": "demo_video_folder",
            "scene": "Text2Video",
            "store_type": "Folder",
            "resource_path": str(folder),
            "model_alias": "prod",
        },
    )
    assert create_resp.status_code == 200

    search_resp = client.post(
        "/api/v1/search",
        json={
            "scene": "Text2Video",
            "store_type": "Folder",
            "topk": 5,
            "need_vectorize": False,
            "input": {"text": "band club", "image_object_keys": []},
            "params": {"model_alias": "prod", "auto_prepare": True, "batch_mode": False},
        },
    )
    assert search_resp.status_code == 200
    body = search_resp.json()
    assert body["meta"]["store_status"] == "preparing"
    status = wait_for_job(client, body["meta"]["job_id"])
    assert status["state"] == "success"

    search_resp_2 = client.post(
        "/api/v1/search",
        json={
            "scene": "Text2Video",
            "store_type": "Folder",
            "topk": 5,
            "need_vectorize": False,
            "input": {"text": "band club", "image_object_keys": []},
            "params": {"model_alias": "prod", "auto_prepare": True, "batch_mode": False},
        },
    )
    assert search_resp_2.status_code == 200
    data = search_resp_2.json()
    assert data["meta"]["store_status"] == "ready"
    assert "band_club_001.mp4" in data["results"][0]["object_key"]


def test_image2image_search(client, temp_data_dir):
    folder = temp_data_dir / "gallery"
    folder.mkdir(parents=True)
    for name in ["airplane_001.jpg", "airplane_002.jpg", "car_001.jpg"]:
        (folder / name).write_text("demo", encoding="utf-8")

    vec_resp = client.post(
        "/api/v1/vectorize",
        json={
            "scene": "Image2Image",
            "store_type": "Folder",
            "store_name": "gallery_store",
            "keys": [str(folder)],
            "params": {"model_alias": "prod", "batch_size": 10, "force_rebuild": False},
        },
    )
    assert vec_resp.status_code == 200
    status = wait_for_job(client, vec_resp.json()["job_id"])
    assert status["state"] == "success"

    search_resp = client.post(
        "/api/v1/search",
        json={
            "scene": "Image2Image",
            "store_type": "Folder",
            "topk": 2,
            "need_vectorize": False,
            "input": {"text": None, "image_object_keys": [str(folder / 'airplane_001.jpg')]},
            "params": {"model_alias": "prod", "auto_prepare": True, "batch_mode": False},
        },
    )
    assert search_resp.status_code == 200
    data = search_resp.json()
    assert len(data["results"]) >= 1
    assert "airplane_001.jpg" in data["results"][0]["object_key"] or "airplane_002.jpg" in data["results"][0]["object_key"]


def test_delete_store_removes_index_files(client, temp_data_dir):
    folder = temp_data_dir / "delete_gallery"
    folder.mkdir(parents=True)
    for name in ["x_001.jpg", "x_002.jpg"]:
        (folder / name).write_text("demo", encoding="utf-8")

    vec_resp = client.post(
        "/api/v1/vectorize",
        json={
            "scene": "Image2Image",
            "store_type": "Folder",
            "store_name": "delete_gallery_store",
            "keys": [str(folder)],
            "params": {"model_alias": "prod", "batch_size": 10, "force_rebuild": False},
        },
    )
    assert vec_resp.status_code == 200
    status = wait_for_job(client, vec_resp.json()["job_id"])
    store_id = status["result"]["store_id"]

    settings = get_settings()
    index_npy = Path(settings.faiss_dir) / f"{store_id}.npy"
    index_json = Path(settings.faiss_dir) / f"{store_id}.json"
    managed_store_dir = Path(settings.managed_assets_dir) / "Image2Image" / store_id
    assert index_npy.exists()
    assert index_json.exists()
    assert managed_store_dir.exists()

    delete_resp = client.delete(f"/api/v1/stores/{store_id}")
    assert delete_resp.status_code == 200
    assert not index_npy.exists()
    assert not index_json.exists()
    assert not managed_store_dir.exists()


def test_force_rebuild_keeps_file_and_vector_counts_in_sync(client, temp_data_dir):
    folder = temp_data_dir / "sync_gallery"
    folder.mkdir(parents=True)
    for name in ["a_001.jpg", "a_002.jpg", "a_003.jpg"]:
        (folder / name).write_text(name, encoding="utf-8")

    first = client.post(
        "/api/v1/vectorize",
        json={
            "scene": "Image2Image",
            "store_type": "Folder",
            "store_name": "sync_store",
            "keys": [str(folder)],
            "params": {"model_alias": "prod", "batch_size": 8, "force_rebuild": True},
        },
    )
    first.raise_for_status()
    first_status = wait_for_job(client, first.json()["job_id"])
    assert first_status["state"] == "success"
    store_id = first_status["result"]["store_id"]

    (folder / "a_003.jpg").unlink()

    second = client.post(
        "/api/v1/vectorize",
        json={
            "scene": "Image2Image",
            "store_type": "Folder",
            "store_name": "sync_store",
            "keys": [str(folder)],
            "params": {"model_alias": "prod", "batch_size": 8, "force_rebuild": True},
        },
    )
    second.raise_for_status()
    second_status = wait_for_job(client, second.json()["job_id"])
    assert second_status["state"] == "success"

    detail = client.get(f"/api/v1/stores/{store_id}").json()
    assert detail["file_count"] == 2
    assert detail["vector_count"] == 2
