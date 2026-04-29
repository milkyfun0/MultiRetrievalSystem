# MultiRetrievalSystem Docker 化构建指南

本文档详细说明如何将多模态检索系统（MultiRetrievalSystem）打包为 Docker 容器并部署。

## 项目架构概述

系统包含三个主要组件：
1. **前端** (Vue 3 + Vite) - 用户界面
2. **后端** (FastAPI) - 业务逻辑和 API
3. **算法服务** (三个独立服务 + 网关) - 多模态检索算法

## 文件结构准备

在项目根目录创建以下文件结构：

```
MultiRetrievalSystem/
├── build.md                          # 本文档
├── docker-compose.yml               # Docker Compose 编排文件
├── .env.docker                      # 环境变量配置
├── docker-build-run.sh              # 构建和运行脚本
├── backend/
│   ├── Dockerfile                   # 后端 Dockerfile
│   └── requirements.txt             # (已存在)
├── algorithm/
│   ├── Dockerfile                   # 算法服务 Dockerfile
│   ├── requirements.txt             # 算法服务依赖
│   └── docker-entrypoint.sh         # 启动脚本
├── frontend/
│   ├── Dockerfile                   # 前端 Dockerfile
│   └── nginx.conf                   # Nginx 配置
└── scripts/
    └── docker-build-run.sh          # (可选移动到 scripts/)
```

## 文件内容

### 1. 算法服务依赖文件：`algorithm/requirements.txt`

```txt
# 核心框架
fastapi>=0.111.0
uvicorn>=0.30.0
pydantic>=2.7.0
httpx>=0.27.0
python-multipart>=0.0.6

# 深度学习框架
torch>=2.0.0
torchvision>=0.15.0
transformers>=4.40.0

# 图像处理
Pillow>=10.0.0
opencv-python-headless>=4.8.0

# 视频处理
ffmpeg-python>=0.2.0

# 配置管理
hydra-core>=1.3.0
omegaconf>=2.3.0
pyyaml>=6.0

# 科学计算
numpy>=1.26.0

# 工具库
tqdm>=4.66.0
psutil>=5.9.0

# 测试
pytest>=8.0.0
```

### 2. 后端 Dockerfile：`backend/Dockerfile`

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY . .

# 创建数据目录
RUN mkdir -p data/sqlite data/faiss data/assets data/query_uploads data/preprocess_tmp

# 环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MMR_ALGORITHM_MODE=http
ENV MMR_ALGORITHM_GATEWAY_URL=http://algorithm-gateway:18080

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. 算法服务 Dockerfile：`algorithm/Dockerfile`

```dockerfile
FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制算法代码
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 18080 18081 18082 18083

# 启动脚本
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
```

### 4. 算法服务启动脚本：`algorithm/docker-entrypoint.sh`

```bash
#!/bin/bash
set -e

echo "Starting MultiRetrieval Algorithm Services..."

# 设置Python路径
export PYTHONPATH=/app:$PYTHONPATH

# 启动所有算法服务（使用后台进程）
cd /app
python launcher/run_all.py &

# 保持容器运行
wait
```

### 5. 前端 Dockerfile：`frontend/Dockerfile`

```dockerfile
# 构建阶段
FROM node:18-alpine as build-stage

WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm ci

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产阶段
FROM nginx:alpine as production-stage

# 复制Nginx配置
COPY nginx.conf /etc/nginx/nginx.conf

# 从构建阶段复制构建结果
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 6. 前端 Nginx 配置：`frontend/nginx.conf`

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    sendfile on;
    keepalive_timeout 65;

    # gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    server {
        listen 80;
        server_name localhost;
        root /usr/share/nginx/html;
        index index.html;

        # 前端路由支持
        location / {
            try_files $uri $uri/ /index.html;
        }

        # 代理后端API
        location /api/ {
            proxy_pass http://backend:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 代理算法网关
        location /algorithm/ {
            proxy_pass http://algorithm-gateway:18080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 7. Docker Compose 编排文件：`docker-compose.yml`

```yaml
version: '3.8'

