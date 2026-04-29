import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union

from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import open_dict

import t2i_encode

from common.api_utils import (
    ModelGuard,
    isolated_argv,
    normalize_request,
    normalize_to_str_list,
    pushd,
    tensor_to_list,
)


app = FastAPI(title="t2i worker")
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


def _compose_task_cfg(config_dir: Path, config_name: str = "train"):
    GlobalHydra.instance().clear()

    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name=config_name, return_hydra_config=True)

    HydraConfig.instance().set_config(cfg)

    with open_dict(cfg):
        if "hydra" in cfg:
            del cfg["hydra"]

    return cfg


def get_model_adapter(ckpt_path: str):
    t2i_encode.CKPT_PATH = (ckpt_path or "").strip()

    module_dir = Path(t2i_encode.__file__).resolve().parent
    config_dir = module_dir / "configs"
    if not config_dir.exists():
        raise FileNotFoundError(f"t2i Hydra config dir not found: {config_dir}")

    with pushd(module_dir):
        with isolated_argv("serve_t2i"):
            cfg = _compose_task_cfg(config_dir, "train")
            result = t2i_encode.build_model_and_cfg(cfg)

    if result is None:
        raise RuntimeError("t2i build_model_and_cfg returned None")
    return result


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
        "worker": "t2i",
    }


@app.post("/encode")
def encode(req: EncodeRequest):
    if not STATE["ready"]:
        raise HTTPException(status_code=503, detail="worker not ready")

    try:
        payload = normalize_request(req.dict())
        scene = payload["scene"] or "t2i"

        text_input = normalize_to_str_list(payload["query"])
        image_input = normalize_to_str_list(payload["key"])

        with guard.locked():
            text_feats, img_feats = t2i_encode.encode(
                STATE["cfg"],
                text_input,
                image_input,
                STATE["model"],
                STATE["tokenizer"],
            )

        return {
            "scene": scene,
            "query": text_input,
            "query_embed": tensor_to_list(text_feats),
            "key_embed": tensor_to_list(img_feats),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))