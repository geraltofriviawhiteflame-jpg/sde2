# SDE2 Prep Plan — dual track (applying now)

**Start date:** Sep 24, 2026 · **Mode:** applying while prepping · **Profile:** 2–4 YoE, backend + full-stack + MCP/agents

## Decisions made

| Decision | Choice | Why |
|---|---|---|
| Flagship | **AgentOps** (Tier 1A) | Best MCP-profile fit; covers the most SDE2 backend signals (idempotency, queues, replay, multi-tenancy, rate limits); React dashboard covers the full-stack bar → Tier 3 skipped |
| Flagship stack | **Python / FastAPI + Postgres + Redis + React** | "One language deeply"; agent ecosystem fit; matches target JDs |
| MCP server | **Node / TypeScript → npm** | Quick win from the research doc; makes MCP experience publicly verifiable |
| LLD language | **Java** (locally) or Python here | Amazon-style loops; Java not installed in this sandbox |
| Backend-depth (Tier 2) | Payments system — **only after flagship is demo-able** | Outbox/saga/idempotency patterns partially overlap with flagship |
| RAG SaaS | Deferred — fold in as a "document-QA agent" on AgentOps if an interview demands it | Avoids a second 6-week build |

## Track A — Interview readiness (daily, non-negotiable)

- [ ] **DSA: 1 problem/day** → log in `prep/dsa/TRACKER.md` (pattern rotation in that file)
- [ ] **LLD: 2/week** → pick from `prep/lld/README.md`, solve in `prep/lld/<problem>/`
- [ ] **HLD: 2/week** → pick from `prep/hld/README.md`, write-up in `prep/hld/<question>/`
- [ ] **Behavioral: story bank to 9–12 stories** → `prep/behavioral/STORY_BANK.md`
- [ ] Storytelling pattern for every project answer: **scale → bottleneck → diagnosis → fix → measured result**

## Track B — Build (flagship: `flagship/agentops/`)

**Step-by-step guides with designs & acceptance criteria: `flagship/agentops/docs/steps/README.md`** — start every session there. Step 1 (foundations) is DONE and has a study guide for understanding the code.

Milestones (details in `flagship/agentops/docs/DESIGN.md`):

- [ ] **M1 — Week 1 (by Sep 30):** design doc v1, repo scaffold, FastAPI service up, Postgres schema (runs/steps/idempotency_keys), GitHub Actions CI green
- [ ] **M2 — Week 2 (by Oct 7):** agent runner (tool-calling, structured outputs, retries) + job queue + idempotency keys; MCP server MVP published to npm
- [ ] **M3 — Week 3 (by Oct 14):** checkpoint + replay of agent runs; evals harness v1 (LLM-as-judge + deterministic checks, cost/latency per run); OpenTelemetry traces
- [ ] **M4 — Week 4 (by Oct 21):** React dashboard (run timeline, replay viewer, eval charts); guardrails (token budgets, tool allowlists, PII redaction); multi-tenant rate limiting
- [ ] **M5 — Week 5 (by Oct 28):** k6 load test → p50/p95/p99 in README; architecture diagram; deployed URL + demo account; 2 failure stories documented

## Weekly cadence

| Week | Track A focus | Track B focus |
|---|---|---|
| W1 (Sep 24–30) | Story bank v1 (6 stories) · LLD parking lot · HLD URL shortener | M1 + pick MCP-server target |
| W2 (Oct 1–7) | LLD ATM · HLD notification system | M2 + npm publish |
| W3 (Oct 8–14) | LLD BookMyShow · HLD news feed · mock behavioral | M3 |
| W4 (Oct 15–21) | LLD elevator · HLD rate limiter / distributed cache | M4 |
| W5 (Oct 22–28) | Full mock loop (2×DSA + LLD + HLD + behavioral) | M5 |
| W6+ | Keep rotations going; add company-specific prep | Tier 2 payments (outbox, saga, reconciliation, webhooks) if bandwidth |

## Rules while interviewing

1. Applications/interviews win ties: if an onsite lands this week, shift Track B milestones, never Track A.
2. Every project milestone must produce interview material: a number, a trade-off, or a failure story. No milestone without one.
3. Before each interview: reread the target company's JD and map 3 stories + 1 project deep-dive to it.
4. If time compresses further, the priority order is: **story bank > DSA > flagship design doc + M1–M2 > HLD reps > M3–M5**.
