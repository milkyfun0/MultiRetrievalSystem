from __future__ import annotations

import time
from typing import Any

import numpy as np

from app.core.config import Settings
from app.core.enums import JobStateEnum, StoreStatusEnum
from app.core.errors import ApiError
from app.repositories.job_repo import JobRepo
from app.repositories.object_repo import ObjectRepo
from app.repositories.store_repo import StoreRepo
from app.repositories.vector_repo import VectorRepo
from app.services.faiss_service import FaissLikeService
from app.services.object_service import ObjectService
from app.utils.normalize import normalize_to_str_list
from app.workers.local_jobs import LocalJobRunner


class SearchService:
    def __init__(
        self,
        settings: Settings,
        store_repo: StoreRepo,
        object_repo: ObjectRepo,
        vector_repo: VectorRepo,
        job_repo: JobRepo,
        faiss_service: FaissLikeService,
        algorithm_service: Any,
        object_service: ObjectService,
        prepare_service: Any,
        job_runner: LocalJobRunner,
    ):
        self.settings = settings
        self.store_repo = store_repo
        self.object_repo = object_repo
        self.vector_repo = vector_repo
        self.job_repo = job_repo
        self.faiss_service = faiss_service
        self.algorithm_service = algorithm_service
        self.object_service = object_service
        self.prepare_service = prepare_service
        self.job_runner = job_runner

    def search(self, request: Any) -> dict[str, Any]:
        started = time.perf_counter()
        store = self.store_repo.get_latest_by_scene_store_type(request.scene.value, request.store_type.value)
        if not store:
            raise ApiError("STORE_NOT_FOUND", "未找到匹配的检索库", {"scene": request.scene.value, "store_type": request.store_type.value}, retryable=False, status_code=404)

        if store["status"] != StoreStatusEnum.READY.value:
            auto_prepare = request.params.auto_prepare if request.params.auto_prepare is not None else self.settings.auto_prepare_default
            if auto_prepare:
                job = self.prepare_service.start_prepare_job(
                    scene=store["scene"],
                    store_type=store["store_type"],
                    keys=[store["resource_path"]],
                    store_name=store["store_name"],
                    store_description=store.get("store_description"),
                    merge_on_name_conflict=True,
                    model_alias=store["model_alias"],
                    batch_size=64,
                    force_rebuild=False,
                    preprocess_mode=store.get("preprocess_mode"),
                    interval_sec=store.get("interval_sec"),
                )
                self.job_runner.submit(job["job_id"], self.prepare_service.execute_prepare_job, job["job_id"], 64, False)
                return {
                    "scene": request.scene.value,
                    "store_type": request.store_type.value,
                    "results": [],
                    "meta": {
                        "store_id": store["store_id"],
                        "store_status": StoreStatusEnum.PREPARING.value,
                        "job_id": job["job_id"],
                        "message": "检索库尚未准备完成，已开始后台向量化",
                    },
                }
            return {
                "scene": request.scene.value,
                "store_type": request.store_type.value,
                "results": [],
                "meta": {
                    "store_id": store["store_id"],
                    "store_status": store["status"],
                    "model_alias": store["model_alias"],
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                },
            }

        query_values = self._extract_query_values(request)
        if not query_values:
            return {
                "scene": request.scene.value,
                "store_type": request.store_type.value,
                "results": [],
                "meta": {
                    "store_id": store["store_id"],
                    "store_status": store["status"],
                    "model_alias": store["model_alias"],
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                },
            }
        encoded = self.algorithm_service.encode(store["scene"], query=query_values, key=None, params={"model_alias": store["model_alias"]})
        query_embeddings = encoded.get("query_embed", []) or []
        if not query_embeddings:
            raise ApiError("QUERY_ENCODING_FAILED", "Query 编码失败", retryable=True, status_code=502)
        query_vector = np.asarray(query_embeddings, dtype=float).mean(axis=0).tolist()
        ranked = self.faiss_service.search(store["store_id"], query_vector, request.topk)
        faiss_ids = [item[0] for item in ranked]
        vectors = {row["faiss_id"]: row for row in self.vector_repo.list_by_faiss_ids(store["store_id"], faiss_ids)}
        results = []
        for rank, (faiss_id, score) in enumerate(ranked, start=1):
            vec = vectors.get(faiss_id)
            if not vec:
                continue
            obj = self.object_repo.get(vec["object_id"])
            if not obj:
                continue
            results.append(
                {
                    "rank": rank,
                    "score": round(score, 6),
                    "media_type": obj["media_type"],
                    "object_key": obj["object_key"],
                    "preview_url": self.object_service.build_preview_url(obj["object_key"]),
                    "source_label": obj["source_label"] or store["store_type"],
                    "parent_video_name": obj.get("parent_video_name"),
                    "segment_start_sec": obj.get("segment_start_sec"),
                    "segment_end_sec": obj.get("segment_end_sec"),
                    "frame_timestamp_sec": obj.get("frame_timestamp_sec"),
                    "derive_type": obj.get("derive_type"),
                }
            )
        return {
            "scene": request.scene.value,
            "store_type": request.store_type.value,
            "results": results,
            "meta": {
                "store_id": store["store_id"],
                "store_status": store["status"],
                "model_alias": store["model_alias"],
                "latency_ms": int((time.perf_counter() - started) * 1000),
            },
        }

    def _extract_query_values(self, request: Any) -> list[str]:
        if request.scene.value == "Image2Image":
            return [self.object_service.resolve_local_path(item) for item in normalize_to_str_list(request.input.image_object_keys)]
        return normalize_to_str_list(request.input.text)
