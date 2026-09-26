# HLD / System Design Practice

Format per question folder (`prep/hld/<question>/`): requirements & NFRs → capacity estimates → API → data model → high-level diagram → deep dives (2–3) → trade-offs & bottlenecks. Keep each write-up ≤ 2 pages; practice one **on a whiteboard/timer (45 min)** after writing it.

## Question queue (in order)

- [ ] **URL shortener** (W1) — read-heavy scaling, base62, cache-aside, counter sharding *(also a Tier-4 mini-project option)*
- [ ] **Notification system** (W2) — multi-channel, priority queues, dedup, DLQ, quiet hours — *your flagship's cousin; build knowledge twice*
- [ ] **News feed** (W3) — fan-out on write vs read, celebrity problem, ranking
- [ ] **Distributed rate limiter** (W4) — token bucket, Redis+Lua atomicity, sliding window, hot keys — *you will implement this in the flagship*
- [ ] Design AgentOps itself — *interviewers often ask you to design what's on your resume; have the full HLD ready*
- [ ] Distributed KV cache — consistent hashing, replication, failover
- [ ] Payment/order system — idempotency, outbox, saga, reconciliation *(Tier 2 prep)*
- [ ] Chat system — WebSockets, message ordering, presence
- [ ] RAG pipeline at scale — chunking, hybrid retrieval, reranking, ingestion workers
- [ ] Typeahead / autocomplete

## Estimation cheat numbers (memorize)

- 1 day ≈ 86k s ≈ 100k requests/day if 1 rps; 1M req/day ≈ 12 rps avg / ~120 rps peak (×10)
- Memory: 1 char ≈ 1 B; UUID ≈ 36 B; a small object ≈ 1 KB rule of thumb
- 10 GB/day of writes ≈ ~116 KB/s ≈ trivial for one Postgres box — know when NOT to scale
- Read:write ratio drives cache vs fan-out decisions; p99 dominates tail-latency discussions
