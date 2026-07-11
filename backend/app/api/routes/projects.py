"""Project intake — API contract §Project."""

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession, ProjectDep
from app.api.errors import database_error
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectRead, ProjectStatus

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DbSession) -> Project:
    project = Project(
        name=payload.name,
        project_type=payload.project_type,
        target_capacity_mw=payload.target_capacity_mw,
        minimum_acres=payload.minimum_acres,
        target_state=payload.target_state,
        screening_criteria=payload.screening_criteria.model_dump(),
        notes=payload.notes,
        status=ProjectStatus.ACTIVE,
    )

    try:
        db.add(project)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_error("create the project") from exc

    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(db: DbSession) -> list[Project]:
    """Newest first — the dashboard shows the most recent work at the top."""
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())).all())


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project: ProjectDep) -> Project:
    return project
