"""Deterministic scoring rules — spec §14.

Every case here is a pure function call. No database, no network, no model.
The scoring bands come from spec §14; the two rules the spec leaves open are
resolved in docs/BACKEND_CONTRACT_NOTES.md:

* acreage below the project minimum is the only FATAL deterministic finding;
* permitting readiness scores the spec's "ambiguous or missing ordinance
  evidence" band (+10) while no document has been analyzed.
"""

from app.schemas.common import FindingSeverity, RecommendationStatus
from app.schemas.finding import FindingCategory, FindingGroup
from app.schemas.screening import PermittingAnalysisStatus
from app.services.scoring import ScoringCriteria, SiteScoringInput, score_site

CRITERIA = ScoringCriteria(
    minimum_acres=25,
    maximum_flood_overlap_percent=5,
    maximum_wetland_overlap_percent=10,
    maximum_road_distance_miles=2,
)


def site(
    *,
    acreage: float = 34,
    road: float | None = 0.7,
    flood: float | None = 0,
    wetland: float | None = 2,
) -> SiteScoringInput:
    """A site that clears every threshold, unless a field is overridden."""
    return SiteScoringInput(
        acreage=acreage,
        road_distance_miles=road,
        flood_overlap_percent=flood,
        wetland_overlap_percent=wetland,
    )


def award(result: object, rule: str) -> int:
    """Points awarded by a single named rule."""
    items = [item for item in result.breakdown if item.rule == rule]  # type: ignore[attr-defined]
    assert len(items) == 1, f"expected exactly one {rule!r} breakdown item, got {len(items)}"
    return items[0].points_awarded


# ---------------------------------------------------------------- site suitability


def test_acreage_at_the_minimum_earns_full_site_suitability() -> None:
    result = score_site(site(acreage=25), CRITERIA)

    assert award(result, "acreage_minimum") == 25
    assert result.site_suitability_score == 25


def test_acreage_above_the_minimum_earns_full_site_suitability() -> None:
    assert score_site(site(acreage=34), CRITERIA).site_suitability_score == 25


def test_acreage_just_below_the_minimum_falls_to_the_90_percent_band() -> None:
    # 24.9 / 25 = 99.6% — the first point below the requirement.
    assert award(score_site(site(acreage=24.9), CRITERIA), "acreage_minimum") == 15


def test_acreage_at_90_percent_of_the_minimum_stays_in_the_90_percent_band() -> None:
    assert award(score_site(site(acreage=22.5), CRITERIA), "acreage_minimum") == 15


def test_acreage_just_under_90_percent_falls_to_the_75_percent_band() -> None:
    assert award(score_site(site(acreage=22.4), CRITERIA), "acreage_minimum") == 8


def test_acreage_at_75_percent_of_the_minimum_stays_in_the_75_percent_band() -> None:
    assert award(score_site(site(acreage=18.75), CRITERIA), "acreage_minimum") == 8


def test_acreage_below_75_percent_of_the_minimum_earns_nothing() -> None:
    assert award(score_site(site(acreage=18.7), CRITERIA), "acreage_minimum") == 0


def test_acreage_below_the_minimum_is_a_fatal_finding() -> None:
    result = score_site(site(acreage=22), CRITERIA)

    fatal = [f for f in result.findings if f.severity is FindingSeverity.FATAL]
    assert len(fatal) == 1
    assert fatal[0].rule == "acreage_minimum"
    assert fatal[0].category is FindingCategory.SITE_SUITABILITY
    assert fatal[0].actual_value == 22
    assert fatal[0].threshold_value == 25


def test_acreage_at_the_minimum_produces_a_positive_signal_not_a_risk() -> None:
    result = score_site(site(acreage=34), CRITERIA)

    signals = [f for f in result.findings if f.group is FindingGroup.POSITIVE_SIGNAL]
    assert any(f.rule == "acreage_minimum" for f in signals)
    assert not [f for f in result.findings if f.severity is FindingSeverity.FATAL]


# ---------------------------------------------------------------- environmental


def test_flood_overlap_at_the_threshold_earns_full_flood_points() -> None:
    assert award(score_site(site(flood=5), CRITERIA), "flood_overlap_threshold") == 12


