# 演示机零环境部署指南（前端机静态托管 + 单入口反代）

本文档是 [`LAN_DEPLOYMENT.md`](LAN_DEPLOYMENT.md) 的延伸方案，目标场景：

- **演示机**：**只装浏览器**，不装 Node、不装 Python、不装任何依赖。打开一个 IP 即可使用。
- **前端机**：托管前端静态产物 + 反代 `/api` 到算力机。**不需要 Node 运行环境**（只需一个静态服务器，如 nginx / Caddy）。
- **算力机**：照旧跑算法 + 后端，命令几乎不变。

> 全文沿用 [`LAN_DEPLOYMENT.md`](LAN_DEPLOYMENT.md) 的 IP 示例：`<算力机IP>=10.98.229.114`、`<前端机IP>=10.98.229.50`，请按实际值替换。

---

## 1. 拓扑

```
[ 算力机 Windows ]               [ 前端机 ]                  [ 演示机 ]
 10.98.229.114                    10.98.229.50                浏览器
  ├─ 算法 18080-18083              ├─ nginx :5173 (静态)        │
  └─ 后端 0.0.0.0:8000  ◀──────────┤  └─ /api → 算力机:8000     │
                                   └─ /api/v1/media/preview ◀──┘
                                       (图片/视频也走同一入口)
```

核心思想：演示机**只**访问 `http://<前端机IP>:5173`，所有 API 调用与媒体预览都通过前端机的 nginx 反代到算力机后端，演示机**不直接接触算力机**。

---

## 2. 为什么源码可以零改动

经过代码确认：

| 关注点 | 现状 | 结论 |
|---|---|---|
| axios `baseURL` | [`frontend/src/api/client.ts`](frontend/src/api/client.ts:4) 默认 `'/'`，所有请求走 `/api/v1/xxx` 同源相对路径 | ✅ 静态部署后浏览器自动同源访问当前域名 |
| 前端路由 | Vue Router 默认 hash 或 history（需 SPA fallback） | ✅ nginx `try_files $uri /index.html` 解决 |
| 图片/视频预览 | 后端 [`backend/app/services/object_service.py:20`](backend/app/services/object_service.py:20) 把 preview 拼成 `{public_base_url}/api/v1/media/preview?...`，**统一在 `/api/v1` 路径下**（见 [`backend/app/api/v1/media.py:12`](backend/app/api/v1/media.py:12)） | ✅ 反代 `/api` 一并覆盖，不需要额外路由 |
| 后端绑定 | `uvicorn --host 0.0.0.0 --port 8000` | ✅ 与 [`LAN_DEPLOYMENT.md`](LAN_DEPLOYMENT.md) 完全一致 |

唯一需要的"运行期变化"：把 `MMR_PUBLIC_BASE_URL` 改成 **前端机** 的对外地址，让浏览器在拿到 `preview_url` 时仍指向 `http://<前端机IP>:5173`，从而保持单入口。

---

## 3. 一次性准备：构建前端静态产物

可以在**任何**有 Node 的机器上做（比如开发机），产物 `frontend/dist/` 拷到前端机即可。

```bash
cd frontend
npm install     # 首次
npm run build   # 产出 frontend/dist/
```

> 不需要任何 `.env`：构建产物里 axios 会走相对路径，不会硬编码任何 IP。

把整个 `frontend/dist/` 目录拷到前端机，例如：

```
/opt/mmr/dist/
├── index.html
├── assets/
└── ...
```

---

## 4. 前端机：用 nginx 托管 + 反代

### 4.1 安装 nginx

