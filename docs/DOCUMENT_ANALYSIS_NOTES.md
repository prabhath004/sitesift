# Document Analysis Notes

## Implemented API Surface

- `POST /api/sites/{site_id}/documents`
- `GET /api/documents/{document_id}`
- `POST /api/documents/{document_id}/analyze`
- `GET /api/documents/{document_id}/analysis`
- `GET /api/sites/{site_id}/findings`
- `PATCH /api/findings/{finding_id}/review`

## Contract Notes

- Document processing uses the finer statuses required by this branch:
  `uploaded`, `validating`, `extracting`, `retrieving`, `analyzing`,
  `needs_review`, `completed`, `partially_completed`, `failed`.
- The shared draft enum in `backend/app/schemas/common.py` still has the older
  foundation values. I did not update the frontend mirror because this branch is
  not allowed to modify `frontend/**`. Integration should reconcile the shared
  enum and `docs/API_CONTRACT.md`.
- Review request `decision` values use the shared `ReviewDecision` enum:
  `approve`, `edit`, `reject`, `escalate`. The product spec's `approved`
  example is treated as a typo because `approved` is a resulting review status,
  not a decision.
- Duplicate upload behavior is defined as same `site_id` plus PDF SHA-256 hash:
  the API returns the existing document with HTTP 200 and does not create a new
  row.
- `storage_path`, `content_hash`, and `size_bytes` are internal and are not
  returned by document response schemas.

## Confidence Rules

- `confidence >= 0.80`: valid evidence, persisted as `pending` human review.
- `0.55 <= confidence < 0.80`: valid evidence, persisted as `pending` human
  review.
- `0.25 <= confidence < 0.55`: valid evidence, persisted as `pending`, and the
  document is marked `partially_completed`.
- `confidence < 0.25`: rejected by validation and not persisted.
- Missing or invalid evidence is never persisted as a verified finding.
- No document-derived finding is automatically approved.

## Integration Assumptions

- This isolated branch adds minimal `projects` and `candidate_sites` table
  definitions so document upload can enforce that a site exists. The screening
  branch owns the complete versions of those tables; integration should merge
  the definitions and preserve the document foreign-key behavior.
- The default requirement extractor is a deterministic local fallback for tests
  and demos. The LangGraph node accepts an injected extractor so a real
  model-backed implementation can be added without changing evidence validation,
  persistence, or review behavior.
- Synchronous analysis is implemented. `document_analysis_requests` and
  `workflow_events` are structured so a background worker can take over later.
