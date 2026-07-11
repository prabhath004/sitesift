"""The seeded demo project — spec §24, "Load Sample Solar Project"."""

from fastapi.testclient import TestClient


def test_seeding_creates_the_project_from_the_spec(client: TestClient) -> None:
    response = client.post("/api/demo/seed")

    assert response.status_code == 201
    project = response.json()["project"]
    assert project["name"] == "Hudson Valley Community Solar"
    assert project["project_type"] == "community_solar"
    assert project["target_capacity_mw"] == 5
    assert project["minimum_acres"] == 25
    assert project["target_state"] == "NY"
    assert project["screening_criteria"] == {
        "maximum_flood_overlap_percent": 5,
        "maximum_wetland_overlap_percent": 10,
        "maximum_road_distance_miles": 2,
    }


def test_seeding_creates_the_five_candidate_sites(client: TestClient) -> None:
    body = client.post("/api/demo/seed").json()

    project_id = body["project"]["id"]
    sites = client.get(f"/api/projects/{project_id}/sites").json()
    assert [site["name"] for site in sites] == [
        "River Road",
        "Oak Parcel",
        "County Route 9",
        "Mill Farm",
        "North Ridge",
    ]


def test_seeding_completes_one_deterministic_screening_run(client: TestClient) -> None:
    body = client.post("/api/demo/seed").json()

    run = body["screening_run"]
    assert run["status"] == "completed"
    assert len(run["results"]) == 5
    assert run["results"][0]["site"]["name"] == "River Road"
    assert run["results"][0]["score"]["recommendation_status"] == "recommended"
    assert run["results"][-1]["score"]["recommendation_status"] == "reject"


def test_seeding_twice_is_safe_and_does_not_duplicate_anything(client: TestClient) -> None:
    first = client.post("/api/demo/seed").json()

    second = client.post("/api/demo/seed")

    assert second.status_code == 200, "the second call is a no-op, not a creation"
    assert second.json()["project"]["id"] == first["project"]["id"]
    assert second.json()["screening_run"]["id"] == first["screening_run"]["id"]

    assert len(client.get("/api/projects").json()) == 1
    project_id = first["project"]["id"]
    assert len(client.get(f"/api/projects/{project_id}/sites").json()) == 5


def test_the_seeded_run_is_the_one_the_demo_narrative_describes(client: TestClient) -> None:
    # Spec §7: River Road recommended, Oak Parcel wetland risk, Mill Farm flood
    # and access risk, County Route 9 rejected for insufficient acreage.
    run = client.post("/api/demo/seed").json()["screening_run"]
    results = {result["site"]["name"]: result for result in run["results"]}

    assert results["Oak Parcel"]["risks"][0]["rule"] == "wetland_overlap_threshold"
    assert {risk["rule"] for risk in results["Mill Farm"]["risks"]} == {
        "flood_overlap_threshold",
        "road_distance_threshold",
    }
    assert results["County Route 9"]["risks"][0]["severity"] == "fatal"
