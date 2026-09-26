-- ============================================================================
-- AgentOps — Step 1 schema (practice build)
-- Run on your device:  psql -d agentops -f schema.sql
-- Requires Postgres 13+ (gen_random_uuid is built in)
-- Inspect afterwards:  \d tenants   \d agents   \d runs   etc.
-- Mirrors: flagship/agentops/server/alembic/versions/0001_initial_schema.py
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 0. Clean slate (idempotent: safe to run repeatedly)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS evals            CASCADE;
DROP TABLE IF EXISTS idempotency_keys CASCADE;
DROP TABLE IF EXISTS steps            CASCADE;
DROP TABLE IF EXISTS runs             CASCADE;
DROP TABLE IF EXISTS agents           CASCADE;
DROP TABLE IF EXISTS tenants          CASCADE;

-- ---------------------------------------------------------------------------
-- 1. tenants — who pays you. Every other table hangs off this.
-- ---------------------------------------------------------------------------
CREATE TABLE tenants (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL UNIQUE,
    plan        text NOT NULL DEFAULT 'free',          -- free | pro | enterprise
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 2. agents — a registered agent = prompt + model + which tools it may use
--    tool_allowlist / budget_limits are JSONB: schema evolves per tenant
--    without migrations (validate in app code).
-- ---------------------------------------------------------------------------
CREATE TABLE agents (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      uuid NOT NULL REFERENCES tenants(id),   -- RESTRICT by default: keep audit
    name           text NOT NULL,
    system_prompt  text NOT NULL DEFAULT '',
    model          text NOT NULL DEFAULT 'gpt-4o-mini',
    tool_allowlist jsonb NOT NULL DEFAULT '{}',   -- e.g. {"refund": true, "lookup": true}
    budget_limits  jsonb NOT NULL DEFAULT '{}',   -- e.g. {"max_tokens_per_run": 20000}
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_agents_tenant_id ON agents (tenant_id);

-- ---------------------------------------------------------------------------
-- 3. runs — ONE EXECUTION OF AN AGENT. The most important table.
--    Two independent uniqueness layers (this is the whole design):
--      uq_run_idem                    : same REQUEST twice  -> 200 w/ original
--      uq_one_active_run_per_entity   : same ENTITY twice   -> 409 busy
-- ---------------------------------------------------------------------------
CREATE TABLE runs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id),
    agent_id        uuid NOT NULL REFERENCES agents(id),
    idempotency_key text NOT NULL,                        -- caller-provided (header)
    parent_run_id   uuid REFERENCES runs(id),             -- set on replay forks
    entity_type     text,                                 -- e.g. 'ticket' (nullable:
    entity_id       text,                                 --  not all runs lock an entity)
    status          text NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
    input           jsonb NOT NULL DEFAULT '{}',
    output          jsonb,
    error           jsonb,                                -- {"reason": "...", "detail": ...}
    prompt_tokens     integer NOT NULL DEFAULT 0,
    completion_tokens integer NOT NULL DEFAULT 0,
    cost_usd          numeric(12,6) NOT NULL DEFAULT 0,   -- money is NUMERIC, never float
    trace_id        text,                                 -- OTel trace link (Step 6)
    created_at      timestamptz NOT NULL DEFAULT now(),
    started_at      timestamptz,
    finished_at     timestamptz,

    -- LAYER 1: the same request can only ever create ONE run
    CONSTRAINT uq_run_idem UNIQUE (tenant_id, idempotency_key)
);

-- LAYER 2: at most one ACTIVE run per business entity, per tenant.
-- PARTIAL index: only rows matching the WHERE participate — so history is
-- unlimited, and a terminal status automatically frees the slot.
CREATE UNIQUE INDEX uq_one_active_run_per_entity
    ON runs (tenant_id, entity_type, entity_id)
    WHERE status IN ('queued', 'running');

-- Listing a tenant's runs, newest first (cursor pagination later)
CREATE INDEX ix_runs_tenant_created ON runs (tenant_id, created_at DESC);
-- Queue claims (Step 2 will thank you): only queued rows are candidates
CREATE INDEX ix_runs_queued ON runs (created_at) WHERE status = 'queued';

