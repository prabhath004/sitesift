"""The seeded demo project — spec §7 and §24, "Load Sample Solar Project".

Safe to run repeatedly. The project carries a fixed id, so a second call finds
the existing project and returns it untouched rather than creating a second
Hudson Valley. That means a reviewer can hit the button as often as they like
and always land on the same demo.

The five sites are the spec's, loaded through the ordinary CSV import path — the
demo exercises the same validation and de-duplication code as a real upload, so
seeding proves the import works rather than bypassing it.
"""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.screening_run import ScreeningRun
from app.schemas.common import ProjectType, ScreeningRunStatus
from app.schemas.project import ProjectStatus, ScreeningCriteria
from app.services.screening import run_screening
from app.services.site_import import import_sites_csv

# A fixed id is what makes the seed idempotent without a "have I seeded yet?" flag.
DEMO_PROJECT_ID = "11111111-1111-4111-8111-111111111111"
DEMO_IDEMPOTENCY_KEY = "demo-seed"

DEMO_CSV_PATH = Path(__file__).resolve().parents[3] / "demo-data" / "candidate-sites.sample.csv"

# The demo data is checked in, but the seed must not fail if the repository was
# packaged without demo-data/. Spec §7 is the source of truth either way.
FALLBACK_CSV = (
    "site_name,latitude,longitude,acreage,jurisdiction,"
    "road_distance_miles,flood_overlap_percent,wetland_overlap_percent\n"
    "River Road,42.110,-73.910,34,Greenfield County,0.7,0,2\n"
    "Oak Parcel,42.145,-73.880,27,Greenfield County,1.1,4,14\n"
    "County Route 9,42.090,-73.970,22,Greenfield County,0.4,0,1\n"
    "Mill Farm,42.180,-73.930,41,Greenfield County,2.8,7,4\n"
    "North Ridge,42.125,-73.850,31,Greenfield County,1.3,2,5\n"
)


def seed_demo_project(db: Session) -> tuple[Project, ScreeningRun, bool]:
    """Create the demo project, sites, and one completed run.

    Returns the project, its screening run, and whether anything was created.
    """
    existing = db.get(Project, DEMO_PROJECT_ID)
    if existing is not None:
        run = db.scalar(
            select(ScreeningRun)
            .where(
                ScreeningRun.project_id == DEMO_PROJECT_ID,
                ScreeningRun.status == ScreeningRunStatus.COMPLETED,
            )
            .order_by(ScreeningRun.created_at)
            .limit(1)
        )
        if run is not None:
            return existing, run, False

        # The project exists but its run does not — a previous seed was
        # interrupted. Finish the job rather than leaving a half-seeded demo.
        return existing, run_screening(db, existing, DEMO_IDEMPOTENCY_KEY), True

    project = Project(
        id=DEMO_PROJECT_ID,
        name="Hudson Valley Community Solar",
        project_type=ProjectType.COMMUNITY_SOLAR,
        target_capacity_mw=5,
        minimum_acres=25,
        target_state="NY",
        screening_criteria=ScreeningCriteria(
            maximum_flood_overlap_percent=5,
            maximum_wetland_overlap_percent=10,
            maximum_road_distance_miles=2,
        ).model_dump(),
        notes="Sample project from the SiteSift specification (§7).",
        status=ProjectStatus.ACTIVE,
    )
    db.add(project)
    db.flush()

    import_sites_csv(db, project, _demo_csv())
    run = run_screening(db, project, DEMO_IDEMPOTENCY_KEY)

    return project, run, True


def _demo_csv() -> str:
    if DEMO_CSV_PATH.exists():
        return DEMO_CSV_PATH.read_text(encoding="utf-8")
    return FALLBACK_CSV
