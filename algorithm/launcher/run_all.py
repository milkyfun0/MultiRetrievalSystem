import os
import sys
import time
import signal
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# ========= checkpoint 配置（支持环境变量覆盖） =========
# 为空字符串表示不加载权重，只初始化模型结构
# 局域网部署时通过 export I2I_CKPT_PATH=/path/to/ckpt 注入
I2I_CKPT_PATH = os.getenv("I2I_CKPT_PATH", "")
T2I_CKPT_PATH = os.getenv("T2I_CKPT_PATH", "")
T2V_CKPT_PATH = os.getenv("T2V_CKPT_PATH", "")

# ========= 监听地址/端口配置（支持环境变量覆盖） =========
# 默认 0.0.0.0 以支持局域网访问，可通过环境变量收紧为 127.0.0.1
GATEWAY_HOST = os.getenv("MMR_GATEWAY_HOST", "0.0.0.0")
GATEWAY_PORT = int(os.getenv("MMR_GATEWAY_PORT", "18080"))

I2I_HOST = os.getenv("MMR_I2I_HOST", "0.0.0.0")
I2I_PORT = int(os.getenv("MMR_I2I_PORT", "18081"))

T2I_HOST = os.getenv("MMR_T2I_HOST", "0.0.0.0")
T2I_PORT = int(os.getenv("MMR_T2I_PORT", "18082"))

T2V_HOST = os.getenv("MMR_T2V_HOST", "0.0.0.0")
T2V_PORT = int(os.getenv("MMR_T2V_PORT", "18083"))

# 启动间隔（大模型加载较慢，可调整）
LAUNCH_INTERVAL_SEC = float(os.getenv("MMR_LAUNCH_INTERVAL_SEC", "1.5"))


def _fmt_ckpt(v: str) -> str:
    return v if v else "<EMPTY, no weight load>"


def build_env(model_ckpt_path: str) -> dict:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["MODEL_CKPT_PATH"] = model_ckpt_path or ""

    # 关键：让子进程在 ImageRetrieval / MedicalRetrieval / VideoRetrieval 下启动时，
    # 仍然能 import 到根目录下的 gateway / common 等包
    old_pythonpath = env.get("PYTHONPATH", "")
    root_str = str(ROOT_DIR)
    if old_pythonpath:
        env["PYTHONPATH"] = root_str + os.pathsep + old_pythonpath
    else:
        env["PYTHONPATH"] = root_str
    return env


def launch_service(cwd: Path, module_app: str, host: str, port: int, model_ckpt_path: str = ""):
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        module_app,
        "--host",
        host,
        "--port",
        str(port),
    ]
    env = build_env(model_ckpt_path)
    print(f"[launch] cwd={cwd} -> {' '.join(cmd)}", flush=True)
    return subprocess.Popen(cmd, cwd=str(cwd), env=env)


def terminate_process(proc: subprocess.Popen):
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGTERM)
    except Exception:
        pass


def main():
    print("[launch] checkpoint config:", flush=True)
    print(f"  I2I_CKPT_PATH={_fmt_ckpt(I2I_CKPT_PATH)}", flush=True)
    print(f"  T2I_CKPT_PATH={_fmt_ckpt(T2I_CKPT_PATH)}", flush=True)
    print(f"  T2V_CKPT_PATH={_fmt_ckpt(T2V_CKPT_PATH)}", flush=True)
    print("[launch] bind config:", flush=True)
    print(f"  GATEWAY {GATEWAY_HOST}:{GATEWAY_PORT}", flush=True)
    print(f"  I2I     {I2I_HOST}:{I2I_PORT}", flush=True)
    print(f"  T2I     {T2I_HOST}:{T2I_PORT}", flush=True)
    print(f"  T2V     {T2V_HOST}:{T2V_PORT}", flush=True)

    processes = []
    try:
        processes.append(
            launch_service(
                ROOT_DIR / "ImageRetrieval",
                "serve_i2i:app",
                I2I_HOST,
                I2I_PORT,
                I2I_CKPT_PATH,
            )
        )
        time.sleep(LAUNCH_INTERVAL_SEC)

        processes.append(
            launch_service(
                ROOT_DIR / "MedicalRetrieval",
                "serve_t2i:app",
                T2I_HOST,
                T2I_PORT,
                T2I_CKPT_PATH,
            )
        )
        time.sleep(LAUNCH_INTERVAL_SEC)

        processes.append(
            launch_service(
                ROOT_DIR / "VideoRetrieval",
                "serve_t2v:app",
                T2V_HOST,
                T2V_PORT,
                T2V_CKPT_PATH,
            )
        )
        time.sleep(LAUNCH_INTERVAL_SEC)

        processes.append(
            launch_service(
                ROOT_DIR,
                "gateway.app:app",
                GATEWAY_HOST,
                GATEWAY_PORT,
                "",
            )
        )

        print("[launch] all services started. Press Ctrl+C to stop.", flush=True)

        while True:
            time.sleep(1)
            for proc in processes:
                code = proc.poll()
                if code is not None:
                    print(f"[launch] process exited early with code={code}", flush=True)
                    raise SystemExit(code)

    except KeyboardInterrupt:
        print("\n[launch] stopping all services...", flush=True)
    finally:
        for proc in reversed(processes):
            terminate_process(proc)
        time.sleep(1)


if __name__ == "__main__":
    main()