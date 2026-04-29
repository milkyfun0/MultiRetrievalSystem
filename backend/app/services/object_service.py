from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import UploadFile


class ObjectService:
    def __init__(self, public_base_url: str, query_upload_dir: str, managed_assets_dir: str):
        self.public_base_url = public_base_url.rstrip("/")
        self.query_upload_dir = Path(query_upload_dir)
        self.managed_assets_dir = Path(managed_assets_dir)
        self.query_upload_dir.mkdir(parents=True, exist_ok=True)
        self.managed_assets_dir.mkdir(parents=True, exist_ok=True)

    def build_preview_url(self, object_key: str) -> str:
        return f"{self.public_base_url}/api/v1/media/preview?object_key={quote(object_key, safe='')}"

    def media_type_from_path(self, path: str, scene: str) -> str:
        return "video" if scene == "Text2Video" else "image"

    def save_query_upload(self, file: UploadFile) -> dict[str, str]:
        suffix = Path(file.filename or "query.jpg").suffix or ".bin"
        relative_key = f"uploads/query/{uuid.uuid4().hex}{suffix}"
        absolute_path = self.query_upload_dir / relative_key.replace("uploads/query/", "")
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        with absolute_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        return {
            "object_key": relative_key,
            "preview_url": self.build_preview_url(relative_key),
            "filename": file.filename or absolute_path.name,
            "absolute_path": str(absolute_path.resolve()),
        }

    def compute_hash(self, source_path: str) -> tuple[str, int]:
        path = Path(source_path)
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest(), path.stat().st_size

    def build_managed_key(self, scene: str, store_id: str, filename: str, content_hash: str) -> str:
        safe_name = Path(filename).name or f"{content_hash}.bin"
        return f"managed/{scene}/{store_id}/{content_hash}/{safe_name}"

    def managed_relpath_from_key(self, managed_object_key: str) -> Path:
        assert managed_object_key.startswith("managed/")
        return Path(managed_object_key.replace("managed/", "", 1))

    def ingest_managed_asset(self, source_path: str, scene: str, store_id: str) -> dict[str, str | int]:
        source = Path(source_path).resolve()
        content_hash, file_size = self.compute_hash(str(source))
        filename = source.name
        managed_object_key = self.build_managed_key(scene, store_id, filename, content_hash)
        relpath = self.managed_relpath_from_key(managed_object_key)
        destination = self.managed_assets_dir / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)
        return {
            "source_path_original": str(source),
            "managed_relpath": str(relpath).replace("\\", "/"),
            "managed_object_key": managed_object_key,
            "content_hash": content_hash,
            "file_size": int(file_size),
            "filename": filename,
            "storage_backend": "local_managed",
            "local_path": str(destination.resolve()),
        }

    def remove_store_assets(self, scene: str, store_id: str) -> None:
        root = self.managed_assets_dir / scene / store_id
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)

    def resolve_local_path(self, object_key: str) -> str:
        path = Path(object_key)
        if path.is_absolute() and path.exists():
            return str(path.resolve())
        if object_key.startswith("uploads/query/"):
            relative = object_key.replace("uploads/query/", "")
            candidate = self.query_upload_dir / relative
            if candidate.exists():
                return str(candidate.resolve())
        if object_key.startswith("managed/"):
            relpath = self.managed_relpath_from_key(object_key)
            candidate = self.managed_assets_dir / relpath
            if candidate.exists():
                return str(candidate.resolve())
        if path.exists():
            return str(path.resolve())
        return object_key
