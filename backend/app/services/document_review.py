"""Human review service for document-derived findings."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document
from app.models.document_finding import DocumentFinding
from app.models.evidence import Evidence
from app.models.review import Review
from app.schemas.common import ReviewDecision, ReviewStatus
from app.schemas.document import DocumentWorkflowStatus, ReviewFindingRequest
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
) -> DocumentFinding:
    finding = db.get(
        DocumentFinding,
        finding_id,
        options=[selectinload(DocumentFinding.evidence), selectinload(DocumentFinding.reviews)],
    )
    if finding is None:
        raise NotFoundError("Finding was not found.")

    if request.decision == ReviewDecision.APPROVE and not finding.evidence:
        raise ConflictError("A document-derived finding cannot be approved without evidence.")

    review = Review(
        finding_id=finding.id,
        decision=request.decision.value,
        edited_title=request.edited_title,
        edited_description=request.edited_description,
        reviewer_note=request.reviewer_note,
        original_title=finding.title,
        original_description=finding.description,
    )
    db.add(review)

    if request.decision == ReviewDecision.EDIT:
        if request.edited_title:
            finding.title = request.edited_title
        if request.edited_description:
            finding.description = request.edited_description

    finding.review_status = DECISION_TO_STATUS[request.decision].value
    db.add(finding)
    db.flush()
    _refresh_related_document_statuses(db, finding)
    db.commit()
    db.refresh(finding)
    return finding


def _refresh_related_document_statuses(db: Session, finding: DocumentFinding) -> None:
    document_ids = {evidence.document_id for evidence in finding.evidence}
    for document_id in document_ids:
        statuses = list(
            db.scalars(
                select(DocumentFinding.review_status)
                .join(Evidence, Evidence.finding_id == DocumentFinding.id)
                .where(Evidence.document_id == document_id)
            ).all()
        )
        document = db.get(Document, document_id)
        if document is None or not statuses:
            continue
        if all(status in _FINAL_REVIEW_STATUSES for status in statuses):
            document.processing_status = DocumentWorkflowStatus.COMPLETED.value
        else:
            document.processing_status = DocumentWorkflowStatus.NEEDS_REVIEW.value
        db.add(document)


_FINAL_REVIEW_STATUSES = {
    ReviewStatus.APPROVED.value,
    ReviewStatus.EDITED.value,
    ReviewStatus.REJECTED.value,
}
