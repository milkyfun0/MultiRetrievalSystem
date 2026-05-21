from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.dependencies import AppContainer

router = APIRouter(tags=["health"])


@router.get("/health")
def health(container: AppContainer = Depends(get_container)):
    return {
        "status": "healthy",
        "services": {
            "api": True,
            "faiss": True,
            "minio": True,
            "algorithm": True,
        },
    }
