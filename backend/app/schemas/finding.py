"""Risk findings — API contract additions proposed in docs/BACKEND_CONTRACT_NOTES.md.

``FindingCategory`` and ``FindingGroup`` are new enums. They are deliberately
NOT in ``app/schemas/common.py``: that file is mirrored by ``frontend/types/api.ts``,
which this branch does not own. The frontend mirror is specified in
docs/BACKEND_CONTRACT_NOTES.md for whoever picks it up.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import (
    CandidateSiteId,
    FindingSeverity,
    FindingSourceType,
    ReviewStatus,
    RiskFindingId,
    ScreeningRunId,
)


class FindingCategory(StrEnum):
    """Which screening dimension a finding belongs to.

    The first four mirror the four scoring categories of spec §14.
    ``DATA_COMPLETENESS`` carries known-unknowns that carry no points.
    """

    SITE_SUITABILITY = "site_suitability"
    ENVIRONMENTAL = "environmental"
    ACCESS = "access"
    PERMITTING = "permitting"
    DATA_COMPLETENESS = "data_completeness"


class FindingGroup(StrEnum):
    """How a finding should be presented (spec §10.4).

    Missing information is kept separate from confirmed risks: an absent input is
    not evidence of a problem, and the two must never be conflated in the UI.
    """

    POSITIVE_SIGNAL = "positive_signal"
    RISK = "risk"
    MISSING_INFORMATION = "missing_information"


class FindingDraft(BaseModel):
    """A finding produced by the scoring service, before it is persisted."""

    category: FindingCategory
    group: FindingGroup
    rule: str
    title: str
    description: str
    severity: FindingSeverity
    actual_value: float | None = None
    threshold_value: float | None = None
    value: str | None = None


class RiskFindingRead(BaseModel):
    """A persisted finding as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: RiskFindingId
    site_id: CandidateSiteId
    screening_run_id: ScreeningRunId | None
    source_type: FindingSourceType
    category: FindingCategory
    group: FindingGroup
    rule: str | None
    title: str
    description: str
    severity: FindingSeverity
    value: str | None
    actual_value: float | None
    threshold_value: float | None
    confidence: float | None = Field(default=None, ge=0, le=1)
    review_status: ReviewStatus
    created_at: datetime
    updated_at: datetime
