#!/usr/bin/env python
"""One-process dev server: ensure Postgres (embedded) -> migrate -> seed -> exec uvicorn.

The exec*() at the end replaces this process image, so pgserver's atexit
cleanup never runs and Postgres lives as long as uvicorn does.
"""

import os
import pathlib
import sys
import urllib.parse

BASE = pathlib.Path(__file__).resolve().parents[1]
SERVER = BASE / "server"
sys.path.insert(0, str(SERVER))
os.chdir(SERVER)

import pgserver  # noqa: E402
import psycopg  # noqa: E402

server = pgserver.get_server(str(BASE / ".pgdata"))
admin_uri = server.get_uri()
parsed = urllib.parse.urlparse(admin_uri)
db_uri = urllib.parse.urlunparse(parsed._replace(path="/agentops"))
app_db_url = db_uri.replace("postgresql://", "postgresql+psycopg://")

with psycopg.connect(admin_uri, autocommit=True) as conn:
    exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = 'agentops'").fetchone()
    if not exists:
        conn.execute("CREATE DATABASE agentops")

os.environ["DATABASE_URL"] = app_db_url

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

command.upgrade(Config("alembic.ini"), "head")

from app.db import SessionLocal  # noqa: E402
from app.models import Agent, Tenant  # noqa: E402

(SERVER / ".env").write_text(f"DATABASE_URL={app_db_url}\nENV=dev\n")

with SessionLocal() as s:
    tenant = s.query(Tenant).filter_by(name="demo").one_or_none()
    if tenant is None:
        tenant = Tenant(name="demo")
        s.add(tenant)
        s.flush()
    agent = s.query(Agent).filter_by(tenant_id=tenant.id, name="triage-demo").one_or_none()
    if agent is None:
        agent = Agent(
            tenant_id=tenant.id,
            name="triage-demo",
            system_prompt="You triage support tickets.",
            tool_allowlist={"refund": True},
            budget_limits={"max_tokens_per_run": 20000},
        )
        s.add(agent)
    s.commit()
    print("=== AgentOps dev server ===")
    print("tenant_id:", tenant.id)
    print("agent_id :", agent.id)

os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])
