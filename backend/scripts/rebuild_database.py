"""重建数据库。

模型改动后 create_all 只补新表，不会给已有表加新列，
结构变化较大时直接重建更省事。删库前会先确认。
"""

from __future__ import annotations

import os
import sys

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_NAME = "resistance_db"
CONFIRM = "yes"

def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        confirmed = True
    else:
        confirmed = input(f"确认重建数据库 {DB_NAME}？输入 {CONFIRM} 继续: ").strip() == CONFIRM
    if not confirmed:
        print("已取消")
        return 1

    host = os.environ.get("PGHOST", "127.0.0.1")
    port = int(os.environ.get("PGPORT", "5432"))
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD")
    if not password:
        print("缺少 PGPASSWORD 环境变量", file=sys.stderr)
        return 1

    conn = psycopg2.connect(
        host=host, port=port, user=user, password=password, dbname="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()"
                ),
                (DB_NAME,),
            )
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(DB_NAME)))
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            print(f"数据库 {DB_NAME} 已重建")
    finally:
        conn.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
