"""Risk findings — API contract §Risk finding.

Read only on this branch. ``PATCH /api/findings/{finding_id}/review`` belongs to
the human-review flow, which this branch does not build (spec §8.1F).
"""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession, SiteDep
from app.models.risk_finding import RiskFinding
from app.schemas.finding import RiskFindingRead

router = APIRouter(tags=["findings"])


@router.get("/sites/{site_id}/findings", response_model=list[RiskFindingRead])
def list_site_findings(site: SiteDep, db: DbSession) -> list[RiskFinding]:
    return list(
        db.scalars(
            select(RiskFinding)
            .where(RiskFinding.site_id == site.id)
            .order_by(RiskFinding.created_at)
        ).all()
    )
