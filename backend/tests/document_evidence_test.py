"""Evidence validation tests."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document, DocumentPage
from app.schemas.common import FindingSeverity
from app.schemas.document import ExtractedRequirement, RequirementCategory
from app.schemas.evidence import EvidenceCreate
from app.services.document_evidence import excerpt_matches_page, validate_requirement_evidence
from app.services.document_service import upload_document
from tests.document_helpers import create_site, fixture_pdf_bytes


def test_excerpt_matches_page_after_safe_normalization() -> None:
    page = DocumentPage(
        document_id="doc",
        page_number=1,
        raw_text="The Board must hold a public\nhearing before approval.",
        normalized_text="The Board must hold a public hearing before approval.",
        section_heading=None,
        char_count=53,
    )

    assert excerpt_matches_page("public hearing before approval", page)


def test_invalid_page_is_rejected(db: Session) -> None:
    site = create_site(db)
    document = upload_document(
        db,
        site_id=site.id,
        filename="sample.pdf",
        mime_type="application/pdf",
        content=fixture_pdf_bytes(),
        settings=get_settings(),
    ).document
    requirement = _requirement(
        evidence=[
            EvidenceCreate(
                document_id=document.id,
                document_name=document.filename,
                page_number=99,
                excerpt="not found",
            )
        ]
    )

    result = validate_requirement_evidence(document, document.pages, requirement)

    assert not result.evidence
    assert any("missing page" in error for error in result.errors)


def test_excerpt_not_found_is_rejected(db: Session) -> None:
    site = create_site(db)
    document = upload_document(
        db,
        site_id=site.id,
        filename="sample.pdf",
        mime_type="application/pdf",
        content=fixture_pdf_bytes(),
        settings=get_settings(),
    ).document
    requirement = _requirement(
        evidence=[
            EvidenceCreate(
                document_id=document.id,
                document_name=document.filename,
                page_number=1,
                excerpt="Invented text not in the source.",
            )
        ]
    )

    result = validate_requirement_evidence(document, document.pages, requirement)

    assert not result.evidence
    assert any("not found" in error for error in result.errors)


def test_requirement_without_evidence_is_rejected() -> None:
    requirement = _requirement(evidence=[])

    result = validate_requirement_evidence(
        _document_stub(),
        [],
        requirement,
    )

    assert not result.evidence
    assert result.errors


def test_multiple_evidence_records_are_validated(db: Session) -> None:
    site = create_site(db)
    document = upload_document(
        db,
        site_id=site.id,
        filename="sample.pdf",
        mime_type="application/pdf",
        content=fixture_pdf_bytes(),
        settings=get_settings(),
    ).document
    requirement = _requirement(
        evidence=[
            EvidenceCreate(
                document_id=document.id,
                document_name=document.filename,
                page_number=1,
                excerpt=(
                    "The Board must hold a public hearing before granting conditional-use approval."
                ),
            ),
            EvidenceCreate(
                document_id=document.id,
                document_name=document.filename,
                page_number=3,
                excerpt=(
                    "The applicant shall submit a decommissioning plan describing "
                    "removal of equipment and restoration of disturbed land."
                ),
            ),
        ]
    )

    result = validate_requirement_evidence(document, document.pages, requirement)

    assert len(result.evidence) == 2
    assert not result.errors


def _requirement(evidence: list[EvidenceCreate]) -> ExtractedRequirement:
    return ExtractedRequirement(
        category=RequirementCategory.PUBLIC_HEARING,
        title="Public hearing",
        description="A public hearing is required.",
        value=None,
        severity=FindingSeverity.WARNING,
        confidence=0.9,
        requires_human_review=True,
        evidence=evidence,
    )


def _document_stub() -> Document:
    return Document(
        id="doc",
        project_id="project",
        site_id="site",
        filename="stub.pdf",
        mime_type="application/pdf",
        storage_path="/tmp/stub.pdf",
        size_bytes=1,
        content_hash="hash",
        page_count=1,
        processing_status="uploaded",
    )
