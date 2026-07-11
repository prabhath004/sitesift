"""Human review service.

Reviews are append-only: every decision writes a ``reviews`` row carrying the
finding as it stood, and an edit never destroys the extracted original
(spec §9.3).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document
from app.models.evidence import Evidence
from app.models.review import Review
from app.models.risk_finding import RiskFinding
from app.schemas.common import (
    DocumentProcessingStatus,
    FindingSourceType,
    ReviewDecision,
    ReviewStatus,
)
from app.schemas.document import ReviewFindingRequest
from app.services.document_errors import ConflictError, NotFoundError

DECISION_TO_STATUS: dict[ReviewDecision, ReviewStatus] = {
    ReviewDecision.APPROVE: ReviewStatus.APPROVED,
    ReviewDecision.EDIT: ReviewStatus.EDITED,
    ReviewDecision.REJECT: ReviewStatus.REJECTED,
    ReviewDecision.ESCALATE: ReviewStatus.ESCALATED,
}


def review_finding(
    db: Session,
    *,
    finding_id: str,
    request: ReviewFindingRequest,
) -> RiskFinding:
    finding = db.get(
        RiskFinding,
        finding_id,
        options=[selectinload(RiskFinding.evidence), selectinload(RiskFinding.reviews)],
    )
    if finding is None:
        raise NotFoundError("Finding was not found.")

    # Only a document-derived claim needs evidence to stand on. A deterministic
    # finding is a threshold check against data the user supplied — it has no
    # excerpt to cite, and demanding one would make it unapprovable.
    if (
        request.decision == ReviewDecision.APPROVE
        and finding.source_type == FindingSourceType.DOCUMENT
        and not finding.evidence
    ):
        raise ConflictError("A document-derived finding cannot be approved without evidence.")

    review = Review(
        finding_id=finding.id,
        decision=request.decision.value,
        edited_title=request.edited_title,
        edited_description=request.edited_description,
        reviewer_note=request.reviewer_note,
        # The finding as it stands before this decision. Combined with the
        # append-only review rows, every edit remains traceable to the original.
        original_title=finding.original_title or finding.title,
        original_description=finding.original_description or finding.description,
    )
    db.add(review)

    if request.decision == ReviewDecision.EDIT:
        if request.edited_title:
            finding.title = request.edited_title
        if request.edited_description:
            finding.description = request.edited_description

    finding.review_status = DECISION_TO_STATUS[request.decision]
    db.add(finding)
    db.flush()
    _refresh_related_document_statuses(db, finding)
    db.commit()
    db.refresh(finding)
    return finding


def _refresh_related_document_statuses(db: Session, finding: RiskFinding) -> None:
    document_ids = {evidence.document_id for evidence in finding.evidence}
    for document_id in document_ids:
        statuses = list(
            db.scalars(
                select(RiskFinding.review_status)
                .join(Evidence, Evidence.finding_id == RiskFinding.id)
                .where(Evidence.document_id == document_id)
            ).all()
        )
        document = db.get(Document, document_id)
        if document is None or not statuses:
            continue
        if all(status in _FINAL_REVIEW_STATUSES for status in statuses):
            document.processing_status = DocumentProcessingStatus.COMPLETED.value
        else:
            document.processing_status = DocumentProcessingStatus.NEEDS_REVIEW.value
        db.add(document)


_FINAL_REVIEW_STATUSES = {
    ReviewStatus.APPROVED,
    ReviewStatus.EDITED,
    ReviewStatus.REJECTED,
}
