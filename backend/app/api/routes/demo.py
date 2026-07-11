"""Seeded demo — spec §24, "Load Sample Solar Project"."""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.api.errors import database_error
from app.schemas.project import ProjectRead
from app.schemas.screening import ScreeningRunDetail
from app.services.results import build_run_detail
from app.services.seed import seed_demo_project

router = APIRouter(prefix="/demo", tags=["demo"])


class DemoSeedResponse(BaseModel):
    """The seeded project and its completed screening run."""

    project: ProjectRead
    screening_run: ScreeningRunDetail
    created: bool


@router.post("/seed", response_model=DemoSeedResponse, status_code=status.HTTP_201_CREATED)
def seed_demo(db: DbSession, response: Response) -> DemoSeedResponse:
    """Load the sample solar project: one project, five sites, one completed run.

    Safe to call repeatedly. A second call returns the existing demo — 200, not
    201 — and creates nothing.
    """
    try:
        project, run, created = seed_demo_project(db)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_error("seed the demo project") from exc

    if not created:
        response.status_code = status.HTTP_200_OK

    return DemoSeedResponse(
        project=ProjectRead.model_validate(project),
        screening_run=build_run_detail(db, run),
        created=created,
    )
