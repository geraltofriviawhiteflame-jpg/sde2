# Step 5 — Real LLM provider + your MCP server

> Goal: swap FakeLLM for a real provider behind the same `LLMProtocol`, and expose the
> tools through **your own MCP server** (TypeScript, npm) — making your existing MCP
> experience visible on your resume/GitHub. Needs your API key (local machine).

## 1. Design

### Provider adapter
- `app/llm/openai_compat.py` — implements `LLMProtocol` against OpenAI-compatible chat
  completions (works for OpenAI, Groq, Together, local Ollama — key + base_url from env)
- Retries: 429/5xx → exponential backoff + jitter (max 3), honoring `Retry-After`;
  timeout per call; **per-provider circuit breaker** (fail fast while provider is down)
- Cost table: `app/llm/pricing.py` — model → $/1M input+output tokens; `LLMResult.usage`
  → USD at checkpoint time (prices change; store model + price snapshot per step)
- Never block the event loop: async client or `run_in_executor` in the worker

### MCP server (TypeScript → npm)
- Small, real, useful: e.g. `@you/mcp-orders` — an orders service (pg or sqlite) with
  tools: `lookup_order`, `get_order_status`, `refund_order` (idempotent, takes dedupe
  token — mirror of the Python tool semantics)
- stdio transport; tests (vitest); GitHub Actions; README with a demo GIF; publish to npm
- AgentOps connects: Python MCP client runs the server as a subprocess; `ToolRegistry`
  wraps MCP tools — the platform's "tools are MCP servers" claim becomes true

### Config/secrets
- `.env` additions: `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MCP_ORDERS_CMD`
- API keys for *tenants* → AgentOps itself (hashed `api_keys` table + auth dependency)
  — replaces the `tenant_id`-in-body TODO from Step 1

## 2. Task breakdown
- [ ] Provider adapter + pricing table + backoff/circuit breaker (+ fake retryable
      server test via `respx`/httpx mock)
- [ ] Auth: `X-API-Key` → tenant resolution (hash stored, constant-time compare) +
      migration `0004` for `api_keys` + tests (401/403 paths)
- [ ] TS MCP server skeleton → tools → tests → CI → npm publish (can be its own weekend)
- [ ] Python MCP client + registry integration; demo agent uses MCP tools end-to-end
- [ ] Live demo with a real model: run triage on a fake order; costs visible per step

## 3. Definition of done
- [ ] Same agent runs on FakeLLM in CI, real LLM locally — zero code difference, env only
- [ ] MCP server live on npm with README; AgentOps calls it as a subprocess
- [ ] Cost per run visible and plausible against the pricing table

## 4. Interview stories
- "How do you abstract LLM providers?" — protocol + adapter + why pricing snapshots
- "What did you ship open-source?" — the MCP server (stars/issues = public proof)
- Rate limits: backoff/jitter/circuit breaker — with the retry-test as evidence

## 5. Discuss before building
1. Which provider first (cheapest reliable)? Which model for the judge later?
2. MCP stdio vs HTTP transport for our worker model — implications for tool timeouts?
3. Where do API keys hash — why store only the hash, and what's the rotation story?
