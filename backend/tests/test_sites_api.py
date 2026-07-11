"""Candidate-site import and retrieval — API contract §Candidate site."""

from fastapi.testclient import TestClient

from tests.factories import DEMO_CSV, create_project, import_csv


def test_importing_a_valid_csv_persists_every_row(client: TestClient) -> None:
    project_id = create_project(client)

    response = import_csv(client, project_id, DEMO_CSV)

    assert response.status_code == 201
    body = response.json()
    assert body["summary"] == {
        "total_rows": 5,
        "valid_rows": 5,
        "invalid_rows": 0,
        "imported_rows": 5,
        "duplicate_rows": 0,
    }
    assert body["errors"] == []
    assert len(body["imported_sites"]) == 5
    assert body["imported_sites"][0]["name"] == "River Road"


def test_imported_sites_are_listed_for_the_project(client: TestClient) -> None:
    project_id = create_project(client)
    import_csv(client, project_id, DEMO_CSV)

    response = client.get(f"/api/projects/{project_id}/sites")

    assert response.status_code == 200
    names = [site["name"] for site in response.json()]
    assert names == ["River Road", "Oak Parcel", "County Route 9", "Mill Farm", "North Ridge"]


def test_a_project_with_no_sites_lists_an_empty_array(client: TestClient) -> None:
    project_id = create_project(client)

    response = client.get(f"/api/projects/{project_id}/sites")

    assert response.status_code == 200
    assert response.json() == []


def test_optional_values_round_trip_through_the_import(client: TestClient) -> None:
    project_id = create_project(client)

    site = import_csv(client, project_id, DEMO_CSV).json()["imported_sites"][0]

    assert site["road_distance_miles"] == 0.7
    assert site["flood_overlap_percent"] == 0
    assert site["wetland_overlap_percent"] == 2


def test_a_site_can_be_retrieved_by_id(client: TestClient) -> None:
    project_id = create_project(client)
    site_id = import_csv(client, project_id, DEMO_CSV).json()["imported_sites"][0]["id"]

    response = client.get(f"/api/sites/{site_id}")

    assert response.status_code == 200
    assert response.json()["site"]["name"] == "River Road"


