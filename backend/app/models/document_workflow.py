"""Workflow event and idempotency ORM models for document analysis.

Integration note. This module's event model was called ``WorkflowEvent`` and
mapped to ``workflow_events`` — the same table name the screening branch uses
for its own, different event model (screening steps, keyed to a screening run,
with text summaries). They are not the same entity: a LangGraph node has a
document parent and JSON summaries. Rather than force one table to serve both
and lose columns from each, the document events keep every column they had and
move to ``document_workflow_events``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.document import Document, new_uuid, utc_now


class DocumentAnalysisRequest(Base):
    """Idempotency record for document analysis requests."""

    __tablename__ = "document_analysis_requests"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "idempotency_key",
            name="uq_document_analysis_requests_document_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="uploaded")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped[Document] = relationship()
    events: Mapped[list[DocumentWorkflowEvent]] = relationship(
        back_populates="analysis_request",
        cascade="all, delete-orphan",
    )


class DocumentWorkflowEvent(Base):
    """Persisted public audit event for a LangGraph node."""

    __tablename__ = "document_workflow_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_request_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("document_analysis_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    node_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    output_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    document: Mapped[Document] = relationship()
    analysis_request: Mapped[DocumentAnalysisRequest | None] = relationship(back_populates="events")
