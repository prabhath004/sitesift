"""Evidence schemas for document-derived findings."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvidenceBase(BaseModel):
    document_id: str
    document_name: str
    page_number: int = Field(ge=1)
    section_name: str | None = None
    excerpt: str = Field(min_length=1)


class EvidenceCreate(EvidenceBase):
    finding_id: str | None = None


class EvidenceResponse(EvidenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    created_at: datetime
