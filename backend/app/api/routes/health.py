"""Health check.

Mounted at the root (``GET /health``), not under ``/api``: it is an
infrastructure probe, used by docker compose, the Superset runner, and the
frontend shell to prove that the two services can talk to each other.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.get("/health", response_model=HealthResponse)
def health(db: DbSession, settings: AppSettings) -> HealthResponse:
    """Report service liveness and whether the database is reachable.

    A missing database does not fail the probe: the API is still up, and the
    frontend shell needs to render either way.
    """
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        database = "unavailable"

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version="0.1.0",
        environment=settings.environment,
        database=database,
    )
