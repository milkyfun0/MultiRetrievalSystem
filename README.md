# MultiRetrievalSystem 多模态检索系统

## 概述

MultiRetrievalSystem 是一个完整的多模态检索系统，支持文本到视频（Text2Video）、文本到图像（Text2Image）和图像到图像（Image2Image）三种检索模式。系统采用模块化架构，包含前端界面、后端服务和算法服务三大组件，适用于多媒体内容检索、医学影像检索、视频检索等多种场景。
pip install uvicorn fastapi httpx pyyaml transformers bytecode hydra-core omegaconf

### 核心功能
- **文本到视频检索**：输入文本描述，检索相关视频片段
- **文本到图像检索**：输入文本描述，检索相关图像（特别优化医学影像检索）
- **图像到图像检索**：输入查询图像，从库中检索相似图像
- **资源管理**：支持检索库的创建、向量化、删除等全生命周期管理
- **任务管理**：异步向量化任务提交、状态跟踪、任务终止

### 技术栈
- **前端**：Vue 3 + TypeScript + Vite + Pinia + Element Plus
- **后端**：FastAPI + SQLite + FAISS（模拟）
- **算法服务**：
  - ImageRetrieval：Vision Transformer + 知识蒸馏
  - MedicalRetrieval：CLIP医学变体 + 临床BERT
  - VideoRetrieval：VidCLIP模型 + 时空注意力
- **部署**：Docker（可选）、一键启动脚本

## 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- FFmpeg（视频处理，已包含在backend/ffmpeg目录）
- 硬件：推荐GPU（算法服务可运行在CPU但较慢）

### 一键启动
项目提供了完整的启动脚本：

```bash
# 启动所有服务（三个终端分别执行）
./run.sh
```

或手动启动各组件：

```bash
# 1. 启动算法服务（网关+三个算法服务）
cd ./algorithm
python launcher/run_all.py

# 2. 启动后端服务
cd ./backend
uvicorn app.main:app --reload

# 3. 启动前端服务
cd ./frontend
npm install  # 首次运行需要
npm run dev
```

### 最小化验证
1. 访问前端：http://localhost:5173
2. 检查后端健康：`curl http://127.0.0.1:8000/api/v1/health`
3. 检查算法网关健康：`curl http://127.0.0.1:18080/health`

## 系统架构

### 整体架构图
```
用户请求 → 前端(Vue) → 后端(FastAPI) → 算法网关 → 算法服务
                ↑           ↑              ↑
             展示结果    管理元数据     路由请求
                │           │              │
              SQLite     FAISS索引     I2I/T2I/T2V服务
```

### 组件说明
1. **前端**：提供用户界面，支持三种检索模式、资源准备、库管理
2. **后端**：处理业务逻辑，管理元数据（SQLite），维护向量索引（FAISS）
3. **算法网关**：统一入口，根据scene参数路由到对应算法服务
4. **算法服务**：三个独立服务，分别处理不同模态的编码和检索

### 数据流
1. **检索流程**：用户输入 → 前端收集 → 后端API → 算法编码 → FAISS搜索 → 返回结果 → 前端展示
2. **向量化流程**：用户提交任务 → 后端创建作业 → 扫描文件 → 算法编码 → 构建索引 → 更新状态
3. **资源管理**：创建库 → 配置参数 → 启动向量化 → 监控进度 → 检索使用

## 算法模块详解

### 1. ImageRetrieval（图像到图像检索）

#### 目的
基于内容的图像检索（CBIR），输入查询图像，从数据库中检索视觉相似的图像。主要用于遥感图像、自然图像等场景。

#### 关键技术
- **模型架构**：Vision Transformer（ViT）、CNN基础模型、知识蒸馏架构
- **训练技术**：对比学习、三元组损失、知识蒸馏（教师-学生）
- **数据增强**：PatchMask增强、随机裁剪、颜色抖动
- **哈希编码**：支持128/256位哈希编码，提升检索效率

#### 使用方法
```bash
# 启动I2I服务（通过启动器自动启动）
cd ./algorithm
python launcher/run_all.py

# 单独启动I2I服务
cd ./algorithm/ImageRetrieval
uvicorn serve_i2i:app --host 0.0.0.0 --port 18081
```

#### API接口
- **编码请求**：`POST /encode`
  ```json
  {
    "scene": "i2i",
    "query": ["/path/to/query/image.jpg"],
    "key": ["/path/to/key/image1.jpg", "/path/to/key/image2.jpg"],
    "params": {"model_alias": "prod"}
  }
  ```
- **健康检查**：`GET /health`

