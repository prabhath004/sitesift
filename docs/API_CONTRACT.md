# SiteSift API contract — version 1

**Status: implemented.** Every endpoint below exists and is exercised by tests.

**The backend is the source of truth, and the contract is now generated, not
transcribed.** `docs/openapi.json` is exported from the running FastAPI app, and
`frontend/lib/api/generated.ts` is generated from it:

```bash
cd frontend && npm run api:generate   # re-exports the spec and regenerates types
```

`frontend/types/api.ts` is no longer a hand-maintained mirror of
`backend/app/schemas/common.py` — it is a set of aliases over the generated types.
A backend field change therefore becomes a TypeScript error rather than a silent
drift. **Changing an enum member, a field name, or a field type is still a
contract change**: update the backend schema, regenerate, and update this
document in the same commit.

Prose below documents intent; the generated spec documents the exact shapes.

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
| `DocumentProcessingStatus` | `uploaded`, `processing`, `validating`, `extracting`, `retrieving`, `analyzing`, `needs_review`, `completed`, `partially_completed`, `failed` |
| `FindingCategory` | `site_suitability`, `environmental`, `access`, `permitting`, `data_completeness` |
| `FindingGroup` | `positive_signal`, `risk`, `missing_information`, `requirement` |
| `RequirementCategory` | `use_permission`, `setback`, `public_hearing`, `decommissioning`, `financial_security`, `environmental_study`, `traffic_study`, `application_requirement`, `other` |
| `PermittingAnalysisStatus` | `not_analyzed`, `pending_document_review`, `analyzed` |

> **Open question (v1):** the spec lists project types as Solar / Battery storage
> / Data center / EV charging / Other (§10.2) but the example request uses
> `community_solar` (§16.1). Both are included until a product decision is made.
> Do not resolve this unilaterally.

## Contract changes made during integration

These were resolved when the three feature branches were merged
(`docs/INTEGRATION_NOTES.md` explains each one):

1. **`DocumentProcessingStatus` gained six members.** The document-analysis branch
   carried a parallel `DocumentWorkflowStatus` enum over the same
   `documents.processing_status` column. Two enums for one column is the drift
   this contract exists to prevent, so the workflow's finer states
   (`validating`, `extracting`, `retrieving`, `analyzing`, `needs_review`,
   `partially_completed`) were folded into the contract enum and the duplicate
   deleted.
2. **`FindingGroup` gained `requirement`.** Document-derived permitting
   requirements are neither risks nor missing information: an obligation an
   ordinance imposes is not a defect in the site, and not an unknown. They get
   their own list.
3. **`RiskFinding` is the only finding shape.** The document branch had a separate
   `DocumentFindingResponse` over the same `risk_findings` table. There is one
   schema now; it carries `evidence[]`, and the document-only fields
   (`requirement_category`, `original_title`, `original_description`,
   `requires_human_review`, `confidence`) are null/false on a deterministic
   finding.
4. **New endpoints** (see below): `GET /api/projects/dashboard`,
   `GET /api/projects/{project_id}/screenings/latest`,
   `GET /api/sites/{site_id}/documents`, `GET /api/sites/{site_id}/brief`.

## Entity contracts

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

### Diligence brief

`GET /api/sites/{site_id}/brief` → `SiteBriefRead`. Spec §8.1G. Every section is
read back from data screening and review already produced — the brief computes no
score and states no new fact, so it cannot disagree with the screen a reviewer
approved it from.

Sections: project summary, selected site, candidate ranking, positive signals,
major risks, permitting requirements (with evidence and review status), missing
information, recommended next steps, evidence references.

### Derived reads

Both exist so the UI never derives a backend-owned value itself:

- `GET /api/projects/dashboard` → `ProjectDashboardItem[]` — per project:
  `candidate_count`, `top_score`, `high_risk_finding_count`,
  `recommended_site_count`, `latest_screening_run_id`.
- `GET /api/projects/{project_id}/screenings/latest` → `ScreeningRunDetail` — the
  latest run with its embedded project and ranked results. 404 when the project
  has never been screened, which the UI shows as an empty state, not an error.

`SiteScreeningResult` also carries `high_risk_finding_count`, `warning_count`, and
`recommended_next_action`. The frontend's mock used to compute all three; they are
conclusions drawn from findings and a recommendation status, and the backend is
the only place allowed to draw them.

## Not in v1

Authentication, pagination, filtering, sorting parameters, and webhooks remain
undefined. The agent that first needs one proposes it here before implementing it.
