# 多模态检索系统后端技术说明文档（当前代码版本）

## 1. 文档目的

本文档面向三类读者：

- 前端开发同学
- 算法服务开发同学
- 新接手后端的开发同学

目标是让未接触过当前后端代码的人，也能快速理解以下内容：

1. 后端当前到底提供了哪些服务
2. 前端页面应该如何调用这些服务
3. 算法端和后端之间如何分工、如何传输数据
4. 请求和响应的字段格式要求是什么
5. 当前版本有哪些实现边界、约束和默认行为

本文档基于**当前后端代码版本**整理，重点描述的是**已经落到代码中的行为**，而不是仅仅停留在设计讨论层。

---

## 2. 当前后端的定位

当前后端是一个统一的 FastAPI 服务层，位于前端页面与算法编码服务之间，负责把“页面操作”变成“可执行的检索和建库流程”。

后端不负责训练模型，也不负责直接做模型推理细节；它的核心职责是：

- 接收前端请求
- 做参数校验与归一化
- 管理检索库和任务状态
- 组织建库流程
- 调用算法服务生成向量
- 管理本地托管资源
- 管理向量索引与元数据映射
- 返回前端可直接展示的结构化结果

从职责上可以简单理解为：

- **前端**负责页面交互与展示
- **后端**负责编排、资源管理、索引与结果组织
- **算法端**只负责编码，把输入转成向量

---

## 3. 当前版本支持的业务能力

### 3.1 检索任务

当前后端支持三类业务场景：

- `Text2Video`
- `Text2Image`
- `Image2Image`

它们是前端和后端的**业务场景名**。

后端在调用算法端时，会自动映射成算法服务识别的场景名：

| 前端/后端 scene | 算法端 scene |
|---|---|
| `Text2Video` | `t2v` |
| `Text2Image` | `t2i` |
| `Image2Image` | `i2i` |

前端**不需要**自己做这个映射，直接传业务场景名即可。

### 3.2 检索库类型

当前正式支持：

- `Folder`
- `DataBase`

协议层保留了 `LongVideo`，但当前版本**不支持**真正的长视频切片建库与检索。如果收到 `LongVideo`，后端会返回不支持错误。

### 3.3 资源准备方式

当前版本支持两种典型操作：

1. 主动建库
2. 查询时自动触发建库

也就是：

- 前端可以先调用 `/api/v1/vectorize` 做资源准备
- 也可以在 `/api/v1/search` 中打开 `auto_prepare=true`，当库还没准备好时，由后端自动触发后台建库任务

---

## 4. 当前后端的核心设计原则

### 4.1 前端接口尽量稳定

前端调用的核心接口保持稳定，后端内部实现可以演进。当前版本已经把资源管理从“依赖外部磁盘路径”升级成了“后端内部托管资源”，但前端接口没有因此变化。

### 4.2 查询走网络传输，建库不走大文件网络传输

当前版本明确采用下面的原则：

- **查询图片上传**：走 HTTP 网络传输
- **建库资源准备**：前端传资源位置或资源标识，不直接上传整个目录内容

这样做的原因是：

- 查询通常是单张图片，数据量小，适合走 HTTP 上传
- 建库通常是目录级、批量级资源，不适合前端把所有文件通过接口逐个传给后端

### 4.3 后端内部托管资源，不长期依赖原始磁盘路径

这是当前代码版本的重要变化。

后端在建库时，不再把“外部目录中的绝对路径”作为长期服务依赖，而是会把文件纳入后端自己的托管目录。这样即使原始磁盘盘符变化、目录迁移、原始路径失效，已建好的库仍然可以检索和预览。

### 4.4 算法端只做编码，不参与业务规则判断

算法端当前只负责两件事：

- 接收 query / key
- 返回对应 embedding

是否需要建库、是否允许自动准备、如何组织返回结果、如何做预览 URL 生成，都由后端负责。

---

## 5. 当前代码目录与模块说明

当前后端代码主要结构如下：

```text
backend/
├── app/
│   ├── main.py
│   ├── api/v1/
│   ├── core/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   └── workers/
├── data/
│   ├── sqlite/
│   ├── faiss/
│   ├── assets/
│   └── query_uploads/
└── tests/
```

