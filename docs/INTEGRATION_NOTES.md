# Integration notes

How `feature/backend-screening`, `feature/document-analysis`, and
`feature/frontend` were merged into one working application, what conflicted, and
what is still open.

Merge commits, in order:

| Commit | Merge |
| --- | --- |
| `40e8669` | `merge: backend screening` |
| `4244efb` | `merge: document analysis` |
| `fccd869` | `merge: frontend` |

## The conflicts that mattered

Git reported only three textual conflicts. The dangerous ones were *semantic*:
files that merged cleanly and produced an application that could not start.

### 1. Two ORM classes over one table (`risk_findings`)

Screening defined `RiskFinding`; document analysis defined `DocumentFinding` with
`__tablename__ = "risk_findings"` and a different column set. Both are imported by
`app/models/__init__.py`, so SQLAlchemy raises a duplicate-table error at import —
the merged app could not boot.

**Resolved:** one `RiskFinding`, which is what `docs/API_CONTRACT.md` described all
along. The document columns (`requirement_category`, `original_title`,
`original_description`, `requires_human_review`) are nullable additions, and
`evidence` / `reviews` hang off it. Deterministic screening and document analysis
both write it; neither lost a column.

`category` and the requirement taxonomy were also in conflict — screening's
`category` is the scoring dimension (`permitting`), document's was the kind of
obligation (`setback`, `public_hearing`, …). Both survive: `category` stays the
scoring dimension and `requirement_category` holds the taxonomy. Two document
tests asserted the taxonomy from `category`; they now assert it from
`requirement_category`.

### 2. Two different tables both named `workflow_events`

Screening's event belongs to a screening run (`screening_run_id`, text summaries,
an ordinal). Document's belongs to a LangGraph node (`document_id`,
`analysis_request_id`, JSON summaries, evidence). Same name, different entity.

**Resolved:** they are not merged into one table — that would have forced one to
drop columns. Screening keeps `workflow_events`; the document events move to
`document_workflow_events` (`DocumentWorkflowEvent`). Both audit trails are intact.

### 3. Stub `projects` / `candidate_sites`

The document branch carried `ProjectRecord` and `CandidateSiteRecord` — cut-down
mappings onto `projects` and `candidate_sites` so it could validate uploads
against a real site id while developed in isolation. Its own docstring asked
integration to reconcile them.

**Resolved:** stubs deleted; document code uses the real `Project` and
`CandidateSite`. `CandidateSite` gained a `documents` relationship.

### 4. One route path, two handlers

Both branches registered `GET /sites/{site_id}/findings`. FastAPI takes the first
match, so whichever router was included first would have silently hidden the
other's findings — deterministic risks *or* document requirements would have
vanished with no error.

**Resolved:** `app/api/routes/findings.py` owns every finding path and returns both
kinds together with evidence eager-loaded. `PATCH /findings/{id}/review` moved
there too. The documents router no longer registers a findings path.

### 5. Two Alembic roots that both create the same tables

Both revisions had `down_revision = None`, and both created `projects`,
`candidate_sites`, and `risk_findings`. This is *not* fixable with a merge
revision: upgrading through both would fail on a duplicate table.

**Resolved:** the document revision is rebased onto the screening revision
(`down_revision = "21e763a954ce"`). It no longer creates the three shared tables;
it `ALTER`s `risk_findings` to add the document columns and creates only its own
tables. One linear history, one head. `alembic check` reports no drift between the
models and the migrations.

### 6. Two enums over one column

`DocumentWorkflowStatus` (9 members, document branch) and the contract's
`DocumentProcessingStatus` (4 members) both described
`documents.processing_status`.

**Resolved — contract change:** the workflow's finer states were folded into
`DocumentProcessingStatus` and the duplicate deleted. `docs/API_CONTRACT.md` and
the frontend types are updated.

### 7. Textual conflicts

`backend/app/api/router.py` and `backend/app/models/__init__.py` (each branch
rewrote them) were resolved as reconciled unions. `backend/requirements.txt`
auto-merged but listed `python-multipart` twice; deduplicated. The union is
`langgraph`, `PyMuPDF`, `python-multipart`.

## The frontend was not connected to anything

It merged without a textual conflict — it shares no files with the backend — but
`lib/api.ts` exported `siteSiftApi = mockApi`, and the mock **computed scores,
ranks, recommendation statuses, finding counts, and next actions in TypeScript**.
That is a second implementation of the deterministic scoring the backend owns
(CLAUDE.md rule 1), and two implementations disagree the moment either changes.

What integration did:

