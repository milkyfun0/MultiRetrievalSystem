from pydantic import BaseModel

from app.core.enums import PreprocessModeEnum, SceneEnum, StoreTypeEnum


class StoreCreateRequest(BaseModel):
    store_name: str
    store_description: str | None = None
    scene: SceneEnum
    store_type: StoreTypeEnum
    resource_path: str
    model_alias: str = "prod"
    preprocess_mode: PreprocessModeEnum | None = None
    interval_sec: int | None = None


class StoreUpdateRequest(BaseModel):
    store_name: str | None = None
    store_description: str | None = None
    resource_path: str | None = None
    preprocess_mode: PreprocessModeEnum | None = None
    interval_sec: int | None = None
    rescan: bool = False


class StoreResponse(BaseModel):
    store_id: str
    store_name: str
    store_description: str | None = None
    scene: str
    store_type: str
    resource_path: str
    status: str
    current_index_id: str | None = None
    model_alias: str
    preprocess_mode: str | None = None
    interval_sec: int | None = None
    created_at: str
    updated_at: str
    file_count: int | None = None
    object_count: int | None = None
    active_object_count: int | None = None
    vector_count: int | None = None


class StoreStatusResponse(BaseModel):
    store_id: str
    store_name: str
    store_description: str | None = None
    status: str
    current_index_id: str | None = None
    model_alias: str
    preprocess_mode: str | None = None
    interval_sec: int | None = None
    file_count: int | None = None
    object_count: int | None = None
    active_object_count: int | None = None
    vector_count: int | None = None


class StoreListResponse(BaseModel):
    items: list[StoreResponse]


class StoreActionResponse(BaseModel):
    store_id: str
    status: str | None = None
    message: str