def test_an_unknown_site_id_returns_a_clear_404(client: TestClient) -> None:
    response = client.get("/api/sites/2f3a5c9e-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_a_site_that_has_not_been_screened_has_no_score_yet(client: TestClient) -> None:
    project_id = create_project(client)
    site_id = import_csv(client, project_id, DEMO_CSV).json()["imported_sites"][0]["id"]

    body = client.get(f"/api/sites/{site_id}").json()

    assert body["score"] is None
    assert body["positive_signals"] == []
    assert body["risks"] == []
    assert body["missing_information"] == []


# ---------------------------------------------------------------- error handling


def test_importing_into_an_unknown_project_returns_404(client: TestClient) -> None:
    response = import_csv(client, "2f3a5c9e-0000-4000-8000-000000000000", DEMO_CSV)

    assert response.status_code == 404


def test_an_empty_csv_is_rejected_with_a_readable_message(client: TestClient) -> None:
    project_id = create_project(client)

    response = import_csv(client, project_id, "")

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_a_csv_missing_required_columns_names_them(client: TestClient) -> None:
    project_id = create_project(client)

    response = import_csv(client, project_id, "site_name,latitude\nRiver Road,42.1\n")

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "acreage" in detail
    assert "jurisdiction" in detail


def test_a_header_with_no_rows_is_rejected(client: TestClient) -> None:
    project_id = create_project(client)
    header = DEMO_CSV.splitlines()[0]

    response = import_csv(client, project_id, header + "\n")

    assert response.status_code == 400
    assert "no data rows" in response.json()["detail"].lower()


def test_a_non_csv_upload_is_rejected(client: TestClient) -> None:
    project_id = create_project(client)

    response = client.post(
        f"/api/projects/{project_id}/sites/import",
        files={"file": ("ordinance.pdf", b"%PDF-1.7 not a csv", "application/pdf")},
    )

    assert response.status_code == 400


# ---------------------------------------------------------------- partial and repeated imports


def test_invalid_rows_are_reported_and_valid_rows_are_still_imported(client: TestClient) -> None:
    project_id = create_project(client)
    csv_content = (
        "site_name,latitude,longitude,acreage,jurisdiction\n"
        "River Road,42.110,-73.910,34,Greenfield County\n"
        "Bad Coords,999,-73.880,27,Greenfield County\n"
        "No Acres,42.180,-73.930,-4,Greenfield County\n"
        "North Ridge,42.125,-73.850,31,Greenfield County\n"
    )

    body = import_csv(client, project_id, csv_content).json()

    assert body["summary"]["total_rows"] == 4
    assert body["summary"]["valid_rows"] == 2
    assert body["summary"]["invalid_rows"] == 2
    assert body["summary"]["imported_rows"] == 2
    assert [site["name"] for site in body["imported_sites"]] == ["River Road", "North Ridge"]

    failed_rows = {error["row_number"] for error in body["errors"]}
    assert failed_rows == {3, 4}


def test_no_row_is_persisted_when_every_row_is_invalid(client: TestClient) -> None:
    project_id = create_project(client)
    csv_content = (
        "site_name,latitude,longitude,acreage,jurisdiction\n"
        "Bad Coords,999,-73.880,27,Greenfield County\n"
    )

    body = import_csv(client, project_id, csv_content).json()

    assert body["summary"]["imported_rows"] == 0
    assert client.get(f"/api/projects/{project_id}/sites").json() == []


def test_a_duplicate_row_inside_one_upload_is_imported_once(client: TestClient) -> None:
    project_id = create_project(client)
    csv_content = (
        "site_name,latitude,longitude,acreage,jurisdiction\n"
        "River Road,42.110,-73.910,34,Greenfield County\n"
        "River Road,42.999,-73.111,50,Greenfield County\n"
    )

    body = import_csv(client, project_id, csv_content).json()

    assert body["summary"]["duplicate_rows"] == 1
    assert body["summary"]["imported_rows"] == 1
    assert len(client.get(f"/api/projects/{project_id}/sites").json()) == 1


def test_re_uploading_the_same_csv_does_not_duplicate_sites(client: TestClient) -> None:
    project_id = create_project(client)
    import_csv(client, project_id, DEMO_CSV)

    body = import_csv(client, project_id, DEMO_CSV).json()

    assert body["summary"]["duplicate_rows"] == 5
    assert body["summary"]["imported_rows"] == 0
    assert body["imported_sites"] == []
    assert len(client.get(f"/api/projects/{project_id}/sites").json()) == 5


def test_a_second_upload_adds_only_the_sites_that_are_new(client: TestClient) -> None:
    project_id = create_project(client)
    import_csv(client, project_id, DEMO_CSV)
    csv_content = (
        "site_name,latitude,longitude,acreage,jurisdiction\n"
        "River Road,42.110,-73.910,34,Greenfield County\n"
        "Quarry Lot,42.200,-73.800,29,Greenfield County\n"
    )

    body = import_csv(client, project_id, csv_content).json()

    assert body["summary"]["imported_rows"] == 1
    assert body["summary"]["duplicate_rows"] == 1
    assert [site["name"] for site in body["imported_sites"]] == ["Quarry Lot"]
    assert len(client.get(f"/api/projects/{project_id}/sites").json()) == 6


def test_the_same_site_name_in_two_different_projects_is_not_a_duplicate(
    client: TestClient,
) -> None:
    first = create_project(client, name="First")
    second = create_project(client, name="Second")
    import_csv(client, first, DEMO_CSV)

    body = import_csv(client, second, DEMO_CSV).json()

    assert body["summary"]["imported_rows"] == 5
    assert body["summary"]["duplicate_rows"] == 0
