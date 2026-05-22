# 后端服务组件文档

本文档面向前端开发人员、算法服务对接人员及后续维护人员，完整说明后端的定位、配置、接口规范、数据模型及常见问题。

---

## 1. 组件概述

后端是一个基于 **FastAPI** 的统一服务层，位于前端与算法服务之间。它负责将用户的页面操作转化为可执行的检索和建库流程。

### 核心职责

- **接收前端请求**，做参数校验与归一化
- **管理检索库**（store）、任务（job）、对象（object）及向量（vector）的元数据
- **托管媒体资源**，使预览链路不依赖原始磁盘路径
- **调用算法服务**生成向量并写入索引
- **执行后台建库任务**，支持任务终止与进度查询
- **长视频预处理**，通过 FFmpeg 切片/抽帧后再向量化
- **返回检索结果**，包含 preview_url，前端可直接展示

### 支持的业务场景

| 业务场景名 | 说明 | 算法 scene |
|---|---|---|
| `Text2Video` | 文搜视频 | `t2v` |
| `Text2Image` | 文搜图 | `t2i` |
| `Image2Image` | 以图搜图 | `i2i` |

### 支持的检索库类型

| 库类型 | 说明 |
|---|---|
| `Folder` | 扫描本地目录建库 |
| `DataBase` | 从 JSON / 文本文件列表建库 |
| `LongVideo` | 对单个长视频文件进行切片/抽帧后建库 |

### 目录结构

```
backend/
├── app/
│   ├── main.py                # FastAPI 应用入口，注册所有路由
│   ├── dependencies.py        # 依赖注入容器（AppContainer）
│   ├── api/v1/                # HTTP 路由层
│   │   ├── health.py
│   │   ├── stores.py
│   │   ├── vectorize.py
│   │   ├── tasks.py
│   │   ├── search.py
│   │   ├── uploads.py
│   │   └── media.py
│   ├── core/
│   │   ├── config.py          # 环境变量配置（MMR_ 前缀）
│   │   ├── enums.py           # 场景/状态枚举及映射函数
│   │   └── errors.py          # 统一错误类 ApiError
│   ├── schemas/               # Pydantic 请求/响应模型
│   ├── services/              # 业务逻辑层
│   │   ├── algorithm_service.py   # 调用算法编码服务
│   │   ├── search_service.py      # 检索逻辑
│   │   ├── prepare_service.py     # 建库流程（扫描→托管→编码→入库）
│   │   ├── longvideo_service.py   # 长视频 FFmpeg 预处理
│   │   ├── faiss_service.py       # 向量索引管理
│   │   ├── object_service.py      # 资源托管与预览 URL
│   │   └── store_service.py       # 检索库 CRUD
│   ├── repositories/          # SQLite 读写层
│   └── workers/
│       └── local_jobs.py      # 线程池任务执行器（支持取消/进程管理）
└── data/
    ├── sqlite/app.db          # 元数据数据库
    ├── faiss/                 # 向量索引文件
    ├── assets/                # 后端托管媒体资源
    ├── query_uploads/         # 查询图片上传目录
    └── preprocess_tmp/        # 长视频预处理临时目录
```

---

## 2. 快速上手

### 2.1 前提条件

- Python ≥ 3.9
- FFmpeg 与 FFprobe（长视频功能必须，可通过环境变量指定路径）
- 项目根目录已安装 `requirements.txt` 依赖

### 2.2 启动后端

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

生产/演示场景（不自动重载）：

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2.3 验证启动状态

```bash
curl http://127.0.0.1:8000/api/v1/health
```

正常返回：

```json
{
  "status": "healthy",
  "services": {
    "api": true,
    "faiss": true,
    "algorithm": true
  }
}
```

### 2.4 接口文档

启动后访问 FastAPI 自动生成的交互式文档：

