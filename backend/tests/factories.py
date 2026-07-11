"""Deterministic test fixtures. No randomness, no network, no external service."""

from typing import Any

import httpx
from fastapi.testclient import TestClient

# The five candidate sites from spec §7, verbatim.
DEMO_CSV = (
    "site_name,latitude,longitude,acreage,jurisdiction,"
    "road_distance_miles,flood_overlap_percent,wetland_overlap_percent\n"
    "River Road,42.110,-73.910,34,Greenfield County,0.7,0,2\n"
    "Oak Parcel,42.145,-73.880,27,Greenfield County,1.1,4,14\n"
    "County Route 9,42.090,-73.970,22,Greenfield County,0.4,0,1\n"
    "Mill Farm,42.180,-73.930,41,Greenfield County,2.8,7,4\n"
    "North Ridge,42.125,-73.850,31,Greenfield County,1.3,2,5\n"
)


def create_project(client: TestClient, name: str = "Hudson Valley Community Solar") -> str:
    """Create the demo project and return its id."""
    response = client.post(
        "/api/projects",
        json={
            "name": name,
            "project_type": "community_solar",
            "target_capacity_mw": 5,
            "minimum_acres": 25,
            "target_state": "NY",
            "screening_criteria": {
                "maximum_flood_overlap_percent": 5,
                "maximum_wetland_overlap_percent": 10,
                "maximum_road_distance_miles": 2,
            },
        },
    )
    assert response.status_code == 201, response.text
    project_id: str = response.json()["id"]
    return project_id


def import_csv(client: TestClient, project_id: str, content: str) -> httpx.Response:
    return client.post(
        f"/api/projects/{project_id}/sites/import",
        files={"file": ("candidate-sites.csv", content.encode(), "text/csv")},
    )


def screen(
    client: TestClient, project_id: str, idempotency_key: str | None = None
) -> httpx.Response:
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
    return client.post(f"/api/projects/{project_id}/screenings", headers=headers)


def screened_project(client: TestClient) -> dict[str, Any]:
    """Create the demo project, import the five sites, and run one screening."""
    project_id = create_project(client)
    import_csv(client, project_id, DEMO_CSV)
    response = screen(client, project_id)
    assert response.status_code == 201, response.text
    run: dict[str, Any] = response.json()
    return run
