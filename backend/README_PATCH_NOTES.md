# Patch Notes - v5 Resource Managed Backend

## 本次改动重点

本版本在保持前端接口不变的前提下，对后端内部资源管理做了升级。

### 1. 查询仍走网络传输

- `POST /api/v1/uploads/query-image` 不变
- 查询图片上传后由后端保存到 `data/query_uploads`
- `/search` 仍然只接收 `image_object_keys`

### 2. 建库改为“本机扫描 + 后端内部托管”

- `/api/v1/vectorize` 仍然只接收 `keys`
- 后端扫描来源目录后，会把对象复制到 `data/assets/{scene}/{store_id}/...`
- 后续编码、预览、搜索结果都依赖托管资源，而不是外部原始路径

### 3. 对象元数据增强

`objects` 表新增：

- `source_path_original`
- `managed_relpath`
- `managed_object_key`
- `content_hash`
- `file_size`
- `filename`
- `storage_backend`
- `last_seen_at`

### 4. 向量元数据增强

`vectors` 表新增：

- `embedding_json`

作用：

- 保存向量副本
- 支持删除文件、增量更新后重建索引文件，而不必强依赖原始来源再次编码

### 5. force_rebuild 行为更严格

- 清空当前 store 的 objects 与 vectors
- 删除托管资源目录
- 重置索引文件
- 再次全量扫描并建库

这样可保证重建后：

- `file_count == vector_count`

### 6. 增量模式支持对象失活与索引重建

- 本轮未再次扫描到的旧对象会被标记 inactive
- 对应向量记录会被删除
- 最后根据 active 向量重建索引文件

### 7. 删除库时清理更完整

`DELETE /api/v1/stores/{store_id}` 现在会同时删除：

- SQLite 元数据
- 索引文件
- 托管资源目录

## 当前测试结果

```text
10 passed
```