- macOS：`brew install nginx`
- Ubuntu / Debian：`sudo apt install nginx`
- Windows：[nginx.org/en/download.html](https://nginx.org/en/download.html) 下载解压即用

### 4.2 配置文件放在哪？

**两种位置都可以，强烈推荐放在项目目录下**（配置随代码一起进 git，部署到任何机器都能复用，不污染系统）：

| 方式 | 路径示例 | 适用场景 |
|---|---|---|
| **A. 项目目录（推荐）** | `MultiRetrievalSystem/deploy/nginx/mmr.conf` | 团队协作 / 多机复用 / 想进 git |
| B. nginx 软件目录 | Linux: `/etc/nginx/conf.d/mmr.conf`<br/>Windows: `nginx/conf/conf.d/mmr.conf` | 单机长期运行、习惯系统级管理 |

> 两种方式效果完全一样，nginx 不关心配置文件路径，关心的是「启动时它读到了哪个文件」。区别只在你**怎么告诉 nginx 去读它**。

#### 方式 A：放项目目录（推荐）

1. 在项目根目录建一个文件 `deploy/nginx/mmr.conf`，写入下方 server 块内容。
2. 启动 nginx 时用 `-c` 参数指定**绝对路径**：

   ```bash
   # Linux / macOS
   sudo nginx -c /Users/caoqixuan.1/code/MultiRetrievalSystem/deploy/nginx/mmr.conf
   sudo nginx -s reload -c /Users/caoqixuan.1/code/MultiRetrievalSystem/deploy/nginx/mmr.conf

   # Windows（在 nginx 解压目录里执行）
   cd deploy/nginx
   .\nginx.exe -c conf/nginx.conf 
   ```

   > ⚠️ `-c` 必须传**绝对路径**，相对路径 nginx 会按它自己的 prefix 解析，容易出错。

3. **注意**：`nginx -c` 指定的文件需要是「主配置文件」，所以下面的 server 块要外面包一层 `events` 和 `http`：

   ```nginx
   # deploy/nginx/mmr.conf —— 项目目录方式（自包含主配置）
   worker_processes  1;
   events { worker_connections 1024; }

   http {
       include       mime.types;       # 让 nginx 正确识别 css/js 的 Content-Type
       default_type  application/octet-stream;
       sendfile      on;

       server {
           listen       5173;
           server_name  _;

           root   /opt/mmr/dist;       # 改成你的 dist 实际路径，下文同
           index  index.html;

           location / {
               try_files $uri $uri/ /index.html;
           }

           location /api/ {
               proxy_pass         http://10.98.229.114:8000;
               proxy_http_version 1.1;
               proxy_set_header   Host              $host;
               proxy_set_header   X-Real-IP         $remote_addr;
               proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
               proxy_set_header   X-Forwarded-Proto $scheme;
               proxy_read_timeout 300s;
               proxy_send_timeout 300s;
               client_max_body_size 200m;
           }
       }
   }
   ```

   > 提示：`include mime.types;` 里的 `mime.types` 文件在 nginx 安装目录（如 `/usr/local/etc/nginx/mime.types`）。如果启动时报「mime.types 找不到」，把它改成绝对路径，例如 `include /usr/local/etc/nginx/mime.types;`（macOS Homebrew）或 `include /etc/nginx/mime.types;`（Ubuntu）。

4. **`dist` 也可以放项目目录**，让整个部署都自包含：

   ```nginx
   root /Users/caoqixuan.1/code/MultiRetrievalSystem/frontend/dist;
   ```

   构建完直接 `nginx -s reload` 即可生效。

#### 方式 B：放 nginx 软件目录（系统级）

```nginx
server {
    listen       5173;
    server_name  _;

    # 静态站点根目录
    root   /opt/mmr/dist;
    index  index.html;

    # SPA 路由回退：刷新 /search 等子路径不会 404
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 关键：把 /api 全部反代到算力机后端
    # 包括 /api/v1/health、/api/v1/stores、/api/v1/search/...
    # 也包括 /api/v1/media/preview（图片/视频）
    location /api/ {
        proxy_pass         http://10.98.229.114:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # 上传/检索可能较慢，放宽超时
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        client_max_body_size 200m;
    }
}
```

把上面这段 `server { ... }` 保存到 `/etc/nginx/conf.d/mmr.conf`（Linux）或 `<nginx安装目录>/conf/conf.d/mmr.conf`（Windows，需要在 `nginx.conf` 的 `http` 块里有 `include conf.d/*.conf;`，主流安装包默认都有）。

启动 / 重载（**方式 B 用默认主配置即可，不加 `-c`**）：

```bash
sudo nginx -t              # 语法检查
sudo nginx                 # 启动
sudo nginx -s reload       # 修改后热重载
```

> 方式 A 启动命令记得带 `-c` 绝对路径；方式 B 不带 `-c`，nginx 自动读默认 `nginx.conf` 并 include 你新加的 `mmr.conf`。

### 4.3 不想装 nginx？Caddy 一行搞定

新建 `Caddyfile`：

```caddyfile
:5173 {
    root * /opt/mmr/dist
    try_files {path} /index.html
    file_server

    reverse_proxy /api/* 10.98.229.114:8000
}
```

启动：`caddy run --config Caddyfile`

### 4.4 防火墙放行

- macOS：默认无需操作
- Ubuntu：`sudo ufw allow 5173/tcp`
- Windows：
  ```powershell
  New-NetFirewallRule -DisplayName "MMR-Frontend" -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow
  ```

---

## 5. 算力机：唯一变化是 `MMR_PUBLIC_BASE_URL`

把它指向**前端机**，确保 preview_url 也从前端机入口出来：

**PowerShell：**

```powershell
cd backend
$env:MMR_PUBLIC_BASE_URL="http://10.98.229.50:5173"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**CMD：**

```cmd
cd backend
set MMR_PUBLIC_BASE_URL=http://10.98.229.50:5173
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> 算法服务启动命令完全不变：`python launcher/run_all.py`。

防火墙：算力机 8000 端口**只需对前端机可达**（演示机不再直连），更安全。如果之前已按 [`LAN_DEPLOYMENT.md`](LAN_DEPLOYMENT.md:84) 放行过 8000，无需改动。

---

## 6. 演示机：什么都不装

直接浏览器打开：

```
http://10.98.229.50:5173
```

完事。无 Node、无 npm、无 `.env.local`、无源码。

---

## 7. 验证清单

| # | 位置 | 命令 / 操作 | 期望结果 |
|---|---|---|---|
| 1 | 算力机 | `curl http://127.0.0.1:8000/api/v1/health` | 200 + `"status":"healthy"` |
| 2 | 前端机 | `curl http://10.98.229.114:8000/api/v1/health` | 200（前端机能直连算力机后端） |
| 3 | 前端机 | `curl http://127.0.0.1:5173/` | 返回 `index.html` 内容 |
| 4 | 前端机 | `curl http://127.0.0.1:5173/api/v1/health` | 200，证明反代生效 |
| 5 | 演示机 | `curl http://10.98.229.50:5173/api/v1/health` | 200 |
| 6 | 演示机 | 浏览器打开 `http://10.98.229.50:5173`，F12 Network | `/api/v1/health`、`/api/v1/stores` 均 200 |
| 7 | 演示机 | 检索后查看图片 `Request URL` | host 是 `10.98.229.50:5173`，不是算力机 IP |
| 8 | 演示机 | 上传查询 / 触发 T2I / T2V / I2I | 结果返回，预览图正常加载 |

---

## 8. 与方案 A / B（[`LAN_DEPLOYMENT.md`](LAN_DEPLOYMENT.md)）的对比

| 维度 | 方案 A（命令行 env） | 方案 B（修 vite.config） | **方案 C（本文，静态托管）** |
|---|---|---|---|
| 演示机需要 Node | ✅ 需要 | ✅ 需要 | ❌ 不需要 |
| 演示机需要源码 | ✅ 需要 | ✅ 需要 | ❌ 不需要 |
| 演示机访问方式 | `localhost:5173` | `localhost:5173` | `http://<前端机IP>:5173` |
| 多人同时演示 | 每人一台都得装环境 | 同左 | ✅ 一台前端机服务所有人 |
| 前端代码改动 | 0 | 改 1 处 | 0 |
| 启动复杂度 | 中（要记 env） | 低 | 低（nginx 启动后常驻） |
| 适用场景 | 单人开发调试 | 单人长期演示 | **多人路演 / 客户演示** |

---

## 9. 常见问题

### Q1：演示机打开 `http://<前端机IP>:5173` 是空白页

- F12 Console 看是不是 JS 加载 404：检查 `frontend/dist/assets/` 是否完整拷贝
- 检查 nginx `root` 路径是否正确，`nginx -t` 看语法
- 强刷一下 `Cmd+Shift+R` / `Ctrl+F5`

### Q2：页面能开，但 API 全部 502 / 504

- 在前端机 `curl http://10.98.229.114:8000/api/v1/health` 看是否能直连算力机后端
- 不通：算力机 uvicorn 没加 `--host 0.0.0.0`，或 Windows 防火墙没放行 8000
- 通但 502：检查 nginx 配置里 `proxy_pass` 的 IP 是否写对、有没有少 `http://` 前缀

### Q3：检索返回了，但图片是 404 / 跨域错误

- F12 Network 选一张图，看 `Request URL`：
  - 如果是 `http://10.98.229.114:8000/api/v1/media/preview?...` → 算力机端 `MMR_PUBLIC_BASE_URL` 没改，仍是老值，**重启后端**并设成 `http://<前端机IP>:5173`
  - 如果是 `http://10.98.229.50:5173/api/v1/media/preview?...` 但 502 → 反代有问题，回到 Q2
- nginx 的 `location /api/` 要确保**结尾带斜杠**且 `proxy_pass` 也对应正确（本文配置已验证）

### Q4：演示路演时算力机换了 Wi-Fi、IP 变了

只需在前端机改一处：nginx 配置里的 `proxy_pass` IP，然后 `nginx -s reload`。
算力机重启后端时 `MMR_PUBLIC_BASE_URL` 不用变（仍是前端机 IP），这是单入口架构的好处。

### Q5：能不能跑在 80 端口让用户连端口都不用敲？

可以。把 nginx 的 `listen 5173` 改成 `listen 80`，防火墙同步放行。Linux 下 80 端口需要 root，建议用 `sudo` 启动 nginx 或用 `setcap`。

### Q6：可以 HTTPS 吗？

可以，但需要证书。最简单是用 Caddy，把 `:5173` 改成域名（如 `mmr.example.lan`），Caddy 会自动签证书。局域网无公网域名时可以自签。一般演示场景 HTTP 已足够。

---

## 10. 一键部署速查（前端机）

假设静态产物已放到 `/opt/mmr/dist/`，nginx 已装：

```bash
# 1. 写配置
sudo tee /etc/nginx/conf.d/mmr.conf > /dev/null <<'EOF'
server {
    listen 5173;
    server_name _;
    root /opt/mmr/dist;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
    location /api/ {
        proxy_pass http://10.98.229.114:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 200m;
    }
}
EOF

# 2. 启动
sudo nginx -t && sudo nginx -s reload || sudo nginx

# 3. 自检
curl -I http://127.0.0.1:5173/
curl    http://127.0.0.1:5173/api/v1/health
```

算力机：

```powershell
cd algorithm; python launcher/run_all.py     # 终端 1

cd backend                                    # 终端 2
$env:MMR_PUBLIC_BASE_URL="http://10.98.229.50:5173"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

演示机：浏览器打开 `http://10.98.229.50:5173` —— 完成。

---

## 11. 改动清单总结

| 项目 | 改动 | 性质 |
|---|---|---|
| `frontend/` 源码 | **0 改动** | ✅ |
| `frontend/dist/` | `npm run build` 产出后拷到前端机 | 构建产物 |
| 前端机 nginx 配置 | 新增 1 个 server 块 | 部署配置 |
| 算力机启动命令 | `MMR_PUBLIC_BASE_URL` 改成前端机地址 | 环境变量 |
| 算力机 / 后端代码 | **0 改动** | ✅ |
| 演示机 | **什么都不装** | ✅ |

—— 全程**零代码修改**，只动部署配置与一个环境变量。