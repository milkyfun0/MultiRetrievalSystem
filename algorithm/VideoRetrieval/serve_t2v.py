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
from transformers import CLIPTokenizerFast

import t2v_encode

from common.api_utils import (
    ModelGuard,
    isolated_argv,
    normalize_request,
    normalize_to_str_list,
    tensor_to_list,
)


app = FastAPI(title="t2v worker")
guard = ModelGuard()

STATE: Dict[str, Any] = {
    "cfg": None,
    "model": None,
    "tokenizer": None,
    "ready": False,
}


class EncodeRequest(BaseModel):
    scene: Optional[str] = None
    scence: Optional[str] = None
    query: Optional[Union[str, List[str]]] = None
    key: Optional[Union[str, List[str]]] = None
    params: Optional[Dict[str, Any]] = None


def get_model_adapter(ckpt_path: str):
    with isolated_argv("serve_t2v"):
        cfg = t2v_encode.shared_configs.get_pretraining_args()

    t2v_encode.set_random_seed(cfg.seed)

    ckpt_path = (ckpt_path or "").strip()
    cfg.e2e_weights_path = ckpt_path if ckpt_path else ""

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    cfg.n_gpu = 1 if torch.cuda.is_available() else 0
    cfg.world_size = cfg.n_gpu

    model = t2v_encode.setup_model(cfg, device=device)
    tokenizer = CLIPTokenizerFast.from_pretrained(cfg.clip_weights)
    model.eval()
    return cfg, model, tokenizer


@app.on_event("startup")
def startup():
    ckpt_path = os.getenv("MODEL_CKPT_PATH", "").strip()
    cfg, model, tokenizer = get_model_adapter(ckpt_path)
    STATE["cfg"] = cfg
    STATE["model"] = model
    STATE["tokenizer"] = tokenizer
    STATE["ready"] = True


@app.get("/health")
def health():
    return {
        "ok": bool(STATE["ready"]),
        "worker": "t2v",
    }


@app.post("/encode")
def encode(req: EncodeRequest):
    if not STATE["ready"]:
        raise HTTPException(status_code=503, detail="worker not ready")

    try:
        payload = normalize_request(req.dict())
        scene = payload["scene"] or "t2v"

        text_input = normalize_to_str_list(payload["query"])
        video_input = normalize_to_str_list(payload["key"])

        with guard.locked():
            text_feats, video_feats = t2v_encode.encode(
                STATE["cfg"],
                text_input,
                video_input,
                STATE["model"],
                STATE["tokenizer"],
            )

        return {
            "scene": scene,
            "query": text_input,
            "query_embed": tensor_to_list(text_feats),
            "key_embed": tensor_to_list(video_feats),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))