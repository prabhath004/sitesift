"""Assembling screening results for the API.

Findings are grouped the way spec §10.4 presents them — positive signals, risks,
and missing information as three separate lists. Missing information is never
folded into risks: not knowing something is not the same as having found a
problem, and the UI must not blur the two.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate_site import CandidateSite
from app.models.risk_finding import RiskFinding
from app.models.screening_run import ScreeningRun
from app.models.site_score import SiteScore
from app.schemas.finding import FindingGroup, RiskFindingRead
from app.schemas.screening import (
    ScreeningRunDetail,
    SiteDetail,
    SiteScoreRead,
    SiteScreeningResult,
)
from app.schemas.site import CandidateSiteRead


def build_run_detail(db: Session, run: ScreeningRun) -> ScreeningRunDetail:
    """A run with its sites ranked highest score first."""
    scores = list(
        db.scalars(
            select(SiteScore).where(SiteScore.screening_run_id == run.id).order_by(SiteScore.rank)
        ).all()
    )
    findings = _findings_by_site(db, run.id)

    results = [
        SiteScreeningResult(
            site=CandidateSiteRead.model_validate(score.site),
            score=SiteScoreRead.model_validate(score),
            **_group(findings.get(score.site_id, [])),
        )
        for score in scores
    ]

    return ScreeningRunDetail(
        id=run.id,
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
    """A site with the result of the most recent run that scored it."""
    score = db.scalar(
        select(SiteScore)
        .where(SiteScore.site_id == site.id)
        .order_by(SiteScore.created_at.desc())
        .limit(1)
    )

    findings: list[RiskFinding] = []
    if score is not None:
        findings = list(
            db.scalars(
                select(RiskFinding).where(
                    RiskFinding.site_id == site.id,
                    RiskFinding.screening_run_id == score.screening_run_id,
                )
            ).all()
        )

    return SiteDetail(
        site=CandidateSiteRead.model_validate(site),
        score=SiteScoreRead.model_validate(score) if score is not None else None,
        **_group(findings),
    )


def _findings_by_site(db: Session, run_id: str) -> dict[str, list[RiskFinding]]:
    findings = db.scalars(select(RiskFinding).where(RiskFinding.screening_run_id == run_id)).all()

    by_site: dict[str, list[RiskFinding]] = {}
    for finding in findings:
        by_site.setdefault(finding.site_id, []).append(finding)
    return by_site


def _group(findings: list[RiskFinding]) -> dict[str, list[RiskFindingRead]]:
    """Split findings into the three lists the site detail screen shows."""
    buckets: dict[FindingGroup, list[RiskFindingRead]] = {group: [] for group in FindingGroup}
    for finding in findings:
        buckets[finding.group].append(RiskFindingRead.model_validate(finding))

    return {
        "positive_signals": buckets[FindingGroup.POSITIVE_SIGNAL],
        "risks": buckets[FindingGroup.RISK],
        "missing_information": buckets[FindingGroup.MISSING_INFORMATION],
    }
