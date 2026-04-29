from fastapi import status

from app.core.enums import StoreStatusEnum
from app.core.errors import ApiError
from app.repositories.store_repo import StoreRepo


class StoreService:
    def __init__(self, store_repo: StoreRepo):
        self.store_repo = store_repo

    def create_store(
        self,
        store_name: str,
        store_description: str | None,
        scene: str,
        store_type: str,
        resource_path: str,
        model_alias: str,
        preprocess_mode: str | None = None,
        interval_sec: int | None = None,
    ):
        existing = self.store_repo.find_by_name(scene, store_type, store_name)
        if existing:
            raise ApiError(
                "STORE_NAME_CONFLICT",
                "已存在同名检索库，请更换名称或走合库流程",
                {
                    "store_id": existing["store_id"],
                    "store_name": existing["store_name"],
                    "store_description": existing.get("store_description"),
                },
                retryable=False,
                status_code=status.HTTP_409_CONFLICT,
            )
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
