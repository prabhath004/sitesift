"""Screening runs, ranking, persistence, and idempotency — spec §14, §18.

The five-site expectations are the demo scenario from spec §7, scored by the
§14 rules. Working values, for reference:

    River Road      25 + (12+13) + 25 + 10 = 85   recommended
    North Ridge     25 + (12+13) + 25 + 10 = 85   recommended
    Oak Parcel      25 + (12+ 7) + 25 + 10 = 79   recommended_with_review
    Mill Farm       25 + ( 6+13) + 15 + 10 = 69   needs_investigation
    County Route 9   8 + (12+13) + 25 + 10 = 68   reject (fatal: 22 < 25 acres)
"""

from typing import Any

from fastapi.testclient import TestClient

from tests.factories import DEMO_CSV, create_project, import_csv, screen, screened_project


def results_by_name(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {result["site"]["name"]: result for result in run["results"]}


# ---------------------------------------------------------------- running a screening


def test_a_screening_run_completes_and_scores_every_site(client: TestClient) -> None:
    run = screened_project(client)

    assert run["status"] == "completed"
    assert run["started_at"]
    assert run["completed_at"]
    assert run["error_message"] is None
    assert len(run["results"]) == 5


def test_screening_a_project_with_no_sites_is_rejected(client: TestClient) -> None:
    project_id = create_project(client)

    response = screen(client, project_id)

    assert response.status_code == 409
    assert "no candidate sites" in response.json()["detail"].lower()


def test_screening_an_unknown_project_returns_404(client: TestClient) -> None:
    response = screen(client, "2f3a5c9e-0000-4000-8000-000000000000")

    assert response.status_code == 404


# ---------------------------------------------------------------- scores and ranking


def test_the_demo_sites_score_exactly_as_the_rules_require(client: TestClient) -> None:
    results = results_by_name(screened_project(client))

    assert results["River Road"]["score"]["overall_score"] == 85
    assert results["North Ridge"]["score"]["overall_score"] == 85
    assert results["Oak Parcel"]["score"]["overall_score"] == 79
    assert results["Mill Farm"]["score"]["overall_score"] == 69
    assert results["County Route 9"]["score"]["overall_score"] == 68


def test_the_demo_sites_receive_the_recommendation_statuses_the_rules_require(
    client: TestClient,
) -> None:
    results = results_by_name(screened_project(client))

    assert results["River Road"]["score"]["recommendation_status"] == "recommended"
    assert results["Oak Parcel"]["score"]["recommendation_status"] == "recommended_with_review"
    assert results["Mill Farm"]["score"]["recommendation_status"] == "needs_investigation"
    assert results["County Route 9"]["score"]["recommendation_status"] == "reject"


def test_sites_are_ranked_from_highest_score_to_lowest(client: TestClient) -> None:
    run = screened_project(client)

    scores = [result["score"]["overall_score"] for result in run["results"]]
    assert scores == sorted(scores, reverse=True)
    assert [result["score"]["rank"] for result in run["results"]] == [1, 2, 3, 4, 5]


def test_the_demo_ranking_matches_the_specs_expected_order(client: TestClient) -> None:
    run = screened_project(client)

    assert [result["site"]["name"] for result in run["results"]] == [
        "River Road",
        "North Ridge",
        "Oak Parcel",
        "Mill Farm",
        "County Route 9",
    ]


def test_a_tie_on_score_is_broken_by_import_order_not_arbitrarily(client: TestClient) -> None:
    # River Road and North Ridge both score 85. River Road is row 2 of the CSV,
    # North Ridge row 6, so River Road must rank first — and must do so on every run.
    for _ in range(3):
        run = screened_project(client)
        names = [result["site"]["name"] for result in run["results"]]
        assert names.index("River Road") < names.index("North Ridge")


def test_category_scores_add_up_to_the_overall_score(client: TestClient) -> None:
    run = screened_project(client)

    for result in run["results"]:
        score = result["score"]
        assert score["overall_score"] == (
            score["site_suitability_score"]
            + score["environmental_score"]
            + score["access_score"]
            + score["permitting_score"]
        )


# ---------------------------------------------------------------- explainability


def test_every_score_carries_a_breakdown_that_accounts_for_all_hundred_points(
    client: TestClient,
) -> None:
    run = screened_project(client)

    for result in run["results"]:
        breakdown = result["score"]["breakdown"]
        assert sum(item["points_possible"] for item in breakdown) == 100
        assert sum(item["points_awarded"] for item in breakdown) == result["score"]["overall_score"]


def test_a_deduction_names_its_rule_actual_value_and_threshold(client: TestClient) -> None:
    results = results_by_name(screened_project(client))

    breakdown = results["Oak Parcel"]["score"]["breakdown"]
    wetland = next(item for item in breakdown if item["rule"] == "wetland_overlap_threshold")
    assert wetland["actual_value"] == 14
    assert wetland["threshold_value"] == 10
    assert wetland["points_possible"] == 13
    assert wetland["points_awarded"] == 7
    assert wetland["severity"] == "high"
    assert wetland["category"] == "environmental"
    assert wetland["explanation"]


def test_permitting_is_reported_as_not_analyzed_on_every_site(client: TestClient) -> None:
    run = screened_project(client)

    for result in run["results"]:
        assert result["score"]["permitting_status"] == "not_analyzed"
        assert result["score"]["permitting_score"] == 10


# ---------------------------------------------------------------- findings


def test_a_clean_site_reports_positive_signals_and_no_risks(client: TestClient) -> None:
    results = results_by_name(screened_project(client))

    river_road = results["River Road"]
    assert river_road["risks"] == []
    signals = {finding["rule"] for finding in river_road["positive_signals"]}
    assert signals == {
        "acreage_minimum",
        "flood_overlap_threshold",
        "wetland_overlap_threshold",
        "road_distance_threshold",
    }


def test_a_wetland_breach_is_reported_as_a_high_risk(client: TestClient) -> None:
    results = results_by_name(screened_project(client))

    risks = results["Oak Parcel"]["risks"]
    assert len(risks) == 1
    assert risks[0]["rule"] == "wetland_overlap_threshold"
    assert risks[0]["severity"] == "high"
    assert risks[0]["actual_value"] == 14


def test_flood_and_access_breaches_are_both_reported(client: TestClient) -> None:
    results = results_by_name(screened_project(client))

    rules = {risk["rule"] for risk in results["Mill Farm"]["risks"]}
    assert rules == {"flood_overlap_threshold", "road_distance_threshold"}


def test_insufficient_acreage_is_reported_as_a_fatal_risk(client: TestClient) -> None:
    results = results_by_name(screened_project(client))

    risks = results["County Route 9"]["risks"]
    assert [risk["severity"] for risk in risks] == ["fatal"]
    assert risks[0]["rule"] == "acreage_minimum"


def test_missing_information_is_reported_separately_from_risks(client: TestClient) -> None:
    results = results_by_name(screened_project(client))

    missing = results["River Road"]["missing_information"]
    rules = {finding["rule"] for finding in missing}
    assert "permitting_readiness" in rules
    assert "missing_site_control" in rules
    assert "missing_interconnection" in rules


def test_every_deterministic_finding_declares_its_source(client: TestClient) -> None:
    run = screened_project(client)

    for result in run["results"]:
        findings = result["positive_signals"] + result["risks"] + result["missing_information"]
        assert findings
        for finding in findings:
            assert finding["source_type"] == "deterministic"
            assert finding["review_status"] == "pending"
            assert finding["confidence"] is None


def test_findings_are_retrievable_for_a_site(client: TestClient) -> None:
    run = screened_project(client)
    site_id = run["results"][0]["site"]["id"]

    response = client.get(f"/api/sites/{site_id}/findings")

    assert response.status_code == 200
    assert response.json()
    assert all(f["source_type"] == "deterministic" for f in response.json())


def test_findings_for_an_unknown_site_return_404(client: TestClient) -> None:
    response = client.get("/api/sites/2f3a5c9e-0000-4000-8000-000000000000/findings")

    assert response.status_code == 404


# ---------------------------------------------------------------- persistence


def test_a_completed_run_can_be_retrieved_with_its_results(client: TestClient) -> None:
    run_id = screened_project(client)["id"]

    response = client.get(f"/api/screenings/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["results"]) == 5
    assert body["results"][0]["score"]["rank"] == 1


def test_an_unknown_screening_id_returns_404(client: TestClient) -> None:
    response = client.get("/api/screenings/2f3a5c9e-0000-4000-8000-000000000000")

    assert response.status_code == 404


def test_a_screened_site_carries_its_score_and_findings(client: TestClient) -> None:
    run = screened_project(client)
    site_id = next(r["site"]["id"] for r in run["results"] if r["site"]["name"] == "Oak Parcel")

    body = client.get(f"/api/sites/{site_id}").json()

    assert body["score"]["overall_score"] == 79
    assert body["score"]["recommendation_status"] == "recommended_with_review"
    assert body["risks"][0]["rule"] == "wetland_overlap_threshold"
    assert body["score"]["explanation"]


def test_screening_marks_the_project_as_screened(client: TestClient) -> None:
    project_id = create_project(client)
    import_csv(client, project_id, DEMO_CSV)
    screen(client, project_id)

    assert client.get(f"/api/projects/{project_id}").json()["status"] == "screened"


def test_a_second_run_rescoring_the_same_sites_replaces_nothing_from_the_first(
    client: TestClient,
) -> None:
    project_id = create_project(client)
    import_csv(client, project_id, DEMO_CSV)

    first = screen(client, project_id).json()
    second = screen(client, project_id).json()

    assert first["id"] != second["id"]
    assert client.get(f"/api/screenings/{first['id']}").json()["results"]
    assert client.get(f"/api/screenings/{second['id']}").json()["results"]


# ---------------------------------------------------------------- idempotency


def test_a_repeated_idempotency_key_returns_the_first_run_instead_of_creating_a_second(
    client: TestClient,
) -> None:
    project_id = create_project(client)
    import_csv(client, project_id, DEMO_CSV)

    first = screen(client, project_id, idempotency_key="run-1")
    second = screen(client, project_id, idempotency_key="run-1")

    assert first.status_code == 201
    assert second.status_code == 200, "a replay is not a creation"
    assert first.json()["id"] == second.json()["id"]


def test_a_replayed_screening_does_not_duplicate_scores_or_findings(client: TestClient) -> None:
    project_id = create_project(client)
    import_csv(client, project_id, DEMO_CSV)
    screen(client, project_id, idempotency_key="run-1")

    replay = screen(client, project_id, idempotency_key="run-1").json()

    assert len(replay["results"]) == 5
    site_id = replay["results"][0]["site"]["id"]
    findings = client.get(f"/api/sites/{site_id}/findings").json()
    assert len(findings) == len({finding["id"] for finding in findings})


def test_different_idempotency_keys_create_different_runs(client: TestClient) -> None:
    project_id = create_project(client)
    import_csv(client, project_id, DEMO_CSV)

    first = screen(client, project_id, idempotency_key="run-1").json()
    second = screen(client, project_id, idempotency_key="run-2").json()

    assert first["id"] != second["id"]


def test_the_same_idempotency_key_in_another_project_creates_its_own_run(
    client: TestClient,
) -> None:
    first_project = create_project(client, name="First")
    second_project = create_project(client, name="Second")
    import_csv(client, first_project, DEMO_CSV)
    import_csv(client, second_project, DEMO_CSV)

    first = screen(client, first_project, idempotency_key="run-1")
    second = screen(client, second_project, idempotency_key="run-1")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


# ---------------------------------------------------------------- workflow events


def test_a_run_records_its_workflow_steps(client: TestClient) -> None:
    run_id = screened_project(client)["id"]

    response = client.get(f"/api/screenings/{run_id}/events")

    assert response.status_code == 200
    events = response.json()
    assert [event["step_name"] for event in events] == [
        "load_project",
        "load_candidate_sites",
        "score_sites",
        "rank_sites",
        "persist_results",
    ]
    assert all(event["status"] == "completed" for event in events)
    assert all(event["duration_ms"] is not None for event in events)
    assert all(event["error_message"] is None for event in events)


def test_workflow_events_for_an_unknown_run_return_404(client: TestClient) -> None:
    response = client.get("/api/screenings/2f3a5c9e-0000-4000-8000-000000000000/events")

    assert response.status_code == 404
