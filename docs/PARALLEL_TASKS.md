# Parallel work — ownership boundaries

Five agents will build SiteSift from this foundation commit, each in its own
Superset worktree. This document says who owns what, so that two agents do not
edit the same file at the same time and so that no one changes a shared shape
out from under someone else.

Every agent branches from the same foundation commit.

## Ownership

### Backend screening agent

Owns:

- `backend/app/models/**` — projects, candidate_sites, screening_runs, site_scores, risk_findings
- `backend/app/schemas/project.py`, `site.py`, `screening.py`, `finding.py`
- `backend/app/services/csv_import.py` — CSV parsing and validation (spec §17)
- `backend/app/services/scoring.py` — category scores, overall score, status (spec §14)
- `backend/app/services/ranking.py`
- `backend/app/api/routes/projects.py`, `sites.py`, `screenings.py`, `findings.py`
- `backend/tests/` for the above
- The initial Alembic migration

Constraints: everything here is deterministic. No LLM call may produce a number,
a threshold decision, or a status. Screening must be idempotent per
`idempotency_key` (spec §18).

### Frontend agent

Owns:

- `frontend/**` (all of it)
- Screens: dashboard, new screening, screening results, site detail, document
  evidence, diligence brief (spec §10)
- API integration through `frontend/lib/api.ts`
- Loading, empty, and error states for every data-backed view

Constraints: consumes `docs/API_CONTRACT.md`; does not invent fields. Where the
backend is not ready, mock at the `lib/api.ts` boundary rather than reshaping
types. Never display model reasoning or chain-of-thought — only workflow step,
tool, status, structured output, evidence, and errors (spec §10.5).

### Document-analysis agent

Owns:

- `backend/app/workflows/**` — the LangGraph permitting graph (spec §13)
- `backend/app/services/document_parser.py` — PDF text extraction, page-aware chunking
- `backend/app/models/document.py`, `evidence.py`, `workflow_event.py`
- `backend/app/schemas/document.py`, `evidence.py`
- `backend/app/api/routes/documents.py`
- `demo-data/sample-zoning-ordinance.pdf`
- `backend/tests/` for the above

Constraints: every extracted requirement carries evidence (document, page or
section, verbatim excerpt) and a confidence score, and page references are
validated against the extracted text before persisting. Failure in this workflow
must leave deterministic screening results intact (spec §9.4). Calls no scoring
code; scoring calls no LLM.

### Integration agent

Owns:

- Merging the completed branches
- Reconciling `docs/API_CONTRACT.md` against what was actually built
- `backend/app/api/router.py` conflicts, Alembic revision linearization
- The end-to-end flow: create project → import sites → screen → rank → upload
  PDF → analyze → review a finding → generate brief
- `docker-compose.yml` and `.superset/` if the merged stack needs changes

Does not add features. If a branch is missing something, hand it back.

### Audit agent

Owns:

- Test coverage against spec §20 (unit, integration, frontend, acceptance)
- Screenshots of each screen
- `docs/AUDIT.md` — findings, gaps, and risks

**No production changes during the first audit pass.** Report first; fix only
after the report is reviewed.

## High-conflict shared files

Do not edit these casually, and never in parallel without coordination. If you
must, keep the edit to the smallest possible number of lines and say so in your
final summary.

| File | Why it conflicts | Rule |
| --- | --- | --- |
| `backend/app/schemas/common.py` | Shared enums and IDs; frontend mirrors it | Contract change — propose in `docs/API_CONTRACT.md` first |
| `frontend/types/api.ts` | Mirror of the above | Must stay member-for-member identical |
| `docs/API_CONTRACT.md` | Every agent reads it | Append; do not rewrite another agent's section |
| `backend/app/api/router.py` | Every backend agent adds a router include | One line per agent, appended at the end |
| `backend/app/models/__init__.py` | Every model must be imported for Alembic | One import line per model, appended |
| `backend/alembic/versions/**` | Parallel revisions branch from the same head | Coordinate, or let the integration agent `alembic merge` |
| `backend/requirements.txt` | Parallel dependency additions | Append only; do not re-pin someone else's dependency |
| `frontend/package.json` | Same | Append only; commit the matching `package-lock.json` |
| `docker-compose.yml`, `.superset/**`, `.env.example` | Environment for everyone | Integration agent owns these after the foundation |
| `CLAUDE.md` | Instructions for everyone | Foundation/integration only |

## Rules for every agent

1. Read `CLAUDE.md` and `docs/API_CONTRACT.md` before writing code.
2. Never silently change a shared schema. It breaks someone else's branch.
3. Deterministic calculations stay out of LLM workflows, and vice versa.
4. Every document-derived finding must carry evidence.
5. Run `./scripts/check.sh` before declaring your work complete. All of it must
   pass — backend format, lint, types, tests; frontend lint, types, tests, build.
6. Stay in your lane. If you need something another agent owns, note it in your
   summary rather than reaching into their files.
