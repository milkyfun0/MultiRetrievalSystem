import os
import sys
from pathlib import Path
from contextlib import contextmanager
from threading import Lock
from typing import Any, Dict, List, Optional


class ModelGuard:
    def __init__(self):
        self._lock = Lock()

    @contextmanager
    def locked(self):
        self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()


@contextmanager
def isolated_argv(argv0: Optional[str] = None):
    original = sys.argv[:]
    sys.argv = [argv0 or (original[0] if original else "app")]
    try:
        yield
    finally:
        sys.argv = original


@contextmanager
def pushd(path: Path):
    old = Path.cwd()
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(str(old))


def normalize_to_str_list(value: Any) -> List[str]:
    """
    统一把单值/列表/None 归一化成 List[str]
    过滤 None、空串、纯空白串
    """
    if value is None:
        return []

    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        raise ValueError("value must be str, list, tuple or null")

    result: List[str] = []
    for x in items:
        if x is None:
            continue
        s = str(x).strip()
        if s == "":
            continue
        result.append(s)
    return result


def normalize_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    这里只做基础字段提取，不把 query/key 限死成某一种类型
    query/key 的真正归一化在 worker 层做
    """
    scene = payload.get("scene") or payload.get("scence") or ""
    query = payload.get("query", None)
    key = payload.get("key", None)
    params = payload.get("params", {}) or {}

    if not isinstance(params, dict):
        raise ValueError("`params` must be a dict")

    return {
        "scene": scene,
        "query": query,
        "key": key,
        "params": params,
    }


def tensor_to_list(x: Any):
    """
    Tensor -> list
    list -> 原样返回
    None -> []
    """
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if hasattr(x, "detach"):
        x = x.detach()
    if hasattr(x, "cpu"):
        x = x.cpu()
    if hasattr(x, "numpy"):
        return x.numpy().tolist()
    if isinstance(x, tuple):
        return list(x)
    return x