- Swagger UI：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`

---

## 3. 配置说明

所有配置均通过环境变量注入，以 `MMR_` 为前缀：

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `MMR_SQLITE_PATH` | `data/sqlite/app.db` | SQLite 数据库文件路径 |
| `MMR_FAISS_DIR` | `data/faiss/` | 向量索引文件目录 |
| `MMR_MANAGED_ASSETS_DIR` | `data/assets/` | 托管媒体资源目录 |
| `MMR_QUERY_UPLOAD_DIR` | `data/query_uploads/` | 查询图片上传目录 |
| `MMR_PREPROCESS_TEMP_DIR` | `data/preprocess_tmp/` | 长视频预处理临时目录 |
| `MMR_PUBLIC_BASE_URL` | `http://127.0.0.1:8000` | 生成 preview_url 时使用的公网基础地址 |
| `MMR_ALGORITHM_MODE` | `http` | `http` 使用真实算法服务；`deterministic` 为本地伪随机模式（测试用） |
| `MMR_ALGORITHM_GATEWAY_URL` | `http://127.0.0.1:18080` | 算法网关地址 |
| `MMR_LOCAL_JOB_WORKERS` | `4` | 后台任务线程池大小 |
| `MMR_DEFAULT_TOPK` | `10` | 默认返回结果数 |
| `MMR_MAX_TOPK` | `100` | 允许的最大 topk |
| `MMR_FFMPEG_BIN` | `ffmpeg` | FFmpeg 可执行文件路径 |
| `MMR_FFPROBE_BIN` | `ffprobe` | FFprobe 可执行文件路径 |

**多机部署时必须设置 `MMR_PUBLIC_BASE_URL`**，否则返回的 `preview_url` 会指向 `127.0.0.1:8000` 导致前端无法访问。

---

## 4. HTTP 接口总览

```
GET    /api/v1/health
POST   /api/v1/stores
GET    /api/v1/stores
GET    /api/v1/stores/{store_id}
PUT    /api/v1/stores/{store_id}
DELETE /api/v1/stores/{store_id}
GET    /api/v1/stores/{store_id}/status
POST   /api/v1/vectorize
GET    /api/v1/tasks/{job_id}
POST   /api/v1/tasks/{job_id}/terminate
POST   /api/v1/search
POST   /api/v1/uploads/query-image
GET    /api/v1/media/preview
```

---

## 5. 接口详细说明

### 5.1 健康检查

```
GET /api/v1/health
```

用于确认后端及依赖服务是否正常运行，适合用于页面初始化探测。

**返回示例：**

```json
{
  "status": "healthy",
  "services": {
    "api": true,
    "faiss": true,
    "algorithm": true
  }
}
```

---

### 5.2 查询图片上传

```
POST /api/v1/uploads/query-image
Content-Type: multipart/form-data
```

**请求字段：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | file | 是 | 用户上传的查询图片 |

**返回示例：**

```json
{
  "object_key": "uploads/query/xxx.jpg",
  "preview_url": "http://127.0.0.1:8000/api/v1/media/preview?object_key=uploads%2Fquery%2Fxxx.jpg",
  "media_type": "image",
  "filename": "photo.jpg"
}
```

前端须先上传查询图片，拿到 `object_key` 后再发起检索请求。

---

### 5.3 检索接口

```
POST /api/v1/search
Content-Type: application/json
```

**请求体：**

```json
{
  "scene": "Text2Image",
  "store_type": "Folder",
  "store_id": "store_xxx",
  "topk": 10,
  "need_vectorize": false,
  "input": {
    "text": "a band performing in a small club",
    "image_object_keys": []
  },
  "params": {
    "model_alias": "prod",
    "auto_prepare": true,
    "batch_mode": false,
    "uncertainty_weight": null
  }
}
```

**顶层字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `scene` | string | 是 | `Text2Video` / `Text2Image` / `Image2Image` |
| `store_type` | string | 是 | `Folder` / `DataBase` / `LongVideo` |
| `store_id` | string | 否 | 指定检索库，不填则自动选择 |
| `topk` | int | 否 | 返回结果数，默认 10 |
| `input.text` | string / list / null | 否 | 文本检索输入 |
| `input.image_object_keys` | list[string] | 否 | 图片 object_key 列表（以图搜图用） |
| `params.auto_prepare` | bool | 否 | 库未就绪时是否自动触发建库，默认 true |

**正常检索返回示例：**

```json
{
  "scene": "Text2Image",
  "store_type": "Folder",
  "results": [
    {
      "rank": 1,
      "score": 0.9123,
      "media_type": "image",
      "object_key": "managed/Text2Image/store_xxx/hash/file.jpg",
      "preview_url": "http://127.0.0.1:8000/api/v1/media/preview?object_key=...",
      "source_label": "Folder",
      "parent_video_name": null,
      "segment_start_sec": null,
      "segment_end_sec": null,
      "frame_timestamp_sec": null,
      "derive_type": null
    }
  ],
  "meta": {
    "store_id": "store_xxx",
    "store_status": "ready",
    "model_alias": "prod",
    "latency_ms": 35,
    "job_id": null,
    "message": null
  }
}
```

