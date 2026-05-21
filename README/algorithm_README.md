# 多模态检索系统算法端说明

## 系统定位
提供统一的HTTP编码服务，将三类检索模型封装为标准化接口，供后端调用。

## 服务架构
```
Gateway (18080)
├── i2i Worker (18081) - 图搜图编码
├── t2i Worker (18082) - 文搜图编码
└── t2v Worker (18083) - 文搜视频编码
```

## 核心接口
```
POST /encode     # 统一编码入口
GET  /health     # 健康检查
```

## 业务场景映射
| 算法场景 | 前端场景 | 说明 |
|---------|---------|------|
| i2i | Image2Image | 图搜图编码 |
| t2i | Text2Image | 文搜图编码 |
| t2v | Text2Video | 文搜视频编码 |

## 输入输出格式

### 输入格式
```json
{
  "scene": "i2i|t2i|t2v",
  "query": "str|list[str]",     // 可为空
  "key": "str|list[str]",       // 可为空
  "params": {}                  // 预留参数
}
```

### 输出格式
```json
{
  "scene": "i2i",
  "query_embed": [[...]],       // 二维列表
  "key_embed": [[...], [...]]   // 二维列表
}
```

## 快速启动
```bash
cd algorithm
python launcher/run_all.py
```

## 健康检查
```bash
# 统一检查
curl http://127.0.0.1:18080/health

# 单独检查
curl http://127.0.0.1:18081/health
curl http://127.0.0.1:18082/health
curl http://127.0.0.1:18083/health
```

## 设计原则
1. **编码器原则**: 只负责向量化，不做检索排序
2. **批量原则**: 支持单值和列表输入
3. **空值过滤**: 自动过滤None、空字符串等无效值
4. **统一格式**: 始终返回二维列表，即使单条数据

## 使用示例

### 图搜图
```python
payload = {
    "scene": "i2i",
    "query": "/path/to/query.jpg",
    "key": ["/path/to/key1.jpg", "/path/to/key2.jpg"]
}
```

### 文搜图
```python
payload = {
    "scene": "t2i",
    "query": "a red car on the street",
    "key": ["/path/to/image1.jpg", "/path/to/image2.jpg"]
}
```

### 文搜视频
```python
payload = {
    "scene": "t2v",
    "query": "a cat playing with a ball",
    "key": ["/path/to/video1.mp4", "/path/to/video2.mp4"]
}
```

## 故障排查
| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Gateway 502 | 系统代理干扰 | gateway/app.py 设置 trust_env=False |
| 文件找不到 | 路径不可访问 | 确保算法服务能访问传入路径 |
| 设备不一致 | tensor不在同设备 | encode()中统一.to(device) |
| 空列表cat报错 | 空输入未处理 | 空输入直接返回[] |

## 配置说明
```
# 模型权重路径配置 (launcher/run_all.py)
I2I_CKPT_PATH = ""    # 空=不加载权重
T2I_CKPT_PATH = ""    # 空=不加载权重
T2V_CKPT_PATH = ""    # 空=不加载权重
```

## 注意事项
- 算法端只负责编码，不参与业务规则
- 路径必须是算法服务所在机器可访问的
- 输入输出格式必须严格遵循规范
- 空值会被自动过滤，不会报错