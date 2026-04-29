# 多模态检索系统前端技术说明文档（当前实现版）

## 1. 文档目的

本文档面向未直接参与前端开发的后端与算法同学，说明当前多模态检索系统前端的实现结构、页面能力、接口对齐方式、状态流转、媒体预览链路、已知限制与联调要点。

本文档重点回答以下问题。

- 当前前端到底提供了哪些页面与功能
- 前端如何调用后端接口
- 前端向后端发送什么格式的数据
- 前端如何消费后端返回的数据
- 图像检索、视频检索、资源准备、资源管理分别怎么走
- 哪些问题属于前端，哪些问题属于后端或算法侧
- 联调时最容易踩坑的地方有哪些

本文档基于当前已经完成的前端版本整理，重点描述“实际实现与当前约定”，而不是理想化设计。

---

## 2. 一句话理解当前前端

当前前端是一个面向多模态检索系统的 Web 界面，主要承担三类职责。

- 为用户提供检索入口，包括视频检索、图像检索、以图搜图
- 为管理员或开发人员提供资源准备入口，用于新建向量化任务并跟踪任务状态
- 为管理员或开发人员提供资源管理入口，用于查看已有检索库、查看统计信息、删除检索库

前端不负责模型推理，不负责索引构建，不负责文件持久化，也不负责结果排序逻辑。前端只负责页面交互、参数组织、接口调用、状态展示与错误提示。

---

## 3. 当前前端页面与导航结构

### 3.1 顶部一级导航

当前前端包含三个一级入口。

- 检索
- 资源准备
- 资源管理

### 3.2 页面职责

#### 检索页

用于发起三类检索任务。

- 视频检索，对应业务 scene `Text2Video`
- 图像检索，对应业务 scene `Text2Image`
- 以图搜图，对应业务 scene `Image2Image`

该页面提供以下能力。

- 模式切换
- 检索库类型与具体检索库选择
- 文本输入或查询图片上传
- 检索参数配置
- 结果展示，支持网格和 Rank 流视图
- 结果详情弹窗
- 当前检索库信息展示

#### 资源准备页

用于创建向量化任务并查看任务执行情况。

该页面提供以下能力。

- 任务模式选择
- 检索库类型选择
- 库名称输入
- 库备注输入
- 资源路径或库标识输入
- 模型版本、批量大小、强制重建设置
- 同名库冲突时合库确认
- 任务列表展示
- 任务详情弹窗
- 失败任务重试与状态刷新

#### 资源管理页

用于查看当前已有检索库并删除检索库。

该页面提供以下能力。

- 查看检索库列表
- 查看库状态、模式、备注、文件数、向量数
- 删除检索库
- 删除后根据后端返回信息提示用户

---

## 4. 前端与后端、算法端的职责边界

### 4.1 前端负责什么

- 采集用户输入
- 对输入做基础校验
- 调用后端 API
- 展示结果与任务状态
- 对后端错误码或错误信息做用户可理解的提示
- 在图搜图场景先上传查询图片，再使用后端返回的 `object_key` 发起检索

### 4.2 后端负责什么

- 对外提供统一业务接口
- 管理 store、job、object、vector 等元数据
- 调用算法端完成编码
- 管理向量索引
- 返回检索结果
- 返回任务进度与统计
- 负责资源删除、预览地址、自动准备等业务逻辑

### 4.3 算法端负责什么

- 仅负责把文本、图像或视频编码成 embedding
- 不负责检索库管理
- 不负责任务状态
- 不负责预览地址生成
- 不负责结果卡信息组织

### 4.4 关键边界结论

- 前端只与后端业务接口交互，不直接调用算法端 `/encode`
- 前端使用业务 scene `Text2Video`、`Text2Image`、`Image2Image`
- 算法端内部 scene `t2v`、`t2i`、`i2i` 的映射由后端承担

---

## 5. 当前前端支持的核心业务流程

## 5.1 文本检索视频

适用于 `Text2Video`。

流程如下。

