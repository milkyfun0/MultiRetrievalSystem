# 多模态检索前端增量改动说明（面向后端联调）

## 1. 文档目的

本文档说明当前前端在 **保持上一版可运行代码主结构不变** 的前提下，为适配《多模态检索系统补充需求文档》和《前端对接改动说明 v6》所做的**增量接入**。本文档面向后端同学，帮助后端明确：

- 前端新增调用了哪些接口
- 前端新增消费了哪些字段
- 哪些既有接口与主结构保持不变
- 页面逻辑如何根据后端返回值变化
- LongVideo 场景下，前端如何构造请求与展示结果

本次前端修改原则是 **最小侵入式增强**。上一版已可运行的页面结构与主链路不重做，只在原有页面和状态管理基础上扩展新能力。

---

## 2. 这次哪些主链路保持不变

以下主链路保持不变，前端没有推翻旧逻辑：

### 2.1 检索页主链路不变

仍使用：

- `POST /api/v1/search`
- `GET /api/v1/stores`
- `GET /api/v1/stores/{store_id}`
- `POST /api/v1/uploads/query-image`
- 检索结果仍以 `results + meta` 结构消费

### 2.2 资源准备页主链路不变

仍使用：

- `POST /api/v1/vectorize`
- `GET /api/v1/tasks/{job_id}`

### 2.3 资源管理页主链路不变

仍使用：

- `GET /api/v1/stores`
- `GET /api/v1/stores/{store_id}`
- `DELETE /api/v1/stores/{store_id}`

### 2.4 媒体预览主链路不变

前端仍遵循：

- 优先使用后端直接返回的 `preview_url`
- 若结果项没有 `preview_url`，再 fallback 到 `/api/v1/media/preview?object_key=...`

因此，旧有 `Folder / DataBase` 检索场景理论上不应因本次改动被破坏。

---

## 3. 本次前端新增能力概览

本次前端新增能力主要集中在三块：

1. **任务终止**
2. **LongVideo 资源准备动态表单与结果展示**
3. **Object Key 展示优化与详情增强**

此外，本次修改继续保留此前已经接入的：

- 自定义 `store_name`
- `store_description`
- 同名库合库确认
- 查询图片上传后再检索
- 资源管理页删除已有检索库

---

## 4. 新增页面与主组件改动范围

本次仍保留原有三个一级页面：

- `/search` 检索
- `/prepare` 资源准备
- `/stores` 资源管理

### 4.1 本次主要修改文件

以下文件做了增量修改：

- `src/api/prepare.ts`
- `src/stores/prepare.ts`
- `src/components/prepare/VectorizeTaskForm.vue`
- `src/components/prepare/TaskTable.vue`
- `src/components/prepare/TaskDetailModal.vue`
- `src/views/PreparePage.vue`
- `src/types/prepare.ts`
- `src/types/store.ts`
- `src/types/search.ts`
- `src/stores/search.ts`
- `src/views/SearchPage.vue`
- `src/views/StoreManagePage.vue`
- `src/utils/display.ts`

本次没有重构 router、layout、搜索页主骨架，也没有替换原有全局状态结构。

---

## 5. 任务终止能力，前端如何接入

## 5.1 新增接口调用

前端新增调用：

```http
POST /api/v1/tasks/{job_id}/terminate
```

请求体：

```json
{
  "reason": "用户手动终止"
}
```

### 5.2 终止按钮出现条件

前端仅在以下条件下显示“终止任务”按钮：

- `task.status === "running"`
- `task.canTerminate === true`

也就是说，前端不会只凭 `status=running` 就展示按钮，而是以后端返回的 `can_terminate` 为最终准入条件。

### 5.3 前端终止交互逻辑

资源准备页中：

1. 用户点击“终止任务”
2. 前端弹出确认框
3. 用户确认后调用 `/api/v1/tasks/{job_id}/terminate`
4. 成功后：
   - 当前任务状态更新为 `terminated`
   - 当前轮询停止
   - 立即刷新一次该任务详情

### 5.4 前端使用的新增任务字段

`GET /api/v1/tasks/{job_id}` 新增字段，前端已开始消费：

- `phase`
- `can_terminate`
- `terminated_at`
- `terminate_reason`

### 5.5 前端展示规则

- `state` 决定主状态标签
- `phase` 决定阶段中文文案
- `can_terminate` 决定是否显示终止按钮
- `terminated_at` 与 `terminate_reason` 会在任务详情中展示

