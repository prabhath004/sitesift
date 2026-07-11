"""Workflow event — spec §15.9. The audit trail for one screening run.

OWNERSHIP NOTE. docs/PARALLEL_TASKS.md assigns this module to the
document-analysis agent, but ``GET /api/screenings/{id}/events`` needs it now.
It is defined here, at the path that document lists, so that a merge produces
one conflict in one file rather than two competing tables. The columns are the
spec's, and nothing here is specific to deterministic screening — the LangGraph
nodes should be able to write their own steps to this table unchanged.

``input_summary`` and ``output_summary`` are summaries by design: CLAUDE.md rule
7 forbids logging user content or document text.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import created_at_column, uuid_pk

if TYPE_CHECKING:
    from app.models.screening_run import ScreeningRun


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[str] = uuid_pk()
    screening_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("screening_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Steps within a run share a timestamp at millisecond resolution, so events
    # carry their own ordinal rather than relying on created_at to sort them.
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = created_at_column()

    screening_run: Mapped["ScreeningRun"] = relationship(back_populates="events")
