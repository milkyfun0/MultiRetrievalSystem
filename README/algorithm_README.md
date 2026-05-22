# 算法服务组件文档

本文档面向初次接触本系统的开发人员，完整说明算法服务的架构设计、启动方式、接口规范、常见问题及与其他组件的集成方式。

---

## 1. 组件概述

算法服务是多模态检索系统的向量化核心。它**不负责检索排序**，只负责一件事：把输入的图像路径、文本、视频路径编码成向量（embedding），供后端的 FAISS 索引层使用。

### 支持的任务类型

| 内部场景名 | 功能 | 对应业务场景 |
|---|---|---|
| `i2i` | 图像 → 向量 | 以图搜图（Image2Image） |
| `t2i` | 文本/图像 → 向量 | 文搜图（Text2Image） |
| `t2v` | 文本/视频 → 向量 | 文搜视频（Text2Video） |

### 服务架构

算法服务由 4 个进程组成，Gateway 作为统一入口向后端暴露，各 Worker 处理具体编码：

```
后端 FastAPI (8000)
       │
       ▼
  Gateway (:18080)          ← 统一入口，负责路由和健康聚合
  ├─ I2I Worker (:18081)    ← 图像编码（base_distill 模型）
  ├─ T2I Worker (:18082)    ← 文本+图像编码（CXR-CLIP 医学模型）
  └─ T2V Worker (:18083)    ← 文本+视频编码（CLIP-VIP 模型）
```

### 目录结构

```
algorithm/
├── gateway/
│   └── app.py              # 统一网关，路由 /encode 到各 worker
├── common/
│   └── api_utils.py        # 共享工具：归一化、设备检测、ModelGuard 等
├── ImageRetrieval/
│   ├── serve_i2i.py        # I2I HTTP 服务（端口 18081）
│   └── i2i_encode.py       # 底层图像编码逻辑
├── MedicalRetrieval/
│   ├── serve_t2i.py        # T2I HTTP 服务（端口 18082）
│   └── t2i_encode.py       # 底层文本+图像编码逻辑（Hydra 配置）
├── VideoRetrieval/
│   ├── serve_t2v.py        # T2V HTTP 服务（端口 18083）
│   └── t2v_encode.py       # 底层文本+视频编码逻辑（CLIP-VIP）
└── launcher/
    └── run_all.py          # 一键启动所有 4 个服务进程
```

---

## 2. 快速上手

### 2.1 前提条件

- Python ≥ 3.9
- PyTorch（推荐 CUDA 版本，CPU 亦可运行但速度较慢）
- 项目根目录已安装 `requirements.txt` 依赖

### 2.2 配置模型权重

打开 `launcher/run_all.py`，填写各模型的 checkpoint 路径：

```python
# 路径相对于各自 worker 的工作目录
# I2I 权重路径相对于 algorithm/ImageRetrieval/
I2I_CKPT_PATH = "analyze_valid/base_distill_patchmask/.../xxx.pt"

# T2I 权重路径相对于 algorithm/MedicalRetrieval/
T2I_CKPT_PATH = "Ksample4Ratio0.32025-01-29/21-09-16/checkpoints/model-best.tar"

# T2V 权重路径相对于 algorithm/VideoRetrieval/
T2V_CKPT_PATH = "ckpts/model_step_10547.pt"
```

> 留空字符串 `""` 表示不加载权重，仅初始化模型结构（向量没有业务意义，仅用于功能联调）。

### 2.3 启动服务

```bash
# 在 algorithm/ 目录下执行
cd algorithm
python launcher/run_all.py
```

启动成功后，终端会依次打印 4 个服务的启动日志，全部就绪后显示：

```
[launch] all services started. Press Ctrl+C to stop.
```

### 2.4 验证启动状态

```bash
# 检查 Gateway（聚合所有 worker 状态）
curl http://127.0.0.1:18080/health

# 单独检查各 worker
curl http://127.0.0.1:18081/health   # I2I
curl http://127.0.0.1:18082/health   # T2I
curl http://127.0.0.1:18083/health   # T2V
```

Gateway 健康检查返回示例：

```json
{
  "gateway": "ok",
  "workers": {
    "i2i": { "loaded": true, "detail": { "ok": true, "worker": "i2i" } },
    "t2i": { "loaded": true, "detail": { "ok": true, "worker": "t2i" } },
    "t2v": { "loaded": true, "detail": { "ok": true, "worker": "t2v" } }
  }
}
```

---

## 3. 配置说明

### 3.1 端口配置

在 `launcher/run_all.py` 中统一管理：

```python
GATEWAY_HOST = "0.0.0.0"
GATEWAY_PORT = 18080

I2I_HOST = "0.0.0.0";  I2I_PORT = 18081
T2I_HOST = "0.0.0.0";  T2I_PORT = 18082
T2V_HOST = "0.0.0.0";  T2V_PORT = 18083
```

### 3.2 模型权重传递机制

launcher 通过环境变量 `MODEL_CKPT_PATH` 把路径传递给子进程，各 worker 在 `startup()` 事件中读取：

