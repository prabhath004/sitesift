"""Citation verification for document-derived findings."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.document import Document, DocumentPage
from app.schemas.document import ExtractedRequirement
from app.schemas.evidence import EvidenceCreate
from app.services.pdf_parser import normalize_for_match


@dataclass(frozen=True)
class EvidenceValidationResult:
    requirement: ExtractedRequirement
    evidence: list[EvidenceCreate]
    errors: list[str]


def validate_requirement_evidence(
    document: Document,
    pages: list[DocumentPage],
    requirement: ExtractedRequirement,
) -> EvidenceValidationResult:
    """Verify every citation before a requirement can be persisted."""
    page_by_number = {page.page_number: page for page in pages}
    errors: list[str] = []
    valid_evidence: list[EvidenceCreate] = []

    if not requirement.evidence:
        return EvidenceValidationResult(
            requirement=requirement,
            evidence=[],
            errors=[f"Requirement '{requirement.title}' has no evidence."],
        )

    for evidence in requirement.evidence:
        page = page_by_number.get(evidence.page_number)
        if page is None:
            errors.append(
                f"Requirement '{requirement.title}' cites missing page {evidence.page_number}."
            )
            continue
        if not excerpt_matches_page(evidence.excerpt, page):
            errors.append(
                f"Requirement '{requirement.title}' cites text that was not found on "
                f"page {evidence.page_number}."
            )
            continue
        valid_evidence.append(
            EvidenceCreate(
                document_id=document.id,
                document_name=document.filename,
                page_number=evidence.page_number,
                section_name=evidence.section_name or page.section_heading,
                excerpt=evidence.excerpt.strip(),
            )
        )

    if not valid_evidence:
        errors.append(f"Requirement '{requirement.title}' has no valid evidence.")

    return EvidenceValidationResult(requirement=requirement, evidence=valid_evidence, errors=errors)


def excerpt_matches_page(excerpt: str, page: DocumentPage) -> bool:
    """Return true when the excerpt occurs verbatim or after safe normalization."""
    if not excerpt.strip():
        return False
    if excerpt in page.raw_text:
        return True
    normalized_excerpt = normalize_for_match(excerpt)
    normalized_page = normalize_for_match(page.raw_text or page.normalized_text)
    return normalized_excerpt in normalized_page
