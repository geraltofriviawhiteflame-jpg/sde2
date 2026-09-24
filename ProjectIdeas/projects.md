# SDE2 Project List — Backend + Full-Stack + AI/Agents

**Calibrated for:** 2–4 YoE · Backend + Full-stack · MCP/agents experience · Target: Big tech + Indian product startups (Amazon, Flipkart, Microsoft, Razorpay, Swiggy, Fynd, Atlassian tier)

---

## 1. What SDE2 job postings actually ask for (Sept 2026 research)

Scanning current SDE2 postings (Amazon SDE II, Flipkart SDE-2, Fynd "Backend & Agentic AI", Triomics, Woodfrog, Syfe, plus AI engineer roles), the same signals repeat:

**Backend core (non-negotiable)**
- REST API design, microservices, one language deeply (Java/Spring Boot, Node, Go, or Python/FastAPI)
- Distributed systems fundamentals: idempotency, consistency, async processing, duplicate/late events, checkpoints, replay
- PostgreSQL: schema design, indexing, query optimization
- Kafka / event-driven architecture, Redis caching, concurrency
- Docker/K8s, AWS, CI/CD
- **Ownership evidence**: "you can explain their scale, bottlenecks, performance targets, and availability outcomes" (Fynd JD, verbatim)
- Observability: logs, metrics, traces, profiling; monitoring & alerting