```python
# 各 worker 的 startup 函数
@app.on_event("startup")
def startup():
    ckpt_path = os.getenv("MODEL_CKPT_PATH", "").strip()
    # 加载模型...
```

### 3.3 PYTHONPATH 配置

launcher 启动时会自动把项目根目录（`algorithm/` 的上一级）加入 `PYTHONPATH`，使各 worker 能正确 `import common.api_utils`。**不需要手动设置。**

---

## 4. 接口说明

### 4.1 统一编码接口

所有请求通过 Gateway 的 `/encode` 接口转发：

```
POST http://127.0.0.1:18080/encode
Content-Type: application/json
```

**请求字段：**

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| `scene` | string | 是 | `i2i`、`t2i`、`t2v`（支持旧拼写 `scence`） |
| `query` | string / list / null | 否 | 查询侧输入（文本或路径） |
| `key` | string / list / null | 否 | 库侧输入（文件路径列表） |
| `params` | dict | 否 | 预留扩展参数 |

**输入空值处理规则：**
- `null`、`""`、纯空白字符串、`[]` 均视为空
- 列表中混入的 `null` 和空串会被自动过滤
- 空输入不报错，对应的 `query_embed` / `key_embed` 返回 `[]`

**响应字段：**

| 场景 | 响应示例 |
|---|---|
| `i2i` | `{ "scene": "i2i", "query_embed": [[...]], "key_embed": [[...]] }` |
| `t2i` | `{ "scene": "t2i", "query": ["text..."], "query_embed": [[...]], "key_embed": [[...]] }` |
| `t2v` | `{ "scene": "t2v", "query": ["text..."], "query_embed": [[...]], "key_embed": [[...]] }` |

所有向量统一返回**二维列表**（即使只有一个输入，也返回 `[[...]]`）。

### 4.2 健康检查接口

```
GET http://127.0.0.1:18080/health       # Gateway 聚合检查
GET http://127.0.0.1:18081/health       # I2I worker
GET http://127.0.0.1:18082/health       # T2I worker
GET http://127.0.0.1:18083/health       # T2V worker
```

---

## 5. 使用示例

### 5.1 I2I：图像编码

```python
import requests

url = "http://127.0.0.1:18080/encode"

# 单张图像查询，多张图像作为库
resp = requests.post(url, json={
    "scene": "i2i",
    "query": "/data/images/query_airplane.jpg",
    "key": [
        "/data/images/airplane_001.jpg",
        "/data/images/airplane_002.jpg",
        "/data/images/airplane_003.jpg",
    ]
}, timeout=300)

result = resp.json()
print(f"query 向量维度: {len(result['query_embed'][0])}")
print(f"key 向量数量: {len(result['key_embed'])}")
```

### 5.2 T2I：文搜图编码

```python
import requests

url = "http://127.0.0.1:18080/encode"

resp = requests.post(url, json={
    "scene": "t2i",
    "query": "Spindle cell variant of embryonal rhabdomyosarcoma",
    "key": [
        "/data/medical/image_001.jpg",
        "/data/medical/image_002.jpg",
    ]
}, timeout=300)

result = resp.json()
print(f"文本 query 向量: {result['query_embed']}")
print(f"图像 key 向量数量: {len(result['key_embed'])}")
```

### 5.3 T2V：文搜视频编码

```python
import requests

url = "http://127.0.0.1:18080/encode"

resp = requests.post(url, json={
    "scene": "t2v",
    "query": "a band performing in a small club",
    "key": [
        "/data/videos/video_001.mp4",
        "/data/videos/video_002.mp4",
    ]
}, timeout=1200)  # 视频编码耗时较长，建议延长 timeout

result = resp.json()
print(f"文本向量数: {len(result['query_embed'])}")
print(f"视频向量数: {len(result['key_embed'])}")
```

### 5.4 批量 query

```python
# 所有场景均支持 query 为列表
resp = requests.post(url, json={
    "scene": "t2i",
    "query": ["text query 1", "text query 2", "text query 3"],
    "key": ["/data/images/image_001.jpg"]
}, timeout=300)
```

### 5.5 空输入（仅编码单侧）

```python
# 只编码 key，不编码 query（常用于建库阶段）
resp = requests.post(url, json={
    "scene": "i2i",
    "query": None,
    "key": ["/data/images/airplane_001.jpg"]
}, timeout=300)

# 返回 query_embed 为空列表
# { "scene": "i2i", "query_embed": [], "key_embed": [[...]] }
```

---

## 6. 开发说明

### 6.1 各 worker 编码职责

#### I2I Worker（`serve_i2i.py`）

- 接收图像路径列表，调用 `i2i_encode.encode(opt, model, image_paths)`
- 底层使用 base_distill 蒸馏模型（TinyCLIP）
- 空路径列表时直接返回 `[]`，不调用模型

#### T2I Worker（`serve_t2i.py`）

- 分别接收文本列表和图像路径列表，独立编码
- 底层使用 CXR-CLIP 医学图像模型，通过 Hydra 管理配置
- 启动时通过 `_compose_task_cfg()` + `HydraConfig.instance().set_config()` 正确初始化配置

#### T2V Worker（`serve_t2v.py`）

