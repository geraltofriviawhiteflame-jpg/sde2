from app.models import Run


def run_to_dict(run: Run) -> dict:
    return {
        "id": str(run.id),
        "tenant_id": str(run.tenant_id),
        "agent_id": str(run.agent_id),
        "status": run.status.value if run.status else None,
        "input": run.input,
        "output": run.output,
        "error": run.error,
        "prompt_tokens": run.prompt_tokens,
        "completion_tokens": run.completion_tokens,
        "cost_usd": str(run.cost_usd) if run.cost_usd is not None else None,
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
        "entity_type": run.entity_type,
        "entity_id": run.entity_id,
    }
