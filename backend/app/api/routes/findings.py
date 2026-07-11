"""Risk findings — API contract §Risk finding.

This router owns every finding path, whatever produced the finding. Deterministic
screening and document analysis both write ``risk_findings`` and the site page
shows them together, so splitting the path across two routers would mean one
source silently shadowing the other.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, SiteDep
from app.models.risk_finding import RiskFinding
from app.schemas.document import ReviewFindingRequest
from app.schemas.finding import RiskFindingRead
from app.services.document_errors import DocumentError
from app.services.document_review import review_finding

router = APIRouter(tags=["findings"])


@router.get("/sites/{site_id}/findings", response_model=list[RiskFindingRead])
def list_site_findings(site: SiteDep, db: DbSession) -> list[RiskFinding]:
    """Every finding for a site — deterministic and document-derived alike.

    Evidence is eager-loaded: a document-derived claim is only meaningful with the
    excerpt it rests on, and the UI must never show one without the other.
    """
    return list(
        db.scalars(
            select(RiskFinding)
            .where(RiskFinding.site_id == site.id)
            .options(selectinload(RiskFinding.evidence))
            .order_by(RiskFinding.created_at)
        ).all()
    )


@router.patch("/findings/{finding_id}/review", response_model=RiskFindingRead)
def review_site_finding(
    finding_id: str,
    request: ReviewFindingRequest,
    db: DbSession,
) -> RiskFinding:
    """Approve, edit, reject, or escalate a finding.

    Append-only: each decision writes a new ``reviews`` row and the extracted
    original is preserved, so an edit never destroys what the document actually
    said (spec §9.3).
    """
    try:
        return review_finding(db, finding_id=finding_id, request=request)
    except DocumentError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