def test_flood_overlap_just_over_the_threshold_earns_the_partial_band() -> None:
    assert award(score_site(site(flood=5.1), CRITERIA), "flood_overlap_threshold") == 6


def test_flood_overlap_at_one_and_a_half_times_the_threshold_stays_in_the_partial_band() -> None:
    assert award(score_site(site(flood=7.5), CRITERIA), "flood_overlap_threshold") == 6


def test_flood_overlap_materially_over_the_threshold_earns_nothing() -> None:
    assert award(score_site(site(flood=7.6), CRITERIA), "flood_overlap_threshold") == 0


def test_flood_overlap_over_the_threshold_is_a_high_severity_risk() -> None:
    result = score_site(site(flood=7), CRITERIA)

    finding = next(f for f in result.findings if f.rule == "flood_overlap_threshold")
    assert finding.severity is FindingSeverity.HIGH
    assert finding.group is FindingGroup.RISK
    assert finding.actual_value == 7
    assert finding.threshold_value == 5


def test_wetland_overlap_at_the_threshold_earns_full_wetland_points() -> None:
    assert award(score_site(site(wetland=10), CRITERIA), "wetland_overlap_threshold") == 13


def test_wetland_overlap_just_over_the_threshold_earns_the_partial_band() -> None:
    assert award(score_site(site(wetland=10.1), CRITERIA), "wetland_overlap_threshold") == 7


def test_wetland_overlap_at_one_and_a_half_times_the_threshold_stays_in_the_partial_band() -> None:
    assert award(score_site(site(wetland=15), CRITERIA), "wetland_overlap_threshold") == 7


def test_wetland_overlap_materially_over_the_threshold_earns_nothing() -> None:
    assert award(score_site(site(wetland=15.1), CRITERIA), "wetland_overlap_threshold") == 0


def test_high_wetland_overlap_produces_the_breakdown_record_from_the_contract() -> None:
    # The worked example in docs/BACKEND_CONTRACT_NOTES.md.
    result = score_site(site(wetland=14), CRITERIA)

    item = next(i for i in result.breakdown if i.rule == "wetland_overlap_threshold")
    assert item.category is FindingCategory.ENVIRONMENTAL
    assert item.actual_value == 14
    assert item.threshold_value == 10
    assert item.points_possible == 13
    assert item.points_awarded == 7
    assert item.severity is FindingSeverity.HIGH
    assert item.explanation


def test_environmental_score_is_the_sum_of_the_flood_and_wetland_rules() -> None:
    result = score_site(site(flood=7, wetland=14), CRITERIA)

    assert result.environmental_score == 6 + 7


# ---------------------------------------------------------------- access and proximity


def test_road_distance_at_the_preferred_distance_earns_full_access_points() -> None:
    assert score_site(site(road=2), CRITERIA).access_score == 25


def test_road_distance_just_over_the_preferred_distance_earns_the_partial_band() -> None:
    assert score_site(site(road=2.1), CRITERIA).access_score == 15


def test_road_distance_at_one_and_a_half_times_the_preferred_distance_stays_partial() -> None:
    assert score_site(site(road=3), CRITERIA).access_score == 15


def test_road_distance_beyond_one_and_a_half_times_the_preferred_distance_earns_five() -> None:
    # Spec §14 keeps 5 points here rather than dropping to zero.
    assert score_site(site(road=3.1), CRITERIA).access_score == 5


def test_excessive_road_distance_is_a_high_severity_risk() -> None:
    result = score_site(site(road=2.8), CRITERIA)

    finding = next(f for f in result.findings if f.rule == "road_distance_threshold")
    assert finding.severity is FindingSeverity.HIGH
    assert finding.group is FindingGroup.RISK


# ---------------------------------------------------------------- missing optional inputs


def test_missing_flood_value_scores_zero_and_reports_missing_information() -> None:
    result = score_site(site(flood=None), CRITERIA)

    assert award(result, "flood_overlap_threshold") == 0
    finding = next(f for f in result.findings if f.rule == "flood_overlap_threshold")
    assert finding.group is FindingGroup.MISSING_INFORMATION
    assert finding.severity is FindingSeverity.WARNING
    assert finding.actual_value is None


