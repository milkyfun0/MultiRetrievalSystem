# 局域网部署整改 — 代码重构差异说明

> 依据：[`README/lan_deployment_plan.md`](README/lan_deployment_plan.md) PRD
> 基线：当前 `main` 分支 HEAD（已修改但未提交）
> 涉及文件：7 个（算法端 2 个 + 后端 5 个）

## 0. 总览

| # | 文件 | 改动类型 | 关键目的 |
| - | --- | --- | --- |
| 1 | [`algorithm/launcher/run_all.py`](algorithm/launcher/run_all.py) | 改造 | checkpoint 路径 / 监听地址 / 启动间隔全部环境变量化 |
| 2 | [`algorithm/gateway/app.py`](algorithm/gateway/app.py) | 改造 | worker 地址与超时支持环境变量，便于 worker 分布式部署 |
| 3 | [`backend/app/core/config.py`](backend/app/core/config.py) | 扩展 | 新增连接池/超时/重试/`DEMO_MODE` 配置项 |
| 4 | [`backend/app/services/algorithm_service.py`](backend/app/services/algorithm_service.py) | 重构 | HTTP 客户端复用连接池 + 指数退避重试 |
| 5 | [`backend/app/services/prepare_service.py`](backend/app/services/prepare_service.py) | 增强 | 演示模式下路径不存在仅告警跳过，不再中断建库 |
| 6 | [`backend/app/api/v1/health.py`](backend/app/api/v1/health.py) | 升级 | `/health` 直接探测算法网关，返回 degraded 状态 |
| 7 | [`backend/app/dependencies.py`](backend/app/dependencies.py) | 适配 | 容器装配传入新配置 + 关闭算法 client 资源 |

新增 / 变更的环境变量速查：

| 环境变量 | 作用 | 默认值 |
| --- | --- | --- |
| `I2I_CKPT_PATH` / `T2I_CKPT_PATH` / `T2V_CKPT_PATH` | 算法 checkpoint 路径 | `""`（不加载权重） |
| `MMR_GATEWAY_HOST` / `MMR_GATEWAY_PORT` | 网关监听 | `0.0.0.0` / `18080` |
| `MMR_I2I_HOST` / `MMR_I2I_PORT`（t2i/t2v 同名） | worker 监听 | `0.0.0.0` / `18081-18083` |
| `MMR_LAUNCH_INTERVAL_SEC` | 子进程启动间隔 | `1.5` |
| `MMR_WORKER_I2I_URL` / `MMR_WORKER_T2I_URL` / `MMR_WORKER_T2V_URL` | 网关到 worker 的目标地址 | `http://127.0.0.1:1808x` |
| `MMR_GATEWAY_READ_TIMEOUT` / `MMR_GATEWAY_CONNECT_TIMEOUT` | 网关 → worker httpx 超时 | `300` / `5` |
| `MMR_ALGORITHM_MODE` | 算法模式 `http` / `deterministic` | `http` |
| `MMR_ALGORITHM_GATEWAY_URL` | 后端 → 算法网关地址 | `http://127.0.0.1:18080` |
| `MMR_ALGORITHM_TIMEOUT` | 后端 → 算法网关全局超时（秒） | `300` |
| `MMR_ALGORITHM_CONNECTION_POOL_SIZE` | 后端连接池 keepalive | `10` |
| `MMR_ALGORITHM_CONNECTION_POOL_MAXSIZE` | 后端连接池 max | `20` |
| `MMR_ALGORITHM_MAX_RETRIES` | 后端调用最大重试次数 | `2` |
| `MMR_ALGORITHM_RETRY_BACKOFF` | 重试退避基数（秒） | `1.0` |
| `MMR_DEMO_MODE` | 演示模式 | `false` |

---

## 1. `algorithm/launcher/run_all.py`

将 checkpoint 路径、监听 host/port、启动间隔全部从硬编码常量改造为环境变量优先、默认值兜底，符合 PRD 2.2.1 / 2.2.2 节。

