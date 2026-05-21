from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any

import httpx
import numpy as np

from app.core.enums import to_algorithm_scene
from app.utils.normalize import normalize_to_str_list

logger = logging.getLogger(__name__)


class HttpAlgorithmService:
    """通过 HTTP 调用算法网关（gateway/encode）的服务。

    - 支持复用 httpx.Client 连接池，避免每次请求新建 TCP/TLS。
    - 支持基础的指数退避重试，覆盖网络抖动/瞬时不可用场景。
    - t2v 编码会自动放宽超时。
    """

    def __init__(
        self,
        gateway_url: str,
        *,
        timeout: int = 300,
        max_connections: int = 20,
        max_keepalive_connections: int = 10,
        max_retries: int = 2,
        retry_backoff: float = 1.0,
    ):
        self.gateway_url = gateway_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff = float(retry_backoff)

        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
        )
        # 复用同一个 client，trust_env=False 避免企业代理把局域网请求劫持
        self._client = httpx.Client(
            timeout=self.timeout,
            limits=limits,
            trust_env=False,
        )

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:  # noqa: BLE001
            pass

    def _post_with_retry(self, url: str, json_body: dict[str, Any], timeout_override: float | None = None) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                if timeout_override is not None:
                    return self._client.post(url, json=json_body, timeout=timeout_override)
                return self._client.post(url, json=json_body)
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.PoolTimeout) as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    break
                sleep_for = self.retry_backoff * (2 ** attempt)
                logger.warning(
                    "Algorithm call retry: url=%s attempt=%s/%s err=%s sleep=%.2fs",
                    url, attempt + 1, self.max_retries, exc, sleep_for,
                )
                time.sleep(sleep_for)
        assert last_exc is not None
        raise RuntimeError(f"Algorithm call failed after retries: url={url}, err={last_exc}")

    def encode(self, scene: str, query: Any = None, key: Any = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        algorithm_scene = to_algorithm_scene(scene)
        payload = {
            "scene": algorithm_scene,
            "query": query,
            "key": key,
            "params": params or {},
        }

        # t2v 编码明显比图片编码更重，这里单独放宽 timeout（至少 1200s）
        timeout_seconds = max(1200, self.timeout * 4) if algorithm_scene == "t2v" else self.timeout

        response = self._post_with_retry(
            f"{self.gateway_url}/encode",
            json_body=payload,
            timeout_override=timeout_seconds,
        )
        if response.status_code >= 400:
            body = response.text
            raise RuntimeError(
                f"Algorithm encode failed: status={response.status_code}, "
                f"scene={algorithm_scene}, body={body[:1000]}"
            )
        data = response.json()
        return {
            "scene": data.get("scene", algorithm_scene),
            "query_embed": data.get("query_embed", []) or [],
            "key_embed": data.get("key_embed", []) or [],
        }


class DeterministicAlgorithmService:
    vocabulary = [
        "cat", "dog", "bird", "airplane", "car", "band", "club", "lecture", "indoor",
        "medicine", "cell", "video", "image", "sunset", "dance", "mountain", "ocean"
    ]

    def _embed_one(self, value: str) -> list[float]:
        text = Path(value).stem.lower()
        vec = np.zeros(len(self.vocabulary) + 4, dtype=float)
        for idx, token in enumerate(self.vocabulary):
            if token in text:
                vec[idx] = 1.0
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        for i in range(4):
            vec[len(self.vocabulary) + i] = digest[i] / 255.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(float).tolist()

    def _embed_many(self, items: list[str]) -> list[list[float]]:
        return [self._embed_one(item) for item in items]

    def encode(self, scene: str, query: Any = None, key: Any = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query_items = normalize_to_str_list(query)
        key_items = normalize_to_str_list(key)
        return {
            "scene": to_algorithm_scene(scene),
            "query_embed": self._embed_many(query_items) if query_items else [],
            "key_embed": self._embed_many(key_items) if key_items else [],
        }