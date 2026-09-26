from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import IdempotencyKey, Run, RunStatus
from app.serializers import run_to_dict

router = APIRouter()

TERMINAL_RUN_STATES = {RunStatus.succeeded, RunStatus.failed, RunStatus.cancelled}


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.post("/v1/runs", status_code=202)
def create_run(
    body: dict,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    """Submit an agent run.

    Two independent uniqueness layers (docs/DESIGN.md D1 + discussion 2026-09-26):

    1. Idempotency key  — dedupes the SAME request. A retry with the same key
       returns the ORIGINAL run (200), because the caller just wants their answer.
    2. Entity lock      — blocks any CONCURRENT second run on the same business
       entity, even from a different caller (409), because the entity is busy.

    No "check then insert": we INSERT and let Postgres's unique constraints
    arbitrate. The losing transaction reads which constraint refused it
    (constraint_name on the IntegrityError) and answers accordingly.
    """
    tenant_id = body.get("tenant_id")  # TODO(M2): resolve from API key auth instead
    agent_id = body.get("agent_id")
    if not tenant_id or not agent_id:
        raise HTTPException(422, "tenant_id and agent_id are required")
    entity_type = body.get("entity_type")
    entity_id = body.get("entity_id")
    if (entity_type is None) != (entity_id is None):
        raise HTTPException(422, "entity_type and entity_id must be sent together")

    run = Run(
        tenant_id=tenant_id,
        agent_id=agent_id,
        idempotency_key=idempotency_key,
        entity_type=entity_type,
        entity_id=entity_id,
        status=RunStatus.queued,
        input=body.get("input", {}),
    )
    db.add(run)
    try:
        db.flush()  # assigns run.id; may violate either uniqueness layer
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc, "orig", None), "diag", None)
        violated = getattr(constraint, "constraint_name", "")
        if violated == "uq_run_idem" or not violated and _find_by_key(db, tenant_id, idempotency_key):
            # Same request as an existing run → hand back the original (200).
            existing = _find_by_key(db, tenant_id, idempotency_key)
            if existing is not None:
                return JSONResponse(run_to_dict(existing), status_code=200)
            # Winner hasn't committed yet → sub-millisecond double-submit.
            raise HTTPException(409, "request in flight with this Idempotency-Key")
        # Otherwise it's the entity lock refusing a concurrent second run.
        raise HTTPException(
            409,
            f"{entity_type} {entity_id} is busy: an active run already exists",
        )
    # TODO(M2): enqueue agent_runner Celery task here (+ idempotency_keys row
    # with response hash & expiry, written in the same transaction).
    return run_to_dict(run)


def _find_by_key(db: Session, tenant_id, key: str) -> Run | None:
    return db.scalar(
        select(Run).where(Run.tenant_id == tenant_id, Run.idempotency_key == key)
    )


@router.get("/v1/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)) -> dict:
    run = db.scalar(select(Run).where(Run.id == run_id))
    if run is None:
        raise HTTPException(404, "run not found")
    return run_to_dict(run)


@router.post("/v1/runs/{run_id}/replay", status_code=202)
def replay_run(
    run_id: str,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> dict:
    """Fork a new run from the last successful step (DESIGN.md D2).

    Replays get a NEW idempotency key by contract; parent_run_id links lineage.
    Replaying an ACTIVE run is refused: the entity is still locked.
    """
    source = db.scalar(select(Run).where(Run.id == run_id))
    if source is None:
        raise HTTPException(404, "run not found")
    if source.status not in TERMINAL_RUN_STATES:
        raise HTTPException(409, "run is still active — cancel it before replaying")

    replay = Run(
        tenant_id=source.tenant_id,
        agent_id=source.agent_id,
        idempotency_key=idempotency_key,
        parent_run_id=source.id,
        entity_type=source.entity_type,
        entity_id=source.entity_id,
        status=RunStatus.queued,
        input=source.input,
    )
    try:
        db.add(replay)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "entity is busy: an active run already exists")
    return run_to_dict(replay)
