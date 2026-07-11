"""ORM model registry for Alembic autogenerate."""

from app.models.document import (
    CandidateSiteRecord,
    Document,
    DocumentChunk,
    DocumentPage,
    ProjectRecord,
)
from app.models.document_finding import DocumentFinding
from app.models.document_workflow import DocumentAnalysisRequest, WorkflowEvent
from app.models.evidence import Evidence
from app.models.review import Review

__all__ = [
    "CandidateSiteRecord",
    "Document",
    "DocumentAnalysisRequest",
    "DocumentChunk",
    "DocumentFinding",
    "DocumentPage",
    "Evidence",
    "ProjectRecord",
    "Review",
    "WorkflowEvent",
]
