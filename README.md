# MultiRetrievalSystem 多模态检索系统

> 基于 Vue 3 + FastAPI + 自研算法栈的多模态检索平台，支持 **文搜视频 (T2V)**、**文搜图 (T2I)**、**图搜图 (I2I)** 三类场景。

---

## 目录

1. [架构与端口](#1-架构与端口)
2. [仓库结构](#2-仓库结构)
3. [快速开始](#3-快速开始)
4. [部署文档](#4-部署文档)
5. [组件文档](#5-组件文档)
6. [常见问题](#6-常见问题)
7. [许可证](#7-许可证)

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

| 服务 | 默认监听 | 说明 |
|---|---|---|
| 前端 (Vite dev) | `0.0.0.0:5173` | 开发模式 |
| 后端 FastAPI | `0.0.0.0:8000` | 前端 `/api` 反代目标 |
| 算法网关 | `0.0.0.0:18080` | 仅供本机后端调用 |
| I2I / T2I / T2V | `:18081 / :18082 / :18083` | 网关内部转发 |

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
├── deploy/                    # 部署文档（见 feature/deploy 分支）
├── data/Query.txt             # 演示用查询样例
├── run.sh                     # 单机开发启动脚本（参考用）
└── README.md                  # 本文件
```

---

## 3. 快速开始

### 3.1 环境要求

- Python ≥ 3.9（注意：3.8 不支持 `X | Y` 联合类型）
- Node.js ≥ 16
- FFmpeg（视频检索使用，已附带在 backend 目录）
- GPU 可选；无 GPU 时算法服务会回落到 CPU，速度较慢

### 3.2 安装依赖

```bash
# 后端 + 算法
pip install -r requirements.txt

# 前端
cd frontend && npm install && cd ..
```

### 3.3 启动（三个终端）

```bash
# 终端 1：算法网关 + I2I/T2I/T2V
cd algorithm && python launcher/run_all.py

# 终端 2：后端
cd backend && uvicorn app.main:app --reload

# 终端 3：前端
cd frontend && npm run dev
```

### 3.4 验证

| 检查项 | 命令 / 操作 | 期望 |
|---|---|---|
| 算法网关 | `curl http://127.0.0.1:18080/health` | 200 |
| 后端 | `curl http://127.0.0.1:8000/api/v1/health` | 200 + `"status":"healthy"` |
| 前端 | 浏览器 `http://localhost:5173` | 页面正常加载 |

---

## 4. 部署文档

> 当前 `master` 分支包含基础功能代码。如需部署到生产环境或多机环境，请参考 `feature/deploy` 分支的相关文档。

### 4.1 部署文档概览

`feature/deploy` 分支提供了完整的部署文档体系：

| 部署场景 | 文档 | 说明 |
|---|---|---|
| 单机开发 | [README.md](README.md) | 当前文档 |
| 局域网双机 | [LAN_DEPLOYMENT.md](LAN_DEPLOYMENT.md) | 算力机 + 演示机部署 |
| 静态托管演示 | [CLIENT_DEPLOYMENT.md](CLIENT_DEPLOYMENT.md) | 演示机零环境部署 |

### 4.2 部署脚本

- [`run.sh`](run.sh) - 单机开发启动脚本（参考用）
- [`run_lan.sh`](run_lan.sh) - 算力机一键启动脚本（feature/deploy 分支）

### 4.3 部署配置

- [`deploy/nginx/mmr.conf`](deploy/nginx/mmr.conf) - nginx 静态托管配置（feature/deploy 分支）

---

## 5. 组件文档

每个组件均有完整的独立文档，涵盖架构概述、快速上手、配置说明、接口规范、常见问题及集成说明：

### 算法服务文档 → [`README/algorithm_README.md`](README/algorithm_README.md)

涵盖：服务架构（Gateway + 3 个 Worker）、模型权重配置、启动方式、编码接口规范、使用示例（I2I / T2I / T2V）、常见启动问题（HydraConfig、argparse 冲突、CUDA 设备不一致等）、与后端的集成方式。

### 后端服务文档 → [`README/backend_README.md`](README/backend_README.md)

涵盖：核心职责与架构、全量环境变量配置（`MMR_*` 前缀）、所有 HTTP 接口详细说明（请求/响应格式）、建库流程（普通 Folder 建库、LongVideo 切片/抽帧建库）、SQLite/FAISS/托管资源的数据存储设计、算法服务集成说明、常见问题（preview_url 失效、任务 pending、FFmpeg 报错等）。

### 前端应用文档 → [`README/frontend_README.md`](README/frontend_README.md)

涵盖：技术栈（Vue 3 + TypeScript + Pinia + Element Plus）、三个页面的功能说明（检索 / 资源准备 / 资源管理）、后端接口依赖总览、请求格式说明（含以图搜图和 LongVideo）、Pinia 状态管理结构、ViewModel 设计、枚举中文映射表、媒体预览链路（图片 / 视频 / 长视频片段）、生产部署 nginx 参考配置。

---

## 6. 常见问题

### Q1：后端启动报 `unsupported operand type(s) for |: 'type' 'NoneType'`

Python 3.8 不支持 `X | Y` 联合类型语法，升级到 3.9+ 即可。

### Q2：检索结果回来了，但图片缩略图加载失败

99% 是 `MMR_PUBLIC_BASE_URL` 没设对。F12 → Network 选一张图看 `Request URL` 的 host：

- 是 `127.0.0.1:8000` → 算力机后端没注入正确的 `MMR_PUBLIC_BASE_URL`
- 是旧的 IP → 算力机换了 Wi-Fi 但后端没重启
- 是前端机 IP 但 502 → nginx 反代没生效

> 数据库里 `objects.preview_url` 字段虽然也存了快照，但**不影响检索接口实际返回值**——后端会用当前的 `MMR_PUBLIC_BASE_URL` 实时重拼，所以**只需重启后端**，不用清库重建。

### Q3：向量化任务一直 `pending`

- 看 [`logs/backend.log`](logs/backend.log)（双机模式下由 `run_lan.sh` 落盘）或后端终端
- 确认源路径在算力机上**真实可访问**（不是演示机的本地路径）
- 调大 `local_job_workers` 或检查算法网关是否健康

---

## 7. 许可证

MIT License