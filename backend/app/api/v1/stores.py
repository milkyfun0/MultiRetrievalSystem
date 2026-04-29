from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_container
from app.dependencies import AppContainer
from app.schemas.stores import StoreActionResponse, StoreCreateRequest, StoreListResponse, StoreResponse, StoreStatusResponse, StoreUpdateRequest

router = APIRouter(tags=["stores"])


def _attach_store_counts(container: AppContainer, store: dict) -> dict:
    enriched = dict(store)
    store_id = store["store_id"]
    enriched["file_count"] = container.object_repo.count_by_store(store_id, active_only=True)
    enriched["object_count"] = container.object_repo.count_by_store(store_id, active_only=False)
    enriched["active_object_count"] = container.object_repo.count_by_store(store_id, active_only=True)
    enriched["vector_count"] = container.vector_repo.count_by_store(store_id)
    return enriched


@router.post("/stores", response_model=StoreActionResponse)
def create_store(payload: StoreCreateRequest, container: AppContainer = Depends(get_container)):
    store = container.store_service.create_store(
        store_name=payload.store_name,
        store_description=payload.store_description,
        scene=payload.scene.value,
        store_type=payload.store_type.value,
        resource_path=payload.resource_path,
        model_alias=payload.model_alias,
        preprocess_mode=payload.preprocess_mode.value if payload.preprocess_mode else None,
        interval_sec=payload.interval_sec,
    )
    return {"store_id": store["store_id"], "status": store["status"], "message": "检索库已创建"}


@router.get("/stores", response_model=StoreListResponse)
def list_stores(container: AppContainer = Depends(get_container)):
    stores = [_attach_store_counts(container, item) for item in container.store_repo.list()]
    return {"items": stores}


@router.get("/stores/{store_id}", response_model=StoreResponse)
def get_store(store_id: str, container: AppContainer = Depends(get_container)):
    store = container.store_repo.get(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="store not found")
    return _attach_store_counts(container, store)


@router.put("/stores/{store_id}", response_model=StoreActionResponse)
def update_store(store_id: str, payload: StoreUpdateRequest, container: AppContainer = Depends(get_container)):
    store = container.store_repo.get(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="store not found")
    updates = {}
    if payload.store_name is not None:
        updates["store_name"] = payload.store_name
    if payload.store_description is not None:
        updates["store_description"] = payload.store_description
    if payload.resource_path is not None:
        updates["resource_path"] = payload.resource_path
    if payload.preprocess_mode is not None:
        updates["preprocess_mode"] = payload.preprocess_mode.value
    if payload.interval_sec is not None:
        updates["interval_sec"] = payload.interval_sec
    if payload.rescan:
        updates["status"] = "not_ready"
    updated = container.store_repo.update(store_id, **updates)
    return {
        "store_id": store_id,
        "status": updated["status"] if updated else None,
        "message": "检索库已更新并开始重新扫描" if payload.rescan else "检索库已更新",
    }


@router.delete("/stores/{store_id}", response_model=StoreActionResponse)
def delete_store(store_id: str, container: AppContainer = Depends(get_container)):
    store = container.store_repo.get(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="store not found")
    container.vector_repo.delete_by_store(store_id)
    container.object_repo.delete_by_store(store_id)
    if hasattr(container.job_repo, "delete_by_store"):
        container.job_repo.delete_by_store(store_id)
    container.faiss_service.delete_index(store_id)
    container.object_service.remove_store_assets(store["scene"], store_id)
    container.store_repo.delete(store_id)
    return {"store_id": store_id, "status": "deleted", "message": "检索库、托管资源、对象元数据与索引文件已删除"}


@router.get("/stores/{store_id}/status", response_model=StoreStatusResponse)
def get_store_status(store_id: str, container: AppContainer = Depends(get_container)):
    store = container.store_repo.get(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="store not found")
    enriched = _attach_store_counts(container, store)
    return {
        "store_id": enriched["store_id"],
        "store_name": enriched["store_name"],
        "store_description": enriched.get("store_description"),
        "status": enriched["status"],
        "current_index_id": enriched["current_index_id"],
        "model_alias": enriched["model_alias"],
        "preprocess_mode": enriched.get("preprocess_mode"),
        "interval_sec": enriched.get("interval_sec"),
        "file_count": enriched["file_count"],
        "object_count": enriched["object_count"],
        "active_object_count": enriched["active_object_count"],
        "vector_count": enriched["vector_count"],
    }
