"""Document upload API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.document_helpers import create_site, fixture_pdf_bytes


def test_upload_valid_pdf(client: TestClient, db: Session) -> None:
    site = create_site(db)

    response = client.post(
        f"/api/sites/{site.id}/documents",
        files={"file": ("sample.pdf", fixture_pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["site_id"] == site.id
    assert body["project_id"] == site.project_id
    assert body["filename"] == "sample.pdf"
    assert body["mime_type"] == "application/pdf"
    assert body["page_count"] == 3
    assert body["processing_status"] == "uploaded"


def test_upload_rejects_non_pdf(client: TestClient, db: Session) -> None:
    site = create_site(db)

    response = client.post(
        f"/api/sites/{site.id}/documents",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_upload_rejects_empty_pdf(client: TestClient, db: Session) -> None:
    site = create_site(db)

    response = client.post(
        f"/api/sites/{site.id}/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_rejects_corrupt_pdf(client: TestClient, db: Session) -> None:
    site = create_site(db)

    response = client.post(
        f"/api/sites/{site.id}/documents",
        files={"file": ("broken.pdf", b"%PDF-1.7\nbroken", "application/pdf")},
    )

    assert response.status_code == 400
    assert "parsed" in response.json()["detail"].lower()


def test_upload_rejects_missing_site(client: TestClient) -> None:
    response = client.post(
        "/api/sites/missing-site/documents",
        files={"file": ("sample.pdf", fixture_pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Site was not found."


def test_duplicate_upload_returns_existing_document(client: TestClient, db: Session) -> None:
    site = create_site(db)

    first = client.post(
        f"/api/sites/{site.id}/documents",
        files={"file": ("sample.pdf", fixture_pdf_bytes(), "application/pdf")},
    )
    second = client.post(
        f"/api/sites/{site.id}/documents",
        files={"file": ("sample.pdf", fixture_pdf_bytes(), "application/pdf")},
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
