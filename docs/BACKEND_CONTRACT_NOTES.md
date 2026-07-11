# Backend screening — contract notes

Written by the backend-screening agent (`feature/backend-screening`). It records
every place where this branch had to resolve something `docs/API_CONTRACT.md` or
`SiteSift_Product_Spec.md` left open, and every addition it makes to the shared
contract.

Nothing here changes an existing field, enum member, or type. Every item is
**additive**. `backend/app/schemas/common.py` is **untouched**, because its
mirror `frontend/types/api.ts` belongs to the frontend agent and the two must
stay identical member for member (CLAUDE.md). The new enums therefore live in
backend-owned schema modules, and the TypeScript the frontend needs is written
out below so the mirror can be added in one edit.

---

## 1. The spec's demo numbers cannot be produced by the spec's scoring rules

**The problem.** §14 defines the scoring bands as discrete steps:

| Rule | Bands |
| --- | --- |
| Acreage | 25 / 15 / 8 / 0 |
| Flood overlap | 12 / 6 / 0 |
| Wetland overlap | 13 / 7 / 0 |
| Road distance | 25 / 15 / 5 |
| Permitting | 25 / 18 / 10 / 0 |

No combination of those numbers produces the site scores in §7 and §10.3 — River
Road at 88 (shown in §10.4 as 24 + 23 + 21 + 20), Oak Parcel at 61, Mill Farm at
47, County Route 9 at 35. Every one of those category scores (24, 23, 21, 20) is
off-band. The two parts of the spec cannot both be right.

**The decision.** **§14 is authoritative; §7 and §10.3 are illustrative
mockups.** The rules are the algorithm, the tables are a sketch of the screen. A
scoring engine has to be derived from rules, not from a picture of a table.

**What that produces**, with the spec's own criteria (25 acres, 5% flood, 10%
wetland, 2 miles):

| Rank | Site | Suit. | Env. | Access | Permit | Overall | Status |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | River Road | 25 | 25 | 25 | 10 | **85** | recommended |
| 2 | North Ridge | 25 | 25 | 25 | 10 | **85** | recommended |
| 3 | Oak Parcel | 25 | 19 | 25 | 10 | **79** | recommended_with_review |
| 4 | Mill Farm | 25 | 19 | 15 | 10 | **69** | needs_investigation |
| 5 | County Route 9 | 8 | 25 | 25 | 10 | **68** | reject (fatal) |

The **ranking is exactly the order §7 expects**, and the two verdicts the demo
narrative turns on — River Road recommended, County Route 9 rejected for
insufficient acreage — both hold. The middle statuses read more generously than
the §10.3 mockup because the mockup's scores are lower than any rule produces.

**If the product wants the mockup's statuses**, the lever is the status
thresholds (§14: 80 / 70 / 55), not the scoring bands. That is a product
decision, and this branch did not make it.

## 2. Nothing in the spec says what makes a finding fatal

**The problem.** §14's status rule makes `Reject` reachable *only* through
`fatal_findings > 0`. §7 expects County Route 9 — 22 acres against a 25-acre
minimum, which is 88% of the requirement — to be rejected for insufficient
acreage. But the spec never defines a deterministic rule that emits a fatal
finding, so as written, nothing can ever be rejected.

**The decision.** **Acreage below the project minimum is the one fatal
deterministic finding.** It is the only rule that can produce the Reject the demo
requires. A site that cannot physically hold the project is a fatal flaw in a way
that a threshold exceedance is not.

Consequences, stated plainly:

- Every site below the minimum is rejected, whichever §14 acreage band it lands
  in. The bands still set the *number* (how far below it is), while the fatal
  finding sets the *status*.
- Flood, wetland, and road exceedances are `high`, **never** `fatal`. This is
  what §10.3 implies: Oak Parcel and Mill Farm carry high risks and are not
  rejected.

## 3. Permitting readiness, with no document analyzed

**The problem.** This branch does not read ordinances — that is the
document-analysis branch. But permitting is 25 of the 100 points, and the score
must not imply an assessment that never happened.

**The decision.** Permitting scores §14's own band for exactly this state —
*"Ambiguous or missing ordinance evidence: +10"* — and every score carries an
explicit `permitting_status` saying so. The placeholder is the spec's number, not
an invented one, and it is never presented as a pass.

- `permitting_score` = **10 of 25** on every site.
- `permitting_status` = **`not_analyzed`** on every site.
- A `warning`-severity finding, grouped as **missing information** (not as a
  risk): *"Permitting readiness not analyzed."*

When document analysis lands, it should set `permitting_status` to `analyzed` and
score the remaining §14 bands (25 permitted by right / 18 conditional / 0
prohibited). `PermittingAnalysisStatus.ANALYZED` exists for that and is written
by nothing on this branch.

## 4. "Slightly over" versus "materially over" a threshold

