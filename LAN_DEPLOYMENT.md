# 局域网双机部署指南（演示机 + 算力机）

本文档说明在**局域网演示场景**下，如何把 MultiRetrievalSystem 部署到两台机器：

- **算力机（Windows，有 GPU）**：运行算法服务 + 后端服务
- **演示机（Mac / 其他，无 GPU）**：只运行前端，浏览器访问

> 算法服务代码、后端服务代码**均无需修改**；前端可以选择是否修改 `vite.config.ts`。下文给出"零代码改动"和"一次性永久修复"两种方案。

---

## 1. 拓扑与端口规划

```
[ 算力机 Windows ]                            [ 演示机 ]
  IP: <算力机IP> 例如 10.98.229.114             IP: <演示机IP> 例如 10.98.229.x
  ├─ 算法网关       0.0.0.0:18080              └─ 前端 (Vite)  :5173
  ├─ I2I 服务       0.0.0.0:18081                  └── 浏览器
  ├─ T2I 服务       0.0.0.0:18082
  ├─ T2V 服务       0.0.0.0:18083
  └─ 后端 (FastAPI) 0.0.0.0:8000  ←──────── 前端 /api 代理
        │
        └── 后端通过 127.0.0.1:18080 调用算法网关
```

| 服务 | 监听 | 是否需暴露到局域网 | 说明 |
|---|---|---|---|
| 算法网关 | `0.0.0.0:18080` | 否（仅本机调用） | 后端走 `127.0.0.1:18080` 即可 |
| I2I / T2I / T2V | `0.0.0.0:18081-18083` | 否 | 仅供网关内部转发 |
| **后端** | **`0.0.0.0:8000`** | **是** | 演示机前端通过此端口访问 |
| 前端 Vite | `0.0.0.0:5173` | 是 | 浏览器访问入口 |

> 全文以 **`<算力机IP>` = `10.98.229.114`** 为例，请按你实际值替换。

---

## 2. 怎么查看本机 IP

### Windows（算力机）

```powershell
ipconfig
```
看「以太网适配器」或「无线局域网适配器 WLAN」下的 **IPv4 地址**。一般以 `192.168.x.x` / `10.x.x.x` / `172.16~31.x.x` 开头。

### macOS / Linux（演示机）

```bash
ipconfig getifaddr en0          # Wi-Fi
ipconfig getifaddr en1          # 有线
# 或一条龙
ifconfig | grep "inet " | grep -v 127.0.0.1
```

### 验证两机互通

在演示机上：

```bash
ping -c 3 <算力机IP>
```

不通可能是：不在同一网段、Windows 防火墙拦了 ICMP（不影响 HTTP）、公司网络客户端隔离。

---

## 3. 算力机（Windows）启动步骤

### 3.1 启动算法服务（命令完全不变）

```powershell
cd algorithm
python launcher/run_all.py
```

启动器会拉起 4 个服务，全部绑定 `0.0.0.0`，详见 [`algorithm/launcher/run_all.py`](algorithm/launcher/run_all.py)。

### 3.2 启动后端（关键改动）

> ⚠️ 与原 `run.sh` 不同：必须加 `--host 0.0.0.0`，否则 uvicorn 默认只监听 `127.0.0.1`，演示机无法访问。

**PowerShell：**

```powershell
cd backend
$env:MMR_PUBLIC_BASE_URL="http://10.98.229.114:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**CMD：**

```cmd
cd backend
set MMR_PUBLIC_BASE_URL=http://10.98.229.114:8000
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

参数说明：

- `--host 0.0.0.0`：监听所有网口，使后端可被局域网访问。
- `MMR_PUBLIC_BASE_URL`：被 [`backend/app/core/config.py`](backend/app/core/config.py) 和 [`backend/app/services/object_service.py`](backend/app/services/object_service.py) 用于拼接上传文件的预览 URL。如果不设置，前端在演示机会拿到 `http://127.0.0.1:8000/...`，导致图片预览失败（浏览器会去访问演示机本地）。
- 生产演示**不要加 `--reload`**，更稳定。

