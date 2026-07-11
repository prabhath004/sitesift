"""SiteSift FastAPI application.

Foundation only: an app shell, CORS, a health probe, and an empty ``/api``
router for feature agents to hang endpoints on. No SiteSift business logic
lives here.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes import health
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Evidence-backed site triage for renewable energy and power "
        "infrastructure projects. Foundation build — endpoints are added by "
        "feature agents (see docs/PARALLEL_TASKS.md)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(api_router, prefix=settings.api_prefix)
