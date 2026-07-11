"""Shared helpers for document-analysis tests."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.candidate_site import CandidateSite
from app.models.project import Project
from app.schemas.common import ProjectType
from app.schemas.project import ProjectStatus


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


def create_site(
    db: Session,
    *,
    project_type: ProjectType = ProjectType.COMMUNITY_SOLAR,
    project_name: str = "Hudson Valley Community Solar",
    site_name: str = "River Road",
) -> CandidateSite:
    """A project and one candidate site, built from the real models.

    These tests used to build ``ProjectRecord`` / ``CandidateSiteRecord`` — the
    document branch's stub tables. Integration deleted those, so the fixture now
    builds the same rows the CSV import would.
    """
    project = Project(
        name=project_name,
        project_type=project_type,
        target_capacity_mw=5,
        minimum_acres=25,
        target_state="NY",
        screening_criteria={
            "maximum_flood_overlap_percent": 5,
            "maximum_wetland_overlap_percent": 10,
            "maximum_road_distance_miles": 2,
        },
        status=ProjectStatus.ACTIVE,
    )
    db.add(project)
    db.flush()

    site = CandidateSite(
        project_id=project.id,
        name=site_name,
        name_key=site_name.casefold(),
        latitude=42.110,
        longitude=-73.910,
        acreage=34,
        jurisdiction="Greenfield County",
        road_distance_miles=0.7,
        flood_overlap_percent=0,
        wetland_overlap_percent=2,
        sequence=0,
        raw_input={},
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
