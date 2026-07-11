"""Screening runs — API contract §Screening run."""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession, ProjectDep, ScreeningRunDep
from app.api.errors import database_error
from app.models.workflow_event import WorkflowEvent
from app.schemas.screening import ScreeningRunDetail, WorkflowEventRead
from app.services.results import build_run_detail
from app.services.screening import (
    NoCandidateSitesError,
    find_latest_run,
    find_run_by_idempotency_key,
    run_screening,
)

router = APIRouter(tags=["screenings"])


@router.post(
    "/projects/{project_id}/screenings",
    response_model=ScreeningRunDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_screening(
    project: ProjectDep,
    db: DbSession,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ScreeningRunDetail:
    """Screen every candidate site in the project.

    Spec §18: a repeated request carrying the same ``Idempotency-Key`` returns
    the run that already exists — 200, not 201 — rather than screening twice.
    """
    if idempotency_key:
        existing = find_run_by_idempotency_key(db, project.id, idempotency_key)
        if existing is not None:
            response.status_code = status.HTTP_200_OK
            return build_run_detail(db, existing)

    try:
        run = run_screening(db, project, idempotency_key)
        db.commit()
    except NoCandidateSitesError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_error("run the screening") from exc

    return build_run_detail(db, run)


@router.get("/projects/{project_id}/screenings/latest", response_model=ScreeningRunDetail)
def get_latest_screening(project: ProjectDep, db: DbSession) -> ScreeningRunDetail:
    """The project's most recent run, with its ranked results.

    The results screen needs the project, the run, and the ranking together. 404
    means the project has not been screened yet — a normal state the UI shows as
    an empty state, not an error.
    """
    run = find_latest_run(db, project.id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project.id} has not been screened yet.",
        )
    return build_run_detail(db, run)


@router.get("/screenings/{screening_id}", response_model=ScreeningRunDetail)
def get_screening(run: ScreeningRunDep, db: DbSession) -> ScreeningRunDetail:
    return build_run_detail(db, run)


@router.get("/screenings/{screening_id}/events", response_model=list[WorkflowEventRead])
def list_screening_events(run: ScreeningRunDep, db: DbSession) -> list[WorkflowEvent]:
    """The audit trail for a run, in the order the steps ran (spec §18)."""
    return list(
        db.scalars(
            select(WorkflowEvent)
            .where(WorkflowEvent.screening_run_id == run.id)
            .order_by(WorkflowEvent.sequence)
        ).all()
    )
