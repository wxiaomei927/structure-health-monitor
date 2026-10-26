"""给已有表补上模型里新增的列。

create_all 只建新表，不会给已存在的表加列。字段少时用 ALTER TABLE 补，
比重建数据库安全，存量数据不丢。
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import engine  # noqa: E402
from app.models.entities import Base  # noqa: E402

# 列名 -> 建表语句
COLUMN_DDL = {
    "users.email": "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(128)",
}


def main() -> int:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    changed = False
    with engine.begin() as conn:
        for target, ddl in COLUMN_DDL.items():
            table, column = target.split(".")
            if table not in existing_tables:
                continue
            columns = {col["name"] for col in inspector.get_columns(table)}
            if column in columns:
                print(f"  {target} 已存在，跳过")
                continue
            conn.execute(text(ddl))
            print(f"  {target} 已补上")
            changed = True

    if not changed:
        print("表结构无需变更")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
