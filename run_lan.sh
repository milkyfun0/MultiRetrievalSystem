#!/usr/bin/env bash
# 局域网一键启动脚本：在 LAN 服务器上启动 [算法 4 进程] + [后端]
# 演示机不需要执行本脚本，演示机只跑前端 (npm run dev)。

set -e

# ---------- 探测本机 LAN IP ----------
detect_ip() {
    if command -v hostname >/dev/null 2>&1; then
        # Linux: hostname -I 取第一个非环回 IP
        ip=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [ -n "$ip" ]; then
            echo "$ip"; return
        fi
    fi
    # macOS / 兜底
    python3 - <<'PY'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(("8.8.8.8", 80))
    print(s.getsockname()[0])
except Exception:
    print("127.0.0.1")
finally:
    s.close()
PY
}

LAN_IP=$(detect_ip)
echo "[run_lan] detected LAN IP: ${LAN_IP}"

# ---------- 注入后端环境变量 ----------
export MMR_PUBLIC_BASE_URL="http://${LAN_IP}:8000"
export MMR_ALGORITHM_MODE="http"
export MMR_ALGORITHM_GATEWAY_URL="http://127.0.0.1:18080"
export MMR_CORS_ALLOW_ORIGINS='["*"]'

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "${ROOT_DIR}/logs"

# ---------- 1) 启动算法 (gateway + i2i/t2i/t2v) ----------
( cd "${ROOT_DIR}/algorithm" \
  && nohup python launcher/run_all.py > "${ROOT_DIR}/logs/algorithm.log" 2>&1 & echo $! > "${ROOT_DIR}/logs/algorithm.pid" )
echo "[run_lan] algorithm started, pid=$(cat ${ROOT_DIR}/logs/algorithm.pid), log=logs/algorithm.log"

# ---------- 2) 启动后端 ----------
( cd "${ROOT_DIR}/backend" \
  && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "${ROOT_DIR}/logs/backend.log" 2>&1 & echo $! > "${ROOT_DIR}/logs/backend.pid" )
echo "[run_lan] backend  started, pid=$(cat ${ROOT_DIR}/logs/backend.pid), log=logs/backend.log"

echo ""
echo "[run_lan] DONE."
echo "  Backend  : http://${LAN_IP}:8000   (docs: /docs)"
echo "  Algorithm: http://${LAN_IP}:18080  (health: /health)"
echo "  演示机请在 frontend/.env.local 设置:"
echo "    VITE_BACKEND_PROXY_TARGET=http://${LAN_IP}:8000"
echo "    VITE_API_BASE_URL=http://${LAN_IP}:8000"
echo ""
echo "  停止: kill \$(cat logs/backend.pid) \$(cat logs/algorithm.pid)"