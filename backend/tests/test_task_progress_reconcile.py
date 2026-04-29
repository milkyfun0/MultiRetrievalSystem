from app.core.enums import StoreStatusEnum


def test_job_progress_reconciles_to_success_when_store_already_ready(client, monkeypatch):
    store_resp = client.post(
        "/api/v1/stores",
        json={
            "store_name": "reconcile_store",
            "scene": "Text2Image",
            "store_type": "Folder",
            "resource_path": ".",
            "model_alias": "prod",
        },
    )
    store_resp.raise_for_status()
    store_id = store_resp.json()["store_id"]

    container = client.app.state.container
    job = container.job_repo.create(
        job_type="vectorize",
        scene="Text2Image",
        store_id=store_id,
        state="running",
        message="正在处理第 1/8 个批次",
        payload={"keys": [], "batch_size": 32, "force_rebuild": False},
        phase="vectorizing",
        can_terminate=True,
    )

    container.store_repo.update_status(store_id, StoreStatusEnum.READY.value, current_index_id="idx_demo")

    resp = client.get(f"/api/v1/tasks/{job['job_id']}")
    resp.raise_for_status()
    data = resp.json()

    assert data["state"] == "success"
    assert data["progress"] == 100
    assert data["can_terminate"] is False
    assert data["result"]["store_id"] == store_id
    assert data["result"]["final_index_id"] == "idx_demo"
