from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Env-driven settings — 12-factor, no secrets in code."""

    env: str = "dev"
    database_url: str = "postgresql+psycopg://agentops:agentops@localhost:5432/agentops"
    redis_url: str = "redis://localhost:6379/0"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