```diff
@@ -7,24 +7,29 @@ from pathlib import Path

 ROOT_DIR = Path(__file__).resolve().parent.parent

-# ========= checkpoint 常量配置 =========
+# ========= checkpoint 配置（支持环境变量覆盖） =========
 # 为空字符串表示不加载权重，只初始化模型结构
-I2I_CKPT_PATH = ""
-T2I_CKPT_PATH = ""
-T2V_CKPT_PATH = ""
+# 局域网部署时通过 export I2I_CKPT_PATH=/path/to/ckpt 注入
+I2I_CKPT_PATH = os.getenv("I2I_CKPT_PATH", "")
+T2I_CKPT_PATH = os.getenv("T2I_CKPT_PATH", "")
+T2V_CKPT_PATH = os.getenv("T2V_CKPT_PATH", "")

-# ========= 端口配置 =========
-GATEWAY_HOST = "0.0.0.0"
-GATEWAY_PORT = 18080
+# ========= 监听地址/端口配置（支持环境变量覆盖） =========
+# 默认 0.0.0.0 以支持局域网访问，可通过环境变量收紧为 127.0.0.1
+GATEWAY_HOST = os.getenv("MMR_GATEWAY_HOST", "0.0.0.0")
+GATEWAY_PORT = int(os.getenv("MMR_GATEWAY_PORT", "18080"))

-I2I_HOST = "0.0.0.0"
-I2I_PORT = 18081
+I2I_HOST = os.getenv("MMR_I2I_HOST", "0.0.0.0")
+I2I_PORT = int(os.getenv("MMR_I2I_PORT", "18081"))

-T2I_HOST = "0.0.0.0"
-T2I_PORT = 18082
+T2I_HOST = os.getenv("MMR_T2I_HOST", "0.0.0.0")
+T2I_PORT = int(os.getenv("MMR_T2I_PORT", "18082"))

-T2V_HOST = "0.0.0.0"
-T2V_PORT = 18083
+T2V_HOST = os.getenv("MMR_T2V_HOST", "0.0.0.0")
+T2V_PORT = int(os.getenv("MMR_T2V_PORT", "18083"))
+
+# 启动间隔（大模型加载较慢，可调整）
+LAUNCH_INTERVAL_SEC = float(os.getenv("MMR_LAUNCH_INTERVAL_SEC", "1.5"))
@@ -80,6 +85,11 @@ def main():
     print(f"  I2I_CKPT_PATH={_fmt_ckpt(I2I_CKPT_PATH)}", flush=True)
     print(f"  T2I_CKPT_PATH={_fmt_ckpt(T2I_CKPT_PATH)}", flush=True)
     print(f"  T2V_CKPT_PATH={_fmt_ckpt(T2V_CKPT_PATH)}", flush=True)
+    print("[launch] bind config:", flush=True)
+    print(f"  GATEWAY {GATEWAY_HOST}:{GATEWAY_PORT}", flush=True)
+    print(f"  I2I     {I2I_HOST}:{I2I_PORT}", flush=True)
+    print(f"  T2I     {T2I_HOST}:{T2I_PORT}", flush=True)
+    print(f"  T2V     {T2V_HOST}:{T2V_PORT}", flush=True)
@@ -92,7 +102,7 @@ def main():
-        time.sleep(1.5)
+        time.sleep(LAUNCH_INTERVAL_SEC)
@@ -103,7 +113,7 @@ def main():
-        time.sleep(1.5)
+        time.sleep(LAUNCH_INTERVAL_SEC)
@@ -114,7 +124,7 @@ def main():
-        time.sleep(1.5)
+        time.sleep(LAUNCH_INTERVAL_SEC)
```

---

## 2. `algorithm/gateway/app.py`

支持把 i2i / t2i / t2v 三个 worker 拆到不同节点；网关 → worker 的 httpx 超时也环境变量化。