**The AI/agent premium (2026's differentiator)**
- "Applied AI engineering: shipping LLM applications or agents with tool calling, structured outputs, retrieval, and evaluations of correctness, latency, cost, and failure behaviour" (Fynd SDE2/3 JD)
- MCP tools, multi-agent orchestration, LangGraph-style workflows
- RAG: chunking, hybrid retrieval (BM25 + dense), reranking, query rewriting
- Eval frameworks: comparing prompt/model variants quantitatively
- Guardrails, hallucination control, PII safety, audit trails

**Full-stack**: React + backend integration, SQL, AWS (Zinier, Flipkart GenAI postings)

**SDE2 interviews** (Amazon-style): 2 DSA rounds + LLD (design an ATM, parking lot) + HLD (URL shortener, notification system, news feed, product page) + behavioral/Leadership Principles — your projects are your story bank for LPs like Ownership, Dive Deep, Deliver Results.

> **Strategy: 2–3 deep projects beat 10 toy projects.** Every JD values "shipped, owned, can explain trade-offs" over a list of clones. Recommended: **1 flagship + 1 backend-depth + 1 full-stack**, with the MCP/eval work folded into the flagship.

---

## 2. Tier 1 — Flagship project (pick ONE, ~4–6 weeks)

### 🥇 Option A: AgentOps — production-grade agent orchestration platform
*The single best fit for your profile. Mirrors the Fynd "SDE-2/3 Backend & Agentic AI" JD almost line by line.*

**Build:** A multi-tenant platform where users register AI agents that call tools (your own MCP servers), run workflows, and get monitored/evaluated.

- **Core:** FastAPI or Node/NestJS backend; agent runner with tool-calling, structured outputs (JSON schema validation), retries
- **Reliability engineering (the SDE2 part):** async job queue (Celery/BullMQ/Kafka), idempotency keys on every run, checkpoint + replay of agent runs (resume from last successful step), duplicate/late event handling
- **State:** PostgreSQL (runs, steps, traces), Redis (cache LLM responses, rate limits, distributed locks)
- **Evals harness:** score each agent run on correctness (LLM-as-judge + deterministic checks), latency, cost per run, failure taxonomy — dashboard comparing prompt/model variants
- **Observability:** OpenTelemetry traces per agent run (each LLM call & tool call = a span), Prometheus/Grafana or Grafana Cloud, structured logs
- **Full-stack layer:** React dashboard — live run timeline, replay viewer, eval charts, cost analytics
- **Guardrails:** token budget limits, tool allowlists per tenant, PII redaction, audit log

**Interview stories it generates:** idempotency design, exactly-once vs at-least-once trade-offs, replay semantics, rate limiting multi-tenant LLM usage, eval methodology, failure modes of agents and how you handled each.

### 🥈 Option B: Multi-tenant RAG knowledge-base SaaS
*Matches RAG + Agentic AI engineer JDs (Codvo-type) and Flipkart SDE II GenAI.*

**Build:** Upload docs (PDF/DOCX/markdown) → chunk → embed → ask questions with citations.

- Ingestion pipeline: parsing, component-aware chunking, async workers, re-indexing without downtime
- Hybrid retrieval: BM25 (Elasticsearch/OpenSearch or Postgres FTS) + dense (pgvector/Qdrant), reranking, query rewriting
- Multi-tenancy with row-level security, per-tenant usage metering, API keys
- Chat UI in React with citation highlighting, streaming responses (SSE/WebSockets)
- Evals: retrieval hit-rate, faithfulness, answer correctness on a golden dataset
- Same production trappings: caching, rate limiting, tracing, CI/CD, load-test numbers

---

## 3. Tier 2 — Backend depth project (pick ONE, ~3–4 weeks)

### 🥇 Option A: UPI-style payment & order processing system
*Razorpay/Flipkart/PhonePe-flavored; the event-driven patterns in every Indian startup JD.*

**Build:** Microservices — Order, Payment, Inventory, Ledger, Notification.

- **Idempotency:** idempotency keys on payment creation (the classic Razorpay/Stripe problem)
- **Outbox pattern:** reliable event publishing from Postgres to Kafka
- **Saga orchestration:** order → reserve inventory → capture payment → confirm/compensate on failure
- **Reconciliation service:** nightly job detecting mismatched payments vs ledger (real fintech work)
- **Webhooks with retries:** HMAC signing, exponential backoff, dead-letter queue
- **Load test with k6** → put p50/p95/p99 numbers and bottleneck analysis in the README

### 🥈 Option B: Multi-channel notification platform
*Maps directly to a classic Amazon SDE2 HLD question ("design a notification system") — build it for real.*

- Email/SMS/push providers with failover, per-provider rate limiting, priority queues
- Kafka consumers, dedup, user preferences, quiet hours, template service
- Delivery tracking + analytics; DLQ with replay tooling
- Handles 10k+ events/sec in load tests; document the throughput you achieved

---

## 4. Tier 3 — Full-stack product (pick ONE, ~2–3 weeks)

### 🥇 Option A: SaaS with subscriptions, multi-tenancy & RBAC
*Proves end-to-end ownership — the core SDE2 bar at startups.*

**Build:** something small but real — appointment booking, expense management, or an internal-tool builder.

- React + Node/NestJS (or Next.js), PostgreSQL, Prisma/TypeORM
- Razorpay/Stripe **test-mode** subscriptions: plans, trials, proration, webhook-driven state machine, dunning
- Multi-tenant data isolation, RBAC (owner/admin/member), audit logs, feature flags
- Deployed: AWS (ECS/EC2 + RDS) or Railway/Render, GitHub Actions CI/CD, Sentry, uptime monitoring
- Public URL + demo account. A deployed link with real users (even 10) outweighs a perfect repo nobody ran.

### 🥈 Option B: AI-native full-stack app
An AI-powered product feature on top of a conventional app (e.g., support desk with AI triage agent that classifies, drafts replies, and escalates — with human-in-the-loop approval UI). Shows you can integrate AI into real product flows, not just demos.

---

## 5. Tier 4 — Systems-depth / interview-aligned (optional, ~1–2 weeks)

*Pick only if interviewing at Amazon/Microsoft-style shops; these map 1:1 to HLD rounds and give you "Dive Deep" stories.*

| Project | HLD question it preps | Key concepts you'll actually implement |
|---|---|---|
| Distributed KV cache (Go/Java) | "Design a distributed cache" | Consistent hashing, replication, LRU eviction, gossip/failover |
| Mini message queue | "Design Kafka" | Append-only log, consumer groups, offsets, at-least-once delivery |
| Distributed rate limiter service | API gateway designs | Token bucket, Redis + Lua atomicity, sliding window, hot-key handling |
| URL shortener + analytics | "Design bit.ly" | Base62, read-heavy scaling, cache-aside, counter sharding |

---

## 6. The MCP/agents differentiators (low effort, high signal — 2–5 days each)

You already work with MCP — make it *visible and credible*:

1. **Ship an open-source MCP server** for a real tool/service (npm/PyPI), with tests, docs, and CI. Recruiters and interviewers can see it; GitHub stars/issues = public proof. Quantiphi and others explicitly list MCP in requirements.
2. **Write an eval-driven blog post**: "I compared 3 models / 2 prompt strategies on task X — here's the cost/latency/correctness data." The hiring bar for agent engineers is literally "has run an eval suite that compares two prompt variants quantitatively."
3. **Add MCP to your flagship**: your AgentOps platform exposing tools *via* your own MCP server makes the whole story cohesive.

---

## 7. Presentation checklist (this is what converts projects → offers)

For **every** project:

- [ ] **README with an architecture diagram** (draw.io/Excalidraw), tech choices, and *why* — trade-offs, not features
- [ ] **Numbers**: load-test throughput, p95 latency, error rates, eval scores, cost per 1k requests
- [ ] **Design doc** (`/docs` folder) written as if proposing to a team — SDE2s are expected to drive design discussions
- [ ] **Tests + CI** (unit + integration; GitHub Actions badge green)
- [ ] **Deployed & observable**: live URL, dashboards, alerts — "operated in production" is the phrase JDs use
- [ ] **Failure story**: one incident you simulated/fixed (failover, cache stampede, poisoned message in DLQ) — this becomes your Ownership/Dive Deep behavioral story
- [ ] Resume line format: *"Built X — handles N req/s at p95 < Yms using A, B, C; designed idempotent Z processing with replay support"*

---

## 8. Suggested 3-month plan (while employed)

| Weeks | Focus |
|---|---|
| 1–2 | Ship MCP server + set up shared infra knowledge (Docker, K8s, OTel basics) |
| 3–8 | Flagship (AgentOps or RAG SaaS), demo-able by week 6, evals + observability by week 8 |
| 9–12 | Backend-depth project (payments/notification) + one HLD-aligned mini system |
| Ongoing | 1 DSA problem/day (Amazon SDE2 loops still weight DSA heavily) + LLD practice (ATM, parking lot, BookMyShow) |

**Final tip:** In interviews, structure project talk as *scale → bottleneck → diagnosis → fix → measured result*. That single pattern answers both the system design round and the "tell me about a complex project you owned" behavioral round.
