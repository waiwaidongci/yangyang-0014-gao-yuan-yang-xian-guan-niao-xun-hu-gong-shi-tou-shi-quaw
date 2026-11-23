"""Run with python -m scripts.seed_demo."""
import json
from psycopg import sql

import domain
from core import db, seed_users

def seed_all():
    with db() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(381614)")
        seed_users(connection)
        domain.seed(connection)
        rows = connection.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        ).fetchall()
        return {
            row["tablename"]: connection.execute(
                sql.SQL("SELECT count(*) AS count FROM {}").format(sql.Identifier(row["tablename"]))
            ).fetchone()["count"]
            for row in rows
        }

if __name__ == "__main__":
    print(json.dumps(seed_all(), ensure_ascii=False, sort_keys=True))
