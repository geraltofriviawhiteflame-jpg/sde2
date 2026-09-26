from fastapi import FastAPI

from app.config import get_settings


def create_app() -> FastAPI:
    application = FastAPI(title="AgentOps", version="0.1.0")
    application.state.settings = get_settings()

    from app.api_runs import router

    application.include_router(router)
    return application


app = create_app()