1. 用户在搜索页选择“视频检索”
2. 输入文本 query
3. 选择检索库类型，如文件夹
4. 选择具体检索库
5. 点击搜索
6. 前端调用 `POST /api/v1/search`
7. 后端返回结果列表与元信息
8. 前端展示结果卡与详情弹窗

## 5.2 文本检索图像

适用于 `Text2Image`。

流程与文本检索视频基本一致，只是 scene 不同，返回的媒体类型通常为 image。

## 5.3 以图搜图

适用于 `Image2Image`。

该流程与文本检索不同，查询图像不会直接以本地路径传给后端检索接口，而是分两步。

1. 用户在搜索页切换到“以图搜图”
2. 用户选择查询图片
3. 前端先调用 `POST /api/v1/uploads/query-image`
4. 后端返回 `object_key` 与 `preview_url`
5. 前端把这个 `object_key` 存入查询图片列表
6. 用户点击搜索
7. 前端调用 `POST /api/v1/search`，在 `input.image_object_keys` 中传入这个 `object_key`
8. 后端返回检索结果
9. 前端渲染结果列表

这一点非常关键。当前前端不会在图搜图检索时直接把查询图片本机路径传给后端，而是先上传查询图片，再用对象标识进行搜索。

## 5.4 创建向量化任务

1. 用户进入资源准备页
2. 选择任务模式与检索库类型
3. 输入库名称与备注
4. 输入资源路径或库标识
5. 配置模型版本、批量大小、强制重建等参数
6. 点击“提交向量化任务”
7. 前端调用 `POST /api/v1/vectorize`
8. 如果返回成功，则刷新任务列表
9. 如果同名库冲突且后端返回 409，则前端弹出是否合库确认
10. 若用户确认，则带 `merge_on_name_conflict=true` 重试提交

## 5.5 删除检索库

1. 用户进入资源管理页
2. 查看已有检索库列表
3. 点击删除操作
4. 前端弹出确认
5. 前端调用 `DELETE /api/v1/stores/{store_id}`
6. 后端删除索引文件、映射关系与数据库记录
7. 前端根据返回的 `status=deleted` 与 `message` 进行提示并刷新列表

---

## 6. 前端当前页面状态模型

## 6.1 检索页状态

当前检索页核心状态包括。

- `mode`，任务模式
- `storeType`，检索库类型
- `selectedStoreId`，具体检索库 ID
- `queryText`，文本查询
- `uploadedItems`，图搜图时已上传的查询图片列表
- `queryImageUploading`，查询图片上传中状态
- `searchState`，搜索状态
- `results`，结果列表
- `resultCount`，结果数
- `detailModalVisible`，结果详情弹窗开关

建议从后端角度理解，这表示前端会始终维护“当前查询上下文”。后端返回的数据不仅要能用于一次性渲染，还要能支持用户继续查看详情、切换上一条下一条、切换网格和 Rank 流视图。

## 6.2 资源准备页状态

- 表单状态
- 当前任务列表
- 当前选中的任务详情
- 提交中状态
- 轮询状态
- 错误提示状态

## 6.3 资源管理页状态

- 当前库列表
- 当前过滤条件
- 删除中状态
- 当前选中的库详情

---

## 7. 前端对后端接口的依赖总览

当前前端依赖以下后端接口。

```text
GET    /api/v1/health
GET    /api/v1/stores
GET    /api/v1/stores/{store_id}
GET    /api/v1/stores/{store_id}/status
DELETE /api/v1/stores/{store_id}

POST   /api/v1/search
POST   /api/v1/vectorize
GET    /api/v1/tasks/{job_id}

POST   /api/v1/uploads/query-image
GET    /api/v1/media/preview?object_key=...
```

这些接口中，最关键的是 `/search`、`/vectorize`、`/tasks/{job_id}`、`/stores*`、`/uploads/query-image`、`/media/preview`。

---

## 8. 传输格式说明

## 8.1 检索请求格式

### 文本检索视频 / 文本检索图像

请求体格式如下。