### 5.6 任务状态前端枚举

当前前端任务状态已扩展为：

- `pending`
- `running`
- `success`
- `failed`
- `terminated`

前端已停止假设“任务结束状态只有 success / failed”。

---

## 6. 资源准备页对 LongVideo 的增量支持

## 6.1 设计原则

LongVideo 的支持没有改变资源准备页的主提交接口，仍然是：

```http
POST /api/v1/vectorize
```

只是当前端选择：

- `store_type = LongVideo`

时，会动态增加 LongVideo 专有参数，并根据 scene 自动推导处理模式。

## 6.2 前端 LongVideo 推导规则

### 6.2.1 Text2Video + LongVideo

前端自动采用：

```json
"preprocess_mode": "segment"
```

并展示“切片间隔（秒）”。

默认值：

- `interval_sec = 5`

可选值：

- `1 / 3 / 5 / 10 / 30 / 60`

### 6.2.2 Text2Image + LongVideo

前端自动采用：

```json
"preprocess_mode": "frame"
```

并展示“抽帧间隔（秒）”。

默认值：

- `interval_sec = 3`

可选值：

- `1 / 3 / 5 / 10 / 30`

### 6.2.3 Image2Image + LongVideo

与 `Text2Image + LongVideo` 完全一致：

```json
"preprocess_mode": "frame"
```

### 6.3 LongVideo 请求体格式

当前前端提交 `/api/v1/vectorize` 时，LongVideo 请求体如下：

#### Text2Video + LongVideo

```json
{
  "scene": "Text2Video",
  "store_type": "LongVideo",
  "store_name": "会议长视频库",
  "store_description": "按 5 秒切片生成的视频检索库",
  "merge_on_name_conflict": null,
  "keys": ["F:\\videos\\meeting.mp4"],
  "params": {
    "model_alias": "prod",
    "batch_size": 16,
    "force_rebuild": true,
    "preprocess_mode": "segment",
    "interval_sec": 5
  }
}
```

#### Text2Image / Image2Image + LongVideo

```json
{
  "scene": "Text2Image",
  "store_type": "LongVideo",
  "store_name": "会议抽帧图库",
  "store_description": "按 3 秒抽帧生成",
  "merge_on_name_conflict": null,
  "keys": ["F:\\videos\\meeting.mp4"],
  "params": {
    "model_alias": "prod",
    "batch_size": 32,
    "force_rebuild": true,
    "preprocess_mode": "frame",
    "interval_sec": 3
  }
}
```

### 6.4 表单侧后端要求

当 `store_type = LongVideo` 时，前端默认认为后端可以接受：

- `params.preprocess_mode`
- `params.interval_sec`

若后端不支持，应返回显式错误信息，而不是静默忽略。

---

## 7. 任务详情页新增了哪些展示

资源准备页的任务详情弹窗已不再展示整串 JSON，而是改成结构化卡片。

### 7.1 任务详情当前消费的字段

基础字段：

- `job_id`
- `state`
- `progress`
- `message`
- `error`
- `phase`
- `terminated_at`
- `terminate_reason`

`result` 中的统计字段：

- `store_id`
- `store_name`
- `store_description`
- `scanned_files`
- `file_count`
- `new_files`
- `new_vectors`
- `skipped_files`
- `skipped_vectors`
- `processed_batches`
- `total_batches`
- `failed_batches`
- `vector_count`
- `final_index_id`
- `generated_segments`
- `generated_frames`

### 7.2 LongVideo 任务统计展示

当前前端已经对以下字段做了单独展示：

- `generated_segments`
- `generated_frames`

因此后端如果在 LongVideo 任务中返回这些字段，前端会直接显示“LongVideo 预处理统计”模块。

---

## 8. 检索页对 LongVideo 结果的兼容展示

## 8.1 `/search` 请求主结构未变

前端仍然通过：

```http
POST /api/v1/search
```

发起检索，主结构没有推翻。

### 8.2 结果项新增的可选字段

前端现在支持从结果项中读取以下可选字段：

- `parent_video_name`
- `segment_start_sec`
- `segment_end_sec`
- `frame_timestamp_sec`
- `derive_type`

这些字段不会影响旧有结果渲染；如果字段不存在，前端按旧逻辑展示。

### 8.3 卡片页如何用这些字段

结果卡片不会大幅改版，但会在卡片元信息区尝试显示：

