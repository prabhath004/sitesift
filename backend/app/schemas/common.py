"""Shared identifiers and status enums — API contract v1 (draft).

SHARED FILE. These enums are the compatibility surface between the backend and
the frontend. Every member here has a one-to-one counterpart in
``frontend/types/api.ts``. Changing a member without changing both files, and
without updating ``docs/API_CONTRACT.md``, breaks other agents' work.

Entity request/response models are NOT defined here. They belong to the agent
that owns the entity (see docs/PARALLEL_TASKS.md) and live in sibling modules
such as ``app/schemas/project.py``.
"""

from enum import StrEnum

# Identifiers are UUID strings at the API boundary. The database may store
# native UUIDs; the wire format is always a string.
ProjectId = str
CandidateSiteId = str
ScreeningRunId = str
SiteScoreId = str
RiskFindingId = str
DocumentId = str
EvidenceId = str
ReviewId = str


class ProjectType(StrEnum):
    """Spec §10.2. ``COMMUNITY_SOLAR`` comes from the §16.1 request example."""

    SOLAR = "solar"
    COMMUNITY_SOLAR = "community_solar"
    BATTERY_STORAGE = "battery_storage"
    DATA_CENTER = "data_center"
    EV_CHARGING = "ev_charging"
    OTHER = "other"


class ScreeningRunStatus(StrEnum):
    """Spec §18 — partial completion is a first-class outcome."""

    QUEUED = "queued"
    SCREENING = "screening"
    DOCUMENT_ANALYSIS = "document_analysis"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"


class RecommendationStatus(StrEnum):
    """Spec §8.1D / §14 — assigned deterministically from score and findings."""

    RECOMMENDED = "recommended"
    RECOMMENDED_WITH_REVIEW = "recommended_with_review"
    NEEDS_INVESTIGATION = "needs_investigation"
    HIGH_RISK = "high_risk"
    REJECT = "reject"


class FindingSourceType(StrEnum):
    """Spec §15.5 — how a finding was produced."""

    DETERMINISTIC = "deterministic"
    DOCUMENT = "document"
    HUMAN = "human"


class FindingSeverity(StrEnum):
    """Spec §13. A single ``FATAL`` finding forces a ``REJECT`` recommendation."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    FATAL = "fatal"


class ReviewStatus(StrEnum):
    """State of a finding in the human-review loop (spec §8.1F)."""

    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class ReviewDecision(StrEnum):
    """A reviewer's action on a finding. Maps onto ``ReviewStatus``."""

    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"
    ESCALATE = "escalate"


class DocumentProcessingStatus(StrEnum):
    """Spec §15.6 — lifecycle of an uploaded permitting document."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
