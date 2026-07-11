"""Structured document-analysis workflow tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import DocumentPage
from app.models.document_workflow import DocumentWorkflowEvent
from app.models.risk_finding import RiskFinding
from app.services.document_service import upload_document
from app.workflows.permitting_graph import analyze_document
from tests.document_helpers import create_site, fixture_pdf_bytes, make_pdf_bytes, upload_pdf
from tests.document_test_doubles import (
    InvalidEvidenceExtractor,
    InvalidOutputExtractor,
    LowConfidenceExtractor,
    TransientFailureExtractor,
    UnknownCategoryExtractor,
)


def test_analysis_extracts_verified_requirements(client: TestClient, db: Session) -> None:
    site = create_site(db)
    document = upload_pdf(client, site_id=site.id)

    response = client.post(
        f"/api/documents/{document['id']}/analyze",
        headers={"Idempotency-Key": "analysis-success"},
    )

    assert response.status_code == 200
    body = response.json()
    # The requirement taxonomy lives in `requirement_category` after integration;
    # `category` is the scoring dimension, and a permitting requirement always
    # scores against permitting.
    categories = {finding["requirement_category"] for finding in body["findings"]}
    assert {"use_permission", "setback", "public_hearing", "decommissioning"}.issubset(categories)
    assert all(finding["category"] == "permitting" for finding in body["findings"])
    assert body["document"]["processing_status"] == "needs_review"
    assert all(finding["evidence"] for finding in body["findings"])
    assert all(finding["review_status"] == "pending" for finding in body["findings"])


def test_invalid_model_output_fails_without_losing_extraction(db: Session) -> None:
    site = create_site(db)
    document = upload_document(
        db,
        site_id=site.id,
        filename="sample.pdf",
        mime_type="application/pdf",
        content=fixture_pdf_bytes(),
        settings=get_settings(),
    ).document

    response = analyze_document(
        db,
        document_id=document.id,
        settings=get_settings(),
        idempotency_key="invalid-output",
        extractor=InvalidOutputExtractor(),
    )

    assert response.document.processing_status == "failed"
    assert response.findings == []
    assert db.query(DocumentPage).filter(DocumentPage.document_id == document.id).count() == 3
    assert any(event.status == "failed" for event in response.workflow_events)


def test_unknown_category_is_mapped_to_other_and_reviewed(db: Session) -> None:
    site = create_site(db)
    document = upload_document(
        db,
        site_id=site.id,
        filename="sample.pdf",
        mime_type="application/pdf",
        content=fixture_pdf_bytes(),
        settings=get_settings(),
    ).document

    response = analyze_document(
        db,
        document_id=document.id,
        settings=get_settings(),
        idempotency_key="unknown-category",
        extractor=UnknownCategoryExtractor(),
    )

    assert response.document.processing_status == "needs_review"
    assert response.findings[0].requirement_category == "other"
    assert response.findings[0].review_status == "pending"


def test_ambiguous_low_confidence_requirement_partially_completes(db: Session) -> None:
    site = create_site(db)
    document = upload_document(
        db,
        site_id=site.id,
        filename="sample.pdf",
        mime_type="application/pdf",
        content=fixture_pdf_bytes(),
        settings=get_settings(),
    ).document

    response = analyze_document(
        db,
        document_id=document.id,
        settings=get_settings(),
        idempotency_key="low-confidence",
        extractor=LowConfidenceExtractor(),
    )

    assert response.document.processing_status == "partially_completed"
    assert len(response.findings) == 1
    assert response.findings[0].requires_human_review is True
    assert response.findings[0].confidence == 0.40


def test_no_relevant_sections_partially_completes(client: TestClient, db: Session) -> None:
    site = create_site(db)
    document = upload_pdf(
        client,
        site_id=site.id,
        content=make_pdf_bytes(["General town meeting minutes with no ordinance terms."]),
    )

    response = client.post(
        f"/api/documents/{document['id']}/analyze",
        headers={"Idempotency-Key": "no-sections"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document"]["processing_status"] == "partially_completed"
    assert body["findings"] == []
    assert "No relevant permitting sections" in body["document"]["error_message"]


def test_invalid_evidence_is_not_persisted(db: Session) -> None:
    site = create_site(db)
    document = upload_document(
        db,
        site_id=site.id,
        filename="sample.pdf",
        mime_type="application/pdf",
        content=fixture_pdf_bytes(),
        settings=get_settings(),
    ).document

    response = analyze_document(
        db,
        document_id=document.id,
        settings=get_settings(),
        idempotency_key="invalid-evidence",
        extractor=InvalidEvidenceExtractor(),
    )

    assert response.document.processing_status == "partially_completed"
    assert response.findings == []
    assert db.query(RiskFinding).count() == 0


def test_duplicate_idempotency_key_does_not_duplicate_findings(
    client: TestClient, db: Session
) -> None:
    site = create_site(db)
    document = upload_pdf(client, site_id=site.id)

    first = client.post(
        f"/api/documents/{document['id']}/analyze",
        headers={"Idempotency-Key": "same-key"},
    )
    second = client.post(
        f"/api/documents/{document['id']}/analyze",
        headers={"Idempotency-Key": "same-key"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(second.json()["findings"]) == len(first.json()["findings"])
    assert db.query(RiskFinding).count() == len(first.json()["findings"])


def test_failed_analysis_can_be_retried_with_same_key(db: Session) -> None:
    site = create_site(db)
    document = upload_document(
        db,
        site_id=site.id,
        filename="sample.pdf",
        mime_type="application/pdf",
        content=fixture_pdf_bytes(),
        settings=get_settings(),
    ).document

    failed = analyze_document(
        db,
        document_id=document.id,
        settings=get_settings(),
        idempotency_key="retry-key",
        extractor=TransientFailureExtractor(),
    )
    retried = analyze_document(
        db,
        document_id=document.id,
        settings=get_settings(),
        idempotency_key="retry-key",
        extractor=UnknownCategoryExtractor(),
    )

    assert failed.document.processing_status == "failed"
    assert retried.document.processing_status == "needs_review"
    assert len(retried.findings) == 1


def test_workflow_events_are_persisted(client: TestClient, db: Session) -> None:
    site = create_site(db)
    document = upload_pdf(client, site_id=site.id)

    response = client.post(
        f"/api/documents/{document['id']}/analyze",
        headers={"Idempotency-Key": "events"},
    )

    assert response.status_code == 200
    node_names = {event["node_name"] for event in response.json()["workflow_events"]}
    assert {
        "validate_document",
        "extract_text",
        "create_page_chunks",
        "retrieve_relevant_sections",
        "extract_requirements",
        "validate_evidence",
        "flag_ambiguity",
        "persist_findings",
        "generate_summary",
    }.issubset(node_names)
    assert db.query(DocumentWorkflowEvent).count() >= 9
