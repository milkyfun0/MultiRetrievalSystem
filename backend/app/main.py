from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.api.v1.media import router as media_router
from app.api.v1.search import router as search_router
from app.api.v1.stores import router as stores_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.vectorize import router as vectorize_router
from app.core.config import get_settings
from app.dependencies import build_container


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    container = build_container(settings)
    app.state.container = container
    yield
    container.shutdown()


app = FastAPI(
    title="Multi-modal Retrieval Backend",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(search_router, prefix="/api/v1")
app.include_router(vectorize_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(stores_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(media_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
