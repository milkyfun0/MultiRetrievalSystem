from dataclasses import dataclass

from app.core.config import Settings
from app.models.sqlite import Database
from app.repositories.job_repo import JobRepo
from app.repositories.object_repo import ObjectRepo
from app.repositories.store_repo import StoreRepo
from app.repositories.vector_repo import VectorRepo
from app.services.algorithm_service import DeterministicAlgorithmService, HttpAlgorithmService
from app.services.faiss_service import FaissLikeService
from app.services.longvideo_service import LongVideoService
from app.services.object_service import ObjectService
from app.services.prepare_service import PrepareService
from app.services.search_service import SearchService
from app.services.store_service import StoreService
from app.workers.local_jobs import LocalJobRunner


@dataclass
class AppContainer:
    settings: Settings
    db: Database
    store_repo: StoreRepo
    object_repo: ObjectRepo
    vector_repo: VectorRepo
    job_repo: JobRepo
    faiss_service: FaissLikeService
    object_service: ObjectService
    longvideo_service: LongVideoService
    algorithm_service: object
    store_service: StoreService
    prepare_service: PrepareService
    search_service: SearchService
    job_runner: LocalJobRunner

    def shutdown(self) -> None:
        self.job_runner.shutdown()


def build_container(settings: Settings) -> AppContainer:
    db = Database(settings.sqlite_path)
    db.init_schema()
    store_repo = StoreRepo(db)
    object_repo = ObjectRepo(db)
    vector_repo = VectorRepo(db)
    job_repo = JobRepo(db)
    faiss_service = FaissLikeService(settings.faiss_dir)
    object_service = ObjectService(settings.public_base_url, settings.query_upload_dir, settings.managed_assets_dir)
    if settings.algorithm_mode == "http":
        algorithm_service = HttpAlgorithmService(settings.algorithm_gateway_url)
    else:
        algorithm_service = DeterministicAlgorithmService()
    job_runner = LocalJobRunner(max_workers=settings.local_job_workers)
    longvideo_service = LongVideoService(settings, job_runner)
    store_service = StoreService(store_repo)
    prepare_service = PrepareService(
        settings=settings,
        store_repo=store_repo,
        object_repo=object_repo,
        vector_repo=vector_repo,
        job_repo=job_repo,
        faiss_service=faiss_service,
        algorithm_service=algorithm_service,
        object_service=object_service,
        longvideo_service=longvideo_service,
        job_runner=job_runner,
    )
    search_service = SearchService(
        settings=settings,
        store_repo=store_repo,
        object_repo=object_repo,
        vector_repo=vector_repo,
        job_repo=job_repo,
        faiss_service=faiss_service,
        algorithm_service=algorithm_service,
        object_service=object_service,
        prepare_service=prepare_service,
        job_runner=job_runner,
    )
    return AppContainer(
        settings=settings,
        db=db,
        store_repo=store_repo,
        object_repo=object_repo,
        vector_repo=vector_repo,
        job_repo=job_repo,
        faiss_service=faiss_service,
        object_service=object_service,
        longvideo_service=longvideo_service,
        algorithm_service=algorithm_service,
        store_service=store_service,
        prepare_service=prepare_service,
        search_service=search_service,
        job_runner=job_runner,
    )
