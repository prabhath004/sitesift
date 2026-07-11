"""Assembling screening results for the API.

Findings are grouped the way spec §10.4 presents them — positive signals, risks,
permitting requirements, and missing information as separate lists. Missing
information is never folded into risks: not knowing something is not the same as
having found a problem, and the UI must not blur the two. Permitting requirements
are separate again: an obligation an ordinance imposes is not a defect in the site.

Integration note. The finding counts and the recommended next action used to be
computed by the frontend's mock client. They are conclusions drawn from findings
and a recommendation status, so they are derived here instead — one derivation,
one answer, and the dashboard, the ranking, the site page, and the brief cannot
disagree about them.
"""

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.models.candidate_site import CandidateSite
from app.models.project import Project
from app.models.risk_finding import RiskFinding
from app.models.screening_run import ScreeningRun
from app.models.site_score import SiteScore
from app.schemas.brief import BriefRankingEntry, SiteBriefRead
from app.schemas.common import (
    FindingSeverity,
    RecommendationStatus,
    ReviewStatus,
    ScreeningRunStatus,
)
from app.schemas.document import DocumentResponse
from app.schemas.finding import FindingGroup, RiskFindingRead
from app.schemas.project import ProjectDashboardItem, ProjectRead
from app.schemas.screening import (
    ScreeningRunDetail,
    SiteDetail,
    SiteScoreRead,
    SiteScreeningResult,
)
from app.schemas.site import CandidateSiteRead

# What a developer should do next with a site, given how it scored. Deterministic:
# the same status always produces the same instruction.
NEXT_ACTION_BY_STATUS: dict[RecommendationStatus, str] = {
    RecommendationStatus.RECOMMENDED: "Advance to detailed diligence",
    RecommendationStatus.RECOMMENDED_WITH_REVIEW: "Review the flagged items, then advance",
    RecommendationStatus.NEEDS_INVESTIGATION: "Resolve the missing data before deciding",
    RecommendationStatus.HIGH_RISK: "Investigate the key risks before spending more",
    RecommendationStatus.REJECT: "Do not advance this site",
}

UNSCREENED_NEXT_ACTION = "Run screening for this project"


def build_run_detail(db: Session, run: ScreeningRun) -> ScreeningRunDetail:
    """A run with its sites ranked highest score first."""
    scores = list(
        db.scalars(
            select(SiteScore).where(SiteScore.screening_run_id == run.id).order_by(SiteScore.rank)
        ).all()
    )
    findings = _findings_by_site(db, run.id)
    results = [_screening_result(score, findings.get(score.site_id, [])) for score in scores]

    return ScreeningRunDetail(
        id=run.id,
        project=ProjectRead.model_validate(run.project),
        project_id=run.project_id,
        status=run.status,
        idempotency_key=run.idempotency_key,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
        created_at=run.created_at,
        results=results,
    )


def build_site_detail(db: Session, site: CandidateSite) -> SiteDetail:
    """A site with the result of the most recent run that scored it.

    Document-derived findings are attached whether or not the site has been
    screened, and deterministic findings survive a failed document analysis:
    partial results are still useful (CLAUDE.md rule 4).
    """
    score = db.scalar(
        select(SiteScore)
        .where(SiteScore.site_id == site.id)
        .order_by(SiteScore.created_at.desc())
        .limit(1)
    )

    findings = _site_findings(db, site.id, score.screening_run_id if score is not None else None)
    next_action = (
        NEXT_ACTION_BY_STATUS[score.recommendation_status]
        if score is not None
        else UNSCREENED_NEXT_ACTION
    )

    return SiteDetail(
        project=ProjectRead.model_validate(site.project),
        site=CandidateSiteRead.model_validate(site),
        score=SiteScoreRead.model_validate(score) if score is not None else None,
        documents=[
            DocumentResponse.model_validate(document)
            for document in sorted(site.documents, key=lambda item: item.created_at)
        ],
        recommended_next_action=next_action,
        **_group(findings),
    )


def build_project_dashboard(db: Session) -> list[ProjectDashboardItem]:
    """Every project with the rollups the dashboard shows, newest first."""
    projects = list(db.scalars(select(Project).order_by(Project.created_at.desc())).all())

    items: list[ProjectDashboardItem] = []
    for project in projects:
        run = _latest_completed_run(db, project.id)
        if run is None:
            items.append(
                ProjectDashboardItem(
                    project=ProjectRead.model_validate(project),
                    candidate_count=len(project.sites),
                    top_score=None,
                    high_risk_finding_count=0,
                    recommended_site_count=0,
                    latest_screening_run_id=None,
                )
            )
            continue

        detail = build_run_detail(db, run)
        items.append(
            ProjectDashboardItem(
                project=ProjectRead.model_validate(project),
                candidate_count=len(detail.results),
                top_score=detail.results[0].score.overall_score if detail.results else None,
                high_risk_finding_count=sum(
                    result.high_risk_finding_count for result in detail.results
                ),
                recommended_site_count=sum(
                    1
                    for result in detail.results
                    if result.score.recommendation_status == RecommendationStatus.RECOMMENDED
                ),
                latest_screening_run_id=run.id,
            )
        )
    return items