- `时间段 x s - y s`
- 或 `时间戳 x s`

### 8.4 详情弹窗如何用这些字段

检索结果详情弹窗会新增展示：

- 来源长视频名
- 时间段
- 时间戳
- 派生方式（均匀切片 / 均匀抽帧）

因此后端返回这些字段后，前端不需要再额外改弹窗结构。

---

## 9. Object Key 展示规则

## 9.1 后端无需改字段

后端仍返回完整 `object_key` 原值。

前端自己做展示层截断，不要求后端新增短字段。

## 9.2 前端当前处理方式

在结果卡中：

- Object Key 单行显示
- 超长自动省略号截断
- 鼠标悬浮显示完整值

因此后端不应主动截断 `object_key`。

---

## 10. stores 详情接口新增字段消费情况

前端已开始消费以下 `stores` 详情增强字段：

- `file_count`
- `vector_count`
- `preprocess_mode`
- `interval_sec`

### 10.1 搜索页当前检索库卡片

当前检索库卡片现在会显示：

- 当前文件数
- 当前向量数
- 若为 LongVideo 库，还会显示：
  - LongVideo 预处理方式
  - 处理间隔

### 10.2 资源管理页详情弹窗

资源管理页查看详情时，也会展示：

- `file_count`
- `vector_count`
- `preprocess_mode`
- `interval_sec`

因此，后端如果是 LongVideo store，建议在 `GET /api/v1/stores/{store_id}` 中稳定返回这两个字段。

---

## 11. 删除检索库接口，前端如何使用

前端资源管理页删除仍使用：

```http
DELETE /api/v1/stores/{store_id}
```

当前前端行为：

1. 弹出二次确认
2. 删除成功后显示后端返回的 `message`
3. 刷新列表
4. 若当前打开的是被删除库详情，则自动关闭详情弹窗

前端默认后端返回结构：

```json
{
  "store_id": "store_001",
  "status": "deleted",
  "message": "检索库已删除, 索引文件与映射关系已清理"
}
```

---

## 12. 查询图片上传链路未变

图搜图仍然采用：

1. `POST /api/v1/uploads/query-image`
2. 拿到 `object_key` + `preview_url`
3. 再调用 `/api/v1/search`

即：

```json
{
  "scene": "Image2Image",
  "store_type": "Folder",
  "store_id": "store_xxx",
  "topk": 10,
  "input": {
    "text": null,
    "image_object_keys": ["managed/query/xxx.jpg"]
  },
  "params": {
    "model_alias": "prod",
    "auto_prepare": true,
    "batch_mode": false,
    "return_detail_meta": false
  }
}
```

本次修改没有改变这条链路。

---

## 13. 当前前端对后端的联调假设

## 13.1 最重要的兼容性假设

前端假设以下内容继续成立：

- 旧接口路径不改
- 旧主请求体结构不推翻
- 新能力通过新增字段或新增终止接口扩展
- 旧场景数据字段继续可用

## 13.2 前端对任务轮询的停止条件

前端当前将以下状态视为“任务已结束，不继续轮询”：

- `success`
- `failed`
- `terminated`

因此，如果后端新增其他终态，请提前同步前端。

## 13.3 前端对 LongVideo 的假设

前端不会要求算法端理解 LongVideo。前端只负责把 LongVideo 参数传给后端，后续切片或抽帧都应由后端完成。

---

## 14. 后端联调建议顺序

建议后端按下面顺序与前端联调：

1. 先验证 `Folder / DataBase` 旧场景不受影响
2. 再验证 `/api/v1/tasks/{job_id}/terminate`
3. 再验证 LongVideo 的 `/vectorize` 动态参数是否被正确消费
4. 再验证 `/search` 返回的 LongVideo 详情增强字段
5. 最后验证 `stores/{id}` 的 `preprocess_mode / interval_sec / file_count / vector_count`

---

## 15. 结论

本次前端改动遵循“**在上一版可运行代码上做增量修改**”的原则，没有重做整体结构。

对后端而言，最需要明确的是：

- 任务终止接口已经接入
- `terminated` 已被视为正式终态
- LongVideo 动态参数已经接入 `/vectorize`
- 搜索结果详情已兼容 LongVideo 扩展字段
- `stores` 详情增强字段已被前端消费

因此后端只需按 v6 增量接口与字段返回，即可与当前前端版本直接联调。