**库正在准备时的返回示例（auto_prepare 触发）：**

```json
{
  "scene": "Text2Video",
  "store_type": "Folder",
  "results": [],
  "meta": {
    "store_id": "store_xxx",
    "store_status": "preparing",
    "model_alias": "prod",
    "latency_ms": null,
    "job_id": "job_xxx",
    "message": "检索库尚未准备完成，已开始后台向量化"
  }
}
```

前端收到 `store_status=preparing` 且 `job_id` 不为 null 时，应提示用户并轮询任务状态。

**检索结果中的长视频相关字段说明：**

| 字段 | 说明 |
|---|---|
| `parent_video_name` | 来源长视频文件名（LongVideo 库有值） |
| `segment_start_sec` | 片段起始秒数（segment 模式有值） |
| `segment_end_sec` | 片段结束秒数（segment 模式有值） |
| `frame_timestamp_sec` | 帧时间戳（frame 模式有值） |
| `derive_type` | `segment` / `frame` / `raw`（普通文件为 null） |

---

### 5.4 资源准备（建库）接口

```
POST /api/v1/vectorize
Content-Type: application/json
```

**请求体：**

```json
{
  "scene": "Image2Image",
  "store_type": "Folder",
  "store_name": "飞机图像库",
  "store_description": "用于测试的飞机图片集",
  "merge_on_name_conflict": null,
  "keys": ["/absolute/path/to/images/"],
  "params": {
    "model_alias": "prod",
    "batch_size": 64,
    "force_rebuild": false,
    "preprocess_mode": null,
    "interval_sec": null
  }
}
```

**LongVideo 专用参数：**

| 参数 | 说明 |
|---|---|
| `params.preprocess_mode` | `segment`（视频切片）或 `frame`（抽帧），Text2Video 场景必须用 `segment` |
| `params.interval_sec` | 切片间隔（秒），segment 支持 1/3/5/10/30/60，frame 支持 1/3/5/10/30 |

**同名库冲突处理：**

| `merge_on_name_conflict` | 后端行为 |
|---|---|
| `null` | 检测到同名库时返回 409，要求前端确认 |
| `true` | 复用已有库，合并本次资源 |
| `false` | 检测到同名库时返回 409，要求重新命名 |

**成功返回示例：**

```json
{
  "job_id": "job_xxx",
  "status": "running",
  "store_id": "store_xxx",
  "message": "资源准备任务已启动"
}
```

**冲突返回示例（HTTP 409）：**

```json
{
  "detail": {
    "code": "STORE_NAME_CONFLICT",
    "message": "已存在同名检索库，请确认是否合库",
    "detail": {
      "store_id": "store_xxx",
      "store_name": "飞机图像库",
      "requires_merge_confirmation": true
    }
  }
}
```

---

### 5.5 任务状态查询

```
GET /api/v1/tasks/{job_id}
```

**返回示例：**

```json
{
  "job_id": "job_xxx",
  "state": "running",
  "progress": 65,
  "message": "正在处理第 5/8 个批次",
  "error": null,
  "phase": "vectorizing",
  "can_terminate": true,
  "terminated_at": null,
  "terminate_reason": null,
  "result": {
    "store_id": "store_xxx",
    "store_name": "飞机图像库",
    "scanned_files": 520,
    "new_vectors": 300,
    "skipped_vectors": 100,
    "failed_batches": 0,
    "processed_batches": 5,
    "total_batches": 8,
    "generated_segments": 0,
    "generated_frames": 0,
    "final_index_id": null
  }
}
```

**`state` 可选值：**

| 值 | 含义 |
|---|---|
| `pending` | 等待执行 |
| `running` | 执行中 |
| `success` | 成功完成 |
| `failed` | 执行失败 |
| `terminated` | 用户手动终止 |

**`phase` 可选值（反映当前执行阶段）：**

| 值 | 含义 |
|---|---|
| `validating` | 扫描验证资源 |
| `preprocessing` | 长视频预处理（FFmpeg 切片/抽帧） |
| `vectorizing` | 批量调用算法编码 |
| `saving` | 写入索引与数据库 |

