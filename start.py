import subprocess
import sys
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(BASE, "pre-consultation-system", "backend")
FRONTEND = os.path.join(BASE, "pre-consultation-system", "frontend")


def kill_port(port):
    r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if f":{port}" in line and "LISTENING" in line:
            pid = line.strip().split()[-1]
            subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
            print(f"  [OK] 已杀掉端口 {port} 的进程 (PID {pid})")
            return


def backend():
    os.chdir(BACKEND)
    kill_port(8000)

    print("[1/3] 检查依赖...")
    deps_missing = subprocess.run([
        sys.executable, "-c",
        "import fastapi, uvicorn, sqlalchemy, pymysql, jose, bcrypt"
    ], capture_output=True).returncode != 0
    if deps_missing:
        print("  > 安装缺失依赖...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"])
    else:
        print("  > 依赖已就绪")

    print("[2/3] 初始化种子数据...")
    subprocess.run([sys.executable, "-m", "seed.seed_data"])

    print("[3/3] 启动 FastAPI 服务 -> http://localhost:8000")
    print("       API文档 -> http://localhost:8000/docs\n")
    subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])


def frontend():
    os.chdir(FRONTEND)
    if not os.path.exists("node_modules"):
        print("[1/2] 安装 npm 依赖...")
        subprocess.run(["cmd", "/c", "npm install"])
    else:
        print("[1/2] npm 依赖已就绪")

    print("[2/2] 启动 Vite 开发服务器 -> http://localhost:5173\n")
    subprocess.run(["cmd", "/c", "npm run dev"])


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "backend":
        backend()
    elif mode == "frontend":
        frontend()
    else:
        print("用法:")
        print("  python start.py backend   # 启动后端")
        print("  python start.py frontend  # 启动前端")
        print("  python start.py all       # 启动全部 (需要两个终端分别运行)")
