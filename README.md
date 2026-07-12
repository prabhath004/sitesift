# SiteSift

Evidence-backed site triage for renewable energy and power infrastructure.

SiteSift is a full-stack MVP for early project diligence. It accepts candidate
project sites, applies transparent screening rules, ranks the sites, analyzes
permitting or zoning PDFs through a LangGraph workflow, validates page-level
evidence, and routes document-derived findings through human review.

Full product definition: [`SiteSift_Product_Spec.md`](./SiteSift_Product_Spec.md).

## What It Does

SiteSift separates the work into three layers:

- **Deterministic screening** for measurable facts and rules: acreage, flood
  overlap, wetland overlap, road distance, scores, rankings, and next actions.
- **Agentic document analysis** for unstructured permitting documents: PDF text
  extraction, retrieval, OpenAI-backed structured requirement extraction,
  citation validation, ambiguity handling, and workflow events.
- **Human review** before document-derived conclusions are treated as reviewed:
  approve, edit, reject, or escalate extracted requirements.

The frontend renders backend-owned results. It does not compute scores, ranks,
recommendation statuses, finding counts, or next actions.

## Implemented

| Area | State |
| --- | --- |
| Project intake and screening criteria | Implemented |
| Candidate-site CSV upload, preview, validation, import | Implemented |
| Deterministic screening and ranking | Implemented |
| Site score breakdowns and risk findings | Implemented |
| Dashboard and project results UI | Implemented |
| Site detail, findings, missing information, and brief UI | Implemented |
| PDF upload and parsing | Implemented |
| LangGraph permitting-analysis workflow | Implemented |
| OpenAI-backed requirement extraction (`gpt-4.1-mini` default) | Implemented |
| Page-level evidence validation | Implemented |
| Human review for document-derived findings | Implemented |
| Diligence brief generation | Implemented |
| Generated frontend API types from OpenAPI | Implemented |
| Backend and frontend tests | Implemented |
| Docker Compose local stack | Implemented |

## Architecture

```text
Next.js / TypeScript / Tailwind          frontend/
        |
        | REST JSON under /api
        v
FastAPI / Pydantic                       backend/app/api
        |-- services/                    deterministic import, scoring, ranking
        |-- workflows/                   LangGraph document analysis
        v
SQLAlchemy / Alembic                     backend/app/models
        v
SQLite locally, Postgres in Docker
```

The important boundary is deliberate: deterministic scoring stays in
`backend/app/services`, while the unstructured permitting-document workflow lives
in `backend/app/workflows`.

## Scoring

Each site receives a 100-point score:

| Category | Points |
| --- | ---: |
| Site suitability / acreage | 25 |
| Environmental | 25 |
| Access and road distance | 25 |
| Permitting readiness | 25 |

Environmental is split into flood overlap and wetland overlap. Permitting starts
at the missing-evidence band until an ordinance is analyzed; document-derived
requirements are shown separately and must be reviewed by a human.

Recommendation status is assigned by the backend:

| Rule | Status |
| --- | --- |
| Fatal finding | `reject` |
| Score >= 80 | `recommended` |
| Score >= 70 | `recommended_with_review` |
| Score >= 55 | `needs_investigation` |
| Otherwise | `high_risk` |

Ranking is deterministic: overall score descending, fewer fatal findings, fewer
high-severity findings, then CSV import order.

## Agentic Document Workflow

PDF analysis is run by `backend/app/workflows/permitting_graph.py`.

```text
validate_document
extract_text
create_page_chunks
retrieve_relevant_sections
extract_requirements
validate_evidence
flag_ambiguity
persist_findings
generate_summary
```

The `extract_requirements` node uses OpenAI when `OPENAI_API_KEY` is configured.
The default model is `gpt-4.1-mini`, chosen as the cheaper 4.1-family default
for structured extraction. If no key is configured, the app falls back to the
local heuristic extractor so demos and tests still run offline.

Every extracted requirement must include evidence. The backend verifies that the
quoted excerpt appears on the cited PDF page before persisting the finding.

## Local Setup

Requirements: Python 3.11+, Node 20+, optionally Docker.

```bash
cp .env.example .env
./scripts/setup.sh
./scripts/dev.sh
```

Open the frontend URL printed by `dev.sh`.

Useful optional `.env` values:

```bash
OPENAI_API_KEY=...
DOCUMENT_EXTRACTOR_PROVIDER=auto
OPENAI_DOCUMENT_MODEL=gpt-4.1-mini
NEXT_PUBLIC_USE_MOCK_API=false
```

Provider behavior:

| `DOCUMENT_EXTRACTOR_PROVIDER` | Behavior |
| --- | --- |
| `auto` | Use OpenAI when `OPENAI_API_KEY` exists, otherwise heuristic fallback |
| `openai` | Require OpenAI extraction and fail if the key is missing |
| `heuristic` | Force local extractor |

## Demo Data

Sample files live in [`demo-data/`](./demo-data):

- [`candidate-sites.sample.csv`](./demo-data/candidate-sites.sample.csv)
- [`sample-zoning-ordinance.pdf`](./demo-data/sample-zoning-ordinance.pdf)

Fastest demo path:

1. Start the app.
2. Click **Load Sample Solar Project**.
3. Open a ranked site.
4. Upload `demo-data/sample-zoning-ordinance.pdf` in the permitting panel.
5. Review the extracted requirements and open the diligence brief.

Manual CSV path:

1. Click **New Screening**.
2. Fill in project details and thresholds.
3. Upload `demo-data/candidate-sites.sample.csv`.
4. Run screening.

## Commands

Backend:

```bash
cd backend
./.venv/bin/uvicorn app.main:app --reload --port 8000
./.venv/bin/pytest
./.venv/bin/ruff format . && ./.venv/bin/ruff check .
./.venv/bin/mypy
./.venv/bin/alembic upgrade head
```

Frontend:

```bash
cd frontend
npm run dev
npm test
npm run lint
npm run typecheck
npm run build
```

All checks:

```bash
./scripts/check.sh
```

## Docker

```bash
docker compose up
```

This starts Postgres, the backend at `http://localhost:8000`, and the frontend at
`http://localhost:3000`. Override `BACKEND_PORT`, `FRONTEND_PORT`, and
`POSTGRES_PORT` to run multiple stacks side by side.

## Contracts And Fixtures

The frontend client reads backend-owned values and uses generated API types.

```bash
cd frontend && npm run api:generate
python3 scripts/record-fixtures.py
```

The mock API is only enabled by `NEXT_PUBLIC_USE_MOCK_API=true`. It replays
recorded backend fixtures and does not create projects, import CSVs, or compute
scores in TypeScript.

## Current Limitations

- Geospatial values are uploaded as precomputed CSV fields in the MVP.
- Permitting findings do not yet recalculate the numeric permitting score after
  review; they are shown as evidence-backed requirements.
- Review records are anonymous because authentication is out of scope.
- The workflow runs synchronously; a background queue would be the next
  production step.

SiteSift provides early-screening support only. Results are not legal,
environmental, engineering, utility, title, or investment advice and must be
validated by qualified professionals.
