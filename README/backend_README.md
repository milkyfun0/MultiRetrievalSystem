# 多模态检索系统后端说明

## 系统定位
后端是FastAPI服务层，负责连接前端和算法端，主要职责：
- 接收前端请求，参数校验
- 管理检索库和任务状态
- 组织建库流程，调用算法服务
- 管理向量索引与元数据
- 返回结构化结果

## 核心接口
```
GET    /api/v1/health           # 健康检查
GET    /api/v1/stores           # 检索库列表
POST   /api/v1/stores           # 创建检索库
GET    /api/v1/stores/{id}      # 检索库详情
DELETE /api/v1/stores/{id}      # 删除检索库
POST   /api/v1/vectorize        # 资源准备
GET    /api/v1/tasks/{id}       # 任务状态
POST   /api/v1/search           # 统一检索
POST   /api/v1/uploads/query-image  # 查询图片上传
GET    /api/v1/media/preview    # 媒体预览
```

## 业务场景映射
| 前端场景 | 算法场景 | 说明 |
|---------|---------|------|
| Text2Video | t2v | 文本检索视频 |
| Text2Image | t2i | 文本检索图像 |
| Image2Image | i2i | 以图搜图 |

## 数据存储
- **SQLite**: 元数据存储 (stores, objects, vectors)
- **本地索引**: FAISS索引文件 (.npy/.json)
- **托管资源**: 文件复制到统一目录管理
- **查询上传**: 临时存储查询图片

## 关键设计
1. **前端接口稳定**: 内部实现可演进，接口保持不变
2. **查询走网络**: 建库不走大文件传输
3. **后端托管资源**: 不依赖原始磁盘路径
4. **算法只做编码**: 不参与业务规则判断

## 快速启动
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 环境变量
```
MMR_ALGORITHM_MODE=deterministic|http
MMR_ALGORITHM_GATEWAY_URL=http://127.0.0.1:18080
MMR_PUBLIC_BASE_URL=http://localhost:8000
```