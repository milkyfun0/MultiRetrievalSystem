# 前端应用组件文档

本文档面向后端与算法服务对接人员、以及新加入前端开发的同学，说明前端的功能结构、技术架构、接口依赖、状态管理及常见问题。

---

## 1. 组件概述

前端是一个基于 **Vue 3 + TypeScript** 的单页应用（SPA），使用 **Vite** 构建，**Element Plus** 作为 UI 组件库。

它为用户提供三类能力：
- **检索**：发起多模态检索（文搜视频、文搜图、以图搜图），展示结果卡片与详情弹窗
- **资源准备**：提交向量化任务，查看任务进度与详情，支持手动终止任务
- **资源管理**：查看和删除已有检索库

### 技术栈

| 层 | 技术 |
|---|---|
| 框架 | Vue 3（Composition API + `<script setup>`） |
| 语言 | TypeScript |
| 构建工具 | Vite 6 |
| 路由 | Vue Router 4 |
| 状态管理 | Pinia |
| HTTP 客户端 | Axios |
| UI 组件库 | Element Plus 2 |

### 目录结构

```
frontend/src/
├── api/                    # 后端接口封装
│   ├── client.ts           # Axios 实例（反代 /api 路径）
│   ├── search.ts           # 检索、查询图片上传
│   ├── prepare.ts          # 向量化任务提交、状态查询、终止
│   └── stores.ts           # 检索库增删改查
├── components/
│   ├── common/             # 通用组件（导航栏、状态徽章、分页等）
│   ├── search/             # 检索页组件（搜索输入、结果卡、详情弹窗等）
│   └── prepare/            # 资源准备组件（表单、任务列表、任务详情）
├── composables/
│   ├── useLayoutMode.ts    # 视图模式（网格/流式）切换逻辑
│   └── usePolling.ts       # 轮询工具
├── stores/
│   ├── search.ts           # 检索页全局状态（Pinia）
│   └── prepare.ts          # 资源准备页全局状态（Pinia）
├── types/                  # TypeScript 类型定义（DTO、VM、枚举）
├── utils/
│   ├── mapper.ts           # DTO → ViewModel 映射函数
│   ├── display.ts          # 枚举中文映射（场景名、库类型、状态等）
│   ├── constants.ts        # 常量（场景列表、库类型列表）
│   └── normalize.ts        # 输入归一化（批量文本拆行等）
└── views/
    ├── SearchPage.vue      # 检索页
    ├── PreparePage.vue     # 资源准备页
    └── StoreManagePage.vue # 资源管理页
```

---

## 2. 快速上手

### 2.1 前提条件

- Node.js ≥ 16
- 后端服务已启动（默认 `http://127.0.0.1:8000`）

### 2.2 安装依赖

```bash
cd frontend
npm install
```

### 2.3 启动开发服务器

```bash
cd frontend
npm run dev
```

成功后访问 `http://localhost:5173`。

### 2.4 构建生产版本

```bash
cd frontend
npm run build
# 产物位于 frontend/dist/
```

### 2.5 预览构建产物

```bash
npm run preview
```

---

## 3. 配置说明

### 3.1 环境变量

复制 `.env.example` 为 `.env.local` 并按需修改：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `VITE_BACKEND_PROXY_TARGET` | `http://127.0.0.1:8000` | 开发模式下 `/api` 请求的反代目标 |

```bash
cp .env.example .env.local
# 修改 VITE_BACKEND_PROXY_TARGET 为后端地址
```

### 3.2 Vite 代理配置

`vite.config.ts` 中已配置反代，开发模式下所有 `/api` 请求自动转发到后端：

```ts
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: process.env.VITE_BACKEND_PROXY_TARGET || 'http://127.0.0.1:8000',
      changeOrigin: true,
    },
  },
},
```

**跨机访问时**（后端在另一台机器），只需修改 `VITE_BACKEND_PROXY_TARGET` 重启 dev server，无需修改代码。

### 3.3 多机演示场景

当算力机和演示机分离时：

```bash
# 演示机上运行前端
VITE_BACKEND_PROXY_TARGET=http://<算力机IP>:8000 npm run dev
```

或将产物打包后用 nginx 反代：

```nginx
location /api/ {
    proxy_pass http://<算力机IP>:8000/api/;
}
```

---

## 4. 页面功能说明

### 4.1 检索页（SearchPage.vue）

检索页是系统的核心入口，支持三种检索模式的统一操作流程。

**主要功能：**

