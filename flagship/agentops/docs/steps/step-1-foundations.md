# Step 1 — Foundations: API, idempotency, entity lock (DONE — study guide)

> Status: **built, tested (8/8 green), pushed.** This doc is your map to understand every line.
> Goal for you: be able to **rebuild this from scratch** and **explain each decision out loud**.

## 1. What this step accomplishes

The front door of AgentOps: `POST /v1/runs` that safely accepts agent-run submissions and
survives the two classic failure modes:

| Failure | Handled by | Response |
|---|---|---|
| Same request arrives twice (double-click, network retry) | **Idempotency key** — `UNIQUE (tenant_id, idempotency_key)` on `runs` | 200, original run |
| Two *different* requests target the same business entity (ticket 123) concurrently | **Entity lock** — partial unique index on active runs | 409 busy |

Both are enforced **by the database**, not by application checks. That's the headline lesson.

## 2. Concepts primer (read before the code)

### 2.1 Check-then-act is a race
```
A: SELECT "is ticket busy?" → no
B: SELECT "is ticket busy?" → no     ← both looked before either wrote
A: INSERT ✓   B: INSERT ✓            ← double refund
```
Any application-level "check first" has this hole, no matter how fast. Fix: make the
*write itself* the check — a UNIQUE constraint. The second INSERT physically cannot commit.

### 2.2 Partial unique index = "unique while it matters"
```sql
CREATE UNIQUE INDEX uq_one_active_run_per_entity
ON runs (tenant_id, entity_type, entity_id)
WHERE status IN ('queued', 'running');
```
Unique **only among active runs**. A ticket may have unlimited *historical* runs; the
moment a run reaches `succeeded|failed|cancelled`, its row leaves the index predicate and
the slot frees **automatically** — no unlock code anywhere. Compare with the alternatives
in your own words: a `status` column check (race), a claims table with insert+delete
(more moving parts, manual cleanup on crash).

### 2.3 Constraint arbitration (how the API tells conflicts apart)
One INSERT can violate either uniqueness layer. We don't pre-check anything — we attempt
the insert and inspect *which constraint* refused us:
```python
except IntegrityError as exc:
    violated = exc.orig.diag.constraint_name   # psycopg exposes this
    if violated == "uq_run_idem":  → same request → fetch + return original (200)
    else:                          → entity busy → 409
```
Sub-millisecond edge case: loser's SELECT runs before winner's COMMIT → no row visible
yet → answer 409 "in flight" (the client retries and gets the 200). Say this out loud —
it's a favourite follow-up.

### 2.4 202 vs 200 (semantics callers program against)
- `POST /v1/runs` → **202 Accepted**: work is queued, body carries the run id, caller polls.
- Duplicate key → **200 OK**: "here is your (original) answer."
- Entity conflict → **409 Conflict**: caller may retry later with a new key.

### 2.5 ORM gotcha you already hit
`tenant.id` is `None` until `flush()` — Python-side defaults (`default=uuid4`) are applied
at flush time, not at object construction. Hence `s.add(tenant); s.flush()` before using
`tenant.id` in a FK. You'll feel this one again.

## 3. File map (what lives where)

| File | Role | Read for |
|---|---|---|
| `server/app/config.py` | env-driven settings (12-factor) | `pydantic-settings`, `lru_cache` |
| `server/app/db.py` | engine + session factory + `get_db` dependency | session-per-request pattern |
| `server/app/models.py` | ORM schema: tenants, agents, runs, steps, idempotency_keys, evals | the two uniqueness layers, `__table_args__` |
| `server/alembic/versions/0001_initial_schema.py` | hand-written migration = schema as code | how the partial index is created in raw Alembic |
| `server/app/api_runs.py` | the three endpoints + conflict arbitration | the heart of this step |
| `server/app/serializers.py` | ORM → JSON (UUID/Decimal safety) | why Decimals are stringified |
| `server/tests/test_runs_api.py` | the double-click suite | how tests encode the design discussion |
| `server/tests/conftest.py` | embedded Postgres fixture + session-scoped client | CI DATABASE_URL vs sandbox pgserver |
| `scripts/serve.py` | one-process dev boot: pg → migrate → seed → exec uvicorn | the `exec` trick that keeps pg alive |

## 4. Rebuild order (do this from a blank folder as an exercise)

1. **Infra up** — docker-compose (pg+redis) or `scripts/serve.py` embedded route
2. **Config + db** — `Settings`, `Base`, `SessionLocal`, `get_db` dependency
3. **Models** — tenants → agents → runs (both constraints!) → steps → evals
4. **Migration 0001** — hand-write it; compare against `Base.metadata` via `alembic check`
5. **API** — `create_run` with try/insert/arbitrate; `get_run`; `replay` (terminal-only!)
6. **Tests** — write the 8 tests *before* the API next time; notice how they forced 2 design fixes
7. **CI** — postgres service container, `alembic upgrade head`, `pytest -q`

## 5. Exercises (extend it yourself — each is 30–90 min)

1. **`POST /v1/runs/{id}/cancel`** — only when `queued|running`; sets `cancelled`;
   verify the entity slot frees (write the test first).
2. **Pagination** — `GET /v1/runs?tenant_id=&limit=&cursor=` keyset pagination on
   `(created_at, id)`. Why is OFFSET a trap at scale?
3. **Concurrency test** — two threads POST the same key simultaneously; assert exactly
   one 202 and one 200/409. (Hint: `ThreadPoolExecutor` + TestClient is not thread-safe;
   use real `httpx` clients against a live server.)
4. **`GET /v1/runs/{id}` tenant scoping** — currently any caller can read any run. Add
   `X-Tenant-Id` enforcement + a test that cross-tenant reads 404. (Real auth lands in Step 5.)
5. **Draw the ER diagram from memory**, then compare with `models.py`.

## 6. Self-quiz (answer out loud)

1. Why is the idempotency unique constraint on `runs` itself better than a separate
   claim-table with `run_id NULL`? (We *tried* the claim table — what broke?)
2. What releases the entity lock when a run finishes — and where is that code?
3. Why can two runs with `entity_id = NULL` coexist when the partial index includes
   `entity_id`?
4. A duplicate request arrives *while* the winner's transaction is still uncommitted.
   Walk through exactly what the loser does and returns.
5. Why is `replay` refused while the source run is still active?
6. What would break first if we removed `pool_pre_ping=True`?

## 7. Interview stories this step gives you (story bank §7–8 material)

- **"Tell me about a concurrency bug you designed away"** — check-then-act race →
  partial unique index; the claim-table detour that tests killed.
- **"How do you make an API idempotent?"** — the full D1 story with 200/202/409 semantics.
- **"Why migrations as code?"** — reviewable schema diffs, `alembic check` drift guard.
