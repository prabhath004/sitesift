"""Diligence brief — spec §8.1G.

The contract left ``GET /api/sites/{site_id}/brief`` undefined in v1 and said the
agent that first needed one should propose it. The end-to-end workflow needs it,
so it is defined in docs/API_CONTRACT.md and implemented here. It reads back what
screening and review already produced and computes nothing new.
"""

from fastapi import APIRouter

from app.api.deps import DbSession, SiteDep
from app.schemas.brief import SiteBriefRead
from app.services.results import build_site_brief

router = APIRouter(tags=["briefs"])


@router.get("/sites/{site_id}/brief", response_model=SiteBriefRead)
def get_site_brief(site: SiteDep, db: DbSession) -> SiteBriefRead:
    return build_site_brief(db, site)
