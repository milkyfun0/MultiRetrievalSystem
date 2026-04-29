from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.deps import get_container
from app.dependencies import AppContainer

router = APIRouter(tags=["media"])


@router.get("/media/preview")
def preview_media(object_key: str = Query(...), container: AppContainer = Depends(get_container)):
    local_path = Path(container.object_service.resolve_local_path(object_key))
    if not local_path.exists() or not local_path.is_file():
        raise HTTPException(status_code=404, detail="object not found")
    return FileResponse(path=str(local_path), filename=local_path.name)
