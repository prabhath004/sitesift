"""Diligence brief — spec §8.1G.

The brief is a *view* over data the rest of the system already produced: the
project, the ranking, the site's score and its breakdown, its findings, its
document-derived permitting requirements and their evidence, and the review state
of each. It computes no new score and states no new fact. Anything shown here can
be traced back to a screening run or a reviewed document finding, which is why it
is safe to print and hand to someone.
"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.document import DocumentResponse
from app.schemas.finding import RiskFindingRead
from app.schemas.project import ProjectRead
from app.schemas.screening import SiteScoreRead
from app.schemas.site import CandidateSiteRead


class BriefRankingEntry(BaseModel):
    """One line of the candidate ranking, as it appears on the results screen."""

    site_id: str
    site_name: str
    rank: int
    overall_score: int
    recommendation_status: str
    is_selected_site: bool


class SiteBriefRead(BaseModel):
    """Everything the printable brief renders, in the order spec §8.1G lists it."""

    generated_at: datetime

    project: ProjectRead
    site: CandidateSiteRead
    score: SiteScoreRead | None

    candidate_ranking: list[BriefRankingEntry]

    positive_signals: list[RiskFindingRead]
    risks: list[RiskFindingRead]
    permitting_requirements: list[RiskFindingRead]
    missing_information: list[RiskFindingRead]

    documents: list[DocumentResponse]
    recommended_next_steps: list[str]