各层职责如下。

### 5.1 `api/v1`

这一层只负责暴露 HTTP 接口。

当前主要接口文件：

- `health.py`
- `stores.py`
- `vectorize.py`
- `tasks.py`
- `search.py`
- `uploads.py`
- `media.py`

### 5.2 `schemas`

这一层定义请求体和响应体的数据结构，前端对接时最应该关注这一层的字段定义。

### 5.3 `services`

这是后端核心业务层，负责实现真正逻辑。

当前主要服务：

- `algorithm_service.py`
- `search_service.py`
- `prepare_service.py`
- `faiss_service.py`
- `object_service.py`
- `store_service.py`

### 5.4 `repositories`

负责 SQLite 的数据库读写。

### 5.5 `workers`

当前是伪异步本地任务执行器，用线程池执行向量化任务。未来可以平滑替换成 Celery。

---

## 6. 当前版本的数据存储方式

当前版本涉及三类核心数据。

### 6.1 SQLite 元数据

用于保存：

- 检索库信息
- 文件对象信息
- 向量映射关系
- 任务状态

默认数据库路径：

```text
MMR_SQLITE_PATH
默认值: data/sqlite/app.db
```

### 6.2 本地索引文件

当前索引层使用本地 `npy + json` 文件模拟 FAISS 的读写流程。

默认目录：

```text
MMR_FAISS_DIR
默认值: data/faiss/
```

每个 store 会生成类似：

```text
{store_id}.npy
{store_id}.json
```

### 6.3 后端托管资源

当前版本已经引入后端内部资源托管。

默认目录：

```text
MMR_MANAGED_ASSETS_DIR
默认值: data/assets/
```

托管资源路径示意：

```text
data/assets/{scene}/{store_id}/{content_hash}/{filename}
```

### 6.4 查询上传目录

前端上传的查询图片不会直接暴露本机路径，而是保存到后端自己的查询上传目录。

默认目录：

```text
MMR_QUERY_UPLOAD_DIR
默认值: data/query_uploads/
```

---

## 7. 资源管理模型：为什么前端不用关心磁盘路径

这是前端和算法同学最容易误解的地方。

### 7.1 原始来源路径

建库时，前端提交的 `keys` 可能是目录路径、文件路径或资源标识。后端会把这些路径视为**来源路径**，用于扫描文件。

### 7.2 托管资源路径

扫描完成后，后端会把资源复制到自己的托管目录，并在数据库里保存：

- 原始来源路径 `source_path_original`
- 托管相对路径 `managed_relpath`
- 托管对象键 `managed_object_key`
- 文件哈希 `content_hash`
- 文件大小 `file_size`
- 文件名 `filename`

### 7.3 为什么这样设计

这样做的直接好处是：

- 原始盘符改变，不影响已建库检索
- 外部目录迁移，不会立刻让历史索引失效
- 预览和算法读取统一依赖后端托管资源
- 前端不需要直接操作本地磁盘路径

### 7.4 前端需要知道什么

前端只需要知道：

- 建库时传 `keys`
- 查询时上传图片或传 query 文本
- 检索结果里拿 `preview_url` 显示内容

前端**不应该依赖任何本机绝对路径**。

---

## 8. 当前提供的 HTTP 接口总览

当前主要接口如下：

```text
GET    /api/v1/health
POST   /api/v1/stores
GET    /api/v1/stores
GET    /api/v1/stores/{store_id}
PUT    /api/v1/stores/{store_id}
DELETE /api/v1/stores/{store_id}
GET    /api/v1/stores/{store_id}/status

POST   /api/v1/vectorize
GET    /api/v1/tasks/{job_id}
POST   /api/v1/search

POST   /api/v1/uploads/query-image
GET    /api/v1/media/preview
```

下面重点说明前端最关心的几个接口。

---

## 9. 健康检查接口

### `GET /api/v1/health`

作用：

- 用于判断后端服务是否存活
- 可用于页面启动时的服务状态探测
- 也适合联调时快速排查后端是否启动成功

返回示例：