#### 模型配置
- 检查点路径：`analyze_valid/base_distill_patchmask/augment_base_distill_float32_NWEP_RESISC45_256_2024-09-21-13-44-39/base_distill_NWEP_RESISC45_256_0.9648.pt`
- 支持模型：base_cnn, base_vit, base_vit_plus, base_distill, base_distill2
- 性能指标：NWEP_RESISC45 0.965, AID 0.9727, UCMD 0.9856

### 2. MedicalRetrieval（文本到医学图像检索）

#### 目的
医学文本到医学图像的跨模态检索，输入医学文本描述（如临床报告），检索相关的医学影像（X光、CT等）。专门针对医学领域优化。

#### 关键技术
- **模型架构**：CLIP模型变体（clip_swin_clinical, clip_resnet_clinical）
- **文本编码**：临床BERT tokenizer，医学领域词表
- **图像预处理**：CLAHE增强、医学图像标准化
- **训练数据**：MIMIC-CXR、CheXpert、ChestXray14等医学数据集

#### 使用方法
```bash
# 启动T2I服务（通过启动器自动启动）
cd ./algorithm
python launcher/run_all.py

# 单独启动T2I服务
cd ./algorithm/MedicalRetrieval
uvicorn serve_t2i:app --host 0.0.0.0 --port 18082
```

#### API接口
- **编码请求**：`POST /encode`
  ```json
  {
    "scene": "t2i",
    "query": ["肺结节疑似恶性肿瘤", "心脏扩大伴肺水肿"],
    "key": ["/path/to/medical/image1.png"],
    "params": {"model_alias": "clinical"}
  }
  ```
- **健康检查**：`GET /health`

#### 模型配置
- 检查点路径：`Ksample4Ratio0.32025-01-29/21-09-16/checkpoints/model-best.tar`
- 数据集支持：MIMIC-CXR、VinDr-CXR、RSNA Pneumonia等
- 评估指标：BERTScore、医学特异性指标

### 3. VideoRetrieval（文本到视频检索）

#### 目的
文本到视频的跨模态检索，输入文本描述，检索相关的视频片段。支持长视频的切片和抽帧处理。

#### 关键技术
- **模型架构**：VidCLIP模型（基于CLIP的视频扩展）、ViP（Video Proxy）架构
- **视频处理**：帧采样策略、时空注意力机制
- **文本增强**：文本代理（Text Proxy）、掩码语言建模
- **数据集**：视频检索基准数据集

#### 使用方法
```bash
# 启动T2V服务（通过启动器自动启动）
cd ./algorithm
python launcher/run_all.py

# 单独启动T2V服务
cd ./algorithm/VideoRetrieval
uvicorn serve_t2v:app --host 0.0.0.0 --port 18083
```

#### API接口
- **编码请求**：`POST /encode`
  ```json
  {
    "scene": "t2v",
    "query": ["一个人在公园跑步", "城市夜景车流"],
    "key": ["/path/to/video1.mp4"],
    "params": {"model_alias": "video"}
  }
  ```
- **健康检查**：`GET /health`

#### 模型配置
- 检查点路径：`ckpts/model_step_10547.pt`
- 视频处理：支持长视频切片、关键帧提取
- 特征维度：视频特征和文本特征对齐

### 算法网关
- **端口**：18080
- **功能**：统一入口，根据scene参数路由到对应算法服务
- **健康检查**：聚合各算法服务状态
- **错误处理**：统一异常处理和日志记录

## 后端服务

### API接口详细说明

#### 检索接口
- `POST /api/v1/search` - 执行检索
  ```json
  {
    "scene": "t2v",
    "store_id": "store_123",
    "query": {
      "text": ["一个人在公园跑步"]
    },
    "params": {
      "topk": 10,
      "threshold": 0.5
    }
  }
  ```

#### 向量化接口
- `POST /api/v1/vectorize` - 创建向量化任务
  ```json
  {
    "scene": "i2i",
    "store_id": "store_456",
    "source_path": "/path/to/images",
    "model_alias": "prod",
    "force_rebuild": false
  }
  ```

#### 任务管理
- `GET /api/v1/tasks/{job_id}` - 获取任务状态
- `POST /api/v1/tasks/{job_id}/terminate` - 终止任务

#### 资源管理
- `GET /api/v1/stores` - 获取检索库列表
- `GET /api/v1/stores/{store_id}` - 获取检索库详情
- `DELETE /api/v1/stores/{store_id}` - 删除检索库（同时删除元数据、索引和托管资源）

#### 文件上传
- `POST /api/v1/uploads/query-image` - 上传查询图片（Image2Image用）
- `GET /api/v1/media/preview` - 获取媒体预览

