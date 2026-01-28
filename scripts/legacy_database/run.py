#!/usr/bin/env python3
"""
启动应用程序

使用示例:
    python run.py
    python run.py --host 0.0.0.0 --port 8000 --reload
"""

import argparse
import os
import sys
from pathlib import Path

import uvicorn

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR / "backend"))

DEFAULT_HOST = os.environ.get("BACKEND_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
DEFAULT_LOG_LEVEL = os.environ.get("BACKEND_LOG_LEVEL", "info")


def main():
    parser = argparse.ArgumentParser(description="启动Agent AI Backend服务器")
    parser.add_argument("--host", default=DEFAULT_HOST, help="绑定地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="绑定端口")
    parser.add_argument("--reload", action="store_true", help="开启自动重载")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数")

    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level=DEFAULT_LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
