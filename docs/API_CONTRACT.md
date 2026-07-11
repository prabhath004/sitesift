# SiteSift API contract — version 1 (draft)

**Status: draft. Nothing below is implemented yet** apart from `GET /health` and
the shared status enums. This document exists so that the backend, frontend, and
document-analysis agents can work in parallel against the same shapes.

Source of truth for the shared enums:

- Backend: `backend/app/schemas/common.py`
- Frontend: `frontend/types/api.ts`

Those two files must always agree, member for member. **Changing an enum member,
a field name, or a field type is a contract change**: update both files and this
document in the same commit, and say so in the commit message. Do not change a
shared shape silently — another agent is coding against it.

## Conventions

- Base path `/api`. `GET /health` sits at the root (infrastructure probe).
- Identifiers are UUID strings on the wire.
- Field names are `snake_case` in JSON, in both directions.
- Timestamps are ISO 8601 UTC (`2026-07-11T16:00:00Z`).
- Errors use FastAPI's default shape: `{"detail": "..."}` (422 for validation).
- Percentages are numbers 0–100. Distances are miles. Areas are acres.
- Scores are integers 0–100; category scores are integers 0–25.

## Status enums (implemented)

These are the only parts of the contract that exist in code today.

| Enum | Values |
| --- | --- |
| `ProjectType` | `solar`, `community_solar`, `battery_storage`, `data_center`, `ev_charging`, `other` |
| `ScreeningRunStatus` | `queued`, `screening`, `document_analysis`, `needs_review`, `completed`, `partially_completed`, `failed` |
| `RecommendationStatus` | `recommended`, `recommended_with_review`, `needs_investigation`, `high_risk`, `reject` |
| `FindingSourceType` | `deterministic`, `document`, `human` |
| `FindingSeverity` | `info`, `warning`, `high`, `fatal` |
| `ReviewStatus` | `pending`, `approved`, `edited`, `rejected`, `escalated` |
| `ReviewDecision` | `approve`, `edit`, `reject`, `escalate` |
| `DocumentProcessingStatus` | `uploaded`, `processing`, `completed`, `failed` |

> **Open question (v1):** the spec lists project types as Solar / Battery storage
> / Data center / EV charging / Other (§10.2) but the example request uses
> `community_solar` (§16.1). Both are included until a product decision is made.
> Do not resolve this unilaterally.

## Entity contracts (draft — not implemented)

### Project

```jsonc
{
  "id": "uuid",
  "name": "Hudson Valley Community Solar",
  "project_type": "community_solar",       // ProjectType
  "target_capacity_mw": 5,
  "minimum_acres": 25,
  "target_state": "NY",
  "screening_criteria": {
    "maximum_flood_overlap_percent": 5,
    "maximum_wetland_overlap_percent": 10,
    "maximum_road_distance_miles": 2
  },
  "notes": "string | null",
  "status": "string",
  "created_at": "iso8601",
  "updated_at": "iso8601"
}
```

Endpoints: `POST /api/projects`, `GET /api/projects`, `GET /api/projects/{project_id}`.

### Candidate site

```jsonc
{
  "id": "uuid",
  "project_id": "uuid",
  "name": "River Road",
  "latitude": 42.11,                        // -90..90
  "longitude": -73.91,                      // -180..180
  "acreage": 34,                            // > 0
  "jurisdiction": "Greenfield County",
  "road_distance_miles": 0.7,               // optional, precomputed
  "flood_overlap_percent": 0,               // optional, precomputed
  "wetland_overlap_percent": 2,             // optional, precomputed
  "created_at": "iso8601"
}
```

Endpoints: `POST /api/projects/{project_id}/sites/import` (CSV, multipart),
`GET /api/projects/{project_id}/sites`, `GET /api/sites/{site_id}`.

Import responds with parsed rows plus per-row validation errors; it does not
persist rows that fail validation (spec §17).

### Screening run

```jsonc
{
  "id": "uuid",
  "project_id": "uuid",
  "status": "completed",                    // ScreeningRunStatus
  "idempotency_key": "string | null",
  "started_at": "iso8601 | null",
  "completed_at": "iso8601 | null",
  "error_message": "string | null"
}
```

Endpoints: `POST /api/projects/{project_id}/screenings` (accepts an
`Idempotency-Key`; a repeat must return the existing run, not create a second),
`GET /api/screenings/{screening_id}`, `GET /api/screenings/{screening_id}/events`.

### Site score

```jsonc
{
  "id": "uuid",
  "screening_run_id": "uuid",
  "site_id": "uuid",
  "overall_score": 88,                      // 0..100
  "site_suitability_score": 24,             // 0..25
  "environmental_score": 23,                // 0..25
  "access_score": 21,                       // 0..25
  "permitting_score": 20,                   // 0..25
  "recommendation_status": "recommended",   // RecommendationStatus
  "explanation": "string",
  "created_at": "iso8601"
}
```

Computed deterministically (spec §14). Every deduction must be explainable in
the UI, so the explanation must enumerate deductions rather than summarize them.

### Risk finding

```jsonc
{
  "id": "uuid",
  "site_id": "uuid",
  "screening_run_id": "uuid | null",
  "source_type": "deterministic",           // FindingSourceType
  "category": "string",
  "title": "Wetland overlap exceeds threshold",
  "description": "string",
  "severity": "high",                       // FindingSeverity
  "value": "string | null",
  "confidence": 0.91,                       // 0..1; null for deterministic findings
  "review_status": "pending",               // ReviewStatus
  "evidence": [],                           // Evidence[]; required when source_type = "document"
  "created_at": "iso8601",
  "updated_at": "iso8601"
}
```

Endpoints: `GET /api/sites/{site_id}/findings`, `PATCH /api/findings/{finding_id}/review`.

### Document

```jsonc
{
  "id": "uuid",
  "project_id": "uuid",
  "site_id": "uuid",
  "filename": "greenfield-county-zoning.pdf",
  "mime_type": "application/pdf",
  "page_count": 128,
  "processing_status": "completed",         // DocumentProcessingStatus
  "created_at": "iso8601"
}
```

Endpoints: `POST /api/sites/{site_id}/documents` (multipart PDF),
`POST /api/documents/{document_id}/analyze`, `GET /api/documents/{document_id}/analysis`.

`storage_path` is internal and is never returned to the client.

### Evidence

```jsonc
{
  "id": "uuid",
  "finding_id": "uuid",
  "document_id": "uuid",
  "document_name": "Greenfield County Zoning Ordinance",
  "page_number": 84,                        // nullable, but page or section must be present
  "section_name": "Section 4.3",
  "excerpt": "Utility-scale solar energy systems may be permitted following conditional-use approval by the Planning Board.",
  "created_at": "iso8601"
}
```

The excerpt must be verbatim from the source document, and the page reference
must be verifiable against the extracted text (spec §17). A document-derived
finding with no evidence is invalid and must not be persisted.

### Human review

```jsonc
// PATCH /api/findings/{finding_id}/review
{
  "decision": "approve",                    // ReviewDecision
  "edited_title": "string | null",
  "edited_description": "string | null",
  "reviewer_note": "Confirmed against Section 4.3."
}
```

Responds with the updated risk finding. A finding is not final until it is
approved (spec §9.3). Review history is append-only: a `reviews` row per
decision, never an in-place overwrite.

## Not in v1

Authentication, pagination, filtering, sorting parameters, webhooks, and the
diligence-brief payload (`/api/sites/{site_id}/brief`) are undefined. The agent
that first needs one proposes it here before implementing it.
