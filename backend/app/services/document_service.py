"""Persistence services for document upload and analysis results."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.models.candidate_site import CandidateSite
from app.models.document import (
    Document,
    DocumentChunk,
    DocumentPage,
    new_uuid,
    utc_now,
)
from app.models.document_workflow import DocumentWorkflowEvent
from app.models.evidence import Evidence
from app.models.risk_finding import RiskFinding
from app.schemas.common import DocumentProcessingStatus, FindingSourceType, ReviewStatus
from app.schemas.document import DocumentAnalysisResponse, ExtractedRequirement
from app.schemas.evidence import EvidenceCreate
from app.schemas.finding import FindingCategory, FindingGroup
from app.services.document_errors import NotFoundError
from app.services.pdf_parser import ParsedPdf, PdfParser, PdfValidationError
from app.services.pdf_storage import sha256_bytes, store_pdf


@dataclass(frozen=True)
class UploadedDocumentResult:
    document: Document
    duplicate: bool


@dataclass(frozen=True)
class PersistableRequirement:
    requirement: ExtractedRequirement
    evidence: list[EvidenceCreate]
    review_status: ReviewStatus
    requires_human_review: bool


def upload_document(
    db: Session,
    *,
    site_id: str,
    filename: str,
    mime_type: str,
    content: bytes,
    settings: Settings,
) -> UploadedDocumentResult:
    """Validate, store, and persist a PDF upload."""
    site = db.get(CandidateSite, site_id)
    if site is None:
        raise NotFoundError("Site was not found.")

    parser = PdfParser(
        max_chars=settings.document_chunk_max_chars,
        overlap_chars=settings.document_chunk_overlap_chars,
    )
    parsed = parser.parse(
        content,
        filename=filename,
        mime_type=mime_type,
        max_size_bytes=settings.document_max_upload_bytes,
    )
    content_hash = sha256_bytes(content)

    existing = db.scalar(
        select(Document)
        .where(Document.site_id == site_id, Document.content_hash == content_hash)
        .options(selectinload(Document.pages), selectinload(Document.chunks))
    )
    if existing is not None:
        return UploadedDocumentResult(document=existing, duplicate=True)

    document_id = new_uuid()
    storage_path = store_pdf(
        content,
        document_id=document_id,
        storage_dir=settings.document_storage_dir,
    )
    document = Document(
        id=document_id,
        project_id=site.project_id,
        site_id=site_id,
        filename=filename,
        mime_type=mime_type,
        storage_path=str(storage_path),
        size_bytes=len(content),
        content_hash=content_hash,
        page_count=parsed.page_count,
        processing_status=DocumentProcessingStatus.UPLOADED.value,
    )
    db.add(document)
    db.flush()
    persist_extracted_text(db, document=document, parsed=parsed)
    db.commit()
    db.refresh(document)
    return UploadedDocumentResult(document=document, duplicate=False)


def get_document(db: Session, document_id: str) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise NotFoundError("Document was not found.")
    return document


def get_document_with_text(db: Session, document_id: str) -> Document:
    document = db.scalar(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.pages), selectinload(Document.chunks))
    )
    if document is None:
        raise NotFoundError("Document was not found.")
    return document


def persist_extracted_text(db: Session, *, document: Document, parsed: ParsedPdf) -> None:
    """Replace persisted pages/chunks for a document with parsed output."""
    db.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    for page in parsed.pages:
        db.add(
            DocumentPage(
                document_id=document.id,
                page_number=page.page_number,
                raw_text=page.raw_text,
                normalized_text=page.normalized_text,
                section_heading=page.section_heading,
                char_count=page.char_count,
            )
        )
    for chunk in parsed.chunks:
        db.add(
            DocumentChunk(
                document_id=document.id,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                normalized_text=chunk.normalized_text,
                section_heading=chunk.section_heading,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
            )
        )
    document.page_count = parsed.page_count


def update_document_status(
    db: Session,
    document: Document,
    status: DocumentProcessingStatus,
    *,
    error_message: str | None = None,
) -> None:
    document.processing_status = status.value
    document.error_message = error_message
    document.updated_at = utc_now()
    db.add(document)
    db.flush()


def persist_document_findings(
    db: Session,
    *,
    document: Document,
    requirements: list[PersistableRequirement],
) -> list[RiskFinding]:
    """Persist validated requirements, skipping duplicates for this document.

    A requirement is only reachable here if evidence validation produced at least
    one verified excerpt, so ``item.evidence`` is never empty — a document finding
    without evidence is never written (CLAUDE.md rule 2).
    """
    existing_keys = _existing_document_finding_keys(db, document.id)
    persisted: list[RiskFinding] = []

    for item in requirements:
        if not item.evidence:
            continue

        first_evidence = item.evidence[0]
        key = (
            item.requirement.category.value,
            item.requirement.title,
            first_evidence.page_number,
            first_evidence.excerpt,
        )
        if key in existing_keys:
            continue

        finding = RiskFinding(
            site_id=document.site_id,
            screening_run_id=None,
            source_type=FindingSourceType.DOCUMENT,
            # Every document requirement scores against permitting; the finer
            # taxonomy the extractor produced is kept in `requirement_category`.
            category=FindingCategory.PERMITTING,
            group=FindingGroup.REQUIREMENT,
            requirement_category=item.requirement.category,
            title=item.requirement.title,
            description=item.requirement.description,
            original_title=item.requirement.title,
            original_description=item.requirement.description,
            severity=item.requirement.severity,
            value=item.requirement.value,
            confidence=item.requirement.confidence,
            requires_human_review=item.requires_human_review,
            review_status=item.review_status,
        )
        db.add(finding)
        db.flush()
        for evidence in item.evidence:
            db.add(
                Evidence(
                    finding_id=finding.id,
                    document_id=document.id,
                    document_name=document.filename,
                    page_number=evidence.page_number,
                    section_name=evidence.section_name,
                    excerpt=evidence.excerpt,
                )
            )
        persisted.append(finding)
        existing_keys.add(key)

    db.flush()
    return persisted


def get_document_findings(db: Session, document_id: str) -> list[RiskFinding]:
    return list(
        db.scalars(
            select(RiskFinding)
            .join(Evidence, Evidence.finding_id == RiskFinding.id)
            .where(Evidence.document_id == document_id)
            .options(selectinload(RiskFinding.evidence))
            .order_by(RiskFinding.created_at)
        )
        .unique()
        .all()
    )


def get_site_document_findings(db: Session, site_id: str) -> list[RiskFinding]:
    return list(
        db.scalars(
            select(RiskFinding)
            .where(
                RiskFinding.site_id == site_id,
                RiskFinding.source_type == FindingSourceType.DOCUMENT,
            )
            .options(selectinload(RiskFinding.evidence))
            .order_by(RiskFinding.created_at)
        ).all()
    )


def list_documents_for_site(db: Session, site_id: str) -> list[Document]:
    return list(
        db.scalars(
            select(Document).where(Document.site_id == site_id).order_by(Document.created_at)
        ).all()
    )


def build_analysis_response(db: Session, document_id: str) -> DocumentAnalysisResponse:
    document = get_document(db, document_id)
    findings = get_document_findings(db, document_id)
    events = list(
        db.scalars(
            select(DocumentWorkflowEvent)
            .where(DocumentWorkflowEvent.document_id == document_id)
            .order_by(DocumentWorkflowEvent.created_at)
        ).all()
    )
    summary = _summary_for(document, findings)
    return DocumentAnalysisResponse(
        document=document,
        findings=findings,
        workflow_events=events,
        summary=summary,
    )


def _existing_document_finding_keys(
    db: Session,
    document_id: str,
) -> set[tuple[str, str, int, str]]:
    rows = db.execute(
        select(
            RiskFinding.category,
            RiskFinding.title,
            Evidence.page_number,
            Evidence.excerpt,
        )
        .join(Evidence, Evidence.finding_id == RiskFinding.id)
        .where(Evidence.document_id == document_id)
    ).all()
    return {
        (category, title, page_number, excerpt) for category, title, page_number, excerpt in rows
    }


def _summary_for(document: Document, findings: list[RiskFinding]) -> str:
    status = DocumentProcessingStatus(document.processing_status)
    if status == DocumentProcessingStatus.FAILED:
        return document.error_message or "Document analysis failed."
    if not findings:
        return "No verified permitting requirements were persisted for this document."
    pending = sum(1 for finding in findings if finding.review_status == ReviewStatus.PENDING.value)
    approved = sum(
        1 for finding in findings if finding.review_status == ReviewStatus.APPROVED.value
    )
    return (
        f"{len(findings)} document-derived requirement(s) found. "
        f"{pending} pending review; {approved} approved."
    )


def validation_error_to_message(error: PdfValidationError) -> str:
    return str(error)
