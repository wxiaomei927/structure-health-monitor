"""后端服务入口。"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import uvicorn  # noqa: E402

HOST = "0.0.0.0"
PORT = 8002


def main() -> None:
    from app.main import app

    print("=" * 52)
    print("  结构健康监测平台 - 后端服务")
    print(f"  接口地址: http://127.0.0.1:{PORT}/api/v1")
    print(f"  接口文档: http://127.0.0.1:{PORT}/docs")
    print("  按 Ctrl+C 停止服务")
    print("=" * 52)
    print()

    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