```diff
@@ -1,3 +1,5 @@
+import os
+
 import httpx
 from fastapi import FastAPI, HTTPException
 from pydantic import BaseModel
@@ -8,13 +10,23 @@ from common.api_utils import normalize_request

 app = FastAPI(title="multimodal gateway")

+# Worker 地址支持通过环境变量覆盖，便于将 worker 拆到不同算力节点
+# 例如：export MMR_WORKER_I2I_URL=http://10.0.0.21:18081
 WORKERS = {
-    "i2i": "http://127.0.0.1:18081",
-    "t2i": "http://127.0.0.1:18082",
-    "t2v": "http://127.0.0.1:18083",
+    "i2i": os.getenv("MMR_WORKER_I2I_URL", "http://127.0.0.1:18081"),
+    "t2i": os.getenv("MMR_WORKER_T2I_URL", "http://127.0.0.1:18082"),
+    "t2v": os.getenv("MMR_WORKER_T2V_URL", "http://127.0.0.1:18083"),
 }

-DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=300.0, write=300.0, pool=5.0)
+# t2v 编码相对耗时，read 超时单独放宽；其他统一沿用
+_READ_TIMEOUT = float(os.getenv("MMR_GATEWAY_READ_TIMEOUT", "300"))
+_CONNECT_TIMEOUT = float(os.getenv("MMR_GATEWAY_CONNECT_TIMEOUT", "5"))
+DEFAULT_TIMEOUT = httpx.Timeout(
+    connect=_CONNECT_TIMEOUT,
+    read=_READ_TIMEOUT,
+    write=_READ_TIMEOUT,
+    pool=_CONNECT_TIMEOUT,
+)
```

---

## 3. `backend/app/core/config.py`

新增算法服务超时 / 连接池 / 重试以及演示模式开关，落实 PRD 2.3.1、2.5.1 节。

```diff
@@ -15,8 +15,25 @@ class Settings(BaseSettings):
     query_upload_dir: str = Field(default_factory=lambda: str(Path("data/query_uploads").resolve()))
     managed_assets_dir: str = Field(default_factory=lambda: str(Path("data/assets").resolve()))
     preprocess_temp_dir: str = Field(default_factory=lambda: str(Path("data/preprocess_tmp").resolve()))
+
+    # ====== 算法服务（局域网/本地）相关配置 ======
     algorithm_mode: str = "http"
     algorithm_gateway_url: str = "http://127.0.0.1:18080"
+    # 算法 HTTP 调用全局超时（秒），t2v 编码会在此基础上倍增
+    algorithm_timeout: int = 300
+    # httpx 连接池配置
+    algorithm_connection_pool_size: int = 10
+    algorithm_connection_pool_maxsize: int = 20
+    # 算法请求重试次数（仅针对网络异常）
+    algorithm_max_retries: int = 2
+    # 算法请求重试退避基数（秒），实际退避为 base * (2 ** attempt)
+    algorithm_retry_backoff: float = 1.0
+
+    # ====== 演示模式 ======
+    # 演示模式下，对于本地不存在的 key，将仅做存在性校验过滤而不报错
+    # 适用于后端与算法/数据共享同一文件系统（NFS / 共享卷）的局域网部署
+    demo_mode: bool = False
+
     local_job_workers: int = 4
```

---

## 4. `backend/app/services/algorithm_service.py`

重构 `HttpAlgorithmService`：

- 复用 `httpx.Client`（连接池 + keepalive），消除每次请求重新握手开销
- 增加指数退避重试，覆盖 `ConnectError / ReadTimeout / RemoteProtocolError / PoolTimeout`
- `t2v` 超时改为 `max(1200, timeout * 4)`，可被全局 timeout 推大
- 新增 `close()` 用于优雅释放

