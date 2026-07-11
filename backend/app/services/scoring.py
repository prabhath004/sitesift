"""Deterministic site scoring — spec §14.

Ordinary arithmetic, no model, no I/O. Given the same site and the same
criteria this module returns the same score forever, which is the whole point:
`app/services/` computes numbers, `app/workflows/` never does (CLAUDE.md rule 1).

Two things the spec leaves open, resolved here and explained in
docs/BACKEND_CONTRACT_NOTES.md:

* **What is fatal.** §14 makes ``Reject`` reachable only through a fatal finding,
  and §7 expects County Route 9 — 22 acres against a 25-acre minimum — to be
  rejected. Acreage below the project minimum is therefore the one fatal
  deterministic rule. Threshold exceedances are ``HIGH``, never fatal.
* **Permitting readiness.** Nothing on this branch reads an ordinance, so
  permitting scores §14's own "ambiguous or missing ordinance evidence" band
  (+10 of 25) and reports ``NOT_ANALYZED``. It is never presented as a pass.

"Slightly over" a threshold means up to 1.5x it, reusing the multiple §14 states
explicitly for road distance. Beyond 1.5x is "materially over".
"""

from dataclasses import dataclass

from app.schemas.common import FindingSeverity, RecommendationStatus
from app.schemas.finding import FindingCategory, FindingDraft, FindingGroup
from app.schemas.screening import PermittingAnalysisStatus, ScoreBreakdownItem

MATERIALLY_OVER_MULTIPLE = 1.5

ACREAGE_POINTS = 25
FLOOD_POINTS = 12
WETLAND_POINTS = 13
ROAD_POINTS = 25
PERMITTING_POINTS = 25

# §14: "Ambiguous or missing ordinance evidence: +10".
PERMITTING_NOT_ANALYZED_POINTS = 10

# Known-unknowns every early-stage screening carries (spec §10.4). They are
# facts we have not been given, not risks we have found, so they score nothing.
STANDARD_MISSING_INFORMATION = (
    ("site_control", "Landowner site-control status"),
    ("interconnection", "Utility interconnection availability"),
    ("title", "Current title or ownership report"),
)


@dataclass(frozen=True)
class ScoringCriteria:
    """Project thresholds a site is measured against."""

    minimum_acres: float
    maximum_flood_overlap_percent: float
    maximum_wetland_overlap_percent: float
    maximum_road_distance_miles: float


@dataclass(frozen=True)
class SiteScoringInput:
    """The measurable facts about one candidate site.

    The three optional values stand in for geospatial lookups a production
    system would compute (spec §12.1). ``None`` means "not provided", which is
    scored as unverified — never as a pass.
    """

    acreage: float
    road_distance_miles: float | None
    flood_overlap_percent: float | None
    wetland_overlap_percent: float | None


@dataclass(frozen=True)
class SiteScoringResult:
    site_suitability_score: int
    environmental_score: int
    access_score: int
    permitting_score: int
    overall_score: int
    permitting_status: PermittingAnalysisStatus
    recommendation_status: RecommendationStatus
    explanation: str
    breakdown: list[ScoreBreakdownItem]
    findings: list[FindingDraft]


def score_site(site: SiteScoringInput, criteria: ScoringCriteria) -> SiteScoringResult:
    """Score one site. Pure: same input, same output, always."""
    acreage = _score_acreage(site.acreage, criteria.minimum_acres)
    flood = _score_overlap(
        rule="flood_overlap_threshold",
        label="Flood",
        value=site.flood_overlap_percent,
        threshold=criteria.maximum_flood_overlap_percent,
        points_possible=FLOOD_POINTS,
        partial_points=6,
    )
    wetland = _score_overlap(
        rule="wetland_overlap_threshold",
        label="Wetland",
        value=site.wetland_overlap_percent,
        threshold=criteria.maximum_wetland_overlap_percent,
        points_possible=WETLAND_POINTS,
        partial_points=7,
    )
    road = _score_road_distance(site.road_distance_miles, criteria.maximum_road_distance_miles)
    permitting = _score_permitting()

    rules = [acreage, flood, wetland, road, permitting]
    breakdown = [item for item, _ in rules]
    findings = [finding for _, finding in rules]
    findings.extend(_standard_missing_information())

    site_suitability_score = acreage[0].points_awarded
    environmental_score = flood[0].points_awarded + wetland[0].points_awarded
    access_score = road[0].points_awarded
    permitting_score = permitting[0].points_awarded
    overall_score = site_suitability_score + environmental_score + access_score + permitting_score

    fatal_findings = sum(1 for f in findings if f.severity is FindingSeverity.FATAL)

    return SiteScoringResult(
        site_suitability_score=site_suitability_score,
        environmental_score=environmental_score,
        access_score=access_score,
        permitting_score=permitting_score,
        overall_score=overall_score,
        permitting_status=PermittingAnalysisStatus.NOT_ANALYZED,
        recommendation_status=recommendation_for(overall_score, fatal_findings=fatal_findings),
        explanation=_explain(overall_score, breakdown),
        breakdown=breakdown,
        findings=findings,
    )


