# Step 4 — Heartbeat, Reaper, Resume: the flagship story

> Goal: workers prove they're alive **per run** (heartbeat = lease); a reaper reclaims
> dead runs; resumed workers continue from the last checkpoint; zombie workers can't
> double-fire tools. This step *is* the "walk me through a hard reliability problem"
> answer for your interviews.

## 1. Design (everything here came out of our discussion sessions)

### Lease = heartbeat
- Migration `0003`: `runs.last_heartbeat_at`, `runs.lease_expires_at`
- Worker heartbeats every 10s while executing: `UPDATE runs SET last_heartbeat_at = now(),
  lease_expires_at = now() + 60s WHERE id = :run AND worker_id = :me`
- **Reaper** (thread in worker or separate process):
  `status='running' AND lease_expires_at < now()` → set `failed / lease_expired`,
  `attempts < max` → requeue instead. Transition, never delete (audit trail).
- Distinguish slow vs dead: heartbeat renews → never reaped regardless of slowness.

### Zombie guard (the 🧟 fix)
Lease expired → reaper requeued → second worker resumed → first wakes up and continues.
Mitigation layers:
1. **Lease re-verify before every tool call** (option c from our discussion):
   `UPDATE runs SET lease_expires_at = now()+60s WHERE id=:run AND worker_id=:me
   AND lease_expires_at > now()` → rowcount 0 ⇒ you're a zombie ⇒ abort immediately.
   Cheapest check at the point of maximum catastrophe.
2. **Idempotent tool adapters** — dangerous tools accept a dedupe token
   (e.g. `run_id:seq`); a replayed refund is a no-op. Defense in depth: the tool's own
   idempotency, because leases alone can't be airtight.

### Resume
- On claim: load steps; `seq > last_successful_seq` only; rebuild context from
  checkpointed steps + original input. LLM calls already paid for are not repeated.

## 2. Task breakdown
- [ ] Migration `0003` (columns + index on `lease_expires_at` partial `status='running'`)
- [ ] Heartbeat thread in worker; stop on terminal state
- [ ] `app/reaper.py` — sweep loop + metrics log line per reclaim
- [ ] Lease re-verify gate inside runner, immediately before `tool.call`
- [ ] `refund` tool with dedupe-token table `tool_dedup(run_id, seq, result)` — a replayed
      call returns the original result
- [ ] Tests (the fun ones):
      - worker "crash" (no terminal write) → reaper reclaims after lease → second worker
        resumes from last step → final output correct, first worker's completed steps not repeated
      - zombie: pause worker A past lease, let B resume, wake A → A aborts at the guard,
        **refund fired exactly once** (assert dedupe table + step count)
      - healthy-but-slow run (heartbeat renewing, execution 3× lease) → never reaped
- [ ] Demo script: kill -9 the worker mid-run on the live server; watch reaper + resume

## 3. Definition of done
- [ ] All three scenarios provable in tests and in the live demo
- [ ] Metrics: reclaims count, zombie-aborts count logged
- [ ] You can tell the whole story in 2 minutes: lease → expire → reclaim → resume →
      zombie guard → idempotent tools, and *why each layer exists* (what fails without it)

## 4. Interview stories (this step is 3 stories)
- "Design a system that survives worker crashes mid-job" — the whole arc
- "Distributed systems: tell me about a time you handled split-brain" — zombie guard
- "What does at-least-once mean in practice?" — refund dedupe token

## 5. Discuss before building
1. Heartbeat every 10s with 60s lease: what failure rate of false positives is acceptable,
   and how do the numbers derive? (heartbeat latency vs DB load vs reclaim speed)
2. Who reaps the reaper? (single reaper = SPOF; two reapers = contention — SKIP LOCKED again?)
3. Should the reaper live in the API process, worker process, or its own deployment?
