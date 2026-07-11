# SiteSift

Evidence-backed site triage for renewable energy and power infrastructure.

SiteSift accepts candidate project sites, applies transparent screening rules,
ranks the sites, and extracts permitting requirements from supporting documents
with page-level evidence and human review.

The engineering idea is the separation between three layers:

- **Deterministic software** for measurable facts and rules (acreage, overlaps,
  distances, scores) — reproducible, no LLM involved.
- **Agent-assisted analysis** for unstructured permitting documents, producing
  structured output with page-level citations.
- **Human approval** before any document-derived conclusion counts as final.

Full product definition: [`SiteSift_Product_Spec.md`](./SiteSift_Product_Spec.md).

---

## Status: foundation

This repository currently contains **the foundation only** — a runnable shell
that parallel agents can branch from. No SiteSift feature is implemented.

### What is implemented

| Area | State |
| --- | --- |
| FastAPI app, CORS, `/api` router structure | ✅ |
| `GET /health` (reports service and database reachability) | ✅ |
| Configuration via `pydantic-settings` (`.env`; every default works) | ✅ |
| SQLAlchemy engine, session, declarative `Base` | ✅ |
| Alembic wired to app settings (no revisions yet) | ✅ |
| Shared status enums and ID types, mirrored backend ↔ frontend | ✅ |
| Next.js app shell, nav, page layout, loading/empty/error components | ✅ |
| Dashboard placeholder that calls the backend health endpoint | ✅ |
| API client (`frontend/lib/api.ts`) | ✅ |
| Backend test (health) and frontend tests (backend status: success + failure) | ✅ |
| Tooling: ruff, mypy, pytest, eslint, tsc, vitest, next build | ✅ |
| Docker Compose (Postgres + backend + frontend) | ✅ |
| Superset run/config, sample CSV, API contract, ownership docs | ✅ |

### What is intentionally **not** implemented

Deferred to the feature branches — their absence is not a bug:

- Project intake and the "New Screening" flow
- CSV import and row validation
- Deterministic screening checks, category scoring, overall score, ranking
- ORM models and the initial migration (no tables exist yet)
- PDF upload, text extraction, and the LangGraph document workflow
- Evidence extraction and citation validation
- Human review of findings
- The diligence brief and report generation
- Geospatial integrations (PostGIS, flood/wetland layers) and maps
- The seeded demo ("Load Sample Solar Project")
- Authentication, a background job queue, production deployment, CI
- Product screens beyond the dashboard placeholder, and any real visual design

## Architecture

```text
Next.js (TypeScript, Tailwind)          frontend/
        │  REST, JSON, under /api
        ▼
FastAPI (Pydantic)                      backend/app/api
        ├── services/    deterministic screening — no LLM, reproducible
        └── workflows/   LangGraph document analysis — structured output + evidence
        ▼
PostgreSQL (SQLAlchemy + Alembic)       backend/app/models
```

The boundary between `services/` (deterministic) and `workflows/` (LLM-assisted)
is the core architectural rule of the project. See `CLAUDE.md`.

## Local setup

Requirements: Python 3.11+, Node 20+, optionally Docker.

### Option A — scripts

```bash
cp .env.example .env        # optional; every value has a working default
./scripts/setup.sh          # venv + backend deps + frontend deps
./scripts/dev.sh            # start both, on the first free ports
```

Open the frontend URL that `dev.sh` prints. The dashboard should show **Backend
connected**.

No `.env` and no AI keys are required. The database defaults to SQLite
(`backend/sitesift.db`), so nothing extra needs to be installed or running.

### Option B — Docker

```bash
docker compose up
```

Starts Postgres, the backend (`http://localhost:8000`), and the frontend
(`http://localhost:3000`). Override `BACKEND_PORT`, `FRONTEND_PORT`, and
`POSTGRES_PORT` to run more than one stack at a time.

## Commands

**Backend** (from `backend/`, via `./.venv/bin/…` or an activated venv):

```bash
uvicorn app.main:app --reload --port 8000   # run  → /health, /docs
pytest                                      # tests
ruff format . && ruff check .               # format + lint
mypy                                        # type check
alembic revision --autogenerate -m "…"      # create a migration
alembic upgrade head                        # apply migrations
```

**Frontend** (from `frontend/`):

```bash
npm run dev          # run
npm test             # vitest
npm run lint         # eslint
npm run typecheck    # tsc --noEmit
npm run build        # production build
```

**Everything at once:**

```bash
./scripts/check.sh   # all backend + frontend gates; run before finishing work
```

## Superset workflow

`.superset/config.json` and `.superset/run.sh` support running several worktrees
side by side: ports come from `BACKEND_PORT` / `FRONTEND_PORT`, and when those
are unset `run.sh` picks the first free port at or above 8000 / 3000. It also
copies `.env.example` to `.env` when one is missing, creates the virtual
environment, installs both dependency sets, and shuts child processes down
cleanly on exit.

```bash
./.superset/run.sh setup    # install everything
./.superset/run.sh start    # run backend + frontend
```

## Next development branches

Each branch starts from this foundation commit. Ownership boundaries and the
high-conflict shared files are in
[`docs/PARALLEL_TASKS.md`](./docs/PARALLEL_TASKS.md); the shared contract is in
[`docs/API_CONTRACT.md`](./docs/API_CONTRACT.md).

| Branch | Scope |
| --- | --- |
| `feat/backend-screening` | Models, CSV import, scoring, ranking, project/site/screening APIs |
| `feat/frontend` | Screens, API integration, UI states |
| `feat/document-analysis` | PDF parsing, LangGraph workflow, evidence extraction, document APIs |
| `chore/integration` | Merge branches, reconcile contracts, end-to-end flow |
| `chore/audit` | Tests, screenshots, audit report (no production changes on the first pass) |

---

SiteSift provides an early-screening prototype. Results are not legal,
environmental, engineering, utility, title, or investment advice and must be
validated by qualified professionals.
