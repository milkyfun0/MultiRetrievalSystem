from typing import Optional

from pydantic import BaseModel

from app.core.enums import PreprocessModeEnum, SceneEnum, StoreTypeEnum


class StoreCreateRequest(BaseModel):
    store_name: str
    store_description: Optional[str] = None
    scene: SceneEnum
    store_type: StoreTypeEnum
    resource_path: str
    model_alias: str = "prod"
    preprocess_mode: Optional[PreprocessModeEnum] = None
    interval_sec: Optional[int] = None


class StoreUpdateRequest(BaseModel):
    store_name: Optional[str] = None
    store_description: Optional[str] = None
    resource_path: Optional[str] = None
    preprocess_mode:  Optional[PreprocessModeEnum] = None
    interval_sec: Optional[int] = None
    rescan: bool = False


class StoreResponse(BaseModel):
    store_id: str
    store_name: str
    store_description: Optional[str] = None
    scene: str
    store_type: str
    resource_path: str
    status: str
    current_index_id: Optional[str] = None
    model_alias: str
    preprocess_mode: Optional[str] = None
    interval_sec: Optional[int] = None
    created_at: str
    updated_at: str
    file_count: Optional[int] = None
    object_count: Optional[int] = None
    active_object_count: Optional[int] = None
    vector_count: Optional[int] = None


class StoreStatusResponse(BaseModel):
    store_id: str
    store_name: str
    store_description: Optional[str] = None
    status: str
    current_index_id: Optional[str] = None
    model_alias: str
    preprocess_mode: Optional[str] = None
    interval_sec: Optional[int] = None
    file_count: Optional[int] = None
    object_count: Optional[int] = None
    active_object_count: Optional[int] = None
    vector_count: Optional[int] = None


class StoreListResponse(BaseModel):
    items: list[StoreResponse]


class StoreActionResponse(BaseModel):
    store_id: str
    status: Optional[str] = None
    message: str
