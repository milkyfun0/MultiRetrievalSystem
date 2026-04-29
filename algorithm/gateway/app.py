import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union

from common.api_utils import normalize_request


app = FastAPI(title="multimodal gateway")

WORKERS = {
    "i2i": "http://127.0.0.1:18081",
    "t2i": "http://127.0.0.1:18082",
    "t2v": "http://127.0.0.1:18083",
}

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=300.0, write=300.0, pool=5.0)


class EncodeRequest(BaseModel):
    scene: Optional[str] = None
    scence: Optional[str] = None
    query: Optional[Union[str, List[str]]] = None
    key: Optional[Union[str, List[str]]] = None
    params: Optional[Dict[str, Any]] = None


def get_worker_url(scene: str) -> str:
    s = (scene or "").strip().lower()
    if s not in WORKERS:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported scene: {scene}, expected one of {list(WORKERS.keys())}",
        )
    return WORKERS[s]


def build_client() -> httpx.Client:
    # 禁用环境代理，避免 Windows / 企业网络环境下本地 127.0.0.1 也走代理
    return httpx.Client(timeout=DEFAULT_TIMEOUT, trust_env=False)


@app.get("/health")
def health():
    results: Dict[str, Any] = {}

    with build_client() as client:
        for scene, base_url in WORKERS.items():
            try:
                resp = client.get(f"{base_url}/health")
                resp.raise_for_status()
                data = resp.json()
                loaded = bool(data.get("ok", False) or data.get("loaded", False))
                results[scene] = {
                    "loaded": loaded,
                    "detail": data,
                }
            except Exception as e:
                results[scene] = {
                    "loaded": False,
                    "error": str(e),
                }

    return {
        "gateway": "ok",
        "workers": results,
    }


@app.post("/encode")
def encode(req: EncodeRequest):
    try:
        payload = normalize_request(req.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    scene = payload["scene"]
    worker_url = get_worker_url(scene)

    with build_client() as client:
        try:
            resp = client.post(f"{worker_url}/encode", json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json()
            except Exception:
                detail = e.response.text
            raise HTTPException(
                status_code=e.response.status_code,
                detail={
                    "worker": scene,
                    "worker_url": worker_url,
                    "error": detail,
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail={
                    "worker": scene,
                    "worker_url": worker_url,
                    "error": str(e),
                },
            )