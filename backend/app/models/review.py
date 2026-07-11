"""Human review ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.document import new_uuid, utc_now
from app.models.risk_finding import RiskFinding


class Review(Base):
    """Append-only review decision for a document-derived finding."""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    finding_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("risk_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    edited_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    edited_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    finding: Mapped[RiskFinding] = relationship(back_populates="reviews")
