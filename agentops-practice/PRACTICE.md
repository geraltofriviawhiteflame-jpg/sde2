# AgentOps Practice Rebuild — my own hands, Step 1

Ground rules (the interview simulation):
1. **I write every line.** The agent never pre-writes my code — I paste code in chat, it goes into files **verbatim**, gets run, and reviewed.
2. **Hint ladder when stuck:** ask for a *nudge* → *approach* → *pseudo-code* — never the full solution on the first ask.
3. **Try before I peek** at `flagship/agentops/` — but peeking after an honest attempt is allowed and smart.
4. **Test-first where possible:** write the test, watch it fail, make it pass.
5. After each micro-step: agent reviews the code like a PR and asks **one "why" question** I must answer out loud.

Reference material (allowed, in this order):
- `flagship/agentops/docs/steps/step-1-foundations.md` (concepts primer + file map)
- `flagship/agentops/docs/DESIGN.md` (the D1/D2 decisions)
- `agentops-practice/sql_demo.py` (raw-SQL lifecycle demo — run: `/tmp/practice/bin/python sql_demo.py`)
- Last resort: the actual implementation

**Bootstrap after sandbox recycle** (~20s):
```bash
python3 -m venv /tmp/practice && /tmp/practice/bin/pip install -q fastapi uvicorn sqlalchemy "psycopg[binary]" alembic pydantic-settings pytest pgserver httpx
```

## Micro-steps

| # | Deliverable | Acceptance | Status |
|---|---|---|---|
| 1.1 | Skeleton + config + `/healthz` | uvicorn on :8001, `GET /healthz` → `{"status":"ok"}`; Settings from env with defaults | ☐ |
| 1.2 | `db.py` — engine, Base, SessionLocal, `get_db` | dependency injects a session into a throwaway route | ☐ |
| 1.3 | Models: Tenant, Agent (+ flush-before-FK lesson) | script creates tenant+agent in one session, ids printed | ☐ |
| 1.4 | Alembic init + migration 001 (tenants, agents) | `alembic upgrade head` creates tables; `downgrade base` removes them | ☐ |
| 1.5 | Models: Run (both uniqueness layers!) + steps/evals minimum | migration 002; partial index visible in the DB | ☐ |
| 1.6 | `POST /v1/runs` happy path + `GET /v1/runs/{id}` | curl: 202 → row in `queued`; 404 on bogus id; 422 missing key | ☐ |
| 1.7 | Idempotency layer (constraint arbitration) | same key twice → 202 then 200 with SAME run id | ☐ |
| 1.8 | Entity lock branch (partial index) | different key, same active ticket → 409; after terminal state → allowed | ☐ |
| 1.9 | Replay endpoint + full test suite | terminal-only replay w/ parent id; ≥6 tests green | ☐ |

**Done when:** all boxes ticked AND the Step-1 self-quiz answered out loud without notes.

## Session log
- 2026-09-26 — raw-SQL lifecycle demo (sql_demo.py): saw both UniqueViolations, NULL-distinct behavior, diag.constraint_name switch
