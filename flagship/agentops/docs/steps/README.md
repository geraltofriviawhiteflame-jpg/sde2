# AgentOps — Step-by-step Build Guides

One guide per build step. Each has: goal, design, task breakdown, definition of done, and the interview story it produces. **New session? Start here.**

**Session bootstrap (every time):**
```bash
python3 -m venv /tmp/verify && /tmp/verify/bin/pip install -r flagship/agentops/server/requirements.txt -r flagship/agentops/server/requirements-dev.txt
/tmp/verify/bin/python flagship/agentops/scripts/serve.py   # pg + migrations + seed + API on :8000
cd flagship/agentops/server && /tmp/verify/bin/pytest -q    # suite must be green before you hack
```

| Step | Guide | Status | Produces interview material about |
|---|---|---|---|
| 1 | [`step-1-foundations.md`](step-1-foundations.md) | ✅ **done** (M1) | Idempotency, entity locks, partial unique indexes, constraint arbitration, migrations, testing |
| 2 | [`step-2-queue-worker.md`](step-2-queue-worker.md) | ⬜ next | Async processing, SKIP LOCKED, at-least-once, worker loops, graceful shutdown |
| 3 | [`step-3-agent-runner.md`](step-3-agent-runner.md) | ⬜ | Tool-calling loops, structured outputs, checkpointing, retries, failure taxonomy |
| 4 | [`step-4-heartbeat-reaper-resume.md`](step-4-heartbeat-reaper-resume.md) | ⬜ | Leases, heartbeats, zombie workers, resume-from-checkpoint — the flagship story |
| 5 | [`step-5-real-llm-mcp.md`](step-5-real-llm-mcp.md) | ⬜ | Real providers, MCP servers, cost/latency accounting |
| 6 | [`step-6-evals-dashboard-loadtest.md`](step-6-evals-dashboard-loadtest.md) | ⬜ | Evals, React dashboard, k6 numbers, deployment — the resume line |

**Rule of the road:** a step is done when its tests pass AND you can explain every design decision in it out loud for 2 minutes without notes.