services:
  # 前端服务
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - mmr-network
    volumes:
      - frontend-logs:/var/log/nginx

  # 后端服务
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - MMR_ALGORITHM_MODE=http
      - MMR_ALGORITHM_GATEWAY_URL=http://algorithm-gateway:18080
      - MMR_SQLITE_PATH=/app/data/sqlite/app.db
      - MMR_FAISS_DIR=/app/data/faiss
      - MMR_QUERY_UPLOAD_DIR=/app/data/query_uploads
      - MMR_MANAGED_ASSETS_DIR=/app/data/assets
      - MMR_PREPROCESS_TEMP_DIR=/app/data/preprocess_tmp
    volumes:
      - shared-data:/app/data
      - backend-logs:/app/logs
    depends_on:
      algorithm-gateway:
        condition: service_healthy
    networks:
      - mmr-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # 算法网关和算法服务
  algorithm-gateway:
    build:
      context: ./algorithm
      dockerfile: Dockerfile
    ports:
      - "18080:18080"
    environment:
      - PYTHONUNBUFFERED=1
      - PYTHONPATH=/app
    volumes:
      - shared-data:/app/data
      - algorithm-logs:/app/logs
    networks:
      - mmr-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:18080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

networks:
  mmr-network:
    driver: bridge

volumes:
  shared-data:
    driver: local
  backend-logs:
    driver: local
  algorithm-logs:
    driver: local
  frontend-logs:
    driver: local
```

### 8. 环境变量配置文件：`.env.docker`

```env
# Docker环境变量配置

# 后端配置
MMR_ALGORITHM_MODE=http
MMR_ALGORITHM_GATEWAY_URL=http://algorithm-gateway:18080
MMR_SQLITE_PATH=/app/data/sqlite/app.db
MMR_FAISS_DIR=/app/data/faiss
MMR_QUERY_UPLOAD_DIR=/app/data/query_uploads
MMR_MANAGED_ASSETS_DIR=/app/data/assets
MMR_PREPROCESS_TEMP_DIR=/app/data/preprocess_tmp
MMR_LOCAL_JOB_WORKERS=4
MMR_DEFAULT_TOPK=10
MMR_MAX_TOPK=100

# 算法服务检查点路径（根据实际路径调整）
I2I_CKPT_PATH=analyze_valid/base_distill_patchmask/augment_base_distill_float32_NWEP_RESISC45_256_2024-09-21-13-44-39/base_distill_NWEP_RESISC45_256_0.9648.pt
T2I_CKPT_PATH=Ksample4Ratio0.32025-01-29/21-09-16/checkpoints/model-best.tar
T2V_CKPT_PATH=ckpts/model_step_10547.pt
```

### 9. 构建和运行脚本：`docker-build-run.sh`

```bash
#!/bin/bash
set -e

echo "========================================="
echo "MultiRetrievalSystem Docker 构建和启动脚本"
echo "========================================="

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装"
    exit 1
fi

# 函数：显示帮助
show_help() {
    echo "用法: $0 [选项]"
    echo "选项:"
    echo "  build     构建所有Docker镜像"
    echo "  up        启动所有服务"
    echo "  down      停止并移除所有服务"
    echo "  restart   重启所有服务"
    echo "  logs      查看服务日志"
    echo "  status    查看服务状态"
    echo "  clean     清理所有Docker资源"
    echo "  help      显示此帮助信息"
}

# 函数：构建镜像
build_images() {
    echo "开始构建Docker镜像..."
    
    echo "1. 构建后端镜像..."
    docker build -t mmr-backend:latest -f backend/Dockerfile backend/
    
    echo "2. 构建算法服务镜像..."
    docker build -t mmr-algorithm:latest -f algorithm/Dockerfile algorithm/
    
    echo "3. 构建前端镜像..."
    docker build -t mmr-frontend:latest -f frontend/Dockerfile frontend/
    
    echo "所有镜像构建完成！"
}