def recommendation_for(score: int, *, fatal_findings: int) -> RecommendationStatus:
    """Spec §14. A fatal finding overrides the number, however high it is."""
    if fatal_findings > 0:
        return RecommendationStatus.REJECT
    if score >= 80:
        return RecommendationStatus.RECOMMENDED
    if score >= 70:
        return RecommendationStatus.RECOMMENDED_WITH_REVIEW
    if score >= 55:
        return RecommendationStatus.NEEDS_INVESTIGATION
    return RecommendationStatus.HIGH_RISK


Rule = tuple[ScoreBreakdownItem, FindingDraft]


def _score_acreage(acreage: float, minimum_acres: float) -> Rule:
    if acreage >= minimum_acres:
        points, severity = ACREAGE_POINTS, FindingSeverity.INFO
    elif acreage >= 0.90 * minimum_acres:
        points, severity = 15, FindingSeverity.FATAL
    elif acreage >= 0.75 * minimum_acres:
        points, severity = 8, FindingSeverity.FATAL
    else:
        points, severity = 0, FindingSeverity.FATAL

    passed = severity is FindingSeverity.INFO
    if passed:
        title = "Acreage meets the project minimum"
        description = (
            f"{_fmt(acreage)} acres meets the {_fmt(minimum_acres)}-acre minimum for this project."
        )
    else:
        title = "Insufficient acreage"
        description = (
            f"{_fmt(acreage)} acres is below the {_fmt(minimum_acres)}-acre minimum for this "
            f"project. Insufficient acreage is a fatal flaw: the site cannot host the project "
            f"as specified."
        )

    return (
        ScoreBreakdownItem(
            category=FindingCategory.SITE_SUITABILITY,
            rule="acreage_minimum",
            actual_value=acreage,
            threshold_value=minimum_acres,
            points_possible=ACREAGE_POINTS,
            points_awarded=points,
            severity=severity,
            explanation=description,
        ),
        FindingDraft(
            category=FindingCategory.SITE_SUITABILITY,
            group=FindingGroup.POSITIVE_SIGNAL if passed else FindingGroup.RISK,
            rule="acreage_minimum",
            title=title,
            description=description,
            severity=severity,
            actual_value=acreage,
            threshold_value=minimum_acres,
            value=f"{_fmt(acreage)} acres",
        ),
    )


def _score_overlap(
    *,
    rule: str,
    label: str,
    value: float | None,
    threshold: float,
    points_possible: int,
    partial_points: int,
) -> Rule:
    """Flood and wetland overlap share one shape; only the point values differ."""
    if value is None:
        return _missing_input(
            rule=rule,
            category=FindingCategory.ENVIRONMENTAL,
            title=f"{label} overlap not provided",
            description=(
                f"No {label.lower()} overlap value was provided for this site, so the "
                f"{_fmt(threshold)}% threshold could not be checked. The check scores zero until "
                f"the value is supplied."
            ),
            points_possible=points_possible,
            threshold=threshold,
        )

    if value <= threshold:
        points, severity, group = (
            points_possible,
            FindingSeverity.INFO,
            FindingGroup.POSITIVE_SIGNAL,
        )
        title = f"{label} overlap is within the threshold"
        description = (
            f"{label} overlap of {_fmt(value)}% is within the configured "
            f"{_fmt(threshold)}% threshold."
        )
    else:
        severity, group = FindingSeverity.HIGH, FindingGroup.RISK
        materially_over = value > MATERIALLY_OVER_MULTIPLE * threshold
        points = 0 if materially_over else partial_points
        title = f"{label} overlap exceeds the threshold"
        degree = "materially exceeds" if materially_over else "exceeds"
        description = (
            f"{label} overlap of {_fmt(value)}% {degree} the configured "
            f"{_fmt(threshold)}% threshold."
        )

    return (
        ScoreBreakdownItem(
            category=FindingCategory.ENVIRONMENTAL,
            rule=rule,
            actual_value=value,
            threshold_value=threshold,
            points_possible=points_possible,
            points_awarded=points,
            severity=severity,
            explanation=description,
        ),
        FindingDraft(
            category=FindingCategory.ENVIRONMENTAL,
            group=group,
            rule=rule,
            title=title,
            description=description,
            severity=severity,
            actual_value=value,
            threshold_value=threshold,
            value=f"{_fmt(value)}%",
        ),
    )


