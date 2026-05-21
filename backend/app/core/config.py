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

    # ====== 算法服务（局域网/本地）相关配置 ======
    algorithm_mode: str = "http"
    algorithm_gateway_url: str = "http://127.0.0.1:18080"
    # 算法 HTTP 调用全局超时（秒），t2v 编码会在此基础上倍增
    algorithm_timeout: int = 300
    # httpx 连接池配置
    algorithm_connection_pool_size: int = 10
    algorithm_connection_pool_maxsize: int = 20
    # 算法请求重试次数（仅针对网络异常）
    algorithm_max_retries: int = 2
    # 算法请求重试退避基数（秒），实际退避为 base * (2 ** attempt)
    algorithm_retry_backoff: float = 1.0

    # ====== 演示模式 ======
    # 演示模式下，对于本地不存在的 key，将仅做存在性校验过滤而不报错
    # 适用于后端与算法/数据共享同一文件系统（NFS / 共享卷）的局域网部署
    demo_mode: bool = False

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