```json
{
  "status": "healthy",
  "services": {
    "api": true,
    "faiss": true,
    "minio": true,
    "algorithm": true
  }
}
```

说明：

- 这里的 `algorithm=true` 是后端当前健康页里的服务标志位，不代表一定已经对真实算法网关做了深度联通性验证
- 真正的算法联通性，需要在联调测试中单独验证

---

## 10. 查询图片上传接口

### `POST /api/v1/uploads/query-image`

作用：

- 前端上传单张查询图片
- 后端保存文件并返回 `object_key`
- 供后续 `Image2Image` 检索使用

### 请求格式

请求方式：

- `multipart/form-data`

请求字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `file` | file | 是 | 用户上传的查询图片 |

### 返回示例

```json
{
  "object_key": "uploads/query/4a4f8f5d5e6d4b0f9e4d1c3a9d9a2c8b.jpg",
  "preview_url": "http://127.0.0.1:8000/api/v1/media/preview?object_key=uploads%2Fquery%2F4a4f8f5d5e6d4b0f9e4d1c3a9d9a2c8b.jpg",
  "media_type": "image",
  "filename": "query.jpg"
}
```

### 前端对接建议

对于 `Image2Image` 页面，不建议直接把浏览器中的 File 对象作为检索请求的一部分长期复用。推荐分两步：

1. 先上传图片，拿到 `object_key`
2. 再调用 `/api/v1/search`

这样可以让检索请求仍然保持 JSON 格式，前端逻辑更清晰。

---

## 11. 检索接口

### `POST /api/v1/search`

作用：

- 统一检索入口
- 支持三类任务
- 对前端来说，不需要区分内部算法 worker

### 请求体结构

```json
{
  "scene": "Text2Image",
  "store_type": "Folder",
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
    "uncertainty_weight": 0.6
  }
}
```

### 字段说明

#### 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `scene` | string | 是 | `Text2Video` / `Text2Image` / `Image2Image` |
| `store_type` | string | 是 | `Folder` / `DataBase` |
| `topk` | int | 是 | 返回结果数，默认 10 |
| `need_vectorize` | bool | 否 | 是否允许向量化流程参与当前请求 |
| `input` | object | 是 | 查询输入 |
| `params` | object | 否 | 扩展参数 |

#### `input` 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `text` | `string \\| list[string] \\| null` | 文本查询输入 |
| `image_object_keys` | `list[string]` | 上传成功后得到的图片 object key |

说明：

- `Text2Video` 和 `Text2Image` 一般使用 `input.text`
- `Image2Image` 一般使用 `input.image_object_keys`

#### `params` 字段

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `model_alias` | string | `prod` | 当前模型别名 |
| `auto_prepare` | bool | `true` | 当库未准备好时是否自动触发准备流程 |
| `batch_mode` | bool | `false` | 批量 query 模式预留字段 |
| `uncertainty_weight` | float/null | `null` | 给 `Text2Video` 预留的扩展参数 |

### 响应结构

