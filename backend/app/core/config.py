from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MMR_", extra="ignore")

    app_name: str = "mmr-backend"
    sqlite_path: str = Field(default_factory=lambda: str(Path("data/sqlite/app.db").resolve()))
    faiss_dir: str = Field(default_factory=lambda: str(Path("data/faiss").resolve()))
    public_base_url: str = "http://127.0.0.1:8000"
    query_upload_dir: str = Field(default_factory=lambda: str(Path("data/query_uploads").resolve()))
    managed_assets_dir: str = Field(default_factory=lambda: str(Path("data/assets").resolve()))
    preprocess_temp_dir: str = Field(default_factory=lambda: str(Path("data/preprocess_tmp").resolve()))
    algorithm_mode: str = "http"
    algorithm_gateway_url: str = "http://127.0.0.1:18080"
    local_job_workers: int = 4
    default_model_alias: str = "prod"
    default_model_version: str = "v0-local"
    default_topk: int = 10
    max_topk: int = 100
    auto_prepare_default: bool = True
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.faiss_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.query_upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.managed_assets_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.preprocess_temp_dir).mkdir(parents=True, exist_ok=True)
    return settings
