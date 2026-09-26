from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class RunStatus(str, PyEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class StepType(str, PyEnum):
    llm = "llm"
    tool = "tool"
    guardrail = "guardrail"


class StepStatus(str, PyEnum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    skipped = "skipped"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agents: Mapped[list["Agent"]] = relationship(back_populates="tenant")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(100), default="gpt-4o-mini")
    tool_allowlist: Mapped[dict] = mapped_column(JSONB, default=dict)
    budget_limits: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="agents")


class Run(Base):
    """One agent execution. Idempotency: UNIQUE (tenant_id, idempotency_key).

    Entity lock: at most one ACTIVE (queued/running) run per business entity
    (e.g. ticket) per tenant — a PARTIAL unique index, so history is unlimited
    but concurrency is capped at one. Terminating the run releases the slot.
    """

    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_run_idem"),
        Index(
            "uq_one_active_run_per_entity",
            "tenant_id",
            "entity_type",
            "entity_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    parent_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("runs.id"), nullable=True
    )  # set on replay forks
    # Business entity this run acts on (e.g. entity_type="ticket", entity_id="123").
    # Nullable: not every run targets a lockable entity.
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), default=RunStatus.queued, index=True
    )
    input: Mapped[dict] = mapped_column(JSONB, default=dict)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list["Step"]] = relationship(
        back_populates="run", order_by="Step.seq", cascade="all, delete-orphan"
    )


class Step(Base):
    """Checkpoint unit — one successful step = a resumable boundary."""

    __tablename__ = "steps"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[StepType] = mapped_column(Enum(StepType, name="step_type"))
    name: Mapped[str] = mapped_column(String(255))
    input: Mapped[dict] = mapped_column(JSONB, default=dict)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[StepStatus] = mapped_column(
        Enum(StepStatus, name="step_status"), default=StepStatus.running
    )
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped["Run"] = relationship(back_populates="steps")


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id"))
    response_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvalFailureClass(str, PyEnum):
    tool_error = "tool_error"
    llm_refusal = "llm_refusal"
    schema_violation = "schema_violation"
    budget_exceeded = "budget_exceeded"
    timeout = "timeout"
    hallucination_flagged = "hallucination_flagged"


class Eval(Base):
    __tablename__ = "evals"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id"), index=True)
    judge_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deterministic_pass: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    failure_class: Mapped[EvalFailureClass | None] = mapped_column(
        Enum(EvalFailureClass, name="eval_failure_class"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