- 顶部 Tab 切换模式（视频检索 / 图像检索 / 以图搜图）
- 按库类型筛选并选择具体检索库
- 文本输入框（文本模式）或图片上传区（以图搜图模式）
- 高级参数面板（topk、auto_prepare、uncertainty_weight 等）
- 结果展示（网格视图 / Rank 流视图切换）
- 结果详情弹窗（支持前后条导航）
- 当前检索库信息卡片（显示文件数、向量数等）

**以图搜图的特殊流程：**

1. 用户选择本地图片 → 前端调用 `POST /api/v1/uploads/query-image` 上传
2. 后端返回 `object_key` → 前端记录到 `uploadedQueryImages` 列表
3. 用户点击搜索 → 前端用 `object_key` 发起检索请求

前端**不会**把浏览器本地文件路径传给后端，必须先上传获取 `object_key`。

### 4.2 资源准备页（PreparePage.vue）

用于创建向量化任务，支持所有三种库类型（Folder、DataBase、LongVideo）。

**主要功能：**

- 库类型和模式选择
- 库名称、备注输入
- 资源路径或库标识输入
- 高级参数（模型版本、批次大小、强制重建）
- LongVideo 专属参数（预处理模式、间隔秒数）
- 同名库冲突时弹窗确认是否合库
- 任务列表展示（显示进度、状态、阶段）
- 任务详情弹窗（统计文件数/向量数/批次）
- 支持手动终止正在运行的任务

**LongVideo 参数自动联动：**

选择 `LongVideo` 库类型时，`preprocess_mode` 和 `interval_sec` 会根据 `scene` 自动设置默认值（Text2Video → segment + 5s，其他 → frame + 3s）。

### 4.3 资源管理页（StoreManagePage.vue）

用于查看和删除已有检索库，支持按场景和库类型筛选，带分页。

**主要功能：**

- 筛选与分页展示检索库列表
- 顶部统计卡片（总库数、可用库数、长视频库数、总向量数）
- 查看单个检索库详情弹窗（基础标识、来源路径、预处理配置）
- 删除检索库（二次确认，成功后刷新列表）

**删除操作说明：** 前端调用 `DELETE /api/v1/stores/{store_id}`，后端会同步清理索引文件与托管资源，该操作不可撤销，UI 上做了二次确认弹窗。

---

## 5. 与后端接口的对接

### 5.1 接口依赖总览

```
GET    /api/v1/health                      # 服务探测
GET    /api/v1/stores                      # 获取检索库列表
GET    /api/v1/stores/{store_id}           # 获取检索库详情
GET    /api/v1/stores/{store_id}/status    # 获取库状态（轻量）
DELETE /api/v1/stores/{store_id}           # 删除检索库

POST   /api/v1/search                      # 发起检索
POST   /api/v1/vectorize                   # 提交向量化任务
GET    /api/v1/tasks/{job_id}              # 查询任务状态
POST   /api/v1/tasks/{job_id}/terminate    # 终止任务

POST   /api/v1/uploads/query-image         # 上传查询图片
GET    /api/v1/media/preview               # 预览媒体文件
```

### 5.2 检索请求格式

**文本检索（Text2Video / Text2Image）：**

```json
{
  "scene": "Text2Video",
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
    "uncertainty_weight": 0.6,
    "return_detail_meta": false
  }
}
```

**以图搜图（Image2Image）：**

```json
{
  "scene": "Image2Image",
  "store_type": "Folder",
  "store_id": "store_xxx",
  "topk": 10,
  "input": {
    "text": null,
    "image_object_keys": ["uploads/query/abc123.jpg"]
  },
  "params": {
    "model_alias": "prod",
    "auto_prepare": true
  }
}
```

### 5.3 向量化任务请求格式

**Folder / DataBase 类型：**

```json
{
  "scene": "Image2Image",
  "store_type": "Folder",
  "store_name": "飞机图像库",
  "store_description": "测试用飞机图片集",
  "merge_on_name_conflict": null,
  "keys": ["/absolute/path/to/images/"],
  "params": {
    "model_alias": "prod",
    "batch_size": 64,
    "force_rebuild": false
  }
}
```

**LongVideo 类型（额外参数）：**

```json
{
  "scene": "Text2Video",
  "store_type": "LongVideo",
  "store_name": "演讲视频库",
  "keys": ["/absolute/path/to/long_video.mp4"],
  "params": {
    "model_alias": "prod",
    "batch_size": 64,
    "force_rebuild": false,
    "preprocess_mode": "segment",
    "interval_sec": 5
  }
}
```