**The problem.** §14 says flood and wetland overlap score a partial band when
"slightly over" the threshold and zero when "materially over", without saying
where the line is.

**The decision.** **Slightly over = up to 1.5x the threshold. Materially over =
beyond 1.5x.** The 1.5x multiple is not invented: §14 uses it explicitly for road
distance ("Road distance <= 1.5x preferred distance"). Reusing it keeps one
notion of "how far over is too far" across all three checks.

## 5. A missing optional value scores zero and is not a risk

**The problem.** `road_distance_miles`, `flood_overlap_percent`, and
`wetland_overlap_percent` are optional. The spec never says how to score a site
that omits one.

**The decision.** A missing input **scores zero for that check** and is reported
as **missing information**, never as a risk.

- Zero, not partial credit: an unverified site is not a qualified site, and
  awarding points for an absent measurement would let a site rank on data nobody
  supplied.
- Missing information, not a risk: not knowing something is not the same as
  having found a problem. Spec §10.4 and §26 keep the two lists apart, and the
  API keeps them apart too.

A cell that is *present but unparseable* (`road_distance_miles: "close"`) is a
row-level validation error, not a missing value. Treating it as missing would let
a typo silently masquerade as absent data.

## 6. Ranking ties

**The problem.** River Road and North Ridge both score 85. "Rank from highest to
lowest" does not say what to do about that, and an unstable answer makes the demo
flicker between runs.

**The decision.** Sort by overall score descending, then by fewer fatal findings,
then by fewer high-severity findings, then by **import order**. Import order is
the last tiebreak because it is the only remaining signal that is stable across
runs. River Road (CSV row 2) therefore ranks above North Ridge (row 6), as §7
expects. `candidate_sites.sequence` carries the import position.

---

## Contract additions

### New enums

```ts
// frontend/types/api.ts — to be added by whoever owns the mirror

// Whether the permitting category rests on a real document.
export type PermittingAnalysisStatus =
  | "not_analyzed"
  | "pending_document_review"
  | "analyzed";

// Which screening dimension a finding belongs to.
export type FindingCategory =
  | "site_suitability"
  | "environmental"
  | "access"
  | "permitting"
  | "data_completeness";

// How a finding should be presented (spec §10.4).
export type FindingGroup = "positive_signal" | "risk" | "missing_information";

// Project lifecycle. The v1 contract types `Project.status` as a plain string;
// these are the values the backend actually emits.
export type ProjectStatus = "active" | "screening" | "screened";
```

Backend homes: `app/schemas/screening.py` (`PermittingAnalysisStatus`),
`app/schemas/finding.py` (`FindingCategory`, `FindingGroup`),
`app/schemas/project.py` (`ProjectStatus`).

### `SiteScore` — three added fields

```jsonc
{
  // ...every field already in the v1 contract...
  "permitting_status": "not_analyzed",   // PermittingAnalysisStatus — see note 3
  "rank": 1,                             // 1 = best. Ranking is persisted, not re-derived.
  "breakdown": [                         // spec §9.5 — every deduction, inspectable
    {
      "category": "environmental",       // FindingCategory
      "rule": "wetland_overlap_threshold",
      "actual_value": 14,
      "threshold_value": 10,
      "points_possible": 13,
      "points_awarded": 7,
      "severity": "high",                // FindingSeverity
      "explanation": "Wetland overlap of 14% exceeds the configured 10% threshold."
    }
  ]
}
```

`breakdown` is the reason the score is defensible. Spec §9.5 forbids presenting a
number the UI cannot break down, so the records that produced the score travel
with it rather than being recomputed on the client. The five rules are
`acreage_minimum`, `flood_overlap_threshold`, `wetland_overlap_threshold`,
`road_distance_threshold`, `permitting_readiness`; their `points_possible` always
sums to 100.

### `RiskFinding` — four added fields

```jsonc
{
  // ...every field already in the v1 contract...
  "category": "environmental",           // now FindingCategory, was an untyped string
  "group": "risk",                       // FindingGroup — which of the three lists it belongs in
  "rule": "wetland_overlap_threshold",   // null for findings no scoring rule produced
  "actual_value": 14,                    // number | null — the measured value
  "threshold_value": 10                  // number | null — what it was measured against
}
```

