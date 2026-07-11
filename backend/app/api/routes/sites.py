"""Candidate sites — API contract §Candidate site."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession, ProjectDep, SiteDep
from app.api.errors import database_error
from app.models.candidate_site import CandidateSite
from app.schemas.screening import SiteDetail
from app.schemas.site import CandidateSiteRead, SiteImportResult
from app.services.csv_import import CsvImportError
from app.services.results import build_site_detail
from app.services.site_import import import_sites_csv

router = APIRouter(tags=["sites"])

# Generous for a candidate-site list, small enough that a mistaken PDF upload is
# rejected before it is read into memory.
MAX_CSV_BYTES = 2 * 1024 * 1024


@router.post(
    "/projects/{project_id}/sites/import",
    response_model=SiteImportResult,
    status_code=status.HTTP_201_CREATED,
)
async def import_sites(
    project: ProjectDep, db: DbSession, file: Annotated[UploadFile, File()]
) -> SiteImportResult:
    """Import candidate sites from a CSV.

    Rows that fail validation are reported and not persisted; rows already
    imported are reported as duplicates and not persisted twice. The valid rows
    are written in one transaction, so a failure leaves the project as it was.
    """
    raw = await file.read()
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The uploaded file exceeds the {MAX_CSV_BYTES // (1024 * 1024)} MB limit.",
        )

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not valid UTF-8 text. Upload a CSV file.",
        ) from exc

    try:
        result = import_sites_csv(db, project, content)
        db.commit()
    except CsvImportError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_error("import the candidate sites") from exc

    return result


@router.get("/projects/{project_id}/sites", response_model=list[CandidateSiteRead])
def list_sites(project: ProjectDep, db: DbSession) -> list[CandidateSite]:
    """In import order, which is the order the user gave us."""
    return list(
        db.scalars(
            select(CandidateSite)
            .where(CandidateSite.project_id == project.id)
            .order_by(CandidateSite.sequence)
        ).all()
    )


@router.get("/sites/{site_id}", response_model=SiteDetail)
def get_site(site: SiteDep, db: DbSession) -> SiteDetail:
    """A site with its latest score, positive signals, risks, and missing information."""
    return build_site_detail(db, site)
