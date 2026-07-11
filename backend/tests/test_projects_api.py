"""Project intake — API contract §Project."""

from fastapi.testclient import TestClient

VALID_PROJECT = {
    "name": "Hudson Valley Community Solar",
    "project_type": "community_solar",
    "target_capacity_mw": 5,
    "minimum_acres": 25,
    "target_state": "NY",
    "screening_criteria": {
        "maximum_flood_overlap_percent": 5,
        "maximum_wetland_overlap_percent": 10,
        "maximum_road_distance_miles": 2,
    },
    "notes": "Five candidate parcels from the county land broker.",
}


def test_creating_a_project_returns_it_with_an_id_and_timestamps(client: TestClient) -> None:
    response = client.post("/api/projects", json=VALID_PROJECT)

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "Hudson Valley Community Solar"
    assert body["project_type"] == "community_solar"
    assert body["minimum_acres"] == 25
    assert body["target_state"] == "NY"
    assert body["screening_criteria"]["maximum_wetland_overlap_percent"] == 10
    assert body["status"] == "active"
    assert body["created_at"]
    assert body["updated_at"]


def test_screening_criteria_default_to_the_spec_thresholds_when_omitted(
    client: TestClient,
) -> None:
    payload = {k: v for k, v in VALID_PROJECT.items() if k != "screening_criteria"}

    body = client.post("/api/projects", json=payload).json()

    assert body["screening_criteria"] == {
        "maximum_flood_overlap_percent": 5,
        "maximum_wetland_overlap_percent": 10,
        "maximum_road_distance_miles": 2,
    }


def test_an_empty_project_name_is_rejected(client: TestClient) -> None:
    response = client.post("/api/projects", json={**VALID_PROJECT, "name": "   "})

    assert response.status_code == 422


def test_a_non_positive_minimum_acreage_is_rejected(client: TestClient) -> None:
    response = client.post("/api/projects", json={**VALID_PROJECT, "minimum_acres": 0})

    assert response.status_code == 422


def test_an_unknown_project_type_is_rejected(client: TestClient) -> None:
    response = client.post("/api/projects", json={**VALID_PROJECT, "project_type": "fusion"})

    assert response.status_code == 422


def test_listing_projects_returns_them_newest_first(client: TestClient) -> None:
    client.post("/api/projects", json={**VALID_PROJECT, "name": "First"})
    client.post("/api/projects", json={**VALID_PROJECT, "name": "Second"})

    response = client.get("/api/projects")

    assert response.status_code == 200
    assert [p["name"] for p in response.json()] == ["Second", "First"]


def test_listing_projects_with_none_created_returns_an_empty_list(client: TestClient) -> None:
    response = client.get("/api/projects")

    assert response.status_code == 200
    assert response.json() == []


def test_a_project_can_be_retrieved_by_id(client: TestClient) -> None:
    created = client.post("/api/projects", json=VALID_PROJECT).json()

    response = client.get(f"/api/projects/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_an_unknown_project_id_returns_a_clear_404(client: TestClient) -> None:
    response = client.get("/api/projects/2f3a5c9e-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_a_malformed_project_id_returns_404_rather_than_a_server_error(
    client: TestClient,
) -> None:
    response = client.get("/api/projects/not-a-uuid")

    assert response.status_code == 404
