from typing import Optional

from pydantic import BaseModel, Field

from app.core.enums import PreprocessModeEnum, SceneEnum, StoreTypeEnum


class VectorizeParams(BaseModel):
    model_alias: str = "prod"
    batch_size: int = 64
    force_rebuild: bool = False
    preprocess_mode:  Optional[PreprocessModeEnum] = None
    interval_sec: Optional[int] = None


class VectorizeRequest(BaseModel):
    scene: SceneEnum
    store_type: StoreTypeEnum
    store_name: str
    store_description: Optional[str] = None
    merge_on_name_conflict: Optional[bool] = None
    keys: list[str] = Field(default_factory=list)
    params: VectorizeParams = Field(default_factory=VectorizeParams)


class VectorizeResponse(BaseModel):
    job_id: Optional[str] = None
    status: str
    store_id: Optional[str] = None
    message: str
    conflict_store_id: Optional[str] = None
    requires_merge_confirmation: bool = False
