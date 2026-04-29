# 多模态检索系统算法端技术说明文档

## 1. 项目目标

本项目将三类检索模型封装为统一的 HTTP 编码服务，供后端直接调用。

支持的任务如下。

- `i2i`，图搜图编码
- `t2i`，文搜图编码
- `t2v`，文搜视频编码

系统目标不是直接做检索排序，而是对输入进行向量化。后端拿到向量后，可以继续执行 FAISS 检索、缓存、入库、索引构建、召回、重排等后续流程。

这与方案文档中的系统分层一致。整体上由后端 FastAPI、算法 Python 编码服务、FAISS、MinIO、MLflow、Celery 等组件构成，算法侧职责是对 Query 和 Keys 做向量化，并在批量输入时支持分批处理。fileciteturn2file0 fileciteturn2file1

---

## 2. 当前服务结构

当前实现采用四个服务进程。

- `gateway`，统一入口，端口 `18080`
- `i2i worker`，图像编码，端口 `18081`
- `t2i worker`，文本和图像编码，端口 `18082`
- `t2v worker`，文本和视频编码，端口 `18083`

调用路径如下。

1. 调用方请求 `gateway /encode`
2. gateway 根据 `scene` 或 `scence` 路由到对应 worker
3. worker 将输入归一化后调用底层 `encode(...)`
4. worker 返回 embedding，gateway 原样转发

health 检查也通过 gateway 聚合完成。

---

## 3. 设计原则

### 3.1 编码器原则

本服务是编码器，不是检索器。

它只负责一件事，有有效输入就编码，无有效输入就返回空。

统一原则如下。

- `query` 有值，就编码 `query`
- `key` 有值，就编码 `key`
- `query` 为空，不报错，返回 `query_embed = []`
- `key` 为空，不报错，返回 `key_embed = []`
- `query` 和 `key` 都为空，也不报错，直接返回空结果

### 3.2 批量原则

`query` 和 `key` 都支持单值和列表。

也就是都支持下面两种形式。

- 单值，例如 `"query": "text"`
- 批量，例如 `"query": ["text1", "text2"]`

服务层会统一归一化成列表，再交给底层模型编码。

### 3.3 空值过滤原则

以下输入会被视为空并自动过滤。

- `None`
- `""`
- 纯空白字符串
- `[]`
- `[
  "",
  None
]` 这类过滤后为空的列表

### 3.4 返回格式原则

为了兼容批量调用，返回统一采用批量形式。

即使只有一个 query，也返回二维列表。

例如。

```json
{
  "scene": "i2i",
  "query_embed": [[0.1, 0.2, 0.3]],
  "key_embed": [[0.4, 0.5, 0.6]]
}
```

---

## 4. 目录说明

推荐项目目录如下。

```text
RetrievalSys/
├─ launcher/
│  └─ run_all.py
├─ gateway/
│  └─ app.py
├─ common/
│  └─ api_utils.py
├─ ImageRetrieval/
│  ├─ i2i_encode.py
│  └─ serve_i2i.py
├─ MedicalRetrieval/
│  ├─ t2i_encode.py
│  └─ serve_t2i.py
├─ VideoRetrieval/
│  ├─ t2v_encode.py
│  └─ serve_t2v.py
└─ tests/
   └─ test_data/
```

三个原始模型入口文件分别是。

- `ImageRetrieval/i2i_encode.py`
- `MedicalRetrieval/t2i_encode.py`
- `VideoRetrieval/t2v_encode.py`

并且都要求在各自目录下运行，这一点与最初需求一致。fileciteturn2file2 fileciteturn2file3 fileciteturn2file4

---

## 5. 启动方式

### 5.1 checkpoint 配置

当前 `launcher/run_all.py` 采用常量配置模型权重路径，而不是环境变量。

典型形式如下。

```python
I2I_CKPT_PATH = ""
T2I_CKPT_PATH = ""
T2V_CKPT_PATH = ""
```

说明如下。

- 空字符串表示不加载 checkpoint，只初始化模型结构
- 填入真实路径表示启动时加载权重

### 5.2 启动命令

