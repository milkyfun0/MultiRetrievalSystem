from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.dependencies import AppContainer
from app.schemas.search import SearchRequest, SearchResponse

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, container: AppContainer = Depends(get_container)):
    return container.search_service.search(payload)
