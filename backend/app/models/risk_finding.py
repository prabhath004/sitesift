"""Risk finding — spec §15.5.

Findings from all three sources share this table. This branch writes only
``DETERMINISTIC`` rows; the document-analysis branch writes ``DOCUMENT`` rows,
which must carry evidence, and the review flow writes ``HUMAN`` rows. The
``confidence`` column stays NULL for deterministic findings: a threshold check
is not a probabilistic claim, and giving it a confidence would imply it is.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import created_at_column, updated_at_column, uuid_pk
from app.schemas.common import FindingSeverity, FindingSourceType, ReviewStatus
from app.schemas.finding import FindingCategory, FindingGroup

if TYPE_CHECKING:
    from app.models.candidate_site import CandidateSite
    from app.models.screening_run import ScreeningRun


class RiskFinding(Base):
    __tablename__ = "risk_findings"

    id: Mapped[str] = uuid_pk()
    site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidate_sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    screening_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("screening_runs.id", ondelete="CASCADE"), nullable=True, index=True
    )

    source_type: Mapped[FindingSourceType] = mapped_column(
        Enum(FindingSourceType, native_enum=False, length=32), nullable=False
    )
    category: Mapped[FindingCategory] = mapped_column(
        Enum(FindingCategory, native_enum=False, length=32), nullable=False
    )
    group: Mapped[FindingGroup] = mapped_column(
        Enum(FindingGroup, native_enum=False, length=32), nullable=False
    )

    # The scoring rule that produced this finding, so a finding can be traced
    # back to its breakdown item. NULL for findings that no rule produced.
    rule: Mapped[str | None] = mapped_column(String(100), nullable=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, native_enum=False, length=32), nullable=False
    )

    value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False, length=32),
        nullable=False,
        default=ReviewStatus.PENDING,
    )

    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    site: Mapped["CandidateSite"] = relationship(back_populates="findings")
    screening_run: Mapped["ScreeningRun | None"] = relationship(back_populates="findings")