在项目根目录执行。

```bash
python launcher/run_all.py
```

正常启动后，会看到四个端口启动。

- `18080`，gateway
- `18081`，i2i
- `18082`，t2i
- `18083`，t2v

### 5.3 健康检查

#### 检查统一入口

```bash
curl http://127.0.0.1:18080/health
```

#### 检查单个 worker

```bash
curl http://127.0.0.1:18081/health
curl http://127.0.0.1:18082/health
curl http://127.0.0.1:18083/health
```

正常返回示例。

```json
{"ok": true, "worker": "i2i"}
```

---

## 6. 接口说明

统一入口。

- `POST /encode`

健康检查。

- `GET /health`

### 6.1 输入字段

`POST /encode` 请求体支持以下字段。

| 字段 | 类型 | 说明 |
|---|---|---|
| scene | str | 推荐使用，任务类型，`i2i`、`t2i`、`t2v` |
| scence | str | 兼容旧拼写 |
| query | str 或 list | query 输入，可为空 |
| key | str 或 list | key 输入，可为空 |
| params | dict | 预留参数，目前可为空 |

### 6.2 返回字段

#### i2i

```json
{
  "scene": "i2i",
  "query_embed": [[...], [...]],
  "key_embed": [[...], [...]]
}
```

#### t2i

```json
{
  "scene": "t2i",
  "query": ["text1", "text2"],
  "query_embed": [[...], [...]],
  "key_embed": [[...], [...]]
}
```

#### t2v

```json
{
  "scene": "t2v",
  "query": ["text1", "text2"],
  "query_embed": [[...], [...]],
  "key_embed": [[...], [...]]
}
```

说明如下。

- 没有有效输入的那一侧，返回 `[]`
- 有输入的一侧，返回批量向量列表

---

## 7. 使用示例

### 7.1 Python 单条调用示例

#### i2i

```python
import requests
import json

url = "http://127.0.0.1:18080/encode"

payload = {
    "scene": "i2i",
    "query": r"F:\\Code\\RetrievalSys\\tests\\test_data\\ImageRetrieval\\airplane_001.jpg",
    "key": [
        r"F:\\Code\\RetrievalSys\\tests\\test_data\\ImageRetrieval\\airplane_002.jpg",
        r"F:\\Code\\RetrievalSys\\tests\\test_data\\ImageRetrieval\\airplane_003.jpg"
    ]
}

resp = requests.post(url, json=payload, timeout=300)
print(resp.status_code)
print(json.dumps(resp.json(), ensure_ascii=False, indent=2)[:1000])
```

#### t2i

```python
import requests
import json

url = "http://127.0.0.1:18080/encode"

payload = {
    "scene": "t2i",
    "query": "Spindle cell variant of embryonal rhabdomyosarcoma is characterized by fascicles of eosinophilic spindle cells.",
    "key": [
        r"F:\\Code\\RetrievalSys\\tests\\test_data\\MedicalRetrieval\\2a2277a9-b0ded155-c0de8eb9-c124d10e-82c5caab.jpg",
        r"F:\\Code\\RetrievalSys\\tests\\test_data\\MedicalRetrieval\\68b5c4b1-227d0485-9cc38c3f-7b84ab51-4b472714.jpg"
    ]
}

resp = requests.post(url, json=payload, timeout=300)
print(resp.status_code)
print(json.dumps(resp.json(), ensure_ascii=False, indent=2)[:1000])
```

#### t2v

```python
import requests
import json

url = "http://127.0.0.1:18080/encode"

payload = {
    "scene": "t2v",
    "query": "a band performing in a small club",
    "key": [
        r"F:\\Code\\RetrievalSys\\tests\\test_data\\VideoRetrieval\\video0.mp4",
        r"F:\\Code\\RetrievalSys\\tests\\test_data\\VideoRetrieval\\video1.mp4"
    ]
}

resp = requests.post(url, json=payload, timeout=300)
print(resp.status_code)
print(json.dumps(resp.json(), ensure_ascii=False, indent=2)[:1000])
```

### 7.2 Python 批量 query 示例