### 5.6 任务终止

```
POST /api/v1/tasks/{job_id}/terminate
Content-Type: application/json

{ "reason": "用户手动终止" }
```

`can_terminate` 为 `true` 时才允许终止（`saving` 阶段不可终止，防止索引损坏）。

---

### 5.7 检索库管理接口

#### 创建检索库（仅建元数据，不建库）

```
POST /api/v1/stores
```

#### 查询检索库列表

```
GET /api/v1/stores
```

返回 `items` 数组，每项包含 `file_count`、`object_count`、`active_object_count`、`vector_count`。

#### 查询单个库详情

```
GET /api/v1/stores/{store_id}
```

返回字段包括：`store_id`、`store_name`、`scene`、`store_type`、`status`、`resource_path`、`current_index_id`、`preprocess_mode`、`interval_sec`、`file_count`、`vector_count` 等。

#### 更新检索库

```
PUT /api/v1/stores/{store_id}
```

支持更新 `store_name`、`store_description`、`resource_path`、`preprocess_mode`、`interval_sec`。  
设置 `rescan: true` 可将库状态置为 `not_ready`，触发后续重新扫描建库。

#### 删除检索库

```
DELETE /api/v1/stores/{store_id}
```

**该操作会同步清理：**
- SQLite 中的 stores / objects / vectors / jobs 记录
- `data/faiss/` 中的索引文件
- `data/assets/` 中的托管媒体资源

前端应在 UI 上做二次确认后再调用。

#### 查询库状态（轻量接口）

```
GET /api/v1/stores/{store_id}/status
```

返回库的当前状态及计数统计，比完整详情接口更轻量。

---

### 5.8 媒体预览接口

```
GET /api/v1/media/preview?object_key={encoded_key}
```

根据 `object_key` 返回对应媒体文件（图片或视频），前端直接使用检索结果中的 `preview_url` 即可，无需自行拼接。

---

## 6. 数据模型与存储

### 6.1 SQLite 元数据

默认路径：`data/sqlite/app.db`

主要数据表：

| 表 | 说明 |
|---|---|
| `stores` | 检索库元数据（名称、场景、状态、资源路径等） |
| `objects` | 托管对象元数据（文件 hash、托管路径、长视频派生信息等） |
| `vectors` | 向量元数据（FAISS ID、模型版本、所属库） |
| `jobs` | 任务状态（进度、阶段、结果统计等） |

### 6.2 向量索引

当前使用本地 `npy + json` 文件模拟 FAISS 读写（每个 store 生成 `{store_id}.npy` 和 `{store_id}.json`），未来可平滑替换为真实 FAISS。

索引默认目录：`data/faiss/`

### 6.3 托管资源目录结构

```
data/assets/
└── {scene}/
    └── {store_id}/
        └── {content_hash}/
            └── {filename}
```

例如：`data/assets/Image2Image/store_xxx/abc123/airplane.jpg`

优点：原始磁盘路径迁移后不影响已建库的检索，预览链路始终可用。

### 6.4 查询上传目录

```
data/query_uploads/
```

前端上传的查询图片保存在此，不会与托管资源混用。

---

## 7. 建库流程说明

### 7.1 普通文件夹建库流程

```
前端 POST /api/v1/vectorize
 ↓ 后端解析请求，解决同名冲突
 ↓ 创建 job，将 store 状态置为 preparing
 ↓ [后台线程] 扫描来源目录，收集文件路径
 ↓ 将文件复制到 data/assets/（去重，按 content_hash）
 ↓ 调用算法服务批量编码 key 向量
 ↓ 写入 objects / vectors 表
 ↓ 重建 FAISS 索引
 ↓ 更新 store 状态为 ready，job 状态为 success
前端轮询 GET /api/v1/tasks/{job_id}
```

### 7.2 长视频建库流程

```
前端 POST /api/v1/vectorize  (store_type=LongVideo)
 ↓ 验证 preprocess_mode 和 interval_sec 合法性
 ↓ [后台线程] FFmpeg 对视频切片（segment）或抽帧（frame）
 ↓ 校验每个片段/帧可被 t2v/t2i 模型正常解码
 ↓ 将片段/帧文件托管到 data/assets/
 ↓ 批量调用算法服务编码（segment→t2v，frame→t2i）
 ↓ 写入 objects（附 parent_video_name、segment_start_sec 等字段）
 ↓ 重建索引，完成后清理预处理临时目录
```

