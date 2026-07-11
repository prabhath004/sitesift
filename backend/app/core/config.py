"""Application configuration.

Settings are read from the environment (and from a local ``.env`` file when
present). The foundation must start with no environment configured at all, so
every setting has a working default and no AI key is required.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SiteSift API"
    api_prefix: str = "/api"
    environment: str = "development"

    # SQLite by default so the foundation runs with no database server.
    # docker compose overrides this with a Postgres URL.
    database_url: str = "sqlite:///./sitesift.db"

    backend_port: int = 8000

    # Origins allowed to call the API. The frontend dev server port is
    # configurable per worktree, so this is a list rather than a single value.
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Optional. Document analysis (a future worktree) needs one of these;
    # nothing in the foundation does.
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Document-analysis defaults. The upload directory is outside the repo by
    # default so tests and local runs do not dirty the worktree.
    document_max_upload_bytes: int = 10 * 1024 * 1024
    document_storage_dir: str = "/tmp/sitesift-documents"
    document_chunk_max_chars: int = 1200
    document_chunk_overlap_chars: int = 120


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Use as a FastAPI dependency or call directly."""
    return Settings()
