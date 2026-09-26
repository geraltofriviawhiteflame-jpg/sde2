# Step 3 — Agent Runner: the LLM → tool → checkpoint loop

> Goal: replace the stub executor with the real agent loop: build prompt → LLM call →
> structured output → tool call (via registry) → repeat → final answer. **FakeLLM** keeps
> this deterministic and free. Every completed step = a checkpoint row.

## 1. Design

### The loop
```
context = run.input + agent.system_prompt
for seq in 1..max_steps:
    resp = llm.complete(context)                     # Step LLM
    write checkpoint(seq, 'llm', resp)               # tokens, cost, latency
    parsed = schema_validate(resp)                   # failure: schema_violation
    if parsed.action == "final_answer":
        finish(run, output=parsed.value); return
    tool = registry.get(parsed.tool)                 # allowlist check!
    result = tool.call(parsed.args)                  # Step tool — IRREVERSIBLE boundary
    write checkpoint(seq, 'tool', result)
    context.append(parsed, result)
finish(run, error="max_steps_exceeded")
```

### Key pieces
- **`FakeLLM`** — scripted: constructor takes a list of responses; `complete()` pops one,
  returns canned tokens/usage. Deterministic tests: script it to call a tool, then to
  answer. Later, `OpenAICompatLLM` implements the same protocol (Step 5).
- **`ToolRegistry`** — tools registered per agent, gated by `tool_allowlist`.
  First tool: `lookup_order(ticket_id)` (pure read — safe). The dangerous `refund`
  tool comes with Step 4, where guardrails matter.
- **Structured output** — pydantic model `AgentDecision {action: tool_call|final_answer,
  tool?, args?, value?}`; validation failure → 1 auto-repair retry ("your JSON was
  invalid: <err>") → then `schema_violation` failure class. (Eval taxonomy begins here.)
- **Checkpoints** — every step row written in its own transaction *after* success
  (step output + tokens + cost). On retry/resume: skip `seq <= max(existing seq)`.
- **Token/cost accounting** — per-step and roll-up to `runs.prompt_tokens /
  completion_tokens / cost_usd`. FakeLLM reports fake-but-realistic usage.

## 2. Task breakdown
- [ ] `app/llm/base.py` — `LLMProtocol.complete(messages) -> LLMResult(text, usage)`
- [ ] `app/llm/fake.py` — scripted responses + usage
- [ ] `app/schemas.py` — `AgentDecision` pydantic model + validation helper
- [ ] `app/tools.py` — registry + `lookup_order` + allowlist enforcement
- [ ] `app/executors/agent_runner.py` — the loop above, checkpoint per step
- [ ] Failure classes wired into `evals.failure_class` on terminal failure
- [ ] Tests: happy path (tool then answer; steps rows correct) · invalid JSON → repair
      retry → success · invalid twice → failed + `schema_violation` · tool not in
      allowlist → refused, run continues/ends correctly · max_steps exceeded ·
      crash mid-run → requeue (Step 2) → **resume skips completed steps**
- [ ] Live demo: seed a scripted agent; run via API; `GET /v1/runs/{id}` shows steps

## 3. Definition of done
- [ ] Full loop runs end-to-end against FakeLLM in tests AND on the live server
- [ ] Re-running after simulated crash does not repeat an already-checkpointed LLM call
- [ ] You can whiteboard the loop with checkpoint boundaries from memory

## 4. Interview stories
- Structured outputs: why schema-validate + repair-retry beats hoping
- Checkpoint granularity: every step vs only before side effects — cost of each
- "What's your failure taxonomy?" — enum from DESIGN.md, each class maps to handling

## 5. Discuss before building
1. Where exactly does the checkpoint transaction sit relative to the tool call — and why
   "after" (not "before+after")?
2. If the tool call succeeded but the worker died before checkpointing it, what happens
   on resume? (This is THE at-least-once pain — hold for Step 4's idempotent-tools idea.)
3. max_steps=8 vs budget_tokens=20000 — which guard fires first in practice?
