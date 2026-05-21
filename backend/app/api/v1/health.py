from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.dependencies import AppContainer

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


def _probe_algorithm_gateway(gateway_url: str, timeout: float = 5.0) -> dict:
    """对算法网关做轻量级 /health 探测，便于局域网部署排障。"""
    url = gateway_url.rstrip("/") + "/health"
    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            resp = client.get(url)
            ok = resp.status_code < 400
            detail = None
            if ok:
                try:
                    detail = resp.json()
                except Exception:  # noqa: BLE001
                    detail = {"raw": resp.text[:200]}
            return {"ok": ok, "url": url, "status_code": resp.status_code, "detail": detail}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Algorithm gateway health probe failed: %s", exc)
        return {"ok": False, "url": url, "error": str(exc)}


@router.get("/health")
def health(container: AppContainer = Depends(get_container)):
    settings = container.settings
    algorithm_health = {"mode": settings.algorithm_mode, "ok": True}
    if settings.algorithm_mode == "http":
        algorithm_health.update(_probe_algorithm_gateway(settings.algorithm_gateway_url))

    overall = algorithm_health.get("ok", True)
    return {
        "status": "healthy" if overall else "degraded",
        "services": {
            "api": True,
            "faiss": True,
            "minio": True,
            "algorithm": algorithm_health,
        },
        "demo_mode": bool(getattr(settings, "demo_mode", False)),
    }