- `lib/api/client.ts` — the real client. One call per operation; it reads scores
  and statuses and never computes them.
- `lib/api/generated.ts` — generated from `docs/openapi.json` (`npm run
  api:generate`). `types/api.ts` is now aliases over it, not a hand-written mirror,
  so a backend field change is a TypeScript error instead of silent drift. No
  `any` was used to paper over a mismatch.
- Backend endpoints were added so the UI never derives a backend-owned value:
  `GET /api/projects/dashboard`, `GET /api/projects/{id}/screenings/latest`, and
  `high_risk_finding_count` / `warning_count` / `recommended_next_action` on each
  ranked result.
- The permitting section was a disabled placeholder. It is now upload → analyze →
  page-level evidence → approve/edit/reject/escalate, plus the diligence brief.

### Mock-data behaviour

The mock survives for isolated frontend work, but:

- it is **off unless `NEXT_PUBLIC_USE_MOCK_API=true`**, and the integrated app
  defaults to the real backend;
- **a failed request never falls back to it.** A fabricated score presented as a
  screening result is the one failure mode this product cannot have. When the API
  is unreachable the UI shows an error state — verified in a browser;
- it serves `lib/api/fixtures.json`, **recorded from the real backend** by
  `scripts/record-fixtures.py`, not invented. The mock cannot make up a score; it
  can only replay one. Operations that must not be faked (create project, CSV
  import) return 501 telling the developer to turn the mock off.

## Regenerating the contract

```bash
cd frontend && npm run api:generate     # exports docs/openapi.json, regenerates lib/api/generated.ts
python3 scripts/record-fixtures.py      # re-records frontend fixtures from the real backend
```

Both artifacts are checked in, so a contract change shows up as a reviewable diff.

Regenerating the types immediately caught real imprecision: fields the API always
sends (`evidence`, `confidence`, `requirement_category`, `error_message`,
`summary`, …) were optional in the schema because they had Pydantic defaults,
which handed the frontend a `| undefined` it could never actually receive. The
backend schemas were tightened to say what the API really does.

## Hardcoding checks

Production frontend code (`app/`, `components/`, `lib/`, excluding the mock and
fixtures) was searched for demo values — `Hudson Valley`, `River Road`,
`North Ridge`, `Oak Parcel`, `County Route 9`, `Mill Farm`, `Greenfield`, scores
`88`/`79`, `localhost`, fixed IDs — and direct `fetch` calls.

Result: none. One form placeholder read `"Hudson Valley Community Solar"` and was
made generic. `API_BASE_URL` in `lib/api/client.ts` reads `NEXT_PUBLIC_API_URL`
and keeps `http://localhost:8000` only as a development default; that is the one
place a default belongs, and it is not a component.

`frontend/tests/sentinel.test.tsx` enforces this going forward: it drives the
**real** HTTP client (with `fetch` stubbed) using values nothing could plausibly
bake in — `SENTINEL_PROJECT_7429`, `SENTINEL_SITE_3816`, `7.37` MW, `43.62` acres,
page `47` evidence — and asserts they render on the dashboard, the ranking, and the
site detail. If someone hard-codes a project name, score, count, or API URL into a
production component, that test fails.

## What was verified, and how

Backend (`backend/`): `ruff format --check`, `ruff check`, `mypy` (78 files),
`pytest` — **160 passed**. `alembic upgrade head` on an empty SQLite database
builds all 14 tables; `alembic check` reports no model/migration drift.

Frontend (`frontend/`): `npm run lint`, `npm run typecheck`, `npm test` — **29
passed** — and `npm run build` (6 routes).

Runtime, against a real `uvicorn` + `next start` on a fresh database, driven with
a headless browser:

| Check | Result |
| --- | --- |
| Seed → exactly five candidate sites | 5 |
| Seed is idempotent | second call 200, `created=false`, same run, still 5 sites |
| Screening is idempotent (`Idempotency-Key`) | replay returns 200 and the same run |
| Duplicate CSV import | 5 duplicates reported, 0 imported, site count unchanged |
| Category scores sum to the overall score | 25+25+25+10 = 85 = sum of breakdown |
| Fatal finding overrides the number | County Route 9 scores 68 but is `reject` |
| Permitting pending before analysis | `not_analyzed`, no requirements |
| Missing information separate from risks | separate lists throughout |
| Document analysis | 8 findings, **all** with page-level evidence, pages within 1–3 |
| Analysis is idempotent | replay returns the same 8 findings, no duplicates |
| Review approve/edit/reject/escalate | all persist; an edit preserves `original_title` |
| Brief | all 9 spec sections, backend score, evidence, review status |
| Score consistency | 85 on dashboard, ranking, site detail, and brief |
| Persistence across refresh | review decisions survive a reload |
| Upload + analyze + approve **through the UI** | 8 excerpts, 8 page refs, approval survives reload |
| Browser console errors | none |
| Failed API requests | none |