```json
{
  "scene": "Text2Image",
  "store_type": "Folder",
  "results": [
    {
      "rank": 1,
      "score": 0.912345,
      "media_type": "image",
      "object_key": "managed/Text2Image/store_xxx/hash/file.jpg",
      "preview_url": "http://127.0.0.1:8000/api/v1/media/preview?object_key=...",
      "source_label": "Folder"
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

### 前端必须关注的点

#### 1. 使用 `preview_url` 展示内容

不要使用本地路径，也不要假设 `object_key` 可直接用于 `<img>` 或 `<video>`。

前端展示应该直接使用：

- `preview_url`

#### 2. `results` 为空不一定代表报错

如果库还没准备好且开启了 `auto_prepare=true`，后端可能返回：

- `results = []`
- `meta.store_status = preparing`
- `meta.job_id` 存在

这时前端应提示“资源准备中”，并轮询任务状态，而不是直接报错。

### auto prepare 返回示例

```json
{
  "scene": "Text2Video",
  "store_type": "Folder",
  "results": [],
  "meta": {
    "store_id": "store_001",
    "store_status": "preparing",
    "model_alias": "prod",
    "latency_ms": null,
    "job_id": "job_xxx",
    "message": "检索库尚未准备完成，已开始后台向量化"
  }
}
```

---

## 12. 资源准备接口

### `POST /api/v1/vectorize`

作用：

- 创建或复用检索库
- 启动资源准备任务
- 扫描来源目录
- 把文件纳入后端托管资源
- 调算法生成向量
- 写入索引与数据库

### 请求体示例

```json
{
  "scene": "Image2Image",
  "store_type": "Folder",
  "store_name": "飞机图像库",
  "store_description": "用于 Image2Image 的飞机图片检索库",
  "merge_on_name_conflict": null,
  "keys": [
    "F:\\Code\\RetrievalSys\\backend\\test_data\\ImageRetrieval"
  ],
  "params": {
    "model_alias": "prod",
    "batch_size": 32,
    "force_rebuild": true
  }
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `scene` | string | 是 | 业务场景 |
| `store_type` | string | 是 | 当前支持 `Folder` / `DataBase` |
| `store_name` | string | 是 | 检索库名称 |
| `store_description` | string/null | 否 | 检索库描述 |
| `merge_on_name_conflict` | bool/null | 否 | 同名库冲突时是否合库 |
| `keys` | list[string] | 是 | 资源位置或资源标识 |
| `params.model_alias` | string | 否 | 模型别名 |
| `params.batch_size` | int | 否 | 编码批次大小 |
| `params.force_rebuild` | bool | 否 | 是否强制重建 |

### 关于 `keys` 的重要说明

前端应把 `keys` 理解为：

- 资源来源位置
- 扫描入口
- 建库输入引用

而不是“库名”。

当前版本明确规定：

- 库名来自 `store_name`
- `keys` 只是扫描来源

### 同名库冲突逻辑

如果 `scene + store_type + store_name` 已存在同名库，后端会按 `merge_on_name_conflict` 决定行为。

#### 情况 1：`merge_on_name_conflict = null`

返回 409，提示前端向用户确认是否合库。

#### 情况 2：`merge_on_name_conflict = false`

返回 409，提示前端重新命名。

#### 情况 3：`merge_on_name_conflict = true`

后端复用已有库，并将本次资源准备合并到该库中。

### 成功返回示例

```json
{
  "job_id": "job_xxx",
  "status": "running",
  "store_id": "store_xxx",
  "message": "资源准备任务已启动",
  "conflict_store_id": null,
  "requires_merge_confirmation": false
}
```

### 冲突返回示例

```json
{
  "detail": {
    "code": "STORE_NAME_CONFLICT",
    "message": "已存在同名检索库，请确认是否合库",
    "detail": {
      "store_id": "store_xxx",
      "store_name": "飞机图像库",
      "store_description": "旧库描述",
      "requires_merge_confirmation": true
    },
    "retryable": false
  }
}
```

### 前端对接建议

资源准备页应至少支持：

- 输入库名称 `store_name`
- 输入库描述 `store_description`
- 传资源路径 `keys`
- 接收同名冲突并弹出确认框
- 记录 `job_id` 用于轮询任务状态

---

## 13. 任务状态接口

### `GET /api/v1/tasks/{job_id}`

作用：

- 轮询资源准备任务进度
- 给前端展示当前进度、消息和结果摘要

### 响应示例

```json
{
  "job_id": "job_xxx",
  "state": "running",
  "progress": 65,
  "message": "正在处理第 5/8 个批次",
  "error": null,
  "result": {
    "store_id": "store_001",
    "store_name": "飞机图像库",
    "store_description": "用于 Image2Image 的飞机图片检索库",
    "scanned_files": 643,
    "new_files": 520,
    "new_vectors": 520,
    "skipped_files": 123,
    "skipped_vectors": 123,
    "removed_files": 0,
    "file_count": 520,
    "object_count": 520,
    "vector_count": 520,
    "failed_batches": 0,
    "processed_batches": 8,
    "total_batches": 8,
    "final_index_id": "index_store_001"
  }
}
```

### 字段解释

#### 顶层字段

| 字段 | 说明 |
|---|---|
| `job_id` | 任务 ID |
| `state` | 任务状态 |
| `progress` | 进度百分比 |
| `message` | 当前阶段说明 |
| `error` | 失败时的错误文本 |
| `result` | 任务结果摘要 |

#### `state` 可选值

- `pending`
- `running`
- `success`
- `failed`

#### `result` 中常见统计字段

| 字段 | 含义 |
|---|---|
| `scanned_files` | 本轮扫描到的候选文件总数 |
| `new_files` | 本轮新增纳管并入库的文件数 |
| `new_vectors` | 本轮新增写入索引的向量数 |
| `skipped_files` | 已存在且无需重复处理的文件数 |
| `skipped_vectors` | 已存在且无需重复编码的向量数 |
| `removed_files` | 在增量模式下被标记失活并从索引移除的文件数 |
| `file_count` | 当前库中有效文件数 |
| `object_count` | 当前库中总对象记录数 |
| `vector_count` | 当前库中有效向量数 |
| `failed_batches` | 失败批次数 |
| `processed_batches` | 已处理批次数 |
| `total_batches` | 总批次数 |
| `final_index_id` | 本次任务结束后生成的索引 ID |

### 前端对接建议

资源准备页可以直接使用：

- `progress` 展示进度条
- `message` 展示当前状态文案
- `scanned_files/new_vectors/skipped_vectors` 做结果摘要
- `file_count/vector_count` 展示库最终规模

---

## 14. 检索库管理接口

### `POST /api/v1/stores`

作用：

- 仅创建库记录，不自动建向量

适合：

- 前端先登记一个库，再后续配置和建库

### `GET /api/v1/stores`

作用：

- 查询检索库列表

每个列表项会附带统计字段：

- `file_count`
- `object_count`
- `active_object_count`
- `vector_count`

### `GET /api/v1/stores/{store_id}`

作用：

- 查询单个库详情

响应字段示例：

```json
{
  "store_id": "store_xxx",
  "store_name": "飞机图像库",
  "store_description": "用于 Image2Image 的飞机图片检索库",
  "scene": "Image2Image",
  "store_type": "Folder",
  "resource_path": "F:\\Code\\RetrievalSys\\backend\\test_data\\ImageRetrieval",
  "status": "ready",
  "current_index_id": "index_store_xxx",
  "model_alias": "prod",
  "created_at": "2026-04-15T12:00:00",
  "updated_at": "2026-04-15T12:05:00",
  "file_count": 88,
  "object_count": 88,
  "active_object_count": 88,
  "vector_count": 88
}
```

### `PUT /api/v1/stores/{store_id}`

作用：

- 更新库名称、描述或资源路径
- 可选将状态置为 `not_ready`，让后续重新扫描

### `DELETE /api/v1/stores/{store_id}`

作用：

- 删除整个检索库

当前版本删除时会同步清理：

- `stores` 记录
- `vectors` 记录
- `objects` 记录
- 本地索引文件
- 后端托管资源目录

这意味着删除是一个影响较大的操作，前端应当在 UI 上做二次确认。

### `GET /api/v1/stores/{store_id}/status`

作用：

- 获取更轻量的库状态信息
- 同样会带 `file_count` 和 `vector_count`

---

## 15. 媒体预览接口

### `GET /api/v1/media/preview?object_key=...`

作用：

- 根据 `object_key` 返回图片或视频文件
- 供前端结果列表和详情页直接展示

### 对前端的意义

前端在结果页里只需要：

- 拿到后端返回的 `preview_url`
- 用于 `<img src>` 或视频播放器

前端无需自己拼接 object key 到磁盘路径，也不应访问后端本地文件系统。

---

## 16. 算法服务对接说明

### 16.1 后端如何调用算法端

当前后端有两种算法模式：

- `deterministic`
- `http`

通过环境变量控制：

```text
MMR_ALGORITHM_MODE
```

#### `deterministic`

用于本地开发和测试，不依赖真实算法服务。

#### `http`

用于真实联调，后端通过 HTTP 请求算法 gateway。

算法网关地址通过以下配置指定：

```text
MMR_ALGORITHM_GATEWAY_URL
默认值: http://127.0.0.1:18080
```

### 16.2 算法端输入格式

后端调用算法端时，统一发送：

```json
{
  "scene": "i2i",
  "query": "... 或 [... ]",
  "key": "... 或 [... ]",
  "params": {}
}
```

注意：

- `scene` 已经由后端映射成算法端格式
- `query` 和 `key` 都可以是单值或列表
- 当前后端会先做归一化，再发给算法服务

### 16.3 算法端返回格式

后端期望算法端返回：

```json
{
  "scene": "i2i",
  "query_embed": [[...]],
  "key_embed": [[...], [...]]
}
```

### 16.4 算法同学最需要知道的边界

算法端只需要保证：

- `/encode` 正常工作
- scene 能正确识别
- `query_embed` 和 `key_embed` 返回结构稳定

算法端不需要负责：

- 资源准备任务状态
- 检索库命名
- 冲突处理
- 向量索引管理
- 预览 URL 构造
- 前端展示字段组织

这些都由后端承担。

---

## 17. 检索流程说明

### 17.1 已准备好库的检索流程

```text
前端
  -> POST /api/v1/search
  -> 后端归一化输入
  -> 后端查找目标 store
  -> store 为 ready
  -> 后端调用算法端编码 query
  -> 后端调用索引搜索 topk
  -> 后端恢复 object 信息
  -> 后端构造 preview_url
  -> 返回结果给前端
```

### 17.2 未准备好库的自动准备流程

```text
前端
  -> POST /api/v1/search
  -> 后端发现 store 不是 ready
  -> auto_prepare=true
  -> 后端启动 prepare job
  -> 返回 preparing + job_id
  -> 前端轮询 /api/v1/tasks/{job_id}
  -> 任务完成后再次调用 /search
```

### 17.3 建库流程

```text
前端
  -> POST /api/v1/vectorize
  -> 后端解析 store_name / keys
  -> 扫描来源目录
  -> 文件纳入托管资源区
  -> 调算法端对 key 批量编码
  -> 写入向量与索引
  -> 更新 objects / vectors / stores / jobs
  -> 前端轮询任务状态
```

---

## 18. 前端页面开发建议

### 18.1 检索页建议

前端可以按以下状态组织页面：

#### 输入区

- scene 选择
- store_type 选择
- text 输入框
- 图片上传按钮（用于 Image2Image）
- topk 设置
- auto_prepare 开关

#### 状态区

- 空闲状态
- 检索中状态
- 资源准备中状态
- 检索成功状态
- 错误状态

#### 结果区

单条结果建议展示：

- rank
- 预览图 / 视频缩略图
- score
- source_label
- 查看详情按钮

### 18.2 资源准备页建议

建议展示：

- store_name
- store_description
- scene
- store_type
- keys
- batch_size
- force_rebuild
- 任务状态
- 任务进度
- scanned_files/new_vectors/skipped_vectors
- file_count/vector_count

### 18.3 冲突确认交互

当 `/vectorize` 返回 409 且是 `STORE_NAME_CONFLICT` 时，前端应弹出“是否合库”的确认框，而不是直接提示失败。

---

## 19. 常见错误与建议处理方式

### 19.1 `STORE_NOT_SUPPORTED`

含义：

- 当前版本不支持该库类型或场景

前端处理：

- 直接提示用户当前版本不支持
- 不建议重试

### 19.2 `STORE_NAME_CONFLICT`

含义：

- 已存在同名检索库

前端处理：

- 弹出确认框，询问是否合库
- 用户确认后重试 `/vectorize`，并设置 `merge_on_name_conflict=true`

### 19.3 `STORE_RENAME_REQUIRED`

含义：

- 用户拒绝合库，需要重新命名

前端处理：

- 让用户修改 `store_name`

### 19.4 `404 store not found`

含义：

- store_id 不存在或已被删除

前端处理：

- 刷新库列表
- 提示用户重新选择

### 19.5 `404 object not found`

通常来自 `/media/preview`

含义：

- object_key 已失效或托管资源缺失

前端处理：

- 图片/视频区域展示占位图
- 给出“预览不可用”提示

---

## 20. 当前版本的重要限制

前端和算法同学需要知道，当前版本还存在一些明确的边界。

### 20.1 不是完整的生产级异步系统

当前任务执行是本地线程池，不是完整 Celery 分布式任务体系。

### 20.2 不是完整 FAISS 生产实现

当前索引层使用本地 `npy + json` 模拟所需流程，便于开发和测试。

### 20.3 LongVideo 仍未真正实现

协议中保留了 `LongVideo`，但当前不支持长视频切片和片段级检索。

### 20.4 健康检查不是全链路联通性证明

`/health` 返回健康，并不代表真实算法端一定可用。联调时仍建议跑真实 HTTP 测试。

---

## 21. 环境变量说明

当前常用配置如下：

| 环境变量 | 作用 | 默认值 |
|---|---|---|
| `MMR_SQLITE_PATH` | SQLite 文件路径 | `data/sqlite/app.db` |
| `MMR_FAISS_DIR` | 索引文件目录 | `data/faiss` |
| `MMR_QUERY_UPLOAD_DIR` | 查询图片上传目录 | `data/query_uploads` |
| `MMR_MANAGED_ASSETS_DIR` | 托管资源目录 | `data/assets` |
| `MMR_PUBLIC_BASE_URL` | 对外预览 URL 基础地址 | `http://127.0.0.1:8000` |
| `MMR_ALGORITHM_MODE` | 算法模式 | `deterministic` |
| `MMR_ALGORITHM_GATEWAY_URL` | 算法网关地址 | `http://127.0.0.1:18080` |
| `MMR_DEFAULT_MODEL_ALIAS` | 默认模型别名 | `prod` |

---

## 22. 启动方式

### 22.1 启动后端

在 backend 目录下执行：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 22.2 接口文档

启动后可访问：

```text
http://127.0.0.1:8000/docs
```

### 22.3 常见本地联调方式

如果需要接真实算法网关，可以设置：

```bash
MMR_ALGORITHM_MODE=http
MMR_ALGORITHM_GATEWAY_URL=http://127.0.0.1:18080
```

Windows PowerShell 示例：

```powershell
$env:MMR_ALGORITHM_MODE = "http"
$env:MMR_ALGORITHM_GATEWAY_URL = "http://127.0.0.1:18080"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## 23. 对前端和算法同学的最终总结

### 前端同学需要记住的最重要三点

1. 检索页统一走 `/api/v1/search`
2. Image2Image 先上传图片，再检索
3. 结果展示只使用 `preview_url`，不要使用本机路径

### 算法同学需要记住的最重要三点

1. 后端传给算法端的 scene 已经是 `i2i/t2i/t2v`
2. 算法端只需要做好 `/encode`
3. 后端负责资源管理、建库、索引、任务状态和结果组织

### 新后端同学需要记住的最重要三点

1. 当前版本最重要的改造是“后端内部托管资源”
2. 前端接口要尽量保持稳定，内部实现可以演进
3. 任何改动都要优先保证 `stores/vectorize/tasks/search/uploads/media` 这几条主链路不被破坏

---

## 24. 推荐联调顺序

如果是新同学第一次接触这套系统，建议按这个顺序理解和联调：

1. 先访问 `/api/v1/health`
2. 再看 `/api/v1/uploads/query-image`
3. 再看 `/api/v1/stores` 和 `/api/v1/vectorize`
4. 轮询 `/api/v1/tasks/{job_id}`
5. 最后调 `/api/v1/search`
6. 在前端页面中验证 `preview_url` 是否可展示

这样最容易理清：

- 文件是怎么被接收的
- 库是怎么被建立的
- 检索结果是怎么回来的
- 资源为什么不再依赖原始磁盘路径

---

## 25. 后续可继续扩展的方向

虽然本文重点描述当前版本，但后续可以沿这些方向扩展：

- 引入真正的 FAISS 实现
- 引入 MinIO 对象存储
- 引入 Celery 异步任务体系
- 引入权限控制和鉴权
- 支持 LongVideo 切片建库
- 支持更细粒度的错误码体系
- 提供更完整的统计与诊断接口

当前代码已经为这些扩展留出了一定空间，但目前对前端和算法端来说，最重要的是先把现有接口和状态流转理解清楚。

