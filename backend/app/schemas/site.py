"""Candidate sites and CSV import — API contract §Candidate site."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import CandidateSiteId, ProjectId

REQUIRED_CSV_COLUMNS = ("site_name", "latitude", "longitude", "acreage", "jurisdiction")
OPTIONAL_CSV_COLUMNS = (
    "road_distance_miles",
    "flood_overlap_percent",
    "wetland_overlap_percent",
)


class CandidateSiteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: CandidateSiteId
    project_id: ProjectId
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    acreage: float = Field(gt=0)
    jurisdiction: str
    road_distance_miles: float | None
    flood_overlap_percent: float | None
    wetland_overlap_percent: float | None
    created_at: datetime


class RowValidationError(BaseModel):
    """One reason one CSV row was not imported.

    ``row_number`` is the line number in the uploaded file, counting the header
    as line 1, so it matches what the user sees in a spreadsheet.
    """

    row_number: int
    field: str | None
    message: str
    value: str | None = None


class ImportSummary(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    imported_rows: int
    duplicate_rows: int


class SiteImportResult(BaseModel):
    """The response to a CSV import. Rows that fail validation are never persisted."""

    project_id: ProjectId
    summary: ImportSummary
    errors: list[RowValidationError]
    imported_sites: list[CandidateSiteRead]