### 5.4 同名库冲突处理逻辑

1. 首次提交时 `merge_on_name_conflict: null`
2. 后端返回 409 → 前端弹出 `window.confirm` 询问用户
3. 用户确认合库 → 重新提交，附 `merge_on_name_conflict: true`
4. 用户取消 → 提示修改库名，不自动重试

### 5.5 任务状态轮询

前端在打开任务详情弹窗期间，会自动轮询任务状态：

```ts
// composables/usePolling.ts
// 每隔固定间隔调用 getTaskStatus(jobId)
// 收到 success / failed / terminated 后停止轮询
```

任务状态字段 `phase` 对应当前执行阶段，前端将其渲染为进度提示文字：

| phase | 显示文字 |
|---|---|
| `validating` | 扫描验证资源 |
| `preprocessing` | 长视频预处理中 |
| `vectorizing` | 向量化编码中 |
| `saving` | 写入索引 |

---

## 6. 状态管理

前端使用 **Pinia** 管理全局状态。

### 6.1 检索页状态（`stores/search.ts`）

| 状态 | 说明 |
|---|---|
| `mode` | 当前检索模式（Text2Video / Text2Image / Image2Image） |
| `storeType` | 当前库类型 |
| `selectedStoreId` | 当前选中库 ID |
| `queryText` | 文本输入 |
| `uploadedQueryImages` | 已上传的查询图片列表（含 objectKey、previewUrl） |
| `searchState` | idle / validating / searching / success / empty / error |
| `results` | 检索结果 ViewModel 列表 |
| `detailModalVisible` | 结果详情弹窗开关 |
| `detailCurrentIndex` | 当前查看的结果索引 |

`searchState` 的流转：

```
idle → validating（点击搜索）
     → searching（参数验证通过，发起请求）
     → success（有结果）
     → empty（无结果或库 preparing）
     → error（请求失败）
```

### 6.2 资源准备页状态（`stores/prepare.ts`）

| 状态 | 说明 |
|---|---|
| `form` | 表单字段（scene、storeType、storeName、keys 等） |
| `tasks` | 当前会话内的任务 ViewModel 列表 |
| `currentTaskId` | 当前查看的任务 ID |
| `submitting` | 任务提交中状态 |
| `taskDetailVisible` | 任务详情弹窗开关 |

### 6.3 ViewModel 设计

前端把后端 DTO 映射为 ViewModel，隔离展示逻辑：

| DTO | ViewModel |
|---|---|
| `SearchResultItemDTO` | `SearchResultCardVM`（含 `thumbnailUrl`、`mediaType`） |
| `TaskStatusResponseDTO` | `VectorizeTaskVM`（含格式化时间、阶段文字等） |

映射逻辑集中在 `utils/mapper.ts`。

---

## 7. 枚举值的中文映射

前端统一在 `utils/display.ts` 中定义展示文字，后端/接口仍使用英文字段值：

| 后端字段值 | 前端显示 |
|---|---|
| `Text2Video` | 视频检索 |
| `Text2Image` | 图像检索 |
| `Image2Image` | 以图搜图 |
| `Folder` | 文件夹 |
| `DataBase` | 数据库 |
| `LongVideo` | 长视频 |
| `not_ready` | 未准备 |
| `preparing` | 准备中 |
| `ready` | 已就绪 |
| `failed` | 失败 |
| `pending` | 等待中 |
| `running` | 执行中 |
| `success` | 成功 |
| `terminated` | 已终止 |
| `segment` | 视频切片 |
| `frame` | 抽帧模式 |

---

## 8. 媒体预览链路

### 8.1 图片预览

图片预览链路简单可靠：

1. 后端返回 `preview_url`（已包含完整 URL）
2. 前端用 `<img :src="preview_url">` 直接展示
3. 若 `preview_url` 为空，fallback 到 `/api/v1/media/preview?object_key=...`

### 8.2 视频预览

视频预览链路更复杂，涉及多个因素：

- 前端使用 `<video controls :src="preview_url">` 播放
- 后端 `/media/preview` 需支持 Range 请求（浏览器视频流需要）
- 视频编码必须为浏览器可播放格式（推荐 H.264/AAC in MP4）

**结果卡中视频缩略图：** 前端目前使用 `<video>` 标签尝试显示，是否能显示首帧取决于浏览器行为与视频格式。

**详情弹窗中的视频：** 详情弹窗使用完整的 `<video controls>` 播放器，视频可用性主要取决于编码格式和后端预览接口的实现。