```diff
@@ -1,6 +1,8 @@
 from __future__ import annotations

 import hashlib
+import logging
+import time
 from pathlib import Path
 from typing import Any
@@ -10,10 +12,68 @@ import numpy as np

 from app.core.enums import to_algorithm_scene
 from app.utils.normalize import normalize_to_str_list

+logger = logging.getLogger(__name__)
+

 class HttpAlgorithmService:
-    def __init__(self, gateway_url: str):
+    """通过 HTTP 调用算法网关（gateway/encode）的服务。
+
+    - 支持复用 httpx.Client 连接池，避免每次请求新建 TCP/TLS。
+    - 支持基础的指数退避��试，覆盖网络抖动/瞬时不可用场景。
+    - t2v 编码会自动放宽超时。
+    """
+
+    def __init__(
+        self,
+        gateway_url: str,
+        *,
+        timeout: int = 300,
+        max_connections: int = 20,
+        max_keepalive_connections: int = 10,
+        max_retries: int = 2,
+        retry_backoff: float = 1.0,
+    ):
         self.gateway_url = gateway_url.rstrip("/")
+        self.timeout = timeout
+        self.max_retries = max(0, int(max_retries))
+        self.retry_backoff = float(retry_backoff)
+
+        limits = httpx.Limits(
+            max_connections=max_connections,
+            max_keepalive_connections=max_keepalive_connections,
+        )
+        # 复用同一个 client，trust_env=False 避免企业代理把局域网请求劫持
+        self._client = httpx.Client(
+            timeout=self.timeout,
+            limits=limits,
+            trust_env=False,
+        )
+
+    def close(self) -> None:
+        try:
+            self._client.close()
+        except Exception:  # noqa: BLE001
+            pass
+
+    def _post_with_retry(self, url, json_body, timeout_override=None):
+        last_exc = None
+        for attempt in range(self.max_retries + 1):
+            try:
+                if timeout_override is not None:
+                    return self._client.post(url, json=json_body, timeout=timeout_override)
+                return self._client.post(url, json=json_body)
+            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.PoolTimeout) as exc:
+                last_exc = exc
+                if attempt >= self.max_retries:
+                    break
+                time.sleep(self.retry_backoff * (2 ** attempt))
+        raise RuntimeError(f"Algorithm call failed after retries: url={url}, err={last_exc}")

     def encode(self, scene, query=None, key=None, params=None):
-        # t2v 编码明显比图片编码更重，这里单独放宽 timeout
-        timeout_seconds = 1200 if algorithm_scene == "t2v" else 300
-
-        with httpx.Client(timeout=timeout_seconds, trust_env=False) as client:
-            response = client.post(f"{self.gateway_url}/encode", json=payload)
+        # t2v 编码明显比图片编码更重，这里单独放宽 timeout（至少 1200s）
+        timeout_seconds = max(1200, self.timeout * 4) if algorithm_scene == "t2v" else self.timeout
+        response = self._post_with_retry(f"{self.gateway_url}/encode", json_body=payload, timeout_override=timeout_seconds)
```

---

## 5. `backend/app/services/prepare_service.py`

新增 `demo_mode` 分支：路径不存在时 warning 跳过而不抛 `FileNotFoundError`，满足 PRD 2.4.1。

```diff
@@ -1,6 +1,7 @@
 from __future__ import annotations

 import json
+import logging
 from pathlib import Path
@@ -20,6 +21,8 @@ from app.utils.batch import batched
 from app.utils.time import now_iso
 from app.workers.local_jobs import LocalJobRunner

+logger = logging.getLogger(__name__)
+

 class PrepareService:
@@ -522,6 +525,7 @@ class PrepareService:
             )

         items: list[dict[str, Any]] = []
+        demo_mode = bool(getattr(self.settings, "demo_mode", False))
         for raw in keys:
             self._raise_if_cancelled(cancel_event)
             path = Path(raw)
@@ -530,6 +534,10 @@ class PrepareService:
                 if linked_store:
                     path = Path(linked_store["resource_path"])
             if not path.exists():
+                # 演示模式：路径不存在时跳过并告警，避免一个坏路径打断整个建库
+                if demo_mode:
+                    logger.warning("[demo_mode] resource path not found, skipped: %s", raw)
+                    continue
                 raise FileNotFoundError(f"Resource path not found: {raw}")
```

---

## 6. `backend/app/api/v1/health.py`

`/health` 不再只返回静态 `algorithm: true`，而是真实探测算法网关并暴露 `demo_mode`，与 PRD 2.7.1 联通性测试呼应。

