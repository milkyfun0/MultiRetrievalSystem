from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_container
from app.dependencies import AppContainer
from app.schemas.vectorize import VectorizeRequest, VectorizeResponse

router = APIRouter(tags=["vectorize"])


@router.post("/vectorize", response_model=VectorizeResponse)
def vectorize(payload: VectorizeRequest, container: AppContainer = Depends(get_container)):
    if not payload.keys:
        raise HTTPException(status_code=400, detail="keys must not be empty")
    job = container.prepare_service.start_prepare_job(
        scene=payload.scene.value,
        store_type=payload.store_type.value,
        keys=payload.keys,
        store_name=payload.store_name,
        store_description=payload.store_description,
        merge_on_name_conflict=payload.merge_on_name_conflict,
        model_alias=payload.params.model_alias,
        batch_size=payload.params.batch_size,
        force_rebuild=payload.params.force_rebuild,
        preprocess_mode=payload.params.preprocess_mode.value if payload.params.preprocess_mode else None,
        interval_sec=payload.params.interval_sec,
    )
    container.job_runner.submit(
        job["job_id"],
        container.prepare_service.execute_prepare_job,
        job["job_id"],
        payload.params.batch_size,
        payload.params.force_rebuild,
    )
    return {
        "job_id": job["job_id"],
        "status": "running",
        "store_id": job["store_id"],
        "message": "资源准备任务已启动",
    }
