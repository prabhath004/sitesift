"""Record real backend responses as frontend fixtures.

The frontend's mock client and its tests need demo data. Hand-writing that data
means hand-writing a second scoring implementation in TypeScript, which is what
the frontend branch did — and two scoring implementations disagree the moment one
of them changes. So the fixtures are *recorded*, not written: this script boots
the real app against a throwaway SQLite database, seeds the demo project, uploads
and analyzes the sample ordinance, and saves the actual responses.

The fixtures are therefore the backend's own output. If a response shape changes,
regenerate them (`npm run api:generate` covers the types; this covers the data).

    python3 scripts/record-fixtures.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

FIXTURE_PATH = ROOT / "frontend" / "lib" / "api" / "fixtures.json"
SAMPLE_PDF = ROOT / "demo-data" / "sample-zoning-ordinance.pdf"


def record() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from app.database.base import Base
    from app.database.session import engine
    from app.main import app

    Base.metadata.create_all(bind=engine)

    with TestClient(app) as client:
        seed = client.post("/api/demo/seed")
        seed.raise_for_status()
        run = seed.json()["screening_run"]

        dashboard = client.get("/api/projects/dashboard")
        dashboard.raise_for_status()

        # The strongest site carries the document walkthrough, because that is the
        # one a reviewer opens first.
        top_site_id = run["results"][0]["site"]["id"]

        upload = client.post(
            f"/api/sites/{top_site_id}/documents",
            files={"file": (SAMPLE_PDF.name, SAMPLE_PDF.read_bytes(), "application/pdf")},
        )
        upload.raise_for_status()
        document_id = upload.json()["id"]

        analysis = client.post(
            f"/api/documents/{document_id}/analyze",
            headers={"Idempotency-Key": "fixture-recording"},
        )
        analysis.raise_for_status()

        sites: dict[str, Any] = {}
        briefs: dict[str, Any] = {}
        findings: dict[str, Any] = {}
        for result in run["results"]:
            site_id = result["site"]["id"]
            detail = client.get(f"/api/sites/{site_id}")
            detail.raise_for_status()
            sites[site_id] = detail.json()

            brief = client.get(f"/api/sites/{site_id}/brief")
            brief.raise_for_status()
            briefs[site_id] = brief.json()

            site_findings = client.get(f"/api/sites/{site_id}/findings")
            site_findings.raise_for_status()
            findings[site_id] = site_findings.json()

        return {
            "_comment": (
                "Recorded from the real backend by scripts/record-fixtures.py. "
                "Do not hand-edit: regenerate instead. Used only by the mock API "
                "client (NEXT_PUBLIC_USE_MOCK_API=true) and by frontend tests."
            ),
            "screening_run": run,
            "dashboard": dashboard.json(),
            "sites": sites,
            "briefs": briefs,
            "findings": findings,
            "document_analysis": analysis.json(),
        }


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp) / 'fixtures.db'}"
        os.environ["DOCUMENT_STORAGE_DIR"] = str(Path(tmp) / "documents")
        fixtures = record()

    FIXTURE_PATH.write_text(json.dumps(fixtures, indent=2, sort_keys=True) + "\n")
    print(f"wrote {FIXTURE_PATH.relative_to(ROOT)}")
