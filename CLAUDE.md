# CLAUDE.md — SiteSift

Instructions for any agent working in this repository. Read this and
`docs/API_CONTRACT.md` before writing code.

## What SiteSift is

Evidence-backed site triage for renewable energy and power infrastructure
projects. A developer uploads candidate sites and project requirements;
SiteSift validates the data, runs **deterministic** screening checks, ranks the
sites with a fully explainable score, extracts permitting requirements from one
zoning/permitting PDF with **page-level evidence**, routes those findings through
**human review**, and produces a diligence brief.

It is not a chatbot. The full product definition is `SiteSift_Product_Spec.md`;
that spec is the source of truth for scope. Do not invent product decisions it
does not make.

**Current state: foundation only.** An app shell, a health endpoint, shared
enums, and empty packages. No screening, scoring, CSV import, document analysis,
review, or brief exists yet — see "What is not built" in `README.md`.

## Repository structure

```text
sitesift/
├── backend/            FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── main.py     App shell: CORS, /health, /api router
│   │   ├── api/        Routers. routes/health.py is the only endpoint today
│   │   ├── core/       Settings (pydantic-settings)
│   │   ├── database/   Engine, session, declarative Base
│   │   ├── models/     ORM models — empty
│   │   ├── schemas/    Pydantic. common.py = shared IDs + status enums
│   │   ├── services/   Deterministic business logic — empty
│   │   └── workflows/  LangGraph / LLM work — empty
│   ├── alembic/        Migrations (no revisions yet)
│   └── tests/          pytest
├── frontend/           Next.js (App Router) + TypeScript + Tailwind
│   ├── app/            Routes. Dashboard placeholder only
│   ├── components/     layout/, states/ (loading, empty, error)
│   ├── lib/api.ts      API client — all backend calls go through here
│   └── types/api.ts    Shared types — mirrors backend/app/schemas/common.py
├── demo-data/          Sample candidate-site CSV
├── docs/               API_CONTRACT.md, PARALLEL_TASKS.md
├── scripts/            setup.sh, dev.sh, check.sh
├── .superset/          config.json, run.sh
└── docker-compose.yml
```

## Commands

```bash
./scripts/setup.sh          # venv + backend deps + frontend deps
./scripts/dev.sh            # run both (auto-picks free ports)
./scripts/check.sh          # every quality gate — run before finishing
docker compose up           # alternative: Postgres + backend + frontend
```

Individually:

```bash
# Backend (from backend/, venv active or via ./.venv/bin/…)
uvicorn app.main:app --reload --port "${BACKEND_PORT:-8000}"
pytest
ruff format . && ruff check . && mypy
alembic revision --autogenerate -m "…" && alembic upgrade head

# Frontend (from frontend/)
npm run dev
npm test
npm run lint && npm run typecheck && npm run build
```

Ports are configurable (`BACKEND_PORT`, `FRONTEND_PORT`) because several
worktrees may run at once. Never hard-code a port.

## Coding conventions

**Backend**

- Python 3.11+, full type annotations (`mypy` runs with `disallow_untyped_defs`).
- `ruff format` and `ruff check` must pass. Line length 100.
- Routers in `app/api/routes/`, one module per resource; register in
  `app/api/router.py` with a single `include_router` line.
- Pydantic schemas for every request and response body. No bare `dict` payloads.
- Business logic lives in `app/services/`, not in route handlers.
- Every ORM model inherits `app.database.base.Base` and is imported in
  `app/models/__init__.py` (Alembic autogenerate depends on it).
- Schema changes require an Alembic revision in the same commit.

**Frontend**

- TypeScript strict. `npm run typecheck` and `npm run lint` must pass.
- Server Components by default; `"use client"` only where interaction requires it.
- All backend calls go through `lib/api.ts`. Do not call `fetch` directly.
- Types come from `types/api.ts`. Do not redefine API shapes locally, and do not
  use `any`.
- Every data-backed view handles loading, empty, and error states using
  `components/states`.
- Tailwind utilities; no CSS-in-JS, no component library.

## API contract rules

`docs/API_CONTRACT.md` is the shared contract. `backend/app/schemas/common.py`
and `frontend/types/api.ts` are mirrors of each other and must stay identical,
member for member.

- **Never silently change a shared schema.** Changing an enum member, a field
  name, or a field type breaks another agent's branch. Update both mirror files
  and `docs/API_CONTRACT.md` in the same commit, and call it out in your summary.
- Adding a new endpoint or entity: document it in `docs/API_CONTRACT.md` first.
- JSON is `snake_case` in both directions. IDs are UUID strings. Percentages are
  0–100. Distances are miles. Areas are acres. Scores are integers.

## File ownership

`docs/PARALLEL_TASKS.md` assigns every area to an agent (backend screening,
frontend, document analysis, integration, audit) and lists the high-conflict
shared files. Stay inside your boundary. If you need a change in someone else's
area, say so in your summary instead of making it.

## Engineering rules

These come straight from the product principles (spec §9) and are not
negotiable:

1. **Deterministic calculations stay separate from LLM workflows.** Acreage,
   distances, overlaps, threshold checks, category scores, the overall score,
   and status assignment are computed in `app/services/` with ordinary code, and
   must be reproducible without an LLM. `app/workflows/` never computes a number
   or assigns a score; `app/services/` never calls a model.
2. **Document findings must include evidence.** Every document-derived claim
   carries the source document, a page number or section, a verbatim excerpt,
   and a confidence score. Page references are validated against the extracted
   text before persisting. A document finding without evidence is a bug — do not
   persist it, do not display it.
3. **Humans stay in control.** A document-derived requirement is not final until
   a reviewer approves it. Review history is append-only.
4. **Partial results are useful.** If document analysis fails, deterministic
   screening results must remain visible. Do not let a workflow failure take down
   a screening run.
5. **The score must be explainable.** Show every deduction. Never present a
   number the UI cannot break down.
6. **Do not display model reasoning.** Show the workflow step, the tool, the
   status, the structured output, the evidence, and errors — nothing else.
7. **Never log full uploaded documents or user content.** Log `request_id`,
   `project_id`, `site_id`, `screening_run_id`, `workflow_step`, `status`,
   `duration_ms`, `error_type`.

## Before you finish

Run `./scripts/check.sh` and make sure it passes end to end: backend format,
lint, types, and tests; frontend lint, types, tests, and production build. New
behavior needs new tests — scoring rules and CSV validation need boundary cases,
document extraction needs an evidence-validation test.

Do not claim work is complete without showing the command output that proves it.
