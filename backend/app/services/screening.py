"""Running a screening — spec §8.1C, §14, §18.

Deterministic end to end. This module reads project criteria, scores every
candidate site with ``scoring``, ranks them with ``ranking``, and persists the
scores, findings, and workflow events in a single transaction. It calls no
model and imports nothing from ``app.workflows`` (CLAUDE.md rule 1).

Execution is synchronous. The run row still moves through ``QUEUED`` ->
``SCREENING`` -> ``COMPLETED``, so handing the work to a queue later means
changing who advances the row, not what the row looks like.
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.candidate_site import CandidateSite
from app.models.project import Project
from app.models.risk_finding import RiskFinding
from app.models.screening_run import ScreeningRun
from app.models.site_score import SiteScore
from app.models.workflow_event import WorkflowEvent
from app.schemas.common import (
    FindingSourceType,
    ReviewStatus,
    ScreeningRunStatus,
)
from app.schemas.project import ProjectStatus, ScreeningCriteria
from app.services.ranking import RankedSite, rank_sites
from app.services.scoring import ScoringCriteria, SiteScoringInput, score_site


class NoCandidateSitesError(Exception):
    """A project cannot be screened until it has at least one candidate site."""


def find_run_by_idempotency_key(
    db: Session, project_id: str, idempotency_key: str
) -> ScreeningRun | None:
    """Spec §18 — a replayed request returns the original run rather than a new one."""
    return db.scalar(
        select(ScreeningRun).where(
            ScreeningRun.project_id == project_id,
            ScreeningRun.idempotency_key == idempotency_key,
        )
    )


def find_latest_run(db: Session, project_id: str) -> ScreeningRun | None:
    """The project's most recent run, whatever its outcome.

    A failed or partially completed run is still the latest thing that happened
    to the project, and hiding it would leave the results screen showing an older
    run as if it were current.
    """
    return db.scalar(
        select(ScreeningRun)
        .where(ScreeningRun.project_id == project_id)
        .order_by(ScreeningRun.created_at.desc())
        .limit(1)
    )


def run_screening(
    db: Session, project: Project, idempotency_key: str | None = None
) -> ScreeningRun:
    """Screen every candidate site in a project and persist the result.

    Raises ``NoCandidateSitesError`` before creating a run, so a project with
    nothing to screen does not accumulate empty runs.
    """
    sites = list(
        db.scalars(
            select(CandidateSite)
            .where(CandidateSite.project_id == project.id)
            .order_by(CandidateSite.sequence)
        ).all()
    )
    if not sites:
        raise NoCandidateSitesError(
            "This project has no candidate sites. Import a candidate-site CSV before screening."
        )

    run = ScreeningRun(
        project_id=project.id,
        status=ScreeningRunStatus.QUEUED,
        idempotency_key=idempotency_key,
    )
    db.add(run)
    db.flush()

    events = _EventLog(db, run)
    run.status = ScreeningRunStatus.SCREENING
    run.started_at = utcnow()

    with events.step("load_project", f"project {project.id}") as step:
        criteria = _criteria_for(project)
        step.output = (
            f"minimum_acres={criteria.minimum_acres:g}, "
            f"max_flood={criteria.maximum_flood_overlap_percent:g}%, "
            f"max_wetland={criteria.maximum_wetland_overlap_percent:g}%, "
            f"max_road={criteria.maximum_road_distance_miles:g}mi"
        )

    with events.step("load_candidate_sites", f"project {project.id}") as step:
        step.output = f"{len(sites)} candidate sites"

    with events.step("score_sites", f"{len(sites)} sites") as step:
        scored = [(site, score_site(_scoring_input(site), criteria)) for site in sites]
        step.output = f"{len(scored)} sites scored"

    with events.step("rank_sites", f"{len(scored)} scored sites") as step:
        ranked = rank_sites(scored)
        step.output = ", ".join(f"{entry.rank}. {entry.site.name}" for entry in ranked)

    with events.step("persist_results", f"{len(ranked)} ranked sites") as step:
        findings = _persist(db, run, ranked)
        step.output = f"{len(ranked)} scores, {findings} findings"

    run.status = ScreeningRunStatus.COMPLETED
    run.completed_at = utcnow()
    project.status = ProjectStatus.SCREENED

    db.flush()
    return run


def _criteria_for(project: Project) -> ScoringCriteria:
    """Project thresholds, falling back to the spec defaults for anything absent."""
    criteria = ScreeningCriteria.model_validate(project.screening_criteria or {})
    return ScoringCriteria(
        minimum_acres=project.minimum_acres,
        maximum_flood_overlap_percent=criteria.maximum_flood_overlap_percent,
        maximum_wetland_overlap_percent=criteria.maximum_wetland_overlap_percent,
        maximum_road_distance_miles=criteria.maximum_road_distance_miles,
    )


def _scoring_input(site: CandidateSite) -> SiteScoringInput:
    return SiteScoringInput(
        acreage=site.acreage,
        road_distance_miles=site.road_distance_miles,
        flood_overlap_percent=site.flood_overlap_percent,
        wetland_overlap_percent=site.wetland_overlap_percent,
    )


def _persist(db: Session, run: ScreeningRun, ranked: list[RankedSite]) -> int:
    """Write scores and findings. Returns the number of findings written."""
    finding_count = 0

    for entry in ranked:
        result = entry.result
        db.add(
            SiteScore(
                screening_run_id=run.id,
                site_id=entry.site.id,
                overall_score=result.overall_score,
                site_suitability_score=result.site_suitability_score,
                environmental_score=result.environmental_score,
                access_score=result.access_score,
                permitting_score=result.permitting_score,
                permitting_status=result.permitting_status,
                recommendation_status=result.recommendation_status,
                rank=entry.rank,
                explanation=result.explanation,
                breakdown=[item.model_dump(mode="json") for item in result.breakdown],
            )
        )

        for draft in result.findings:
            db.add(
                RiskFinding(
                    site_id=entry.site.id,
                    screening_run_id=run.id,
                    source_type=FindingSourceType.DETERMINISTIC,
                    category=draft.category,
                    group=draft.group,
                    rule=draft.rule,
                    title=draft.title,
                    description=draft.description,
                    severity=draft.severity,
                    value=draft.value,
                    actual_value=draft.actual_value,
                    threshold_value=draft.threshold_value,
                    # A threshold check is not a probabilistic claim. Confidence
                    # belongs to document findings, and stays NULL here.
                    confidence=None,
                    review_status=ReviewStatus.PENDING,
                )
            )
            finding_count += 1

    db.flush()
    return finding_count


class _Step:
    """Mutable handle so a step body can set its own output summary."""

    def __init__(self) -> None:
        self.output: str | None = None


class _EventLog:
    """Records one ``workflow_events`` row per screening step (spec §18 auditability).

    Summaries only — never row content (CLAUDE.md rule 7).
    """

    def __init__(self, db: Session, run: ScreeningRun) -> None:
        self._db = db
        self._run = run
        self._sequence = 0

    @contextmanager
    def step(self, name: str, input_summary: str) -> Iterator[_Step]:
        started = time.perf_counter()
        handle = _Step()
        try:
            yield handle
        except Exception as exc:
            self._record(name, "failed", input_summary, None, started, type(exc).__name__)
            raise
        self._record(name, "completed", input_summary, handle.output, started, None)

    def _record(
        self,
        name: str,
        status: str,
        input_summary: str,
        output_summary: str | None,
        started: float,
        error_message: str | None,
    ) -> None:
        self._db.add(
            WorkflowEvent(
                screening_run_id=self._run.id,
                step_name=name,
                status=status,
                input_summary=input_summary,
                output_summary=output_summary,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error_message=error_message,
                sequence=self._sequence,
            )
        )
        self._sequence += 1