- 分别接收文本列表和视频路径列表，独立编码
- 底层使用 CLIP-VIP 视频理解模型
- 需确保文本张量和视频张量都在同一设备（`text.to(device)` + `video.to(device)`）

### 6.2 公共工具（`common/api_utils.py`）

| 工具 | 说明 |
|---|---|
| `normalize_to_str_list(value)` | 将单值/列表归一化为 `List[str]`，自动过滤空值 |
| `normalize_request(payload)` | 提取并规范化 `scene/query/key/params` 字段 |
| `tensor_to_list(x)` | 将 Tensor 转换为 Python 列表（JSON 可序列化） |
| `isolated_argv(argv0)` | 上下文管理器，临时清空 `sys.argv` 防止 argparse 冲突 |
| `pushd(path)` | 上下文管理器，临时切换工作目录 |
| `ModelGuard` | 基于 `threading.Lock` 的模型推理互斥锁 |

---

## 7. 常见问题解答

### Q1：Gateway 健康检查某个 worker 报 502，但单独访问该 worker 是 200

**原因**：Windows 或企业网络环境下，Python HTTP 客户端读取了系统代理配置，导致访问 `127.0.0.1` 也走代理。

**解决**：`gateway/app.py` 中已配置 `httpx.Client(trust_env=False)`，如仍出现问题请确认 `gateway/app.py` 中的 `build_client()` 未被修改。

### Q2：I2I 启动时报 `unrecognized arguments`

**原因**：uvicorn 启动参数残留在 `sys.argv`，被底层 `argparse` 误读。

**解决**：已在 `serve_i2i.py` 的 `get_model_adapter()` 中通过 `isolated_argv()` 处理。如遇到相关问题，请确认 `common/api_utils.py` 中该工具函数存在且被正确调用。

### Q3：T2I 启动时报 `HydraConfig was not set`

**原因**：Hydra 配置未正确注入。

**解决**：`serve_t2i.py` 中的 `_compose_task_cfg()` 已通过以下方式解决：

```python
with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
    cfg = compose(config_name="train", return_hydra_config=True)
HydraConfig.instance().set_config(cfg)
# 移除 hydra 子树
with open_dict(cfg):
    if "hydra" in cfg:
        del cfg["hydra"]
```

### Q4：T2V 推理时报 `Expected all tensors to be on the same device`

**原因**：文本张量或视频张量未移动到模型所在设备。

**解决**：在 `t2v_encode.py` 的 `encode()` 函数中确保：

```python
text_input_ids = text_input_ids.to(device)
text_input_mask = text_input_mask.to(device)
video = video.to(device)
```

### Q5：输入列表中含有 `null` 时返回 422

**原因**：Pydantic 请求模型对 `query`/`key` 类型定义过严，`null` 在请求解析阶段被拒绝。

**解决**：各 worker 的 `EncodeRequest` 已定义为：

```python
query: Optional[Union[str, List[str]]] = None
key: Optional[Union[str, List[str]]] = None
```

如仍出现 422，请检查 Pydantic 版本是否与 `Optional[Union[...]]` 兼容，或改用 `Optional[Any]`。

### Q6：服务启动成功但向量数值无意义

**原因**：`checkpoint` 路径为空，模型仅初始化结构但未加载训练权重。

**解决**：填写 `launcher/run_all.py` 中的正确 checkpoint 路径，重启服务。

### Q7：worker 报告文件找不到，但本地路径存在

**原因**：算法服务直接从本地文件系统读取路径。如果后端（或前端）传入的路径是相对路径或对方机器的路径，在算法服务所在机器上无法访问。

**解决**：后端调用算法服务前，必须确保路径已映射/下载到算法服务可访问的本地绝对路径。

---

## 8. 与其他组件的集成

### 8.1 后端如何调用算法服务

后端通过 `HttpAlgorithmService.encode()` 调用 Gateway，**所有路由、场景映射、错误处理均由后端承担**：

```
后端 (algorithm_service.py)
  → 将业务 scene（Text2Video）映射为算法 scene（t2v）
  → POST http://127.0.0.1:18080/encode
  → t2v 编码 timeout 为 1200s，其他为 300s
```

### 8.2 算法服务的职责边界

算法服务**只负责**：
- 接收 `query` / `key`
- 编码并返回向量

算法服务**不负责**：
- 检索库管理
- 任务状态跟踪
- 预览 URL 构造
- 向量索引管理
- 前端展示字段

这些业务逻辑全部由后端承担。

### 8.3 调试建议

联调时推荐按以下顺序验证：

```bash
# 第 1 步：确认算法服务全部健康
curl http://127.0.0.1:18080/health

# 第 2 步：用固定测试文件验证各 worker
curl -X POST http://127.0.0.1:18080/encode \
  -H "Content-Type: application/json" \
  -d '{"scene":"i2i","query":"/absolute/path/to/test.jpg","key":[]}'

# 第 3 步：确认后端的 MMR_ALGORITHM_MODE=http 且 MMR_ALGORITHM_GATEWAY_URL 正确
curl http://127.0.0.1:8000/api/v1/health
```