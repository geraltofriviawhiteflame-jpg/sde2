#!/usr/bin/env python
"""Sandbox/dev bootstrap: embedded Postgres + migrations + server/.env.

Used where Docker isn't available (e.g. this sandbox). On your own machine,
prefer `docker compose up -d` + a normal DATABASE_URL.
Idempotent: safe to run on every start.
"""

import os
import pathlib
import sys
import urllib.parse

BASE = pathlib.Path(__file__).resolve().parents[1]
PGDATA = BASE / ".pgdata"
ENV_FILE = BASE / "server" / ".env"


def main() -> None:
    import psycopg
    import pgserver

    server = pgserver.get_server(str(PGDATA))
    admin_uri = server.get_uri()
    parsed = urllib.parse.urlparse(admin_uri)
    db_uri = urllib.parse.urlunparse(parsed._replace(path="/agentops"))
    with psycopg.connect(admin_uri, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = 'agentops'"
        ).fetchone()
        if not exists:
            conn.execute("CREATE DATABASE agentops")

    app_db_url = db_uri.replace("postgresql://", "postgresql+psycopg://")
    ENV_FILE.write_text(
        f"DATABASE_URL={app_db_url}\n"
        "REDIS_URL=redis://localhost:6379/0\n"
        "ENV=dev\n"
    )
    print(f"postgres up  -> {db_uri}")
    print(f".env written -> {ENV_FILE}")


if __name__ == "__main__":
    sys.exit(main())
