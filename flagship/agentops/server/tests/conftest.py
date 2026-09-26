"""Test fixtures.

Database strategy:
- CI / any preset DATABASE_URL: use it as-is (GitHub Actions runs a postgres service).
- Local sandbox: spin an embedded Postgres (pgserver wheel) into .pgdata-test/,
  create a throwaway DB, run migrations, tests run against it. No Docker needed.
"""

import os
import pathlib
import urllib.parse
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

PGBASE = pathlib.Path(__file__).resolve().parents[2] / ".pgdata-test"


@pytest.fixture(scope="session")
def database_url() -> str:
    # CI (or any explicit DATABASE_URL) wins; otherwise embedded sandbox Postgres.
    preset = os.environ.get("DATABASE_URL")
    if preset:
        yield preset
        return

    import psycopg
    import pgserver

    server = pgserver.get_server(str(PGBASE))
    admin_uri = server.get_uri()
    parsed = urllib.parse.urlparse(admin_uri)
    test_db_uri = urllib.parse.urlunparse(parsed._replace(path="/agentops_test"))
    with psycopg.connect(admin_uri, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS agentops_test WITH (FORCE)")
        conn.execute("CREATE DATABASE agentops_test")
    yield test_db_uri.replace("postgresql://", "postgresql+psycopg://")


@pytest.fixture(scope="session")
def client(database_url: str):
    os.environ["DATABASE_URL"] = database_url

    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def tenant_and_agent(database_url: str) -> tuple[str, str]:
    engine = create_engine(database_url)
    with Session(engine) as s:
        from app.models import Agent, Tenant

        tenant = Tenant(name=f"t-{uuid.uuid4().hex[:12]}")
        s.add(tenant)
        s.flush()  # id defaults are assigned at flush — needed for the FK below
        agent = Agent(tenant_id=tenant.id, name="triage")
        s.add(agent)
        s.commit()
        return str(tenant.id), str(agent.id)
