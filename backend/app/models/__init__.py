"""ORM models.

Every model must be imported here so that Alembic autogenerate discovers it.
SHARED FILE — one import line per model, appended (docs/PARALLEL_TASKS.md).

Still owned by the document-analysis agent and not defined yet: documents,
evidence, reviews. ``risk_findings`` deliberately holds no foreign key to those
tables; evidence points at a finding, not the other way round, so the two
branches can land in either order.
"""

from app.models.candidate_site import CandidateSite
from app.models.project import Project
from app.models.risk_finding import RiskFinding
from app.models.screening_run import ScreeningRun
from app.models.site_score import SiteScore
from app.models.workflow_event import WorkflowEvent

__all__ = [
    "CandidateSite",
    "Project",
    "RiskFinding",
    "ScreeningRun",
    "SiteScore",
    "WorkflowEvent",
]
