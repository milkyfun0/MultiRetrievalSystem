# v6 补丁说明

本版本基于 v5 代码进行最小化改造，新增以下能力：

1. 任务管理支持终止执行中任务
2. 资源准备支持 `LongVideo`
   - `Text2Video + LongVideo` 走均匀切片
   - `Text2Image + LongVideo` 走均匀抽帧
   - `Image2Image + LongVideo` 走均匀抽帧
3. 检索结果支持返回长视频衍生对象的附加元数据
4. `stores` 与 `jobs` 元数据结构增加 LongVideo/终止任务相关字段

## 新增接口

- `POST /api/v1/tasks/{job_id}/terminate`

## 兼容性

- 既有 `/search`、`/vectorize`、`/tasks/{job_id}`、`/stores*` 路径保持不变
- 旧的 `Folder` 和 `DataBase` 资源准备逻辑保持兼容
- `Object Key` 展示优化不需要后端改接口

## 运行依赖

LongVideo 预处理依赖：

- `ffmpeg`
- `ffprobe`

默认从系统 PATH 中查找，也可通过环境变量覆盖：

- `MMR_FFMPEG_BIN`
- `MMR_FFPROBE_BIN`