(The only browser network noise is Next.js RSC link *prefetches* aborted on
navigation — expected framework behaviour, not application failures.)

## Requirement extraction: model-backed, with a verification gate

Extraction was a keyword/regex heuristic. It is now a model call when a key is
configured, with the heuristic retained as the fallback.

**Where the code lives matters.** `app/workflows/llm_extraction.py` is the only
module in SiteSift that calls a model, and it sits in `workflows/` because
CLAUDE.md rule 1 forbids `services/` from calling one. The heuristic extractor
stays in `services/` — it computes, it does not infer.

**The model produces claims, not conclusions.** Its output is:

1. constrained by a strict JSON schema (OpenAI structured outputs, `temperature=0`),
2. re-validated by the same `ExtractedRequirement` Pydantic model the heuristic's
   output goes through — malformed output raises `InvalidModelOutputError` rather
   than reaching the database,
3. forced to `requires_human_review = True` regardless of what it claims, and
4. **checked against the extracted page text.** An excerpt that is not a verbatim
   substring of the page it cites is not evidence; it is the model's paraphrase.

**The citation-repair loop.** Point 4 is where a real model actually fails: it
paraphrases the ordinance instead of quoting it, and a naive implementation would
silently drop the finding. So `validate_evidence` now feeds unverifiable citations
into a conditional edge — the only branch in the graph:

```text
extract_requirements → validate_evidence ─┬─ (failed citations, budget left) → repair_citations ─┐
                                          │                                                       │
                                          └─ flag_ambiguity → persist_findings → generate_summary │
                                                     ▲                                            │
                                                     └────────────────────────────────────────────┘
```

`repair_citations` hands the model its own rejected quote and demands a
character-for-character copy. The repaired requirement goes back through evidence
validation — a repair is a second attempt to *prove* a claim, never a licence to
skip the proof. The budget is `EXTRACTION_CITATION_RETRIES` (default 1); when it
is spent, the unverifiable claims are discarded and the run reports
`partially_completed` with the reason, rather than quietly showing fewer findings
than the document contains.

The repair step is a first-class node, so it appears in the public workflow trail
with its status and duration — a reviewer can see that a citation was rejected and
re-requested. As with every event, only summaries are recorded: no document text,
no model reasoning (rules 6 and 7).

**No key, no problem.** `select_extractor()` returns the model-backed extractor
when `OPENAI_API_KEY` is set and the heuristic otherwise. Tests inject their own
extractor and never touch the network, so CI needs no secret, and a demo survives
a dead network or a rate limit. The system degrades to *deterministic*, never to
*fabricated*.

## Limitations and open items

- **Postgres was not exercised.** Docker is unavailable in this environment, so
  migrations and tests ran on SQLite, the documented local default.
  `docker compose up` is unchanged and should work, but it is unverified here.
- **`NEXT_PUBLIC_*` is inlined at build time.** Pointing the frontend at a
  different backend needs a rebuild, not just a restart. `.superset/run.sh`
  already exports `NEXT_PUBLIC_API_URL` and a matching `CORS_ORIGINS` for the
  ports it picks; a hand-rolled run that skips `CORS_ORIGINS` will be blocked by
  the browser even though `curl` succeeds.
- **Permitting score does not yet respond to review.** Approving a permitting
  requirement records the decision and shows it everywhere, but the permitting
  category still reports `not_analyzed` / 10 of 25. Feeding approved requirements
  back into the deterministic score is a product decision the spec does not make,
  so it was left alone rather than invented.
- **The model-backed extractor has not been exercised against the live OpenAI
  API here** — no key is configured in this environment. It is covered by tests
  with a stubbed client (request shape, structured-output parsing, provider
  failure, repair prompting) and the repair loop is covered end to end with
  extractors that paraphrase. Set `OPENAI_API_KEY` and re-run the document flow to
  exercise it for real.
- **Extraction cost and latency are unmeasured.** One call per analysis (up to 8
  retrieved sections), plus one more if a citation needs repair.
- **Review has no reviewer identity.** `reviews` rows are append-only but
  anonymous; there is no auth in v1.
- **The mock client cannot create projects or import CSVs** (it returns 501 by
  design). Those paths need the real backend.
