"""document analysis: documents, pages, chunks, evidence, reviews, workflow events

Revision ID: 20260711_0001
Revises: 21e763a954ce
Create Date: 2026-07-11 00:00:00.000000

Integration note. This revision arrived from feature/document-analysis as a
second *root* (``down_revision = None``) that created ``projects``,
``candidate_sites``, and ``risk_findings`` itself — stub versions of tables the
screening revision already creates. Two roots means two heads, and a merge
revision could not have reconciled them: both branches create the same three
tables, so upgrading through both would fail on a duplicate table.

It is rebased onto the screening revision instead, giving one linear history with
one head. The three duplicated tables are gone from it, and the document columns
it needed on ``risk_findings`` are added here as ALTERs rather than baked into a
competing CREATE. Its own tables are unchanged, except ``workflow_events`` →
``document_workflow_events``: the screening revision already owns
``workflow_events``, for a different entity (a screening step, not a LangGraph
node).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260711_0001"
down_revision: str | None = "21e763a954ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Document-derived columns on the shared findings table. Nullable, because a
    # deterministic finding has no extracted original and no confidence.
    op.add_column(
        "risk_findings",
        sa.Column(
            "requirement_category",
            sa.Enum(
                "USE_PERMISSION",
                "SETBACK",
                "PUBLIC_HEARING",
                "DECOMMISSIONING",
                "FINANCIAL_SECURITY",
                "ENVIRONMENTAL_STUDY",
                "TRAFFIC_STUDY",
                "APPLICATION_REQUIREMENT",
                "OTHER",
                name="requirementcategory",
                native_enum=False,
                length=32,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "risk_findings", sa.Column("original_title", sa.String(length=200), nullable=True)
    )
    op.add_column("risk_findings", sa.Column("original_description", sa.Text(), nullable=True))
    op.add_column(
        "risk_findings",
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default="0"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("site_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("processing_status", sa.String(length=40), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["candidate_sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "content_hash", name="uq_documents_site_content_hash"),
    )
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_site_id", "documents", ["site_id"])

    op.create_table(
        "document_pages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("section_heading", sa.String(length=255), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "page_number", name="uq_document_pages_document_page"),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("section_heading", sa.String(length=255), nullable=True),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "page_number",
            "chunk_index",
            name="uq_document_chunks_document_page_index",
        ),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    op.create_table(
        "document_analysis_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "idempotency_key",
            name="uq_document_analysis_requests_document_key",
        ),
    )
    op.create_index(
        "ix_document_analysis_requests_document_id",
        "document_analysis_requests",
        ["document_id"],
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_name", sa.String(length=255), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("section_name", sa.String(length=255), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["finding_id"], ["risk_findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_document_id", "evidence", ["document_id"])
    op.create_index("ix_evidence_finding_id", "evidence", ["finding_id"])

    op.create_table(
        "reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("edited_title", sa.String(length=255), nullable=True),
        sa.Column("edited_description", sa.Text(), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("original_title", sa.String(length=255), nullable=False),
        sa.Column("original_description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["risk_findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reviews_finding_id", "reviews", ["finding_id"])

    op.create_table(
        "document_workflow_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_request_id", sa.String(length=36), nullable=True),
        sa.Column("node_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("input_summary", sa.JSON(), nullable=False),
        sa.Column("output_summary", sa.JSON(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_request_id"],
            ["document_analysis_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_workflow_events_analysis_request_id",
        "document_workflow_events",
        ["analysis_request_id"],
    )
    op.create_index(
        "ix_document_workflow_events_document_id",
        "document_workflow_events",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_workflow_events_document_id", table_name="document_workflow_events")
    op.drop_index(
        "ix_document_workflow_events_analysis_request_id",
        table_name="document_workflow_events",
    )
    op.drop_table("document_workflow_events")
    op.drop_index("ix_reviews_finding_id", table_name="reviews")
    op.drop_table("reviews")
    op.drop_index("ix_evidence_finding_id", table_name="evidence")
    op.drop_index("ix_evidence_document_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index(
        "ix_document_analysis_requests_document_id",
        table_name="document_analysis_requests",
    )
    op.drop_table("document_analysis_requests")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_document_pages_document_id", table_name="document_pages")
    op.drop_table("document_pages")
    op.drop_index("ix_documents_site_id", table_name="documents")
    op.drop_index("ix_documents_project_id", table_name="documents")
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.drop_table("documents")

    with op.batch_alter_table("risk_findings") as batch:
        batch.drop_column("requires_human_review")
        batch.drop_column("original_description")
        batch.drop_column("original_title")
        batch.drop_column("requirement_category")
