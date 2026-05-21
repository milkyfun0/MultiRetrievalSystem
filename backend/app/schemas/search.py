from typing import Union, Optional

from pydantic import BaseModel, Field

from app.core.enums import SceneEnum, StoreTypeEnum


class SearchInput(BaseModel):
    text: Union[str, list[str], None] = None
    image_object_keys: list[str] = Field(default_factory=list)


class SearchParams(BaseModel):
    model_alias: str = "prod"
    auto_prepare: bool = True
    batch_mode: bool = False
    uncertainty_weight: Optional[float] = None


class SearchRequest(BaseModel):
    scene: SceneEnum
    store_type: StoreTypeEnum
    topk: int = 10
    need_vectorize: bool = False
    input: SearchInput
    params: SearchParams = Field(default_factory=SearchParams)


class SearchResultItem(BaseModel):
    rank: int
    score: float
    media_type: str
    object_key: str
    preview_url: str
    source_label: str
    parent_video_name: Optional[str] = None
    segment_start_sec: Optional[float] = None
    segment_end_sec: Optional[float] = None
    frame_timestamp_sec: Optional[float] = None
    derive_type: Optional[str] = None


class SearchMeta(BaseModel):
    store_id: Optional[str] = None
    store_status: str
    model_alias: Optional[str] = None
    latency_ms: Optional[int] = None
    job_id: Optional[str] = None
    message: Optional[str] = None


class SearchResponse(BaseModel):
    scene: str
    store_type: str
    results: list[SearchResultItem]
    meta: SearchMeta


class QueryUploadResponse(BaseModel):
    object_key: str
    preview_url: str
    media_type: str = "image"
    filename: str
