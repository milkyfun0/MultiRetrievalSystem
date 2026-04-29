# 进度条卡住修复说明

本次修改基于 `mmr_backend_scaffold_v6_http`，只针对“资源准备任务进度条不动，但检索库已显示就绪”的问题做最小改动。

## 修复点

### 1. 更细粒度的任务进度更新
修改文件：
- `app/services/prepare_service.py`

新增 `_update_job_progress()` 辅助方法，并将资源准备进度拆成以下阶段：
- 扫描资源：约 1% → 8%
- 托管资源：约 12% → 30%
- 批量编码：约 30% → 95%
- 重建索引与收尾：97%
- 完成：100%

这样即使任务很快完成或中途前端轮询较慢，也更容易看到进度变化。

### 2. 任务状态与库状态自动对齐
修改文件：
- `app/api/v1/tasks.py`

新增 `_reconcile_job_if_stale()`：
- 当任务仍是 `pending/running`，但对应 `store.status` 已经是 `ready` 时，自动将任务修正为：
  - `state = success`
  - `progress = 100`
  - `can_terminate = false`
- 同时补齐 `result` 中的统计字段，例如 `file_count`、`vector_count`、`final_index_id`

这可以修复“库已经 ready，但任务列表还停在 running，进度条不动”的前后端不一致问题。

## 本次未改动

- 未改动搜索主链路
- 未改动前端接口协议
- 未改动算法调用协议
- 未改动已有 store / vectorize / search 的请求体结构

## 测试结果

```text
12 passed
```
