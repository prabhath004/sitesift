"""Screening run — spec §15.3.

Execution is synchronous today, but the shape is the one a queued worker needs:
a row exists in ``QUEUED`` before any work happens, and ``started_at`` /
``completed_at`` / ``error_message`` are filled in as it progresses. Moving to a
background worker means changing who advances the row, not the schema.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import created_at_column, uuid_pk
from app.schemas.common import ScreeningRunStatus

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.risk_finding import RiskFinding
    from app.models.site_score import SiteScore
    from app.models.workflow_event import WorkflowEvent


class ScreeningRun(Base):
    __tablename__ = "screening_runs"
    __table_args__ = (
        # Spec §18: a repeated request with the same key must not create a second
        # run. Scoped per project, so two projects may reuse a key.
        UniqueConstraint(
            "project_id", "idempotency_key", name="uq_screening_run_project_idempotency_key"
        ),
    )

    id: Mapped[str] = uuid_pk()
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ScreeningRunStatus] = mapped_column(
        Enum(ScreeningRunStatus, native_enum=False, length=32),
        nullable=False,
        default=ScreeningRunStatus.QUEUED,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = created_at_column()

    project: Mapped["Project"] = relationship(back_populates="screening_runs")
    scores: Mapped[list["SiteScore"]] = relationship(
        back_populates="screening_run", cascade="all, delete-orphan"
    )
    findings: Mapped[list["RiskFinding"]] = relationship(
        back_populates="screening_run", cascade="all, delete-orphan"
    )
    events: Mapped[list["WorkflowEvent"]] = relationship(
        back_populates="screening_run", cascade="all, delete-orphan"
    )
