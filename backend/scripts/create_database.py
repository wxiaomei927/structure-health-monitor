"""创建 resistance_db 数据库。

库已存在时直接跳过，不会动里面的数据。
连接参数从 PGHOST / PGPORT / PGUSER / PGPASSWORD 四个环境变量读。
"""

import os
import sys

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_NAME = "resistance_db"

def main() -> int:
    host = os.environ.get("PGHOST", "127.0.0.1")
    port = int(os.environ.get("PGPORT", "5432"))
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD")
    if not password:
        print("缺少 PGPASSWORD 环境变量", file=sys.stderr)
        return 1

    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
            exists = cur.fetchone() is not None
            if exists:
                print(f"数据库 {DB_NAME} 已存在，跳过创建")
            else:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
                print(f"数据库 {DB_NAME} 创建完成")
    finally:
        conn.close()

    # 立刻验证能否连上，并打印版本与当前库名
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=DB_NAME,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), version()")
            db_name, version = cur.fetchone()
            print(f"连接成功: database={db_name}")
            print(f"版本: {version.split(',')[0]}")
    finally:
        conn.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
