"""Persisting a parsed candidate-site CSV.

Two guarantees, both from spec §17 / §18:

* rows that fail validation are never written;
* re-uploading the same file never duplicates a site.

The write happens in one transaction, so a failure part-way through leaves the
project with the sites it had before, not half of a spreadsheet.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidate_site import CandidateSite
from app.models.project import Project
from app.schemas.site import (
    CandidateSiteRead,
    ImportSummary,
    RowValidationError,
    SiteImportResult,
)
from app.services.csv_import import parse_sites_csv


def import_sites_csv(db: Session, project: Project, content: str) -> SiteImportResult:
    """Validate and persist a candidate-site CSV. Raises ``CsvImportError`` on a bad file."""
    parsed = parse_sites_csv(content)

    existing_names = set(
        db.scalars(
            select(CandidateSite.name_key).where(CandidateSite.project_id == project.id)
        ).all()
    )
    next_sequence = _next_sequence(db, project.id)

    errors: list[RowValidationError] = list(parsed.errors)
    duplicate_rows = parsed.duplicate_rows
    created: list[CandidateSite] = []

    for row in parsed.rows:
        name_key = row.name.casefold()

        # Already imported by an earlier upload. Not an error — a retry of the
        # same file is a normal thing to do — but it is not a new site either.
        if name_key in existing_names:
            duplicate_rows += 1
            errors.append(
                RowValidationError(
                    row_number=row.row_number,
                    field="site_name",
                    message=(
                        f"Duplicate site: {row.name!r} is already imported for this project. "
                        f"The existing site was kept and this row was skipped."
                    ),
                    value=row.name,
                )
            )
            continue

        existing_names.add(name_key)
        site = CandidateSite(
            project_id=project.id,
            name=row.name,
            name_key=name_key,
            latitude=row.latitude,
            longitude=row.longitude,
            acreage=row.acreage,
            jurisdiction=row.jurisdiction,
            road_distance_miles=row.road_distance_miles,
            flood_overlap_percent=row.flood_overlap_percent,
            wetland_overlap_percent=row.wetland_overlap_percent,
            sequence=next_sequence,
            raw_input=row.raw,
        )
        next_sequence += 1
        db.add(site)
        created.append(site)

    db.flush()

    # A duplicate is neither valid nor invalid — it is a row we already have.
    # Counting it in both buckets would make the summary fail to add up.
    valid_rows = len(parsed.rows)
    invalid_rows = parsed.total_rows - valid_rows - parsed.duplicate_rows

    return SiteImportResult(
        project_id=project.id,
        summary=ImportSummary(
            total_rows=parsed.total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            imported_rows=len(created),
            duplicate_rows=duplicate_rows,
        ),
        errors=sorted(errors, key=lambda error: error.row_number),
        imported_sites=[CandidateSiteRead.model_validate(site) for site in created],
    )


def _next_sequence(db: Session, project_id: str) -> int:
    """Continue the project's existing numbering, so a second upload appends."""
    highest = db.scalar(
        select(func.max(CandidateSite.sequence)).where(CandidateSite.project_id == project_id)
    )
    return 0 if highest is None else int(highest) + 1
