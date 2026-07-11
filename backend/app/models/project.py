"""Screening project — spec §15.1."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import created_at_column, updated_at_column, uuid_pk
from app.schemas.common import ProjectType
from app.schemas.project import ProjectStatus

if TYPE_CHECKING:
    from app.models.candidate_site import CandidateSite
    from app.models.screening_run import ScreeningRun


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    project_type: Mapped[ProjectType] = mapped_column(
        Enum(ProjectType, native_enum=False, length=32), nullable=False
    )
    target_capacity_mw: Mapped[float | None] = mapped_column(Float, nullable=True)
    minimum_acres: Mapped[float] = mapped_column(Float, nullable=False)
    target_state: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # The thresholds a site is screened against. JSON rather than columns: the
    # criteria set is a product decision that is still moving (spec §10.2).
    screening_criteria: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=32),
        nullable=False,
        default=ProjectStatus.ACTIVE,
    )

    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    sites: Mapped[list["CandidateSite"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    screening_runs: Mapped[list["ScreeningRun"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
