"""Screening runs, site scores, score breakdowns, and workflow events.

Contract additions relative to docs/API_CONTRACT.md v1 (all additive, all
described in docs/BACKEND_CONTRACT_NOTES.md):

* ``PermittingAnalysisStatus`` — permitting readiness cannot be assessed on this
  branch, and the score must not pretend otherwise.
* ``SiteScore.breakdown`` and ``SiteScore.rank`` — spec §9.5 requires that every
  deduction be inspectable, so the score ships with the records that produced it.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import (
    CandidateSiteId,
    FindingSeverity,
    ProjectId,
    RecommendationStatus,
    ScreeningRunId,
    ScreeningRunStatus,
    SiteScoreId,
)
from app.schemas.document import DocumentResponse
from app.schemas.finding import FindingCategory, RiskFindingRead
from app.schemas.project import ProjectRead
from app.schemas.site import CandidateSiteRead


class PermittingAnalysisStatus(StrEnum):
    """Whether the permitting category rests on a real document.

    Deterministic screening never analyzes a document, so a run on this branch
    always reports ``NOT_ANALYZED``. ``ANALYZED`` is reserved for the
    document-analysis branch, which owns the only code allowed to set it.
    """

    NOT_ANALYZED = "not_analyzed"
    PENDING_DOCUMENT_REVIEW = "pending_document_review"
    ANALYZED = "analyzed"


class ScoreBreakdownItem(BaseModel):
    """One scoring rule, and what it awarded. Spec §9.5 — show every deduction."""

    category: FindingCategory
    rule: str
    actual_value: float | None = None
    threshold_value: float | None = None
    points_possible: int
    points_awarded: int
    severity: FindingSeverity
    explanation: str


class SiteScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: SiteScoreId
    screening_run_id: ScreeningRunId
    site_id: CandidateSiteId
    overall_score: int = Field(ge=0, le=100)
    site_suitability_score: int = Field(ge=0, le=25)
    environmental_score: int = Field(ge=0, le=25)
    access_score: int = Field(ge=0, le=25)
    permitting_score: int = Field(ge=0, le=25)
    permitting_status: PermittingAnalysisStatus
    recommendation_status: RecommendationStatus
    rank: int
    explanation: str
    breakdown: list[ScoreBreakdownItem]
    created_at: datetime


class ScreeningRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: ScreeningRunId
    project_id: ProjectId
    status: ScreeningRunStatus
    idempotency_key: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime


class SiteScreeningResult(BaseModel):
    """One ranked site, with everything needed to explain its result.

    The counts and the next action are computed here rather than in the UI. They
    are conclusions drawn from findings and a recommendation status, and the
    backend is the only place allowed to draw them (CLAUDE.md, spec §9.1).
    """

    site: CandidateSiteRead
    score: SiteScoreRead
    positive_signals: list[RiskFindingRead]
    risks: list[RiskFindingRead]
    permitting_requirements: list[RiskFindingRead]
    missing_information: list[RiskFindingRead]
    high_risk_finding_count: int
    warning_count: int
    recommended_next_action: str


class ScreeningRunDetail(ScreeningRunRead):
    """A run plus its ranked results, highest score first.

    The project is embedded because every screen that shows a ranking also shows
    the criteria the ranking was produced against; sending them together means the
    UI cannot render a score next to a stale threshold.
    """

    project: ProjectRead
    results: list[SiteScreeningResult]


class SiteDetail(BaseModel):
    """One site with its most recent screening result, if it has been screened.

    ``score`` is ``None`` until a run has scored the site — an unscreened site is
    a normal state, not an error.

    ``permitting_requirements`` are the document-derived findings for the site,
    each carrying its evidence and its review status. They are listed separately
    from ``risks`` because a permitting obligation is not a defect in the site,
    and from ``missing_information`` because it is not an unknown.
    """

    project: ProjectRead
    site: CandidateSiteRead
    score: SiteScoreRead | None
    positive_signals: list[RiskFindingRead]
    risks: list[RiskFindingRead]
    permitting_requirements: list[RiskFindingRead]
    missing_information: list[RiskFindingRead]
    documents: list[DocumentResponse]
    recommended_next_action: str


class WorkflowEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    screening_run_id: ScreeningRunId
    step_name: str
    status: str
    input_summary: str | None
    output_summary: str | None
    duration_ms: int | None
    error_message: str | None
    created_at: datetime
