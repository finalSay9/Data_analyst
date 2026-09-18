"""
Centralized application configuration.

Why Pydantic Settings instead of os.environ scattered around the codebase:
- Single source of truth for every config value
- Type validation at startup (fail fast if POSTGRES_PORT isn't an int, etc.)
- Autocomplete/type hints everywhere `settings` is imported
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ENVIRONMENT: str = "development"

    # Postgres
    POSTGRES_USER: str = "analyst"
    POSTGRES_PASSWORD: str = "analyst"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ai_data_analyst"

    # Uploads
    MAX_UPLOAD_SIZE_MB: int = 50

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    """
    Cached so we don't re-parse .env on every import/request.
    Use `get_settings()` (a dependency-injectable function) rather than
    importing a bare `settings` instance directly — this makes it trivial
    to override settings in tests later (FastAPI dependency_overrides).
    """
    return Settings()


settings = get_settings()