### 3.3 放行 Windows 防火墙

首次启动 uvicorn 时，Windows 一般会弹窗，勾选「专用网络/工作网络」即可。

也可手动添加规则（管理员 PowerShell）：

```powershell
New-NetFirewallRule -DisplayName "MMR-Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

确认监听情况：

```powershell
netstat -ano | findstr :8000
# 应看到 TCP    0.0.0.0:8000  ...  LISTENING    <pid>
```

### 3.4 算力机本地自检

```powershell
curl http://127.0.0.1:18080/health
curl http://127.0.0.1:8000/api/v1/health
```

均返回 200 即可。

---

## 4. 演示机启动步骤（Mac / Linux）

### 4.1 安装依赖（首次）

```bash
cd frontend
npm install
```

### 4.2 验证能访问算力机后端

```bash
curl -v --max-time 5 http://10.98.229.114:8000/api/v1/health
```

返回 `200 OK` 且 body 含 `"status":"healthy"` 即可。如果失败，回到第 3.3 节排查防火墙。

### 4.3 启动前端（**推荐：方案 A，零代码改动**）

直接在命令行传环境变量启动 vite：

```bash
cd frontend
VITE_BACKEND_PROXY_TARGET=http://10.98.229.114:8000 npm run dev
```

> 这是经过实战验证的写法。命令行 env 会被注入 `process.env`，[`frontend/vite.config.ts`](../frontend/vite.config.ts:5) 会通过 `process.env.VITE_BACKEND_PROXY_TARGET` 读到代理目标。

可选：每次都不想敲，写个 shell alias（`~/.zshrc`）：

```bash
alias mmr-fe='VITE_BACKEND_PROXY_TARGET=http://10.98.229.114:8000 npm run dev'
# source ~/.zshrc 后，frontend 目录下直接 mmr-fe 即可
```

> ⚠️ 使用方案 A 时**不要**依赖 `.env.local`，详见 4.5 节"为什么 `.env.local` 失效"。

### 4.4 浏览器访问

```
http://localhost:5173
```

打开后按 `F12` → **Network** 标签，应能看到：

| 请求 URL | 状态 |
|---|---|
| `localhost:5173/api/v1/health` | 200 |
| `localhost:5173/api/v1/stores` | 200 |

vite 终端**不应**再有 `http proxy error: ... ECONNREFUSED 127.0.0.1:8000` 的报错。

### 4.5 为什么 `.env.local` 失效（背景说明）

[`frontend/vite.config.ts`](../frontend/vite.config.ts:5) 当前用的是：

```ts
const backendTarget = process.env.VITE_BACKEND_PROXY_TARGET || 'http://127.0.0.1:8000'
```

但 vite 默认**不会**把 `.env.local` 自动注入 `process.env`（需要显式调用 `loadEnv()`）。所以即使 `frontend/.env.local` 写对了，仍会回落到默认值 `127.0.0.1:8000`，表现为：

```
[vite] http proxy error: /api/v1/health
Error: connect ECONNREFUSED 127.0.0.1:8000
```

方案 A（命令行传 env）能完全绕开这个坑，因此作为推荐方案。

---

## 5. 方案 B：永久修复 `vite.config.ts`（可选，一次性改好）

如果不想每次启动都敲 `VITE_BACKEND_PROXY_TARGET=...`，可以一次性改 [`frontend/vite.config.ts`](frontend/vite.config.ts) 让它正确加载 `.env.local`：

```ts
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget =
    env.VITE_BACKEND_PROXY_TARGET ||
    process.env.VITE_BACKEND_PROXY_TARGET ||
    'http://127.0.0.1:8000'

  // 启动时打印实际目标，方便排查
  console.log(`[vite] backend proxy target = ${backendTarget}`)

  return {
    plugins: [vue()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
```

然后在 `frontend/.env.local`（与 `vite.config.ts` 同级）写：

```env
VITE_BACKEND_PROXY_TARGET=http://10.98.229.114:8000
```

⚠️ **不要**再额外设置 `VITE_API_BASE_URL=/api/v1`：前端代码（如 [`frontend/src/api/health.ts`](frontend/src/api/health.ts)、[`frontend/src/api/stores.ts`](frontend/src/api/stores.ts)）已经在每个调用里写死了 `/api/v1/xxx`，axios 的 `baseURL` 留空即可；再加前缀会拼成 `/api/v1/api/v1/health` 导致代理报错。

修改后用普通命令启动即可：

```bash
npm run dev
```

启动日志中会看到 `[vite] backend proxy target = http://10.98.229.114:8000`，眼见为实。

---

## 6. 全链路验证清单

依次完成以下检查，全部通过则部署成功：

| # | 位置 | 命令 / 操作 | 期望结果 |
|---|---|---|---|
| 1 | 算力机 | `curl http://127.0.0.1:18080/health` | 200 OK |
| 2 | 算力机 | `curl http://127.0.0.1:8000/api/v1/health` | 200 OK + `"status":"healthy"` |
| 3 | 算力机 | `netstat -ano \| findstr :8000` | 包含 `0.0.0.0:8000 ... LISTENING` |
| 4 | 演示机 | `curl http://10.98.229.114:8000/api/v1/health` | 200 OK |
| 5 | 演示机 | 启动 vite 后终端无 `ECONNREFUSED 127.0.0.1:8000` 报错 | 干净 |
| 6 | 演示机 | 浏览器 `http://localhost:5173`，F12 看 `/api/v1/health` | 200 OK，路径**单层** `/api/v1/health` |
| 7 | 演示机 | 「资源管理」页能看到算力机的检索库 | 列表非空 |
| 8 | 演示机 | 执行 T2V / T2I / I2I 检索 | 结果返回，预览图能加载 |

---

## 7. 常见问题

### Q1：演示机访问 `http://<算力机IP>:8000/api/v1/health` 超时

- 在算力机执行 `netstat -ano | findstr :8000`，确认是 `0.0.0.0:8000` 而非 `127.0.0.1:8000`；若是后者，重启时加 `--host 0.0.0.0`。
- 检查 Windows 防火墙是否放行 8000 端口（见 3.3 节）。
- 临时关防火墙做二分：`Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False`，能通就 100% 是防火墙问题，加规则后再开回来。
- 检查两台机器是否在同一网段，能否互相 `ping`。

### Q2：vite 报 `http proxy error: /api/v1/health  ECONNREFUSED 127.0.0.1:8000`

- 用了 `npm run dev` 但没在命令前加 `VITE_BACKEND_PROXY_TARGET=...`：改用方案 A 的写法 `VITE_BACKEND_PROXY_TARGET=http://10.98.229.114:8000 npm run dev`，或采用方案 B 修 `vite.config.ts`。
- 已采用方案 B 但仍报错：检查 `.env.local` 是否在 `frontend/` 目录、文件名是否正确（不是 `.env.local.txt`）、改完是否重启了 `npm run dev`（vite 只在启动时读一次 env）。

### Q3：vite 报 `http proxy error: /api/v1/api/v1/health`（路径出现两层 `/api/v1`）

- 你设置了 `VITE_API_BASE_URL=/api/v1`。前端代码已经写死 `/api/v1/xxx`，axios 不需要再加前缀。删除该变量并重启 vite。

### Q4：检索结果返回了，但图片/视频缩略图加载失败

**根因**：图片 src 里 host 是错的（如旧 IP `6.8.147.66`），说明后端进程仍在用历史的 `MMR_PUBLIC_BASE_URL` 拼接 preview_url。

后端检索接口会**实时**根据当前的 `MMR_PUBLIC_BASE_URL` 拼出 `preview_url` 返回给前端（见 [`backend/app/services/search_service.py:127`](../backend/app/services/search_service.py:127) 调用的 [`object_service.build_preview_url`](../backend/app/services/object_service.py:20)），所以**只需用正确 IP 重启后端**即可，**不用清数据库、不用重建库、不用改代码**。

```powershell
# 算力机：Ctrl+C 停掉当前后端，然后用真实 IP 重启
cd backend
$env:MMR_PUBLIC_BASE_URL="http://10.98.229.114:8000"   # 替换为算力机真实 IP
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

演示机浏览器 `Cmd+Shift+R`（Windows 是 `Ctrl+F5`）硬刷新页面，图片即可加载。F12 → Network → 选一张图片，看 `Request URL` 的 host 是不是新 IP。

> 💡 数据库 `objects.preview_url` 字段里的旧 IP 只是历史快照，不会影响检索接口实际返回值，**不需要清理**。
>
> 💡 每次算力机换 Wi-Fi/IP，重启后端时把 `MMR_PUBLIC_BASE_URL` 同步更新即可。如果嫌麻烦，可以考虑把 [`backend/app/services/object_service.py:20`](../backend/app/services/object_service.py:20) 改成 `public_base_url` 为空时返回相对路径（与 IP 解耦）——本指南遵循"零代码改动"原则未采用。

### Q5：业务接口返回 500（健康检查 200 但其他接口报错）

- `/api/v1/health` 返回 `"algorithm":true` 只代表算法网关 18080 端口存活，**不代表模型加载成功**。500 真正的 Traceback 在算力机 uvicorn 终端窗口里。
- 排查顺序：
  1. 浏览器 F12 → Network，看 500 请求的 URL 和 Response body
  2. 切到算力机 uvicorn 终端找 `ERROR: Exception in ASGI application` 后面的 Traceback
  3. 单独验证三个算法子服务：`curl http://127.0.0.1:18081/health`、`18082`、`18083`

### Q6：前端控制台报 CORS 错误

- 不应该出现。Vite dev server 通过 `/api` 代理转发，浏览器看到的请求源是 `http://localhost:5173` → 同源。如果出现，说明前端某处直接访问了 `http://10.98.229.114:8000`（绕过了代理），检查是不是改 axios `baseURL` 时填了完整 URL。

### Q7：能不能演示机直接访问算法网关？

- 不需要、也不建议。当前架构里所有算法调用都由后端发起，前端只跟后端打交道。算法服务即使绑了 `0.0.0.0`，也只供算力机本机的后端调用。

---

## 8. 与原 `run.sh` 的差异速查

| 步骤 | 原 `run.sh`（单机） | 局域网演示版（双机） |
|---|---|---|
| 算法 | `python launcher/run_all.py` | 同上（不变） |
| 后端 | `uvicorn app.main:app --reload` | `uvicorn app.main:app --host 0.0.0.0 --port 8000`，配合 `MMR_PUBLIC_BASE_URL=http://<算力机IP>:8000` |
| 前端 | `npm run dev` | `VITE_BACKEND_PROXY_TARGET=http://<算力机IP>:8000 npm run dev`（方案 A）<br/>或修 `vite.config.ts` 后用 `.env.local`（方案 B） |
| 机器分工 | 全部在一台机 | 算力机跑算法+后端，演示机只跑前端 |

---

## 9. 实战示例（已验证）

以下是一次成功部署的完整命令记录，IP 仅作示例：

**算力机 Windows：**

```powershell
# 终端 1
cd algorithm
python launcher/run_all.py

# 终端 2
cd backend
$env:MMR_PUBLIC_BASE_URL="http://10.98.229.114:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 终端 3（首次部署）：放行防火墙
New-NetFirewallRule -DisplayName "MMR-Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

**演示机 Mac：**

```bash
# 一次性自检：直接 curl 算力机后端
curl http://10.98.229.114:8000/api/v1/health
# → {"status":"healthy","services":{"api":true,"faiss":true,"minio":true,"algorithm":true}}

# 启动前端（方案 A）
cd frontend
VITE_BACKEND_PROXY_TARGET=http://10.98.229.114:8000 npm run dev

# 浏览器打开 http://localhost:5173 即可
```

---

> 本指南仅涉及启动命令与环境变量；如采用方案 B，会修改 [`frontend/vite.config.ts`](frontend/vite.config.ts) 一处，其他源码无需改动。