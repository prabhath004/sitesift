"""Confidence thresholds for document-derived requirements."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.common import DocumentProcessingStatus, ReviewStatus
from app.schemas.document import ExtractedRequirement

HIGH_CONFIDENCE = 0.80
MEDIUM_CONFIDENCE = 0.55
LOW_CONFIDENCE = 0.25


@dataclass(frozen=True)
class ConfidenceDecision:
    review_status: ReviewStatus
    requires_human_review: bool
    workflow_status: DocumentProcessingStatus
    keep_requirement: bool


def assign_confidence(requirement: ExtractedRequirement) -> ConfidenceDecision:
    """Use confidence as a workflow signal, never as proof."""
    if requirement.confidence < LOW_CONFIDENCE:
        return ConfidenceDecision(
            review_status=ReviewStatus.REJECTED,
            requires_human_review=True,
            workflow_status=DocumentProcessingStatus.PARTIALLY_COMPLETED,
            keep_requirement=False,
        )
    if requirement.confidence < MEDIUM_CONFIDENCE:
        return ConfidenceDecision(
            review_status=ReviewStatus.PENDING,
            requires_human_review=True,
            workflow_status=DocumentProcessingStatus.PARTIALLY_COMPLETED,
            keep_requirement=True,
        )
    return ConfidenceDecision(
        review_status=ReviewStatus.PENDING,
        requires_human_review=True,
        workflow_status=DocumentProcessingStatus.NEEDS_REVIEW,
        keep_requirement=True,
    )
