"""initial schema — tenants, agents, runs, steps, idempotency_keys, evals

Revision ID: 0001
Revises:
Create Date: 2026-09-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    run_status = sa.Enum("queued", "running", "succeeded", "failed", "cancelled", name="run_status")
    step_type = sa.Enum("llm", "tool", "guardrail", name="step_type")
    step_status = sa.Enum("running", "succeeded", "failed", "skipped", name="step_status")
    eval_failure_class = sa.Enum(
        "tool_error",
        "llm_refusal",
        "schema_violation",
        "budget_exceeded",
        "timeout",
        "hallucination_flagged",
        name="eval_failure_class",
    )

    op.create_table(
        "tenants",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "agents",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("tool_allowlist", pg.JSONB(), nullable=False),
        sa.Column("budget_limits", pg.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agents_tenant_id", "agents", ["tenant_id"])

    op.create_table(
        "runs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("agent_id", pg.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("parent_run_id", pg.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=True),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("status", run_status, nullable=False),
        sa.Column("input", pg.JSONB(), nullable=False),
        sa.Column("output", pg.JSONB(), nullable=True),
        sa.Column("error", pg.JSONB(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_run_idem"),
    )
    op.create_index("ix_runs_tenant_id", "runs", ["tenant_id"])
    op.create_index("ix_runs_agent_id", "runs", ["agent_id"])
    op.create_index("ix_runs_status", "runs", ["status"])
    # Entity lock: at most one ACTIVE run per (tenant, entity). Partial index —
    # terminal runs leave the index, releasing the slot automatically.
    op.create_index(
        "uq_one_active_run_per_entity",
        "runs",
        ["tenant_id", "entity_type", "entity_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )

    op.create_table(
        "steps",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", pg.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("type", step_type, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("input", pg.JSONB(), nullable=False),
        sa.Column("output", pg.JSONB(), nullable=True),
        sa.Column("status", step_status, nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_steps_run_id", "steps", ["run_id"])

    op.create_table(
        "idempotency_keys",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("run_id", pg.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("response_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "evals",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", pg.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("judge_model", sa.String(100), nullable=True),
        sa.Column("deterministic_pass", sa.Boolean(), nullable=True),
        sa.Column("scores", pg.JSONB(), nullable=True),
        sa.Column("failure_class", eval_failure_class, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evals_run_id", "evals", ["run_id"])


def downgrade() -> None:
    op.drop_table("evals")
    op.drop_table("idempotency_keys")
    op.drop_table("steps")
    op.drop_index("uq_one_active_run_per_entity", table_name="runs")
    op.drop_table("runs")
    op.drop_table("agents")
    op.drop_table("tenants")
    for name in ("eval_failure_class", "step_status", "step_type", "run_status"):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