#### t2i 批量 query

```python
payload = {
    "scene": "t2i",
    "query": [
        "Spindle cell variant of embryonal rhabdomyosarcoma is characterized by fascicles of eosinophilic spindle cells.",
        "cell variant of embryonal rhabdomyosarcoma is characterized by fas"
    ],
    "key": [
        r"F:\\Code\\RetrievalSys\\tests\\test_data\\MedicalRetrieval\\2a2277a9-b0ded155-c0de8eb9-c124d10e-82c5caab.jpg"
    ]
}
```

#### i2i 批量 query

```python
payload = {
    "scene": "i2i",
    "query": [
        r"F:\\Code\\RetrievalSys\\tests\\test_data\\ImageRetrieval\\airplane_001.jpg",
        r"F:\\Code\\RetrievalSys\\tests\\test_data\\ImageRetrieval\\airplane_002.jpg"
    ],
    "key": []
}
```

### 7.3 空输入示例

#### query 为空，key 有值

```python
payload = {
    "scene": "i2i",
    "query": "",
    "key": [
        r"F:\\Code\\RetrievalSys\\tests\\test_data\\ImageRetrieval\\airplane_001.jpg"
    ]
}
```

返回预期。

```json
{
  "scene": "i2i",
  "query_embed": [],
  "key_embed": [[...]]
}
```

#### query 和 key 都为空

```python
payload = {
    "scene": "t2v",
    "query": "",
    "key": []
}
```

返回预期。

```json
{
  "scene": "t2v",
  "query": [],
  "query_embed": [],
  "key_embed": []
}
```

---

## 8. 开发说明

### 8.1 三个底层 encode 的职责

#### i2i

输入图像路径列表，输出图像 embedding。

要求。

- 输入为空时返回 `[]`
- 输入非空时返回 `Tensor`
- service 层会将 Tensor 转成 Python 列表

#### t2i

输入文本列表和图像路径列表，分别独立编码。

要求。

- 只对有值的一侧建 dataloader
- 文本侧为空时返回 `[]`
- 图像侧为空时返回 `[]`

#### t2v

输入文本列表和视频路径列表，分别独立编码。

要求。

- 只对有值的一侧建 dataloader
- 文本张量和视频张量都要放到 model 所在 device
- 文本侧为空时返回 `[]`
- 视频侧为空时返回 `[]`

### 8.2 service 层职责

worker 层负责。

- 接收 HTTP 请求
- 归一化 query 和 key
- 过滤空字符串和空值
- 调用底层 encode
- 将 Tensor 转成 JSON 可序列化的列表

### 8.3 gateway 层职责

gateway 负责。

- 统一入口
- 根据 `scene` 路由到不同 worker
- 聚合健康检查
- 代理下游错误信息

---

## 9. 回归测试建议

推荐使用统一测试脚本，一次性覆盖以下情况。

- 正常单条 query 和多 key
- query 为空，key 有值
- query 为 list，key 为空
- query 和 key 都为空
- query 为 `None`，key 为 `None`
- `scence` 旧拼写兼容
- 列表中混入空字符串和 `None`

你最近一次测试中，19 个 case 通过了 16 个，失败的 3 个全部是 `invalid_blank_items_filtered`，原因是请求模型过早将 `None` 拦截成 422，还没有进入过滤逻辑。fileciteturn3file0

因此开发侧需要确保 `EncodeRequest` 中 `query` 和 `key` 的类型足够宽松，例如使用 `Union[str, List[Any]]` 或 `Any`，然后统一交给 `normalize_to_str_list()` 过滤。fileciteturn3file0

---

## 10. 常见故障排查

### 10.1 gateway 健康检查报 502，但单独访问 worker 是 200

现象。

- `curl http://127.0.0.1:18081/health` 返回 200
- `curl http://127.0.0.1:18080/health` 中某个 worker 显示 502

原因。

在 Windows 或企业网络环境下，Python HTTP 客户端可能读取了系统代理环境变量，导致访问 `127.0.0.1` 也走代理。

处理方式。

在 `gateway/app.py` 中使用。

