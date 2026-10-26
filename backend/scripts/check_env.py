"""检查依赖是否装齐。"""

import importlib
import sys

MODULES = [
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "psycopg",
    "jwt",
    "bcrypt",
    "pydantic_settings",
    "pandas",
    "openpyxl",
]

print(f"Python: {sys.executable}")
print(f"版本: {sys.version.split()[0]}")
print()

missing = []
for name in MODULES:
    try:
        mod = importlib.import_module(name)
        version = getattr(mod, "__version__", "")
        print(f"  {name:18s} OK       {version}")
    except Exception as exc:
        missing.append(name)
        print(f"  {name:18s} 缺失     {type(exc).__name__}")

print()
if missing:
    print("缺少:", ", ".join(missing))
else:
    print("依赖齐全，可以启动平台")