def _score_road_distance(value: float | None, threshold: float) -> Rule:
    rule = "road_distance_threshold"

    if value is None:
        return _missing_input(
            rule=rule,
            category=FindingCategory.ACCESS,
            title="Road distance not provided",
            description=(
                f"No road distance was provided for this site, so the {_fmt(threshold)}-mile "
                f"preferred distance could not be checked. The check scores zero until the value "
                f"is supplied."
            ),
            points_possible=ROAD_POINTS,
            threshold=threshold,
        )

    if value <= threshold:
        points, severity, group = ROAD_POINTS, FindingSeverity.INFO, FindingGroup.POSITIVE_SIGNAL
        title = "Road access is within the preferred distance"
        description = (
            f"Road distance of {_fmt(value)} miles is within the preferred "
            f"{_fmt(threshold)}-mile distance."
        )
    else:
        severity, group = FindingSeverity.HIGH, FindingGroup.RISK
        # §14 keeps 5 points beyond 1.5x: poor access is a cost, not a disqualification.
        points = 5 if value > MATERIALLY_OVER_MULTIPLE * threshold else 15
        title = "Road distance exceeds the preferred distance"
        description = (
            f"Road distance of {_fmt(value)} miles exceeds the preferred "
            f"{_fmt(threshold)}-mile distance, which adds access and interconnection cost."
        )

    return (
        ScoreBreakdownItem(
            category=FindingCategory.ACCESS,
            rule=rule,
            actual_value=value,
            threshold_value=threshold,
            points_possible=ROAD_POINTS,
            points_awarded=points,
            severity=severity,
            explanation=description,
        ),
        FindingDraft(
            category=FindingCategory.ACCESS,
            group=group,
            rule=rule,
            title=title,
            description=description,
            severity=severity,
            actual_value=value,
            threshold_value=threshold,
            value=f"{_fmt(value)} miles",
        ),
    )


def _score_permitting() -> Rule:
    """Permitting readiness with no ordinance analyzed.

    This is the honest state of the deterministic branch: the document-analysis
    workflow has not run, so the category scores §14's missing-evidence band and
    says so. It is reported as missing information, not as a risk we found.
    """
    # Short in the breakdown, which the score explanation strings together; the
    # finding itself carries the full guidance.
    deduction = "Permitting readiness has not been analyzed: no ordinance has been reviewed."
    description = (
        "Permitting readiness has not been analyzed. No zoning or permitting document has been "
        "reviewed for this site, so the category scores the missing-evidence band "
        f"({PERMITTING_NOT_ANALYZED_POINTS} of {PERMITTING_POINTS}). Upload an ordinance to "
        "replace this placeholder with an evidence-backed assessment."
    )

    return (
        ScoreBreakdownItem(
            category=FindingCategory.PERMITTING,
            rule="permitting_readiness",
            points_possible=PERMITTING_POINTS,
            points_awarded=PERMITTING_NOT_ANALYZED_POINTS,
            severity=FindingSeverity.WARNING,
            explanation=deduction,
        ),
        FindingDraft(
            category=FindingCategory.PERMITTING,
            group=FindingGroup.MISSING_INFORMATION,
            rule="permitting_readiness",
            title="Permitting readiness not analyzed",
            description=description,
            severity=FindingSeverity.WARNING,
            value=PermittingAnalysisStatus.NOT_ANALYZED.value,
        ),
    )


def _missing_input(
    *,
    rule: str,
    category: FindingCategory,
    title: str,
    description: str,
    points_possible: int,
    threshold: float,
) -> Rule:
    """An input we were never given. Scores zero, but is not a risk we found."""
    return (
        ScoreBreakdownItem(
            category=category,
            rule=rule,
            actual_value=None,
            threshold_value=threshold,
            points_possible=points_possible,
            points_awarded=0,
            severity=FindingSeverity.WARNING,
            explanation=description,
        ),
        FindingDraft(
            category=category,
            group=FindingGroup.MISSING_INFORMATION,
            rule=rule,
            title=title,
            description=description,
            severity=FindingSeverity.WARNING,
            actual_value=None,
            threshold_value=threshold,
        ),
    )


def _standard_missing_information() -> list[FindingDraft]:
    return [
        FindingDraft(
            category=FindingCategory.DATA_COMPLETENESS,
            group=FindingGroup.MISSING_INFORMATION,
            rule=f"missing_{rule}",
            title=title,
            description=f"{title} has not been provided and must be confirmed before diligence.",
            severity=FindingSeverity.INFO,
        )
        for rule, title in STANDARD_MISSING_INFORMATION
    ]


CATEGORY_LABELS = {
    FindingCategory.SITE_SUITABILITY: "Site suitability",
    FindingCategory.ENVIRONMENTAL: "Environmental",
    FindingCategory.ACCESS: "Access and proximity",
    FindingCategory.PERMITTING: "Permitting readiness",
}


def _explain(overall_score: int, breakdown: list[ScoreBreakdownItem]) -> str:
    """Enumerate the deductions rather than summarize them (spec §9.5)."""
    parts = [f"Overall {overall_score}/100."]

    for category, label in CATEGORY_LABELS.items():
        items = [item for item in breakdown if item.category is category]
        awarded = sum(item.points_awarded for item in items)
        possible = sum(item.points_possible for item in items)
        lost = [item for item in items if item.points_awarded < item.points_possible]

        if not lost:
            parts.append(f"{label} {awarded}/{possible}.")
            continue

        deductions = "; ".join(
            f"{item.explanation.rstrip('.')} (−{item.points_possible - item.points_awarded})"
            for item in lost
        )
        parts.append(f"{label} {awarded}/{possible}: {deductions}.")

    return " ".join(parts)


def _fmt(value: float) -> str:
    """Render a measurement without a pointless trailing zero: 34.0 -> '34'."""
    return f"{value:g}"