```json
{
  "scene": "Text2Video",
  "store_type": "Folder",
  "store_id": "store_001",
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

其中：

- `scene` 是业务模式
- `store_type` 是库类型
- `store_id` 是具体库
- `input.text` 是文本查询
- `input.image_object_keys` 在文本场景下为空数组
- `params.auto_prepare` 用于允许后端自动触发准备逻辑

### 以图搜图

请求体格式如下。

```json
{
  "scene": "Image2Image",
  "store_type": "Folder",
  "store_id": "store_001",
  "topk": 10,
  "need_vectorize": false,
  "input": {
    "text": null,
    "image_object_keys": [
      "query/image/20260415/demo_query_001.jpg"
    ]
  },
  "params": {
    "model_alias": "prod",
    "auto_prepare": true,
    "batch_mode": false
  }
}
```

这里的 `image_object_keys` 来源于 `POST /api/v1/uploads/query-image` 的返回值。

## 8.2 查询图片上传格式

前端上传查询图片时使用 `multipart/form-data`。

请求：

```text
POST /api/v1/uploads/query-image
Content-Type: multipart/form-data
```

表单字段：

- `file`，单个图片文件

理想返回格式如下。

```json
{
  "object_key": "query/image/20260415/demo_query_001.jpg",
  "preview_url": "/api/v1/media/preview?object_key=query%2Fimage%2F20260415%2Fdemo_query_001.jpg"
}
```

当前前端会把返回值映射成内部查询图片项：

```ts
{
  objectKey: string,
  previewUrl: string,
  name?: string
}
```

## 8.3 向量化任务提交格式

当前资源准备页向后端提交的格式如下。

```json
{
  "scene": "Text2Video",
  "store_type": "Folder",
  "keys": [
    "F:\\Code\\RetrievalSys\\backend\\test_data\\VideoRetrieval"
  ],
  "store_name": "视频库",
  "store_description": "视频样例集",
  "merge_on_name_conflict": null,
  "params": {
    "model_alias": "prod",
    "batch_size": 64,
    "force_rebuild": true
  }
}
```

说明如下。

- `keys` 是资源路径或资源标识数组
- `store_name` 是用户定义的库名称，不再由 `keys` 隐式承担命名作用
- `store_description` 是备注说明
- `merge_on_name_conflict` 支持 `null`、`true`、`false`
- `params.force_rebuild` 表示是否强制重建索引

## 8.4 同名库冲突处理

当后端检测到同名库冲突时，前端按如下逻辑处理。

### 第一次提交

```json
{
  "merge_on_name_conflict": null
}
```

如果后端返回 409，则前端弹窗询问用户是否合库。

### 用户确认合库

前端再次提交：

```json
{
  "merge_on_name_conflict": true
}
```

### 用户拒绝合库

前端不会自动再次提交，而是要求用户修改库名称。

## 8.5 任务状态接口返回格式

当前前端能消费的任务状态格式大致如下。

```json
{
  "job_id": "prep_20260411_0002",
  "state": "success",
  "progress": 100,
  "message": "任务执行完成",
  "error": null,
  "result": {
    "store_id": "store_72d23861",
    "store_name": "视频库",
    "store_description": "视频",
    "scanned_files": 3,
    "new_files": 3,
    "new_vectors": 3,
    "skipped_files": 0,
    "skipped_vectors": 0,
    "file_count": 3,
    "vector_count": 3,
    "failed_batches": 0,
    "processed_batches": 1,
    "total_batches": 1,
    "final_index_id": "index_store_72d23861"
  }
}
```

前端已经不再把 `result` 整体作为 JSON 字符串直接展示，而是拆成以下几个板块。

- 基础信息
- 文件与向量统计
- 批次执行情况
- 失败原因

## 8.6 删除库接口返回格式

后端删除库后，前端期望返回如下结构。

```json
{
  "store_id": "store_001",
  "status": "deleted",
  "message": "检索库已删除, 索引文件与映射关系已清理"
}
```

前端根据 `status=deleted` 判断删除成功，并展示 `message`。

## 8.7 检索结果返回格式

当前前端消费的结果项关键字段如下。

```json
{
  "rank": 1,
  "score": 0.85,
  "media_type": "video",
  "object_key": "E:\\Code\\RetrievalSys\\test_data\\VideoRetrieval\\video80.mp4",
  "preview_url": null,
  "source_label": "Folder"
}
```

前端会把它映射成内部 ViewModel：

```ts
{
  rank: number,
  score: number,
  mediaType: 'image' | 'video',
  objectKey: string,
  thumbnailUrl: string,
  sourceLabel: string
}
```

其中 `thumbnailUrl` 的生成规则如下。

1. 如果后端直接返回了 `preview_url`，优先使用 `preview_url`
2. 如果没有 `preview_url`，则 fallback 到 `/api/v1/media/preview?object_key=...`

---

## 9. 当前前端对返回字段的实际使用方式

## 9.1 搜索结果卡

每个结果卡当前固定展示：

- Rank
- 预览区
- 分数
- 来源
- Object Key 简写
- 查看详情按钮

前端对媒体类型的处理如下。

- `media_type = image` 时，结果卡使用 `<img>`
- `media_type = video` 时，结果卡使用 `<video>` 或视频占位区

当前实现中，视频结果详情弹窗使用真正的视频播放器。结果卡的小尺寸预览是否能显示首帧，还受到后端预览链路和视频编码格式影响。

## 9.2 当前检索库卡片

当前搜索页会展示“当前检索库”信息。主要来自 `GET /api/v1/stores/{store_id}`。

当前前端会展示这些字段。

- `store_name`
- `store_description`
- `store_type`
- `scene`
- `status`
- `file_count`
- `vector_count`

注意，按当前产品要求，搜索页的“当前检索库”卡片不提供删除按钮，删除功能被单独放在“资源管理”页面中。

## 9.3 任务详情弹窗

当前任务详情页重点展示以下统计项。

### 文件统计

- 扫描文件数 `scanned_files`
- 新增文件数 `new_files`
- 跳过文件数 `skipped_files`
- 当前有效文件数 `file_count`

### 向量统计

- 新增向量数 `new_vectors`
- 跳过向量数 `skipped_vectors`
- 当前向量总数 `vector_count`

### 批次统计

- 已处理批次 `processed_batches`
- 总批次数 `total_batches`
- 失败批次数 `failed_batches`

### 其他信息

- 库名称
- 备注
- 最终索引 ID
- 失败原因

---

## 10. 中文化与用户展示映射

为了让非技术用户更易理解，前端当前已经把一部分后端或协议字段做了中文化展示。

### 10.1 scene 展示映射

- `Text2Video` -> `视频检索`
- `Text2Image` -> `图像检索`
- `Image2Image` -> `以图搜图`

### 10.2 store_type 展示映射

- `Folder` -> `文件夹`
- `DataBase` -> `数据库`
- `LongVideo` -> `长视频`

### 10.3 task state 展示映射

- `pending` -> `等待中`
- `running` -> `执行中`
- `success` -> `成功`
- `failed` -> `失败`

前端内部仍然保留原始字段值用于接口交互，但页面上尽量展示中文文本。

---

## 11. 媒体预览链路说明

这是当前联调中最需要后端和算法同学理解的部分。

## 11.1 图片预览

图片预览链路相对简单。

- 以图搜图的查询图片通过 `/uploads/query-image` 上传
- 检索结果图像通常可以直接通过 `preview_url` 或 `/media/preview?object_key=...` 预览
- 浏览器对图片的解码与展示通常没有额外问题

因此，图像检索和以图搜图当前一般都能正常显示。

## 11.2 视频预览

视频预览链路比图片复杂得多。

当前前端已经支持：

- 结果详情弹窗中使用 `<video controls>` 播放视频
- 结果卡中尝试显示视频预览
- 优先消费后端 `preview_url`
- 没有 `preview_url` 时 fallback 到 `/api/v1/media/preview?object_key=...`

但当前实践中已经确认，视频预览是否能正常显示，不只取决于前端。

还取决于：

- 后端 `/media/preview` 是否正确处理 Range 请求
- 返回头是否适合内嵌播放，而不是附件下载
- 视频编码是否浏览器兼容
- 是否提供了更适合结果卡展示的 `poster_url` 或缩略图

目前已排查到，视频预览问题的主要瓶颈在于**视频编码兼容性**，而不是图片或请求路径本身。

因此，对后端和算法同学的建议是：

- 尽量为前端提供浏览器兼容的预览视频
- 优先提供封面图或缩略图，而不要让结果卡直接依赖原始视频流
- 详情弹窗再播放视频本体或预览版视频

## 11.3 当前前端对视频预览的结论

- 当前前端已经把视频结果按视频组件处理，而不是图片组件
- 当前前端已经支持通过 HTTP 预览接口拉取视频，而不是直接使用本机文件路径
- 如果视频仍不能正常显示，优先排查视频编码与后端预览返回头

---

## 12. 当前前端项目结构概览

当前前端大致按如下方式组织。

```text
src/
├── api/
│   ├── client.ts
│   ├── search.ts
│   ├── prepare.ts
│   └── stores.ts
├── components/
│   ├── common/
│   ├── search/
│   │   ├── SearchHeroInput.vue
│   │   ├── ResultCard.vue
│   │   ├── ResultDetailModal.vue
│   │   └── ...
│   ├── prepare/
│   │   ├── VectorizeTaskForm.vue
│   │   ├── TaskTable.vue
│   │   ├── TaskDetailModal.vue
│   │   └── ...
│   └── resource/
├── stores/
│   ├── app.ts
│   ├── search.ts
│   ├── prepare.ts
│   └── resource.ts
├── utils/
│   ├── mapper.ts
│   ├── normalize.ts
│   └── constants.ts
├── views/
│   ├── SearchPage.vue
│   ├── PreparePage.vue
│   └── ResourceManagePage.vue
└── router/
```

从后端或算法同学视角来看，只要知道：

- `api/*` 决定接口调用格式
- `stores/*` 决定页面状态组织
- `components/search/*` 负责搜索结果相关展示
- `components/prepare/*` 负责任务相关展示
- `views/*` 负责把页面拼起来

---

## 13. 当前实现中的关键前端服务能力

从“前端提供了什么服务”这个角度来看，当前前端主要提供以下服务能力。

### 13.1 检索任务编排能力

虽然前端不做业务编排，但前端负责：

- 根据用户当前模式组织正确的 `/search` 请求体
- 在图搜图场景先上传查询图，再发起搜索
- 在库未 ready 时展示 `preparing + job_id` 状态提示
- 在搜索页展示当前检索库信息

### 13.2 任务提交与跟踪能力

前端负责：

- 向后端提交向量化任务
- 处理同名库冲突交互
- 获取任务状态
- 把复杂的任务结果统计转成可读页面

### 13.3 资源管理能力

前端负责：

- 获取已有检索库列表
- 展示库信息与统计字段
- 删除检索库并反馈结果

### 13.4 预览与详情展示能力

前端负责：

- 媒体预览
- 结果详情弹窗
- 前后条切换
- 状态提示
- 中文化展示

---

## 14. 与后端联调时最关键的注意事项

## 14.1 `/search` 不只是返回结果列表

后端返回的 `meta` 对前端很重要，特别是：

- `store_status`
- `job_id`
- `message`
- `latency_ms`

如果库未准备好且开启了自动准备，前端需要依赖这些字段告诉用户：当前处于 preparing 状态，并且提供进入任务页的线索。

## 14.2 `/stores/{store_id}` 的详情字段不能省

当前搜索页“当前检索库”卡片依赖详情接口中的以下字段。

- `store_name`
- `store_description`
- `file_count`
- `vector_count`

如果这些字段缺失，页面的库信息展示会退化。

## 14.3 `/tasks/{job_id}` 的 result 字段现在会被结构化展示

当前前端不再直接原样打印 result JSON，而是会拆解里面的统计字段。后端新增字段越稳定，前端展示就越准确。

## 14.4 删除库接口现在是一个真实业务动作

当前前端已经支持资源管理页删除库，因此删除接口不再只是“可有可无”。

它会影响：

- 资源管理页
- 搜索页当前检索库可选列表
- 资源准备页可复用库逻辑

## 14.5 查询图片上传接口是图搜图的前置条件

如果 `/uploads/query-image` 不可用，则 `Image2Image` 搜索流程无法完成。

---

## 15. 与算法侧联调时最关键的注意事项

## 15.1 前端不直接传本地 query 图路径给算法

图搜图时，前端不会把浏览器本地文件路径直接发给后端，更不会直接发给算法端。前端只会上传图片，后端返回 `object_key` 后再检索。

算法同学不应假设前端会直接提供浏览器本地绝对路径。

## 15.2 视频检索预览问题不等于搜索失败

当前已知的一个常见误区是：

- 搜索接口返回结果了
- 排序分数也出来了
- 但视频预览区黑屏或 0:00

这不一定说明检索失败，更可能是视频预览资产或编码不适合浏览器播放。

算法同学如果看到“结果对但视频预览不正常”，不应直接判断前端逻辑有误。

## 15.3 向量化任务中的统计字段对算法评估很有价值

当前前端已经开始把下面这些指标展示出来：

- 扫描文件数
- 新增向量数
- 跳过向量数
- 当前向量总数

这对算法和后端判断增量向量化是否生效、版本复用是否正常都很重要。

---

## 16. 已知限制与当前实现说明

## 16.1 Windows 本机绝对路径

当前前端支持输入资源路径，也尽量支持通过本地桥接能力获取本机绝对路径。但在纯浏览器环境下，浏览器通常不能直接暴露真实 Windows 绝对路径。

因此：

- 如果运行在普通浏览器中，资源准备页可能仍需要用户手工补充绝对路径
- 如果未来接入 Electron、Tauri 或本地桥接层，则可以进一步优化路径选择体验

## 16.2 视频结果卡预览不稳定

当前已经确认，视频结果卡的小尺寸预览会受以下因素影响：

- 视频编码
- 后端预览流处理
- 是否提供封面图

因此结果卡对视频的展示天然不如图片稳定。

## 16.3 当前前端不会在搜索页直接删除库

这是刻意设计。删除库操作被移动到了资源管理页，避免用户在搜索主流程中误删。

---

## 17. 推荐联调顺序

对于后端或算法同学，如果要理解当前前端行为，建议按下面顺序联调。

1. 先确认 `GET /api/v1/health` 正常
2. 再确认 `GET /api/v1/stores` 与 `GET /api/v1/stores/{store_id}` 返回完整字段
3. 再确认 `POST /api/v1/vectorize` 能接受当前前端提交的字段
4. 再确认 `GET /api/v1/tasks/{job_id}` 返回结构化统计字段
5. 再确认 `POST /api/v1/uploads/query-image` 能正常上传并返回 `object_key`
6. 最后确认 `POST /api/v1/search` 与 `/api/v1/media/preview` 链路

---

## 18. 当前前端实现总结

当前版本前端已经形成了较完整的三块能力。

### 检索能力

- 三种模式的统一搜索入口
- 图搜图上传后搜索
- 当前检索库信息展示
- 结果列表与详情弹窗

### 资源准备能力

- 自定义库名称与备注
- 向量化任务提交
- 同名冲突确认
- 结构化任务详情展示

### 资源管理能力

- 检索库列表
- 统计字段展示
- 删除库操作

从后端和算法同学视角，最重要的理解是：

- 前端现在已经不只是“做个页面”
- 它已经把搜索、准备、管理三条主线串起来了
- 因此前端对后端字段稳定性、返回格式一致性、预览链路可用性有更强依赖

只要后端维持接口稳定、算法端维持编码与预览资产链路可用，当前前端可以较稳定地完成检索与管理工作。
