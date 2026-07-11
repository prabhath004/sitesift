"""CSV parsing and row validation — spec §17.

These exercise the pure parser. Persistence, cross-upload de-duplication, and
the HTTP surface are covered in test_sites_api.py.
"""

import pytest

from app.services.csv_import import CsvImportError, parse_sites_csv

HEADER = (
    "site_name,latitude,longitude,acreage,jurisdiction,"
    "road_distance_miles,flood_overlap_percent,wetland_overlap_percent"
)
VALID_ROW = "River Road,42.110,-73.910,34,Greenfield County,0.7,0,2"


def csv_of(*rows: str, header: str = HEADER) -> str:
    return "\n".join([header, *rows]) + "\n"


def messages(errors: object) -> str:
    return " ".join(e.message for e in errors)  # type: ignore[attr-defined]


# ---------------------------------------------------------------- happy path


def test_a_valid_row_is_parsed_with_every_field() -> None:
    parsed = parse_sites_csv(csv_of(VALID_ROW))

    assert parsed.total_rows == 1
    assert not parsed.errors

    row = parsed.rows[0]
    assert row.name == "River Road"
    assert row.latitude == 42.110
    assert row.longitude == -73.910
    assert row.acreage == 34
    assert row.jurisdiction == "Greenfield County"
    assert row.road_distance_miles == 0.7
    assert row.flood_overlap_percent == 0
    assert row.wetland_overlap_percent == 2


def test_the_five_demo_sites_all_parse() -> None:
    parsed = parse_sites_csv(
        csv_of(
            "River Road,42.110,-73.910,34,Greenfield County,0.7,0,2",
            "Oak Parcel,42.145,-73.880,27,Greenfield County,1.1,4,14",
            "County Route 9,42.090,-73.970,22,Greenfield County,0.4,0,1",
            "Mill Farm,42.180,-73.930,41,Greenfield County,2.8,7,4",
            "North Ridge,42.125,-73.850,31,Greenfield County,1.3,2,5",
        )
    )

    assert parsed.total_rows == 5
    assert len(parsed.rows) == 5
    assert not parsed.errors


def test_the_optional_columns_may_be_absent_entirely() -> None:
    parsed = parse_sites_csv(
        csv_of(
            "River Road,42.110,-73.910,34,Greenfield County",
            header="site_name,latitude,longitude,acreage,jurisdiction",
        )
    )

    row = parsed.rows[0]
    assert row.road_distance_miles is None
    assert row.flood_overlap_percent is None
    assert row.wetland_overlap_percent is None


def test_an_empty_optional_cell_is_read_as_missing_not_as_zero() -> None:
    parsed = parse_sites_csv(csv_of("River Road,42.110,-73.910,34,Greenfield County,,,"))

    row = parsed.rows[0]
    assert row.road_distance_miles is None
    assert row.flood_overlap_percent is None
    assert row.wetland_overlap_percent is None


def test_surrounding_whitespace_is_stripped() -> None:
    parsed = parse_sites_csv(csv_of("  River Road , 42.110 , -73.910 , 34 , Greenfield County "))

    assert parsed.rows[0].name == "River Road"
    assert parsed.rows[0].jurisdiction == "Greenfield County"


# ---------------------------------------------------------------- file-level errors


def test_an_empty_file_is_rejected() -> None:
    with pytest.raises(CsvImportError, match="empty"):
        parse_sites_csv("")


def test_a_file_with_only_whitespace_is_rejected() -> None:
    with pytest.raises(CsvImportError, match="empty"):
        parse_sites_csv("   \n  \n")


def test_a_header_with_no_data_rows_is_rejected() -> None:
    with pytest.raises(CsvImportError, match="no data rows"):
        parse_sites_csv(HEADER + "\n")


def test_missing_required_columns_are_named_in_the_error() -> None:
    with pytest.raises(CsvImportError) as exc:
        parse_sites_csv(
            csv_of("River Road,42.110", header="site_name,latitude"),
        )

    detail = str(exc.value)
    assert "acreage" in detail
    assert "jurisdiction" in detail
    assert "longitude" in detail


def test_a_file_that_is_not_csv_at_all_is_rejected() -> None:
    with pytest.raises(CsvImportError):
        parse_sites_csv("this is not a csv file, it is a sentence\n")


# ---------------------------------------------------------------- row-level validation


def test_an_empty_site_name_is_a_row_error() -> None:
    parsed = parse_sites_csv(csv_of(",42.110,-73.910,34,Greenfield County"))

    assert not parsed.rows
    assert len(parsed.errors) == 1
    error = parsed.errors[0]
    assert error.row_number == 2
    assert error.field == "site_name"
    assert "empty" in error.message.lower()


def test_a_latitude_above_ninety_is_a_row_error() -> None:
    parsed = parse_sites_csv(csv_of("River Road,90.1,-73.910,34,Greenfield County"))

    assert not parsed.rows
    assert parsed.errors[0].field == "latitude"
    assert "-90" in parsed.errors[0].message


