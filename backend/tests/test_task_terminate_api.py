import time


def test_terminate_running_job(client):
    container = client.app.state.container

    job = container.job_repo.create(
        job_type="vectorize",
        scene="Text2Image",
        store_id=None,
        state="running",
        message="测试任务运行中",
        payload={"keys": []},
        phase="vectorizing",
        can_terminate=True,
    )

    def sleeper(job_id: str, cancel_event=None):
        while True:
            if cancel_event and cancel_event.is_set():
                return None
            time.sleep(0.01)

    container.job_runner.submit(job["job_id"], sleeper, job["job_id"])

    resp = client.post(f"/api/v1/tasks/{job['job_id']}/terminate", json={"reason": "测试终止"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["job_id"] == job["job_id"]
    assert data["state"] == "terminated"
    assert data["message"] == "任务已终止"

    status_resp = client.get(f"/api/v1/tasks/{job['job_id']}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["state"] == "terminated"
    assert status_data["terminate_reason"] == "测试终止"
