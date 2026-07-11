"""Document-analysis API and workflow schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import FindingSeverity, FindingSourceType, ReviewDecision, ReviewStatus
from app.schemas.evidence import EvidenceCreate, EvidenceResponse


class DocumentWorkflowStatus(StrEnum):
    """Fine-grained document-processing statuses for this vertical slice."""

    UPLOADED = "uploaded"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    RETRIEVING = "retrieving"
    ANALYZING = "analyzing"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"


class RequirementCategory(StrEnum):
    USE_PERMISSION = "use_permission"
    SETBACK = "setback"
    PUBLIC_HEARING = "public_hearing"
    DECOMMISSIONING = "decommissioning"
    FINANCIAL_SECURITY = "financial_security"
    ENVIRONMENTAL_STUDY = "environmental_study"
    TRAFFIC_STUDY = "traffic_study"
    APPLICATION_REQUIREMENT = "application_requirement"
    OTHER = "other"


class WorkflowEventStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    site_id: str
    filename: str
    mime_type: str
    page_count: int
    processing_status: DocumentWorkflowStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    page_number: int
    raw_text: str
    normalized_text: str
    section_heading: str | None
    char_count: int
    created_at: datetime


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    page_number: int
    chunk_index: int
    text: str
    normalized_text: str
    section_heading: str | None
    start_char: int
    end_char: int
    created_at: datetime


class ExtractedRequirement(BaseModel):
    """Structured output expected from requirement extraction."""

    category: RequirementCategory
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    value: str | None = Field(default=None, max_length=255)
    severity: FindingSeverity
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceCreate] = Field(default_factory=list)
    requires_human_review: bool = True

    @field_validator("requires_human_review")
    @classmethod
    def force_human_review(cls, value: bool) -> bool:
        """Document-derived requirements are never auto-approved."""
        return True if value is False else value


class DocumentFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    screening_run_id: str | None
    source_type: FindingSourceType
    category: RequirementCategory
    title: str
    description: str
    original_title: str
    original_description: str
    severity: FindingSeverity
    value: str | None
    confidence: float
    requires_human_review: bool
    review_status: ReviewStatus
    evidence: list[EvidenceResponse]
    created_at: datetime
    updated_at: datetime


class WorkflowEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    analysis_request_id: str | None
    node_name: str
    status: WorkflowEventStatus
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]
    duration_ms: int
    error_message: str | None
    evidence: list[dict[str, Any]]
    created_at: datetime


class DocumentAnalysisResponse(BaseModel):
    document: DocumentResponse
    findings: list[DocumentFindingResponse]
    workflow_events: list[WorkflowEventResponse]
    summary: str | None = None


class ReviewFindingRequest(BaseModel):
    decision: ReviewDecision
    edited_title: str | None = Field(default=None, max_length=255)
    edited_description: str | None = None
    reviewer_note: str | None = None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    decision: ReviewDecision
    edited_title: str | None
    edited_description: str | None
    reviewer_note: str | None
    original_title: str
    original_description: str
    created_at: datetime