# 函数：启动服务
start_services() {
    echo "启动MultiRetrievalSystem服务..."
    
    # 加载环境变量
    if [ -f .env.docker ]; then
        echo "加载环境变量..."
        export $(grep -v '^#' .env.docker | xargs)
    fi
    
    # 启动服务
    docker-compose up -d
    
    echo "服务启动完成！"
    echo ""
    echo "访问地址:"
    echo "  前端界面: http://localhost"
    echo "  后端API: http://localhost:8000"
    echo "  算法网关: http://localhost:18080"
    echo ""
    echo "查看服务状态: docker-compose ps"
    echo "查看服务日志: docker-compose logs -f"
}

# 函数：停止服务
stop_services() {
    echo "停止MultiRetrievalSystem服务..."
    docker-compose down
    echo "服务已停止"
}

# 函数：重启服务
restart_services() {
    echo "重启MultiRetrievalSystem服务..."
    docker-compose restart
    echo "服务已重启"
}

# 函数：查看日志
show_logs() {
    echo "查看服务日志..."
    docker-compose logs -f
}

# 函数：查看状态
show_status() {
    echo "服务状态:"
    docker-compose ps
    echo ""
    echo "容器运行状态:"
    docker-compose top
}

# 函数：清理资源
clean_resources() {
    echo "清理Docker资源..."
    
    read -p "确定要清理所有Docker资源吗？(y/N): " confirm
    if [[ $confirm == [yY] ]]; then
        docker-compose down -v --rmi all
        docker system prune -af
        echo "资源清理完成"
    else
        echo "取消清理"
    fi
}

# 主逻辑
case "$1" in
    "build")
        build_images
        ;;
    "up"|"start")
        start_services
        ;;
    "down"|"stop")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "clean")
        clean_resources
        ;;
    "help"|"")
        show_help
        ;;
    *)
        echo "未知选项: $1"
        show_help
        exit 1
        ;;
esac
```

## 构建和部署步骤

### 步骤1：创建文件
1. 在项目根目录创建 `build.md`（本文档）
2. 在 `algorithm/` 目录创建 `requirements.txt`
3. 在 `backend/` 目录创建 `Dockerfile`
4. 在 `algorithm/` 目录创建 `Dockerfile` 和 `docker-entrypoint.sh`
5. 在 `frontend/` 目录创建 `Dockerfile` 和 `nginx.conf`
6. 在项目根目录创建 `docker-compose.yml` 和 `.env.docker`
7. 在项目根目录创建 `docker-build-run.sh`

### 步骤2：设置文件权限
```bash
# 在项目根目录执行
chmod +x algorithm/docker-entrypoint.sh
chmod +x docker-build-run.sh
```

### 步骤3：构建 Docker 镜像
```bash
# 方法1：使用构建脚本
./docker-build-run.sh build

# 方法2：手动构建
docker-compose build
```

### 步骤4：启动服务
```bash
# 方法1：使用脚本启动
./docker-build-run.sh up

# 方法2：手动启动
docker-compose up -d
```

### 步骤5：验证服务状态
```bash
# 检查所有容器状态
docker-compose ps

# 查看服务日志
docker-compose logs -f

# 健康检查
curl http://localhost/api/v1/health        # 后端健康检查
curl http://localhost:18080/health         # 算法网关健康检查

# 或者使用脚本
./docker-build-run.sh status
```

### 步骤6：访问应用
- **前端界面**：http://localhost
- **后端API文档**：http://localhost:8000/docs
- **算法网关**：http://localhost:18080

## 配置说明

### 端口映射
| 服务 | 容器端口 | 主机端口 | 说明 |
|------|----------|----------|------|
| 前端 | 80 | 80 | Web界面 |
| 后端 | 8000 | 8000 | API服务 |
| 算法网关 | 18080 | 18080 | 算法服务入口 |

### 数据持久化
Docker Compose 配置了以下数据卷：
1. `shared-data` - 共享数据目录（SQLite、FAISS索引、资源文件）
2. `backend-logs` - 后端服务日志
3. `algorithm-logs` - 算法服务日志
4. `frontend-logs` - Nginx日志

### 环境变量配置
主要环境变量在 `.env.docker` 中配置：
- `MMR_ALGORITHM_MODE`：算法模式（http/deterministic）
- `MMR_ALGORITHM_GATEWAY_URL`：算法网关地址
- 数据目录路径配置

## 高级配置

### GPU 支持（可选）
如果需要 GPU 加速，修改 `algorithm/Dockerfile`：

```dockerfile
# 使用CUDA基础镜像
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
```

并在 `docker-compose.yml` 中添加 GPU 配置：
```yaml
algorithm-gateway:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