def test_missing_wetland_value_scores_zero_and_reports_missing_information() -> None:
    result = score_site(site(wetland=None), CRITERIA)

    assert award(result, "wetland_overlap_threshold") == 0
    finding = next(f for f in result.findings if f.rule == "wetland_overlap_threshold")
    assert finding.group is FindingGroup.MISSING_INFORMATION


def test_missing_road_value_scores_zero_and_reports_missing_information() -> None:
    result = score_site(site(road=None), CRITERIA)

    assert result.access_score == 0
    finding = next(f for f in result.findings if f.rule == "road_distance_threshold")
    assert finding.group is FindingGroup.MISSING_INFORMATION


def test_a_missing_input_is_never_counted_as_a_risk() -> None:
    result = score_site(site(road=None, flood=None, wetland=None), CRITERIA)

    assert not [f for f in result.findings if f.group is FindingGroup.RISK]


# ---------------------------------------------------------------- permitting readiness


def test_permitting_is_not_analyzed_on_the_deterministic_branch() -> None:
    result = score_site(site(), CRITERIA)

    assert result.permitting_status is PermittingAnalysisStatus.NOT_ANALYZED
    assert result.permitting_score == 10


def test_permitting_reports_itself_as_missing_information_rather_than_a_pass() -> None:
    result = score_site(site(), CRITERIA)

    finding = next(f for f in result.findings if f.rule == "permitting_readiness")
    assert finding.group is FindingGroup.MISSING_INFORMATION
    assert finding.severity is FindingSeverity.WARNING
    assert finding.category is FindingCategory.PERMITTING


# ---------------------------------------------------------------- overall score and status


def test_overall_score_is_the_sum_of_the_four_categories() -> None:
    result = score_site(site(acreage=34, road=0.7, flood=0, wetland=2), CRITERIA)

    assert result.overall_score == (
        result.site_suitability_score
        + result.environmental_score
        + result.access_score
        + result.permitting_score
    )
    assert result.overall_score == 85


def test_a_fatal_finding_overrides_an_otherwise_strong_score() -> None:
    # 22 acres: every other check passes, so the numeric score stays high.
    result = score_site(site(acreage=22, road=0.4, flood=0, wetland=1), CRITERIA)

    assert result.overall_score == 68
    assert result.recommendation_status is RecommendationStatus.REJECT


def test_status_is_recommended_at_eighty() -> None:
    assert _status_for_score(80) is RecommendationStatus.RECOMMENDED


def test_status_is_recommended_with_review_at_seventy() -> None:
    assert _status_for_score(70) is RecommendationStatus.RECOMMENDED_WITH_REVIEW


def test_status_is_needs_investigation_at_fifty_five() -> None:
    assert _status_for_score(55) is RecommendationStatus.NEEDS_INVESTIGATION


def test_status_is_high_risk_below_fifty_five() -> None:
    assert _status_for_score(54) is RecommendationStatus.HIGH_RISK


def _status_for_score(score: int) -> RecommendationStatus:
    from app.services.scoring import recommendation_for

    return recommendation_for(score, fatal_findings=0)


def test_a_fatal_finding_rejects_regardless_of_score() -> None:
    from app.services.scoring import recommendation_for

    assert recommendation_for(100, fatal_findings=1) is RecommendationStatus.REJECT


# ---------------------------------------------------------------- explainability


def test_every_scoring_rule_appears_in_the_breakdown() -> None:
    result = score_site(site(), CRITERIA)

    assert {item.rule for item in result.breakdown} == {
        "acreage_minimum",
        "flood_overlap_threshold",
        "wetland_overlap_threshold",
        "road_distance_threshold",
        "permitting_readiness",
    }


def test_the_breakdown_accounts_for_all_one_hundred_points() -> None:
    result = score_site(site(flood=9, wetland=14, road=3.4, acreage=20), CRITERIA)

    assert sum(item.points_possible for item in result.breakdown) == 100
    assert sum(item.points_awarded for item in result.breakdown) == result.overall_score


def test_the_explanation_names_every_deduction() -> None:
    result = score_site(site(wetland=14, road=2.8), CRITERIA)

    assert "wetland" in result.explanation.lower()
    assert "road" in result.explanation.lower()
    assert "permitting" in result.explanation.lower()
