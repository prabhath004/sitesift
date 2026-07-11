"""Projects and their screening criteria — API contract §Project."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import ProjectId, ProjectType

# Spec §7 — the demo project's thresholds, and a sane default for any project
# created without explicit criteria.
DEFAULT_MAX_FLOOD_OVERLAP_PERCENT = 5.0
DEFAULT_MAX_WETLAND_OVERLAP_PERCENT = 10.0
DEFAULT_MAX_ROAD_DISTANCE_MILES = 2.0


class ProjectStatus(StrEnum):
    """Serialized as a plain string, which is all the v1 contract promises."""

    ACTIVE = "active"
    SCREENING = "screening"
    SCREENED = "screened"


class ScreeningCriteria(BaseModel):
    """Thresholds a candidate site is screened against (spec §10.2 section B).

    ``minimum_acres`` is not repeated here — it lives on the project itself, as
    in the contract's worked example.
    """

    maximum_flood_overlap_percent: float = Field(
        default=DEFAULT_MAX_FLOOD_OVERLAP_PERCENT, ge=0, le=100
    )
    maximum_wetland_overlap_percent: float = Field(
        default=DEFAULT_MAX_WETLAND_OVERLAP_PERCENT, ge=0, le=100
    )
    maximum_road_distance_miles: float = Field(default=DEFAULT_MAX_ROAD_DISTANCE_MILES, ge=0)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    project_type: ProjectType
    target_capacity_mw: float | None = Field(default=None, gt=0)
    minimum_acres: float = Field(gt=0)
    target_state: str | None = Field(default=None, max_length=100)
    screening_criteria: ScreeningCriteria = Field(default_factory=ScreeningCriteria)
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def name_is_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name cannot be empty")
        return cleaned


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: ProjectId
    name: str
    project_type: ProjectType
    target_capacity_mw: float | None
    minimum_acres: float
    target_state: str | None
    screening_criteria: ScreeningCriteria
    notes: str | None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
