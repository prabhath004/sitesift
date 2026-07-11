"""Candidate-site CSV parsing and validation — spec §17.

Parsing is pure and has no database in sight, so every validation rule is
testable on its own. Persistence lives in ``site_import``: rows that fail
validation are never written, and a repeated upload never duplicates a site.
"""

import csv
import io
from dataclasses import dataclass, field

from app.schemas.site import (
    OPTIONAL_CSV_COLUMNS,
    REQUIRED_CSV_COLUMNS,
    RowValidationError,
)

# The header occupies line 1, so the first data row is line 2. Reporting the
# file's own line numbers is what makes an error message actionable.
FIRST_DATA_ROW = 2


class CsvImportError(Exception):
    """The file cannot be read at all — as opposed to a row that fails validation."""


@dataclass(frozen=True)
class ParsedSiteRow:
    """One candidate site that passed validation."""

    row_number: int
    name: str
    latitude: float
    longitude: float
    acreage: float
    jurisdiction: str
    road_distance_miles: float | None
    flood_overlap_percent: float | None
    wetland_overlap_percent: float | None
    raw: dict[str, str]


@dataclass
class ParsedImport:
    total_rows: int = 0
    duplicate_rows: int = 0
    rows: list[ParsedSiteRow] = field(default_factory=list)
    errors: list[RowValidationError] = field(default_factory=list)


def parse_sites_csv(content: str) -> ParsedImport:
    """Validate a candidate-site CSV. Raises only when the file itself is unusable."""
    if not content.strip():
        raise CsvImportError("The uploaded CSV is empty.")

    reader = csv.DictReader(io.StringIO(content))
    header = [(name or "").strip().lower() for name in (reader.fieldnames or [])]

    missing = [column for column in REQUIRED_CSV_COLUMNS if column not in header]
    if missing:
        raise CsvImportError(
            "The CSV is missing required column(s): "
            f"{', '.join(missing)}. Required columns are: {', '.join(REQUIRED_CSV_COLUMNS)}."
        )

    parsed = ParsedImport()
    seen: set[str] = set()

    for offset, raw_row in enumerate(reader):
        row_number = FIRST_DATA_ROW + offset
        parsed.total_rows += 1
        row = {key.strip().lower(): (value or "").strip() for key, value in raw_row.items() if key}

        errors: list[RowValidationError] = []
        name = _read_name(row, row_number, errors)
        latitude = _read_bounded(row, "latitude", -90, 90, row_number, errors)
        longitude = _read_bounded(row, "longitude", -180, 180, row_number, errors)
        acreage = _read_acreage(row, row_number, errors)
        jurisdiction = _read_required_text(row, "jurisdiction", row_number, errors)
        optional = {
            column: _read_optional_number(row, column, row_number, errors)
            for column in OPTIONAL_CSV_COLUMNS
        }

        if errors:
            parsed.errors.extend(errors)
            continue

        # Every value is present once the row has no errors; narrow for mypy.
        assert name is not None
        assert latitude is not None
        assert longitude is not None
        assert acreage is not None
        assert jurisdiction is not None

        key = name.casefold()
        if key in seen:
            parsed.duplicate_rows += 1
            parsed.errors.append(
                RowValidationError(
                    row_number=row_number,
                    field="site_name",
                    message=(
                        f"Duplicate site: {name!r} already appears earlier in this upload. "
                        f"The first occurrence was kept."
                    ),
                    value=name,
                )
            )
            continue

        seen.add(key)
        parsed.rows.append(
            ParsedSiteRow(
                row_number=row_number,
                name=name,
                latitude=latitude,
                longitude=longitude,
                acreage=acreage,
                jurisdiction=jurisdiction,
                road_distance_miles=optional["road_distance_miles"],
                flood_overlap_percent=optional["flood_overlap_percent"],
                wetland_overlap_percent=optional["wetland_overlap_percent"],
                raw=row,
            )
        )

    if parsed.total_rows == 0:
        raise CsvImportError("The uploaded CSV has a header but no data rows.")

    return parsed


def _read_name(
    row: dict[str, str], row_number: int, errors: list[RowValidationError]
) -> str | None:
    value = row.get("site_name", "")
    if not value:
        errors.append(
            RowValidationError(
                row_number=row_number,
                field="site_name",
                message="Site name cannot be empty.",
                value=None,
            )
        )
        return None
    return value


def _read_required_text(
    row: dict[str, str], column: str, row_number: int, errors: list[RowValidationError]
) -> str | None:
    value = row.get(column, "")
    if not value:
        errors.append(
            RowValidationError(
                row_number=row_number,
                field=column,
                message=f"{column} is required and cannot be empty.",
                value=None,
            )
        )
        return None
    return value


def _read_number(
    row: dict[str, str], column: str, row_number: int, errors: list[RowValidationError]
) -> float | None:
    """Parse a required numeric cell, recording an error rather than raising."""
    raw = row.get(column, "")
    if not raw:
        errors.append(
            RowValidationError(
                row_number=row_number,
                field=column,
                message=f"{column} is required and cannot be empty.",
                value=None,
            )
        )
        return None

    try:
        return float(raw)
    except ValueError:
        errors.append(
            RowValidationError(
                row_number=row_number,
                field=column,
                message=f"{column} must be a valid number.",
                value=raw,
            )
        )
        return None


def _read_bounded(
    row: dict[str, str],
    column: str,
    low: float,
    high: float,
    row_number: int,
    errors: list[RowValidationError],
) -> float | None:
    value = _read_number(row, column, row_number, errors)
    if value is None:
        return None

    if not low <= value <= high:
        errors.append(
            RowValidationError(
                row_number=row_number,
                field=column,
                message=f"{column} must be between {low:g} and {high:g}.",
                value=row.get(column),
            )
        )
        return None

    return value


def _read_acreage(
    row: dict[str, str], row_number: int, errors: list[RowValidationError]
) -> float | None:
    value = _read_number(row, "acreage", row_number, errors)
    if value is None:
        return None

    if value <= 0:
        errors.append(
            RowValidationError(
                row_number=row_number,
                field="acreage",
                message="acreage must be greater than zero.",
                value=row.get("acreage"),
            )
        )
        return None

    return value


def _read_optional_number(
    row: dict[str, str], column: str, row_number: int, errors: list[RowValidationError]
) -> float | None:
    """An absent optional value is missing information, not an error.

    A *present but unparseable* one is an error: silently dropping it would let a
    typo masquerade as "no data", and the scoring rules treat those very
    differently.
    """
    raw = row.get(column, "")
    if not raw:
        return None

    try:
        return float(raw)
    except ValueError:
        errors.append(
            RowValidationError(
                row_number=row_number,
                field=column,
                message=f"{column} must be a valid number when provided.",
                value=raw,
            )
        )
        return None
