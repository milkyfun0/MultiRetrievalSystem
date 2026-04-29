from pydantic import BaseModel, Field

from app.core.enums import PreprocessModeEnum, SceneEnum, StoreTypeEnum


class VectorizeParams(BaseModel):
    model_alias: str = "prod"
    batch_size: int = 64
    force_rebuild: bool = False
    preprocess_mode: PreprocessModeEnum | None = None
    interval_sec: int | None = None


class VectorizeRequest(BaseModel):
    scene: SceneEnum
    store_type: StoreTypeEnum
    store_name: str
    store_description: str | None = None
    merge_on_name_conflict: bool | None = None
    keys: list[str] = Field(default_factory=list)
    params: VectorizeParams = Field(default_factory=VectorizeParams)


class VectorizeResponse(BaseModel):
    job_id: str | None = None
    status: str
    store_id: str | None = None
    message: str
    conflict_store_id: str | None = None
    requires_merge_confirmation: bool = False