`value` (the contract's existing display string, e.g. `"14%"`) is unchanged and
still populated. `actual_value` and `threshold_value` are the machine-readable
pair; the UI should not parse `value` to get at them.

`confidence` is **null** on every deterministic finding. A threshold check is not
a probabilistic claim, and giving it a confidence would imply it is one.
Confidence belongs to document findings.

### New response payloads

The v1 contract does not define these. They are proposed here.

```jsonc
// POST /api/projects/{project_id}/sites/import  (multipart, field name: "file")
{
  "project_id": "uuid",
  "summary": {
    "total_rows": 5,      // total_rows == valid_rows + invalid_rows
    "valid_rows": 5,      // passed field validation and unique within the file
    "invalid_rows": 0,    // failed field validation
    "imported_rows": 5,   // actually written
    "duplicate_rows": 0   // already present, or repeated within the file — not written
  },
  "errors": [
    { "row_number": 3, "field": "latitude", "message": "latitude must be between -90 and 90.", "value": "999" }
  ],
  "imported_sites": [ /* CandidateSite[] — only the rows that were written */ ]
}
```

`row_number` counts the header as line 1, so it matches what the user sees in a
spreadsheet. A duplicate is counted in `duplicate_rows` and *not* in
`invalid_rows` — it is a row we already have, not a broken one.

```jsonc
// GET /api/screenings/{screening_id}  — ScreeningRun plus its ranked results
{
  /* ...every ScreeningRun field... */
  "results": [
    {
      "site": { /* CandidateSite */ },
      "score": { /* SiteScore, including breakdown */ },
      "positive_signals": [ /* RiskFinding[] */ ],
      "risks": [ /* RiskFinding[] */ ],
      "missing_information": [ /* RiskFinding[] */ ]
    }
  ]
}

// GET /api/sites/{site_id}  — the same shape, minus the run
{
  "site": { /* CandidateSite */ },
  "score": { /* SiteScore */ } | null,   // null until a run has scored the site
  "positive_signals": [], "risks": [], "missing_information": []
}

// GET /api/screenings/{screening_id}/events  — WorkflowEvent[]
{
  "id": "uuid",
  "screening_run_id": "uuid",
  "step_name": "score_sites",
  "status": "completed",
  "input_summary": "5 sites",
  "output_summary": "5 sites scored",
  "duration_ms": 3,
  "error_message": null,
  "created_at": "iso8601"
}

// POST /api/demo/seed  — spec §24, "Load Sample Solar Project"
{
  "project": { /* Project */ },
  "screening_run": { /* ScreeningRunDetail, as above */ },
  "created": true    // false when the demo already existed and nothing was created
}
```

The three finding lists are pre-grouped by the backend rather than derived on the
client, so that "missing information is not a risk" is enforced in one place
instead of being re-decided by every consumer.

### Status codes

| Case | Code | Why |
| --- | --- | --- |
| Create project / import sites / create screening | `201` | Something was created. |
| Screening replayed with a known `Idempotency-Key` | `200` | A replay is not a creation. The existing run is returned. |
| `POST /api/demo/seed` when the demo already exists | `200` | Nothing was created; `created: false`. |
| Project or site not found | `404` | Includes a malformed UUID — an id that cannot exist is not found. |
| Empty CSV, malformed CSV, missing columns, non-UTF-8, oversized | `400` | The file is unusable. Row-level errors are *not* 400 — they come back in the import summary with a `201`. |
| Screening a project with no candidate sites | `409` | The project exists; its state does not permit the operation. |
| Database failure | `500` | A fixed sentence. No driver text, no SQL, no stack trace. |

Idempotency is scoped **per project**: the same `Idempotency-Key` in two
different projects creates two runs. A key is not a global identifier.

---

## Ownership overlaps — for the integration agent

1. **`backend/app/models/workflow_event.py`.** `docs/PARALLEL_TASKS.md` assigns
   this module to the **document-analysis agent**, but
   `GET /api/screenings/{id}/events` — which this branch was asked for — needs
   the table. It is implemented here, at the exact path that document names, so
   that a merge produces one conflict in one file rather than two competing
   tables. The columns are the spec's (§15.9) and nothing in them is specific to
   deterministic screening: the LangGraph nodes should be able to write their own
   steps to this table unchanged. If document analysis needs a nullable
   `document_id`, add the column; do not fork the table.

2. **`risk_findings` has no foreign key to `documents` or `evidence`.** Evidence
   points at a finding, not the other way round (spec §15.7), so the two branches
   can land in either order. This branch writes only `source_type:
   "deterministic"` rows and never writes evidence.

3. **`GET /api/sites/{site_id}/findings` is read-only here.**
   `PATCH /api/findings/{finding_id}/review` belongs to the human-review flow,
   which this branch does not build. `review_status` is written as `pending` and
   never advanced.

4. **`backend/app/schemas/common.py` was not modified**, so
   `frontend/types/api.ts` still mirrors it exactly. The four new enums above are
   the only additions the mirror needs.

## Left for integration, deliberately

- Background execution. Screening is synchronous, but the run row already moves
  `queued` -> `screening` -> `completed`, and `ScreeningRunStatus` retains
  `document_analysis`, `needs_review`, `partially_completed`, and `failed` for
  the branches that will use them. Moving to a queue means changing who advances
  the row, not what the row looks like.
- `partially_completed` is defined but never assigned on this branch: nothing
  here can partially fail. It is what a run should become when deterministic
  screening succeeds and document analysis does not (spec §9.4).
- Pagination, filtering, and sorting parameters — still out of scope in v1.
