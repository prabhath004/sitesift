"""Aggregate API router, mounted at ``Settings.api_prefix`` (``/api``).

SHARED FILE — see docs/PARALLEL_TASKS.md. Feature agents add exactly one
``include_router`` line each; keep edits to a single line to avoid conflicts.

Planned routers (see docs/API_CONTRACT.md), none implemented yet:
    projects     — POST/GET /api/projects, GET /api/projects/{project_id}
    sites        — /api/projects/{project_id}/sites, /api/sites/{site_id}
    screenings   — /api/projects/{project_id}/screenings, /api/screenings/{id}
    documents    — /api/sites/{site_id}/documents, /api/documents/{id}/analyze
    findings     — /api/sites/{site_id}/findings, /api/findings/{id}/review
    briefs       — /api/sites/{site_id}/brief
"""

from fastapi import APIRouter

api_router = APIRouter()

# Feature agents: add router includes below, one line each.
# from app.api.routes import projects
# api_router.include_router(projects.router)