#### 健康检查
- `GET /api/v1/health` - 系统健康状态

### 数据库设计
使用SQLite存储元数据，主要表结构：

#### stores表
```sql
CREATE TABLE stores (
    id TEXT PRIMARY KEY,
    scene TEXT NOT NULL,  -- i2i/t2i/t2v
    display_name TEXT,
    model_alias TEXT,
    file_count INTEGER,
    vector_count INTEGER,
    status TEXT,  -- pending/encoding/indexing/ready/error
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### objects表
```sql
CREATE TABLE objects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT NOT NULL,
    source_path_original TEXT,
    managed_relpath TEXT,
    managed_object_key TEXT,
    content_hash TEXT,
    file_size INTEGER,
    filename TEXT,
    storage_backend TEXT,
    last_seen_at TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);
```

#### vectors表
```sql
CREATE TABLE vectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT NOT NULL,
    object_id INTEGER NOT NULL,
    embedding_json TEXT,  -- 向量副本
    created_at TIMESTAMP
);
```

#### jobs表
```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL,
    status TEXT,  -- pending/running/success/failed/terminated
    progress REAL DEFAULT 0.0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 向量索引
- **索引类型**：FAISS（Facebook AI Similarity Search）
- **索引文件**：存储在`data/faiss/{store_id}.index`
- **重建策略**：支持增量更新和全量重建
- **检索优化**：支持top-k检索和相似度阈值过滤

### 配置说明
后端配置文件：`backend/app/core/config.py`

```python
# 关键配置项
algorithm_mode = "deterministic"  # 或 "http"（连接真实算法服务）
algorithm_gateway_url = "http://127.0.0.1:18080"
sqlite_path = "data/sqlite/app.db"
faiss_dir = "data/faiss"
default_topk = 10
max_topk = 100
auto_prepare_default = True  # 检索时自动触发向量化
```

环境变量前缀：`MMR_`，如`MMR_ALGORITHM_MODE=http`

## 前端界面

### 功能页面

#### 1. 检索页 (`/search`)
- **检索模式选择**：Text2Video、Text2Image、Image2Image
- **查询输入**：
  - 文本输入框（Text2Video/Text2Image）
  - 图片拖拽上传（Image2Image）
- **库选择**：下拉选择已就绪的检索库
- **参数配置**：topK、相似度阈值
- **结果展示**：网格视图、Rank流视图、结果详情弹窗

#### 2. 资源准备页 (`/prepare`)
- **任务提交**：选择场景、输入源路径、配置参数
- **任务列表**：查看所有向量化任务状态
- **进度监控**：实时进度条、日志查看
- **任务管理**：终止任务、重试失败任务

#### 3. 资源管理页 (`/manage`)
- **库列表**：查看所有检索库状态
- **库详情**：文件数量、向量数量、创建时间
- **库操作**：删除检索库、触发重建

### 使用指南

#### 首次使用步骤
1. **启动服务**：按照"快速开始"启动所有组件
2. **创建检索库**：
   - 进入"资源准备"页面
   - 选择场景（如i2i）
   - 输入源文件路径（本地目录）
   - 提交向量化任务
3. **等待任务完成**：监控任务进度，直到状态为"成功"
4. **执行检索**：
   - 进入"检索"页面
   - 选择对应的检索库
   - 输入查询内容
   - 点击"搜索"

#### Image2Image特殊说明
当前协议使用`input.image_object_keys`，因此前端保留了本地拖拽预览区，但真正提交给后端的是图片Object Key列表。用户需要先将图片上传到后端托管存储。

### 配置说明

#### 环境变量
创建`.env.local`文件：
```bash
VITE_BACKEND_PROXY_TARGET=http://127.0.0.1:8000
VITE_API_BASE_URL=/api/v1
```

#### 开发代理
默认开发服务器配置（`vite.config.ts`）：
```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true
    }
  }
}
```

#### 构建部署
```bash
# 开发模式
npm run dev

# 生产构建
npm run build

# 预览构建结果
npm run preview
```

## 部署与运维

### 生产环境部署

#### 1. 环境准备
```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install -y python3-pip nodejs npm ffmpeg

# 创建项目目录
mkdir -p /opt/multiretriever
cd /opt/multiretriever
```

#### 2. 服务配置
```bash
# 后端服务（systemd）
sudo vi /etc/systemd/system/multiretriever-backend.service

# 算法服务（systemd）
sudo vi /etc/systemd/system/multiretriever-algorithm.service

# 前端服务（nginx）
sudo vi /etc/nginx/sites-available/multiretriever
```

