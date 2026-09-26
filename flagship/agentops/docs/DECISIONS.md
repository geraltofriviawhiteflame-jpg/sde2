# Decision Log (mini-ADRs)

Interviewers probe *why*, not *what*. Every architecture decision gets one entry here. Keep additions to 3–6 lines.

## ADR-001 — Python/FastAPI over Node/NestJS
- **Decision:** FastAPI for the control plane and workers.
- **Why:** agent/LLM ecosystem (sdk maturity, eval libs) is Python-first; async-first framework fits long-running tool calls; "one language deeply" per prep strategy.
- **Rejected:** NestJS (team-skill argument exists but ecosystem penalty for agent work), Go (fastest but slowest to iterate on LLM plumbing).

## ADR-002 — Postgres over MongoDB for run/step state
- **Decision:** PostgreSQL.
- **Why:** relational fit (tenant→agent→run→step), unique constraints are load-bearing for idempotency (D1), JSONB for flexible payloads, pgvector later if we fold in RAG.

## ADR-003 — At-least-once + checkpoints, not exactly-once
- **Decision:** design for at-least-once delivery; idempotency keys + checkpoint/resume give effectively-once semantics.
- **Why:** exactly-once requires transactional coupling between queue and DB (or idempotent sinks anyway) — cost/complexity not justified.
- **Status:** core interview story; be ready to name where duplicates can still surface (non-idempotent external tools).

## ADR-004 — Celery first, Kafka later
- **Decision:** Celery + Redis broker for M2.
- **Why:** days-to-ship beats weeks-to-ship while applying; Kafka migration path documented (outbox table → relay) if event history/replay-at-broker becomes a requirement.

## ADR-005 — (reserved) Rate limiter fail-open vs fail-closed split
- See DESIGN.md D3; fill in with load-test data at M4.
