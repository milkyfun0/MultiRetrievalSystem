from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_container
from app.dependencies import AppContainer
from app.schemas.search import QueryUploadResponse

router = APIRouter(tags=["uploads"])


@router.post("/uploads/query-image", response_model=QueryUploadResponse)
def upload_query_image(file: UploadFile = File(...), container: AppContainer = Depends(get_container)):
    saved = container.object_service.save_query_upload(file)
    return {
        "object_key": saved["object_key"],
        "preview_url": saved["preview_url"],
        "media_type": "image",
        "filename": saved["filename"],
    }
