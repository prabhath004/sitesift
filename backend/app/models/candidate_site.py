"""Candidate site — spec §15.2."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import created_at_column, uuid_pk

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.project import Project
    from app.models.risk_finding import RiskFinding
    from app.models.site_score import SiteScore


class CandidateSite(Base):
    __tablename__ = "candidate_sites"
    __table_args__ = (
        # Re-importing the same CSV must not duplicate a site. The database
        # enforces that, not just the import service.
        UniqueConstraint("project_id", "name_key", name="uq_candidate_site_project_name"),
    )

    id: Mapped[str] = uuid_pk()
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Case-folded name. Carried as a column so the uniqueness rule the import
    # service applies and the one the database enforces cannot drift apart.
    name_key: Mapped[str] = mapped_column(String(200), nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    acreage: Mapped[float] = mapped_column(Float, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(200), nullable=False)

    # Precomputed stand-ins for geospatial lookups (spec §12.1). NULL means "not
    # provided", which scoring treats as unverified — never as a pass.
    road_distance_miles: Mapped[float | None] = mapped_column(Float, nullable=True)
    flood_overlap_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    wetland_overlap_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Position within the project, assigned at import. Gives ranking a stable
    # tie-break that does not depend on timestamp resolution.
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    raw_input: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = created_at_column()

    project: Mapped["Project"] = relationship(back_populates="sites")
    scores: Mapped[list["SiteScore"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    findings: Mapped[list["RiskFinding"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