def build_site_brief(db: Session, site: CandidateSite) -> SiteBriefRead:
    """The diligence brief — spec §8.1G.

    Every section is read back from what screening and review already produced.
    Nothing is recomputed here, so the brief cannot disagree with the screen the
    reviewer approved it from.
    """
    detail = build_site_detail(db, site)

    run = _latest_completed_run(db, site.project_id)
    ranking = [
        BriefRankingEntry(
            site_id=result.site.id,
            site_name=result.site.name,
            rank=result.score.rank,
            overall_score=result.score.overall_score,
            recommendation_status=result.score.recommendation_status.value,
            is_selected_site=result.site.id == site.id,
        )
        for result in (build_run_detail(db, run).results if run is not None else [])
    ]

    return SiteBriefRead(
        generated_at=datetime.now(UTC),
        project=detail.project,
        site=detail.site,
        score=detail.score,
        candidate_ranking=ranking,
        positive_signals=detail.positive_signals,
        risks=detail.risks,
        permitting_requirements=detail.permitting_requirements,
        missing_information=detail.missing_information,
        documents=detail.documents,
        recommended_next_steps=_next_steps(detail),
    )


def _screening_result(score: SiteScore, findings: list[RiskFinding]) -> SiteScreeningResult:
    grouped = _group(findings)
    return SiteScreeningResult(
        site=CandidateSiteRead.model_validate(score.site),
        score=SiteScoreRead.model_validate(score),
        high_risk_finding_count=_count_severity(
            grouped["risks"], {FindingSeverity.HIGH, FindingSeverity.FATAL}
        ),
        warning_count=_count_severity(grouped["risks"], {FindingSeverity.WARNING}),
        recommended_next_action=NEXT_ACTION_BY_STATUS[score.recommendation_status],
        **grouped,
    )


def _next_steps(detail: SiteDetail) -> list[str]:
    """The brief's "recommended next steps", derived from what screening found."""
    steps = [detail.recommended_next_action]

    pending = [
        finding
        for finding in detail.permitting_requirements
        if finding.review_status == ReviewStatus.PENDING
    ]
    if pending:
        steps.append(
            f"Review {len(pending)} pending permitting requirement(s) against the evidence"
        )
    if not detail.documents:
        steps.append("Upload a zoning or permitting ordinance to assess permitting readiness")
    if detail.missing_information:
        steps.append(
            f"Supply {len(detail.missing_information)} missing input(s) so the site is scored "
            "on evidence rather than gaps"
        )
    return steps


def _count_severity(findings: list[RiskFindingRead], severities: set[FindingSeverity]) -> int:
    return sum(1 for finding in findings if finding.severity in severities)


def _latest_completed_run(db: Session, project_id: str) -> ScreeningRun | None:
    return db.scalar(
        select(ScreeningRun)
        .where(
            ScreeningRun.project_id == project_id,
            ScreeningRun.status.in_(
                [ScreeningRunStatus.COMPLETED, ScreeningRunStatus.PARTIALLY_COMPLETED]
            ),
        )
        .order_by(ScreeningRun.created_at.desc())
        .limit(1)
    )


def _site_findings(db: Session, site_id: str, run_id: str | None) -> list[RiskFinding]:
    """The site's findings from its latest run, plus every document finding.

    A document finding carries no ``screening_run_id`` — it comes from an
    ordinance, not from a run — so filtering by run alone would hide it.
    """
    from_run: ColumnElement[bool] = RiskFinding.screening_run_id.is_(None)
    if run_id is not None:
        from_run = or_(from_run, RiskFinding.screening_run_id == run_id)

    return list(
        db.scalars(
            select(RiskFinding)
            .where(RiskFinding.site_id == site_id, from_run)
            .options(selectinload(RiskFinding.evidence))
            .order_by(RiskFinding.created_at)
        ).all()
    )


def _findings_by_site(db: Session, run_id: str) -> dict[str, list[RiskFinding]]:
    findings = db.scalars(
        select(RiskFinding)
        .where(RiskFinding.screening_run_id == run_id)
        .options(selectinload(RiskFinding.evidence))
    ).all()

    by_site: dict[str, list[RiskFinding]] = {}
    for finding in findings:
        by_site.setdefault(finding.site_id, []).append(finding)
    return by_site


def _group(findings: list[RiskFinding]) -> dict[str, list[RiskFindingRead]]:
    """Split findings into the four lists the site detail screen shows."""
    buckets: dict[FindingGroup, list[RiskFindingRead]] = {group: [] for group in FindingGroup}
    for finding in findings:
        buckets[finding.group].append(RiskFindingRead.model_validate(finding))

    return {
        "positive_signals": buckets[FindingGroup.POSITIVE_SIGNAL],
        "risks": buckets[FindingGroup.RISK],
        "permitting_requirements": buckets[FindingGroup.REQUIREMENT],
        "missing_information": buckets[FindingGroup.MISSING_INFORMATION],
    }
