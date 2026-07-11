"""Database engine and session wiring.

The engine is created from ``Settings.database_url``. SQLite is the local
default; Postgres is used in docker compose and is the production target.
"""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_connect_args: dict[str, Any] = {}
if settings.database_url.startswith("sqlite"):
    # FastAPI serves requests from a threadpool; SQLite needs this to allow it.
    _connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)
session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session."""
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
