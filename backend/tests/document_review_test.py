"""Human review tests for document-derived findings."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.review import Review
from tests.document_helpers import create_site, upload_pdf


def _analyzed_finding_id(client: TestClient, site_id: str) -> str:
    document = upload_pdf(client, site_id=site_id)
    response = client.post(
        f"/api/documents/{document['id']}/analyze",
        headers={"Idempotency-Key": f"review-{document['id']}"},
    )
    assert response.status_code == 200
    return str(response.json()["findings"][0]["id"])


def test_approve_finding(client: TestClient, db: Session) -> None:
    site = create_site(db)
    finding_id = _analyzed_finding_id(client, site.id)

    response = client.patch(
        f"/api/findings/{finding_id}/review",
        json={"decision": "approve", "reviewer_note": "Confirmed."},
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == "approved"
    assert db.query(Review).count() == 1


def test_edit_finding_preserves_review_history(client: TestClient, db: Session) -> None:
    site = create_site(db)
    finding_id = _analyzed_finding_id(client, site.id)

    response = client.patch(
        f"/api/findings/{finding_id}/review",
        json={
            "decision": "edit",
            "edited_title": "Edited conditional-use approval",
            "edited_description": "Reviewer clarified the approval pathway.",
            "reviewer_note": "Clarified title and description.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "edited"
    assert body["title"] == "Edited conditional-use approval"
    review = db.query(Review).one()
    assert review.original_title != "Edited conditional-use approval"
    assert review.edited_title == "Edited conditional-use approval"


def test_reject_finding(client: TestClient, db: Session) -> None:
    site = create_site(db)
    finding_id = _analyzed_finding_id(client, site.id)

    response = client.patch(
        f"/api/findings/{finding_id}/review",
        json={"decision": "reject", "reviewer_note": "Not applicable."},
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == "rejected"
    assert db.query(Review).count() == 1


def test_escalate_finding(client: TestClient, db: Session) -> None:
    site = create_site(db)
    finding_id = _analyzed_finding_id(client, site.id)

    response = client.patch(
        f"/api/findings/{finding_id}/review",
        json={"decision": "escalate", "reviewer_note": "Needs legal review."},
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == "escalated"
    assert db.query(Review).count() == 1
