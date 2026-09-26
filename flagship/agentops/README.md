# AgentOps

Production-grade agent orchestration platform: register AI agents that call tools (via MCP servers), run workflows, and get monitored/evaluated. The flagship project — design doc is the source of truth.

- **Design doc:** [`docs/DESIGN.md`](docs/DESIGN.md)
- **Decision log:** [`docs/DECISIONS.md`](docs/DECISIONS.md)
- **Build guides (start here each session):** [`docs/steps/README.md`](docs/steps/README.md)

## Stack

Python 3.11 · FastAPI · PostgreSQL · Redis · Celery · OpenTelemetry · React (dashboard, M4) · k6 (load tests)

## Layout

```
agentops/
├── docs/            design doc + ADRs
├── server/          FastAPI app
│   ├── app/
│   │   ├── main.py        entrypoint (/healthz)
│   │   ├── config.py      env-driven settings
│   │   ├── db.py          engine/session
│   │   └── models.py      SQLAlchemy schema (runs/steps/idempotency)
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml  postgres + redis (local dev)
└── .env.example
```

## Quickstart (your machine — Docker)

```bash
docker compose up -d                 # postgres + redis
cp .env.example server/.env
cd server && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head                 # create schema
uvicorn app.main:app --reload        # http://localhost:8000/docs
```

## Quickstart (no Docker — embedded Postgres)

```bash
pip install -r server/requirements.txt -r server/requirements-dev.txt
python scripts/dev_up.py             # embedded pg + migrations + server/.env
cd server && uvicorn app.main:app --reload
python ../scripts/seed.py            # demo tenant/agent ids for /docs
```

## Tests

```bash
cd server && pytest -q    # CI runs the same suite against a postgres service
```

## Milestones

See `PLAN.md` in the repo root — M1 (scaffold+schema) → M5 (load test + deploy).
