"""Shared helpers for document-analysis tests."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import CandidateSiteRecord, ProjectRecord


def fixture_pdf_bytes() -> bytes:
    path = Path(__file__).parents[2] / "demo-data" / "sample-zoning-ordinance.pdf"
    return path.read_bytes()


def make_pdf_bytes(pages: list[str]) -> bytes:
    fitz: Any = importlib.import_module("fitz")
    document = fitz.open()
    for text in pages:
        page = document.new_page(width=612, height=792)
        if text:
            page.insert_textbox(fitz.Rect(72, 72, 540, 720), text, fontsize=11, fontname="helv")
    content = document.tobytes()
    document.close()
    return bytes(content)


def create_site(db: Session, *, project_type: str = "community_solar") -> CandidateSiteRecord:
    project = ProjectRecord(name="Hudson Valley Community Solar", project_type=project_type)
    db.add(project)
    db.flush()
    site = CandidateSiteRecord(
        project_id=project.id,
        name="River Road",
        jurisdiction="Greenfield County",
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def upload_pdf(
    client: TestClient,
    *,
    site_id: str,
    content: bytes | None = None,
    filename: str = "sample-zoning-ordinance.pdf",
    mime_type: str = "application/pdf",
) -> dict[str, Any]:
    response = client.post(
        f"/api/sites/{site_id}/documents",
        files={
            "file": (filename, content if content is not None else fixture_pdf_bytes(), mime_type)
        },
    )
    assert response.status_code in {200, 201}, response.text
    return dict(response.json())
