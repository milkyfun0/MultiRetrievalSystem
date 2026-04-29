from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_container
from app.core.enums import JobStateEnum, StoreStatusEnum
from app.dependencies import AppContainer
from app.schemas.tasks import JobStatusResponse, TaskTerminateRequest, TaskTerminateResponse


def _reconcile_job_if_stale(job: dict, container: AppContainer) -> dict:
    if job["state"] not in {JobStateEnum.PENDING.value, JobStateEnum.RUNNING.value}:
        return job
    store_id = job.get("store_id")
    if not store_id:
        return job
    store = container.store_repo.get(store_id)
    if not store:
        return job

    if store.get("status") == StoreStatusEnum.READY.value:
        result = job.get("result") or {}
        result.setdefault("store_id", store_id)
        result.setdefault("store_name", store.get("store_name"))
        result.setdefault("store_description", store.get("store_description"))
        result.setdefault("file_count", container.object_repo.count_by_store(store_id, active_only=True))
        result.setdefault("object_count", container.object_repo.count_by_store(store_id, active_only=False))
        result.setdefault("vector_count", container.vector_repo.count_by_store(store_id))
        result.setdefault("final_index_id", store.get("current_index_id"))
        reconciled = container.job_repo.update(
            job["job_id"],
            state=JobStateEnum.SUCCESS.value,
            progress=100,
            message=job.get("message") if job.get("message") in {"资源准备完成"} else "资源准备完成",
            phase="saving",
            can_terminate=False,
            result=result,
            error=None,
        )
        return reconciled or job

    if store.get("status") == StoreStatusEnum.FAILED.value:
        reconciled = container.job_repo.update(
            job["job_id"],
            state=JobStateEnum.FAILED.value,
            message=job.get("message") or "任务执行失败",
            can_terminate=False,
        )
        return reconciled or job

    return job

router = APIRouter(tags=["tasks"])


@router.get("/tasks/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, container: AppContainer = Depends(get_container)):
    job = container.job_repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    job = _reconcile_job_if_stale(job, container)
    return {
        "job_id": job["job_id"],
        "state": job["state"],
        "progress": job["progress"],
        "message": job.get("message"),
        "error": job.get("error"),
        "result": job.get("result"),
        "phase": job.get("phase"),
        "can_terminate": bool(job.get("can_terminate")),
        "terminated_at": job.get("terminated_at"),
        "terminate_reason": job.get("terminate_reason"),
    }


@router.post("/tasks/{job_id}/terminate", response_model=TaskTerminateResponse)
def terminate_job(job_id: str, payload: TaskTerminateRequest, container: AppContainer = Depends(get_container)):
    job = container.prepare_service.terminate_job(job_id, payload.reason)
    return {
        "job_id": job["job_id"],
        "state": job["state"],
        "message": job.get("message") or "任务已终止",
        "terminated_at": job.get("terminated_at"),
    }