def test_a_latitude_below_minus_ninety_is_a_row_error() -> None:
    parsed = parse_sites_csv(csv_of("River Road,-90.1,-73.910,34,Greenfield County"))

    assert parsed.errors[0].field == "latitude"


def test_latitude_at_the_poles_is_accepted() -> None:
    parsed = parse_sites_csv(
        csv_of(
            "North Pole,90,-73.910,34,Greenfield County",
            "South Pole,-90,-73.910,34,Greenfield County",
        )
    )

    assert len(parsed.rows) == 2
    assert not parsed.errors


def test_a_longitude_beyond_one_eighty_is_a_row_error() -> None:
    parsed = parse_sites_csv(csv_of("River Road,42.110,180.1,34,Greenfield County"))

    assert parsed.errors[0].field == "longitude"
    assert "-180" in parsed.errors[0].message


def test_longitude_at_the_antimeridian_is_accepted() -> None:
    parsed = parse_sites_csv(csv_of("Edge,42.110,180,34,Greenfield County"))

    assert len(parsed.rows) == 1


def test_zero_acreage_is_a_row_error() -> None:
    parsed = parse_sites_csv(csv_of("River Road,42.110,-73.910,0,Greenfield County"))

    assert parsed.errors[0].field == "acreage"
    assert "greater than zero" in parsed.errors[0].message


def test_negative_acreage_is_a_row_error() -> None:
    parsed = parse_sites_csv(csv_of("River Road,42.110,-73.910,-5,Greenfield County"))

    assert parsed.errors[0].field == "acreage"


def test_a_non_numeric_latitude_is_a_row_error_naming_the_bad_value() -> None:
    parsed = parse_sites_csv(csv_of("River Road,north,-73.910,34,Greenfield County"))

    error = parsed.errors[0]
    assert error.field == "latitude"
    assert error.value == "north"
    assert "number" in error.message.lower()


def test_a_non_numeric_optional_field_is_a_row_error() -> None:
    parsed = parse_sites_csv(csv_of("River Road,42.110,-73.910,34,Greenfield County,close,0,2"))

    assert parsed.errors[0].field == "road_distance_miles"
    assert not parsed.rows


def test_a_missing_required_value_is_a_row_error() -> None:
    parsed = parse_sites_csv(csv_of("River Road,42.110,-73.910,34,"))

    assert parsed.errors[0].field == "jurisdiction"


def test_one_row_can_produce_several_errors() -> None:
    parsed = parse_sites_csv(csv_of(",999,-73.910,-4,Greenfield County"))

    assert {e.field for e in parsed.errors} == {"site_name", "latitude", "acreage"}


def test_row_numbers_count_the_header_so_they_match_a_spreadsheet() -> None:
    parsed = parse_sites_csv(csv_of(VALID_ROW, ",42.1,-73.9,10,Greenfield County"))

    assert parsed.errors[0].row_number == 3


# ---------------------------------------------------------------- duplicates


def test_a_duplicate_site_name_in_the_same_upload_is_rejected() -> None:
    parsed = parse_sites_csv(
        csv_of(VALID_ROW, "River Road,42.999,-73.111,50,Greenfield County,1,1,1")
    )

    assert len(parsed.rows) == 1, "the first occurrence is kept"
    assert parsed.duplicate_rows == 1
    assert parsed.errors[0].row_number == 3
    assert "duplicate" in parsed.errors[0].message.lower()


def test_duplicate_detection_ignores_case_and_surrounding_whitespace() -> None:
    parsed = parse_sites_csv(csv_of(VALID_ROW, "  river road  ,42.1,-73.9,30,Greenfield County"))

    assert parsed.duplicate_rows == 1
    assert len(parsed.rows) == 1


def test_distinct_site_names_are_not_duplicates() -> None:
    parsed = parse_sites_csv(csv_of(VALID_ROW, "Oak Parcel,42.145,-73.880,27,Greenfield County"))

    assert parsed.duplicate_rows == 0
    assert len(parsed.rows) == 2


# ---------------------------------------------------------------- partial imports


def test_valid_rows_survive_alongside_invalid_ones() -> None:
    parsed = parse_sites_csv(
        csv_of(
            "River Road,42.110,-73.910,34,Greenfield County,0.7,0,2",
            "Bad Coords,999,-73.880,27,Greenfield County,1.1,4,14",
            "County Route 9,42.090,-73.970,22,Greenfield County,0.4,0,1",
            "No Acres,42.180,-73.930,0,Greenfield County,2.8,7,4",
        )
    )

    assert parsed.total_rows == 4
    assert [row.name for row in parsed.rows] == ["River Road", "County Route 9"]
    assert {e.row_number for e in parsed.errors} == {3, 5}
