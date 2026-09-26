# Step 6 — Evals, Dashboard, Load Test: numbers or it didn't happen

> Goal: close the loop. Score runs (deterministic + LLM-as-judge), render everything in a
> React dashboard, put **p50/p95/p99 + throughput + $/run** in the README, deploy it.
> This step converts the project into offer material — the resume line comes from here.

## 1. Design

### Evals harness
- **Deterministic checks** (inline, free, blocking): output schema valid · expected fields
  present · assertions from the agent config (e.g. "refund requires order_id") · run
  ended within budget
- **LLM-as-judge** (async job after terminal state): faithfulness to tool results,
  helpfulness, refusal detection → scores JSONB `{faithfulness: 0-1, helpfulness: 0-1}`;
  sampled (e.g. 20%) for high-volume tenants — cost control (JD language, verbatim)
- **Failure taxonomy** already accumulates from Steps 3–4 — aggregate it: failures by
  class per agent per day
- **Variant comparison endpoint** `GET /v1/evals?agent_id=&from=`: group by
  `agents.model` / prompt version → correctness %, p95 latency, $/run — *the* chart from
  the Fynd JD ("evaluations of correctness, latency, cost, and failure behaviour")

### Dashboard (React + Vite)
- Runs list (filters: status, agent, failure class) + run detail: step timeline,
  tokens/cost per step, error JSON, replay button
- Evals view: variant comparison table + failure-class breakdown
- Live tail: polling is fine (SSE later); keep it one deployable static bundle
- Served by FastAPI as static files → one deployment, one URL

### Load test + numbers
- k6 scenarios: submit-heavy (POST /v1/runs), read-heavy (GET run/steps), mixed
- Record: p50/p95/p99 per endpoint, max throughput before errors, queue depth over time
- Find **one bottleneck**, fix it (likely: claim query index or connection pool sizing),
  re-run, document before/after — the "scale → bottleneck → diagnosis → fix → measured
  result" arc, done for real

### Deploy
- Railway/Render: api + worker + postgres; dashboard as static; Sentry free tier; uptime
  monitor; demo account + seed data; link on the README

## 2. Task breakdown
- [ ] Deterministic checks module + wiring at terminal transition
- [ ] Judge job (async, sampled) + scores written to `evals`
- [ ] `GET /v1/evals` aggregation endpoint (+ tests on grouped math)
- [ ] React app: runs list, run detail timeline, evals view; build wired into deploy
- [ ] k6 scripts in `loadtest/` + README numbers table (before/after bottleneck fix)
- [ ] Deploy + demo account + Sentry + uptime link; architecture diagram refresh
- [ ] Resume line finalized: *"Built AgentOps — N req/s at p95 < Y ms; idempotent run
      submission with exactly-once tool effects; checkpoint/replay across worker crashes;
      eval harness comparing model variants on cost/latency/correctness."*

## 3. Definition of done
- [ ] Public URL with demo credentials in the README
- [ ] Load-test numbers + bottleneck before/after documented
- [ ] Eval comparison chart screenshots in README
- [ ] Two simulated incidents written up (failure stories for the bank)

## 4. Interview stories
- "How do you evaluate non-deterministic systems?" — the whole harness design
- "Tell me about a performance problem you diagnosed" — the k6 bottleneck arc
- "What does operating in production mean to you?" — Sentry, uptime, alerts, on-call-you

## 5. Discuss before building
1. Judge model: fixed cheap model vs tenant-selectable — cost vs flexibility?
2. Sample rate for judges: fixed 20% vs budget-adaptive?
3. Dashboard live updates: polling vs SSE — what changes at 10k concurrent viewers?
