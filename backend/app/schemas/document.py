"""Document-analysis API and workflow schemas.

Integration note. Two schemas that lived here are gone, reconciled rather than
duplicated:

* ``DocumentWorkflowStatus`` described the same column as the contract's
  ``DocumentProcessingStatus``. The workflow's finer states were folded into that
  enum (``app/schemas/common.py``) and this module imports it.
* ``DocumentFindingResponse`` described the same ``risk_findings`` row as
  ``RiskFindingRead``. There is one finding schema now, and it carries evidence.

``RequirementCategory`` moved to ``app/schemas/finding.py``, next to the other
finding enums, because the unified ``RiskFinding`` model needs it and importing
it from here would have the model depending on a document schema.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import (
    DocumentProcessingStatus,
    FindingSeverity,
    ReviewDecision,
)
from app.schemas.evidence import EvidenceCreate
from app.schemas.finding import RequirementCategory, RiskFindingRead


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
    processing_status: DocumentProcessingStatus
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


class DocumentWorkflowEventResponse(BaseModel):
    """One LangGraph node's public audit record.

    Named for the table it reads (``document_workflow_events``) so it is not
    confused with ``WorkflowEventRead``, which is a screening run's step. Carries
    the step, tool, status, structured output, and errors — never model reasoning
    (CLAUDE.md rule 6).
    """

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
    findings: list[RiskFindingRead]
    workflow_events: list[DocumentWorkflowEventResponse]
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
