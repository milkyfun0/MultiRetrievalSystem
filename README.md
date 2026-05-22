# MultiRetrievalSystem 多模态检索系统

> 基于 Vue 3 + FastAPI + 自研算法栈的多模态检索平台，支持 **文搜视频 (T2V)**、**文搜图 (T2I)**、**图搜图 (I2I)** 三类场景。
>
> 当前分支 `feature/deploy` 主要任务是：把单机原型拆成 **算力机 / 前端机 / 演示机** 三角部署形态，覆盖从开发到客户路演的全部场景。

---

## 目录

1. [架构与端口](#1-架构与端口)
2. [仓库结构](#2-仓库结构)
3. [部署形态总览](#3-部署形态总览)
4. [快速开始（单机开发）](#4-快速开始单机开发)
5. [部署文档导航](#5-部署文档导航)
6. [组件文档](#6-组件文档)
7. [关键配置项](#7-关键配置项)
8. [常见问题](#8-常见问题)

---

## 1. 架构与端口

```
浏览器 ──▶ 前端 (Vue3 + Vite)  ──/api──▶ 后端 (FastAPI :8000)
                                           │
                                           ├─▶ SQLite (元数据)
                                           ├─▶ FAISS  (向量索引)
                                           └─▶ 算法网关 (:18080)
                                                    ├─ I2I :18081
                                                    ├─ T2I :18082
                                                    └─ T2V :18083
```

| 服务 | 默认监听 | 是否需暴露到局域网 | 说明 |
|---|---|---|---|
| 前端 (Vite dev) | `0.0.0.0:5173` | 视部署形态 | 开发模式；生产建议 `npm run build` 后用 nginx 托管 |
| 后端 FastAPI | `0.0.0.0:8000` | **是**（双机部署时） | 前端 `/api` 反代目标 |
| 算法网关 | `0.0.0.0:18080` | 否 | 仅供本机后端调用 |
| I2I / T2I / T2V | `:18081 / :18082 / :18083` | 否 | 网关内部转发 |

> 全局环境变量前缀 `MMR_`，例如 `MMR_PUBLIC_BASE_URL`、`MMR_ALGORITHM_MODE`，在 [`backend/app/core/config.py`](backend/app/core/config.py) 中定义。

---

## 2. 仓库结构

```
MultiRetrievalSystem/
├── algorithm/                 # 算法服务（详见 README/algorithm_README.md）
│   ├── gateway/               #   统一网关 :18080
│   ├── ImageRetrieval/        #   I2I  :18081
│   ├── MedicalRetrieval/      #   T2I  :18082
│   ├── VideoRetrieval/        #   T2V  :18083
│   ├── launcher/run_all.py    #   一键拉起 4 个进程
│   └── common/
├── backend/                   # 后端服务（详见 README/backend_README.md）
│   ├── app/                   #   FastAPI 应用（api / core / services / models）
│   ├── data/                  #   SQLite + FAISS + 托管资源
│   └── tests/
├── frontend/                  # 前端应用（详见 README/frontend_README.md）
│   ├── src/                   #   Vue 3 + TS + Pinia + Element Plus
│   ├── vite.config.ts
│   └── .env.example
├── deploy/
│   └── nginx/mmr.conf         # 静态托管 + /api 反代的自包含 nginx 主配置
├── data/Query.txt             # 演示用查询样例
├── logs/                      # run_lan.sh 输出的运行日志与 pid 文件
├── run.sh                     # 单机开发启动脚本（参考用）
├── run_lan.sh                 # 算力机一键起算法 + 后端（局域网形态）
├── LAN_DEPLOYMENT.md          # 局域网双机部署指南
├── CLIENT_DEPLOYMENT.md       # 演示机零环境部署指南（前端机静态托管）
└── README.md                  # 本文件
```

---

## 3. 部署形态总览

`feature/deploy` 分支同时支持三种形态，按场景挑一种即可：

| 形态 | 角色分布 | 演示机要求 | 入口文档 | 适用场景 |
|---|---|---|---|---|
| **A. 单机开发** | 一台机器跑全部组件 | 同一台 | 本文 §4 + [`run.sh`](run.sh) | 本地开发、调试 |
| **B. 局域网双机** | 算力机（算法+后端）+ 演示机（前端 Vite） | Node + 源码 | [`LAN_DEPLOYMENT.md`](LAN_DEPLOYMENT.md) | 单人长期演示、内部联调 |
| **C. 静态托管演示** | 算力机 + 前端机（nginx 静态站）+ 演示机（仅浏览器） | **仅浏览器** | [`CLIENT_DEPLOYMENT.md`](CLIENT_DEPLOYMENT.md) | 多人路演、客户演示 |

> 三种形态对源码要求都是 **零改动**，全部通过环境变量与部署配置切换。

---

## 4. 快速开始（单机开发）

### 4.1 环境要求

- Python ≥ 3.9（注意：3.8 不支持 `X | Y` 联合类型）
- Node.js ≥ 16
- FFmpeg（视频检索使用，已附带在 backend 目录）
- GPU 可选；无 GPU 时算法服务会回落到 CPU，速度较慢

### 4.2 安装依赖

```bash
# 后端 + 算法
pip install -r requirements.txt

# 前端
cd frontend && npm install && cd ..
```

### 4.3 启动（三个终端）

```bash
# 终端 1：算法网关 + I2I/T2I/T2V
cd algorithm && python launcher/run_all.py

# 终端 2：后端
cd backend && uvicorn app.main:app --reload

# 终端 3：前端
cd frontend && npm run dev
```

### 4.4 验证

| 检查项 | 命令 / 操作 | 期望 |
|---|---|---|
| 算法网关 | `curl http://127.0.0.1:18080/health` | 200 |
| 后端 | `curl http://127.0.0.1:8000/api/v1/health` | 200 + `"status":"healthy"` |
| 前端 | 浏览器 `http://localhost:5173` | 页面正常加载 |

---

## 5. 部署文档导航

### 5.1 局域网双机部署 → [`LAN_DEPLOYMENT.md`](LAN_DEPLOYMENT.md)

**形态**：算力机跑算法 + 后端，演示机跑前端 Vite。

核心命令：

```bash
# 算力机一键起算法 + 后端（自动探测 LAN IP，注入 MMR_PUBLIC_BASE_URL）
./run_lan.sh

# 演示机起前端（命令行注入代理目标，零代码改动）
cd frontend
VITE_BACKEND_PROXY_TARGET=http://<算力机IP>:8000 npm run dev
```

文档涵盖：

- 算力机 / 演示机 IP 探测与互通验证
- Windows 防火墙放行 8000 端口
- 方案 A（命令行 env，推荐）/ 方案 B（修 `vite.config.ts` + `.env.local`）
- 全链路 8 项验证清单与 7 个高频 FAQ

### 5.2 演示机零环境部署 → [`CLIENT_DEPLOYMENT.md`](CLIENT_DEPLOYMENT.md)

**形态**：在 5.1 的基础上把前端从「Vite 进程」换成「nginx 托管的静态产物」，演示机只需浏览器。

核心命令：

```bash
# 1) 任意机器构建静态产物
cd frontend && npm run build      # 产出 frontend/dist/

# 2) 前端机：用项目内自包含 nginx 配置启动
sudo nginx -c $(pwd)/deploy/nginx/mmr.conf

# 3) 算力机：把 MMR_PUBLIC_BASE_URL 指向前端机，让 preview_url 也走单入口
export MMR_PUBLIC_BASE_URL="http://<前端机IP>:5173"
./run_lan.sh
```

文档涵盖：

- 配置文件放项目目录 vs 系统目录的取舍（`deploy/nginx/mmr.conf` 已就绪）
- nginx 与 Caddy 两种实现
- 单入口架构下 `/api/v1/media/preview` 的图片/视频反代说明
- 路演时算力机换 Wi-Fi 的应对策略

### 5.3 nginx 配置文件

[`deploy/nginx/mmr.conf`](deploy/nginx/mmr.conf) 是项目内自包含主配置，已写好：

- 监听 `:5173`，托管 `frontend/dist`
- SPA 路由回退 `try_files $uri $uri/ /index.html`
- `/api/` 反代到算力机后端，含超时与 `client_max_body_size 200m`

部署到目标机器时只需改两处：

| 字段 | 默认值 | 改成 |
|---|---|---|
| `root` | `/opt/mmr/dist` | 实际 `dist` 路径，例如 `<repo>/frontend/dist` |
| `proxy_pass` | `http://10.98.229.114:8000` | 算力机 IP:8000 |

---

## 6. 组件文档

每个组件单独的细节文档：

- 算法服务接口、模型权重、健康检查 → [`README/algorithm_README.md`](README/algorithm_README.md)
- 后端 API、SQLite/FAISS 设计、关键服务 → [`README/backend_README.md`](README/backend_README.md)
- 前端页面、状态管理、API 客户端 → [`README/frontend_README.md`](README/frontend_README.md)

---

## 7. 关键配置项

### 7.1 后端环境变量（前缀 `MMR_`）

| 变量 | 默认值 | 含义 |
|---|---|---|
| `MMR_PUBLIC_BASE_URL` | `http://127.0.0.1:8000` | 用于拼接 `preview_url`。**双机/演示机部署时必须改**，否则浏览器拿到的图片/视频地址会指向 127.0.0.1。详见 [`backend/app/services/object_service.py:20`](backend/app/services/object_service.py:20) |
| `MMR_ALGORITHM_MODE` | `deterministic` | 设为 `http` 时连接真实算法网关，`run_lan.sh` 已自动注入 |
| `MMR_ALGORITHM_GATEWAY_URL` | `http://127.0.0.1:18080` | 算法网关地址 |
| `MMR_CORS_ALLOW_ORIGINS` | `["*"]`（脚本注入） | CORS 白名单 |

### 7.2 前端环境变量

`frontend/.env.local`（可选，详见 [`frontend/.env.example`](frontend/.env.example)）：

| 变量 | 含义 |
|---|---|
| `VITE_BACKEND_PROXY_TARGET` | Vite dev server `/api` 反代目标。**单机**填 `http://127.0.0.1:8000`；**双机**填 `http://<算力机IP>:8000` |
| `VITE_API_BASE_URL` | axios `baseURL`。一般留空（走相对路径，由代理/nginx 处理）；若前端直连后端可填完整 URL |

> ⚠️ axios 调用已经在源码里写死 `/api/v1/xxx`，不要再把 `VITE_API_BASE_URL` 设成 `/api/v1`，否则会拼出 `/api/v1/api/v1/...`。

### 7.3 nginx 配置

见 [`deploy/nginx/mmr.conf`](deploy/nginx/mmr.conf) 与 [`CLIENT_DEPLOYMENT.md`](CLIENT_DEPLOYMENT.md) §4。

---

## 8. 常见问题

下面是跨组件、跨形态的高频问题；组件内部问题请看各 README，部署相关问题请看对应部署文档。

### Q1：后端启动报 `unsupported operand type(s) for |: 'type' 'NoneType'`

Python 3.8 不支持 `X | Y` 联合类型语法，升级到 3.9+ 即可。

### Q2：演示机访问后端超时

按顺序排查：

1. 算力机 `netstat -ano | findstr :8000`，确认是 `0.0.0.0:8000` 而非 `127.0.0.1:8000`（必须 `--host 0.0.0.0`）
2. Windows 防火墙是否放行 8000 端口（[`LAN_DEPLOYMENT.md`](LAN_DEPLOYMENT.md) §3.3 给了 PowerShell 命令）
3. 两机是否在同一网段、能否 `ping` 通

### Q3：检索结果回来了，但图片缩略图加载失败

99% 是 `MMR_PUBLIC_BASE_URL` 没设对。F12 → Network 选一张图看 `Request URL` 的 host：

- 是 `127.0.0.1:8000` → 算力机后端没注入正确的 `MMR_PUBLIC_BASE_URL`
- 是旧的 IP → 算力机换了 Wi-Fi 但后端没重启
- 是前端机 IP 但 502 → nginx 反代没生效，回到 [`CLIENT_DEPLOYMENT.md`](CLIENT_DEPLOYMENT.md) Q3

> 数据库里 `objects.preview_url` 字段虽然也存了快照，但**不影响检索接口实际返回值**——后端会用当前的 `MMR_PUBLIC_BASE_URL` 实时重拼，所以**只需重启后端**，不用清库重建。

### Q4：向量化任务一直 `pending`

- 看 [`logs/backend.log`](logs/backend.log)（双机模式下由 `run_lan.sh` 落盘）或后端终端
- 确认源路径在算力机上**真实可访问**（不是演示机的本地路径）
- 调大 `local_job_workers` 或检查算法网关是否健康

### Q5：算法网关返回 502 / `proxy error`

`algorithm/gateway/app.py` 已经设置了 `trust_env=False` 来规避系统代理干扰；如果仍然失败，临时 `unset http_proxy https_proxy all_proxy` 再启动。

### Q6：`run_lan.sh` 启动后想停止服务

```bash
kill $(cat logs/backend.pid) $(cat logs/algorithm.pid)
```

---

## 许可证

MIT License