**如果视频无法预览但检索结果正确：** 这不是检索失败，而是视频编码或预览接口问题，应排查后端 `/media/preview` 接口返回头和视频格式。

### 8.3 长视频片段预览

长视频建库后，检索结果的 `derive_type` 为 `segment` 或 `frame`：

- `segment`：片段视频，使用视频播放器；结果卡同时显示时间范围（`segment_start_sec` ~ `segment_end_sec`）
- `frame`：抽取的帧图片，使用图片展示；结果卡显示帧时间戳（`frame_timestamp_sec`）

---

## 9. 常见问题解答

### Q1：前端启动后访问报 404 或一片空白

- 确认 `npm install` 已执行
- 确认 `npm run dev` 正常启动，端口 5173 未被占用
- 检查浏览器控制台是否有 JS 报错

### Q2：检索请求失败，报 Network Error 或 502

- 确认后端服务已启动（`curl http://127.0.0.1:8000/api/v1/health`）
- 确认 `VITE_BACKEND_PROXY_TARGET` 配置正确
- 若后端在另一台机器，确认端口对外开放且网络可达

### Q3：以图搜图时点击搜索没有反应或报"请先上传查询图片"

- 以图搜图必须先上传图片才能发起检索
- 上传入口在检索页切换到"以图搜图"模式后的图片上传区域
- 确认 `/api/v1/uploads/query-image` 接口可用

### Q4：检索结果有数据但图片/视频加载失败（小方块或黑屏）

- 用 F12 查看图片/视频请求的实际 URL 和状态码
- 若 URL 中包含 `127.0.0.1:8000` 但访问的是另一台机器 → 后端 `MMR_PUBLIC_BASE_URL` 未正确设置，需在后端机器上修改并重启后端
- 若状态码 404 → 托管资源可能未正确复制，检查 `data/assets/` 目录
- 若状态码 200 但视频黑屏 → 视频编码格式问题，建议转码为 H.264/MP4

### Q5：资源准备提交后任务列表没有显示

- 当前版本任务列表仅保存在当前会话内存中，刷新页面后历史任务列表不会保留
- 提交成功后会自动打开任务详情弹窗，可从弹窗查看进度
- 刷新页面后可通过 `GET /api/v1/tasks/{job_id}` 直接查询历史任务状态

### Q6：任务进度长时间停在某个百分比不动

- `vectorizing` 阶段（30%~95%）耗时最长，取决于资源数量和模型推理速度
- 视频编码（T2V）每批次耗时可能达数分钟
- 可在后端终端查看日志确认任务是否仍在运行

### Q7：如何在生产环境部署前端

```bash
# 构建
npm run build

# 产物在 frontend/dist/
# 用 nginx 托管静态文件，并反代 /api 到后端
```

参考 nginx 配置（简化版）：

```nginx
server {
    listen 80;
    root /path/to/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://<后端地址>:8000/api/;
        proxy_set_header Host $host;
    }
}
```

---

## 10. 与其他组件的集成

### 10.1 与后端的职责边界

| 职责 | 由谁承担 |
|---|---|
| 场景名（Text2Video）→ 算法 scene（t2v）映射 | 后端 |
| 媒体文件路径管理 | 后端（托管到 data/assets/） |
| 向量索引管理 | 后端（FAISS） |
| 预览 URL 生成 | 后端（基于 MMR_PUBLIC_BASE_URL 实时构造） |
| 任务状态持久化 | 后端（SQLite） |
| 前端任务列表展示 | 前端（当前会话内存） |

### 10.2 前端不直接调用算法服务

前端通过后端 `/api/v1/search` 发起检索，后端内部调用算法服务完成编码。前端无需关心算法服务地址或编码细节。

### 10.3 联调推荐顺序

对于后端/算法同学，理解前端行为的推荐顺序：

```
1. GET  /api/v1/health              → 确认后端可达
2. GET  /api/v1/stores              → 确认检索库列表接口返回完整字段
3. GET  /api/v1/stores/{store_id}   → 确认详情字段（file_count、vector_count 等）
4. POST /api/v1/uploads/query-image → 确认图片上传返回 object_key 和 preview_url
5. POST /api/v1/vectorize           → 确认建库任务可正常启动
6. GET  /api/v1/tasks/{job_id}      → 确认任务状态字段结构完整
7. POST /api/v1/search              → 确认检索返回 preview_url 可用
8. GET  /api/v1/media/preview       → 确认图片/视频能正常预览
```