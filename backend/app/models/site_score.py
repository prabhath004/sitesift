"""Site score — spec §15.4.

``breakdown`` is not in the spec's column list. It is here because spec §9.5
requires every deduction to be inspectable: a score without the records that
produced it is a number the UI cannot break down, which the product principles
forbid.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import created_at_column, uuid_pk
from app.schemas.common import RecommendationStatus
from app.schemas.screening import PermittingAnalysisStatus

if TYPE_CHECKING:
    from app.models.candidate_site import CandidateSite
    from app.models.screening_run import ScreeningRun


class SiteScore(Base):
    __tablename__ = "site_scores"
    __table_args__ = (
        UniqueConstraint("screening_run_id", "site_id", name="uq_site_score_run_site"),
    )

    id: Mapped[str] = uuid_pk()
    screening_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("screening_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidate_sites.id", ondelete="CASCADE"), nullable=False, index=True
    )

    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    site_suitability_score: Mapped[int] = mapped_column(Integer, nullable=False)
    environmental_score: Mapped[int] = mapped_column(Integer, nullable=False)
    access_score: Mapped[int] = mapped_column(Integer, nullable=False)
    permitting_score: Mapped[int] = mapped_column(Integer, nullable=False)

    permitting_status: Mapped[PermittingAnalysisStatus] = mapped_column(
        Enum(PermittingAnalysisStatus, native_enum=False, length=32),
        nullable=False,
        default=PermittingAnalysisStatus.NOT_ANALYZED,
    )
    recommendation_status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus, native_enum=False, length=32), nullable=False
    )

    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    breakdown: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = created_at_column()

    screening_run: Mapped["ScreeningRun"] = relationship(back_populates="scores")
    site: Mapped["CandidateSite"] = relationship(back_populates="scores")