#### 3. 反向代理配置（Nginx）
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 前端静态文件
    location / {
        root /opt/multiretriever/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # 后端API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # 算法网关代理（可选）
    location /algorithm/ {
        proxy_pass http://127.0.0.1:18080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 服务监控

#### 健康检查端点
- 前端：`http://localhost:5173`（运行状态）
- 后端：`http://localhost:8000/api/v1/health`
- 算法网关：`http://localhost:18080/health`

#### 日志查看
```bash
# 后端日志
tail -f backend/logs/app.log

# 算法服务日志
tail -f algorithm/logs/*.log

# 系统服务日志
sudo journalctl -u multiretriever-backend -f
```

#### 性能监控
- **磁盘空间**：监控`data/`目录增长
- **内存使用**：算法服务加载模型后内存占用
- **响应时间**：API端点响应时间监控

### 数据备份与恢复

#### 关键数据目录
```
data/
├── sqlite/          # 数据库文件
├── faiss/           # 向量索引
├── assets/          # 托管资源
└── query_uploads/   # 查询上传文件
```

#### 备份策略
```bash
# 定期备份
tar -czf backup_$(date +%Y%m%d).tar.gz data/
# 恢复备份
tar -xzf backup_20240101.tar.gz -C ./
```

### 性能调优

#### 算法服务优化
1. **GPU加速**：配置CUDA环境，使用GPU运行模型
2. **批处理大小**：调整编码时的批处理大小
3. **模型量化**：使用FP16或INT8量化减小模型大小

#### 后端优化
1. **连接池**：调整数据库连接池大小
2. **缓存策略**：实现查询结果缓存
3. **索引优化**：定期重建FAISS索引

#### 前端优化
1. **代码分割**：路由级懒加载
2. **图片懒加载**：结果图片延迟加载
3. **请求合并**：批量请求优化

## 开发指南

### 项目结构
```
MultiRetrievalSystem/
├── algorithm/           # 算法服务
│   ├── ImageRetrieval/     # 图像检索
│   ├── MedicalRetrieval/   # 医学检索
│   ├── VideoRetrieval/     # 视频检索
│   ├── gateway/            # 统一网关
│   ├── launcher/           # 服务启动器
│   └── common/             # 共享工具
├── backend/             # 后端服务
│   ├── app/                # FastAPI应用
│   │   ├── api/            # 路由端点
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务服务
│   │   └── utils/          # 工具函数
│   ├── data/               # 数据目录
│   └── tests/              # 测试文件
├── frontend/            # 前端应用
│   ├── public/             # 静态资源
│   ├── src/                # 源代码
│   │   ├── api/            # API客户端
│   │   ├── components/     # 组件
│   │   ├── pages/          # 页面
│   │   ├── router/         # 路由
│   │   ├── stores/         # 状态管理
│   │   └── utils/          # 工具函数
│   ├── index.html          # 入口HTML
│   └── vite.config.ts      # Vite配置
├── README/              # 文档目录
└── run.sh               # 启动脚本
```

### 代码贡献流程

1. **环境搭建**
   ```bash
   git clone <repository-url>
   cd MultiRetrievalSystem
   
   # 后端依赖
   cd backend
   pip install -r requirements.txt
   
   # 前端依赖
   cd ../frontend
   npm install
   ```

2. **开发测试**
   ```bash
   # 运行测试
   cd backend && pytest -v
   cd ../algorithm && python -m pytest tests/
   
   # 代码检查
   flake8 backend/app
   eslint frontend/src
   ```

3. **提交规范**
   - 功能分支：`feat/description`
   - 修复分支：`fix/issue-description`
   - 提交信息：遵循Conventional Commits

### 测试运行

#### 后端测试
```bash
cd backend
pytest tests/ -v
# 测试覆盖率
pytest tests/ --cov=app --cov-report=html
```

#### 算法测试
```bash
cd algorithm
python -m pytest tests/
# 网关健康检查测试
python tests/test_gateway.py
```

#### 集成测试
```bash
# 启动所有服务
./run.sh
# 运行集成测试脚本
python algorithm/tests/test_integration.py
```

### 常见开发任务

#### 添加新的算法场景
1. 在`algorithm/`下创建新目录（如`AudioRetrieval`）
2. 实现编码服务（参考现有服务结构）
3. 在网关`WORKERS`字典中添加路由配置
4. 更新后端`scene`枚举和模型配置
5. 前端添加对应的检索模式界面

#### 修改API接口
1. 更新后端`app/api/`中的对应端点
2. 更新前端API客户端`src/api/client.ts`
3. 更新TypeScript类型定义
4. 运行测试确保兼容性

#### 更新模型检查点
1. 将新模型文件放入对应目录
2. 更新`algorithm/launcher/run_all.py`中的检查点路径
3. 测试编码服务是否正常加载
4. 更新性能指标文档

## 常见问题

### 安装问题

#### Q1: 启动算法服务时提示"ModuleNotFoundError"
**A**: 确保设置了正确的PYTHONPATH：
```bash
cd algorithm
export PYTHONPATH=$(pwd):$PYTHONPATH
python launcher/run_all.py
```

#### Q2: 前端启动时端口冲突
**A**: 修改Vite配置或使用其他端口：
```bash
cd frontend
npm run dev -- --port 5174
```

#### Q3: 后端连接算法服务超时
**A**: 检查算法服务是否正常启动：
1. 确认算法网关运行在18080端口
2. 检查`backend/app/core/config.py`中的`algorithm_gateway_url`
3. 验证网络连接：`curl http://127.0.0.1:18080/health`

### 运行问题

#### Q1: 向量化任务卡在"pending"状态
**A**:
1. 检查后端日志：`tail -f backend/logs/app.log`
2. 确认本地作业运行器配置：`local_job_workers`参数
3. 检查源文件路径是否可访问

#### Q2: 检索结果不准确
**A**:
1. 确认检索库状态为"ready"
2. 检查向量数量与文件数量是否匹配
3. 验证算法服务是否正确加载模型
4. 调整检索参数（topk、threshold）

#### Q3: 内存使用过高
**A**:
1. 算法服务：减小批处理大小，使用CPU模式
2. 后端服务：调整连接池大小，增加内存限制
3. 考虑分布式部署，分离算法服务

### 性能问题

#### Q1: 检索速度慢
**A**:
1. 优化FAISS索引类型（使用IVFx索引）
2. 启用GPU加速（如果可用）
3. 实现结果缓存机制
4. 减少返回的topk数量

#### Q2: 向量化任务耗时过长
**A**:
1. 增加`local_job_workers`参数
2. 使用GPU运行算法服务
3. 优化文件扫描逻辑（增量更新）
4. 分批处理大型文件集

#### Q3: 前端加载缓慢
**A**:
1. 启用Gzip压缩
2. 配置CDN加速静态资源
3. 实现图片懒加载
4. 优化包大小（代码分割）

### 故障排除

#### 日志查看
```bash
# 后端日志
cat backend/logs/app.log | grep ERROR

# 算法服务日志
cat algorithm/logs/*.log | grep -i error

# 系统日志（Linux）
sudo dmesg | tail -50
```

#### 服务状态检查
```bash
# 检查所有服务端口
netstat -tulpn | grep -E '8000|18080|18081|18082|18083|5173'

# 检查进程状态
ps aux | grep -E 'uvicorn|node|python' | grep -v grep
```

#### 数据库维护
```bash
# 检查SQLite数据库
sqlite3 backend/data/sqlite/app.db "SELECT count(*) FROM stores;"

# 备份数据库
cp backend/data/sqlite/app.db app.db.backup.$(date +%Y%m%d)

# 修复数据库（如果需要）
sqlite3 backend/data/sqlite/app.db ".recover" | sqlite3 app.db.fixed
```

## 版本历史

### v5.0 - 资源管理后端
- 资源管理升级：本机扫描 + 后端内部托管
- 对象元数据增强：source_path_original, managed_relpath等
- 向量元数据增强：保存向量副本，支持索引重建
- 增量模式优化：对象失活与索引重建
- 删除库时完整清理：SQLite元数据、索引文件、托管资源

### v4.0 - 多模态检索系统
- 完整的三模态支持：Text2Video, Text2Image, Image2Image
- 算法服务统一网关架构
- 前端Vue 3 + TypeScript重构
- 后端FastAPI + SQLite + FAISS完整实现
- 任务管理和资源管理全流程

### v3.0 - 算法服务框架
- 独立的算法服务：I2I, T2I, T2V
- 统一编码接口规范
- 模型检查点管理和配置
- 服务健康检查和监控

### v2.0 - 后端脚手架
- FastAPI后端基础框架
- SQLite元数据存储
- 模拟FAISS向量服务
- 基本API端点实现

### v1.0 - 前端骨架
- Vue 3 + TypeScript前端框架
- 基本页面结构：检索页、准备页、管理页
- Element Plus组件集成
- API客户端和状态管理

## 许可证

本项目采用 MIT 许可证 - 查看 LICENSE 文件了解详情。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 项目仓库：[GitHub Repository]
- 问题反馈：[Issues]
- 文档更新：[Pull Requests]

---

**感谢使用 MultiRetrievalSystem！** 我们持续改进系统，欢迎贡献代码和反馈意见。
