"""Aggregate API router, mounted at ``Settings.api_prefix`` (``/api``).

Routers (see docs/API_CONTRACT.md):
    projects     — POST/GET /api/projects, GET /api/projects/{project_id}
    sites        — /api/projects/{project_id}/sites, /api/sites/{site_id}
    screenings   — /api/projects/{project_id}/screenings, /api/screenings/{id}
    documents    — /api/sites/{site_id}/documents, /api/documents/{id}/analyze
    findings     — /api/sites/{site_id}/findings, /api/findings/{id}/review
    briefs       — /api/sites/{site_id}/brief

``findings`` owns every finding route, deterministic and document-derived alike.
The document router deliberately does not register ``/sites/{site_id}/findings``:
both feature branches defined it, and two handlers on one path means whichever
router is included first silently shadows the other.
"""

from fastapi import APIRouter

from app.api.routes import briefs, demo, documents, findings, projects, screenings, sites

api_router = APIRouter()

api_router.include_router(projects.router)
api_router.include_router(sites.router)
api_router.include_router(screenings.router)
api_router.include_router(documents.router)
api_router.include_router(findings.router)
api_router.include_router(briefs.router)
api_router.include_router(demo.router)
