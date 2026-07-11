"""Risk findings — one shape for every source.

``FindingCategory``, ``FindingGroup``, and ``RequirementCategory`` are mirrored in
``frontend/types/api.ts`` and documented in ``docs/API_CONTRACT.md``.

Integration note. Deterministic screening and document analysis each arrived with
their own finding schema (``RiskFindingRead`` and ``DocumentFindingResponse``)
over the same ``risk_findings`` table. They are reconciled into ``RiskFindingRead``
here: the document-only fields are optional and stay ``None`` for deterministic
findings, and ``evidence`` is a list that is empty for them. A document-derived
finding without evidence is invalid and is never persisted (CLAUDE.md rule 2), so
an empty list on a ``DOCUMENT`` finding cannot occur.
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
from app.schemas.evidence import EvidenceResponse


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

    ``REQUIREMENT`` was added at integration for document-derived permitting
    requirements. Filing them under ``RISK`` would assert that "a conditional-use
    permit is required" is a problem with the site, which it is not — it is an
    obligation, and it gets its own list on the site page.
    """

    POSITIVE_SIGNAL = "positive_signal"
    RISK = "risk"
    MISSING_INFORMATION = "missing_information"
    REQUIREMENT = "requirement"


class RequirementCategory(StrEnum):
    """The kind of permitting obligation a document-derived finding states.

    Distinct from ``FindingCategory``, which says which of the four scoring
    dimensions a finding belongs to. A document finding is always
    ``FindingCategory.PERMITTING``; this says what sort of permitting item it is.
    """

    USE_PERMISSION = "use_permission"
    SETBACK = "setback"
    PUBLIC_HEARING = "public_hearing"
    DECOMMISSIONING = "decommissioning"
    FINANCIAL_SECURITY = "financial_security"
    ENVIRONMENTAL_STUDY = "environmental_study"
    TRAFFIC_STUDY = "traffic_study"
    APPLICATION_REQUIREMENT = "application_requirement"
    OTHER = "other"


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
    """A persisted finding as returned by the API, whatever produced it."""

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

    # Document-derived findings only; None / False on a deterministic finding.
    requirement_category: RequirementCategory | None = None
    original_title: str | None = None
    original_description: str | None = None
    requires_human_review: bool = False

    # Required on a DOCUMENT finding, empty on every other source.
    evidence: list[EvidenceResponse] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime
