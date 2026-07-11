"""ORM model registry for Alembic autogenerate.

Every model must be imported here so that Alembic autogenerate discovers it.

Integration note. The document-analysis branch carried its own ``ProjectRecord``
and ``CandidateSiteRecord`` stubs, mapped onto ``projects`` and
``candidate_sites``, so that it could validate document upload against a real
site id while working in isolation. Those stubs are gone: the screening branch's
``Project`` and ``CandidateSite`` are the real tables and document code now uses
them. Likewise there is exactly one ``risk_findings`` model — ``RiskFinding`` —
written by both deterministic screening and document analysis, and two distinct
workflow-event tables, because a screening step and a LangGraph node have
different parents and different columns (docs/INTEGRATION_NOTES.md).
"""

from app.models.candidate_site import CandidateSite
from app.models.document import Document, DocumentChunk, DocumentPage
from app.models.document_workflow import DocumentAnalysisRequest, DocumentWorkflowEvent
from app.models.evidence import Evidence
from app.models.project import Project
from app.models.review import Review
from app.models.risk_finding import RiskFinding
from app.models.screening_run import ScreeningRun
from app.models.site_score import SiteScore
from app.models.workflow_event import WorkflowEvent

__all__ = [
    "CandidateSite",
    "Document",
    "DocumentAnalysisRequest",
    "DocumentChunk",
    "DocumentPage",
    "DocumentWorkflowEvent",
    "Evidence",
    "Project",
    "Review",
    "RiskFinding",
    "ScreeningRun",
    "SiteScore",
    "WorkflowEvent",
]