### 自定义模型检查点
模型检查点路径在 `algorithm/launcher/run_all.py` 中定义，如需自定义：
1. 在容器中挂载模型目录
2. 修改检查点路径环境变量

## 运维管理

### 常用命令
```bash
# 查看服务状态
./docker-build-run.sh status

# 查看实时日志
./docker-build-run.sh logs

# 重启服务
./docker-build-run.sh restart

# 停止服务
./docker-build-run.sh down

# 清理所有Docker资源
./docker-build-run.sh clean
```

### 日志管理
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs algorithm-gateway
docker-compose logs frontend

# 跟踪实时日志
docker-compose logs -f
```

### 备份和恢复
```bash
# 备份数据卷
docker run --rm -v shared-data:/data -v $(pwd):/backup alpine tar czf /backup/backup-$(date +%Y%m%d).tar.gz /data

# 恢复数据卷
docker run --rm -v shared-data:/data -v $(pwd):/backup alpine sh -c "cd /data && tar xzf /backup/backup.tar.gz --strip 1"
```

## 故障排除

### 常见问题

#### 1. 构建失败：依赖安装错误
**解决方案**：
- 检查网络连接
- 更新 `requirements.txt` 中的版本号
- 使用国内镜像源

#### 2. 服务启动失败：端口冲突
**解决方案**：
- 检查端口占用：`netstat -tulpn | grep -E '80|8000|18080'`
- 修改 `docker-compose.yml` 中的端口映射

#### 3. 算法服务无法连接
**解决方案**：
1. 检查算法网关健康状态：`curl http://localhost:18080/health`
2. 查看算法服务日志：`docker-compose logs algorithm-gateway`
3. 验证模型检查点路径是否正确

#### 4. 前端无法访问后端 API
**解决方案**：
1. 检查 Nginx 配置中的代理设置
2. 验证后端服务是否正常运行：`curl http://backend:8000/api/v1/health`
3. 检查跨域配置

### 调试技巧
```bash
# 进入容器内部调试
docker-compose exec backend bash
docker-compose exec algorithm-gateway bash

# 查看容器资源使用情况
docker stats

# 检查容器网络
docker network inspect mmr_mmr-network
```

## 性能优化建议

1. **内存优化**：
   - 算法服务分配足够内存（建议8GB+）
   - 使用内存监控工具

2. **GPU加速**：
   - 启用CUDA支持
   - 使用混合精度训练

3. **存储优化**：
   - 定期清理临时文件
   - 使用SSD存储提高IO性能

4. **网络优化**：
   - 配置合适的连接池大小
   - 启用HTTP/2

## 更新和升级

### 更新代码
```bash
# 停止服务
./docker-build-run.sh down

# 拉取最新代码
git pull

# 重新构建和启动
./docker-build-run.sh build
./docker-build-run.sh up
```

### 更新依赖
1. 更新 `requirements.txt` 或 `package.json`
2. 重新构建Docker镜像
3. 重启服务

## 安全建议

1. **网络隔离**：使用Docker网络隔离服务
2. **最小权限**：使用非root用户运行容器
3. **密钥管理**：使用Docker Secrets管理敏感信息
4. **定期更新**：及时更新基础镜像和安全补丁

## 扩展部署

### 多节点部署
对于生产环境，建议使用：
1. Docker Swarm 或 Kubernetes
2. 负载均衡器
3. 分布式存储
4. 监控和日志聚合

### 云平台部署
支持部署到：
- AWS ECS/EKS
- Google Cloud Run/GKE
- Azure Container Instances/AKS
- 阿里云容器服务

---

## 支持与反馈

如有问题或建议：
1. 查看日志文件
2. 检查本文档的故障排除部分
3. 联系开发团队

---
*最后更新：2026年4月21日*
*MultiRetrievalSystem Docker化构建指南*