### 7.3 检索流程

```
前端 POST /api/v1/search
 ↓ 后端找到目标 store
 ↓ 若 store 未 ready 且 auto_prepare=true → 触发建库，返回 preparing + job_id
 ↓ 若 store 为 ready
 ↓ 调用算法服务编码 query
 ↓ 在 FAISS 索引中搜索 topk
 ↓ 从 objects 表恢复元数据，构造 preview_url
 ↓ 返回带 preview_url 的结果列表
```

---

## 8. 算法服务集成说明

### 8.1 两种算法模式

通过 `MMR_ALGORITHM_MODE` 切换：

- **`http`**（默认）：调用真实算法网关，适用于联调和生产
- **`deterministic`**：本地伪随机向量，不依赖算法服务，适用于后端单独测试

### 8.2 场景映射

后端自动完成业务场景到算法场景的映射（定义在 `core/enums.py`）：

```python
Text2Video → t2v
Text2Image → t2i
Image2Image → i2i
```

前端传业务场景名，算法侧传内部场景名，映射由后端承担。

### 8.3 Timeout 设置

后端调用算法服务时，t2v 场景 timeout 为 **1200s**（视频编码耗时），其他场景为 **300s**。

---

## 9. 常见问题解答

### Q1：后端启动报 `unsupported operand type(s) for |`

Python 3.8 不支持 `X | Y` 联合类型语法。升级到 Python 3.9+。

### Q2：检索结果有内容但图片/视频加载失败

99% 是 `MMR_PUBLIC_BASE_URL` 未正确设置。用 F12 查看图片请求的 Host：
- 是 `127.0.0.1:8000` → 后端 `MMR_PUBLIC_BASE_URL` 未设置为外网可访问地址
- IP 是旧地址 → 算力机网络变化后后端未重启
- 正确 IP 但 502 → 反代配置未生效

**重要**：数据库中存储的 `preview_url` 快照不影响实际返回值，后端每次返回时都用当前 `MMR_PUBLIC_BASE_URL` 实时重拼，只需重启后端即可，无需重建索引。

### Q3：向量化任务一直 `pending`

- 确认后台线程池未被占满（调大 `MMR_LOCAL_JOB_WORKERS`）
- 确认来源路径在算法服务所在机器上真实可访问
- 查看后端日志确认是否有报错

### Q4：长视频建库时任务 failed，报 `ffprobe validation failed`

- 确认视频文件格式被 FFmpeg 支持（推荐 mp4/h264）
- 确认 `MMR_FFMPEG_BIN` / `MMR_FFPROBE_BIN` 路径正确
- 在命令行手动运行 `ffprobe -v error ... <file>` 查看具体错误

### Q5：前端调用 `/search` 返回 `store not found`

- 确认 `store_id` 字段正确
- 确认数据库中该 store 记录存在（可通过 `GET /api/v1/stores` 验证）

### Q6：算法服务正常但后端调用报 `Algorithm encode failed`

- 确认 `MMR_ALGORITHM_GATEWAY_URL` 配置正确
- 确认算法服务所在机器网络可达
- 查看算法服务日志确认是否有具体错误

---

## 10. 与其他组件的集成

### 10.1 与前端集成

- 前端通过反代 `/api` 访问后端，本地开发时由 Vite 代理（`VITE_BACKEND_PROXY_TARGET`）
- 前端不直接调用算法服务，所有编码请求通过后端转发
- 前端使用业务场景名（`Text2Video`），后端负责映射到算法 scene

### 10.2 与算法服务集成

- 后端仅通过 `POST /encode` 调用算法 Gateway
- 建库时传 `key` 路径列表（后端托管资源的绝对路径）
- 检索时传 `query`（文本或查询图片路径）
- 算法服务返回向量后，由后端负责写入索引和数据库

### 10.3 不同部署场景

**单机开发：** 前端 + 后端 + 算法服务均在本机，直接用默认配置。

**双机部署（算力机 + 演示机）：** 算力机运行后端 + 算法服务，演示机运行前端。  
需要设置 `MMR_PUBLIC_BASE_URL=http://<算力机IP>:8000`，前端 `VITE_BACKEND_PROXY_TARGET=http://<算力机IP>:8000`。