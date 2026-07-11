"""Shared route dependencies.

Loading a project or a site by id and 404-ing when it is absent is the same in
every router, and getting it wrong leaks an internal error to the client.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.candidate_site import CandidateSite
from app.models.project import Project
from app.models.screening_run import ScreeningRun

DbSession = Annotated[Session, Depends(get_db)]


def get_project(project_id: str, db: DbSession) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found.",
        )
    return project


def get_site(site_id: str, db: DbSession) -> CandidateSite:
    site = db.get(CandidateSite, site_id)
    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate site {site_id} not found.",
        )
    return site


def get_screening_run(screening_id: str, db: DbSession) -> ScreeningRun:
    run = db.get(ScreeningRun, screening_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening run {screening_id} not found.",
        )
    return run


ProjectDep = Annotated[Project, Depends(get_project)]
SiteDep = Annotated[CandidateSite, Depends(get_site)]
ScreeningRunDep = Annotated[ScreeningRun, Depends(get_screening_run)]
