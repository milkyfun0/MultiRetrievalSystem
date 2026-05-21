from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import status

from app.core.config import Settings
from app.core.enums import JobStateEnum, StoreStatusEnum, StoreTypeEnum
from app.core.errors import ApiError
from app.repositories.job_repo import JobRepo
from app.repositories.object_repo import ObjectRepo
from app.repositories.store_repo import StoreRepo
from app.repositories.vector_repo import VectorRepo
from app.services.faiss_service import FaissLikeService
from app.services.longvideo_service import LongVideoService, TaskTerminatedError
from app.services.object_service import ObjectService
from app.utils.batch import batched
from app.utils.time import now_iso
from app.workers.local_jobs import LocalJobRunner

logger = logging.getLogger(__name__)


class PrepareService:
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
        longvideo_service: LongVideoService,
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
        self.longvideo_service = longvideo_service
        self.job_runner = job_runner

    def resolve_store(
        self,
        scene: str,
        store_type: str,
        keys: list[str],
        store_name: str,
        store_description: str | None,
        merge_on_name_conflict: bool | None,
        model_alias: str,
        preprocess_mode: str | None,
        interval_sec: int | None,
    ) -> dict[str, Any]:
        existing_by_name = self.store_repo.find_by_name(scene, store_type, store_name)
        candidate_resource_path = None
        if keys:
            first_key = keys[0]
            first_path = Path(first_key)
            if first_path.exists():
                candidate_resource_path = str(first_path.resolve())
            else:
                linked_store = self.store_repo.get(first_key)
                if linked_store:
                    candidate_resource_path = linked_store["resource_path"]
                else:
                    candidate_resource_path = first_key
        if existing_by_name:
            same_resource = candidate_resource_path and existing_by_name.get("resource_path") == candidate_resource_path
            same_preprocess = existing_by_name.get("preprocess_mode") == preprocess_mode and existing_by_name.get("interval_sec") == interval_sec
            if same_resource and same_preprocess:
                if store_description and store_description != existing_by_name.get("store_description"):
                    self.store_repo.update(existing_by_name["store_id"], store_description=store_description)
                return self.store_repo.get(existing_by_name["store_id"])
            if merge_on_name_conflict is None:
                raise ApiError(
                    "STORE_NAME_CONFLICT",
                    "已存在同名检索库，请确认是否合库",
                    {
                        "store_id": existing_by_name["store_id"],
                        "store_name": existing_by_name["store_name"],
                        "store_description": existing_by_name.get("store_description"),
                        "requires_merge_confirmation": True,
                    },
                    retryable=False,
                    status_code=status.HTTP_409_CONFLICT,
                )
            if merge_on_name_conflict is False:
                raise ApiError(
                    "STORE_RENAME_REQUIRED",
                    "用户拒绝合库，请重新命名后重试",
                    {"conflict_store_id": existing_by_name["store_id"], "store_name": existing_by_name["store_name"]},
                    retryable=False,
                    status_code=status.HTTP_409_CONFLICT,
                )
            if store_description and store_description != existing_by_name.get("store_description"):
                self.store_repo.update(existing_by_name["store_id"], store_description=store_description)
            return self.store_repo.get(existing_by_name["store_id"])

        first_key = keys[0] if keys else store_name
        if Path(first_key).exists():
            resource_path = str(Path(first_key).resolve())
        elif self.store_repo.get(first_key):
            resource_path = self.store_repo.get(first_key)["resource_path"]
        else:
            resource_path = first_key
        return self.store_repo.create(
            store_name=store_name,
            store_description=store_description,
            scene=scene,
            store_type=store_type,
            resource_path=resource_path,
            model_alias=model_alias,
            status=StoreStatusEnum.NOT_READY.value,
            preprocess_mode=preprocess_mode,
            interval_sec=interval_sec,
        )

    def start_prepare_job(
        self,
        scene: str,
        store_type: str,
        keys: list[str],
        store_name: str,
        store_description: str | None,
        merge_on_name_conflict: bool | None,
        model_alias: str,
        batch_size: int,
        force_rebuild: bool,
        preprocess_mode: str | None,
        interval_sec: int | None,
    ) -> dict[str, Any]:
        if store_type == StoreTypeEnum.LONGVIDEO.value:
            preprocess_mode, interval_sec = self.longvideo_service.resolve_and_validate(scene, preprocess_mode, interval_sec)
        store = self.resolve_store(scene, store_type, keys, store_name, store_description, merge_on_name_conflict, model_alias, preprocess_mode, interval_sec)
        self.store_repo.update_status(store["store_id"], StoreStatusEnum.PREPARING.value)
        if preprocess_mode is not None or interval_sec is not None:
            self.store_repo.update(store["store_id"], preprocess_mode=preprocess_mode, interval_sec=interval_sec)
        return self.job_repo.create(
            job_type="vectorize",
            scene=scene,
            store_id=store["store_id"],
            state=JobStateEnum.PENDING.value,
            message="资源准备任务已启动",
            payload={
                "keys": keys,
                "batch_size": batch_size,
                "force_rebuild": force_rebuild,
                "preprocess_mode": preprocess_mode,
                "interval_sec": interval_sec,
            },
            phase="validating",
            can_terminate=True,
        )

    def _update_job_progress(
        self,
        job_id: str,
        *,
        progress: int | None = None,
        message: str | None = None,
        phase: str | None = None,
        result: dict[str, Any] | None = None,
        can_terminate: bool | None = None,
    ) -> None:
        fields: dict[str, Any] = {}
        if progress is not None:
            fields["progress"] = max(0, min(100, int(progress)))
        if message is not None:
            fields["message"] = message
        if phase is not None:
            fields["phase"] = phase
        if result is not None:
            fields["result"] = result
        if can_terminate is not None:
            fields["can_terminate"] = can_terminate
        if fields:
            self.job_repo.update(job_id, **fields)

    def execute_prepare_job(self, job_id: str, batch_size: int, force_rebuild: bool, cancel_event=None) -> None:
        job = self.job_repo.get(job_id)
        if not job:
            return
        store = self.store_repo.get(job["store_id"]) if job.get("store_id") else None
        if not store:
            self.job_repo.update(job_id, state=JobStateEnum.FAILED.value, error="store not found", message="任务执行失败", can_terminate=False)
            return
        payload = job.get("payload") or {}
        raw_keys = payload.get("keys") or []
        preprocess_mode = payload.get("preprocess_mode") or store.get("preprocess_mode")
        interval_sec = payload.get("interval_sec") or store.get("interval_sec")
        self.job_repo.update(job_id, state=JobStateEnum.RUNNING.value, progress=1, message="开始扫描资源", phase="validating", can_terminate=True)
        try:
            self._raise_if_cancelled(cancel_event)
            scanned_sources = self._scan_objects(
                store["scene"],
                store["store_type"],
                raw_keys,
                job_id=job_id,
                preprocess_mode=preprocess_mode,
                interval_sec=interval_sec,
                cancel_event=cancel_event,
            )
            scanned_files = len(scanned_sources)
            self._update_job_progress(
                job_id,
                progress=8,
                message=f"资源扫描完成，共发现 {scanned_files} 个对象",
                phase="validating",
                result={"store_id": store["store_id"], "scanned_files": scanned_files},
                can_terminate=True,
            )

            if force_rebuild:
                self.vector_repo.delete_by_store(store["store_id"])
                self.object_repo.delete_by_store(store["store_id"])
                self.object_service.remove_store_assets(store["scene"], store["store_id"])
                self.faiss_service.reset_index(store["store_id"])

            managed_items: list[dict[str, Any]] = []
            current_object_keys: set[str] = set()
            phase_name = "saving" if store["store_type"] == StoreTypeEnum.LONGVIDEO.value else "vectorizing"
            self._update_job_progress(job_id, progress=12, phase=phase_name, message="开始托管资源与向量化", can_terminate=True)
            managed_total = max(1, len(scanned_sources))
            for source_idx, source in enumerate(scanned_sources, start=1):
                self._raise_if_cancelled(cancel_event)
                managed = self.object_service.ingest_managed_asset(source["source_path"], store["scene"], store["store_id"])
                item = {
                    **source,
                    **managed,
                }
                managed_items.append(item)
                current_object_keys.add(item["managed_object_key"])
                managed_progress = 12 + int(source_idx / managed_total * 18)
                self._update_job_progress(
                    job_id,
                    progress=managed_progress,
                    message=f"正在托管资源 {source_idx}/{managed_total}",
                    phase=phase_name,
                    result={
                        "store_id": store["store_id"],
                        "scanned_files": scanned_files,
                        "managed_files": source_idx,
                        "total_files": managed_total,
                    },
                    can_terminate=True,
                )

            removed_object_ids: list[str] = []
            if not force_rebuild:
                removed_object_ids = self.object_repo.deactivate_missing(store["store_id"], current_object_keys)
                self.vector_repo.delete_by_object_ids(store["store_id"], removed_object_ids)
                self._rebuild_index_from_vectors(store["store_id"])

            # 对 Text2Video + LongVideo 做额外过滤
            # 防止坏片段直接进入 t2v 编码阶段导致整批 timeout
            invalid_segments = 0
            if store["store_type"] == StoreTypeEnum.LONGVIDEO.value and store["scene"] == "Text2Video":
                valid_items: list[dict[str, Any]] = []
                for item in managed_items:
                    self._raise_if_cancelled(cancel_event)
                    try:
                        self.longvideo_service.ensure_video_readable(str(item["local_path"]), job_id=None)
                        valid_items.append(item)
                    except Exception:
                        invalid_segments += 1
                managed_items = valid_items
                self._update_job_progress(
                    job_id,
                    progress=30,
                    message="长视频片段校验完成，开始批量编码",
                    phase="vectorizing",
                    result={
                        "store_id": store["store_id"],
                        "scanned_files": scanned_files,
                        "managed_files": len(managed_items),
                        "invalid_segments": invalid_segments,
                    },
                    can_terminate=True,
                )
                if not managed_items:
                    raise RuntimeError("No valid long-video segments available for vectorization")

            total_batches = max(1, (len(managed_items) + batch_size - 1) // batch_size)
            self._update_job_progress(job_id, progress=30, message="开始批量编码", phase="vectorizing", can_terminate=True)
            new_vectors = 0
            skipped_vectors = 0
            failed_batches = 0
            processed_batches = 0
            generated_segments = sum(1 for item in managed_items if item.get("derive_type") == "segment")
            generated_frames = sum(1 for item in managed_items if item.get("derive_type") == "frame")

            for idx, batch in enumerate(batched(managed_items, batch_size), start=1):
                self._raise_if_cancelled(cancel_event)
                pending_paths: list[str] = []
                batch_objects: list[dict[str, Any]] = []
                try:
                    for item in batch:
                        self._raise_if_cancelled(cancel_event)
                        object_key = item["managed_object_key"]
                        obj = self.object_repo.upsert(
                            store_id=store["store_id"],
                            object_key=object_key,
                            media_type=item["media_type"],
                            preview_url=self.object_service.build_preview_url(object_key),
                            source_label=store["store_type"],
                            source_path_original=item.get("source_path_original") or item["source_path"],
                            managed_relpath=item["managed_relpath"],
                            managed_object_key=item["managed_object_key"],
                            content_hash=item["content_hash"],
                            file_size=int(item["file_size"]),
                            filename=item["filename"],
                            storage_backend=item["storage_backend"],
                            parent_video_name=item.get("parent_video_name"),
                            segment_start_sec=item.get("segment_start_sec"),
                            segment_end_sec=item.get("segment_end_sec"),
                            frame_timestamp_sec=item.get("frame_timestamp_sec"),
                            derive_type=item.get("derive_type"),
                        )
                        existing_vec = self.vector_repo.get_existing_for_object(
                            store_id=store["store_id"],
                            object_id=obj["object_id"],
                            model_version=self.settings.default_model_version,
                        )
                        if existing_vec and not force_rebuild:
                            skipped_vectors += 1
                            continue
                        pending_paths.append(str(item["local_path"]))
                        batch_objects.append(obj)
                    if pending_paths:
                        self.job_repo.update(job_id, phase="vectorizing")
                        encoded = self.algorithm_service.encode(
                            store["scene"],
                            query=None,
                            key=pending_paths,
                            params={"model_alias": store["model_alias"]},
                        )
                        key_embeddings = encoded.get("key_embed", []) or []
                        if len(key_embeddings) != len(batch_objects):
                            raise RuntimeError("algorithm embedding count mismatch")
                        for obj, embedding in zip(batch_objects, key_embeddings):
                            self.vector_repo.create(
                                store_id=store["store_id"],
                                object_id=obj["object_id"],
                                faiss_id=-1,
                                scene=store["scene"],
                                model_alias=store["model_alias"],
                                model_version=self.settings.default_model_version,
                                embedding=embedding,
                            )
                            new_vectors += 1
                    processed_batches += 1
                except TaskTerminatedError:
                    raise
                except Exception:
                    failed_batches += 1
                    raise
                progress = 30 + int(idx / total_batches * 65)
                self._update_job_progress(
                    job_id,
                    progress=progress,
                    message=f"正在处理第 {idx}/{total_batches} 个批次",
                    phase="vectorizing",
                    result={
                        "store_id": store["store_id"],
                        "scanned_files": scanned_files,
                        "generated_segments": generated_segments,
                        "generated_frames": generated_frames,
                        "invalid_segments": invalid_segments,
                        "new_vectors": new_vectors,
                        "skipped_vectors": skipped_vectors,
                        "failed_batches": failed_batches,
                        "processed_batches": processed_batches,
                        "total_batches": total_batches,
                    },
                    can_terminate=True,
                )

            self._raise_if_cancelled(cancel_event)
            self._update_job_progress(job_id, progress=97, message="正在重建索引并收尾", phase="saving", can_terminate=False)
            final_index_id = self._rebuild_index_from_vectors(store["store_id"])
            self.store_repo.update_status(store["store_id"], StoreStatusEnum.READY.value, current_index_id=final_index_id)
            active_file_count = self.object_repo.count_by_store(store["store_id"], active_only=True)
            total_object_count = self.object_repo.count_by_store(store["store_id"], active_only=False)
            total_vector_count = self.vector_repo.count_by_store(store["store_id"])
            self.job_repo.update(
                job_id,
                state=JobStateEnum.SUCCESS.value,
                progress=100,
                message="资源准备完成",
                phase="saving",
                can_terminate=False,
                result={
                    "store_id": store["store_id"],
                    "store_name": store["store_name"],
                    "store_description": store.get("store_description"),
                    "scanned_files": scanned_files,
                    "new_files": new_vectors,
                    "new_vectors": new_vectors,
                    "skipped_files": skipped_vectors,
                    "skipped_vectors": skipped_vectors,
                    "removed_files": len(removed_object_ids),
                    "file_count": active_file_count,
                    "object_count": total_object_count,
                    "vector_count": total_vector_count,
                    "failed_batches": failed_batches,
                    "processed_batches": processed_batches,
                    "total_batches": total_batches,
                    "generated_segments": generated_segments,
                    "generated_frames": generated_frames,
                    "invalid_segments": invalid_segments,
                    "final_index_id": final_index_id,
                },
            )
        except TaskTerminatedError as exc:
            self.store_repo.update_status(store["store_id"], StoreStatusEnum.FAILED.value)
            self.job_repo.update(
                job_id,
                state=JobStateEnum.TERMINATED.value,
                message="任务已被用户终止",
                error=None,
                can_terminate=False,
                terminated_at=now_iso(),
                terminate_reason=(job.get("terminate_reason") or str(exc)),
                result={
                    "store_id": store["store_id"],
                    "store_name": store["store_name"],
                    "store_description": store.get("store_description"),
                },
            )
        except Exception as exc:  # noqa: BLE001
            self.store_repo.update_status(store["store_id"], StoreStatusEnum.FAILED.value)
            self.job_repo.update(
                job_id,
                state=JobStateEnum.FAILED.value,
                message="任务执行失败",
                error=str(exc),
                can_terminate=False,
                result={
                    "store_id": store["store_id"],
                    "store_name": store["store_name"],
                    "store_description": store.get("store_description"),
                },
            )
        finally:
            self.longvideo_service.cleanup_job_temp(job_id)

    def terminate_job(self, job_id: str, reason: str | None = None) -> dict[str, Any]:
        job = self.job_repo.get(job_id)
        if not job:
            raise ApiError("JOB_NOT_FOUND", "任务不存在", {"job_id": job_id}, retryable=False, status_code=404)
        if job["state"] not in {JobStateEnum.RUNNING.value, JobStateEnum.PENDING.value}:
            raise ApiError(
                "TASK_NOT_TERMINABLE",
                "当前任务状态不允许终止",
                {"job_id": job_id, "state": job["state"]},
                retryable=False,
                status_code=status.HTTP_409_CONFLICT,
            )
        terminated_at = now_iso()
        self.job_repo.update(
            job_id,
            state=JobStateEnum.TERMINATED.value,
            message="任务已终止",
            terminated_at=terminated_at,
            terminate_reason=reason or "用户手动终止",
            can_terminate=False,
        )
        self.job_runner.request_terminate(job_id)
        return self.job_repo.get(job_id)

    def _rebuild_index_from_vectors(self, store_id: str) -> str:
        active_vectors = self.vector_repo.list_active_with_embeddings(store_id)
        index_id = self.faiss_service.reset_index(store_id)
        embeddings = [row["embedding"] for row in active_vectors if row.get("embedding")]
        if embeddings:
            faiss_ids, index_id = self.faiss_service.add_vectors(store_id, embeddings)
            for row, faiss_id in zip(active_vectors, faiss_ids):
                self.vector_repo.update_faiss_id(row["vector_id"], faiss_id)
        return index_id

    def _scan_objects(
        self,
        scene: str,
        store_type: str,
        keys: list[str],
        *,
        job_id: str,
        preprocess_mode: str | None,
        interval_sec: int | None,
        cancel_event,
    ) -> list[dict[str, Any]]:
        if store_type == StoreTypeEnum.LONGVIDEO.value:
            if len(keys) != 1:
                raise ApiError(
                    "LONGVIDEO_SINGLE_FILE_REQUIRED",
                    "LongVideo 模式下仅支持单个长视频文件输入",
                    {"keys": keys},
                    retryable=False,
                )
            source = Path(keys[0])
            if not source.exists():
                linked_store = self.store_repo.get(keys[0])
                if linked_store:
                    source = Path(linked_store["resource_path"])
            if not source.exists():
                raise FileNotFoundError(f"Resource path not found: {keys[0]}")
            self.job_repo.update(job_id, phase="preprocessing", message="正在进行长视频预处理")
            return self.longvideo_service.preprocess(
                scene=scene,
                source_video=str(source.resolve()),
                job_id=job_id,
                preprocess_mode=str(preprocess_mode),
                interval_sec=int(interval_sec),
                cancel_event=cancel_event,
            )

        items: list[dict[str, Any]] = []
        demo_mode = bool(getattr(self.settings, "demo_mode", False))
        for raw in keys:
            self._raise_if_cancelled(cancel_event)
            path = Path(raw)
            if not path.exists():
                linked_store = self.store_repo.get(raw)
                if linked_store:
                    path = Path(linked_store["resource_path"])
            if not path.exists():
                # 演示模式：路径不存在时跳过并告警，避免一个坏路径打断整个建库
                if demo_mode:
                    logger.warning("[demo_mode] resource path not found, skipped: %s", raw)
                    continue
                raise FileNotFoundError(f"Resource path not found: {raw}")
            if store_type == StoreTypeEnum.FOLDER.value and path.is_dir():
                items.extend(self._scan_folder(scene, path))
            elif store_type == StoreTypeEnum.DATABASE.value:
                if path.is_dir():
                    items.extend(self._scan_folder(scene, path))
                elif path.suffix.lower() == ".json":
                    loaded = json.loads(path.read_text(encoding="utf-8"))
                    items.extend({"source_path": str(Path(item).resolve()), "media_type": self.object_service.media_type_from_path(item, scene)} for item in loaded)
                else:
                    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
                    items.extend({"source_path": str(Path(item).resolve()), "media_type": self.object_service.media_type_from_path(item, scene)} for item in lines)
            elif path.is_file():
                items.append({"source_path": str(path.resolve()), "media_type": self.object_service.media_type_from_path(str(path), scene)})
            else:
                raise ApiError("STORE_NOT_SUPPORTED", "Unsupported store type", {"store_type": store_type})
        return items

    def _scan_folder(self, scene: str, folder: Path) -> list[dict[str, str]]:
        image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        video_exts = {".mp4", ".avi", ".mov", ".mkv"}
        exts = video_exts if scene == "Text2Video" else image_exts
        items: list[dict[str, str]] = []
        for file in sorted(folder.rglob("*")):
            if file.is_file() and file.suffix.lower() in exts:
                items.append({"source_path": str(file.resolve()), "media_type": self.object_service.media_type_from_path(str(file), scene)})
        return items

    @staticmethod
    def _raise_if_cancelled(cancel_event) -> None:
        if cancel_event and cancel_event.is_set():
            raise TaskTerminatedError("任务已被终止")