-- ---------------------------------------------------------------------------
-- 4. steps — the checkpoint unit. One LLM call or tool call.
--    A completed step = "resume from here" boundary (Step 3/4).
-- ---------------------------------------------------------------------------
CREATE TABLE steps (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,  -- steps die with run
    seq         integer NOT NULL,                 -- 1,2,3… order within the run
    type        text NOT NULL CHECK (type IN ('llm','tool','guardrail')),
    name        text NOT NULL,                    -- 'gpt-4o-mini' | 'refund' | 'pii_check'
    input       jsonb NOT NULL DEFAULT '{}',
    output      jsonb,
    status      text NOT NULL DEFAULT 'running'
                CHECK (status IN ('running','succeeded','failed','skipped')),
    tokens      integer NOT NULL DEFAULT 0,
    cost_usd    numeric(12,6) NOT NULL DEFAULT 0,
    latency_ms  integer NOT NULL DEFAULT 0,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, seq)
);
CREATE INDEX ix_steps_run_id ON steps (run_id, seq);

-- ---------------------------------------------------------------------------
-- 5. idempotency_keys — response memory for key reuse (full-response replay).
--    runs.uq_run_idem is the dedupe TRUTH; this table stores the response
--    snapshot + expiry so a late retry can be served identically.
-- ---------------------------------------------------------------------------
CREATE TABLE idempotency_keys (
    tenant_id     uuid NOT NULL REFERENCES tenants(id),
    key           text NOT NULL,
    run_id        uuid NOT NULL REFERENCES runs(id),
    response_hash text,                              -- sha256 of response body
    created_at    timestamptz NOT NULL DEFAULT now(),
    expires_at    timestamptz,                       -- 24h TTL; cleaned by a sweep job
    PRIMARY KEY (tenant_id, key)
);

-- ---------------------------------------------------------------------------
-- 6. evals — scoring of a run (deterministic checks + LLM-as-judge, Step 6)
-- ---------------------------------------------------------------------------
CREATE TABLE evals (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id             uuid NOT NULL REFERENCES runs(id),
    judge_model        text,
    deterministic_pass boolean,
    scores             jsonb,      -- {"faithfulness": 0.83, "helpfulness": 0.91}
    failure_class      text CHECK (failure_class IN
                       ('tool_error','llm_refusal','schema_violation',
                        'budget_exceeded','timeout','hallucination_flagged')),
    notes              text,
    created_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_evals_run_id ON evals (run_id);

-- ============================================================================
-- EXPERIMENTS — uncomment and run scene by scene (or load sql_demo.py)
-- ============================================================================
-- ① happy path
-- INSERT INTO runs (tenant_id, agent_id, idempotency_key, entity_type, entity_id)
-- SELECT t.id, a.id, 'k1', 'ticket', '123' FROM tenants t, agents a LIMIT 1
-- RETURNING id, status;                                  -- expect: queued
--
-- ② same key twice -> which error? (expect uq_run_idem)
-- (run ① again unchanged)
--
-- ③ different key, same ACTIVE ticket -> which error? (expect the partial index)
-- INSERT INTO runs (tenant_id, agent_id, idempotency_key, entity_type, entity_id)
-- SELECT t.id, a.id, 'k2', 'ticket', '123' FROM tenants t, agents a LIMIT 1;
--
-- ④ finish the run, then retry ③ -> why does it work now?
-- UPDATE runs SET status='succeeded' WHERE idempotency_key='k1';
--
-- ⑤ check yourself: what does this return and why?
-- SELECT count(*) FROM runs WHERE entity_id IS NULL;      -- hint: did ② insert?
--
-- ⑥ prove NULLs are distinct: two entity-less runs, both succeed
-- INSERT INTO runs (tenant_id, agent_id, idempotency_key)
--   SELECT t.id, a.id, 'n1' FROM tenants t, agents a LIMIT 1;
-- INSERT INTO runs (tenant_id, agent_id, idempotency_key)
--   SELECT t.id, a.id, 'n2' FROM tenants t, agents a LIMIT 1;
--
-- ⑦ seed data for your API practice
-- INSERT INTO tenants (name) VALUES ('demo');
-- INSERT INTO agents (tenant_id, name, tool_allowlist)
--   SELECT id, 'triage-demo', '{"refund": true}' FROM tenants WHERE name='demo';
