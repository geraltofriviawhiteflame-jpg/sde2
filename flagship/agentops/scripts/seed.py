#!/usr/bin/env python
"""Create (or reuse) a demo tenant + agent so you can submit runs from /docs.

Usage: python ../scripts/seed.py   (run from server/ with the venv active)
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "server"))

from app.db import SessionLocal  # noqa: E402
from app.models import Agent, Tenant  # noqa: E402


def main() -> None:
    with SessionLocal() as s:
        tenant = s.query(Tenant).filter_by(name="demo").one_or_none()
        if tenant is None:
            tenant = Tenant(name="demo")
            s.add(tenant)
            s.flush()
        agent = (
            s.query(Agent).filter_by(tenant_id=tenant.id, name="triage-demo").one_or_none()
        )
        if agent is None:
            agent = Agent(
                tenant_id=tenant.id,
                name="triage-demo",
                system_prompt="You triage support tickets.",
                tool_allowlist={"refund": True},
                budget_limits={"max_tokens_per_run": 20000},
            )
            s.add(agent)
        s.commit()
        print("tenant_id:", tenant.id)
        print("agent_id :", agent.id)
        print("try: POST /v1/runs with header Idempotency-Key: <any-uuid>")


if __name__ == "__main__":
    main()
