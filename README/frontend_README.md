# 多模态检索系统前端说明

## 系统定位
基于Vue 3 + Vite + TypeScript的前端界面，负责用户交互与展示，不处理模型推理。

## 核心功能
- **检索**: Text2Video、Text2Image、Image2Image
- **资源准备**: 创建向量化任务，跟踪任务状态
- **资源管理**: 查看/删除检索库

## 页面结构
```
检索页
├── 模式切换 (Text2Video/ Text2Image/ Image2Image)
├── 检索库选择
├── 查询输入 (文本/图片)
└── 结果展示 (网格/Rank流)

资源准备页
├── 任务提交表单
├── 任务列表
└── 任务详情

资源管理页
├── 检索库列表
└── 删除操作
```

## 核心接口
```
GET    /api/v1/health           # 服务状态
GET    /api/v1/stores           # 检索库列表
POST   /api/v1/vectorize        # 创建向量化任务
GET    /api/v1/tasks/{id}       # 任务状态
POST   /api/v1/search           # 统一检索
POST   /api/v1/uploads/query-image  # 图片上传
GET    /api/v1/media/preview    # 媒体预览
```

## 快速启动
```bash
cd frontend
npm install
npm run dev
```

## 环境配置
```bash
# 开发环境
VITE_BACKEND_PROXY_TARGET=http://127.0.0.1:8000

# 生产环境
VITE_API_BASE_URL=http://your-backend-domain.com
```

## 关键流程

### Image2Image流程
1. 用户上传查询图片
2. 前端调用 `/uploads/query-image` 获取 `object_key`
3. 调用 `/search` 传入 `image_object_keys`
4. 展示检索结果

### 资源准备流程
1. 用户填写表单 (库名称、路径等)
2. 前端调用 `/vectorize` 提交任务
3. 轮询 `/tasks/{id}` 获取进度
4. 完成后更新页面状态

## 注意事项
- 前端不直接调用算法端，只与后端交互
- 图搜图必须先上传图片再检索
- 视频预览依赖后端编码兼容性
- 删除库操作在资源管理页，不在检索页