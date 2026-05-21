# 多模态检索系统局域网部署整改方案

## 1. 产品需求文档(PRD)

### 1.1 项目背景
当前多模态检索系统采用本地部署模式，由于本地算力不足，需要将算法端和后端迁移到局域网环境，通过分布式部署方式提升系统性能和资源利用率。

### 1.2 核心目标
- 将计算密集型算法服务迁移到局域网专用服务器
- 保持现有系统功能和接口不变
- 优化网络通信和文件访问机制
- 简化演示和测试流程

### 1.3 功能需求
1. **算法服务迁移**：支持将i2i、t2i、t2v算法服务部署到局域网服务器
2. **后端连接配置**：支持通过环境变量配置算法服务地址
3. **文件路径处理**：支持服务器本地路径直接访问
4. **网络通信优化**：支持HTTP协议跨服务器通信

### 1.4 非功能需求
- **性能要求**：网络延迟<100ms，服务响应时间<5s
- **可靠性**：支持服务健康检查和自动重试
- **可扩展性**：支持后续增加更多算法节点
- **安全性**：支持基础网络访问控制

## 2. 技术实现方案

### 2.1 系统架构调整

#### 部署架构
```
局域网部署架构：
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   前端      │    │   后端      │    │  算法服务器  │
│             │    │ (FastAPI)   │    │             │
│  浏览器     │◄──►│  8000端口   │◄──►│ 18080-18083  │
└─────────────┘    └─────────────┘    └─────────────┘
                            │
                            ▼
                    ┌─────────────┐
                    │  文件存储   │
                    │ (共享目录)  │
                    └─────────────┘
```

### 2.2 算法端改造

#### 2.2.1 服务监听配置
```python
# launcher/run_all.py 修改
# 将服务监听地址从127.0.0.1改为0.0.0.0
uvicorn.run("gateway.app:app", host="0.0.0.0", port=18080)
uvicorn.run("ImageRetrieval.serve_i2i:app", host="0.0.0.0", port=18081)
uvicorn.run("MedicalRetrieval.serve_t2i:app", host="0.0.0.0", port=18082)
uvicorn.run("VideoRetrieval.serve_t2v:app", host="0.0.0.0", port=18083)
```

#### 2.2.2 checkpoint路径配置
```python
# 支持环境变量配置checkpoint路径
import os
I2I_CKPT_PATH = os.getenv("I2I_CKPT_PATH", "")
T2I_CKPT_PATH = os.getenv("T2I_CKPT_PATH", "")
T2V_CKPT_PATH = os.getenv("T2V_CKPT_PATH", "")
```

### 2.3 后端配置调整

#### 2.3.1 环境变量配置
```bash
# 后端环境变量设置
export MMR_ALGORITHM_MODE=http
export MMR_ALGORITHM_GATEWAY_URL=http://算法服务器IP:18080
export MMR_ALGORITHM_TIMEOUT=300  # 增加超时时间
```

#### 2.3.2 算法服务调用优化
```python
# app/services/algorithm_service.py 优化
class AlgorithmService:
    def __init__(self):
        self.gateway_url = os.getenv("MMR_ALGORITHM_GATEWAY_URL", "http://127.0.0.1:18080")
        self.timeout = int(os.getenv("MMR_ALGORITHM_TIMEOUT", 300))
        
    async def encode(self, scene: str, query, key):
        # 增加重试机制和网络异常处理
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.gateway_url}/encode",
                json={"scene": scene, "query": query, "key": key}
            )
            return response.json()
```

### 2.4 文件路径处理方案

#### 2.4.1 演示模式优化
```python
# app/services/prepare_service.py 优化
class PrepareService:
    def process_keys(self, keys: List[str], scene: str):
        # 演示模式：直接使用服务器本地路径
        if os.getenv("DEMO_MODE", "false").lower() == "true":
            # 验证路径存在性
            valid_keys = []
            for key in keys:
                if os.path.exists(key):
                    valid_keys.append(key)
                else:
                    logger.warning(f"路径不存在: {key}")
            return valid_keys
        else:
            # 生产模式：原有逻辑
            return self._process_keys_production(keys, scene)
```

### 2.5 网络通信优化

#### 2.5.1 连接池配置
```python
# app/core/config.py 增加配置
class Settings(BaseSettings):
    algorithm_connection_pool_size: int = 10
    algorithm_connection_pool_maxsize: int = 20
    
# app/services/algorithm_service.py
class AlgorithmService:
    def __init__(self):
        limits = httpx.Limits(
            max_connections=self.connection_pool_size,
            max_keepalive_connections=self.connection_pool_maxsize
        )
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=limits,
            trust_env=False  # 避免代理问题
        )
```

### 2.6 部署步骤

#### 2.6.1 算法服务器部署
```bash
# 1. 在算法服务器上安装依赖
cd algorithm/
pip install -r requirements.txt

# 2. 设置环境变量
export I2I_CKPT_PATH="/path/to/i2i/checkpoint"
export T2I_CKPT_PATH="/path/to/t2i/checkpoint" 
export T2V_CKPT_PATH="/path/to/t2v/checkpoint"

# 3. 启动算法服务
python launcher/run_all.py
```

#### 2.6.2 后端服务器部署
```bash
# 1. 在后端服务器上安装依赖
cd backend/
pip install -r requirements.txt

# 2. 设置环境变量
export MMR_ALGORITHM_MODE=http
export MMR_ALGORITHM_GATEWAY_URL=http://算法服务器IP:18080
export MMR_ALGORITHM_TIMEOUT=300
export DEMO_MODE=true  # 演示模式

# 3. 启动后端服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2.7 测试验证方案

#### 2.7.1 连通性测试
```bash
# 测试算法服务
curl http://算法服务器IP:18080/health

# 测试后端到算法服务
curl -X POST http://后端服务器IP:8000/api/v1/health
```

#### 2.7.2 功能测试
```python
# 测试脚本示例
def test_end_to_end():
    # 1. 测试建库
    response = requests.post(
        "http://后端服务器IP:8000/api/v1/vectorize",
        json={
            "scene": "Image2Image",
            "store_type": "Folder",
            "store_name": "测试库",
            "keys": ["/path/to/server/test/data"]
        }
    )
    
    # 2. 等待任务完成
    job_id = response.json()["job_id"]
    # 轮询任务状态...
    
    # 3. 测试检索
    response = requests.post(
        "http://后端服务器IP:8000/api/v1/search",
        json={
            "scene": "Image2Image",
            "store_type": "Folder",
            "topk": 5,
            "input": {
                "image_object_keys": ["uploaded_image_key"]
            }
        }
    )
```

## 3. 实施建议

### 3.1 分阶段实施
1. **第一阶段**：完成算法服务局域网部署和基础连通性测试
2. **第二阶段**：优化文件路径处理和演示流程
3. **第三阶段**：完善错误处理和性能监控

### 3.2 风险控制
- **回滚方案**：保留原有本地部署配置，可随时切换
- **监控告警**：增加服务健康检查和性能监控
- **容量规划**：评估服务器资源需求，避免过载

### 3.3 后续优化
- **负载均衡**：支持多算法节点部署
- **缓存优化**：增加向量结果缓存机制
- **异步处理**：优化大文件处理流程