```python
httpx.Client(..., trust_env=False)
```

这是本次联调里已经确认过的真实问题。fileciteturn3file0

### 10.2 i2i 启动时报 argparse unrecognized arguments

现象。

```text
error: unrecognized arguments: serve_i2i:app --host 0.0.0.0 --port 18081
```

原因。

`uvicorn` 启动参数残留在 `sys.argv` 中，被原始算法代码里的 `argparse` 读到了。

处理方式。

在调用原始配置读取逻辑之前，用 `isolated_argv()` 暂时清空 `sys.argv`。

### 10.3 t2i 启动时报 HydraConfig was not set

现象。

`MedicalRetrieval` 启动时报 Hydra 配置相关错误。

原因。

直接在服务进程里调用 Hydra 入口函数，或只做 `compose` 但没有注入 HydraConfig。

处理方式。

- 使用 `initialize_config_dir + compose`
- 调用 `HydraConfig.instance().set_config(cfg)`
- 视情况移除 `cfg["hydra"]`

### 10.4 t2v 推理时报 Expected all tensors to be on the same device

现象。

```text
Expected all tensors to be on the same device, but found at least two devices, cuda:0 and cpu
```

原因。

`t2v_encode.py` 中的 `text_input_ids`、`text_input_mask`、`video` 没有全部移动到 model 所在 device。

处理方式。

在 `encode()` 中统一做。

```python
text_input_ids = text_input_ids.to(device)
text_input_mask = text_input_mask.to(device)
video = video.to(device)
```

### 10.5 空 key 时 torch.cat 报错

现象。

```text
torch.cat(): expected a non-empty list of Tensors
```

原因。

某一侧输入为空，但底层 `encode()` 仍然在对空列表做 `torch.cat([])`。

处理方式。

底层 `encode()` 改成。

- 输入为空时直接返回 `[]`
- 只有收集到有效 feature 后再 `torch.cat`

### 10.6 列表中带 None 时返回 422

现象。

例如。

```json
{
  "scene": "t2v",
  "query": ["", "   ", "a band performing in a small club"],
  "key": ["", null, "video0.mp4"]
}
```

直接返回 422，而不是被过滤后继续执行。

原因。

Pydantic 请求模型把 `key` 定义成了 `List[str]`，导致列表里的 `None` 在请求解析阶段就失败。

处理方式。

把请求模型改宽松，例如。

```python
query: Optional[Union[str, List[Any]]] = None
key: Optional[Union[str, List[Any]]] = None
```

然后统一交给 `normalize_to_str_list()` 过滤。这个问题在本次测试日志中已经明确出现。fileciteturn3file0

### 10.7 空 checkpoint 启动后向量数值异常

现象。

服务能启动，但 embedding 没有业务意义。

原因。

checkpoint 为空时，仅初始化了模型结构，未加载训练权重。

处理方式。

确认 `launcher/run_all.py` 中三个 checkpoint 常量是否已正确填写。

### 10.8 本地路径存在，但 worker 报文件找不到

原因。

当前三类底层脚本都直接从本地文件系统读取图像或视频路径。因此调用方传入的路径，必须是算法服务所在机器可直接访问的绝对路径或有效相对路径。fileciteturn2file2 fileciteturn2file3 fileciteturn2file4

如果后端只持有 MinIO object key 或数据库记录，需在调用编码器前先完成路径映射或下载到本地。

---

## 11. 开发建议

1. 固定接口语义，不要在 worker 中写“query 必填”这类业务校验
2. worker 只负责编码，业务规则由后端决定
3. 所有输入统一先做归一化，再做编码
4. 所有输出统一返回批量列表，避免单条和批量格式不一致
5. 修改底层模型逻辑后，务必跑一遍统一回归测试

---

## 12. 交付建议

如果后续需要正式交付给后端团队，建议同时交付以下内容。

- 本 README
- `launcher/run_all.py`
- 四个 HTTP 服务文件
- 三个底层 `encode` 文件
- 一份统一测试脚本
- 一份端口说明和 checkpoint 配置说明
- 一份问题排查清单