```diff
@@ -1,19 +1,51 @@
+from __future__ import annotations
+
+import logging
+
+import httpx
 from fastapi import APIRouter, Depends

 from app.api.deps import get_container
 from app.dependencies import AppContainer

 router = APIRouter(tags=["health"])
+logger = logging.getLogger(__name__)
+
+
+def _probe_algorithm_gateway(gateway_url: str, timeout: float = 5.0) -> dict:
+    """对算法网关做轻量级 /health 探测，便于局域网部署排障。"""
+    url = gateway_url.rstrip("/") + "/health"
+    try:
+        with httpx.Client(timeout=timeout, trust_env=False) as client:
+            resp = client.get(url)
+            ok = resp.status_code < 400
+            detail = None
+            if ok:
+                try:
+                    detail = resp.json()
+                except Exception:
+                    detail = {"raw": resp.text[:200]}
+            return {"ok": ok, "url": url, "status_code": resp.status_code, "detail": detail}
+    except Exception as exc:
+        logger.warning("Algorithm gateway health probe failed: %s", exc)
+        return {"ok": False, "url": url, "error": str(exc)}


 @router.get("/health")
 def health(container: AppContainer = Depends(get_container)):
+    settings = container.settings
+    algorithm_health = {"mode": settings.algorithm_mode, "ok": True}
+    if settings.algorithm_mode == "http":
+        algorithm_health.update(_probe_algorithm_gateway(settings.algorithm_gateway_url))
+
+    overall = algorithm_health.get("ok", True)
     return {
-        "status": "healthy",
+        "status": "healthy" if overall else "degraded",
         "services": {
             "api": True,
             "faiss": True,
             "minio": True,
-            "algorithm": True,
+            "algorithm": algorithm_health,
         },
-    }
+        "demo_mode": bool(getattr(settings, "demo_mode", False)),
+    }
```

---

## 7. `backend/app/dependencies.py`

容器装配把新增配置透传给 `HttpAlgorithmService`，并在 `shutdown` 中关闭共享 client。

```diff
@@ -35,6 +35,12 @@ class AppContainer:

     def shutdown(self) -> None:
         self.job_runner.shutdown()
+        close_fn = getattr(self.algorithm_service, "close", None)
+        if callable(close_fn):
+            try:
+                close_fn()
+            except Exception:
+                pass


 def build_container(settings: Settings) -> AppContainer:
@@ -47,7 +53,14 @@ def build_container(settings: Settings) -> AppContainer:
     faiss_service = FaissLikeService(settings.faiss_dir)
     object_service = ObjectService(settings.public_base_url, settings.query_upload_dir, settings.managed_assets_dir)
     if settings.algorithm_mode == "http":
-        algorithm_service = HttpAlgorithmService(settings.algorithm_gateway_url)
+        algorithm_service = HttpAlgorithmService(
+            settings.algorithm_gateway_url,
+            timeout=settings.algorithm_timeout,
+            max_connections=settings.algorithm_connection_pool_maxsize,
+            max_keepalive_connections=settings.algorithm_connection_pool_size,
+            max_retries=settings.algorithm_max_retries,
+            retry_backoff=settings.algorithm_retry_backoff,
+        )
     else:
         algorithm_service = DeterministicAlgorithmService()
```

---

## 8. 部署速查（与 PRD 2.6 节对齐）

### 算法服务器

```bash
cd algorithm/
pip install -r requirements.txt

export I2I_CKPT_PATH="/data/ckpt/i2i"
export T2I_CKPT_PATH="/data/ckpt/t2i"
export T2V_CKPT_PATH="/data/ckpt/t2v"
# 如需把 worker 拆到其它节点，再追加：
# export MMR_WORKER_I2I_URL=http://10.0.0.21:18081

python launcher/run_all.py
```

### 后端服务器

```bash
cd backend/
pip install -r requirements.txt

export MMR_ALGORITHM_MODE=http
export MMR_ALGORITHM_GATEWAY_URL=http://10.0.0.20:18080
export MMR_ALGORITHM_TIMEOUT=600
export MMR_ALGORITHM_MAX_RETRIES=3
export MMR_DEMO_MODE=true

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 连通性自检

```bash
# 1. 算法网关
curl http://10.0.0.20:18080/health

# 2. 后端到算法（同时返回 algorithm 子探测）
curl http://10.0.0.30:8000/api/v1/health
```

## 9. 风险与回滚

- 所有变量都带默认值，不传任何环境变量时行为与重构前保持一致；
- `HttpAlgorithmService.close()` 在 `Container.shutdown()` 中防御性调用，已对老的 `DeterministicAlgorithmService` 兼容；
- `DEMO_MODE` 仅在显式开启时改变错误处理路径，生产模式行为不变；
- 如需回滚，只需还原本文档列出的 7 个文件即可，不涉及 DB / Faiss / 接口契约变更。
