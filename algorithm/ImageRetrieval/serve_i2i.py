import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union

import torch
from models.base_distill.base_distall import Network
from utils import get_options, get_device
import i2i_encode

from common.api_utils import (
    ModelGuard,
    isolated_argv,
    normalize_request,
    normalize_to_str_list,
    tensor_to_list,
)


app = FastAPI(title="i2i worker")
guard = ModelGuard()

STATE: Dict[str, Any] = {
    "opt": None,
    "model": None,
    "ready": False,
}


class EncodeRequest(BaseModel):
    scene: Optional[str] = None
    scence: Optional[str] = None
    query: Optional[Union[str, List[str]]] = None
    key: Optional[Union[str, List[str]]] = None
    params: Optional[Dict[str, Any]] = None


def get_model_adapter(ckpt_path: str):
    with isolated_argv("serve_i2i"):
        opt = get_options("base_distill")

    model = Network(opt)

    ckpt_path = (ckpt_path or "").strip()
    if ckpt_path:
        state_dict = torch.load(ckpt_path, map_location="cpu")
        model.load_state_dict(state_dict, strict=True)

    model.eval()
    model.to(get_device())
    return opt, model


@app.on_event("startup")
def startup():
    ckpt_path = os.getenv("MODEL_CKPT_PATH", "").strip()
    opt, model = get_model_adapter(ckpt_path)
    STATE["opt"] = opt
    STATE["model"] = model
    STATE["ready"] = True


@app.get("/health")
def health():
    return {
        "ok": bool(STATE["ready"]),
        "worker": "i2i",
    }


@app.post("/encode")
def encode(req: EncodeRequest):
    if not STATE["ready"]:
        raise HTTPException(status_code=503, detail="worker not ready")

    try:
        payload = normalize_request(req.dict())
        scene = payload["scene"] or "i2i"

        query_paths = normalize_to_str_list(payload["query"])
        key_paths = normalize_to_str_list(payload["key"])

        with guard.locked():
            query_embed = i2i_encode.encode(STATE["opt"], STATE["model"], query_paths)
            key_embed = i2i_encode.encode(STATE["opt"], STATE["model"], key_paths)

        return {
            "scene": scene,
            "query_embed": tensor_to_list(query_embed),
            "key_embed": tensor_to_list(key_embed),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))