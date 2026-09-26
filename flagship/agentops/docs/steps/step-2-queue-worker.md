# Step 2 — Queue + Worker: runs actually execute (next up)

> Goal: `POST /v1/runs` stops being a row that sits in `queued` — a worker claims it and
> moves it `queued → running → succeeded/failed`. Async processing with at-least-once
> semantics, before any LLM exists (a stub executor stands in).

## 1. Design

### Queue choice — two honest options
| Option | Pros | Cons |
|---|---|---|
| **Postgres `FOR UPDATE SKIP LOCKED`** (build this) | zero new infra, transactional with run state, great interview story ("when is a DB a better queue than Kafka?") | polling latency (~1s), no per-message replay |
| Celery + Redis broker (the ADR-004 upgrade path) | industry-standard, mature retry/visibility tooling | needs Redis; hides the mechanics you're trying to learn |

**Decision: implement the Postgres queue behind a `JobQueue` port (interface), so the
Celery swap later is one adapter.** The mechanics you learn here (claim, lease, retry,
poison messages) transfer 1:1 to any broker.

### The claim — the core 8 lines
```sql
UPDATE runs SET status = 'running', started_at = now(), worker_id = :me
WHERE id = (
  SELECT id FROM runs
  WHERE status = 'queued'
  ORDER BY created_at
  FOR UPDATE SKIP LOCKED      -- two workers never claim the same run
  LIMIT 1
)
RETURNING *;
```
`SKIP LOCKED` is the whole trick: concurrent workers *skip* rows other transactions hold
locks on instead of waiting. No double-claim, no locks-in-application-code.

### Worker process
- standalone loop (`python -m app.worker`), N workers = N processes (start with 2)
- poll → claim → execute (Step 3 fills the executor; here: stub that sleeps + succeeds,
  plus a "crash" payload for tests) → write terminal state
- **graceful shutdown**: SIGTERM → finish current run, stop claiming → exit (K8s
  terminationGracePeriod story)
- failed executions: `attempts < max_attempts` → back to `queued` (+ `attempts + 1`);
  else `failed` with error JSON. Backoff = `created_at` eligibility column
  (`visible_at <= now()`), not sleep.

## 2. Task breakdown
- [ ] Migration `0002`: `runs.worker_id`, `runs.attempts`, `runs.visible_at`,
      `runs.max_attempts` (index on partial `status='queued' AND visible_at <= now()`)
- [ ] `app/queue.py` — `claim_next(db, worker_id)` + `requeue(db, run, error)` behind a small port
- [ ] `app/worker.py` — loop, SIGTERM handling, per-run exception boundary
- [ ] Executor port: `app/executors/base.py` + `StubExecutor` (sleeps, can be told to crash)
- [ ] Tests: queued→running→succeeded happy path · crash → requeued with attempts=1 ·
      attempts exhausted → failed · **two threads claim, never the same run** ·
      `visible_at` future run is not claimed
- [ ] Wire `create_run` TODO: nothing to enqueue (the row IS the job) — delete the TODO

## 3. Definition of done
- [ ] All tests green including the two-worker no-double-claim test
- [ ] A run submitted via live API reaches `succeeded` within ~2s (stub executor)
- [ ] You can explain: why SKIP LOCKED, why the row-is-the-job, what happens on SIGTERM
      mid-poll vs mid-run

## 4. Interview stories
- "Why not Kafka?" — honest trade-off answer + documented migration port
- At-least-once concretely: crash after claim, before terminal write → requeue → what
  runs twice? (nothing yet — but Step 3's LLM calls will, hence checkpoints there)
- "Walk me through claiming work without locking bugs" — the 8-line SQL

## 5. Discuss before building (bring answers)
1. Poll every 200ms vs LISTEN/NOTIFY — when does each win?
2. If the worker dies *after* `status='running'` but *before* finishing, who requeues it?
   (teaser for Step 4's reaper — decide what Step 2 does: nothing? a naive retry sweep?)
3. Should the API enqueue at all, or is "the row is the job" always better?
